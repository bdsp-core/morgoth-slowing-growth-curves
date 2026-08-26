"""Rebuild data/derived/labels_unified.parquet from the manifest (the healthy source-of-record).

WHY: the 2026-07-18 reorg left the on-disk labels_unified.parquet on the WRONG id convention (MOE_/ON_/S0002…
_datetime, none joinable to the S0001 segment/feature tables) and dropped its eeg_datetime column, which broke
scripts/95 and scripts/120. The manifest (report_manifest_v6.parquet) carries the correct S0001/S0002 patient
ids + eeg_datetime + every report-derived label, so we regenerate labels_unified from it.

SCOPE (MBW, 2026-07-19): the MAIN clinical cohort only — `panel_set == 'none'` — which EXCLUDES the MoE and
OccasionNoise panels. SB100/SAI-100 is external validation with expert-vote labels (its own pipeline) and is
correctly not here. One row per recording; bdsp_id == patient_id (convention A); eeg_datetime distinguishes a
patient's recordings. gen_class is derived exactly as fleet_analysis_adapter does (coarse; the SAP-faithful
pathologic/physiologic split lives in recording_labels_sap.parquet).

Run: PYTHONPATH=src python3 scripts/rebuild_labels_unified.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

MAN = Path("data/manifest/report_manifest_v6.parquet")
OUT = Path("data/derived/labels_unified.parquet")
AGES = Path("metadata/ages_v6.parquet")
LABEL_COLS = ["is_normal", "is_abnormal", "has_focal_slow", "has_gen_slow", "clean_normal",
              "focal_side", "focal_region", "focal_band", "gen_topography", "gen_band",
              "clean_pair", "age", "sex"]


def main():
    man = pd.read_parquet(MAN)
    main = man[man.panel_set == "none"].copy()                       # main cohort only (no MoE / OccasionNoise)
    # AGE: the manifest's own `age` is a WHOLE NUMBER of years and partly wrong (median 0.31 y off vs the
    # authoritative table, >1 y for 4.3% of recordings, up to 14 y). metadata/ages_v6.parquet is the
    # OMOP-derived source of record, and copying the manifest column here is what made labels_unified 100%
    # integer -- the exact revert tests/test_ages.py exists to catch. Override per recording.
    _ag = pd.read_parquet(AGES)[["eeg_id", "age"]].drop_duplicates("eeg_id")
    if "eeg_id" in main.columns:
        main = main.merge(_ag.rename(columns={"age": "_age_v6"}), on="eeg_id", how="left")
        # Fall back to the manifest only where ages_v6 has no row -- and BIN THE FALLBACK: the de-identified
        # OMOP export returns ages up to 121 and the manifest carries 217 of them un-binned, so an unguarded
        # fallback reintroduces a HIPAA Safe Harbor violation (ages over 89 are identifiers). ages_v6 already
        # bins; the fallback must too.
        _fb = main["age"].clip(upper=90)
        main["age"] = main["_age_v6"].where(main["_age_v6"].notna(), _fb)
    lu = pd.DataFrame({"bdsp_id": main.patient_id.astype(str),        # convention A: bdsp_id == patient_id (S0001/S0002)
                       "patient_id": main.patient_id.astype(str),
                       "eeg_datetime": main.eeg_datetime.astype(str)})  # the column the reorg had dropped
    for c in LABEL_COLS:
        lu[c] = main[c].values
    gs, ab = lu.has_gen_slow == True, lu.is_abnormal == True          # noqa: E712
    lu["gen_class"] = np.where(gs & ab, "pathologic", np.where(gs & ~ab, "physiologic", "none"))
    lu["age_source"] = np.where(lu.age % 1 != 0, "ages_v6", "manifest")

    if OUT.exists():                                                  # keep the broken file for reference (gitignored)
        bak = OUT.with_suffix(".pre_rebuild.parquet")
        if not bak.exists():
            OUT.rename(bak); print(f"backed up old (broken) file -> {bak}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lu.to_parquet(OUT, index=False)
    print(f"wrote {OUT}: {len(lu)} recordings, {lu.bdsp_id.nunique()} patients")
    print(f"  id prefixes: {dict((p, int(lu.bdsp_id.str.startswith(p).sum())) for p in ['S0001','S0002','MOE','ON'])}")
    print(f"  clean_normal={int((lu.clean_normal==True).sum())}, abnormal={int((lu.is_abnormal==True).sum())}, "
          f"gen pathologic={int((lu.gen_class=='pathologic').sum())}")


if __name__ == "__main__":
    main()
