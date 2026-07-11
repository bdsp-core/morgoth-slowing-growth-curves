# Archive — superseded pre-clean-room material

Retained for **provenance only**. The canonical spec is [../analysis_plan.md](../analysis_plan.md) (the SAP)
and its companions. **Nothing here is an input to the clean-room run.** Several files are cited in
`DATA_INVENTORY.md` / `methods_audit.md` as the provenance of established findings, which is why this is a
`git mv` archive (history preserved), not a deletion.

## Why these were superseded (the canonical facts that made them stale)

theta = **4–8 Hz** (not 4–7); coverage = **up to first 24 h** (not first 600 s); recording key =
**`eeg_id`** (not patient-level `bdsp_id`); norms **stage-conditioned & sex-pooled**; **zero reuse** of
prior derived tables; artifact segments **flagged, not stripped**; severity adjectives / ACNS frequency
words / band-from-our-features are **FORBIDDEN** output.

## Docs

| File | Superseded by |
|---|---|
| `feature_spec.md` | `analysis_plan.md` §4 + `data_dictionary.md` (had θ 4–7 + a forbidden severity ladder) |
| `report_architecture.md` | `description_architecture.md` + `claims_table.md` (had severity/frequency words) |
| `artifact_rejection_plan.md` | `analysis_plan.md` §4.3 (stripped segments → now flag, not strip) |
| `repro_data.md` | `analysis_plan.md` §12–13 (rebuild-from-derived → zero-reuse clean run) |
| `feature_extraction.md`, `paper_outline.md` | `data_dictionary.md`, `manuscript_draft.md` |
| `normative_deviation_plan.md`, `label_cleanup_plan.md`, `label_quality_plan.md`, `localization_improvement_plan.md`, `staging_and_localization_plan.md`, `coverage_expansion_plan.md`, `coverage_by_stage.md` | folded into `analysis_plan.md` |
| `phase0_findings.md`, `reanalysis_status.md`, `status_2026-07-06.md`, `n3_expansion_plan.md`, `table1.md`, `table1_live.md` | historical status logs |
| `PLAN.md`, `EXECUTION_PLAN.md`, `AUTONOMOUS_STATUS.md` (from repo root) | `analysis_plan.md` |

## Scripts (`../../scripts/archive/`)

78 legacy scripts: the old `bdsp_id`-keyed, first-600 s, reuse-based pipeline (Phase 0→E features/curves,
old eval/validation/localization, label injection, the uniform/union table builders, settled sex one-offs,
superseded utils/dashboards). Includes the now-refactored `18_report_agreement.py` and
`26_slowing_ingest_pilot.py` (their reused logic was lifted into `src/morgoth_slowing/report/parse.py` and
`src/morgoth_slowing/fleet/ingest.py`).
