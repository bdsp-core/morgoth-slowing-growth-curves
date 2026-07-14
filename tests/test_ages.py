"""Regression guard for the age column (SAP §6; docs/age_provenance).

The analysis once ran on WHOLE-YEAR ages that were also partly wrong (7 negatives; errors up to 10 y),
while the growth-curve figure plotted age on a log axis with 1/3/6-MONTH ticks — i.e. it displayed
resolution the data did not have, and the infant curve was a quantisation artefact. The corrected ages
(OMOP birth_datetime, 99.6% exact) are committed to metadata/ages_v6.parquet. These tests fail loudly if
anything reverts to the integer ages or violates HIPAA Safe Harbor.
"""
from pathlib import Path
import pandas as pd
import pytest

AGES = Path("metadata/ages_v6.parquet")
pytestmark = pytest.mark.skipif(not AGES.exists(), reason="ages table not present")


@pytest.fixture(scope="module")
def ages():
    return pd.read_parquet(AGES)


def test_ages_are_fractional_not_integer(ages):
    """The bug: 100% of ages were whole numbers. Real ages are overwhelmingly fractional."""
    frac = (ages.age % 1 != 0).mean()
    assert frac > 0.8, f"only {frac:.1%} of ages are fractional — reverted to integer ages?"


def test_no_impossible_ages(ages):
    assert (ages.age >= 0).all(), "negative age — impossible"
    assert (ages.age <= 90).all(), "age > 90 — see Safe Harbor test"


def test_hipaa_safe_harbor_90plus_binned(ages):
    """Ages over 89 are identifiers and MUST be aggregated. The de-identified OMOP does NOT do this
    for us (it returns ages up to 121), so we must."""
    assert (ages.age > 90).sum() == 0, "un-binned age above 90 — HIPAA Safe Harbor violation"


def test_infants_have_subyear_resolution(ages):
    """The whole point: a 6-month-old and an 18-month-old must not both be '1'."""
    u2 = ages[ages.age < 2]
    assert len(u2) > 500, "implausibly few under-2s"
    assert (u2.age % 1 != 0).mean() > 0.9, "under-2 ages are whole numbers — infant curve is fake"


def test_coverage(ages):
    exact = (ages.age_source == "fractional(OMOP)").mean()
    assert exact > 0.95, f"only {exact:.1%} of ages are exact — the OMOP lookup did not apply"


def test_derived_tables_carry_fractional_ages():
    """Guard the revert path: the analysis tables are rebuilt by fleet_analysis_adapter.py, which used to
    take `age` straight from the manifest (integer, partly wrong). It now overrides from metadata/ages_v6."""
    import pandas as pd
    from pathlib import Path
    for t in ("data/derived/labels_unified.parquet", "data/derived/channel_stage_features.parquet"):
        p = Path(t)
        if not p.exists():
            continue
        a = pd.read_parquet(p, columns=["age"]).age.dropna()
        if len(a) < 100:
            continue
        frac = (a % 1 != 0).mean()
        assert frac > 0.8, f"{t}: only {frac:.1%} fractional ages — a rebuild reverted to integer ages"
        assert a.max() <= 90, f"{t}: age {a.max()} > 90 — HIPAA Safe Harbor violation"


def test_authoritative_age_table_is_tracked_in_git():
    """The anti-reversion guarantee is only real if the file is IN GIT.

    metadata/ages_v6.parquet is matched by .gitignore's blanket `*.parquet`, so it was silently untracked
    even though every producer reads it as the single source of truth. If it is absent from a fresh clone,
    the adapter falls back to the manifest's integer ages and the age bug returns with no error message.
    """
    import subprocess
    r = subprocess.run(["git", "ls-files", "--error-unmatch", "metadata/ages_v6.parquet"],
                       capture_output=True)
    assert r.returncode == 0, (
        "metadata/ages_v6.parquet is NOT tracked by git — a fresh clone would silently revert to the "
        "manifest's integer ages. Re-add the `!metadata/ages_v6.parquet` negation to .gitignore.")
