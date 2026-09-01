# Supplementary Material

**Lifespan and sleep-stage-resolved normative EEG background: deviation-from-normal detection and automated reporting of slowing**

Supplementary methods, robustness analyses and negative results supporting the main text. Section numbers (S1, S2, ...) are cited from the main text at the point each is summarised. Every number here is produced by the same scripts as the main text and is covered by the same reproducibility certificate (`scripts/certify_reproducibility.py`).

---

### Supplementary

*Supplementary figures:*

- **Figure S1 --- Pipeline architecture.** One deviation-from-normal field as the shared substrate for detection (two report-trained heads) and claims-governed description, with held-out validation under each.
- **Figure S6 --- Per-segment deviation field**, calibrated & discriminative.
- **Figure S5 --- Stage-resolved curve bank** (rel_delta / TAR / DAR, whole-head).
- **Figure S8 --- Description panels D1/D3/D4/D6** (type/amount, anterior--posterior, persistence, generated-word concordance).
- **Figure S7 --- Why the two detection axes need different read-outs** (localized focal).
- **Figure S9 --- Severity is a null result** .
- **Figure S10 --- Mild example recordings: EEG segments with the automated report vs the clinical report.** The mildest focal and generalized examples, in the same format as Figures 4 and 5, which carry two panels each so that each prints at full size.
- **Figure S3 --- van Putten indices vs LENS vs the Morgoth gate on the clean ON-100 panel** (ROC per axis, expert-majority labels). LENS leads on generalized slowing and ties the foundation-model gate on focal --- generalized 0.961, focal 0.908 --- outperforming the best hand-crafted index by +0.14 / +0.08 and edging the foundation-model gate.

- **Figure S4 --- Scalp topography of the theta/alpha ratio (TAR) by age × sleep stage**. The TAR companion to Figure 1b, confirming that the regional development pattern is not specific to relative delta.

- **Figure S2 --- Held-out centile calibration of the normative curves.** Observed versus nominal centile for
data never used to fit the curves, faceted by sleep stage (rows) and feature (columns); the dashed diagonal is
perfect calibration and bands are patient-clustered bootstrap 95% CIs. Blue: 7,216 held-out clean-normal
recordings (6,779 patients), the complement of the seeded sample the norms are fitted on. Orange: the 71
ON-100 recordings with no expert-majority slowing, an institutionally external reference.

*Supplementary tables:*

- **Table S1 --- van Putten qEEG full-family benchmark** (every index × raw/age-conditioned arms on the report cohort). Isolates the age-conditioning dissociation --- slowing ratios improve, asymmetry indices do not (§3.5).
- **Table S2 --- Human ceiling** (Fleiss κ, self-consistency, conspicuity ρ).
- **Table S3 --- Band calibration.** The band is read from absolute delta/theta power dominance (mean log(δ/θ), which separates the reports\' delta-from-theta at AUROC 0.74 vs 0.68 for the deviation axis); delta/theta/mixed agreement is at the expert-vs-expert floor (κ≈0.10), marginal-matched to the report distribution.

## Supplementary Methods and Results

Methodological detail, robustness analyses and negative results supporting the main text. Every number here is produced by the same scripts and is covered by the reproducibility certificate.


### S1. Normative curve fitting (GAMLSS) in detail

Each feature × region × sleep stage is fitted separately, so a \"cell\" is one such triple and there are 11 × 5 × 6 = 330 of them. **The unit of observation is the individual 15-second segment**, and the design matrix carries a single continuous covariate --- log-transformed age --- with no other fixed effects and no patient random effect. Because a 12-hour overnight recording contributes far more segments than a 20-minute routine study, every segment is weighted by 1/(the number of segments that recording contributes to that cell), so **each recording carries equal total weight** regardless of length; the weights enter the GAMLSS fit directly rather than being approximated by subsampling, which would discard the long overnight recordings that carry most of the deep-sleep data. For each cell we estimate normal-population percentile \"growth curves\" as a continuous function of age using GAMLSS, the method behind clinical growth charts (Cole & Green \[33\]; Rigby & Stasinopoulos \[34\]). Age is entered as `log10(age + 1/12)`, expanding infancy where maturation is fastest. Two families are used according to the feature\'s support: positive features (relative powers, ratios) are fit with a Box--Cox-t (BCT) distribution with penalized-spline median, dispersion and age-varying skewness (`mu`, `sigma`, `nu` each smooth in log-age), which removes an infant-age median bias that a constant-skewness fit produces. The BCT's fourth parameter, the **tail/kurtosis parameter `tau`** (the degrees of freedom of the underlying t), is also fitted per cell and is used in scoring: a value is mapped to its centile through the t CDF at that cell's `tau`, so heavy-tailed cells do not manufacture extreme z-scores. Real-line log features real-line log features (log_delta, log_theta, log_TAR, which take negative values in 15--37% of segments) are fit with a support-aware robust median-in-log-age model on the real line. The Python BCT z-scores are validated exact against R `gamlss` `centiles.pred`. Each curve is checked against a model-free rolling median in a sliding, age-widening window, and both are plotted together in Figure 1a so the reader can see the agreement rather than take it on trust. Agreement is quantified as the median |fitted − rolling| within an age band, scaled by that cell's own interquartile width. An initial fit was too stiff through the infant peak of the ratio features — the sharpest part of the whole lifespan — where the median discrepancy reached 1.37 IQR (DAR in REM) and 0.97 IQR (DAR in wake). Increasing the median spline's degrees of freedom to 20 reduces these to 0.53 and 0.24 IQR while leaving the data-dense adult range untouched (≤ 0.04 IQR in every feature × stage cell at either setting), and is the fit shown. The residual infant discrepancy in the ratio features should not be over-read: bootstrapping the model-free comparator over recordings gives it a 95% interval about 1.2 IQR wide below one year for DAR (n \~200--250 infant recordings, strongly skewed), inside which the fitted median falls at roughly half of grid points; for relative delta, where the comparator is tight (0.43 IQR), the fitted median lies inside it at every grid point.


### S2. Band calibration and artifact rejection

**Calibration.** The delta band is defined as **1--4 Hz** rather than the 0.5--4 Hz used by some pipelines, because the 0.5--1 Hz octave in a scalp recording is dominated by sweat, respiration and electrode drift rather than by cerebral delta. Excluding it puts normal whole-head relative delta at \~0.34 of total power, which matches the proportion expected in a healthy adult record; with the 0.5 Hz edge the same recordings read substantially higher, and the excess is artefactual. Because all deviation scoring is z relative to each feature\'s own age/stage normal curve, the scoring, discrimination, and generated descriptions are scale-invariant.



**Artifact rejection.** A per-segment filter marks a 15-second bipolar segment unusable on three explicit criteria (`src/morgoth_slowing/features/artifact.py`). **Flat/disconnected**: median channel peak-to-peak < 1 µV or median channel standard deviation < 0.5 µV, or more than half of channels meeting either test. **High-amplitude**: any channel with peak-to-peak > 500 µV (electrode pop or movement). **EMG-dominated**: the fraction of 1--45 Hz multitaper power lying above 20 Hz, taken as the median across channels, exceeds 0.55. Segments are flagged rather than deleted, and the usable-segment fraction is carried into scoring so low-yield recordings are visible. Burst suppression and electrode disconnection are deliberately out of scope here and handled by a separate detector upstream, since this pipeline measures slowing, not suppression.


### S3. Detector fitting, splits and hyperparameters

*Fitting and hyperparameters.* Recordings are divided by a **patient-level split, stratified on (class, age band)**, where class is {control, focal-only, gen-only, both, other}, so no patient appears in both train and test. **No cross-validation or grid search was run**: the regularisation strength and class weighting were fixed a priori, k was set on the development data, and the model was then fitted once on the training split. Critically, nothing --- neither a coefficient nor a threshold --- was tuned on ON-100 or SAI-100, which is what makes the external comparisons below fair. The model is trained on clinical report labels and tested (external validation) unchanged on two independent, multi-site evaluation sets --- each 100 EEGs annotated by many experts and drawn entirely from hospitals *outside* the training health system: **ON-100** (100 recordings from five US centers --- Barnes-Jewish Hospital, Washington University in St. Louis, the Dallas VA Medical Center, UT Southwestern, and Louisiana State University --- each read by 18 experts) and **SAI-100** (the 100-recording holdout set of the SCORE-AI validation study \[35\], routine EEGs from Haukeland University Hospital (Norway), the Danish Epilepsy Centre (Denmark), and Mayo Clinic (USA), each read by 14 experts, and with SCORE-AI's own automated predictions available). Both benchmarks are held out entirely from fitting (no patient overlap with the report-trained cohort or with each other). ON-100 and SAI-100 are therefore *both* external validations, at institutions distinct from the training data and from one another.


### S4. Top-k recording aggregation

*From segment to recording.* The model's native output is a score for a lone 15-second clip. A recording's score is the **mean of its top-20 segment scores**. The top-k form follows from the label semantics --- a report names slowing if it occurs anywhere, so a recording is positive when its *most abnormal* stretch is abnormal, and averaging over all segments would dilute a genuine intermittent finding with normal ones. k = 20 (300 seconds) was chosen on the internal report-test split and on a feasibility bound, never on either external set. Detection improves with k on both axes and both splits, monotonically for focal and up to k \~ 20 for generalized, which then plateaus (ON-100 0.967 at k = 20, 0.960 at k = 30, 0.965 at k = 50); each recording contributes at most 80 sampled segments, so beyond about k = 30 the top-k mean degenerates into the plain mean for most recordings; k = 20 leaves ≥90% of recordings with at least k segments and takes most of the available gain.


### S5. Model class and regularisation

*Model class.* LENS is deliberately simple: an **L2-regularised logistic regression** on standardised deviation features (scikit-learn `LogisticRegression`, C = 0.3, `class_weight='balanced'`), fitted at the level of the individual 15-second segment. There is no neural network in the interpretable pipeline; the foundation model appears only as the separate reference detector of §2.7b. Two independent heads are fitted, differing only in which features they see: the **generalized** head takes the six whole-head *amount* deviations (log delta, log theta, relative delta, log DAR, log TAR, relative alpha) plus age; the **focal** head takes, for each of three focal indicators (log delta, relative delta, log TAR), its peak-region z, its focality (peak − median region) and its asymmetry z, plus age.


### S6. The van Putten index family

**2.7c The van Putten benchmark.** We recomputed the van Putten family of indices: the Brain Symmetry Index and its revised pairwise form (r-sBSI), the diffuse-slowing index Q_SLOWING, the anterior--posterior gradient Q_APG, homologous-pair asymmetry Q_ASYM, and the slowing ratios DAR (delta/alpha) and DTABR = (δ+θ)/(α+β), plus the 95% spectral-edge frequency SEF95. Each is evaluated as published and age-conditioned against our normative curves; the clean-panel head-to-head (**Figure S3**) then pits the best index per axis against LENS and the Morgoth gate.


### S7. A worked generated paragraph

> For a lateralised, confident focus the paragraph names the derivation carrying the slowing --- one level finer than the lobe (electrode-level, \~40% of focal recordings) --- localised from left--right delta asymmetry, which cancels the symmetric frontal/eye-movement delta gradient that makes raw power a frontopolar attractor; reports carry no electrode field, so this is an output-granularity gain for automated reporting rather than a scored claim (clause 4e). The discretely checkable components are concordant with the report above the 33% chance rate on side (56%) and region (46%). The band (δ/θ/mixed) call is read off absolute delta/theta power dominance (the whole-head mean of log(δ/θ), not the deviation z), as a clinician who writes \"delta slowing\" generally means delta power dominates the trace, whereas the per-band age/stage z does not track that (normal delta variance is large, so a large delta in a young brain sits at a modest z while a smaller theta excess can win the deviation axis even as delta plainly dominates).
>
The delta-versus-theta call is deliberately calibrated rather than asserted; **S8** below gives the separation achieved and the threshold rule.


### S8. Band (delta vs theta) calibration

> On held-out reports the raw ratio separates delta-from-theta at AUROC 0.74, versus 0.68 for the deviation axis (z_theta − z_delta). Even so the call is deliberately calibrated to the report *distribution* rather than tuned for accuracy: the report band is \~64% \"mixed\", a reader hedge that sits between the two pure bands and is only weakly separable from either, so maximising 3-way accuracy collapses to \"always mixed\". Marginal-matching (default \"mixed\"; a pure delta/theta call only when log(δ/θ) clears a threshold set to the report\'s own rates) reproduces the report distribution and reaches 53% concordance at Cohen κ ≈ 0.10, the low end of published expert-vs-expert band agreement (0.09--0.38), i.e. the human noise floor. We therefore report band as a low-confidence gloss and rely on the continuous dose-response contrast as its valid test.


### S9. Descriptor-to-text assembly

- **D6: words.** Descriptors are assembled into a compact finding line and a full report-style paragraph, governed clause-by-clause by (magnitude as SD/centile; prevalence as a percentage with the ACNS word as an internal gloss; band a low-confidence δ/θ/mixed call on clear dominance; side asserted with the maximum-deviation lobe flagged provisional; anterior--posterior predominance only when it clears the normal centile; stage accentuation and \"present only during sleep\"; and a required abstain path). A representative paragraph: *\"Left temporal theta--delta slowing, maximal over the left temporal region, peaking at T3 (the T3--T5 derivation). Peak deviation 2.8 SD above the age- and stage-matched normal (99th centile), abnormal in 46% of analysed segments; longest continuous run ≈9.1 min over 27 episodes. Present in wakefulness and sleep, most prominent in REM sleep.\"*


### S10. Sleep-verified N3 (adjudicating the staging objection)

**The same holds in deep sleep, which is where the staging objection bites hardest.** Spindles cannot verify N3 directly: they are the defining graphoelement of N2 and are sparse to absent in N3, so requiring one inside an N3 epoch would reject correctly-staged N3. We therefore verify *sleep* rather than *sleep depth*, accepting an N3 segment only when the maximally contiguous non-wake block containing it also holds a spindle-positive N2 segment; a spindle anywhere in that block establishes genuine sleep on evidence independent of delta, which is precisely what an encephalopathic-wake misclassification predicts against. Of 665 staged N3 segments, 320 (48%) sit inside such a verified block. On those, cases still separate from controls on both axes --- log delta AUROC **0.767 \[0.645, 0.870\]** (p = 2×10⁻⁴), DAR **0.784 \[0.671, 0.884\]** (p = 7×10⁻⁵), on 41 cases and 28 controls. Deep-sleep deviation in these recordings is therefore not an artefact of slow-wave-keyed staging mistaking encephalopathic wakefulness for N3.


### S11. The width of the normal range in sleep

**The normal range in sleep is genuinely wide, and our reference is a population one.** Sleep depth and slow-wave activity vary substantially between healthy individuals, and much of that variance is constitutional rather than pathological: sleep EEG spectral profiles are heritable \[22--25\] and modulated by common polymorphisms in adenosine, circadian and neurotrophic genes \[26--28\]; slow-wave activity changes markedly across the lifespan \[29\]; and several drug classes, notably the oxybates and the atypical antipsychotics, raise it directly \[31\]. Phasic phenomena such as the cyclic alternating pattern further alter the spectral content of any given conventional stage. Our norms are conditioned on age and sleep stage but not on genotype, medication, or prior sleep debt, none of which we observe. A recording therefore sits high on our scale either because it is abnormal or because the patient sits high within a wide healthy distribution, and we cannot separate these from the EEG alone. This is the concrete reason the output is framed as a deviation to be adjudicated rather than a diagnosis (§2.11), and it bears most on generalized slowing in deep sleep, where the physiological range is widest. Medication history in particular is a tractable next step: it is present in the health record and would let a future version condition the norm on it.


### S12. Vigilance state in the overnight expansion

**Vigilance state is uncontrolled in the overnight recordings.** A routine EEG is recorded under active alerting by a technologist, whereas the 5,919 overnight/long-term studies are unconstrained: the patient may be drowsy, reading, or eating during nominal wake. Stage-matching absorbs part of this, since a drowsy epoch staged N1 is scored against the N1 norm, but not all of it --- task-related rhythms such as reading-induced temporal theta carry no stage label of their own and will sit inside the wake reference. This widens the wake norm, which is conservative for detection (a wider normal is harder to exceed), but it does mean our \"wake\" is a broader physiological state than routine alert wake.


### S13. Why age-conditioning helps the slowing ratios but not the asymmetry indices

**Age-conditioning some metrics helps but does not close the gap (generalized).** For generalized slowing the field relies on population-agnostic slow/fast ratios (Q_SLOWING, DAR, DTABR) thresholded on single disease populations and blind to age and vigilance. Recomputed on our cohort they detect at raw AUROC 0.691--0.732; age-conditioning each against our clean-normal lifespan curves raises them monotonically (+0.03 to +0.05), lifting DTABR to 0.773 --- a key positive control for the normative framework, since conditioning a *published* metric on our curves improves it, in the direction physiology dictates. Yet even the best age-conditioned arm trails the learned representation, so the residual signal is morphological and stage-topographic, not band-power. This is why the deviation field is deployed as the interpretable, calibrated description and per-stage threshold. This design choice lets physiologic sleep slowing be separated from abnormal-for-stage deviation automatically, something wake-only ratios cannot do, while detection uses the strongest available representation.


### S14. Relation to the Brain Symmetry Index

**Beyond the Brain Symmetry Index (focal).** The van Putten BSI \[8\] and revised pairwise rBSI \[9\] established interhemispheric spectral asymmetry as a quantifiable, clinically meaningful signal, but as a bare 0--1 index tuned on small acute-stroke cohorts (n = 21) with no age/sex/stage reference. Our homologous-channel asymmetry feature is a descendant of this idea, normed against the age × stage-matched normal population and, for the detection decision, replaced by a learned representation: on identical signals the strongest van Putten focal arm (raw r-sBSI 0.723) is exceeded by the gate at 0.870 (+0.147), and age-conditioning the asymmetry indices makes them slightly *worse*, exactly as physiology predicts, since interhemispheric symmetry does not vary across the lifespan. Beyond detection we provide information that a symmetry scalar cannot: lateralization, posed as a focal-gated left-vs-right task from *signed* asymmetry separates the reported sides monotonically (left +0.43, bilateral +0.07, right −0.54), is band-matched (delta cases lateralized by delta asymmetry, theta by theta), and is stable across the lifespan; and regional localization by relative lobe prominence tracks the reported lobe for temporal, frontal, and posterior foci.


### S15. Prior automated-interpretation benchmarks

The Temple University Hospital Abnormal corpus (TUAB; López et al. \[15\]; Obeid & Picone \[16\]) established binary normal/abnormal classification as a standard benchmark, with ConvNets reaching \~85% (Schirrmeister et al. \[17\]; Gemein et al. \[18\]). EEG foundation models (BENDR \[19\], LaBraM \[20\], and clinically grounded variants) now dominate representation learning; our foundation-model (which we call \"Morgoth\") sits in this family and serves here as a *reference detector* our interpretable model is measured against. Report NLP has extracted findings from free text (Biswal et al. \[21\]), and recent systems generate narrative from signal, but none ties generated findings to a lifespan-normative deviation model, nor validates stage-specific slowing sentences against the actual report corpus.


### S16. The historical age-norm literature

Day-to-day clinical EEG reading rests on age norms established decades ago on modest samples. Petersén & Eeg-Olofsson \[5\] characterized the developing EEG in children aged 1--15 years, qualitatively-to-semiquantitatively and awake-focused. The most direct precedent for our deviation framing is John et al. \[6\], whose \"developmental equations\" gave 32 linear age regressions of band power across four bands and four bilateral regions, fitted on groups of healthy children in the eyes-closed resting state; a companion paper in the same volume then used deviation from those same equations to flag dysfunction, an early \"deviation-from-normal\" idea. The narrow-age-band and eyes-closed-only limitations are properties of the equations themselves and so apply to both papers. John et al. \[7\], \"Neurometrics,\" and the commercial normative databases it seeded (NeuroGuide/NxLink lineage) generalized age-regressed z-scoring, but these remain wake-resting, age-banded, of modest and somewhat opaque N, and not reproducible.


### S17. The SAI-100 cohort and pipeline run

The **second external benchmark, SAI-100**, tests whether the same unchanged pipeline also transfers across countries and to an independent scoring system. We ran it on 100 routine scalp EEGs from the SCORE-AI validation study \[35\] --- drawn from three hospitals in two countries (Haukeland University Hospital, the Danish Epilepsy Centre, and Mayo Clinic), with no overlap with training or with ON-100 --- for which SCORE-AI (a published automated EEG-interpretation system), the Morgoth gate, and 14 individual expert calls per recording are available. The full pipeline (feature extraction, Morgoth sleep staging, age- and stage-matched deviation, and the report-trained detectors) ran end-to-end on 98/100 recordings (2 EDFs were unreadable). Ground truth is the expert-vote majority recomputed from the 14 individual expert ratings. The intermediate results workbook we received carries a single summary column that reproduces the focal *interictal epileptiform* consensus rather than the focal non-epileptiform one, so it is not used; the source data release itself is internally consistent (its focal non-epileptiform consensus agrees with the individual ratings on all 100 recordings).


### S18. Cohort construction and inclusion

The analysis cohort comprises 25,536 recordings from 21,757 unique patients curated from a single academic health system (MGB sites), spanning infancy to \>90 years: 19,617 routine clinical EEGs (\"cohort\") and 5,919 overnight/long-term studies (\"expansion\"). Each recording carries report-derived structured finding flags (normal, abnormal, focal slowing, generalized slowing), which are non-exclusive (a report may note more than one). The normal reference is *clean-normal*: flagged normal in clinical EEG reports (n = 10,189). Slowing groups are evaluated **one-vs-clean-normal** --- that is, each slowing class is compared against the clean-normal reference in its own two-group contrast, rather than the classes being forced into a single mutually exclusive multiclass problem. This matches how the findings actually occur: focal and generalized slowing frequently coexist in one recording, so a recording may be a positive case in both contrasts. Focal slowing n = 8,016 and pathologic generalized slowing n = 6,841, of which **2,338 recordings carry both (29.2% of the focal set and 34.2% of the pathologic generalized set)**. Critically, the generalized-slowing flag is split into pathologic vs physiologic slowing, to avoid labeling slowing that occurs in normal drowsy/sleep/hyperventilation as abnormal; only the pathologic set defines the generalized slowing class (physiologic generalized slowing, n = 3,382, is left in the clean-normal reference; 3,009 of them fall in the clean-normal column of **Table 1**, the remainder in recordings excluded by other criteria).


### S19. Held-out centile calibration in detail

**The curves are calibrated on held-out data.** A percentile model is only useful if its percentiles are
real, so we tested them where they were not fitted (**Figure S2**). The norms are fitted on a seeded
3,000-recording sample of the clean-normal reference; the remaining **7,216 clean-normal recordings (6,779
patients)** are therefore held out, and the ON-100 panel recordings the expert majority called neither
focally nor generally slow (n = 71) provide a second, institutionally external reference. For each held-out
15-second observation we took the model-predicted centile at that observation's own age, stage, region and
feature, and asked what fraction of observations actually fell below it. On the internal held-out normals the
observed and nominal centiles agree closely across every stage and feature --- median absolute discrepancy
**1.1 percentage points**, maximum 9.2 --- so a segment at our nominal 97th centile really is a 97th-centile
segment. On the external no-slowing recordings agreement is looser but still close over most cells (median
2.3 points), with one clear exception: **N1 log TAR**, where the nominal 75th centile captures only 54% of
external observations, i.e. the external N1 distribution is wider than our norm expects. Deep sleep is well covered by the internal held-out set --- **4,836 held-out N3 observations from 420 patients**, calibrating to a median 3.7-point discrepancy (relative delta essentially exact: 2.98, 51.5 and 97.6 observed at nominal 3, 50 and 97; log DAR the loosest, 56.7 observed at nominal 50). What could not be assessed is N3 in the *external* set, where it is only 5.4% of segments because both external cohorts are routine daytime recordings. Calibration is therefore good internally in every stage including deep sleep, and good-but-imperfect across institutions in the stages those cohorts actually sample.


### S20. Age and sex provenance

Age and sex are taken from the clinical records; sex is balanced at 49.2% female overall. Age is a critical confound that motivates the entire normative design: abnormal recordings are markedly older than clean-normals (median 53.9 y \[IQR 24.3--69.7\] vs 36.8 y \[18.6--59.2\]), so any unadjusted comparison would conflate slowing with age. Full cohort characteristics --- age bands, sex, recording length, usable segments, stage composition, and the abnormal-detail strata (focal side, generalized topography, band) --- are given in Table 1 (SAP §10). Segment-level feature tables are keyed on the recording; patient is the clustering unit for all confidence intervals (patient-clustered bootstrap), and report-derived quantities are computed only on the `clean_pair` set (§2.6). This work was conducted under IRB protocol number 2022P000417, with the BIDMC IRB granting a waiver of consent.


### S21. Relation to the normative-scoring and automated-interpretation lineages

**The normative lineage and automated interpretation.** Our instrument sits at the confluence of two older lineages. The first is normative deviation scoring: John et al.\'s developmental equations \[6\] and Neurometrics z-scoring \[7\] first expressed a clinical EEG as its deviation from age-matched norms, on a few hundred wake-resting, age-banded subjects; Bethlehem et al.\'s \[4\] MRI brain charts (n = 101,457, GAMLSS centiles) modernized the centile idea for structural imaging. We are the functional-EEG, sleep-stage-resolved analog --- GAMLSS growth curves on \~25,000 clinical EEGs, resolved per sleep stage, in open reproducible Python. The second is automated interpretation: the TUAB corpus and its ConvNet classifiers (\~85%) reduce a recording to a binary label with no localization, band, severity, or narrative, and EEG brain-age (Engemann \[3\]) collapses the spectrum to a single scalar. What we add on top of both is a described, validated, stage-resolved output: the interpretable field detects (outperforming the panel and the gate), describes, and emits clinician-style sentences validated against reports, with the one clause reports systematically omit, *\"present in sleep\"*, defensible on spindle-verified N2.


### S22. Clinical reports as a directionally biased reference standard

**Reports are a directionally biased reference, and a normative model can detect what they miss.** Clinical reports are our reference standard, but an *imperfect reference with a known, directional bias*: because theta/delta slowing is normal in sleep and \"how much is too much\" is hard to judge by eye, reports name sleep-confined slowing less often than waking slowing (§3.8, 54% vs 75%) --- and focal slowing seen only in sleep has low specificity \[38\], so a reader may omit it deliberately rather than miss it. We therefore treat concordance with reports as validation only *where reports are reliable*, and pose the complementary hypothesis: that a per-stage normative model is the better *measuring instrument* exactly where visual reading is weakest --- slowing that occurs in sleep. We are careful about what "better" means here (§2.11). LENS measures the deviation more reproducibly than a reader can; it does not thereby establish that every deviation it finds is pathological, and for generalized slowing confined to N3 there are benign explanations (slow-wave rebound, medication) that no spectral measurement can exclude. The claim is that the reader and the instrument disagree systematically and in a direction the instrument can quantify, not that the instrument is right and the reader wrong. This is supported here by dose-response, a within-subject wake→sleep test, and spindle-verified convergent validity. The definitive test is a blinded expert re-read of high-deviation report-normal sleep studies, proposed as prospective validation.


### S23. The settled direction of lifespan spectral change

The direction of lifespan spectral change is settled in the standard clinical references \[1,2\]. Low-frequency (delta, theta) power dominates in infancy and declines with maturation; faster rhythms increase; the posterior dominant rhythm accelerates from \~3--4 Hz in infancy to the adult 8--12 Hz alpha by adolescence; aperiodic (1/f) activity flattens with development. In aging the picture is subtler and health-dependent, and much apparent \"age-related slowing\" reflects comorbidity rather than healthy aging. Modern quantification has taken two forms. First, EEG \"brain age\" regresses chronological age on resting spectral (and aperiodic) features, formalized as a reusable M/EEG benchmark by Engemann et al. \[3\]. Second, and conceptually closest to us, normative centile modeling of brain measures: Bethlehem et al. \[4\] built MRI \"brain charts\" across the lifespan (n = 101,457) using GAMLSS to yield individual deviation scores, the structural-imaging analog of what we do here functionally with EEG. Crucially, almost all lifespan quantitative EEG (qEEG) reports *normal values*, not the *deviation of an individual clinical EEG from its matched norm*, and essentially none is sleep-stage-specific.


### S24. Two readings of the sleep-confined deviations

Two readings of this are possible and the data here do not fully separate them. Under the first, these are
genuine abnormalities that visual reading misses because judging "how much delta is too much" against an
internalised stage norm is hard. Under the second, some fraction is physiological --- slow-wave rebound in a
sleep-deprived patient, or a pharmacological effect --- that the reader correctly declined to call abnormal.
Per §2.11 our claim is the statistical one, and it is the weaker of the two: these recordings deviate from
their stage-matched norm, and reports name that deviation far less often when it is confined to sleep. Which
of them warrant clinical action is exactly the adjudication we leave to the reader, and the blinded re-read
proposed in §4 is the test that would separate the two accounts. Note that the asymmetry is itself
informative: a *focal* deviation confined to sleep has no benign physiological explanation of this kind,
since sleep-related slowing is a diffuse process, whereas a generalized N3 deviation does.


### S25. Descriptor definitions and the claims table

Once slowing has been detected in a recording, LENS generates a structured verbal description of what kind of slowing it is, where it is, and how persistent it is. Per recording, from the deviation field we read off: type/amount (whole-head delta-excess and theta-excess z: p90, mean, prevalence), laterality (signed left-minus-right region z, + = left), region (per-lobe magnitude and relative prominence/focality), anterior--posterior gradient (anterior − posterior z), persistence, and per-sleep-stage versions of each. Persistence has three components, defined on the sequence of 15-second segments: **prevalence**, the fraction of analysed segments that exceed the abnormality threshold; **longest continuous run**, the duration of the longest unbroken block of such segments; and **number of episodes**, the count of maximally contiguous blocks, so that an episode is one uninterrupted stretch of abnormal segments however long. Episode counts scale with recording length and with how fragmented the finding is --- a long overnight study whose slowing comes and goes can accumulate hundreds of short episodes alongside a longest run of only a few minutes, which is the signature of a highly intermittent rather than a sustained abnormality. Descriptors are assembled into a compact finding line and a full report-style paragraph, governed clause-by-clause by : magnitude as SD and centile (never a severity adjective), prevalence as a percentage following ACNS \[36\] terminology (occasional/frequent/abundant/continuous) as an internal gloss only, band as a low-confidence δ/θ/mixed call read from absolute delta/theta power dominance (whole-head mean log(δ/θ), marginal-matched to the report distribution), side asserted with the maximum-deviation lobe flagged provisional, anterior--posterior predominance asserted only when it clears the normal centile, stage accentuation and \"present only during sleep\", and a required abstain path (\"no lateralizing or regional spectral excess above the normal centile\") so the system never invents a lobe. Validation is by contrast (dose-response), rather than binary classification: each continuous descriptor is compared between recordings whose report *does* and *does not* name the corresponding finding, and must be higher where the report names it.

### Supplementary — code and data map

Every figure, table and number in this paper is produced by a named script in the public repository and regenerates from the released derived data; `scripts/certify_reproducibility.py` checks that mapping mechanically. Paths are collected here rather than in the running text.

| Section | Producers and artifacts |
|---|---|
| 2.1 Cohort and data | `scripts/table1_sap.py` |
| 2.2 Reproducible feature extraction | `config/channels_regions.yaml` |
| 2.4 Normative growth curves (GAMLSS) | `scripts/79`, `scripts/115` |
| 2.5 The per-segment deviation field | `data/derived/segment_deviation/` |
| 2.6 Report--recording pairing and label provenance | `scripts/label_rederive_sap.py` |
| 2.7 Detection | `scripts/54`, `scripts/80`, `scripts/53`, `scripts/recompute_vanputten_fullcov.py`, `scripts/vanputten_panel_s7.py` |
| 2.8 Description: reading the deviation field into words | `scripts/56`, `docs/claims_table.md` |
| 3.4b Detection --- external validation on SAI-100 (SCORE-AI and 14 experts) | `results/story/age_ablation.md` |
| 3.7 Description --- type, location, persistence, and sleep stage, validated by contrast | `results/story/s4_description.md`, `docs/claims_table.md` |
| 3.9 Why we do not describe clinical "severity grade" | `results/severity_null_v6.md`, `results/story/severity_sweep.md` |
| 4. Discussion | `results/story/s4_description.md` |
| 5. Limitations | `results/story/slow_peak_frequency.md` |
| Figures and Tables | `docs/cn_submission_plan.md` |
| Main | `results/table1.md`, `scripts/table1_sap.py`, `figures/growth_v2/keystone_growth_grid.png`, `scripts/76`, `figures/growth_v2/topo_rel_delta_by_age_stage.png`, `scripts/77`, `figures/story/s0d_single_occasion_generalized.png`, `scripts/53–55, 66`, `figures/story/sandor100_slowing.png`, `scripts/sandor100_*`, `figures/story/s4_examples_eeg_focal.png`, `scripts/62`, `figures/story/s4_examples_eeg_generalized.png`, `figures/story/s4_d2.png`, `scripts/57`, `figures/growth_v2/v4a_wake_sleep.png`, `scripts/fig6_sleep_naming.py` |
| Supplementary | `figures/manuscript/`, `scripts/assemble_manuscript_figures.py`, `figures/story/architecture.png`, `scripts/architecture_diagram.py`, `figures/story/s2_segment_deviation.png`, `scripts/44`, `figures/stage_curves/`, `scripts/111`, `figures/story/s4_d1,3,4,6.png`, `scripts/57–58`, `figures/story/s0_occasion_ours_v4_focal.png`, `scripts/49`, `figures/growth_v2/severity_recalibrated.png`, `results/severity_null_v6.md`, `scripts/109`, `figures/figs/vanputten_panel_s7.png`, `scripts/vanputten_panel_s7.py`, `figures/growth_v2/topo_TAR_by_age_stage.png`, `scripts/77`, `figures/story/s9_centile_calibration.png`, `results/story/centile_calibration.md`, `scripts/78`, `results/vanputten_fullcoverage.md`, `results/table5_human_ceiling.md`, `results/story/band_calibration.md`, `scripts/band_calibration.py` |
| Data and code availability | `scripts/reproduce_story.sh`, `docs/REPRODUCE.md` |
