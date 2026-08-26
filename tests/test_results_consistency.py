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
DASHBOARD = Path("scripts/build_story_dashboard.py")
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
def test_manuscript_does_not_quote_superseded_gate_values():
    """The prose must never quote a gate AUROC that Table 6 has SUPERSEDED.

    The original test demanded the manuscript CITE all three gate arms. That was right when SS3.1b quoted the
    row inline, but the paper has since been restructured: Table 6 now reaches the reader as Table S1, inlined
    verbatim (asserted below), and the prose cites only the focal arm in the Discussion. The old test
    therefore failed on a manuscript that was correct.

    A proximity check ("a value near the word gate must match the table") does not work either, and the
    attempt is recorded here so it is not retried: the SAME gate is legitimately benchmarked on THREE
    datasets -- the internal report cohort (Table 6), ON-100, and SAI-100 -- with different and equally
    correct AUROCs, and SS3.5 names both "van Putten" and "Morgoth" while being entirely about ON-100. Any
    line-proximity rule flags that correct paragraph.

    What is actually checkable is the bug that bit: prose left quoting values the table has replaced. So pin
    the superseded numbers explicitly.
    """
    superseded = {"0.881": "abnormal", "0.918": "generalized", "0.875": "focal"}   # pre-clean_pair triple
    live = {f"{v:.3f}" for v in gate_row().values()}
    bad = []
    for ln in MS.read_text().splitlines():
        if not any(w in ln for w in ("Morgoth", "gate")):
            continue
        if any(x in ln.lower() for x in ("superseded", "omitted that filter", "earlier version")):
            continue
        for val, arm in superseded.items():
            # 0.875 is the pre-filter FOCAL value but also the live ABNORMAL value -- only flag it when the
            # table no longer contains it at all, so a legitimate reuse is not a false positive
            if val in ln and val not in live:
                bad.append(f"{val} (superseded {arm}) in: {ln.strip()[:130]}")
    assert not bad, ("manuscript quotes a gate AUROC superseded by Table 6 "
                     f"(live values {sorted(live)}):\n  " + "\n  ".join(bad))


@pytest.mark.skipif(not T6.exists(), reason="results not built")
def test_table6_is_inlined_into_the_manuscript():
    """Table 6's gate row reaches the reader only because the docx builder inlines the file verbatim.

    That is what makes the citation-free prose above safe, so it is worth asserting rather than assuming:
    if the builder stops inlining it, the gate numbers silently leave the paper.
    """
    builder = Path("scripts/build_manuscript_docx.py").read_text()
    assert str(T6) in builder, (
        f"{T6} is no longer inlined by build_manuscript_docx.py -- the gate AUROCs would vanish from the "
        "paper, and the prose does not quote them.")


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
    """The manuscript referenced 7 figures that did not exist on disk. Never again.

    Two shorthands in the prose are legitimate and must be resolved before checking, or the test fails on a
    correct manuscript: a run of panels is written `s4_d1,3,4,6.png` (one token, four files), and after a
    full path is given once, sibling panels are named by BASENAME alone (`s0e_occasion_focal.png`).
    """
    ms = MS.read_text()
    names = set()
    # expand comma runs: s4_d1,3,4,6.png -> s4_d1.png s4_d3.png s4_d4.png s4_d6.png
    for prefix, nums in re.findall(r"([A-Za-z0-9_/.-]*?[A-Za-z_])(\d+(?:,\d+)+)\.png", ms):
        names.update(f"{prefix}{n}.png" for n in nums.split(","))
        ms = ms.replace(f"{prefix}{nums}.png", " ")
    names.update(re.findall(r"[A-Za-z0-9_/.-]+\.png", ms))

    known = {p.name for p in Path("figures").rglob("*.png")} if Path("figures").exists() else set()
    missing = sorted(n for n in names
                     if not Path(n).exists() and Path(n).name not in known)
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


@pytest.mark.skipif(not DASHBOARD.exists(), reason="dashboard builder absent")
def test_dashboard_figures_all_exist():
    """Every figure the dashboard embeds must exist on disk.

    The dashboard inlines its figures as base64 data URIs, so an audit that greps the HTML for
    `src="....png"` finds NOTHING and cheerfully reports "0 missing, 0 stale" — a vacuous pass. (That is
    exactly what happened, and it hid six stale figures, including a van Putten chart from the superseded
    3,130-recording table.) Check the builder's own figure list instead.
    """
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("bd_", DASHBOARD)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bd_"] = mod
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    # SECTIONS = [(id, title, blurb, [(label, blurb, [figs], [tables]), ...]), ...]
    subs = [sub for section in mod.SECTIONS for sub in section[3]]
    figs = [f for sub in subs for f in sub[2]]
    tables = [t for sub in subs for t in sub[3]]
    assert figs, "dashboard builder exposes no figures - the SECTIONS structure changed"

    missing = [str(f) for f in figs if not Path(f).exists()]
    assert not missing, f"dashboard embeds figures that do not exist: {missing}"

    missing_t = [str(x) for x in tables if not Path(x).exists()]
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
