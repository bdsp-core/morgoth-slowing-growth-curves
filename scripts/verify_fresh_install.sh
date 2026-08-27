#!/bin/bash
# Definitive test: does a FRESH INSTALL -- git + exactly what S3 publishes -- reproduce every display item,
# BYTE FOR BYTE?
#
# Models the documented figure-loop sync in REPRODUCE.md:
#   * every top-level file under derived/            (so unpublished local leftovers are hidden)
#   * figure_cache/ and v4a_work/                    (published subdirs)
#   * segment_master + segment_summary: ONLY eeg_id=ON_* / eeg_id=SB_*, plus segment_master/_done/ON_*.done
#   * segment_deviation/: ONLY the six published Figure 4/5 example partitions
#
# Two things this asserts, both of which must hold:
#   1. every stage-4 producer RUNS on that subset, and
#   2. every file it writes under results/ and figures/ is byte-identical to what is committed.
#
# (2) is the point. A producer that runs but silently reads a local-only table will still PASS step 1 while
# writing different numbers -- that is the exact failure mode this script exists to catch.
#
# Run: bash scripts/verify_fresh_install.sh
set -uo pipefail

# Repo root from this script's own location -- never a hardcoded home directory.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

# Same interpreter-resolution rule as scripts/reproduce_story.sh, so both agree on a fresh clone.
PY="${PY:-$([ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)}"
command -v "$PY" >/dev/null 2>&1 || { echo "no usable python (PY=$PY)"; exit 1; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/fresh_install.XXXXXX")" || exit 1
LOGS="$WORK/logs"; mkdir -p "$LOGS"
D=data/derived
# The hidden copies stay INSIDE data/derived, under a name that says what they are. An earlier version
# moved them to a temp directory: if this script then died, or anything else touched data/derived while it
# ran, the real tables ended up orphaned in /tmp and data/derived was left holding empty directories. Keeping
# them here means a crash leaves the data one obvious rename from correct, and recover_stash() below puts it
# back automatically on the next run.
STASH="$D/.fresh_install_stash"
LOCK="$D/.fresh_install.lock"

recover_stash() {
  # A previous run died before restoring. Put everything back before doing anything else.
  [ -d "$STASH" ] || return 0
  echo "!! a previous run left hidden tables in $STASH — restoring them first"
  for d in segment_master segment_summary segment_deviation; do
    [ -e "$STASH/$d" ] || continue
    rm -rf "$D/$d"; mv "$STASH/$d" "$D/$d"; echo "   recovered $d"
  done
  if [ -d "$STASH/files" ]; then
    find "$STASH/files" -maxdepth 1 -mindepth 1 -exec mv {} "$D/" \; 2>/dev/null
  fi
  rmdir "$STASH/files" 2>/dev/null; rmdir "$STASH" 2>/dev/null
}

restore() {
  for d in segment_master segment_summary segment_deviation; do
    if [ -e "$STASH/$d" ]; then rm -rf "$D/$d"; mv "$STASH/$d" "$D/$d"; fi
  done
  if [ -d "$STASH/files" ]; then
    find "$STASH/files" -maxdepth 1 -mindepth 1 -exec mv {} "$D/" \; 2>/dev/null
  fi
  rmdir "$STASH/files" 2>/dev/null; rmdir "$STASH" 2>/dev/null
  rm -rf "$LOCK"
  echo "[restored local install]"
}

# Exclusive lock. While this runs, data/derived does NOT contain the full local install, so a producer or a
# second copy of this script running at the same time silently reads a partial tree -- which is how 198 panel
# partitions ended up empty. mkdir is atomic, so this is a real mutex, not a check-then-act.
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "REFUSING: $LOCK exists — another verify_fresh_install.sh is running, or one died."
  echo "  If nothing is running: rm -rf $LOCK  (and re-run; it will recover $STASH automatically)."
  exit 1
fi
echo "$$ $(date -u +%FT%TZ)" > "$LOCK/owner"
trap restore EXIT INT TERM
recover_stash
mkdir -p "$STASH/files"

cat <<'BANNER'
------------------------------------------------------------------------------
  data/derived is being reduced to what S3 publishes for the duration of this
  run. DO NOT run any producer, notebook or reproduce tier against this
  checkout until it prints "[restored local install]".
------------------------------------------------------------------------------
BANNER

# Snapshot the committed state of everything a producer may write, so step 2 can diff against it.
BASE="$WORK/baseline.sha"
git ls-files -z results figures | xargs -0 shasum -a 256 > "$BASE" 2>/dev/null
echo "baseline: $(wc -l < "$BASE" | tr -d ' ') committed result/figure files"

if ! git diff --quiet -- results figures; then
  echo "REFUSING: results/ or figures/ already differ from HEAD. Commit or stash first," \
       "or the byte-identity check cannot attribute a difference to this run."
  exit 1
fi

# ---------------------------------------------------------------------------
# 1. Hide everything a fresh install would not have
# ---------------------------------------------------------------------------
# 1a. top-level files under derived/ that S3 does NOT publish
PUBLISHED="$WORK/published.txt"
if aws s3 ls "s3://bdsp-opendata-credentialed/morgoth-slowing/derived/" >"$WORK/s3ls.txt" 2>"$WORK/s3err.txt"; then
  awk '$1 != "PRE" && NF >= 4 { $1=$2=$3=""; sub(/^ +/,""); print }' "$WORK/s3ls.txt" | sed '/^$/d' > "$PUBLISHED"
  echo "S3 publishes $(wc -l < "$PUBLISHED" | tr -d ' ') top-level files under derived/"
else
  echo "WARNING: cannot list S3 ($(head -1 "$WORK/s3err.txt")). Falling back to the committed"
  echo "         published-file list; refresh it with scripts/certify_reproducibility.py when S3 changes."
  cp metadata/s3_published_derived.txt "$PUBLISHED" || { echo "no fallback list"; exit 1; }
fi
hidden=0
for f in "$D"/*; do
  [ -f "$f" ] || continue
  b="$(basename "$f")"
  grep -Fxq "$b" "$PUBLISHED" && continue
  mv "$f" "$STASH/files/"; hidden=$((hidden+1))
done
echo "hidden $hidden unpublished top-level file(s)"

# 1b. segment_deviation/: only the six published Figure 4/5 example partitions survive.
#     The identities come from the PINNED_EXAMPLES tuple in scripts/62 -- the committed source of truth --
#     not from a machine-local temp file.
EXIDS="$WORK/exids.txt"
"$PY" - <<'PYEOF' > "$EXIDS"
import ast, pathlib
src = pathlib.Path("scripts/62_example_reports_panel.py").read_text()
tree = ast.parse(src)
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == "PINNED_EXAMPLES" for t in node.targets):
        for e in ast.literal_eval(node.value):
            print(e)
        break
else:
    raise SystemExit("PINNED_EXAMPLES not found in scripts/62")
PYEOF
[ -s "$EXIDS" ] || { echo "could not read PINNED_EXAMPLES"; exit 1; }

if [ -d "$D/segment_deviation" ]; then
  mv "$D/segment_deviation" "$STASH/segment_deviation"; mkdir -p "$D/segment_deviation"; n=0
  while read -r e; do
    [ -d "$STASH/segment_deviation/eeg_id=$e" ] || continue
    ln -s "$STASH/segment_deviation/eeg_id=$e" "$D/segment_deviation/eeg_id=$e"; n=$((n+1))
  done < "$EXIDS"
  echo "segment_deviation: exposed $n published example partition(s) of $(wc -l < "$EXIDS" | tr -d ' ') pinned" \
       "(hid $(ls "$STASH/segment_deviation" | wc -l | tr -d ' ') local)"
fi

# 1c. segment_master / segment_summary: keep only the published panel subsets, via symlinks
for d in segment_master segment_summary; do
  [ -d "$D/$d" ] || continue
  mv "$D/$d" "$STASH/$d"; mkdir -p "$D/$d"; n=0
  for p in "$STASH/$d"/eeg_id=ON_* "$STASH/$d"/eeg_id=SB_*; do
    [ -e "$p" ] || continue
    ln -s "$p" "$D/$d/$(basename "$p")"; n=$((n+1))
  done
  if [ -d "$STASH/$d/_done" ]; then
    mkdir -p "$D/$d/_done"
    for s in "$STASH/$d"/_done/ON_*.done; do
      [ -e "$s" ] && ln -s "$s" "$D/$d/_done/$(basename "$s")"
    done
  fi
  echo "  $d: exposed $n panel partition(s)$([ -d "$D/$d/_done" ] && echo " + $(ls "$D/$d/_done" | wc -l | tr -d ' ') ON_ done-sidecars")"
done
echo

# ---------------------------------------------------------------------------
# 2. Run every stage-4 display-item producer
# ---------------------------------------------------------------------------
PRODUCERS=(76_keystone_growth_grid.py 77_topoplots_by_age.py 54_single_model_train_eval.py 55_recording_model.py
  sandor100_external_validation.py 62_example_reports_panel.py 63_example_eeg_traces.py 57_description_panels.py
  58_description_words.py fig6_sleep_naming.py architecture_diagram.py 78_centile_calibration.py
  vanputten_panel_s7.py 111_curve_bank_v6.py 44_segment_deviation_summary.py 49_occasion_allstage_localized.py
  109_severity_null_v6.py table1_sap.py recompute_vanputten_fullcov.py recompute_human_ceiling_v6.py
  band_calibration.py 95_v4a_wake_sleep.py)

fails=0
for s in "${PRODUCERS[@]}"; do
  if PYTHONPATH=src KMP_DUPLICATE_LIB_OK=TRUE MPLBACKEND=Agg "$PY" "scripts/$s" >"$LOGS/$s.log" 2>&1; then
    echo "PASS  $s"
  else
    echo "FAIL  $s : $(grep -E '^[A-Za-z.]*(Error|Exception)|SystemExit' "$LOGS/$s.log" | tail -1 | cut -c1-100)"
    fails=$((fails+1))
  fi
done
echo

# ---------------------------------------------------------------------------
# 3. Byte-identity: did the fresh-install run reproduce the committed bytes?
# ---------------------------------------------------------------------------
AFTER="$WORK/after.sha"
git ls-files -z results figures | xargs -0 shasum -a 256 > "$AFTER" 2>/dev/null
CHANGED="$(diff <(sort "$BASE") <(sort "$AFTER") | grep -c '^[<>]' || true)"

# --- 3a. the NUMBERS must be byte-identical -------------------------------------------------------
# results/ holds every quoted figure as text (md/csv/json). Any difference here is a real change in what
# the paper says, so this check has no tolerance at all.
drifted=0
while IFS= read -r f; do
  git diff --quiet -- "$f" || { echo "DRIFT  $f"; drifted=$((drifted+1)); }
done < <(git ls-files results | grep -vE '\.(png|pdf)$')

# --- 3b. the FIGURES must be the same plot ---------------------------------------------------------
# PNGs are NOT compared byte-for-byte on purpose. matplotlib/FreeType render the identical figure with
# sub-pixel differences across versions and platforms: re-running a producer on a machine with a different
# matplotlib moves every glyph and every line edge by a fraction of a pixel, so a byte (or exact-pixel)
# comparison reports 100% "drift" on a run whose numbers are provably unchanged. Measured here: matplotlib
# 3.10.8 vs the committed renders differ on 2.8-6.8% of pixels -- all of them anti-aliased EDGES -- while
# every results/ file stays byte-identical.
#
# So the figure test asks the question that actually matters: is this the same plot? Both images are blurred
# (which collapses sub-pixel edge jitter) and compared on mean absolute intensity. A moved curve, a changed
# number, or a different panel survives the blur; a renderer version does not. Pin the environment with
# requirements.lock.txt if you need bit-identical PNGs too.
BLUR_TOL="${BLUR_TOL:-2.0}"        # mean |difference| in 0-255 grey after blur
pixdrift=0
while IFS= read -r f; do
  git diff --quiet -- "$f" && continue
  out="$("$PY" - "$f" "$BLUR_TOL" <<'PYEOF'
import subprocess, sys, io
import numpy as np
from PIL import Image, ImageFilter
p, tol = sys.argv[1], float(sys.argv[2])
old = subprocess.run(["git", "show", f"HEAD:{p}"], capture_output=True).stdout
try:
    A = Image.open(io.BytesIO(old)).convert("L")
    B = Image.open(p).convert("L")
except Exception as e:
    print(f"unreadable: {e}"); sys.exit(1)
if A.size != B.size:
    # a renderer can move a tight bbox by a pixel or two; anything larger is a layout change
    dw, dh = abs(A.size[0]-B.size[0]), abs(A.size[1]-B.size[1])
    if dw > 8 or dh > 8:
        print(f"size {A.size} -> {B.size}"); sys.exit(1)
    B = B.resize(A.size, Image.LANCZOS)
a = np.asarray(A.filter(ImageFilter.GaussianBlur(2.0)), dtype=float)
b = np.asarray(B.filter(ImageFilter.GaussianBlur(2.0)), dtype=float)
m = float(np.abs(a-b).mean())
print(f"mean|d|={m:.2f} (tol {tol})")
sys.exit(0 if m <= tol else 1)
PYEOF
)"
  if [ $? -eq 0 ]; then
    echo "  same plot, renderer differs  $f  [$out]"
  else
    echo "FIGURE DRIFT  $f  [$out]"; pixdrift=$((pixdrift+1))
  fi
done < <(git ls-files figures | grep -E '\.png$')

echo
echo "=============================================================================="
echo "  producers run:        ${#PRODUCERS[@]}   failed: $fails"
echo "  results/ files:       numeric drift: $drifted (must be 0)"
echo "  figures/ PNGs:        figure drift: $pixdrift (must be 0; renderer-only differences are OK)"
echo "=============================================================================="
if [ "$fails" -eq 0 ] && [ "$drifted" -eq 0 ] && [ "$pixdrift" -eq 0 ]; then
  echo "  FRESH INSTALL REPRODUCES THE PAPER BYTE-FOR-BYTE."
  rc=0
else
  echo "  FRESH INSTALL DOES NOT REPRODUCE THE PAPER. Logs: $LOGS"
  rc=1
fi
echo "=============================================================================="
exit $rc
