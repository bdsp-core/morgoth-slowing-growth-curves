#!/usr/bin/env bash
# Overnight rebuild: wait for the uniform table (scripts/70), then re-pull OMOP ages, and regenerate every
# analysis on the full data with all the fixes (TAR index, clean-normal filter, BCT age-varying skewness,
# source-appropriate norms). Robust: each step logged, failures don't abort the chain. Review in the AM.
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=/tmp/overnight.log; : > "$LOG"
say(){ echo "=== $* ($(date +%H:%M:%S)) ==="; }
run(){ echo ">> $*"; "$@" && echo "OK" || echo "FAILED: $*"; }

{
say "OVERNIGHT REBUILD START"

say "1. wait for uniform table build (scripts/70)"
while pgrep -f '70_build_uniform' >/dev/null; do sleep 20; done
tail -6 /tmp/build70.log

say "2. OMOP fractional ages (person_id -> birth_datetime; read-only)"
run python3 scripts/71_omop_fractional_age.py

say "3. source-harmonization diagnostic (cohort vs expansion)"
run env PYTHONPATH=src python3 scripts/75_source_harmonization.py rel_delta

say "4. growth curves — source-appropriate (auto) AND pooled, for rel_delta"
run env PYTHONPATH=src python3 scripts/67_central_stage_growth.py rel_delta smooth auto
run env PYTHONPATH=src python3 scripts/67_central_stage_growth.py rel_delta smooth pooled

say "5. topoplots by age/stage (clean-normal, source-appropriate)"
run env PYTHONPATH=src python3 scripts/68_topoplots_by_age.py rel_delta

say "6. discrimination refresh (single-source cohort; verifies corrected TAR AUC)"
run env PYTHONPATH=src python3 scripts/06_discrimination.py

say "OVERNIGHT REBUILD DONE"
} 2>&1 | tee -a "$LOG"
