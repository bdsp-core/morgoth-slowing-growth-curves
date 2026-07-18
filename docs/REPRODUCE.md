# Reproducing the analysis

Everything in the paper — models, figures, tables, and the story dashboard — regenerates from the
derived feature tables with a single command:

```bash
bash scripts/reproduce_story.sh
```

The runner is self-documenting (see its header). It rebuilds, in dependency order, from
`data/derived/*`:

| Stage | What | Notes |
|---|---|---|
| 0 | canonical tables + corrected SAP labels | scans `segment_master/`; local |
| 1 | GAMLSS normative curves + per-segment deviation field | **needs R + `gamlss`** for the norm grid; deviation field is CPU |
| 2 | expert-panel inputs (features + Morgoth predictions) | **needs the Morgoth model + fleet panel partitions**; `SKIP_PANEL=1` to skip |
| 3 | description descriptors + single-model segment features | local |
| 4 | figures, tables, trained models (Fig 1–5, Table 1–2, S1–S2) | local; two steps need R |
| 5 | assemble `results/story_dashboard.html` | local |

Each step is skipped when its output already exists; `FORCE=1` rebuilds everything, `FROM=<n>` starts at
stage *n*, `SKIP_PANEL=1` skips the Morgoth-dependent stage.

### Prerequisites

- **Python analysis environment** (see `requirements.txt` / `pyproject.toml`); run from the repo root.
- **R with the `gamlss` package** for the two GAMLSS steps (`scripts/gamlss_*.R`, called by `115` and `76`).
- **Upstream fleet/Morgoth outputs already present** under `data/derived/`: `segment_master/`,
  `segment_summary/`, the Morgoth gate rerun (`gate_rerun_done/` → `gate_eeg_level_rerun.parquet`), and the
  raw human panel votes (`occasion_expert_votes.parquet`). These are produced by the cloud fleet
  (`fleet/`, `scripts/31`, `scripts/32*`, `scripts/120`–`130`) and are **assumed done** — the runner does
  not rebuild them.
- **Sleep staging** runs in a separate virtual environment (the stager pins `pandas<2`); it is part of the
  fleet feature-extraction step, upstream of this runner.

### Outputs

- `results/story_dashboard.html` — the narrative dashboard (Table 1 + Figures 1–5), self-contained.
- `results/table1.md`, `results/vanputten_fullcoverage.md`, `results/severity_null_v6.md`,
  `results/table5_human_ceiling.md`, `results/p6_sleep_underreporting.md` — the manuscript tables/results.
- `figures/growth_v2/`, `figures/story/`, `figures/stage_curves/`, `figures/curves/` — the figures.
- `docs/manuscript_draft.md` — the manuscript; its figure/table paths match the above.

### Known reproducibility note

`results/story/s0c_morgoth_free.md` (the in-domain focal/generalized detector trajectory shown in dashboard
block 2b) is a hand-authored summary table with no producing script; it is documentation of the design
search, not a regenerated artifact. Everything else in the dashboard is script-produced by the stages above.
