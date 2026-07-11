"""Assemble the run ledger — ONE row per intended manifest EEG — AFTER all fleet shards finish (B5).

Shard-safe by construction: the worker writes only per-eeg_id sidecars (segment_master/_done/<id>.done on
success, _status/<id>.status otherwise); this pass reads them ONCE, globally, and joins the manifest. No
worker rewrites a global parquet, so concurrent shards never clobber (the old bug).

Emits (under OUTPUT_ROOT):
  recording_meta.parquet   — one row per manifest eeg_id: provenance (source_edf, sha256, resolve_reason),
                             stats (recording_seconds, n_segments, n_usable, frac_artifact, stage fractions,
                             p_slowing coverage), EEG-level gate (p_focal/p_generalized), and the outcome
                             (processed / included / exclusion_reason / error_reason). This is the auditable
                             "single file" view.
  recording_labels.parquet — one row per eeg_id: report/panel labels for label-dependent analyses.

Usability (SAP §3.2): included = processed AND recording_seconds >= MIN and n_usable >= MIN and
usable_fraction >= MIN. Rows that resolve+featurize but fail usability are flagged (not silently kept),
so a top-up pass can hold N (see scripts/130).

Run: OUTPUT_ROOT=/data/run PYTHONPATH=src python scripts/33_assemble_ledger.py [--manifest ...v6.parquet]
"""
from __future__ import annotations
import argparse, os, json
from pathlib import Path
import pandas as pd

OUTROOT = Path(os.environ.get("OUTPUT_ROOT", "data/derived"))
DONE = OUTROOT / "segment_master" / "_done"
STATUS = OUTROOT / "segment_master" / "_status"
MIN_MINUTES = float(os.environ.get("MIN_MINUTES", "5"))
MIN_USABLE_SEGMENTS = int(os.environ.get("MIN_USABLE_SEGMENTS", "20"))
MIN_USABLE_FRACTION = float(os.environ.get("MIN_USABLE_FRACTION", "0.20"))

LABELS = ["eeg_id", "is_abnormal", "has_focal_slow", "has_gen_slow", "clean_normal", "focal_side",
          "focal_region", "focal_band", "gen_topography", "gen_band", "clean_pair", "panel_set", "occasion_category"]
META_KEEP = ["eeg_id", "patient_id", "src", "panel", "panel_set", "source_type", "age", "sex", "bids_task"]


def _load_dir(d, pattern="*", key="eeg_id"):
    """Read every per-eeg JSON sidecar in a dir (.done / .status) into a DataFrame."""
    rows = []
    for p in Path(d).glob(pattern):
        if p.is_dir():
            continue
        try:
            rows.append(json.loads(p.read_text()))
        except Exception:
            pass
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[key])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/manifest/report_manifest_v6.parquet")
    ap.add_argument("--preflight", default="data/manifest/preflight_resolution.parquet")
    a = ap.parse_args()
    man = pd.read_parquet(a.manifest if Path(a.manifest).exists()
                          else "data/manifest/report_manifest_v5.parquet")
    done = _load_dir(DONE, "*.done")          # success stats (rich .done payload)
    stat = _load_dir(STATUS, "*.status")      # non-success outcomes
    pre = pd.read_parquet(a.preflight) if Path(a.preflight).exists() else pd.DataFrame(columns=["eeg_id"])

    led = man[[c for c in META_KEEP if c in man.columns]].copy()
    led["processed"] = led.eeg_id.isin(done.eeg_id) if len(done) else False
    if len(done):
        led = led.merge(done, on="eeg_id", how="left", suffixes=("", "_done"))
    for col in ["status"]:
        if len(stat):
            led = led.merge(stat[["eeg_id", "status"]], on="eeg_id", how="left")
        elif col not in led:
            led[col] = pd.NA
    if len(pre):
        led = led.merge(pre[["eeg_id", "resolved", "resolve_reason"]].rename(
            columns={"resolve_reason": "preflight_reason"}), on="eeg_id", how="left")

    # usability (SAP §3.2) + outcome
    secs = pd.to_numeric(led.get("recording_seconds"), errors="coerce")
    nusable = pd.to_numeric(led.get("n_segments"), errors="coerce") - pd.to_numeric(led.get("n_artifact"), errors="coerce")
    frac = 1 - pd.to_numeric(led.get("frac_artifact"), errors="coerce")
    led["n_usable"] = nusable
    led["usable_fraction"] = frac
    usable = (secs >= MIN_MINUTES * 60) & (nusable >= MIN_USABLE_SEGMENTS) & (frac >= MIN_USABLE_FRACTION)
    led["included"] = led["processed"] & usable.fillna(False)

    def _reason(r):
        if r["processed"]:
            return "included" if r["included"] else "unusable:short_or_artifact"
        s = r.get("status")
        if isinstance(s, str):
            return s                                          # noedf / ambiguous / nopanelfile / error:*
        return "not_processed"
    led["exclusion_reason"] = led.apply(lambda r: (None if r["included"] else _reason(r)), axis=1)

    led.to_parquet(OUTROOT / "recording_meta.parquet", index=False)
    man[[c for c in LABELS if c in man.columns]].to_parquet(OUTROOT / "recording_labels.parquet", index=False)

    n = len(led)
    print(f"ledger: {n} intended EEGs -> {OUTROOT/'recording_meta.parquet'}")
    print(f"  processed {int(led.processed.sum())} | included {int(led.included.sum())} "
          f"| excluded {int((~led.included).sum())}")
    print("  exclusion reasons:", dict(led[~led.included].exclusion_reason.value_counts().head(10)))


if __name__ == "__main__":
    main()
