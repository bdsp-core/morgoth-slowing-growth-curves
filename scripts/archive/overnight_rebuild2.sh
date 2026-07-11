#!/usr/bin/env bash
# Phase 2 overnight: after ALL expansion features are local (expansion/ + pilot_n3/ union ~16,131),
# rebuild the uniform table on the full overnight set + cohort, re-pull OMOP ages, and regenerate the
# source-appropriate curves, harmonization diagnostic, and topoplots. Review in the AM.
set -uo pipefail
cd "$(dirname "$0")/.."
TMP=/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/n3feats
LOG=/tmp/overnight2.log; : > "$LOG"
say(){ echo "=== $* ($(date +%H:%M:%S)) ==="; }
run(){ echo ">> $*"; "$@" && echo "OK" || echo "FAILED: $*"; }
{
say "PHASE 2 START"
say "0. wait for expansion pull to finish"
while pgrep -f 'rclone.*expansion/features' >/dev/null; do sleep 30; done
echo "local features: $(find $TMP -name '*.parquet' | wc -l) (expect ~16131)"

say "1. rebuild uniform table on FULL overnight set + cohort"
run python3 scripts/70_build_uniform_reference.py data/derived/cohort_channel_stage.parquet "$TMP"

say "2. OMOP fractional ages"
run python3 scripts/71_omop_fractional_age.py

say "3. harmonization diagnostic (full data)"
run env PYTHONPATH=src python3 scripts/75_source_harmonization.py rel_delta

say "4. growth curves — source-appropriate + pooled"
run env PYTHONPATH=src python3 scripts/67_central_stage_growth.py rel_delta smooth auto
run env PYTHONPATH=src python3 scripts/67_central_stage_growth.py rel_delta smooth pooled

say "5. topoplots (clean-normal, source-appropriate)"
run env PYTHONPATH=src python3 scripts/68_topoplots_by_age.py rel_delta

say "PHASE 2 DONE — full data (~16,131 overnight + 4,916 routine)"
} 2>&1 | tee -a "$LOG"
