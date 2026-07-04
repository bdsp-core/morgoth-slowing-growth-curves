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
