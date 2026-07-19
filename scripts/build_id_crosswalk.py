"""Build data/derived/id_crosswalk.parquet — the single traceability spine linking the two id conventions.

The derived tables use two keys for the same recordings:
  * convention A  patient_id  (per-patient, e.g. S0001111192519)      -> segment_features, labels_unified
  * convention B  eeg_id      (per-recording, patient_id + _datetime)  -> channel_stage_features (growth curves)
Both are columns of the manifest, and B -> A is just dropping the trailing _<datetime>. This table makes the
A<->B mapping explicit and carries the provenance needed to trace ANY feature back to its EEG file and report:
one row per recording with eeg_id, patient_id, eeg_datetime, panel membership, the EEG file location, the
report note name, and the report<->EEG pairing flag.

Run: PYTHONPATH=src python3 scripts/build_id_crosswalk.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

MAN = Path("data/manifest/report_manifest_v6.parquet")
OUT = Path("data/derived/id_crosswalk.parquet")


def main():
    man = pd.read_parquet(MAN)
    file_col = "bucket_key" if "bucket_key" in man.columns else "eeg_path"
    xw = pd.DataFrame({
        "eeg_id": man.eeg_id.astype(str),                 # convention B (per-recording; = channel_stage_features.bdsp_id)
        "patient_id": man.patient_id.astype(str),         # convention A (per-patient; = segment_features.bdsp_id)
        "eeg_datetime": man.eeg_datetime.astype(str),
        "panel_set": man.get("panel_set", "none"),        # none / moe / occasionnoise
        "eeg_file": man[file_col].astype(str),            # where the EDF lives
        "report_note_name": man.get("report_note_name", ""),
        "clean_pair": man.get("clean_pair", False),
    }).drop_duplicates("eeg_id")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    xw.to_parquet(OUT, index=False)
    print(f"wrote {OUT}: {len(xw)} recordings, {xw.patient_id.nunique()} patients")
    print(f"  panel_set: {xw.panel_set.astype(str).value_counts().to_dict()}")
    print("  A<->B check: eeg_id.rsplit('_',1)[0] == patient_id for",
          int((xw.eeg_id.str.rsplit('_', n=1).str[0] == xw.patient_id).sum()), "/", len(xw), "rows")


if __name__ == "__main__":
    main()
