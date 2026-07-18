# LEGACY — Growth_curves `.mat` feature format (historical reference only)

> **⚠ LEGACY / DO NOT USE AS AN INPUT.** This documents the *precomputed* Growth_curves `.mat` features
> (Dr. Jing), which were first-600 s only and are **not** used by the canonical pipeline. The clean-room
> re-run recomputes every feature from raw EDF over the whole recording (`docs/analysis_plan.md` §4, §12,
> zero-reuse). Kept only to explain historical tables and to preserve the `.mat` column order / stage codes.
> The canonical column definitions live in `docs/data_dictionary.md`.

Source: `s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/`
(2.0 GiB, 12,380 objects). Precomputed by Dr. Jing. Transcribed from its `read_me.txt`.

## Layout

```
Growth_curves/
  read_me.txt
  features/
    normal/        # clinically-normal recordings  -> CONTROL group
    focal_slow/    # focal slowing                  -> abnormal comparison
    general_slow/  # generalized slowing            -> abnormal comparison
```

One file per recording: `sub-<BDSP_ID>_<YYYYMMDDHHMMSS>.mat`
- `<BDSP_ID>` = OMOP `person_id` (e.g. `S0001111192519`).
- `<YYYYMMDDHHMMSS>` = **EEG recording datetime** (e.g. `20150613113205` = 2015-06-13 11:32:05).
  → EEG time is known from the filename; OMOP only needs **birth date** to compute age.

## `.mat` contents — table `res`

One **row per 15-second segment**, 4 columns:

| Col | Name | Meaning |
|---|---|---|
| 1 | sleep_stage | 0=W, 1=N1, 2=N2, 3=N3, 4=R (REM), 5=Other |
| 2 | start | segment start sample/point |
| 3 | end | segment end sample/point |
| 4 | feature array | **18 × 31** matrix (channels × features) |

**Note:** wake is a single stage (0) — eyes-open/closed/drowsy are NOT separated here.

### 18 bipolar channels (double-banana), in order

```
0  Fp1-F7    4  Fp2-F8    8  Fp1-F3   12  Fp2-F4   16  Fz-Cz
1  F7-T3     5  F8-T4     9  F3-C3    13  F4-C4    17  Cz-Pz
2  T3-T5     6  T4-T6    10  C3-P3    14  C4-P4
3  T5-O1     7  T6-O2    11  P3-O1    15  P4-O2
```
Left chains: 0–3 (temporal), 8–11 (parasagittal). Right chains: 4–7 (temporal), 12–15
(parasagittal). Midline: 16–17. See `config/channels_regions.yaml` for the region/asymmetry mapping.

### 31 power features (per channel), in order

```
0  delta-power     8  alpha/total    16 theta/delta    24 beta/theta
1  theta-power     9  beta/total     17 theta/alpha     25 beta/alpha
2  alpha-power    10  gamma/total    18 theta/beta      26 beta/gamma
3  beta-power     11  delta/theta    19 theta/gamma     27 gamma/delta
4  gamma-power    12  delta/alpha    20 alpha/delta     28 gamma/theta*
5  total-power    13  delta/beta     21 alpha/theta     29 gamma/alpha*
6  delta/total    14  delta/gamma    22 alpha/beta      30 gamma/beta*
7  theta/total    15  theta/delta*   23 alpha/gamma
```
\* indices 28–30 continue the ratio series; confirm the exact tail order against `read_me.txt` when
loading (the readme lists ratios through `gamma/delta`; verify gamma/theta, gamma/alpha, gamma/beta).

Powers are **linear** — log-transform before z-scoring. Relative powers (`band/total`) and ratios (esp.
`alpha/delta`=inverse DAR, `alpha/theta`=inverse TAR) were already provided.

## Why this is legacy
- Coverage was **first 600 s only** (≈42 segments) — the canonical run uses the whole recording.
- Provenance was precomputed MATLAB — the canonical run uses one Python extractor over raw EDF.
- The 7–8 Hz theta/alpha edge gap present here is corrected in the canonical extractor (SAP §4.5).
