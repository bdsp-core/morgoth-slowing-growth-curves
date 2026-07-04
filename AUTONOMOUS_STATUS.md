# Autonomous run — status (updated each loop iteration)

**Started:** 2026-07-04 (Brandon away ~24 h). **Mode:** `/loop` autonomous.
**Phone dashboard:** https://claude.ai/code/artifact/ff73ffa6-2a9b-484f-914f-a04a84c5d51a

## The one thing I can't do unattended
Launching the multi-instance **AWS fleet** needs the console/credentials I don't have (box has no IAM
role; Mac has no aws CLI/creds; only BDSP S3 *read* keys, different account). So the full ~15k-in-1-day
run needs **one console action from you**. Everything else below I do autonomously, and I'll leave the
fleet **fully prepped** (scripts + work manifest + budget guardrail) so it's a one-command launch.

## Autonomous plan (what I'm doing while you're gone)
1. **Finish + validate the pilot** (8–10 recordings end-to-end → parquet + sane stats).  ⏳
2. **Multicore feature extraction** (the approved speedup; ~4× on the 4-core box).  ⏳
3. **Persist all outputs** per recording — features + per-window sleep stages + focal/gen/normal gate
   probabilities — each with provenance (source EDF path + code commit), for publication.  ⏳
4. **Overnight single-box expansion** on the existing g4dn.xlarge (bounded ~$13): process as many
   report-labeled recordings as fit, prioritizing sparse age×sex×stage cells.  ⏳
5. **Refit growth curves + rerun** scoring / discrimination / report-agreement / ROC-PRC / calibration
   on the expanded set; regenerate all figures + the gallery.  ⏳
6. **Finalize** manuscript ([TBD]s), bdsp.io writeup, docs.  ⏳
7. **Prep the full fleet**: container/Batch/CLI scripts + work manifest + $ guardrail, ready to fire.  ⏳

## Cost
Single existing box only: ~$0.53/hr × ~24 h ≈ **$13**, bounded and known. **No fleet launched** (can't).

## Log
- (init) scaffolding created; pilot running with memory fix (1/8 done, no OOM).
- (cycle 2) Pipeline hardened + validated end-to-end on the box:
  - Fixed OOM root cause: bounded per-channel preprocess + preallocated bipolar (identical results).
  - Chunked pyedflib loader (bit-exact vs mne, ~3GB peak vs OOM).
  - **Robust resumable per-recording worker** (scripts/30): features + sleep stages + provenance,
    .done markers. Validated 2 recordings incl. a 33h one (5385/8476 usable, 8 min).
  - **Multicore** feature extraction (fork+COW, bit-identical; box load avg ~10 on 4 cores).
  - **Stratified selection** (label × age-band round-robin) to fill sparse cells.
  - Fixed staging: morgoth needs `pytest` (stray sklearn.tests import).
  - **Overnight run launched**: 300 recordings, detached, multicore. Resumable if interrupted.
  - Still TODO: locate slowing-gate checkpoints for focal/gen/normal probs on new recordings;
    refit curves + rerun analysis on expanded data; finalize manuscript/bdsp.io; fleet package.
- (cycle 3) Overnight run healthy (10 done, no OOM). **Gate wired end-to-end**:
  - Located gate checkpoints in S3 (morgoth2/models/202605/morgoth/): NORMAL, SLOWING + FOC/GEN/NORMAL
    EEG-level aggregators; downloaded to box.
  - Validated gate plumbing on a test .mat (5 stages run; pred_EEG_level_{NORMAL,FOC,GEN}.csv).
  - Integrated into the worker: each recording now also gets NORMAL+SLOWING window heads -> focal/gen/
    normal EEG-level probs (10s step, recording-level), persisted to expansion/gate/<rid>.json.
  - Relaunched worker WITH gate (300 target). ~10 early recordings are features+stages only (can
    backfill gate); everything new gets all three outputs. Coverage ~130-150 overnight w/ gate.
  - Next: verify gate probs are sane on real recordings; then refit curves + rerun analysis on the
    expanded data; finalize manuscript/bdsp.io; build fleet package.
