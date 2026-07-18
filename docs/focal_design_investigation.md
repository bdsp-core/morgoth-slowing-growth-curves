# Focal-slowing detection on Sandor_100: design investigation

**Author:** Fable · **Date:** 2026-07-18
**Scope:** why our focal detector "loses" to human experts on the external Sandor_100 benchmark, and what
design/training changes fix it. Prototyping in `scripts/focal_design_probe.py` (scratch — not committed to the
production pipeline). Figures in `figures/scratch/`.

---

## TL;DR — the puzzle was a corrupted ground-truth label, not an algorithm-design failure

The premise ("experts detect focal slowing far better than every automated method; best model AUROC ~0.77 /
~7% experts-under; SCORE-AI 0.61; Morgoth 0.61") is an **artifact of a misaligned `majority` column** in
`FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx`. Every prior experiment (scripts 64/65/66, the diagnostic,
and the manuscript's Sandor focal validation) used that column as ground truth.

The sheet also carries the 14 individual expert votes (`expert_0..expert_14`). Their majority is the real label.
**`majority` disagrees with the expert-vote majority on 23 of 100 recordings**, and the disagreements are not
borderline — e.g. ID002, ID048, ID053 have **11/11 experts voting focal but `majority`=0**; ID077 has **0/11
experts but `majority`=1**.

Re-scored against the corrected label (expert-vote majority), on the same 98 recordings:

| model | AUROC vs `majority` (old) | % experts under (old) | **AUROC vs expert-vote (correct)** | **% experts under (correct)** | sens @ experts' 0.88 spec |
|---|---|---|---|---|---|
| our current focal head | 0.736 | 0% | **0.946** | **79%** | 0.76 |
| Morgoth (foundation gate) | 0.609 | 7% | **0.974** | **93%** | 0.96 |
| SCORE-AI | 0.605 | 0% | **0.878** | **29%** | 0.68 |

Experts operate at ~0.71 sensitivity / ~0.88 specificity. Against the correct label **our head already
matches the experts** (sens 0.76 ≥ 0.71 at their specificity; 79% of experts fall under our ROC, target was
>50%), and Morgoth clearly exceeds them. The "0.77 AUROC / 7% under" ceiling never existed. See
`figures/scratch/focal_label_before_after_roc.png`.

**This is the finding that matters.** The concrete design experiments below (finer spatial focality, window
selection, wake-conditioning, morphology) do **not** move the needle once the label is fixed — the trained
head is already at the expert ceiling, and the only thing that beats it is the Morgoth foundation model.

### Evidence the label — not the algorithm — is the problem (three independent lines)

1. **Two fully independent detectors both track the expert votes, not `majority`.** SCORE-AI (commercial) and
   Morgoth (foundation model) are computed with no access to either label. Their focal scores achieve
   AUROC 0.878 and **0.976** against the expert-vote majority but only 0.616 / 0.624 against `majority`. A
   label that an independent model predicts at 0.976 is the real label; the one it predicts at 0.62 is noise.
2. **On the 23 disagreement rows, Morgoth sides with the experts** (mean focal score 0.73 when experts say
   focal, 0.21 when they don't) — i.e. the model and the experts agree, and only `majority` dissents.
3. **Raw EEG confirms it, ground-truth-independently** (`figures/scratch/focal_mislabel_confirmation.png`):
   ID002/ID048 (11/11 experts focal, `majority`=0) show asymmetric temporal/irregular slowing; ID077 (0/11,
   `majority`=1) looks normal; ID099 (correctly labeled) shows an unambiguous left-frontal Fp1-F7 focus.

The corruption is **specific to the focal sheet**: the parallel `GenSlowingOutput_…xlsx` has **0/100**
disagreements and Morgoth scores 0.951 against either label. So a derived/joined `majority` column was
scrambled when the focal output workbook was assembled; the generalized workbook is fine. It is not a simple
row-shift (best shifted match is worse than identity) — it is a scattered 23-row corruption.

### Manuscript impact
- Commit `4d0d9a6` ("our focal detector beats SCORE-AI and Morgoth") is **reversed** by the fix: correct
  ranking is Morgoth 0.974 > ours 0.946 > SCORE-AI 0.878.
- The in-domain OccasionNoise focal result (71% experts-under) is **not** affected — that eval reads the expert
  vote matrix directly (`wide`) and never touches a `majority` column. Only Sandor focal is contaminated.

---

## (a) Error analysis

### Against the OLD (corrupted) label — what created the illusion
The apparent "false negatives" our head scored low were largely recordings the experts called **non-focal**
(ID077 0/11, ID011 2/11, ID096 2/11 …) that the corrupted `majority` had flipped to focal — so our correct
low scores were counted as misses. Symmetrically, the apparent high-scoring "false positives" (ID002 11/11,
ID048 11/11, ID053 11/11) were **true focal** recordings the corrupted label had flipped to negative.

### Against the CORRECT label — the genuine residual errors (small)
Re-running the error analysis with the expert-vote majority (`scripts/focal_design_probe.py errors`, then
`fusion`/`design`), the residual misses are almost all **borderline-consensus** recordings where the experts
themselves split 6–7/11 (ID016, ID070, ID042, ID063, ID036 — expert mean 0.55–0.64). There is no cluster of
strong-consensus focal cases our head misses.

Residual **false positives** are the more informative errors:
- **ID100** (our head 0.81, but 1/11 experts): the raw EEG at the epoch we fire on is dominated by
  **frontopolar eye-movement / blink artifact** (large bilateral Fp1/Fp2 deflections) mistaken for frontal
  focal delta. A real, addressable specificity leak.
- **ID098, ID035, ID085** (our head 0.71–0.76, ≤5/11 experts): high band-power focality that the experts
  discounted — consistent with drowsy/asymmetric-normal-variant activity rather than pathological focal
  slowing.

So the only mechanistic design weakness that survives the label fix is **artifact/eye-movement robustness at
the frontopolar chain**, and it costs a handful of high-specificity false positives.

---

## (b) Design changes tested and their measured effect (corrected label)

All evaluated on Sandor against the expert-vote majority (n=98, 25 focal). "%under" = fraction of the 14
experts whose leave-one-out operating point falls under the model ROC.

### Single, unsupervised, purely-relative focal statistics (`probe design`)
These are within-recording contrasts (reference/scale/age-invariant → domain-robust by construction):

| statistic | AUROC | %under |
|---|---|---|
| homologous-pair asymmetry, max-pair p90 (log_delta, all stages) | **0.815** | 7% |
| homologous-pair asymmetry (log_TAR) | 0.779 | 7% |
| per-channel focality = peak−median channel (log_delta) | 0.409 | 0% |
| field-coherent focality (focus + neighbour above median) | 0.405 | 0% |
| spatial persistence of the focus (modal argmax fraction) | 0.677 | 0% |

- **Finer per-channel "focality" (peak−median channel) is near-useless (≈0.40).** This is the same signal the
  6-region peak−median encodes, at electrode resolution — making it finer does **not** help. It behaves at
  chance because peak-minus-median tracks overall amount and single-channel artifact, not focal pathology.
- **Homologous L–R asymmetry is the one hand-crafted relative feature that carries focal signal** (0.82), but
  even it cannot reach the high-specificity corner alone (7% under, sens 0.44 at experts' spec).
- No single statistic approaches the trained head (0.946) or Morgoth (0.974).

### Window / epoch selection (lever 3) and state conditioning (lever 4)
- **Wake-conditioning does not help.** Recomputing every relative feature on wake-only segments was **equal or
  worse** than all-stage (asymmetry 0.750 wake vs 0.815 all-stage). Focal slowing in these EMU recordings is
  expressed across stages, and dropping to wake-only just loses statistical power. (Median recording is 25 min
  / 46% wake; 23/98 are <20% wake, so wake-gating also throws away most of some recordings.)
- **Spatial-persistence gating (require the focus at the same channel across epochs) did not add discrimination**
  (persist 0.68, persist×contrast 0.65). It is a sensible artifact filter in principle but is not the missing
  signal here.
- **Top-k "find the focal epoch" pooling is already what the head's p90/max aggregation does**, and the head is
  already at ceiling — so there is no dilution problem to fix on this benchmark.

### Supervised fusion — is there residual headroom over the current head? (`probe fusion`)

| model | AUROC | %under | sens @ experts' spec |
|---|---|---|---|
| current head (trained spectral/region) | 0.946 | 79% | 0.76 |
| + homologous-asymmetry (rank-avg) | 0.919 | 43% | 0.72 |
| + Morgoth (rank-avg) | **0.978** | **86%** | 0.96 |
| + asymmetry + Morgoth | 0.960 | 64% | 0.88 |
| Morgoth alone | 0.974 | 93% | 0.96 |

- Adding more **hand-crafted spatial features actually hurts** (asymmetry drags the head down to 0.919/43%).
  This corroborates the project's prior conclusion that stacking spectral/spatial features caps out — and shows
  that on the corrected label it isn't even neutral, it's negative.
- The **only** thing that improves on our head is the **Morgoth foundation-model score**, and Morgoth alone
  (0.974/93%) is essentially as good as any fusion. The residual gap (0.946→0.974) is a foundation-model-vs-
  handcrafted-spectral gap, not a focality-measurement gap.

---

## (c) Prioritized recommendations

1. **Fix the benchmark label and re-run everything (P0, blocking).** Replace the `majority` column in the
   Sandor focal workbook with the expert-vote majority of `expert_0..expert_14` (median vote ≥ 0.5). Re-run the
   diagnostic, scripts 64/66, and the manuscript's Sandor focal validation. Expected corrected headline: our
   head 0.946 AUROC / 79% experts-under; Morgoth 0.974 / 93%; SCORE-AI 0.878 / 29%. **Correct the manuscript
   claim** — with valid labels Morgoth (and SCORE-AI on some points) is not beaten by our head; our head is at
   the expert ceiling, which is itself the publishable result. Audit how the focal `majority` column was built
   (the generalized workbook is intact, so the join/derivation differs between the two).
2. **Stop investing in focality statistics; adopt the foundation-model score for focal.** Peak−median focality
   (6-region or per-channel) is near-chance; finer spatial resolution, wake-gating, persistence, and morphology
   do not close the small residual gap. If the goal is the best focal detector, use Morgoth (or head+Morgoth
   rank-average, 0.978/86%). The hand-crafted head is a strong, interpretable expert-level baseline; it does
   not need more spectral features.
3. **The one genuine algorithm fix: frontopolar eye-movement/artifact robustness (P2, small).** The surviving
   high-specificity false positives (e.g. ID100) are blink/eye-movement contamination on Fp1/Fp2 read as
   frontal focal delta. Tightening artifact rejection on the frontopolar chain (or a field-coherence gate that
   requires the focus to persist across non-frontopolar neighbours) would recover a few points of specificity.
   This is a targeted specificity patch, not a redesign.
4. **Keep homologous L–R asymmetry as the interpretable focal descriptor**, but only for reporting/explanation
   — it is the single most informative relative focal feature (0.82) and maps to how clinicians describe focal
   slowing ("left temporal > right"). It should not be fused into the classifier (it hurts).

### What experts are actually "seeing"
Nothing our features fundamentally miss. Once the labels are correct, band-power asymmetry + region deviation
(our head) reproduces the expert focal judgement at the experts' own operating point, and the Morgoth
foundation model exceeds it. The apparent expert superiority was entirely the corrupted label pushing the
expert operating points above model ROC curves that had been scored against the wrong y.

---

## Reproduce
```
PYTHONPATH=src MPLBACKEND=Agg KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/focal_design_probe.py relabel   # corrected-label table
python3 scripts/focal_design_probe.py errors    # per-recording head scores + FN/FP lists
python3 scripts/focal_design_probe.py design     # unsupervised relative focal statistics
python3 scripts/focal_design_probe.py fusion      # supervised headroom (head / +asym / +Morgoth)
python3 scripts/focal_design_probe.py roc          # figures/scratch/focal_label_before_after_roc.png
python3 scripts/focal_design_probe.py render        # figures/scratch/focal_mislabel_confirmation.png (raw EEG)
```
(`scripts/focal_design_probe.py` is scratch and imports the diagnostic's builders; production scripts 53/55/64/66
were not modified.)
