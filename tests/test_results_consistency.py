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
