# Run manifest index — the tracked reproducibility anchor

The manifest artifacts themselves live under `data/` and are **gitignored** (PHI-adjacent + large). This
file IS tracked, so a code tag + this index reconstructs the exact starting point of a run. Regenerate the
artifacts with the pinned code (below) and check the sha256 matches.

## LAUNCH manifest — `report_manifest_v6.parquet` (frozen 2026-07-11T17:59Z)

| field | value |
|---|---|
| **sha256** | `8ac7a552d5144e1cc424f74d512d4c3a0c23cb13ce875f8710dc2b65ae912b4d` |
| n_v6 | **27,524** (`held_N: true`; = v5) |
| composition | cohort 10,977 · expansion 10,233 · backfill 2,535 · replacement 1,918 · panel 1,861 |
| invariants | `held_N:true` · `every_bids_row_resolved:true` · `replacements_analysis_ready:true` · `replacement_age_null:0` |
| meta.json | `data/manifest/report_manifest_v6.meta.json` (full record + sha256) |

**Input artifacts (also gitignored) with sha256 prefixes:**
- `report_manifest_v5.parquet` (pre-resolution) — `1a46410e8ec13d39…`
- `preflight_resolution.parquet` (scripts/129 output) — `820bfe8c713aaf2e…`
- `manifest_rejects.parquet` (the 1,918 dropped, with reasons) — `ce3b6c80a32fb481…`

## How to reconstruct v6 exactly
```bash
# from v5 + the pre-flight resolution (both regenerable from the pinned code):
PYTHONPATH=src python scripts/129_preflight_resolve.py --manifest data/manifest/report_manifest_v5.parquet
PYTHONPATH=src python scripts/130_finalize_v6.py        # exits nonzero unless held_N + analysis-ready + all-resolved
# verify:
python -c "import json;m=json.load(open('data/manifest/report_manifest_v6.meta.json'));print(m['sha256'],m['held_N'])"
```
`scripts/130` is deterministic (seeded pool sample) and **fails hard** (exit 1) if any launch invariant is
violated, so a bad manifest can never silently reach the fleet.

## Run-control code (tag this together with the manifest freeze)
Pre-flight/finalize: `scripts/129`, `scripts/130`. Fleet: `scripts/31` (worker), `scripts/33` (ledger),
`scripts/32` (verify). Panels: `scripts/127`, `scripts/128`. Canonical access: `src/morgoth_slowing/io/canonical.py`.
Suggested tag: `git tag run-v6` after committing these.

## S3 location
- BDSP recordings: streamed from `s3:bdsp-opendata-repository/EEG/bids/` (open-data, not copied).
- **Panel sources: `s3://bdsp-opendata-credentialed/morgoth-slowing/panels/`** (occasionnoise/*.edf +
  moe/*.mat; uploaded 2026-07-11; set `PANEL_ROOT` to this). Credentialed bucket — needs BDSP write/read keys.
- Run outputs: `s3://<run-output-bucket>/` (segment_master/summary + ledger; fleet_launch §1b) — TBD at run time.
