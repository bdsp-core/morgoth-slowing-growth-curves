# Source-Data Cleanup Plan: Harvard EEG (BDSP) scalp EDF → morgoth H5

**Status:** proposal / design doc
**Scope:** scalp (surface) EEG recordings only. Stereo-EEG / intracranial (sEEG, iEEG, ECoG, depth/grid/strip) recordings are **out of scope and left byte-for-byte intact** — they are auto-detected and skipped (§1.1).
**Goal:** for scalp EEG, drop channels that carry no real signal (dead / unused / disconnected / duplicated reference) and convert the surviving signals from EDF to morgoth's H5 container (which has room for future annotations), saving disk and improving usability **without ever losing real signal**.

---

## 0. Cardinal principles (non-negotiable invariants)

1. **Never lose real signal.** When a channel's status is uncertain, it is *kept*, not dropped. All ambiguity resolves toward keeping data and/or routing the file to a manual-review queue.
2. **No resampling, no montage forcing, no re-referencing** in the archival converter. Each kept channel is written at its *native* sampling rate and in its *native* physical values. (The lossy MATLAB pipeline in `read_edf_write_h5/` that resamples to 200 Hz and collapses to a fixed 20-row montage is a *modeling* preprocessor, **not** what we do here.)
3. **Staged deletion.** The source EDF is deleted only after (a) all QC gates pass, and (b) an independently-verified backup of the original EDF exists. Every action is written to an append-only audit log.
4. **Reversibility until the last step.** Up to the delete, the pipeline is idempotent and re-runnable; a dropped channel can always be recovered from the retained EDF or its backup.
5. **Provenance is mandatory.** Every H5 records exactly which source EDF it came from, that EDF's checksum, which channels were dropped, and why.

---

## 1. Channel-usefulness detection

Two independent decisions: **(1.1)** is this file scalp or intracranial (file-level gate — decides whether we touch it at all), and **(1.2/1.3)** for scalp files, is each channel real or dead (channel-level keep/drop).

### 1.1 Scalp vs sEEG/iEEG classification (file-level gate)

Read only the EDF *header* (channel labels + count; no signal read needed).

Normalize each label: uppercase, strip a leading `EEG`/`POL`/`REF` token, strip trailing reference suffixes `-REF`, `-AVG`, `-A1`, `-A2`, `-M1`, `-M2`, `A1`, `A2`, and surrounding whitespace/dashes. (This mirrors the `strrep(...,'A1','')...` normalization in `read_edf_write_h5/step1_edf2h5.m`.)

Canonical 10-20 scalp set (two equivalent naming conventions, old ⇄ new):

```
Fp1 F3 C3 P3 F7 T3 T5 O1 Fz Cz Pz Fp2 F4 C4 P4 F8 T4 T6 O2      (old: T3/T5/T4/T6)
Fp1 F3 C3 P3 F7 T7 P7 O1 Fz Cz Pz Fp2 F4 C4 P4 F8 T8 P8 O2      (new: T7/P7/T8/P8)
```
plus common scalp extras that also count as scalp evidence: `Fpz Oz Nz F9 F10 P9 P10 T1 T2 A1 A2 M1 M2 FC1 FC2 CP1 CP2 ...`.

Intracranial evidence = contact-style labels: a letter-prefix + contact index that is **not** a 10-20 name, e.g. `LA1 LA2 ... RH1 RH2 ...`, `GRID12`, `STRIP4`, `LAT1`, `DEPTH...`, dashed bipolar contact pairs `LA1-LA2`, or an explicit `SEEG`/`ECOG`/`DEPTH`/`GRID`/`STRIP` token; typically 64-256 such channels.

Decision (evaluate in order):

| Condition | Classification | Action |
|---|---|---|
| ≥ 8 of the 19 canonical 10-20 labels present **and** intracranial-style labels are a minority | **scalp** | proceed to §1.2 |
| explicit intracranial token present, **or** ≥ 32 contact-style labels and < 8 of the 10-20 set | **intracranial** | **SKIP** — copy/leave EDF untouched, log as `skipped:intracranial` |
| anything else (mixed, sparse, non-standard) | **ambiguous** | **manual-review queue**; never auto-convert |

Log the classification, the matched-label count, and the label list for every file, so the gate itself is auditable and tunable on a pilot set.

### 1.2 Channel taxonomy — the KEEP list (for scalp files)

A channel is **kept** if it is a genuinely-recorded lead. Keep, regardless of amplitude, any channel whose (normalized) label matches:

- **Scalp EEG:** the full 10-20 set above and any extended-10-20 / high-density scalp position.
- **ECG / EKG:** `ECG`, `EKG`, `EKG1/EKG2`, `ECGL/ECGR`.
- **EOG (eye movement):** `EOG`, `LOC`, `ROC`, `E1`, `E2`, `LEOG`, `REOG`.
- **EMG:** `EMG`, `CHIN`, `CHIN1/2`, `LAT/RAT` (leg), submental.
- **Any other physiologic lead present with real signal:** respiratory belts, airflow, SpO2/pleth, snore, photic/`DC`/trigger *if it carries a real waveform*, etc.

Membership in the keep-list only *protects* a channel from being dropped on name grounds; a keep-listed channel is still dropped **only** if §1.3 proves it is physically dead (a flatlined `C3` is still dead). A channel **not** in the keep-list is dropped only if §1.3 also flags it — an unrecognized label with genuine signal is kept and flagged for review (superset-preserving).

### 1.3 DROP criteria — detectable rules + thresholds

Compute per channel from the signal, working in **µV** (convert EDF physical units to µV first) and on the **full record** (or, for very long LTM files, on ≥ 20 evenly-spaced 60 s probe windows — dead channels are dead throughout). Let `x` be the channel samples, `dmax/dmin` the EDF digital extremes (`+32767 / -32768` for int16), `pmax/pmin` the header physical extremes.

| # | Failure mode | Detector | Drop threshold |
|---|---|---|---|
| D1 | **All-NaN / empty** | `fraction(isnan)` | ≥ 0.99 |
| D2 | **Flatline / constant** | `fraction(diff(x)==0)` (consecutive-equal-sample fraction) | ≥ 0.999 over the record |
| D3 | **Near-zero variance (dead)** | robust scale `1.4826·MAD(x)` **and** `std(x)` | both < 0.5 µV (electrically dead; real EEG is ~5-100 µV) |
| D4 | **Railed / saturated (stuck to rail)** | fraction of samples at a digital rail (`x_digital∈{dmin,dmax}`) or at `pmin/pmax` | ≥ 0.20 of samples pinned |
| D5 | **Disconnected / floating electrode** | line-noise dominance: `bandpower(f0±1Hz)/bandpower(0.5–70Hz)` at mains `f0∈{50,60}` **and** low physiologic content `bandpower(1–20Hz)` | line-fraction ≥ 0.8 **and** 1-20 Hz power < 1 µV² |
| D6 | **Pure duplicate / mirrored reference** | max abs Pearson `|corr(xi,xj)|` against every other kept channel after 0.5-40 Hz bandpass; and exact-sample equality check | `|corr| ≥ 0.999` **or** bit-identical samples → drop the *redundant copy* (keep one representative) |
| D7 | **DC-only / drift-only** | fraction of total power below 0.1 Hz | ≥ 0.99 (no AC signal) |

Rules to prevent false drops:

- **Unanimity for keep-listed leads.** A keep-listed channel (§1.2) is dropped only if it trips a *hard* deadness rule (D1, D2, D3, or D4). Line-noise/duplicate heuristics (D5, D6, D7) alone are **not** sufficient to drop a keep-listed EEG/ECG/EOG channel — they route it to review instead. (A physically-present but noisy electrode is still real data.)
- **Duplicate handling (D6) never deletes unique information:** when two channels are ≥ 0.999 correlated, keep the one with the more informative/standard label (prefer a 10-20 name over a raw reference like `A1`/`REF`), and log the dropped twin as `dropped:duplicate_of:<kept>`.
- **Thresholds are pilot-calibrated.** Run §1.4 in *dry-run* on a labeled sample of ~200 scalp files, hand-audit the proposed drops, and freeze thresholds only after false-drop rate on real channels is 0.

### 1.4 Per-file auto-classification algorithm

```
classify_and_plan(edf_path):
    hdr = read_edf_header(edf_path)
    kind = scalp_or_intracranial(hdr.labels)          # §1.1
    if kind == "intracranial": return SKIP(edf_path)  # keep intact
    if kind == "ambiguous":    return REVIEW(edf_path)

    keep, drop = [], []
    sig = read_edf_signals(edf_path)                   # native Fs per ch
    for ch in hdr.channels:
        listed = in_keep_list(ch.label)                # §1.2
        flags  = deadness_flags(sig[ch])               # §1.3 -> {D1..D7}
        hard   = flags & {D1, D2, D3, D4}
        soft   = flags & {D5, D6, D7}
        if listed:
            if hard:            drop.append((ch, hard))
            elif soft:          REVIEW_channel(ch, soft) ; keep.append(ch)
            else:               keep.append(ch)
        else:                                           # unrecognized label
            if hard or soft:    drop.append((ch, flags))
            else:               keep.append(ch) ; flag_unknown_kept(ch)
    if len(keep) == 0: return REVIEW(edf_path)          # never emit empty file
    return PLAN(keep, drop)
```

Output per file: a JSON *conversion plan* (`keep[]`, `drop[]` each with reason codes, classification, thresholds/version used). The plan is reviewable and archived alongside the H5.

---

## 2. EDF → H5 conversion (morgoth container)

### 2.1 Target format

Morgoth's H5 layout (from `infer_sleep_staging.py` `_load_h5` and the morgoth2 reader spec):

```
root.attrs['sampling_rate']     int    Hz   (native; NOT resampled)
signals/<CH>                    dataset  shape (T, 1)  float64   units: Volts (V)
annotations/                   group    (reserved; empty for now — room for stage/IIIC/events later)
```

`_load_h5` iterates `signals/<name>`, reads `[:,0]` as float64 V, uppercases labels (and maps `ECG`→`EKG`). We conform to that contract exactly so existing morgoth heads read our files unchanged, while keeping the *superset* of channels (not just the modeling montage).

### 2.2 What is preserved

- **Signal:** each kept channel's physical values, converted to Volts (EDF physical is usually µV → multiply by 1e-6), stored float64 with **no resampling / filtering / re-referencing**.
- **Sampling rate:** `root.attrs['sampling_rate']`. If channels have heterogeneous rates in the EDF, store the common rate; per-channel rates are written to `signals/<CH>.attrs['fs']` and the file is flagged for review if rates differ among *kept* channels.
- **Labels & units:** original label in `signals/<CH>.attrs['orig_label']`; `.attrs['unit']='V'`; scale factor used in `.attrs['edf_physical_unit']`.
- **Start time & timing:** `root.attrs['start_time']` (ISO-8601 from EDF `startdate`+`starttime`), `n_samples`, `duration_sec`.
- **Provenance (mandatory):** `root.attrs['source_edf']` (basename), `root.attrs['source_edf_sha256']`, `root.attrs['dropped_channels']` (JSON: label→reason code), `root.attrs['classification']` (`scalp`), `root.attrs['converter_version']`, `root.attrs['conversion_utc']`, `root.attrs['plan_json']` (embedded conversion plan).

### 2.3 Converter (pseudocode)

```
edf_to_h5(edf_path, plan, out_path):
    hdr, sig = read_edf(edf_path)               # MNE or pyedflib; physical units
    with h5py.File(out_path + ".tmp", "w") as h5:
        h5.attrs["sampling_rate"] = int(round(common_fs(plan.keep)))
        h5.attrs["start_time"]    = iso8601(hdr.start)
        h5.attrs["source_edf"]        = basename(edf_path)
        h5.attrs["source_edf_sha256"] = sha256(edf_path)
        h5.attrs["dropped_channels"]  = json({ch.label: reasons for ch,reasons in plan.drop})
        h5.attrs["classification"]    = "scalp"
        h5.attrs["converter_version"] = VERSION
        h5.attrs["conversion_utc"]    = utcnow()
        h5.attrs["plan_json"]         = json(plan)
        g = h5.create_group("signals")
        for ch in plan.keep:
            v = sig[ch].astype(float64) * to_volts(ch.unit)   # µV -> V exactly
            d = g.create_dataset(ch.label.upper(), data=v.reshape(-1,1),
                                 compression="gzip", compression_opts=4, shuffle=True)
            d.attrs["orig_label"] = ch.label
            d.attrs["unit"]       = "V"
            d.attrs["fs"]         = float(ch.fs)
        h5.create_group("annotations")          # reserved, empty
    atomic_rename(out_path + ".tmp", out_path)  # never leave a partial .h5
```

Notes: gzip+shuffle on float64 gives solid lossless compression on band-limited EEG. Because EDF physical values derive from `int16 * gain + offset`, they are exactly representable in float64, and the µV→V scale is exact — so §3 Gate A should be essentially bit-exact.

---

## 3. QC — guaranteeing no signal loss (gates before any deletion)

All four gates must pass for a file before it is eligible for staged delete. Any failure → keep EDF, quarantine the H5, log, and route to review.

### Gate A — per-kept-channel reconstruction fidelity (exactness)
Re-read the source EDF and the new H5, align each kept channel, convert both to the same unit (µV), and compare:
- **max-abs-diff** per channel ≤ `1e-6` µV (i.e. bit-exact up to float rounding).
- **MSE** per channel ≤ `1e-12` µV².
- **length match:** identical sample count per channel.
Because we do not resample or filter, these are effectively zero; any nonzero MSE indicates a real bug and blocks deletion.

### Gate B — batch summary-statistic parity
Independently recompute from EDF-kept-channels vs H5 and require agreement:
- per-channel **mean, std, min, max, median, MAD** — relative diff ≤ `1e-9`.
- per-channel **band powers** (δ 1-4, θ 4-8, α 8-13, β 13-30 Hz, and line 50/60 Hz) — relative diff ≤ `1e-6`.
- **channel-set check:** `keep` set in H5 == plan; `drop` set absent; no unexpected additions.
Aggregate these into a batch report (one row per file) so drift across a batch is visible at a glance.

### Gate C — morgoth-inference parity
Run a morgoth head on EDF-derived input and on H5-derived input for the **same** file and confirm predictions match. Reuse `infer_sleep_staging.py`'s own `_load_edf` and `_load_h5` so both paths share identical downstream preprocessing (MNE bandpass+notch, ÷100, 10 s windows) — the only difference under test is the container.
- **argmax agreement:** identical predicted class on ≥ 99.9% of windows (target 100%).
- **probability parity:** max per-class softmax abs diff ≤ `1e-3`; mean ≤ `1e-4`.
This is the end-to-end guarantee that dropping dead channels changed nothing a model consumes. (Dead channels contribute ~zero; if a drop *did* change a prediction, the channel was not dead — the file is quarantined for review.)

### Gate D — checksums, backup, staged delete, audit log
1. Record `sha256(source_edf)` and `sha256(h5)`.
2. Confirm a **verified backup** of the original EDF exists on independent storage (re-hash the backup copy and match — not just "a file exists").
3. **Staged delete:** move the source EDF to a time-boxed `quarantine/` (soft-delete) — not `rm`. Only after Gates A-C pass **and** the verified backup matches. A separate, later sweep hard-deletes quarantined EDFs older than the retention window (e.g. 30 days) once the batch report is signed off.
4. **Audit log (append-only):** one JSON line per file — `{source_edf, sha256_edf, h5_path, sha256_h5, backup_path, sha256_backup, classification, kept[], dropped[], gates:{A,B,C,D}, bytes_before, bytes_after, converter_version, timestamps}`.

**Delete predicate:** `deletable = A && B && C && backup_verified && quarantine_ok`. Nothing else deletes source data.

---

## 4. Rollout, space savings, batching

### 4.1 Space-savings estimate
Typical BDSP scalp EDF: **30-50 channels**, of which only **~19-25** are genuinely useful (10-20 set + EKG + a few EOG/EMG). Two independent savings sources:
- **Channel pruning:** dropping ~10-25 of 30-50 channels removes ~30-50% of samples.
- **Lossless compression** (gzip+shuffle on band-limited float64): typically ~2-3× on the retained signals.

Rough combined estimate: **~40-60% fewer channels**, and with compression a converted H5 commonly lands around **40-55% of the source EDF size** (i.e. ~45-60% saved). Actual numbers must be measured on the pilot batch and reported per-batch from the audit log (`bytes_before`/`bytes_after`), not assumed.

### 4.2 Rollout phases
1. **Pilot (dry-run):** run §1.4 classification + drop-planning on ~200 scalp files with **no writes**; hand-audit every proposed drop; freeze thresholds only at 0 false drops on real channels. Confirm intracranial gate (§1.1) skips all sEEG/iEEG in the sample.
2. **Convert-only:** produce H5 + run Gates A-C on a first real batch; **no deletes**; review batch report.
3. **Staged delete enabled:** enable Gate D quarantine on files that passed A-C, with the hard-delete sweep still held for manual sign-off.
4. **Scale out:** batch the full corpus in chunks (e.g. per BDSP site/date shard), each producing an independent batch report + audit-log segment.

### 4.3 Batching & ops
- Idempotent per file (skip if H5 exists and its `source_edf_sha256` matches); safe to resume after interruption.
- Parallelize across files (I/O-bound); one worker per file, bounded pool.
- Per-batch deliverables: conversion plans, H5 files, batch QC report (A/B/C stats), audit-log segment, quarantine manifest.
- Fail-safe defaults: any error, ambiguity, or gate failure keeps the source EDF and never deletes.

---

## Summary (5 lines)

1. For **scalp** EEG only (intracranial auto-detected by contact-style labels / channel count and left byte-for-byte intact), drop channels carrying no real signal and convert EDF→morgoth H5 (`signals/<CH>` (T,1) float64 V + `attrs['sampling_rate']` + reserved `annotations/`), at native rate with full provenance.
2. **Keep** the 10-20 scalp set, ECG/EKG, EOG, EMG, and any genuinely-recorded lead; **drop** only channels proven dead: all-NaN, flatline, near-zero-variance, railed/saturated, disconnected line-noise-only, DC-only, or exact duplicates.
3. **No resampling / re-referencing / filtering** in conversion — retained signal is preserved bit-exactly (EDF physical values are exact in float64).
4. Four **QC gates** must pass before any delete: (A) per-channel exact reconstruction, (B) batch stat + band-power parity, (C) morgoth-inference parity, (D) checksums + verified backup + staged quarantine-delete + append-only audit log.
5. Expect **~45-60% space saved** (channel pruning + lossless compression), rolled out pilot → convert-only → staged-delete → scale-out, always defaulting to keep-the-source on any doubt.

### Channel keep/drop rule (one-liner)
**KEEP** every channel whose normalized label is a scalp 10-20 / ECG / EOG / EMG / other physiologic lead **or** that shows genuine physiologic signal; **DROP** a channel only when it is proven dead — keep-listed leads require a *hard* deadness flag (all-NaN ≥0.99, flatline ≥0.999, robust-std <0.5 µV, or rail-pinned ≥0.20); non-listed channels also drop on soft flags (line-noise-only, DC-only, or ≥0.999-correlated duplicate); everything uncertain is kept and sent to manual review.

### QC gates (delete predicate)
`deletable = A(max|Δ|≤1e-6 µV, MSE≤1e-12) && B(stat rel-diff≤1e-9, bandpower rel-diff≤1e-6, channel-set exact) && C(argmax match ≥99.9%, prob |Δ|≤1e-3) && backup_verified(re-hashed) && quarantine(soft-delete, not rm)` — all true, logged, and signed off before any hard delete.
