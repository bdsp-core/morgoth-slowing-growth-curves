# Coverage-expansion plan — filling the adult-N3 and abnormal-with-sleep gaps

`docs/coverage_by_stage.md` identified the only two real gaps in our current cohort
(`metadata/cohort_metadata.csv`, 12,379 recordings): **adult N3 / deep sleep** (thin at age ≥3 and
worse with age) and **abnormal-with-sleep** (focal/generalized slowing captured across a full night).
Both are fixable — the full BDSP EEG repository holds thousands of long, sleep-capturing routine EEGs
that carry a clinician-report label.

This is the **selection** step only (no raw EEG, no ingestion). `scripts/23_expansion_cohort.py`
joins the per-site EEG metadata to the report-findings tables and emits
`data/derived/expansion_candidates.csv`. Selection rules:

- **(a) long enough to contain sleep** — `DurationInSeconds > 6*3600`
- **(b) report-derived label** — the interpreting report states `normal` **or** `foc slowing` **or**
  `gen slowing` (a findings-cell value containing `report`; model/annotation-only labels are ignored,
  per Brandon: the report is ground truth)
- **(c) new** — not already in `cohort_metadata.csv` (matched on full `bdsp_id` = `SiteID`+person_id,
  and start **date**)

## Headline: 44,953 NEW candidate recordings

| metric | count |
|---|---:|
| **NEW candidates (total)** | **44,953** |
| adults (age ≥ 18) | 36,512 |
| pediatric (< 18) | 8,412 |
| age missing | 29 |
| multi-day (≥ 24 h) | 9,927 |
| 12–24 h | 28,961 |
| 6–12 h | 6,065 |
| **adult long normal (the N3-norm gap)** | **8,168** |
| **adult abnormal-with-sleep (focal/gen)** | **33,946** |
| total candidate EEG-hours | ~942,700 |

Labels are **non-exclusive** (a recording can be normal, or focal and/or generalized): normal 10,862 ·
focal 11,321 · generalized 38,450 · any-abnormal 34,563.

### Sites covered

| site | new candidates | notes |
|---|---:|---|
| **S0001** | 26,445 | already partly in cohort; huge long-EEG pool |
| **S0002** | 12,655 | already partly in cohort |
| **I0003** | 5,810 | **new site** — not in current cohort at all |
| **I0002** | 43 | findings `StartTime` is date-only/midnight → few date-matches; low yield |

`I0009` has an `eeg-metadata` CSV but **no findings table** (and a different schema), so no report
label can be attached — it is excluded. `I0001` has a findings export but no `eeg-metadata` CSV in the
open repo, so it cannot be duration/age-filtered — also excluded. Current cohort is S0001/S0002 only,
so **I0003 is entirely additive** and S0001/S0002 add the long recordings we skipped the first time.

## NEW candidates by age band × sex × label

Counts are recordings (one row per patient-day). Columns are sex (F / M / Other-NA; pediatric rows
carry a lot of Unknown/X sex). A recording contributes to every label its report states.

### Normal (feeds the reference norms — the adult-N3 fix)
| band | F | M | Other/NA |
|---|---:|---:|---:|
| 0-2 | 240 | 276 | 695 |
| 3-5 | 23 | 53 | 259 |
| 6-12 | 62 | 63 | 496 |
| 13-17 | 72 | 62 | 385 |
| 18-29 | 570 | 334 | 117 |
| 30-44 | 745 | 525 | 5 |
| 45-59 | 1,043 | 994 | 0 |
| 60-74 | 1,157 | 1,274 | 1 |
| 75+ | 685 | 718 | 0 |

Adult bands (18+) now offer **hundreds to >1,000 normal long-EEGs per band/sex** — vs the current
15–42 N3 recordings/band. This closes the adult-N3 norm gap directly.

### Focal slowing (abnormal-with-sleep, focal)
| band | F | M | Other/NA |
|---|---:|---:|---:|
| 0-2 | 73 | 55 | 362 |
| 3-5 | 27 | 25 | 150 |
| 6-12 | 48 | 68 | 219 |
| 13-17 | 77 | 37 | 70 |
| 18-29 | 416 | 454 | 32 |
| 30-44 | 766 | 658 | 1 |
| 45-59 | 1,408 | 1,134 | 0 |
| 60-74 | 1,736 | 1,700 | 1 |
| 75+ | 970 | 820 | 6 |

### Generalized slowing (abnormal-with-sleep, generalized)
| band | F | M | Other/NA |
|---|---:|---:|---:|
| 0-2 | 351 | 363 | 1,320 |
| 3-5 | 143 | 175 | 665 |
| 6-12 | 333 | 423 | 994 |
| 13-17 | 323 | 240 | 431 |
| 18-29 | 2,070 | 1,686 | 200 |
| 30-44 | 2,290 | 2,183 | 7 |
| 45-59 | 3,717 | 3,904 | 4 |
| 60-74 | 5,313 | 5,389 | 5 |
| 75+ | 3,084 | 2,810 | 9 |

## Priority score (in the CSV `priority` column)

Up-weights the two gaps so a batch can be pulled top-down:

```
1.0  base
+1.5  adult (≥18) & normal            -> adult N3 normal-norm gap
+2.0  focal or generalized slowing    -> abnormal-with-sleep gap (any age)
+1.0  adult & (focal or gen)          -> adult abnormal-with-sleep (fills both gaps)
+0.5  multi-day (≥24 h)               -> more full sleep cycles / more N3
```

Resulting tiers (ingest highest first):

| priority | n | who |
|---:|---:|---|
| 5.5–6.0 | 5,602 | adult, normal **and** abnormal-slowing (both gaps at once) |
| 4.0–4.5 | 28,344 | adult abnormal-with-sleep |
| 3.0–3.5 | 6,671 | adult-normal (N3) or pediatric abnormal |
| 1.5–2.5 | 2,710 | remaining normal (mostly pediatric) |
| 1.0 | 1,626 | pediatric normal, single-session |

`priority ≥ 4` = 33,946 recordings — the recommended first wave.

## Ingestion plan (future phase — not run here)

Pipeline per recording, in batches, **drop raw immediately after featurizing** (never mirror the
bucket):

1. **Select** a batch from `data/derived/expansion_candidates.csv`, highest `priority` first, balanced
   across age band × sex so no cell dominates (target ~150–250 recordings/batch).
2. **Pull raw BIDS EEG** for the batch: `rclone copy bdsp:bdsp-opendata-repository/EEG/bids/<site>/
   sub-<bdsp_id>/ …` into a scratch staging dir.
3. **Stage sleep** with morgoth2 `ss_hm_1` (the same stager used for the current cohort) → per-epoch
   stages; keep W/N1/N2/N3/REM epoch indices.
4. **Featurize** with `features/extract.py` (this repo's extractor) → segment- and recording-level
   features; append to `data/derived/segment_features*` / `recording_features*`.
5. **Drop the raw EEG** for the batch; record which `bdsp_id`+date were ingested so re-runs skip them.
6. After all batches, **rebuild the stage×age norms** — now with well-powered adult N3/REM — and
   re-run the abnormal discrimination stage-stratified.

**Batch sizing & disk.** Median candidate duration ≈ 21 h; ~9,900 are multi-day. A 24-h routine EEG
(~19–21 ch, ~200–256 Hz, EDF/BDF) is roughly **2–4 GB**; multi-day files can be 8–15 GB. So a
200-recording batch stages at roughly **0.4–0.8 TB peak scratch** (transient — freed after step 5).
The whole candidate set is ~942,700 EEG-hours; ingesting **only `priority ≥ 4` (33,946)** is the
efficient first target, and staging just the sleep-bearing segments keeps the featurized footprint
small even though raw transit is large.

**Suggested sequence.** Wave 1: `priority ≥ 5.5` (5,602 — dual-gap). Wave 2: rest of `priority ≥ 4`
(adult abnormal-with-sleep). Wave 3: `priority 3.0–3.5` adult-normal to top up adult N3 norms. Stop
once each age band × sex × stage cell clears the fitter's min-effective-n gate (~n=30); the tables
above show every adult cell clears it many times over, so Waves 1–3 are almost certainly sufficient.
