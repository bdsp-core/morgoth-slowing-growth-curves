# Validation plan — what it takes to support "equal or greater value than a clinical neurophysiologist"

The normative foundation and detection are established (Figures 1–2), and detection survives the
report-pairing audit. **Severity grading is a null result** (V1). The remaining work is what licenses the
*comparative* claim. Five items, in priority order. See `docs/methods_audit.md` for what is verified,
what is assumed, and what is broken.

---

## V1. Recalibrate severity and prevalence — **DONE, and it is a NULL result**

**What we did.** Fixed five real defects: (1) `peak_z` was a *maximum* over hundreds of segments (max 19.4 =
artifact) -> robust p90; (2) the adjective extractor returned the first word in *table order* anywhere in the
slowing context, ignoring negation -> clause-scoped, negation-aware, modifier *nearest* to "slow";
(3) focal severity was scored on a whole-head statistic -> scored in the max-deviation region;
(4) scoring ran over *all* segments, though abnormal recordings are only 44.5% wake, so the score was
confounded with how much the patient slept -> restricted to W/N1 (required building abnormal segment stages,
`scripts/87`); (5) 17.2% of recordings carried a report **broadcast from a sibling study** of the same
patient -> restricted to cleanly-paired recordings (`scripts/88`).

**Result.** Severity **rho = 0.050 (p = 0.17, n = 753)**. Null. Prevalence vs the reader's frequency word:
rho = 0.077 (p = 3.3e-6, n = 3,626) — significant, clinically negligible.

**It is not a search failure.** `scripts/89_severity_axis_sweep.py` swept **168 combinations** (7 features x
4 statistics x {raw, z} x {generalized, focal, all}). Largest |rho| anywhere = **0.179**, which fails
Bonferroni (0.05/168 = 3.0e-4; best p = 6.8e-4) and has the **wrong sign**. Raw ~= z (0.159 vs 0.179), so it
is not a normalization artifact.

**Two live hypotheses, not separable with these data.**
- *Wrong axis.* Clinicians grade diffuse slowing chiefly by **posterior dominant rhythm frequency** (8-9 Hz
  mild, 6-7 moderate, <5 severe). We never measure PDR. A regex extraction of PDR Hz from report text was
  **invalid** (non-monotonic: mild 6.98, moderate 9.09, marked 7.29 Hz; it captured slowing and photic-driving
  frequencies). **Next step: measure PDR from the signal** — occipital peak frequency in eyes-closed wake —
  and test it as the severity axis. This is a real analysis, not a regex.
- *Unreliable adjective.* Cannot be assessed without the inter-rater ceiling (V2).

**Consequence for the paper.** We claim detection (AUROC 0.85-0.88) and dose-response across report strata
(rho 0.50-0.55). We **do not** claim severity grading. Manuscript SS3.4b and SS5 now say so explicitly.

---

## V2. The human ceiling — use the **MOE dataset** (experts already marked slowing)

**Why it is indispensable.** We report agreement *with the report* (band 0.74, side 0.87). We have never
established what **two neurophysiologists agree on with each other**. Published inter-rater κ for background
abnormality/slowing is modest (~0.4–0.6). If experts agree at 0.7 on band, our 0.74 is *at the human ceiling*
— a major claim. Without this anchor, "equal value" is not merely unproven, it is **unfalsifiable**.

**Plan.** Use the **MOE dataset**, in which multiple experts already marked slowing, to compute:
- pairwise inter-rater agreement / Cohen's–Fleiss κ for: slowing present/absent, focal vs generalized, band,
  side, and severity grade;
- the **expert-vs-consensus** ceiling (each rater vs the majority of the others);
- our model vs the same consensus, scored identically.

**The headline becomes:** *"our agreement with the consensus read is X, against an expert-vs-consensus ceiling
of Y"* — which is the only defensible form of the comparative claim.
*(Needed: location/format of the MOE annotations and the mapping from MOE recordings to `bdsp_id`.)*

---

## V3. Blinded head-to-head — the actual demonstration

Component metrics (AUROC, per-axis agreement) never demonstrate *value*. The definitive test:

1. Sample N ≈ 150–200 recordings gated in by Morgoth (stratified: focal / generalized; wake-only /
   sleep-accentuated; a range of deviation magnitudes), plus a set of report-normal controls.
2. For each, prepare **two descriptions**: (a) the slowing sentence(s) from the original clinical report,
   (b) our generated sentence. Strip all identifying formatting; randomize order; blind the raters to source.
3. Independent neurophysiologists (≥2, not the original readers) rate each description on: **accuracy**,
   **completeness**, **localization correctness**, **usefulness for management**, and give a forced-choice
   preference (A / B / equivalent), while viewing the raw EEG.
4. Primary endpoint: **non-inferiority** of the generated description on a preference/utility scale.
   Secondary: where our description is *preferred* (hypothesis: sleep-accentuated and quantitatively graded
   cases) and where it fails (hypothesis: rare posterior foci, morphology-dependent band calls).

This converts "same value or more" from an assertion into a measured result.

---

## V4. The "adds value" analyses (clarification — feasible today, no new labels)

The claim that we detect slowing the reader *under-reports* is currently only a hint (in the dose-response,
recordings called abnormal **without slowing named** still deviate by ≈ +0.4 SD). Three concrete analyses turn
that hint into evidence, all using data already in hand:

**V4a — Within-subject wake → sleep test.**
Reports systematically under-declare slowing *in sleep* (it is hard to judge "how much delta is too much" in
N2/N3 by eye). Take recordings whose report flags abnormality **in wake only** and which contain scored sleep.
Compute the stage-specific deviation z in W and in N2/N3 for each. If the abnormality is truly present in
sleep and merely unnamed, those recordings should show **elevated sleep-stage z relative to clean-normals of
the same age and stage**, despite the report never mentioning sleep slowing. This is a **within-subject**
comparison, so it cannot be explained by patient-level confounding. Sign: sleep z > 0 and > matched controls.

**V4b — Convergent validity for the "excess" detections.**
Take report-**normal** recordings with **high sleep-stage deviation** (top decile). If these are true
abnormalities the reader missed — rather than model noise — they should also look abnormal on **independent**
markers we did not use to select them: higher Morgoth p(abnormal); absent/attenuated posterior dominant
rhythm; reduced sleep spindles / K-complexes; and enrichment for downstream clinical outcomes if linkable.
Concordance across independent markers is what makes an "excess detection" credible without a gold standard.

**V4c — Dose-response across report strata.** ✅ **Done** (Figure 3): z rises 0 → +0.4 → +1.4 across
clean-normal → abnormal-without-slowing-named → abnormal-with-slowing-named. V4a and V4b are the two
remaining legs of the same argument.

Together V4a–c support the reframing: *not "reproduce the report", but "a stage-aware normative complement
that is most valuable exactly where expert reading is weakest."*

---

## V5. Report-to-recording pairing — repair is heuristic (NEW, from the 2026-07-09 audit)

`EEGs_And_Reports.csv` is an EEG x report join made at the **patient** level: one report is stamped onto a
mean of 2.9 EEGs (max **170**) of that patient. Our `(bdsp_id, date)` join therefore selected the right *row*
with, 17.2% of the time, the wrong *text*. `scripts/88_report_pairing_audit.py` assigns each report to the
EEG nearest it in time and writes `clean_pair` to `data/derived/report_pairing.parquet`.

**This is a heuristic.** `|time_diff|` for unambiguously-owned reports has median 14.2 h, p90 203 h — it is an
order-to-study offset, not a study timestamp. **Ask BDSP for a true report<->study key.** Until then:
- filter on `clean_pair` for anything derived from report text;
- detection is insensitive to it (all AUROCs within bootstrap CI, `results/detection_pairing_sensitivity.md`);
- see `docs/methods_audit.md` for the full verified/assumed/broken accounting.

Two further defects found in the same audit: `bdsp_id` is a **patient-at-site key, not a recording key**
(352 patients have >=2 recordings, collapsed by `drop_duplicates("bdsp_id")` and by the date-stripped feature
tables); and per-stage "best feature" AUROCs are selected and reported on the same data (needs nested CV).

---

## Also outstanding
- Figure 5 pipeline schematic — artist brief written (`docs/figure5_pipeline_schematic_brief.md`).
- Region localization is weak (macro-F1 0.23; temporal 0.54, posterior <0.1). Either narrow the claim to
  **side + temporal**, or run region-stratified collection.
- Table 1 — done (`results/table1.md`).
