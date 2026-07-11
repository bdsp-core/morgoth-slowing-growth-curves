# Phase 0 findings (2026-07-02)

First look at the real data via the rclone `bdsp:` S3 remote (keys in `~/Desktop/GithubRepos/AWSKeys/`).
Growth_curves feature set pulled to `data/raw/Growth_curves/` (2.1 GiB, 12,379 files).

## Sizes
| Path | Size | Contents |
|---|---|---|
| `morgoth2/.../Growth_curves` | 2.0 GiB | `features/{normal,focal_slow,general_slow}/*.mat` + read_me |
| `morgoth1/.../FOCALSLOWING` | 18.7 GiB | `segments_raw/` + `list_events_focalslowing_20241121.xlsx` |
| `morgoth1/.../GENSLOWING` | 50.7 GiB | `segments_raw/` + `list_events_gensloing_20241121.xlsx` |

Total ~71 GiB vs ~7.1 TiB free → **no disk constraint**.

## `.mat` format (confirmed against embedded metadata)
Keys: `res`, `age`, `channels`, `feature_names`, `res_hdr`.
- `res`: **43 rows × 4** per file. Cols: `[sleep_stage, start, end, 18×31 features]`.
  Every file is exactly **43 segments** of 3000 samples (= 15 s @ 200 Hz) ≈ **10.75 min clip**.
- `channels` (18) and `feature_names` (31) match `config/channels_regions.yaml` and
  `docs/data_dictionary.md` exactly (feature order verified, incl. tail gamma/theta·alpha·beta).
- `age` embedded per file (integer years).

## ✅ Good news
- **Labels are free**: folder = class. Counts — **normal 4,916 · focal_slow 2,067 · general_slow 5,396**
  (12,027 unique person_ids; ~1 recording/patient).
- **Age is in the files** → no OMOP needed for age.
- **Lifespan coverage of the control (`normal`) group is already good** — JJ evidently did this:

```
age band   focal  general  normal   TOTAL
0-2           24     198     344      566
3-5           10     137     174      321
6-12          48     299     284      631
13-17         35     153     278      466
18-29        156     495     883     1534
30-44        249     565     752     1566
45-59        459     975     895     2329
60-74        681    1484     862     3027
75+          405    1076     442     1923
```
Normals span infancy→elderly; thinnest cells are 3–5 (174) and 6–12 (284) but usable.

## ⚠️ Gaps / issues to resolve
1. **Sleep stage is uniformly "Other" (5) in ALL files.** This normative set is **unstaged**, so the
   state-specific-norms design (W/N1/N2/N3/REM) CANNOT be built from Growth_curves as-is. Options:
   (a) obtain morgoth sleep stages for these recordings, (b) run a stager on the raw EEG,
   (c) build stage-agnostic norms first and add staging later. **Needs a decision — this is the
   single biggest blocker to the sleep-stage part of the goal.**
2. **Sex is not in the files.** Sex-stratified curves need sex from OMOP (BDSP id + `person.gender`)
   or another source. Age-only curves can proceed meanwhile.
3. **Age data cleaning:** observed min = −6 and max = 121 (9 missing) → impossible values; filter to a
   plausible range and inspect outliers before fitting.
4. **Each clip is a fixed 43-segment excerpt**, not a full recording — confirm how the 10.75 min was
   selected (random? first N? awake?), since it affects what "prevalence/burden over the recording"
   means.

## Next actions
- Decide the staging strategy (#1).
- Pull sex from OMOP for the 12k person_ids (`io/omop.py`), or confirm another source.
- Build the cleaned control cohort + coverage notebook (Phase 1) and start age-conditioned curves.
