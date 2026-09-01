#!/bin/bash
# Definitive test: does a FRESH INSTALL -- git + exactly what S3 publishes -- reproduce every display item?
#
# Models the documented figure-loop sync:
#   * every top-level file under derived/            (so unpublished local leftovers are hidden)
#   * figure_cache/ and v4a_work/                    (published subdirs)
#   * segment_master + segment_summary: ONLY eeg_id=ON_* / eeg_id=SB_*, plus segment_master/_done/ON_*.done
#   * segment_deviation/: NOT synced at all
set -uo pipefail
cd "/Users/mbwest/Desktop/GithubRepos/morgoth-slowing-growth-curves"
D=data/derived; STASH=/tmp/fresh_stash; rm -rf $STASH; mkdir -p $STASH
restore() {
  for d in segment_master segment_summary segment_deviation; do
    if [ -d "$STASH/$d" ]; then rm -rf "$D/$d"; mv "$STASH/$d" "$D/$d"; fi
  done
  [ -d "$STASH/files" ] && mv "$STASH/files"/* "$D/" 2>/dev/null
  echo "[restored]"
}
trap restore EXIT INT TERM

# 1. hide unpublished top-level files
mkdir -p $STASH/files
for f in .DS_Store adjusted_z.parquet bsi_features.parquet case2_review_set.jsonl cohort_person_ids.txt \
         description_descriptors.parquet deviation_field.parquet expansion_candidates.csv fleet_progress.jsonl \
         gate_probs.parquet growth_curves.parquet labels_unified.pre_rebuild.parquet progress.jsonl \
         recording_asymmetry.parquet recording_features.parquet regional_stage_recording_features.parquet \
         review_set.jsonl scores_v2.parquet slow_peak_freq_sample.parquet stage_abnormals_progress.jsonl \
         stage_curves.parquet stage_recording_features.parquet; do
  [ -e "$D/$f" ] && mv "$D/$f" "$STASH/files/"
done
echo "hidden $(ls $STASH/files | wc -l | tr -d ' ') unpublished top-level files"

# 2. segment_deviation: only the six published Figure 4/5 example partitions survive
if [ -d "$D/segment_deviation" ]; then
  mv "$D/segment_deviation" "$STASH/segment_deviation"; mkdir -p "$D/segment_deviation"; n=0
  # IDs come from the committed examples table, never from a temp file: an earlier version read
  # /tmp/exids.txt, which did not survive, so ZERO partitions were exposed and scripts/63 silently drew
  # "EEG unavailable" panels that differed from the committed figures.
  while read -r e; do
    [ -d "$STASH/segment_deviation/eeg_id=$e" ] || continue
    ln -s "$STASH/segment_deviation/eeg_id=$e" "$D/segment_deviation/eeg_id=$e"; n=$((n+1))
  done < <(.venv/bin/python -c "import pandas as pd; print('\n'.join(pd.read_parquet('results/story/s4_examples.parquet').eeg_id))")
  echo "segment_deviation: exposed $n published example partitions (of $(ls $STASH/segment_deviation | wc -l | tr -d ' '))"
fi

# 3. segment_master / segment_summary: keep only the published panel subsets, via symlinks
for d in segment_master segment_summary; do
  [ -d "$D/$d" ] || continue
  mv "$D/$d" "$STASH/$d"; mkdir -p "$D/$d"
  n=0
  for p in "$STASH/$d"/eeg_id=ON_* "$STASH/$d"/eeg_id=SB_*; do
    [ -e "$p" ] || continue
    ln -s "$p" "$D/$d/$(basename "$p")"; n=$((n+1))
  done
  if [ -d "$STASH/$d/_done" ]; then
    mkdir -p "$D/$d/_done"
    for s in "$STASH/$d"/_done/ON_*.done; do [ -e "$s" ] && ln -s "$s" "$D/$d/_done/$(basename "$s")"; done
  fi
  echo "  $d: exposed $n panel partitions$([ -d "$D/$d/_done" ] && echo " + $(ls $D/$d/_done | wc -l | tr -d ' ') ON_ done-sidecars")"
done
echo

PRODUCERS=(76_keystone_growth_grid.py 77_topoplots_by_age.py 54_single_model_train_eval.py 55_recording_model.py
  sandor100_external_validation.py 62_example_reports_panel.py 63_example_eeg_traces.py 57_description_panels.py
  58_description_words.py fig6_sleep_naming.py architecture_diagram.py 78_centile_calibration.py
  vanputten_panel_s7.py 111_curve_bank_v6.py 44_segment_deviation_summary.py 49_occasion_allstage_localized.py
  109_severity_null_v6.py table1_sap.py recompute_vanputten_fullcov.py recompute_human_ceiling_v6.py
  112_age_ablation.py 79_curve_fit_diagnostic.py 80_topk_sweep.py
  band_calibration.py 95_v4a_wake_sleep.py)
mkdir -p /tmp/flv3
for s in "${PRODUCERS[@]}"; do
  if PYTHONPATH=src .venv/bin/python "scripts/$s" >/tmp/flv3/"$s".log 2>&1; then echo "PASS  $s"
  else echo "FAIL  $s : $(grep -E '^[A-Za-z.]*(Error|Exception)|SystemExit' /tmp/flv3/$s.log | tail -1 | cut -c1-100)"; fi
done
