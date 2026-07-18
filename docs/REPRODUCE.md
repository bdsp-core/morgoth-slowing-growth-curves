# Reproducing the analysis

Everything in the paper regenerates through one runner, in **three named tiers** that differ only in where
they *start*:

```bash
bash scripts/reproduce_story.sh results     # FAST (minutes) — default
bash scripts/reproduce_story.sh features    # MEDIUM (~1 h)
bash scripts/reproduce_story.sh scratch     # FULL (~24 h)
```

| Tier | Starts from | Does | Time | Needs |
|---|---|---|---|---|
| **`results`** | the computed derived tables (`grid_norm.json`, `segment_deviation/`, `description_*`, `single_model_segfeats`, `occasion_*`) | reruns the (fast) figure / model / table scripts + rebuilds the dashboard | minutes | Python env |
| **`features`** | the extracted features (`segment_master/`, `segment_summary/`, `gate_rerun_done/`, raw panel votes) | rebuilds GAMLSS norms + per-segment deviation field + panel inputs + descriptors + single-model features, **trains the detectors**, then all `results` | ~1 h | Python + **R/`gamlss`** (+ Morgoth for the panel-inputs step) |
| **`scratch`** | the raw source EDFs on S3 | runs **the fleet** — Morgoth sleep staging + per-segment feature extraction over ~27k recordings — assembles the canonical tables, then falls through to `features` | ~24 h | BDSP **S3** creds + the **Morgoth** env (`MORGOTH2_DIR`, `PILOT_VENV`); see [fleet_launch.md](fleet_launch.md), [fleet_dependencies.md](fleet_dependencies.md) |

**Which to use.** Iterating on figures/wording for submission → `results`. Changed a norm, a feature, or a
model → `features`. Re-deriving from raw signal (new data, or a full audit) → `scratch`.

### How it runs

The runner executes numbered stages (0 canonical tables · 1 norms + deviation field · 2 panel inputs
[Morgoth] · 3 descriptors + model features · 4 figures/tables/models · 5 dashboard); the tier just sets the
starting stage (`results`→4, `features`→0, `scratch`→fleet then 0). Each step is **skipped when its output
already exists** — `FORCE=1` rebuilds regardless, `SKIP_PANEL=1` skips the Morgoth-dependent panel step.
Steps needing R (`115_descriptor_grid`, `76_keystone_growth_grid`) are marked `[R]` in the output.

`scratch` is a **sharded, multi-host S3 job**, not a laptop run; the runner prints the fleet command
(`scripts/31_segment_master_worker.py` with `SHARD=i/N`, then `scripts/{32,33,120–130}`) and, if
`segment_master/` is already present locally, continues from `features`.

### Outputs

- `results/story_dashboard.html` — the narrative dashboard (Table 1 + Figures 1–5), self-contained.
- `results/table1.md`, `results/vanputten_fullcoverage.md`, `results/severity_null_v6.md`,
  `results/table5_human_ceiling.md`, `results/p6_sleep_underreporting.md`, `results/story/s0*.md`,
  `results/story/s4_*.md` — the manuscript tables/results (panel AUROCs carry recording-level bootstrap CIs).
- `figures/growth_v2/`, `figures/story/`, `figures/stage_curves/`, `figures/curves/` — the figures.
- `docs/manuscript_draft.md` — the manuscript; figure/table paths match the above.

### Known reproducibility note

`results/story/s0c_morgoth_free.md` (the in-domain focal/generalized trajectory in dashboard block 2b) is a
hand-authored summary of the design search, not a script-generated artifact. Everything else is produced by
the stages above.
