# Reproducible feature extraction (Python) — validation & status

The original Growth_curves features were precomputed in MATLAB (code unavailable). `features/extract.py`
recomputes them from raw EEG in Python so the pipeline is reproducible and new recordings can be
featurized identically. `scripts/13_recompute_features.py` regenerated all 12,379 recordings →
`*_py.parquet`, now the canonical feature set (JJ's kept as `*_jj.parquet` for reference).

## Pipeline
referential EEG → 18 bipolar (double-banana) → 0.5 Hz high-pass + 50/60 Hz notch → 15-s segments
(3000 samp @200 Hz, step 2800) → multitaper PSD (NW=4, 7 tapers) → 31 features
(δθαβγ power + total + relative + ratios). Also emits per-channel (18) + homologous-pair (8)
features for focal localization.

## Validation vs JJ's features (scripts/12_validate_extractor.py)
Per-band **log-power correlation r = 0.89–0.95** (delta .89, theta .90, alpha .89, beta .95,
total .87; gamma .79 — filtering-sensitive). The two feature sets carry the same signal.

Downstream re-run on the Python features reproduces the science:
- Stage physiology preserved: normal median rel_delta N3 > N2 > W/REM > N1.
- Discrimination preserved; **per-channel homologous asymmetry (e.g. `|asym_ch_T3-T5_delta|`) is now a
  top focal discriminator** (AUC ~0.70 normal-vs-focal) — the localization signal we added.

## Known caveat (calibration TODO)
**Absolute relative-power values run higher** than JJ's / physiological convention (e.g. normal
whole-head rel_delta median ~0.5 vs JJ ~0.3; N3 ~0.86). Cause: the low-frequency edge / `total`-band
definition differs from JJ's (residual sub-2 Hz power inflates δ/total). This is a *scaling* issue:
- It does **not** affect the z-based scoring, discrimination, or report descriptions (all computed as
  deviations from each feature's own age/sex/stage normal curve → scale-invariant).
- It **does** affect the raw y-axis magnitude of the relative-power curves and cross-feature absolute
  comparisons.
- Fix when needed: calibrate the delta low-edge (try 1 Hz) and/or the `total` band to match JJ /
  clinical convention; re-validate rel_delta median ≈ 0.3 in awake normals. Absolute log-powers
  already match well (r≈0.9), so this is a small, localized calibration.
