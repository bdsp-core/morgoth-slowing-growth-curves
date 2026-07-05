# Full-dataset re-analysis — status (2026-07-05)

After the fleet processed the full cohort, `fleet/reanalyze.sh` rebuilt the derived tables from the S3
outputs (streaming adapter `scripts/51_expansion_to_derived.py`, 24-way parallel) and re-ran the analyses.
Dashboard: `results/analysis_dashboard.html` (published artifact).

## Data scale (was pilot ~7.5k → now full)
- `recording_features(_py).parquet` — **12,027 recordings**, 297,096 region-rows
- `gate_probs.parquet` — 12,027 · `recording_asymmetry.parquet` — 12,027 · `stage_recording_features.parquet` — per (rec,region,stage)
- Fleet: 12,980/13,034 have `.done`; ~953 are noedf/too-short (marked done, no features); **54 permanent-fail** bad EDFs (`results/fleet_failed_recordings.csv`).

## Regenerated on FULL data ✅ (59 fresh figures)
growth curves (04), discrimination / adjusted-z (06), age-AUROC (33), van Putten comparison main fig (47),
BSI growth curves (48), lateralization (40/41/44), region detection (46), stage curves (10), LR-vs-Morgoth
(17: our-LR AUC 0.962 vs Morgoth 0.921/0.936 on n=12,379).

## Known gaps to finish (need a human call — not auto-fixed to avoid fabricating numbers)
1. **`bsi_z` not built.** `48_bsi_growth.py` saves only `bsi` (raw) to `bsi_features.parquet`, not the
   age/sex-normalized `bsi_z`. Consumers `16_gated_report.py` (failed) and the "BSI deviation" row in
   `47_vanputten_comparison.py` need it. **Fix:** add the intended age-conditioned normalization
   (percentile/z vs age-matched normals, same convention as the other deviation features) to 48, re-save
   `bsi_features` with `bsi_z`, then rerun 48→47→16 and rebuild the dashboard.
2. **Report-label panels at pilot coverage.** Lateralization side / region / report-agreement
   (40/41/42/43/44/46/18) depend on `results/report_extracted_labels.csv`, which comes from free-text EEG
   reports on Box (`scripts/20_extract_report_labels.py`), NOT the fleet. To extend to the full cohort,
   run script 20 per site (S0001, S0002, I000x) against each site's `EEGs_And_Reports.csv`.
3. **`50_severity_prevalence.py` skipped** — hard-codes a session-local reports CSV path (line ~16).
   Parametrize it, then rerun.
4. **7 stale figures** (`region_confusion*`, `side_confusion*`, `region_f1`, `severity_prevalence`) — the
   deprecated 3-way confusion matrices (superseded by the gated ROC panels) + severity; not regenerated.
5. **Hard-coded dashboard captions** in `build_analysis_dashboard.py` still cite some pilot numbers in prose
   (figures are full-data-correct); update the caption strings to match.

## Rerun command
```bash
bash fleet/reanalyze.sh            # streams full data from S3, rebuilds tables + analyses + dashboard
# derived *.parquet are gitignored (regenerable); the published dashboard artifact is self-contained.
```
