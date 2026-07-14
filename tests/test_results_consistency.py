"""The manuscript, the scorecard and Table 6 must quote the SAME numbers.

This class of bug bit twice in one session and both times it was silent:

  1. `scripts/table4_predictions_scorecard.py` had the van Putten AUROCs HARDCODED, transcribed by hand
     from an earlier run of Table 6. When Table 6 was recomputed under the SAP §3.3 `clean_pair` filter,
     the scorecard kept quoting the old numbers and nothing complained.
  2. The manuscript quoted the pre-filter headline (0.881 / 0.918 / 0.875) long after the table said
     0.875 / 0.911 / 0.870.

Nothing here re-does any science. It only asserts that the three documents agree with each other, so a
recomputed table forces the paper to be updated rather than quietly disagreeing with it.
"""
from __future__ import annotations
import re
from pathlib import Path

import pytest

T6 = Path("results/vanputten_fullcoverage.md")
T4 = Path("results/table4_predictions.md")
MS = Path("docs/manuscript_draft.md")
TARGETS = ["abnormal", "generalized", "focal"]


def gate_row():
    """The Morgoth gate AUROCs, straight from Table 6 — the single source of truth."""
    for ln in T6.read_text().splitlines():
        if not ln.startswith("|") or "Morgoth" not in ln:
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        vals = [float(re.match(r"([0-9.]+)", c).group(1)) for c in cells[1:4] if re.match(r"([0-9.]+)", c)]
        if len(vals) == 3:
            return dict(zip(TARGETS, vals))
    raise AssertionError("no Morgoth gate row found in Table 6")


@pytest.mark.skipif(not (T6.exists() and T4.exists() and MS.exists()), reason="results not built")
def test_scorecard_quotes_table6_gate():
    gate = gate_row()
    t4 = T4.read_text()
    for t, v in gate.items():
        assert f"{v:.3f}" in t4, (
            f"Table 4 does not quote the gate's {t} AUROC ({v:.3f}) from Table 6 — the scorecard has "
            f"drifted from the table it summarises. Re-run scripts/table4_predictions_scorecard.py.")


@pytest.mark.skipif(not (T6.exists() and MS.exists()), reason="results not built")
def test_manuscript_quotes_table6_gate():
    gate = gate_row()
    ms = MS.read_text()
    for t, v in gate.items():
        assert f"{v:.3f}" in ms, (
            f"The manuscript does not quote the gate's {t} AUROC ({v:.3f}) from Table 6. If Table 6 was "
            f"recomputed, docs/manuscript_draft.md §3.1b + the abstract must be updated to match.")


@pytest.mark.skipif(not MS.exists(), reason="manuscript not present")
def test_manuscript_has_no_prefilter_headline():
    """0.881/0.918 are the pre-clean_pair numbers. They may appear ONLY where we explain that they are
    superseded — never as a live claim."""
    for ln in MS.read_text().splitlines():
        if "0.881" in ln or "0.918" in ln:
            assert ("omitted that filter" in ln or "superseded" in ln or "earlier version" in ln.lower()), (
                "The manuscript quotes the pre-clean_pair headline (0.881/0.918) as a live number:\n"
                f"  {ln.strip()[:160]}\n"
                "These violate SAP §3.3 (report-broadcast guard) and were superseded by 0.875/0.911/0.870.")


@pytest.mark.skipif(not MS.exists(), reason="manuscript not present")
def test_every_referenced_figure_exists():
    """The manuscript referenced 7 figures that did not exist on disk. Never again."""
    ms = MS.read_text()
    missing = [f for f in sorted(set(re.findall(r"[A-Za-z0-9_/.-]+\.png", ms))) if not Path(f).exists()]
    assert not missing, f"manuscript references figures that do not exist: {missing}"


DANGLING_BUDGET = 17   # ratchet: may only go DOWN


@pytest.mark.skipif(not MS.exists(), reason="manuscript not present")
def test_dangling_citations_do_not_grow():
    """The manuscript cites files deleted in the legacy purge.

    These are citations to EVIDENCE — a reader following one lands on nothing. 17 remain (listed by this
    test when it fails). Each must either be regenerated on v6 or cut from the draft; six were repointed to
    their v6 replacements already. This is a ratchet, not a pass: the count may only go down.
    """
    refs = set(re.findall(r"`((?:results|data|scripts|docs)/[A-Za-z0-9_/.-]+\.(?:md|csv|json|py|parquet))`",
                          MS.read_text()))
    missing = sorted(r for r in refs if not Path(r).exists())
    assert len(missing) <= DANGLING_BUDGET, (
        f"dangling citations grew to {len(missing)} (budget {DANGLING_BUDGET}):\n  " +
        "\n  ".join(missing) + "\nRegenerate the evidence or cut the citation — do not raise the budget.")


def test_dashboard_figures_all_exist():
    """Every figure the dashboard embeds must exist on disk.

    The dashboard inlines its figures as base64 data URIs, so an audit that greps the HTML for
    `src="....png"` finds NOTHING and cheerfully reports "0 missing, 0 stale" — a vacuous pass. (That is
    exactly what happened, and it hid six stale figures, including a van Putten chart from the superseded
    3,130-recording table.) Check the builder's own figure list instead.
    """
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("bd_", "scripts/build_dashboard_sap.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bd_"] = mod
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    figs = [f for item in mod.ITEMS for f in item[3]]
    assert figs, "dashboard builder exposes no figures — the ITEMS structure changed"
    missing = [str(f) for f in figs if not Path(f).exists()]
    assert not missing, f"dashboard embeds figures that do not exist: {missing}"

    tables = [t for item in mod.ITEMS for t in item[4]]
    missing_t = [str(t) for t in tables if not Path(t).exists()]
    assert not missing_t, f"dashboard links tables that do not exist: {missing_t}"


def test_worker_keeps_all_three_slowing_classes():
    """Morgoth's SLOWING window head is 3-class softmax {0: Others, 1: Focal, 2: Generalized}.

    The first fleet run kept only `p_slowing = 1 - class_0_prob` and discarded class_1_prob/class_2_prob.
    The prediction CSV lives in a tempfile.mkdtemp() dir that is rmtree'd after every recording, so those
    columns were computed and destroyed on the worker node — never written to OUTPUT_ROOT, never synced to
    S3, unrecoverable without a full gate re-run. Any future run MUST persist all three.
    """
    src = Path("scripts/31_segment_master_worker.py").read_text()
    for col in ("class_1_prob", "class_2_prob"):
        assert col in src, f"worker no longer reads {col} — the 3-class head is being collapsed again"
    for out in ("p_focal_seg", "p_gen_seg"):
        assert out in src, f"worker no longer persists {out} to segment_summary"
