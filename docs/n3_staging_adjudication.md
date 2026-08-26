# Adjudicating the N3 staging-circularity charge (review item C146-a)

## The charge

Shafi, on Figure 4 panel (2,2): *"How is this being classified as N3 sleep? Is that description meaningful
when diffuse encephalopathy is present? This panel raises MAJOR concerns about the sleep classification in
patients with generalized encephalopathy."*

The concern is circular reasoning, and it is a fair one. Our sleep stager keys sleep depth on slow-wave
content — the same delta our deviation score measures. So a pathologically slow **wake** segment can be
misclassified as deep sleep, then scored against deep-sleep norms. Any delta-based check inherits the
circularity and cannot break it.

## Why the existing N2 test does not simply extend

`scripts/95b` adjudicates the same charge for N2 with a delta-free arbiter: the **sleep spindle**, an 11–16 Hz
sigma burst that is an independent physiologic hallmark of N2 and does not depend on delta. Restrict both
groups' N2 to spindle-positive segments; if the case-vs-control elevation survives, the staging was real.

**That arbiter does not transfer to N3, and it would be wrong to apply it there.** Spindles are the defining
graphoelement of *N2*. In N3 they become sparse and then absent as slow-wave activity dominates — their
absence is part of what *makes* an epoch N3. Requiring spindles inside N3 epochs would therefore reject
correctly-staged N3, and "spindle-verified N3" is not a coherent quantity.

## The right test: verify sleep, not sleep depth

Read the charge precisely. It is not *"is this N3 rather than N2?"* — it is *"is this patient asleep at all,
or is this an encephalopathic waking record being called sleep?"* That question **is** answerable without
delta, by using spindles structurally rather than pointwise:

> An N3 segment is **sleep-verified** if it lies inside a maximally contiguous non-wake block (N1/N2/N3/REM)
> that contains at least one **spindle-positive N2** segment.

A spindle anywhere in the block establishes that the patient was genuinely asleep during that stretch, on
evidence entirely independent of delta. The encephalopathic-wake alternative predicts no spindles anywhere in
the block, because an awake encephalopathic patient does not generate them. Restricting both arms to
sleep-verified N3 and re-running the case-vs-control contrast then adjudicates the charge on the same logic as
the N2 test, without demanding an N2 marker inside N3.

Secondary strengthening, if wanted: require the spindle-positive N2 segment to be within a bounded distance
(e.g. one sleep cycle, ~90 min) of the N3 segment rather than anywhere in the block.

## What implementing it requires

1. **An N3 normalisation reference.** `scripts/95` currently emits `v4a_ref_n2.npz` only — age-indexed `mus`
   and `sds` for N2. The N3 contrast needs the same grid computed on N3, written as `v4a_ref_n3.npz`.
2. **Block construction in `scripts/95b`.** Group each recording's staged segments into maximally contiguous
   non-wake runs, mark blocks containing a spindle-positive N2 segment, and keep the N3 segments inside them.
   The spindle detection, EDF alignment and per-segment z machinery already exist and need no change.
3. **A full run.** Both arms, EDFs pulled one at a time. The N2 run is the cost model.

## Status

**Run and reported.** Both items above are implemented (`scripts/95` emits the N3 reference; `scripts/95b`
builds the non-wake blocks and marks the spindle-positive ones) and the full run is done.

Of 665 staged N3 segments, **320 (48%)** sit inside a spindle-verified sleep block. On those, cases still
separate from controls: log_delta AUROC **0.767 [0.645, 0.870]** (p = 2e-4), DAR **0.784 [0.671, 0.884]**
(p = 7e-5), on 41 cases and 28 controls. The secondary strengthening (requiring the spindle within ~90 min
rather than anywhere in the block) was not applied; the block-level criterion is what the numbers reflect.

Results: `results/v4a_wake_sleep.md`, section "Sleep-verified N3". Written up in manuscript §3.8, which is
now entitled to describe it as done. §2.11 continues to carry the framing answer — a deviation is a
statistical statement, not a diagnosis — which addresses the *interpretation* half of Shafi's comment; the
run above addresses the *staging* half.
