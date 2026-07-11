# N3-gap expansion — full plan (2026-07-05)

**Goal.** Fill the sleep-stage normative growth curves — especially **N3 (deep sleep) across the whole
lifespan** — by ingesting long, overnight, report-NORMAL EEGs from the BDSP repository, staging +
featurizing them with the same pipeline, and merging the clean normals into the cohort norms. Today's
refit showed the normal N3 curve dies at **age 36** (min-eff-n gate) because the original cohort is
mostly short routine EEGs that don't capture deep sleep. This is a **data gap**, fixed by adding
overnight recordings — same modality, **no calibration needed** (PSG-calibration is parked as a
back-pocket alternative, `docs/psg_n3_calibration_feasibility.md`).

## The gap (current normal-N3 recordings) vs the new candidate pool
Selection: report-normal, **≥12 h** (overnight-capable), <48 h, not already in the cohort, across
**4 sites** — S0001 (MGH), S0002 (BWH), I0002 (BIDMC), I0003 (BCH). Duration filter is ≥12 h because
12–24 h studies span a full night (they start mostly 6–9 am and run through the night → capture the
00:00–06:00 deep-sleep window); short 6–12 h studies were dropped.

| age band | current N3 normals | new ≥12h candidates | source |
|---|--:|--:|---|
| 0–2 | 154 | 924 | BCH |
| 3–5 | 26 | 242 | **BCH only** |
| 6–12 | 32 | 476 | **BCH only** |
| 13–17 | 13 | 346 | BCH |
| 18–29 | 42 | 708 | MGB+BCH |
| 30–44 | 25 | 936 | MGB |
| 45–59 | 27 | 1,436 | MGB |
| 60–74 | **16** | 1,577 | MGB |
| 75+ | **15** | 972 | MGB |

**Total candidate pool: 7,617 recordings, 163,427 EEG-hours** (12–24 h: 6,139; 24–48 h: 1,478).
Every band goes from 13–154 → 242–1,577. BCH is essential (only source for pediatric 3–12).

### BIDMC (I0002) — recoverable, currently excluded
BIDMC has 43,370 long recordings + 1,286 normal findings, but its **metadata and findings files were
de-identified with inconsistent date shifts** (metadata `2012-11-11`, findings `2022-11-03`, findings
times all midnight), so the pid+date join yields only 6. pids overlap (3,168), so it's recoverable with
the correct linking key (a BIDMC linking table, or matching via BidsFolder/SessionID if present in both).
**Follow-up, not a blocker** — MGB+BCH (7,611) already cover every band. BIDMC would mostly add adults,
where MGB already dominates.

## Phase 1 — Pilot (RUNNING)
- `fleet/manifest_pilot.jsonl`: 750 adult report-normal long MGB recordings, sex-balanced, older bands
  up-weighted. (Built before the 4-site decision; validates the pipeline, not the final coverage.)
- 3 g4dn spot workers launched on account **278057567389** (profile `stanford`), AMI
  `ami-0558041058267feeb`, spot quota **512 vCPU = 128 workers** (confirmed). Output → separate S3 prefix
  `.../Growth_curves/pilot_n3/` (won't collide with the prior full-cohort run).
- **Validation criteria before scaling:**
  1. `.done` markers + `features/`, `stages/` outputs appear (pipeline works end-to-end on new data).
  2. **Actual N3 yield** — of the staged pilot recordings, what fraction have ≥3 usable N3 segments, and
     the per-band N3 recording count. This converts "≥12 h candidates" into real N3 recordings and pins
     the multiplier for the full run.
  3. Per-recording compute time (pins the full-run cost/wall-clock).
- Monitor: background loop on `.done` count + running workers (`scratchpad/pilot_monitor.log`).

## Phase 2 — Full run (PREPARED, gated on pilot validation)
- `fleet/manifest_full.jsonl`: all **7,617** (published to S3). `fleet/scale_full.sh` launches up to 128
  workers fetching it, **same `pilot_n3` prefix → resumable** (pilot's 750 skipped).
- Launch: `bash fleet/scale_full.sh 128` (from repo, profile `stanford`).
- **Cost/wall-clock estimate (refine from pilot):** long recordings ~25–45 min each →
  ~3,200–5,700 worker-hours → **~$900–1,400 spot**, **~1.5–2 days** at 128 workers. Cost is ~flat in
  worker count; more workers only compress wall-clock.
- **Safety net (3 layers, already in the fleet):** each worker self-terminates on a no-new-work pass;
  60 h per-instance `timeout`→shutdown; `fleet/finalize.sh` sweeps all `tag:fleet=morgoth-n3pilot`
  instances. Plus: attempt an AWS Budgets alarm (may need perms the `bdsp-migration` user lacks) and
  active monitoring. Fleet auto-scales to 0 when the manifest drains → idle spend ~0.

## Phase 3 — Integration & refit (after outputs land)
1. **Stream S3 outputs → derived tables** via a `scripts/51`-style adapter pointed at `pilot_n3/`
   (per-recording `features/<rid>.parquet`, `stages/<rid>.csv`) → recording-level + **(recording,
   region, stage)** tables for the new recordings, with bdsp_id = SiteID+pid, age, sex.
2. **Clean-normal labels:** these are report-normal by findings; enforce the clean-normal rule
   (normal & ~abnormal & ~focal & ~gen) from the findings (and MGB report text via `scripts/60` where
   available; BCH has no free-text report, so findings-normal is the label). Only clean normals enter
   the norms.
3. **Merge** the new stage_recording_features into the cohort's (concat + dedup on bdsp_id), then
   **refit** stage curves (`scripts/10`) and the overall growth curves — the N3 curve should now extend
   across the adult lifespan (the acceptance test: N3 `p50` non-NaN well past age 36, ideally to ~85).
4. Regenerate the dashboard; re-check downstream (discrimination, van Putten) is unaffected/improved.

## Risks / caveats
- **Duration is a proxy** — ≥12 h means the study spans a night, not that the patient reached usable N3
  (poor sleepers, artifact). Real yield measured in the pilot; if low, widen the pool (we have thousands
  per band of headroom) or lower the per-recording N3-segment threshold.
- **BCH pediatric normal definition** rests on the findings `normal` flag (no free-text report) — accept
  per Brandon's "report is ground truth" rule; spot-check a sample.
- **Spot reclaim** — self-healing (elastic workers re-cover), no action needed.
- **BIDMC** excluded pending the linking-key fix (above).

## Status / next actions (autonomous)
- [x] 4-site pool built, coverage reviewed, full manifest published (7,617).
- [x] Pilot launched (3 workers), monitor running.
- [ ] Pilot validation (N3 yield, per-recording time) — awaiting `.done` markers (~30–60 min).
- [ ] On validation → `scale_full.sh 128` (authorized: "if the pilot works, scale to the full set").
- [ ] Integration + refit → N3 acceptance test.
- [ ] (follow-up) BIDMC linking fix; (parked) PSG calibration.
