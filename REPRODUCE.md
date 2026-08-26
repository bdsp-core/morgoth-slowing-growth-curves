# Reproduce every figure, table, and number

Everything is driven by one script, [`scripts/reproduce_story.sh`](scripts/reproduce_story.sh), in three
tiers (pick by how much you want to rebuild):

**Prerequisites.** Python 3.12+, and — for the `features` and `scratch` tiers — **R with the `gamlss`
package** (the normative curves in `scripts/115` and `76` are fitted in R; these are the steps marked `[R]`
below) and **pandoc** (only for `scripts/build_manuscript_docx.py`). On macOS:

```bash
brew install r pandoc
Rscript -e 'install.packages("gamlss", repos="https://cloud.r-project.org")'
```

```bash
pip install -e .                                   # or: pip install -r requirements.txt
bash scripts/reproduce_story.sh results            # FAST  — figures/tables from the derived tables
bash scripts/reproduce_story.sh features           # ~1 h  — rebuild norms/deviation/descriptors + train, then results
bash scripts/reproduce_story.sh scratch            # ~24 h — from raw EDFs on the GPU fleet, then everything
```

## Data access (before the `results`/`features` tiers)

**How much you actually need depends on the tier.** A figure-loop install is **~1.9 GB**, not 71 GB: the
flat parquets, the norm grids, the report manifest, `figure_cache/` and ~90 MB of panel partitions (ON-100
and SAI-100). That regenerates **all 17** stage-4 producers — every figure and every table — and does so
**bit-identically** to a full install. That equivalence is tested, not asserted: hiding all 71 GB and
re-running produces byte-identical result files.

`figure_cache/` holds three distillations, each a faithful substitute rather than a sample:

| file | replaces | size |
|---|---|---|
| `wholehead_z.parquet` | the six whole-head columns of `segment_deviation/` (6.5 GB), all Figures S2/S6 read | 367 MB |
| `segfeats_all.parquet` | per-segment model features for every recording, re-derived from `segment_master` | 88 MB |
| `focal_channel_feats.parquet` | the per-recording output of the segment × channel pivot in `scripts/64` | 2.4 MB |

Rebuild them on a full install with `scripts/83`, `85` and `84` after any change to the deviation field or
the feature extractor.

**When the caches are present they DEFINE which recordings are eligible**, rather than being topped up from
`segment_master`. That is deliberate: eligibility used to be `os.path.exists()` on the big table, which
included a few hundred recordings that then yielded no usable features, so a full install and a figure-loop
install trained the focal detector on different sets and produced different numbers from identical code. The
cache is the canonical, portable definition; `segment_master` is only the fallback when it is absent.

The cache is a faithful substitute, not a sample: it carries every segment for the six whole-head deviation
features, which is all the `results` tier reads out of the per-segment field, and both figures that use it
(S5 and S6) come out bit-identical either way. Rebuild it with `scripts/83_build_figure_cache.py` after any
change to the deviation field.

```bash
# figure loop (~1.9 GB) -- rebuilds ALL 17 producers, bit-identically to a full install
aws s3 sync s3://bdsp-opendata-credentialed/morgoth-slowing/derived/ data/derived/ --exclude "*/*"
aws s3 sync s3://bdsp-opendata-credentialed/morgoth-slowing/derived/figure_cache/ data/derived/figure_cache/
# the spindle sub-study checkpoint: the top-level sync above uses --exclude "*/*" and would skip it, and
# scripts/95 needs it to write the SS3.8 verdict. Without it 95 reports "SPINDLE TEST NOT RUN".
aws s3 sync s3://bdsp-opendata-credentialed/morgoth-slowing/derived/v4a_work/ data/derived/v4a_work/
aws s3 cp   s3://bdsp-opendata-credentialed/morgoth-slowing/manifest/report_manifest_v6.parquet data/manifest/
# panel partitions (~90 MB) for the ON-100 / SAI-100 figures
for p in segment_master segment_summary; do
  aws s3 sync s3://bdsp-opendata-credentialed/morgoth-slowing/derived/$p/ data/derived/$p/ \
      --exclude "*" --include "eeg_id=ON_*" --include "eeg_id=SB_*"
done
aws s3 sync s3://bdsp-opendata-credentialed/morgoth-slowing/derived/segment_master/_done/ \
    data/derived/segment_master/_done/ --exclude "*" --include "ON_*.done"
```

`scripts/preflight_reproduce.py` detects which tier you have and checks only what that tier needs; it still
fails loudly on a table that is present but INCOMPLETE, which is the failure mode that silently changed
Table S2 during this revision.

For the `features` and `scratch` tiers you also need the big partitioned tables (needs bdsp.io credentialed
access + a DUA — see [`DATA_SOURCE.md`](DATA_SOURCE.md)):

```bash
export AWS_PROFILE=<your-bdsp-profile>   # a profile with read access to s3://bdsp-opendata-credentialed
                                         # (verify with: aws s3 ls s3://bdsp-opendata-credentialed/morgoth-slowing/)
aws s3 sync s3://bdsp-opendata-credentialed/morgoth-slowing/derived/ data/derived/
aws s3 sync s3://bdsp-opendata-credentialed/morgoth-slowing/panels/  data/derived/   # ON-100 panel inputs
aws s3 cp   s3://bdsp-opendata-credentialed/morgoth-slowing/manifest/report_manifest_v6.parquet data/manifest/   # report-recording pairing (de-identified report text; DUA-governed, not committed)
```

The small **proximal artifacts** each figure/table also needs (report manifest, result CSVs/MD, norm
grids small enough to commit) are already in the repo under `data/`, `results/`, and `figures/`.

## The contract — paper item → script → input → output

Figures are assembled into the submission set by
[`scripts/assemble_manuscript_figures.py`](scripts/assemble_manuscript_figures.py)
(→ `figures/manuscript/Figure*.png` + `.pdf`). Panel producers and their inputs:

| Paper item | Producing script(s) | Key input (derived / proximal) | Output |
|---|---|---|---|
| **Figure 1** normative model | `76_keystone_growth_grid.py`, `77_topoplots_by_age.py` | `grid_norm.json`, `segment_deviation/` | `figures/growth_v2/{keystone_growth_grid,topo_rel_delta_by_age_stage}.png` |
| **Figure 2** detection (gen + focal) | `54_single_model_train_eval.py`, `55_recording_model.py` | `single_model_segfeats.parquet` | `figures/story/{s0d_single_occasion_generalized,s0e_occasion_focal}.png` |
| **Figure 3** SAI-100 external | `sandor100_external_validation.py` | SAI-100 set + `segment_master/eeg_id=SB_*` | `figures/story/sandor100_slowing.png` |
| **Figure 4** example focal | `62_example_reports_panel.py`, `63_example_eeg_traces.py` | `description_recording.parquet`, `data/manifest/report_manifest_v6.parquet`, source EDFs (S3) | `figures/story/s4_examples_eeg_focal.png` |
| **Figure 5** example generalized | `62_example_reports_panel.py`, `63_example_eeg_traces.py` | `description_recording.parquet`, `data/manifest/report_manifest_v6.parquet`, source EDFs (S3) | `figures/story/s4_examples_eeg_generalized.png` |
| **Figure 6** description contrast | `57_description_panels.py` | `description_recording.parquet`, `description_stage.parquet` | `figures/story/{s4_d2,s4_d5}.png` |
| **Figure 7** sleep under-reporting | `fig6_sleep_naming.py` (stat: `95b_v4a_spindle_check.py`) | `description_stage.parquet`, `results/p6_sleep_underreporting.md` | `figures/growth_v2/v4a_wake_sleep.png` |
| **Figure S1** architecture | `architecture_diagram.py` | — | `figures/story/architecture.png` |
| **Figure S2** held-out centile calibration | `78_centile_calibration.py` | `grid_norm.json`, `figure_cache/wholehead_z.parquet`, `panel_v6_scores.parquet` | `figures/story/s9_centile_calibration.png`, `results/story/centile_calibration.md` |
| **Figure S3** van Putten benchmark | `vanputten_panel_s7.py` | `occasion_features.parquet`, gate tables | `figures/figs/vanputten_panel_s7.png` |
| **Figure S4** topoplot (TAR) | `77_topoplots_by_age.py` | `segment_deviation/` | `figures/growth_v2/topo_TAR_by_age_stage.png` |
| **Figure S5** curve bank | `111_curve_bank_v6.py` | `grid_norm.json` | `figures/stage_curves/*__whole_head.png` |
| **Figure S6** deviation field | `44_segment_deviation_summary.py` | `figure_cache/wholehead_z.parquet` | `figures/story/s2_segment_deviation.png` |
| **Figure S7** localized focal | `49_occasion_allstage_localized.py` | `occasion_features.parquet` | `figures/story/s0_occasion_ours_v4_focal.png` |
| **Figure S8** description panels (D1–D6) | `57_description_panels.py`, `58_description_words.py` | `description_recording.parquet` | `figures/story/s4_d{1,3,4,6}.png` |
| **Figure S9** severity null | `109_severity_null_v6.py` | `occasion_features.parquet` | `figures/growth_v2/severity_recalibrated.png` |
| **Table 1** cohort | `table1_sap.py` | `labels_unified.parquet`, manifest | `results/table1.md` |
| **Table S1** van Putten full-coverage | `recompute_vanputten_fullcov.py` | `occasion_features.parquet` | `results/vanputten_fullcoverage.md` |
| **Table S2** human ceiling | `recompute_human_ceiling_v6.py` | ON-100 panel votes | `results/table5_human_ceiling.md` |
| **Table S3** band (δ/θ/mixed) calibration | `band_calibration.py` | `description_recording.parquet` (`band_dtr`) | `results/story/band_calibration.md` |

## Key quoted numbers → where they come from

| Number (paper) | Script | Source artifact |
|---|---|---|
| Detection AUROC (focal 0.908 / gen 0.961) | `54`, `55` | `figure_cache/segfeats_all.parquet` + `focal_channel_feats.parquet` → `results/story/*` |
| ON-100 experts-under-curve; human ceiling κ | `recompute_human_ceiling_v6.py` | ON-100 panel votes (`panels/`) |
| Band δ-vs-θ AUROC 0.74 (vs 0.68 deviation); κ≈0.10 | `band_calibration.py` | `description_recording.parquet` |
| Component concordance (side 56% / region 46% / band 52%) | `58_description_words.py` | `description_recording.parquet` + report labels |
| Sleep under-reporting naming rates; spindle-verified AUROC | `95b_v4a_spindle_check.py` | `description_stage.parquet` + source EDFs |
| Severity null (ρ≈0.05; 168-combination sweep) | `109_severity_null_v6.py` | `occasion_features.parquet` |
| Slow-frequency null (ρ = 0.13 all-seg, 0.04 abnormal-only) | `81_slow_peak_frequency.py` | `report_manifest_v6.parquet` + source EDFs (S3) |

### Known issue: scripts/95 reads age from the manifest, not `metadata/ages_v6.parquet`

`metadata/ages_v6.parquet` is the authoritative age table (OMOP `birth_datetime`, 99.6% exact, >89 binned to
90 for HIPAA Safe Harbor). `fleet_analysis_adapter.py` and `34_recording_meta_from_segments.py` read it;
`scripts/95` still takes `age` from `report_manifest_v6.parquet`, whose `age` is a whole number of years and
partly wrong. Measured against ages_v6 over the 25,654 recordings both cover: median discrepancy **0.31 y**,
**4.3% differ by more than a year**, maximum **14 y**. The manifest also carries **217 un-binned ages above
90** (max 121); §3.8's one-row-per-patient selection picks up 194 of them, which `scripts/95`'s
`age.between(0, 100)` filter admits rather than bins.

The fix was written and measured, then deliberately **not applied**, because applying it half-way is worse
than not applying it: `95` is a stage-4 producer, so changing its ages changes committed results, and the
§3.8 headline numbers come from `95b`, which needs credentialed EDF access to re-run. Fixing `95` without
re-running `95b` would leave the repo producing numbers the paper does not quote.

**Measured impact, so the decision is on the record rather than assumed.** With ages_v6 substituted, every
AUROC `95` produces moves by ≤0.001 (log_delta 0.779 → 0.779, DAR 0.777 → 0.777, TAR 0.689 → 0.688,
low_freq_rel 0.522 → 0.521) and the case count by one (338 → 339). Nothing the manuscript quotes changes at
the precision it is quoted to.

**To close it properly**, run as one unit on a machine with EDF access: patch `95` to prefer ages_v6 (binning
any manifest fallback to 90), re-run `95` → `95b`, then update §3.8 from the regenerated
`results/v4a_wake_sleep.md`. `tests/test_ages.py` guards the derived tables; the same override has already
been applied to `rebuild_labels_unified.py`, which is why `labels_unified.parquet` is now 98.6% fractional.

Numbers that require the **raw EEG or model training** to regenerate (not just the committed CSVs) are
produced by the `features`/`scratch` tiers and are marked in `reproduce_story.sh`; every other number
regenerates from the derived tables in the `results` tier.

## How the runner works

The runner executes numbered stages (0 canonical tables · 1 norms + deviation field · 2 panel inputs
[Morgoth] · 3 descriptors + model features · 4 figures/tables/models · 5 dashboard + manuscript figure set);
the tier just sets the starting stage (`results`→4, `features`→0, `scratch`→fleet then 0). Each step is
**skipped when its output already exists** — `FORCE=1` rebuilds regardless, `SKIP_PANEL=1` skips the
Morgoth-dependent panel step. Steps needing R (`115`, `76`) are marked `[R]`. `scratch` is a sharded,
multi-host S3 job, not a laptop run; the runner prints the fleet command and, if `segment_master/` is present
locally, continues from `features`.

## Known reproducibility note

`results/story/s0c_morgoth_free.md` (the in-domain focal/generalized trajectory in dashboard block 2b) is a
hand-authored summary of the design search, not a script-generated artifact. Everything else is produced by
the stages above.
