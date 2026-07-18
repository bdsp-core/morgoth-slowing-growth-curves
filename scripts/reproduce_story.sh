#!/usr/bin/env bash
# =============================================================================
# reproduce_story.sh — regenerate the paper's results in one of THREE named tiers.
#
#   bash scripts/reproduce_story.sh results     # (default) FAST — figures/tables/dashboard only
#   bash scripts/reproduce_story.sh features    # MEDIUM (~1 h) — rebuild norms/deviation/descriptors +
#                                               #   train the models, then all results, from the features
#   bash scripts/reproduce_story.sh scratch     # FULL (~24 h) — the fleet: raw EDF -> staging + feature
#                                               #   extraction on S3, then everything (needs S3 + Morgoth)
#
# The three tiers, and where each STARTS:
#   scratch  — from the raw source EDFs. Runs "the fleet" (Morgoth sleep staging + per-segment feature
#              extraction over ~27k recordings on S3; scripts/31,32,120-130 + gate rerun), assembles the
#              canonical tables, THEN falls through to `features`. Needs BDSP S3 creds + the Morgoth env
#              (MORGOTH2_DIR, PILOT_VENV) — see docs/fleet_launch.md, docs/fleet_dependencies.md. This is a
#              sharded multi-host job, not a laptop run; this script only PRINTS the fleet command and then
#              (if segment_master/ is present) continues from `features`.
#   features — from data/derived/segment_master + segment_summary + gate_rerun_done + raw panel votes.
#              Rebuilds the GAMLSS norms, the per-segment deviation field, panel inputs, descriptors and
#              single-model features, TRAINS the detectors, and produces every figure/table + the dashboard.
#   results  — from the computed derived tables (grid_norm, segment_deviation, description_*,
#              single_model_segfeats, occasion_*). Reruns the (fast) figure/model/table scripts + dashboard.
#              This is the iterate-on-publication-figures loop.
#
# PREREQUISITES: Python analysis env, run from repo root. `features`/`scratch` also need R + `gamlss`
# (steps marked [R]) and, for the panel-inputs step, the Morgoth model. Env knobs: FORCE=1 rebuild even if
# an output exists; SKIP_PANEL=1 skip the Morgoth-dependent panel-inputs step.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-src}"
export MPLBACKEND=Agg KMP_DUPLICATE_LIB_OK=TRUE
MODE="${1:-results}"
FORCE="${FORCE:-0}"; SKIP_PANEL="${SKIP_PANEL:-0}"
case "$MODE" in
  results)  FROM=4 ;;                                   # figures/tables/dashboard from derived tables
  features) FROM=0 ;;                                   # rebuild derived tables from segment_master, then results
  scratch)  FROM=0
            printf '\n\033[1;33m== SCRATCH (full fleet) ==\033[0m\n'
            echo "  The from-raw-EDF tier is the sharded S3 fleet (Morgoth staging + feature extraction,"
            echo "  ~24 h). It is not run by this laptop script. Launch it per docs/fleet_launch.md:"
            echo "    MORGOTH2_DIR=\$HOME/GithubRepos/morgoth2 PILOT_VENV=\$MORGOTH2_DIR/.venv/bin/python \\"
            echo "    MORGOTH_DEVICE=mps RUN_GATE=1 SHARD=i/N PYTHONPATH=src python scripts/31_segment_master_worker.py"
            echo "  then scripts/{32,33,120-130} to assemble the manifest + canonical tables."
            if [ ! -d data/derived/segment_master ]; then
              echo "  segment_master/ not present -> stopping. Run the fleet, then: reproduce_story.sh features"; exit 0
            fi
            echo "  segment_master/ present -> continuing as 'features' from here."; MODE=features ;;
  *) echo "usage: reproduce_story.sh [results|features|scratch]"; exit 1 ;;
esac
echo "MODE=$MODE  (FROM stage $FROM)"

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
# -- Figure S7 / Table S1: van Putten benchmark
run 4 results/vanputten_fullcoverage.md        "Fig S7 / Table S1 van Putten benchmark (recompute)" -- py scripts/recompute_vanputten_fullcov.py
# -- Figure 3: external validation (Sandor_100). Needs the Box dataset + Morgoth staging (like the panel step);
#    SKIP_SANDOR=1 to skip, or set SANDOR_DIR. Regenerates Figure 3 + results/sandor/sandor100_external.md.
SANDOR_DIR="${SANDOR_DIR:-/Users/mwestover/Library/CloudStorage/Box-Box/Brandon - DeID/0_People/ChenXiSun/ChenXiSun/Morgoth1/Datasets/Sandor_100}"
if [ "${SKIP_SANDOR:-0}" = "1" ]; then echo "  [skip] SKIP_SANDOR=1 (Sandor external validation, Figure 3)"
elif [ ! -d "$SANDOR_DIR" ]; then echo "  [skip] Sandor_100 not found at SANDOR_DIR (needs Box/rclone + Morgoth) -> Figure 3 not regenerated"
else
  run 4 data/derived/segment_master/eeg_id=SB_001 "Sandor Morgoth staging + feature extraction (sandor100_stage_extract)" -- py scripts/sandor100_stage_extract.py
  run 4 figures/story/sandor100_slowing.png    "Fig 3 Sandor external validation (sandor100_external_validation)" -- py scripts/sandor100_external_validation.py
fi
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

hdr "STAGE 5 — assemble the dashboard + the manuscript figure set"
run 5 __always__ "story dashboard (build_story_dashboard)" -- py scripts/build_story_dashboard.py
run 5 __always__ "manuscript figures -> figures/manuscript/ (assemble)" -- py scripts/assemble_manuscript_figures.py

hdr "DONE"
echo "  results/story_dashboard.html    — the narrative dashboard (Table 1 + Figs 1-5)"
echo "  results/table1.md               — cohort table"
echo "  docs/manuscript_draft.md        — manuscript (figure paths match the above)"
