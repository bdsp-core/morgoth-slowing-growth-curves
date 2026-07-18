#!/usr/bin/env bash
# =============================================================================
# reproduce_story.sh — ONE script to regenerate every result in the paper
# (models, figures, tables, dashboard) from the derived feature tables.
#
# The heavy upstream steps — fleet/S3 feature extraction (segment_master/,
# segment_summary/), the Morgoth gate rerun (gate_rerun_done/), and the raw
# human panel votes (occasion_expert_votes.parquet) — are ASSUMED DONE and
# present under data/derived/. This script rebuilds everything downstream of
# them, in dependency order, on a local CPU.
#
# PREREQUISITES
#   - Python analysis env active; run from the repo root.
#   - R with the `gamlss` package (for the two GAMLSS steps, marked [R]).
#   - data/derived/ populated with the fleet/Morgoth outputs listed above.
#
# USAGE
#   bash scripts/reproduce_story.sh              # run all stages, skipping any
#                                                # whose outputs already exist
#   FORCE=1 bash scripts/reproduce_story.sh      # rebuild everything
#   FROM=4  bash scripts/reproduce_story.sh      # start at stage 4 (figures)
#   SKIP_PANEL=1 bash scripts/reproduce_story.sh # skip stage 2 (needs Morgoth)
#
# Each step prints a header; a step is skipped (unless FORCE=1) when its
# sentinel output is already present. Stages: 0 canonical tables, 1 norms +
# deviation field, 2 panel inputs (Morgoth), 3 description + model substrates,
# 4 figures/tables/models, 5 dashboard.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-src}"
export MPLBACKEND=Agg
FORCE="${FORCE:-0}"; FROM="${FROM:-0}"; SKIP_PANEL="${SKIP_PANEL:-0}"

hdr() { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
# run <stage_no> <sentinel_path> <description> -- <command...>
run() {
  local stage="$1" sentinel="$2" desc="$3"; shift 3; [ "$1" = "--" ] && shift
  if [ "$stage" -lt "$FROM" ]; then echo "  [skip stage<$FROM] $desc"; return; fi
  if [ "$FORCE" != "1" ] && [ -e "$sentinel" ]; then echo "  [have] $desc  ($sentinel)"; return; fi
  echo "  [run ] $desc"; "$@"
}
py() { python3 "$@"; }

# ---------------------------------------------------------------------------
hdr "STAGE 0 — canonical tables + corrected labels  (local; scans segment_master)"
run 0 data/derived/recording_meta.parquet     "recording_meta + recording_labels (34)"          -- py scripts/34_recording_meta_from_segments.py
run 0 data/derived/recording_labels_sap.parquet "corrected SAP labels (label_rederive_sap)"      -- py scripts/label_rederive_sap.py
run 0 data/derived/channel_stage_features.parquet "channel_stage_features + labels_unified (adapter)" -- py scripts/fleet_analysis_adapter.py
# fix_ages_fractional patches the two tables above in place (no unique output); guarded by labels_unified
# so it is skipped once stage 0 has completed. Force a re-patch with FORCE=1.
run 0 data/derived/labels_unified.parquet      "patch fractional ages (fix_ages_fractional)"      -- py scripts/fix_ages_fractional.py

hdr "STAGE 1 — normative curves + per-segment deviation field  ([R] = needs gamlss)"
run 1 data/derived/grid_norm.json              "[R] GAMLSS norm grids (115_descriptor_grid)"     -- py scripts/115_descriptor_grid.py
run 1 data/derived/segment_deviation           "per-segment deviation field (43_segment_deviation)" -- py scripts/43_segment_deviation.py
run 1 data/derived/gate_eeg_level_rerun.parquet "assemble Morgoth gate rerun (36_build_gate)"     -- py scripts/36_build_gate_from_rerun.py

hdr "STAGE 2 — expert-panel inputs  (needs Morgoth + fleet ON_ partitions; SKIP_PANEL=1 to skip)"
if [ "$SKIP_PANEL" = "1" ]; then echo "  [skip] SKIP_PANEL=1"; else
  run 2 data/derived/occasion_features.parquet "panel features + Morgoth preds (107_rebuild)"     -- py scripts/107_rebuild_panel_inputs_v6.py
fi

hdr "STAGE 3 — description + single-model substrates  (local)"
run 3 data/derived/description_recording.parquet "description descriptors (56)"                   -- py scripts/56_description_descriptors.py
run 3 data/derived/single_model_segfeats.parquet "single-model segment features (53)"             -- py scripts/53_single_model_features.py

hdr "STAGE 4 — figures, tables, models  (local; [R] = needs gamlss)"
# -- Figure 1: the normative deviation model (foundation)
run 4 figures/growth_v2/keystone_growth_grid.png "[R] Fig 1a growth curves (76)"                  -- py scripts/76_keystone_growth_grid.py
run 4 figures/story/s2_segment_deviation.png   "Fig 1b deviation field (44)"                      -- py scripts/44_segment_deviation_summary.py
run 4 figures/growth_v2/topo_rel_delta_by_age_stage.png "Fig 1c topoplots (77)"                   -- py scripts/77_topoplots_by_age.py
run 4 figures/stage_curves/rel_delta__whole_head.png "Fig 1d curve bank (111)"                    -- py scripts/111_curve_bank_v6.py
# -- Figure 2: detection (Morgoth-free model)
run 4 figures/story/s0d_single_occasion_generalized.png "Fig 2a generalized head (54)"            -- py scripts/54_single_model_train_eval.py
run 4 figures/story/s0e_occasion_focal.png     "Fig 2a focal head (55)"                           -- py scripts/55_recording_model.py
run 4 figures/story/s0_occasion_ours_v4_focal.png "Fig 2b localized focal (49)"                   -- py scripts/49_occasion_allstage_localized.py
# -- Figure 3 / Table 2: van Putten benchmark
run 4 results/vanputten_fullcoverage.md        "Fig 3 / Table 2 van Putten benchmark (recompute)" -- py scripts/recompute_vanputten_fullcov.py
# -- Figure 4: description (D1-D6)
run 4 figures/story/s4_d1.png                  "Fig 4 D1-D5 description panels (57)"              -- py scripts/57_description_panels.py
run 4 figures/story/s4_d6.png                  "Fig 4 D6 words + concordance (58)"               -- py scripts/58_description_words.py
# -- Figure 5 + supplementary results (sleep under-reporting, human ceiling, severity null)
run 4 figures/growth_v2/v4a_wake_sleep.png     "Fig 5 sleep under-reporting (95)"                 -- py scripts/95_v4a_wake_sleep.py
run 4 results/p6_sleep_underreporting.md       "Fig 5 spindle-verified check (95b)"               -- py scripts/95b_v4a_spindle_check.py
run 4 results/table5_human_ceiling.md          "S2 human ceiling (recompute_human_ceiling_v6)"    -- py scripts/recompute_human_ceiling_v6.py
run 4 results/severity_null_v6.md              "S1 severity null (109)"                           -- py scripts/109_severity_null_v6.py
# -- Table 1: cohort
run 4 results/table1.md                        "Table 1 cohort (table1_sap)"                      -- py scripts/table1_sap.py

hdr "STAGE 5 — assemble the dashboard"
run 5 __always__ "story dashboard (build_story_dashboard)" -- py scripts/build_story_dashboard.py

hdr "DONE"
echo "  results/story_dashboard.html    — the narrative dashboard (Table 1 + Figs 1-5)"
echo "  results/table1.md               — cohort table"
echo "  docs/manuscript_draft.md        — manuscript (figure paths match the above)"
