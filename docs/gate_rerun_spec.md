# Gate re-run — the spec, and what we do differently so there is no third run

## The governing rule

> **Persist every raw model output, at the finest granularity the model produces.
> Never collapse, never threshold, never short-circuit on the way in.
> Every reduction is post-processing, and post-processing is free.**

The first run violated this in three separate places, and each one cost us the whole run:

| what happened | where |
|---|---|
| the 3-class SLOWING softmax was collapsed to `1 − P(class_0)`; `class_1` (focal) and `class_2` (generalized) were **destroyed** | `scripts/31:162` |
| the window head ran at **5 s step**; Morgoth's own pipeline runs it at **1 s step** and feeds *that* to the EEG-level heads | `GATE_STEP` default `"5"` |
| Morgoth's EEG-level head **short-circuits to `probability = 0` without a forward pass** when no window's class column exceeds 1/3 — and we stored that zero as if it were a model output | `EEG_level_head.py:579,677` |

**We collapsed the model's output to save nothing.** The three probabilities we discarded are ~5 GB.
`segment_master` — which we *did* keep — is **59 GB**.

---

## The four decisions

### 1. Window step: **1 second.** Yes.

Morgoth's reference pipeline (`morgoth2/run_predict_linux.py`) runs the SLOWING head with
`prediction_slipping_step_second=1` and writes it to a directory literally named `pred_SLOWING_1sStep` —
which is then the input to the EEG-level FOC/GEN heads.

We ran at 5 s. Every `p_focal` / `p_generalized` in the study therefore came from a sequence **5× sparser**
than the heads were trained on (720 rows instead of 3,600 for a 60-minute record). The EEG-level head is a
CNN + Transformer with positional encoding over that sequence, so decimating it 5× rescales the positional
encoding and shifts the CNN's receptive field in wall-clock time.

It also made Morgoth's low-signal guard fire far more often than it should (fewer rows = fewer chances for
any row to exceed 1/3): **20.6% of our `p_focal` values are exactly 0.0** — the model never ran on them —
and those hard zeros propagate into every focal gate decision.

### 2. Keep every probability, every second. **Yes.**

Per 1-second window we persist the **entire raw softmax**:

| column | meaning |
|---|---|
| `t_start_s` | window start |
| `p_class0` | P(Others) |
| `p_class1` | P(Focal Slowing) |
| `p_class2` | P(Generalized Slowing) |

Nothing is derived on the way in. `p_slowing = 1 − p_class0` is a *view*, computed later, not a storage
decision. **Cost: 5.2 GB** — against the 59 GB of spectral features we already store.

These three are a softmax and therefore **mutually exclusive per window**. That is Morgoth's modelling
assumption, not ours, and it is why we also need (3).

### 3. An EEG-level probability every 15 seconds. **Yes — and it is not a hack.**

The EEG-level heads (`FOC_SLOWING_EEGlevel`, `GEN_SLOWING_EEGlevel`) are `CNNTransformerClassifier` models
that consume a **variable-length sequence of window class-probabilities** (T × 3) and emit **one sigmoid**.
They are two **separate models** (`class_idx=1` and `class_idx=2`), so their outputs are **independent** —
both can be high, which is exactly the co-occurrence the window softmax cannot express.

Feeding one 15-second segment is *supported by the code*, not a stretch of it:

- `CSVDataset.__getitem__` **pads any sequence shorter than 30 rows to 30** with its own column means.
  Short input is a designed-for case.
- The training augmentation `clip()` cuts sequences to **as few as 10 rows**. Short sequences were in the
  training distribution.
- `collate_fn` uses `pad_sequence` with explicit lengths — variable length is native.

At 1 s step a 15 s segment is **15 window rows** → padded to 30 → inside the trained regime.

So per segment we persist:

| column | meaning |
|---|---|
| `p_focal_seg` | independent P(focal slowing) for this 15 s |
| `p_gen_seg` | independent P(generalized slowing) for this 15 s |

**Cost: 0.18 GB.**

We also store a **wider-context variant** (`p_focal_ctx60`, `p_gen_ctx60`) — the same heads run on a
60-window window centred on the segment. It is more comfortably in-distribution and costs one extra forward
pass. Having both lets us *measure* the sensitivity to context length instead of arguing about it.

### 4. **No thresholding. No zeroing. Morgoth's guard is DISABLED and its verdict is recorded as a flag.**

This is the one that needs to be unambiguous, because I described it badly before.

Morgoth's `EEG_level_head.py` contains a short-circuit: if the max of that head's class column never exceeds
`1/n_classes` (= 1/3), it **returns `probability = 0` without running the model at all**. It is not a
post-hoc threshold on a real probability — the forward pass simply never happens, and a hard zero is written
in its place. That is where our 20.6% of exact-zero `p_focal` came from.

**We disable it.** The model runs on every segment and every recording, and we store its **actual sigmoid
output**. Alongside it we store a boolean:

| column | meaning |
|---|---|
| `guard_would_fire_focal` | would Morgoth's official short-circuit have zeroed this? |
| `guard_would_fire_gen` | same, generalized head |

This is strictly more information. Morgoth's official behaviour is exactly reproducible in post-processing
(`p_focal.where(~guard_would_fire_focal, 0)`), and we never destroy a number to get it. **No probability is
ever thresholded, rounded, clipped, or zeroed on the way to disk.**

---

## Also run, since the expensive part is already paid

EDF fetch + decode + preprocess + `.mat` write dominates the cost and is *already* being paid. Additional
heads are cheap at the margin. We therefore also run, at 1 s step, and keep raw:

- **NORMAL head** → `p_abnormal` per window (the manuscript uses recording-level `p_abnormal`; we have never
  had it per window).

Anything else (IIIC, SPIKES, BS) is a one-line addition if wanted — say so *before* launch, because the
whole point of this document is that there is no third run.

---

## Provenance, so we never have to guess again

The first run's `.done` sidecar records `worker` and `code_commit` but **not the hardware and not the gate
step**, which is why the cost of this re-run had to be *inferred* rather than read off. The new sidecar adds:

`gate_step_s`, `instance_type`, `n_gpus`, `morgoth2_commit`, `checkpoint_sha256` (per head),
`guard_disabled: true`, and the schema version.

## Safety

The re-run **cannot drift and cannot damage what we have**:

- Each recording is pinned to the **exact same source file** — `source_edf` + `sha256` are already in the
  existing sidecar, and the worker verifies the hash before processing. No re-resolution, so the
  "analyzed an EDF 10 years off" failure mode cannot recur.
- It writes to **new tables only** (`segment_gate/`, `window_gate/`). `segment_master`, `segment_summary`
  and the existing sidecars are never touched.
- A test fails if any raw model output is missing from the schema.

## Cost

| | |
|---|---|
| window forwards | 64.5M → **322M** (the 5× is the price of correctness) |
| dropped from the first run | sleep stager, multitaper featurisation, van Putten metrics |
| wall clock | **~12–20 h** (first run: 8.3 h) |
| spot cost | **~$60–150** |
| new data | **~5.5 GB** |
