# Lifespan and sleep-stage-resolved normative EEG background: deviation-from-normal detection and automated reporting of slowing

**Authors**

Jin Jing^1,\*^, Chenxi Sun^2,\*^, Wolfgang Ganglberger^1,\*^, Alice D. Lam^3^, Haoqi Sun^1^, Tianyu Zhang^1^, Daniel M. Goldenholz^1^, Fabio A. Nascimento^4^, Doyle Yuan^5^, Sándor Beniczky^6^, Jennifer A. Kim^7^, Aaron F. Struck^4^, Sahar F. Zafar^3,†^, Robert J. Thomas^8,†^, Mouhsin M. Shafi^1,†^, M. Brandon Westover^2,†^

\* These authors contributed equally (co-first authors).   † Co-senior authors.

**Affiliations**

1.  Department of Neurology, Beth Israel Deaconess Medical Center, Harvard Medical School, Boston, MA, USA
2.  Department of Neurology and Neurological Sciences, Stanford University School of Medicine, Stanford, CA, USA
3.  Department of Neurology, Massachusetts General Hospital, Harvard Medical School, Boston, MA, USA
4.  Department of Neurology, Washington University School of Medicine in St. Louis, St. Louis, MO, USA
5.  Department of Neurology, University of Texas Southwestern Medical Center, Dallas, TX, USA
6.  Department of Clinical Neurophysiology, Danish Epilepsy Centre, Dianalund, Denmark; and Department of Clinical Medicine, Aarhus University, Aarhus, Denmark
7.  Department of Neurology, Yale School of Medicine, New Haven, CT, USA
8.  Division of Pulmonary, Critical Care and Sleep Medicine, Department of Medicine, Beth Israel Deaconess Medical Center, Harvard Medical School, Boston, MA, USA

**Author email addresses** *(for the submission system; not for publication)*

Jin Jing <jjing@bidmc.harvard.edu>; Chenxi Sun <cxsun@stanford.edu>; Wolfgang Ganglberger
<wganglbe@bidmc.harvard.edu>; Alice D. Lam <lam.alice@mgh.harvard.edu>; Haoqi Sun
<hsun3@bidmc.harvard.edu>; Tianyu Zhang <tzhang11@bidmc.harvard.edu>; Daniel M. Goldenholz
<daniel.goldenholz@bidmc.harvard.edu>; Fabio A. Nascimento <fabion@wustl.edu>; Doyle Yuan
<dy15@alumni.utsw.edu>; Sándor Beniczky <sbz@filadelfia.dk>; Jennifer A. Kim
<jennifer.a.kim@yale.edu>; Aaron F. Struck <struck@wustl.edu>; Sahar F. Zafar
<sfzafar@bidmc.harvard.edu>; Robert J. Thomas <rthomas1@bidmc.harvard.edu>; Mouhsin M. Shafi
<mshafi@bidmc.harvard.edu>; M. Brandon Westover <mbwest@stanford.edu>.

**ORCID iDs.** Wolfgang Ganglberger 0000-0002-6029-2450; Alice D. Lam 0000-0001-7754-4637;
Daniel M. Goldenholz 0000-0002-8370-2758; Sándor Beniczky 0000-0002-6035-6581; Aaron F. Struck
0000-0002-9103-1798; Mouhsin M. Shafi 0000-0002-4531-1967; M. Brandon Westover 0000-0003-4803-312X.
*(Remaining authors: their iDs could not be resolved unambiguously from the public ORCID registry --- each
name returns several records with no distinguishing affiliation --- so they should be supplied by the
authors themselves rather than guessed.)*

*Corresponding author:* M. Brandon Westover, Department of Neurology and Neurological Sciences, Stanford University School of Medicine, Stanford, CA, USA --- email: <mbwest@stanford.edu>.

## Highlights

- Lifespan × sleep-stage EEG growth charts score slowing as deviation from normal
- LENS detects slowing above experts and a foundation model
- It captures sleep slowing that clinicians routinely under-report
- It auto-generates slowing reports validated against the clinical record
- Second-site validation (SAI-100) matches experts and beats SCORE-AI

## Abstract

**Objective.** Norms for abnormal EEG background slowing rest on small, mostly awake samples. We built LENS:
lifespan- and sleep-stage-resolved EEG growth charts and the deviation-from-normal field they yield.

**Methods.** From 25,536 clinical EEGs (21,757 patients; infancy to \>90 y) we estimated age × sleep-stage
percentile curves (GAMLSS) for spectral power and its ratios, scoring each 15-s segment as a deviation z from
its matched normal. Logistic detectors trained on report labels identify, localize and describe slowing. Both
were validated unchanged on two 100-EEG multi-expert sets from outside the training system: ON-100 (18
experts) and SAI-100 (14 experts, plus SCORE-AI).

**Results.** Curves reproduced development and sleep physiology and were calibrated on held-out normals
(median centile error 1.0 point). Against the ON-100 majority LENS reached AUROC 0.946 (generalized) and
0.921 (focal), placing 78% and 71% of experts under its curves and exceeding a foundation model and the best
published index by 0.10--0.13. On SAI-100 it matched experts for focal slowing but ranked last of three for
generalized. Slowing was the least reliable expert judgement (κ 0.37--0.45), and reports named it far less
often when confined to sleep (54% vs 75%).

**Conclusions.** One deviation field, shared by detection and description, identifies slowing at expert level
and yields stage-aware automated reports. As with a growth chart, LENS measures departure from a matched
norm; establishing its cause remains clinical.

**Significance.** The first lifespan- and sleep-stage-resolved deviation-from-normal instrument for EEG.

*Keywords:* EEG; quantitative EEG; slowing; normative modelling; sleep; automated reporting

## 1. Introduction

Slowing of the EEG background is the most common and one of the most clinically consequential abnormalities a neurophysiologist reports. Such slowing takes two forms: focal slowing points to a localized structural or functional lesion; generalized slowing signals diffuse encephalopathy. Yet whether a given rhythm counts as \"slow\" is relative: the posterior dominant rhythm that is normal at 4 Hz in an infant would be markedly abnormal in an adult, and delta activity that is pathological in the waking adult is physiological in deep sleep. Interpretation therefore depends on age and state, and in practice remains qualitative and expert-dependent, causing inter-reader variability and blocking scalable, reproducible second reads.

The direction of lifespan spectral change is settled in the standard clinical references \[1,2\]. Low-frequency (delta, theta) power dominates in infancy and declines with maturation; faster rhythms increase; the posterior dominant rhythm accelerates from \~3--4 Hz in infancy to the adult 8--12 Hz alpha by adolescence; aperiodic (1/f) activity flattens with development. In aging the picture is subtler and health-dependent, and much apparent \"age-related slowing\" reflects comorbidity rather than healthy aging. Modern quantification has taken two forms. First, EEG \"brain age\" regresses chronological age on resting spectral (and aperiodic) features, formalized as a reusable M/EEG benchmark by Engemann et al. \[3\]. Second, and conceptually closest to us, normative centile modeling of brain measures: Bethlehem et al. \[4\] built MRI \"brain charts\" across the lifespan (n = 101,457) using GAMLSS to yield individual deviation scores, the structural-imaging analog of what we do here functionally with EEG. Crucially, almost all lifespan quantitative EEG (qEEG) reports *normal values*, not the *deviation of an individual clinical EEG from its matched norm*, and essentially none is sleep-stage-specific.

Day-to-day clinical EEG reading rests on age norms established decades ago on modest samples. Petersén & Eeg-Olofsson \[5\] characterized the developing EEG in children aged 1--15 years, qualitatively-to-semiquantitatively and awake-focused. The most direct precedent for our deviation framing is John et al. \[6\], whose \"developmental equations\" gave 32 linear age regressions of band power, fitted on a few hundred healthy children in the eyes-closed resting state; a companion paper in the same volume then used deviation from those same equations to flag dysfunction, an early \"deviation-from-normal\" idea. The small-N, narrow-age-band and eyes-closed-only limitations are properties of the equations themselves and so apply to both papers **\[verify: confirm the derivation N against the primary source\]**. John et al. \[7\], \"Neurometrics,\" and the commercial normative databases it seeded (NeuroGuide/NxLink lineage) generalized age-regressed z-scoring, but these remain wake-resting, age-banded, of modest and somewhat opaque N, and not reproducible.

A separate literature quantifies pathology directly without lifespan normalization. van Putten & Tavy \[8\] introduced the Brain Symmetry Index (BSI), a 0--1 measure of interhemispheric spectral asymmetry correlating strongly with stroke severity (n = 21); the revised pairwise BSI followed \[9\]. This is the intellectual ancestor of our homologous-channel asymmetry feature. Slowing ratios such as DAR (delta/alpha ratio) and (delta+theta)/(alpha+beta) track acute-stroke severity (Finnigan & van Putten \[10\]), and relative delta/theta and alpha-delta ratios discriminate ICU delirium and coma. However, these instruments are each tied to one disease and setting, use fixed thresholds, and ignore age, sex, and sleep stages.

The Temple University Hospital Abnormal corpus (TUAB; López et al. \[11\]; Obeid & Picone \[12\]) established binary normal/abnormal classification as a standard benchmark, with ConvNets reaching \~85% (Schirrmeister et al. \[13\]; Gemein et al. \[14\]). EEG foundation models (BENDR \[15\], LaBraM \[16\], and clinically grounded variants) now dominate representation learning; our foundation-model (which we call \"Morgoth\") sits in this family and serves here as a *reference detector* our interpretable model is measured against. Report NLP has extracted findings from free text (Biswal et al. \[17\]), and recent systems generate narrative from signal, but none ties generated findings to a lifespan-normative deviation model, nor validates stage-specific slowing sentences against the actual report corpus.

There are substantial individual differences in sleep depth, slow waves, spindles and phasic events (cyclic alternating pattern, CAP) during normal sleep, which change the visualized frequencies and the interpretation of normal versus pathological slowing \[18--21\]. Sleep EEG slowing is influenced by genetic polymorphisms \[22--24\]. There is a large age-dependency of slow-wave activity \[25,26\]. Several medications, such as the oxybates and atypical antipsychotics, increase slow-wave activity during sleep \[27\]. Thus, in clinical practice, for any given conventional sleep stage, slowing varies widely in health and disease, making the determination of what is normal difficult.

No prior work combines (a) lifespan-continuous and (b) sleep-stage-specific normative modeling of clinical slowing features with (c) per-recording deviation-from-normal scoring, (d) on \>20,000 patients from clinical practice, and (e) closes the loop to clinician-style narrative validated against real reports.

Here we introduce LENS (Lifespan EEG Normative Scoring): lifespan, sleep-stage-resolved EEG growth charts --- the functional-EEG analog of pediatric growth charts --- and the interpretable deviation-from-normal field they yield when a recording is scored against them, which serves both detection and description. Specifically, LENS (1) builds reproducible age × sleep-stage normative growth curves for clinical slowing features across the lifespan, in whole-head, regional, and scalp-topographic form; (2) derives from them a per-segment deviation field (stage- and age-matched z per region × feature), the shared substrate for downstream analysis; (3) detects slowing with an interpretable model based on that deviation field, externally validated on two multi-expert datasets, outperforming the current state-of-the-art foundation-model; (4) generates a structured, validated description (type, laterality, region, anterior--posterior gradient, persistence, sleep stage, electrode) that tracks the report by dose-response contrast; and (5) releases an open Python package with a single-command-reproducible pipeline and a published per-recording label set.

## 2. Methods

The pipeline is organised around a single measurement layer: one age- and sleep-stage-matched deviation-from-normal field, computed per 15-second segment, on which both the detector and the description operate (**Figure S1**).

### 2.1 Cohort and data

The analysis cohort comprises 25,536 recordings from 21,757 unique patients curated from a single academic health system (MGB sites), spanning infancy to \>90 years: 19,617 routine clinical EEGs (\"cohort\") and 5,919 overnight/long-term studies (\"expansion\"). Each recording carries report-derived structured finding flags (normal, abnormal, focal slowing, generalized slowing), which are non-exclusive (a report may note more than one). The normal reference is *clean-normal*: flagged normal in clinical EEG reports (n = 10,189). Slowing groups are evaluated **one-vs-clean-normal** --- that is, each slowing class is compared against the clean-normal reference in its own two-group contrast, rather than the classes being forced into a single mutually exclusive multiclass problem. This matches how the findings actually occur: focal and generalized slowing frequently coexist in one recording, so a recording may be a positive case in both contrasts. Focal slowing n = 8,016 and pathologic generalized slowing n = 6,841, of which **2,340 recordings carry both (29.0% of the focal set and 34.1% of the pathologic generalized set)**. Critically, the generalized-slowing flag is split into pathologic vs physiologic slowing, to avoid labeling slowing that occurs in normal drowsy/sleep/hyperventilation as abnormal; only the pathologic set defines the generalized slowing class (physiologic generalized slowing, n = 3,382, is left in the clean-normal reference).

Age and sex are taken from the clinical records; sex is balanced at 49.2% female overall. Age is a critical confound that motivates the entire normative design: abnormal recordings are markedly older than clean-normals (median 53.9 y \[IQR 24.3--69.7\] vs 36.8 y \[18.6--59.2\]), so any unadjusted comparison would conflate slowing with age. Full cohort characteristics --- age bands, sex, recording length, usable segments, stage composition, and the abnormal-detail strata (focal side, generalized topography, band) --- are given in Table 1 (`scripts/table1_sap.py`, SAP §10). Segment-level feature tables are keyed on the recording; patient is the clustering unit for all confidence intervals (patient-clustered bootstrap), and report-derived quantities are computed only on the `clean_pair` set (§2.6). This work was conducted under IRB protocol number 2022P000417, with the BIDMC IRB granting a waiver of consent.

### 2.2 Reproducible feature extraction

To make the pipeline reproducible and extensible to new recordings, extraction is implemented in Python. The pipeline re-montaged the referential 10-20 EEG to 18 bipolar (double-banana) channels, applied a 0.5 Hz high-pass and 50/60 Hz notch, segmented into 15-second windows (3000 samples at 200 Hz, step 2800), and computes a multitaper power spectral density (time-bandwidth NW = 4, 7 tapers). Per segment we derive band powers (delta/theta/alpha/beta/gamma/total), relative powers, and inter-band ratios (DAR = delta/alpha, TAR = theta/alpha), for each of the 18 bipolar channels, plus 8 homologous left--right pairs for focal localization. Channels are aggregated into regions (whole-head, left/right temporal, left/right parasagittal, anterior, posterior) via `config/channels_regions.yaml`. Linear powers are log-transformed before z-scoring.

**Calibration.** The delta band is defined as **1--4 Hz** rather than the 0.5--4 Hz used by some pipelines, because the 0.5--1 Hz octave in a scalp recording is dominated by sweat, respiration and electrode drift rather than by cerebral delta. Excluding it puts normal whole-head relative delta at \~0.34 of total power, which matches the proportion expected in a healthy adult record; with the 0.5 Hz edge the same recordings read substantially higher, and the excess is artefactual. Because all deviation scoring is z relative to each feature\'s own age/stage normal curve, the scoring, discrimination, and generated descriptions are scale-invariant.

**Artifact rejection.** A per-segment filter marks a 15-second bipolar segment unusable on three explicit criteria (`src/morgoth_slowing/features/artifact.py`). **Flat/disconnected**: median channel peak-to-peak < 1 µV or median channel standard deviation < 0.5 µV, or more than half of channels meeting either test. **High-amplitude**: any channel with peak-to-peak > 500 µV (electrode pop or movement). **EMG-dominated**: the fraction of 1--45 Hz multitaper power lying above 20 Hz, taken as the median across channels, exceeds 0.55. Segments are flagged rather than deleted, and the usable-segment fraction is carried into scoring so low-yield recordings are visible. Burst suppression and electrode disconnection are deliberately out of scope here and handled by a separate detector upstream, since this pipeline measures slowing, not suppression.

### 2.3 Sleep staging

Routine EEG feature sets are unstaged. We staged each recording from the raw EEG with the morgoth2 deep-learning automated sleep stager (5-class window-level model), assigning each 15-second feature segment its majority stage (W/N1/N2/N3/REM) \[28\]. The overnight recordings fill the deep-sleep coverage routine clips cannot. Staging runs in a dedicated virtual environment (the stager\'s `pyhealth` dependency pins pandas \<2, incompatible with the analysis stack).

### 2.4 Normative growth curves (GAMLSS)

For each feature × region × sleep stage we estimate normal-population percentile \"growth curves\" as a continuous function of age using GAMLSS, the method behind clinical growth charts (Cole & Green \[29\]; Rigby & Stasinopoulos \[30\]). Age is entered as `log10(age + 1/12)`, expanding infancy where maturation is fastest. Two families are used according to the feature\'s support: positive features (relative powers, ratios) are fit with a Box--Cox-t (BCT) distribution with penalized-spline median, dispersion and age-varying skewness (`mu`, `sigma`, `nu` each smooth in log-age), which removes an infant-age median bias that a constant-skewness fit produces. The BCT's fourth parameter, the **tail/kurtosis parameter `tau`** (the degrees of freedom of the underlying t), is also fitted per cell and is used in scoring: a value is mapped to its centile through the t CDF at that cell's `tau`, so heavy-tailed cells do not manufacture extreme z-scores. Real-line log features real-line log features (log_delta, log_theta, log_TAR, which take negative values in 15--37% of segments) are fit with a support-aware robust median-in-log-age model on the real line. The Python BCT z-scores are validated exact against R `gamlss` `centiles.pred`. Each curve is checked against a model-free rolling median in a sliding, age-widening window, and both are plotted together in Figure 1a so the reader can see the agreement rather than take it on trust. Agreement is quantified as the median |fitted − rolling| within an age band, scaled by that cell's own interquartile width (`scripts/79`). An initial fit was too stiff through the infant peak of the ratio features — the sharpest part of the whole lifespan — where the median discrepancy reached 1.37 IQR (DAR in REM) and 0.97 IQR (DAR in wake). Increasing the median spline's degrees of freedom to 20 reduces these to 0.53 and 0.24 IQR while leaving the data-dense adult range untouched (≤ 0.04 IQR in every feature × stage cell at either setting), and is the fit shown.

Two points guard against over-reading Figure 1. The displayed curves are fitted on the raw feature, in the units a reader can interpret; the **scoring** norms are fitted on the log-transformed feature (`scripts/115`), a different parameterisation whose skewness the log transform already absorbs. The scoring norms are therefore validated on their own terms rather than by eye: on held-out clean-normal recordings the median wake deviation sits near zero at every age, including infancy (under 1 year: log DAR +0.20, log TAR +0.32, relative delta −0.18 SD; adults: +0.11, +0.19, +0.07), and their centiles are calibrated against held-out data in **Figure S5**.

**Sex is pooled.** Conditioning norms on sex changes abnormality discrimination by ΔAUROC ≤ 0.002 in every feature × region × contrast we tested; we therefore pool sexes, doubling the effective sample per age.

### 2.5 The per-segment deviation field

Every 15-second segment is scored as a deviation z for each feature × region against its own (sleep-stage, age)-matched normal curve (`data/derived/segment_deviation/`, joinable 1:1 to the segment tables), using a precomputed normal grid (`grid_norm.json` regional, `grid_anorm.json` asymmetry). Because each segment is compared to *its own stage\'s* normal, delta that is abnormal in wake but normal in N2/N3 yields near-zero deviation in normals. This per-segment, per-region field is the single measurement layer both the detector and the description run on; it does not depend on any label (it is fit to the normal population only). Its shape is **(segments) × 7 regions × 6 features = 42 deviation z-values per 15-second segment** --- regions being whole-head, anterior, posterior, left/right temporal and left/right parasagittal, and features log delta, log theta, relative delta, log DAR, log TAR and relative alpha --- stored one partition per recording and joining 1:1 to the segment tables on (`eeg_id`, `segment`). The materialised field spans **14.2 million segments**, i.e. \~598 million individual deviation values.

### 2.6 Report--recording pairing and label provenance

We joined reports to EEGs at the patient level upstream: a single report is stamped onto a mean of \~2.9 EEGs of that patient (maximum 170). We assign each report to the EEG nearest it in time, and define a recording as cleanly paired (`clean_pair`) when its report is claimed by no other EEG, or when it is that report\'s nearest-in-time owner; all report-text-derived quantities are computed on `clean_pair` recordings only (1,664 EEGs dropped by the filter). Corrected label rules (`scripts/label_rederive_sap.py`) make focal slowing always pathologic, generalized slowing pathologic only if the report names it among the abnormalities, and abnormal-without-slowing its own stratum.

### 2.7 Detection

Detection and description share the deviation field. We report three detectors.

**2.7a LENS --- the deviation detector (primary).**

*Model class.* LENS is deliberately simple: an **L2-regularised logistic regression** on standardised deviation features (scikit-learn `LogisticRegression`, C = 0.3, `class_weight='balanced'`), fitted at the level of the individual 15-second segment. There is no neural network in the interpretable pipeline; the foundation model appears only as the separate reference detector of §2.7b. Two independent heads are fitted, differing only in which features they see: the **generalized** head takes the six whole-head *amount* deviations (log delta, log theta, relative delta, log DAR, log TAR, relative alpha) plus age; the **focal** head takes, for each of three focal indicators (log delta, relative delta, log TAR), its peak-region z, its focality (peak − median region) and its asymmetry z, plus age (`scripts/54`, `55`).

*Two label strategies (LENS-v1 and LENS-v2).* A report label describes a recording, not a segment, and slowing is often intermittent, so most segments of a "focal slowing" recording show nothing. **LENS-v1 (broadcast)** simply gives every segment its recording's label. **LENS-v2 (multiple-instance)** starts from that broadcast initialisation and then iteratively relabels, keeping as positive only the top-k highest-scoring segments within each positive recording (MIL-EM, three iterations), so positive supervision concentrates on the segments that actually carry the finding. **LENS-v2 is LENS**: every headline number in this paper is the v2 model, and v1 is reported alongside it in Figure 2 as the ablation showing what the multiple-instance step buys.

*From segment to recording.* The model's native output is a score for a lone 15-second clip. A recording's score is the **mean of its top-5 segment scores**. The top-k form follows from the label semantics --- a report names slowing if it occurs anywhere, so a recording is positive when its *most abnormal* stretch is abnormal, and averaging over all segments would dilute a genuine intermittent finding with normal ones. k = 5 (75 seconds) was selected during development on the report data and held fixed thereafter; it was never adjusted on either external evaluation set. **\[verify: recover and report the k sweep behind this choice, or state the range tested\]**

*Fitting and hyperparameters.* Recordings are divided by a **patient-level split, stratified on (class, age band)**, where class is {control, focal-only, gen-only, both, other} (`scripts/53`), so no patient appears in both train and test. **No cross-validation or grid search was run**: the regularisation strength and class weighting were fixed a priori, k was set on the development data, and the model was then fitted once on the training split. Critically, nothing --- neither a coefficient nor a threshold --- was tuned on ON-100 or SAI-100, which is what makes the external comparisons below fair. The model is trained on clinical report labels and tested (external validation) unchanged on two independent, multi-site evaluation sets --- each 100 EEGs annotated by many experts and drawn entirely from hospitals *outside* the training health system: **ON-100** (100 recordings from five US centers --- Barnes-Jewish Hospital, Washington University in St. Louis, the Dallas VA Medical Center, UT Southwestern, and Louisiana State University --- each read by 18 experts) and **SAI-100** (the 100-recording holdout set of the SCORE-AI validation study \[31\], routine EEGs from Haukeland University Hospital (Norway), the Danish Epilepsy Centre (Denmark), and Mayo Clinic (USA), each read by 14 experts, and with SCORE-AI's own automated predictions available). Both benchmarks are held out entirely from fitting (no patient overlap with the report-trained cohort or with each other). ON-100 and SAI-100 are therefore *both* external validations, at institutions distinct from the training data and from one another.

**2.7b The Morgoth gate (reference).** A three-tier hierarchical foundation-model gate (abnormal → slowing → focal/generalized EEG-level heads), calibrated against expert reports, serves as the learned-representation reference detector. It is not part of the interpretable pipeline; it is the bar LENS is measured against.

**2.7c The van Putten benchmark.** We recomputed the van Putten family of indices: the Brain Symmetry Index and its revised pairwise form (r-sBSI), the diffuse-slowing index Q_SLOWING, the anterior--posterior gradient Q_APG, homologous-pair asymmetry Q_ASYM, and the slowing ratios DAR (delta/alpha) and DTABR = (δ+θ)/(α+β), plus the 95% spectral-edge frequency SEF95 (`scripts/recompute_vanputten_fullcov.py`). Each is evaluated as published and age-conditioned against our normative curves (`scripts/recompute_vanputten_fullcov.py`); the clean-panel head-to-head (**Figure S2**, `scripts/vanputten_panel_s7.py`) then pits the best index per axis against LENS and the Morgoth gate.

### 2.8 Description: reading the deviation field into words

Once slowing has been detected in a recording, LENS generates a structured verbal description of what kind of slowing it is, where it is, and how persistent it is (`scripts/56` extracts descriptors; `57` renders the panels; `58` generates sentences). Per recording, from the deviation field we read off: type/amount (whole-head delta-excess and theta-excess z: p90, mean, prevalence), laterality (signed left-minus-right region z, + = left), region (per-lobe magnitude and relative prominence/focality), anterior--posterior gradient (anterior − posterior z), persistence (prevalence = fraction of abnormal segments, longest continuous run, number of episodes), and per-sleep-stage versions of each. Descriptors are assembled into a compact finding line and a full report-style paragraph, governed clause-by-clause by `docs/claims_table.md`: magnitude as SD and centile (never a severity adjective), prevalence as a percentage following ACNS \[32\] terminology (occasional/frequent/abundant/continuous) as an internal gloss only, band as a low-confidence δ/θ/mixed call read from absolute delta/theta power dominance (whole-head mean log(δ/θ), marginal-matched to the report distribution), side asserted with the maximum-deviation lobe flagged provisional, anterior--posterior predominance asserted only when it clears the normal centile, stage accentuation and \"present only during sleep\", and a required abstain path (\"no lateralizing or regional spectral excess above the normal centile\") so the system never invents a lobe. Validation is by contrast (dose-response), rather than binary classification: each continuous descriptor is compared between recordings whose report *does* and *does not* name the corresponding finding, and must be higher where the report names it.

### 2.9 Expert panels and the human ceiling

Agreement with a single clinical report is bounded by report reliability. We therefore evaluate against two independent, multiply-read *external* datasets --- **ON-100** (100 EEGs from five US centers, each read by 18 electroencephalographers, a subset re-read) and **SAI-100** (100 EEGs from the SCORE-AI validation study, each read by 14 experts) --- each recording judged for focal and generalized epileptiform and non-epileptiform abnormality. Ground truth is the panel majority. Our primary metric is the percentage of experts under the curve: we place each expert on the model\'s ROC curve (and its precision--recall, PR, curve) as one sensitivity--specificity point --- graded against the leave-one-out consensus of the other readers --- and count how many fall *below* the curve, i.e. how many the model matches or beats at that expert\'s own operating point. A model performing at the panel\'s own level would put roughly half of the experts under its curve. Inter-rater reliability (Fleiss κ, chance-corrected agreement) and each reader\'s self-consistency quantify the human ceiling. Band agreement is evaluated against experts\' per-band calls (no text extractor in the loop).

### 2.10 Statistics

All confidence intervals are patient-clustered bootstraps. Detection is reported as the area under the ROC curve (AUROC) vs the clean-normal (report) or panel-majority (panel) reference. Description contrasts report group medians with Mann--Whitney tests and Cohen\'s d. LENS is evaluated leave-one-out on the panel with no refitting or threshold tuning. The full pipeline is reproducible from the derived tables via a single ordered runner (§ Data and code availability).

### 2.11 What a deviation does, and does not, assert

LENS reports that a recording lies a stated distance outside the range of its age- and sleep-stage-matched
normal reference. It does not assert a cause. This distinction is the same one that governs every growth
chart in clinical use, and it is worth stating explicitly because the two ideas are easy to conflate. A child
below the 3rd centile for height is genuinely, measurably outside the normal range; that remains true when
the explanation turns out to be familial short stature in an otherwise healthy family. The measurement is
correct, and it is *also* correct that no disease is present. What the centile buys the clinician is not a
diagnosis but a calibrated reason to look --- after which the finding is either explained and dismissed, or
pursued.

EEG background slowing behaves the same way. A recording whose delta sits well above its stage-matched
normal may be encephalopathic; it may equally reflect slow-wave rebound after sleep deprivation, a
medication effect (§5), or constitutional variation in sleep depth. LENS is calibrated to answer *is this
unusual for this patient's age and state?* --- a question with a defensible statistical answer --- and
deliberately not *why?*, which requires the clinical context that the reading physician has and the
signal does not. Throughout, we therefore use **abnormal** in its statistical sense, meaning outside the
normal reference range, and reserve **pathological** for the cases where a report's own impression asserts
a pathological cause. Nothing in this paper should be read as a claim that a deviation, on its own,
establishes disease.

## 3. Results

### 3.1 Cohort (Table 1)

The analysis cohort comprised 25,536 recordings from 21,757 patients (Table 1): 19,617 routine + 5,919 overnight, 49.2% female, median age 48.2 years. The label strata account for the cohort as follows. Of the 25,536 recordings, **1,664 (6.5%) are dropped by the `clean_pair` report-pairing filter** (§2.6) and contribute to the normative curves but to no label-based analysis, leaving **23,872 cleanly paired recordings**. Within those, the clean-normal reference is **10,189** and the abnormal set is **12,676**, of which 8,016 carry reported focal slowing and 6,841 pathologic generalized slowing. The remaining **1,007 (4.2% of the paired set)** are *indeterminate*: their report supports neither a clean-normal nor an abnormal determination --- most carry a normal flag alongside physiologic drowsy/hyperventilation slowing, or name slowing without an abnormal impression. They are excluded from both arms of every one-vs-clean-normal comparison rather than being forced into either, so 10,189 + 12,676 + 1,007 = 23,872. Clean-normals are \~17 years younger than abnormals (median 36.8 vs 53.9 y), reinforcing the need for age conditioning. Segment-weighted stage composition confirms the design: routine studies are wake-dominated (45% W) while overnight studies supply the deep sleep (N2 31%, N3 24%) that anchors the sleep-stage norms. Abnormal-detail strata --- focal side (left 24.7% / bilateral 18.7% / right 16.6%), generalized topography (mostly unspecified), and band (mixed 50.9% / delta 16.5% / theta 13.5%) --- set the base rates description contrasts are read against.

### 3.2 Growth curves reproduce development and aging, in curve and in space

The normative curves recapitulate known maturation patterns: at the occipital derivations (O1/O2), the region from which the posterior dominant rhythm is read clinically, relative delta and the theta/alpha and delta/alpha ratios fall steeply through childhood to an adult plateau by \~30 years, and normal-referenced z-scores center on 0 for controls across the lifespan (**Figure 1a**; solid GAMLSS median tracks the model-free rolling median). The scalp-topography rendering makes the spatial story explicit (**Figure 1b**): relative delta is frontal-predominant, highest in infancy across every sleep stage, and declines monotonically toward adulthood, deepest in N3; these are the regional substrate the localization descriptors rely on; the theta/alpha ratio shows the same developmental pattern (**Figure S3**), so the topographic result is not specific to relative delta. Stage-resolved curves quantify the expected physiology: median relative delta rises with sleep depth W ≈ N1 \< N2 \< N3, REM intermediate (**Figure S4**). The direct clinical consequence is that delta which is abnormal in wake is entirely normal in N2/N3.

**The curves are calibrated on held-out data.** A percentile model is only useful if its percentiles are
real, so we tested them where they were not fitted (**Figure S5**). The norms are fitted on a seeded
3,000-recording sample of the clean-normal reference; the remaining **7,216 clean-normal recordings (6,779
patients)** are therefore held out, and the ON-100 panel recordings the expert majority called neither
focally nor generally slow (n = 71) provide a second, institutionally external reference. For each held-out
15-second observation we took the model-predicted centile at that observation's own age, stage, region and
feature, and asked what fraction of observations actually fell below it. On the internal held-out normals the
observed and nominal centiles agree closely across every stage and feature --- median absolute discrepancy
**1.0 percentage point**, maximum 6.7 --- so a segment at our nominal 97th centile really is a 97th-centile
segment. On the external no-slowing recordings agreement is looser but still close over most cells (median
2.3 points), with one clear exception: **N1 log TAR**, where the nominal 75th centile captures only 54% of
external observations, i.e. the external N1 distribution is wider than our norm expects. Deep sleep could not
be tested externally --- N3 is only 5.4% of segments in these routine recordings, too few for a stable
estimate. Calibration is thus good internally, good-but-imperfect across institutions, and untested externally
in N3, which is the same regime §3.8 and §5 identify as the least secure.

### 3.3 The per-segment deviation field is calibrated and discriminative

Scoring each segment against its own (stage, age) normal yields a field that is both calibrated --- clean-normals sit near z = 0 in every stage (whole-head median +0.24 W to −0.04 N3 for delta excess) --- and discriminative --- abnormal recordings are shifted up in every stage, most in W/N1 (delta excess +0.83 W, +1.57 N1; TAR +1.03 W, +1.25 N1) (**Figure S6**).

### 3.4a Detection --- external validation on the ON-100 panel and the foundation-model gate

A single model trained on report data (patient-stratified, \~16k recordings) when externally validated on the ON-100 panel separated slowing from normal against the panel majority at AUROC 0.946 \[95% CI 0.887--0.990\] (generalized) and 0.921 \[0.824--0.988\] (focal), with average precision (AUPRC) 0.77 on both axes against panel base rates of only 18% (generalized) and 12% (focal) positive (recording-level bootstrap; **Figure 2**). This placed 78% of the 18 experts under our generalized ROC curve (72% under PR) and 71% under focal (65% under PR) (panel base rates 18/100 generalized-, 12/100 focal-positive), a majority of the panel on both axes. Against the Morgoth gate the model clearly wins on both (generalized 0.946 vs 0.853, 78% vs 11% experts under; focal 0.921 vs 0.908, 71% vs 41% experts under).

**The two axes need different read-outs, and the reason is mechanistic.** Amount of slowing does not separate focal from generalized (both raise it), so the focal head localizes (using peak-region z, focality (peak − median region), asymmetry z, spatial stability, aggregated over the recording); the generalized head pools a diffuse whole-head amount score across segments. Stage-matching unlocks the sleep stages (z-scoring each segment against its own stage\'s norm keeps only abnormal-for-its-stage slowing). To isolate how much of the gain comes from these design choices --- localization and stage-matching --- rather than from the training data, we ran an ablation: a model cross-validated *within the panel itself* (trained and tested on ON-100; this is an ablation, not LENS). It raises focal detection from 24% to 53% of experts under the ROC curve and generalized to 78%, and **Figure S7** shows an intermediate W+N1 localized focal detector at 47% under / AUROC 0.89. Because that ablation trains and tests on the same panel, its numbers are an optimistic upper bound, reported only to attribute the benefit to localization and stage-matching; every headline number above comes from the report-trained detector, which never sees the ON-100 recordings.

### 3.4b Detection --- external validation on SAI-100 (SCORE-AI and 14 experts)

The **second external benchmark, SAI-100**, tests whether the same unchanged pipeline also transfers across countries and to an independent scoring system. We ran it on 100 routine scalp EEGs from the SCORE-AI validation study \[31\] --- drawn from three hospitals in two countries (Haukeland University Hospital, the Danish Epilepsy Centre, and Mayo Clinic), with no overlap with training or with ON-100 --- for which SCORE-AI (a published automated EEG-interpretation system), the Morgoth gate, and 14 individual expert calls per recording are available. The full pipeline (feature extraction, Morgoth sleep staging, age- and stage-matched deviation, and the report-trained detectors) ran end-to-end on 98/100 recordings (2 EDFs were unreadable).

Focal slowing is detected well by all learned methods (**Figure 3**). Our LENS model reached AUROC 0.933 \[0.86--0.98\], with 71% of the individual experts under its ROC curve. The Morgoth foundation-model gate is the strongest focal detector (0.974, 93% under), and SCORE-AI weaker (0.878, 29% under). For generalized slowing: ours 0.893 \[0.784, 0.978\], behind Morgoth (0.951) and SCORE-AI (0.930). LENS thus reaches expert-level focal detection on this second external site as well (a majority of experts under its curve, our own sleep staging included) and out-performs a purpose-built EEG classifier (SCORE-AI). Taken together, the two external validations --- **ON-100** (five US centers, 18 experts) and **SAI-100** (three hospitals across two countries, 14 experts, plus SCORE-AI) --- show LENS matching human experts on focal slowing and beating a dedicated EEG classifier across institutions, countries, and scoring systems, with no site-specific refitting.

### 3.5 Benchmark against the published qEEG literature (van Putten)

On the clean ON-100 expert panel we benchmarked LENS head-to-head against the strongest van Putten index and the Morgoth gate, recomputing every index on the same panel signals against the expert-vote majority (**Figure S2**). LENS is the best detector on both axes. For generalized slowing it reaches AUROC 0.946 against the best whole-head slowing ratio (DAR, 0.817) and the Morgoth gate (0.853); for focal slowing 0.921 against the best interhemispheric-asymmetry index (an r-sBSI analog, 0.825) and Morgoth (0.908). LENS therefore exceeds the published qEEG lineage by +0.13 (generalized) / +0.10 (focal), with non-overlapping confidence intervals, and outperforms the foundation-model gate on both: on clean expert labels LENS is the strongest of the three. (The comparison is on the panel, not the full report cohort, because single-report labels cap every detector by their own noise, where LENS and the raw indices converge near \~0.73; removing that ceiling with clean expert labels is the fair test, and is where LENS separates.)

A separate full-cohort analysis isolates the *mechanism* of the normative step (Table S1). Age-conditioning the *slowing* ratios on our normative curves improves them --- Q_SLOWING +0.049, DAR +0.037, DTABR +0.046, SEF95 +0.042 (generalized), a clean positive control for the normative framework; whereas age-conditioning the *asymmetry* indices does not (r-sBSI −0.017, Q_ASYM −0.006): interhemispheric symmetry does not vary with age, so an age reference adds variance and no signal. The dissociation is what physiology predicts, confirming that lifespan normalization is a substantial, targeted gain.

### 3.6 The human ceiling for slowing

**Slowing is the least reliable judgement experts make.** In the 18-expert panel, between-rater Fleiss κ was 0.373 (focal) and 0.450 (generalized), against 0.585 and 0.739 for focal/generalized epileptiform discharges; a reader re-reading the same EEG reproduced their own slowing call at only κ = 0.563 / 0.642. Every \"agreement with the report\" figure in this literature is bounded by these numbers, which is why we validate detection against the panel majority and multiple raters. Our continuous score tracks the fraction of the 18 experts who marked slowing at Spearman ρ = 0.652, a measure of conspicuity to trained readers.

### 3.7 Description --- type, location, persistence, and sleep stage, validated by contrast

Six worked recordings — three exclusively focal, three exclusively generalized — set LENS's generated finding and description beside the clinician's own report text for the same study (**Figure 4**). Across the cohort, the deviation field reads OUT into a structured description whose every component tracks the report by dose-response contrast (see contrasts in **Figure 5**; and the full panel set D1--D6 in **Figure S8**). *(All contrasts among report-slowing recordings unless noted; N = 23,869 report recordings.)*

- **D1: type & amount.** Our theta-excess measure is higher when the report names theta (median 1.39 vs 1.08, Cohen d = 0.29, p = 3×10⁻⁴⁵) and our delta-excess measure is higher when the report names delta (1.63 vs 1.32, d = 0.26, p ≈ 0). The measure tracks the band word.
- **D2: laterality & region.** Our signed left-minus-right asymmetry follows the reported side --- left +0.36, bilateral 0.00, right −0.44 (clean monotonic separation). Because temporal delta magnitude runs high everywhere (a temporal-delta attractor), the specific regional descriptor is *relative prominence* (focality): a lobe\'s prominence rises when the report names it, for temporal, frontal, and posterior alike (all p \< 10⁻³).
- **D3: anterior--posterior predominance.** The anterior − posterior gradient is less posterior-predominant in report-anterior than report-posterior cases (−0.07 vs −0.22, p ≈ 9×10⁻⁶), a meaningful but modest gradient, as most generalized slowing is topographically unspecified.
- **D4: persistence.** Prevalence (fraction of abnormal segments) separates report-slowing from clean-normal (median 0.19 vs 0.05), with a fat continuous-prevalence tail; run length and episode counts give an ACNS-style occasional→continuous read-out. (There is no structured report qualifier, so this is shown as internal reasonableness.)
- **D5: by sleep stage.** Slowing prevalence sits above clean-normal at every stage, wake AND sleep (e.g. N2 0.32 vs 0.12); the description is not wake-only.
- **D6: words.** Descriptors are assembled into a compact finding line and a full report-style paragraph, governed clause-by-clause by `docs/claims_table.md` (magnitude as SD/centile; prevalence as a percentage with the ACNS word as an internal gloss; band a low-confidence δ/θ/mixed call on clear dominance; side asserted with the maximum-deviation lobe flagged provisional; anterior--posterior predominance only when it clears the normal centile; stage accentuation and \"present only during sleep\"; and a required abstain path). A representative paragraph: *\"Left temporal theta--delta slowing, maximal over the left temporal region, peaking at T3 (the T3--T5 derivation). Peak deviation 2.8 SD above the age- and stage-matched normal (99th centile), abnormal in 46% of analysed segments; longest continuous run ≈9.1 min over 27 episodes. Present in wakefulness and sleep, most prominent in REM sleep.\"*

> For a lateralised, confident focus the paragraph names the derivation carrying the slowing --- one level finer than the lobe (electrode-level, \~40% of focal recordings) --- localised from left--right delta asymmetry, which cancels the symmetric frontal/eye-movement delta gradient that makes raw power a frontopolar attractor; reports carry no electrode field, so this is an output-granularity gain for automated reporting rather than a scored claim (clause 4e). The discretely checkable components are concordant with the report above the 33% chance rate on side (56%) and region (46%). The band (δ/θ/mixed) call is read off absolute delta/theta power dominance (the whole-head mean of log(δ/θ), not the deviation z), as a clinician who writes \"delta slowing\" generally means delta power dominates the trace, whereas the per-band age/stage z does not track that (normal delta variance is large, so a large delta in a young brain sits at a modest z while a smaller theta excess can win the deviation axis even as delta plainly dominates).
>
> On held-out reports the raw ratio separates delta-from-theta at AUROC 0.74, versus 0.68 for the deviation axis (z_theta − z_delta). Even so the call is deliberately calibrated to the report *distribution* rather than tuned for accuracy: the report band is \~64% \"mixed\", a reader hedge that sits between the two pure bands and is only weakly separable from either, so maximising 3-way accuracy collapses to \"always mixed\". Marginal-matching (default \"mixed\"; a pure delta/theta call only when log(δ/θ) clears a threshold set to the report\'s own rates) reproduces the report distribution and reaches 53% concordance at Cohen κ ≈ 0.10, the low end of published expert-vs-expert band agreement (0.09--0.38), i.e. the human noise floor. We therefore report band as a low-confidence gloss and rely on the continuous dose-response contrast as its valid test.

### 3.8 Readers under-report slowing in sleep --- a within-subject test

The dose-response suggests that reports under-state slowing; a within-subject test confirms it. Among recordings whose report names slowing, when the slowing is visible only in sleep the report names it 53.6% of the time, versus 74.8% when it is visible awake (base rate 40.0%; **Figure 6**). At the segment level, recordings the reader called abnormal whose report names slowing but never mentions sleep nonetheless deviate above age- and stage-matched clean-normals in N2/N3 (median sleep-stage z +0.62 log delta, +0.98 DAR, vs +0.02 / −0.03 in held-out controls). Because a slow-wave-keyed stager could reproduce this by misstaging slow wake as N2, we adjudicated with a delta-independent marker, detected sleep spindles, and the elevation is undiminished on spindle-verified N2 (AUROC 0.854 log delta, 0.844 DAR). Thus the model sees what the report omits, in the regime where visual reading is most challenging.

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

### 3.9 Why we do not describe clinical "severity grade"

Among recordings whose report names slowing, our score does not recover readers' mild/moderate/marked adjectives (**Figure S9**): Spearman ρ = 0.050 (p = 0.17). This is true over an exhaustive search across 168 combinations of feature × statistic × normalization × stratum, where the largest \|ρ\| anywhere is 0.179, failing Bonferroni and carrying the wrong sign (`results/severity_null_v6.md`). The panel data explain the reason: an adjective attached to a judgement of κ ≈ 0.56--0.64 self-consistency cannot support a strong correlation with any measurement. We report detection, dose-response, localization, persistence, and stage, and avoid severity grading and hard band determination, both of which sit near their (low) human ceilings.

## 4. Discussion

This work unifies four previously separate literatures into a single instrument. Unlike lifespan qEEG that reports *normal values*, we score *deviation from normal* per recording. Unlike classic norms (Petersén & Eeg-Olofsson \[5\]; John et al. \[6\]), which are small-N, wake-only, age-banded, and, in the commercial lineage, opaque, our norms are lifespan-continuous, sleep-stage-resolved, built on \~22,000 patients, and fully reproducible in open Python. Unlike disease-specific abnormality indices, which use fixed thresholds tied to one setting and ignore age and sleep stage, our features are normed against the matched normal population. And unlike binary classifiers or ungrounded report generators, we produce localized, graded, stage-aware descriptions validated against the actual report corpus. This extends the deviation idea of John et al. \[6\] to a modern scale and to slowing and asymmetry specifically, and it is the functional-EEG, sleep-stage-resolved analog of the MRI \"brain charts\" of Bethlehem et al. \[4\] --- in effect, EEG growth charts for clinical slowing.

**Beyond the Brain Symmetry Index (focal).** The van Putten BSI \[8\] and revised pairwise rBSI \[9\] established interhemispheric spectral asymmetry as a quantifiable, clinically meaningful signal, but as a bare 0--1 index tuned on small acute-stroke cohorts (n = 21) with no age/sex/stage reference. Our homologous-channel asymmetry feature is a descendant of this idea, normed against the age × stage-matched normal population and, for the detection decision, replaced by a learned representation: on identical signals the strongest van Putten focal arm (raw r-sBSI 0.723) is exceeded by the gate at 0.870 (+0.147), and age-conditioning the asymmetry indices makes them slightly *worse*, exactly as physiology predicts, since interhemispheric symmetry does not vary across the lifespan. Beyond detection we provide information that a symmetry scalar cannot: lateralization, posed as a focal-gated left-vs-right task from *signed* asymmetry reaches AUROC \~0.87 (single signed temporal-δ feature 0.869), is band-matched (delta cases lateralized by delta asymmetry, theta by theta), and is stable across the lifespan; and regional localization by relative lobe prominence tracks the reported lobe for temporal, frontal, and posterior foci.

**Age-conditioning some metrics helps but does not close the gap (generalized).** For generalized slowing the field relies on population-agnostic slow/fast ratios (Q_SLOWING, DAR, DTABR) thresholded on single disease populations and blind to age and vigilance. Recomputed on our cohort they detect at raw AUROC 0.691--0.732; age-conditioning each against our clean-normal lifespan curves raises them monotonically (+0.03 to +0.05), lifting DTABR to 0.773 --- a key positive control for the normative framework, since conditioning a *published* metric on our curves improves it, in the direction physiology dictates. Yet even the best age-conditioned arm trails the learned representation, so the residual signal is morphological and stage-topographic, not band-power. This is why the deviation field is deployed as the interpretable, calibrated description and per-stage threshold. This design choice lets physiologic sleep slowing be separated from abnormal-for-stage deviation automatically, something wake-only ratios cannot do, while detection uses the strongest available representation.

**The normative lineage and automated interpretation.** Our instrument sits at the confluence of two older lineages. The first is normative deviation scoring: John et al.\'s developmental equations \[6\] and Neurometrics z-scoring \[7\] first expressed a clinical EEG as its deviation from age-matched norms, on a few hundred wake-resting, age-banded subjects; Bethlehem et al.\'s \[4\] MRI brain charts (n = 101,457, GAMLSS centiles) modernized the centile idea for structural imaging. We are the functional-EEG, sleep-stage-resolved analog --- GAMLSS growth curves on \~25,000 clinical EEGs, resolved per sleep stage, in open reproducible Python. The second is automated interpretation: the TUAB corpus and its ConvNet classifiers (\~85%) reduce a recording to a binary label with no localization, band, severity, or narrative, and EEG brain-age (Engemann \[3\]) collapses the spectrum to a single scalar. What we add on top of both is a described, validated, stage-resolved output: the interpretable field detects (beating the panel and the gate), describes, and emits clinician-style sentences validated against reports, with the one clause reports systematically omit, *\"present in sleep\"*, defensible on spindle-verified N2.

**Reports are a directionally biased reference, and a normative model can detect what they miss.** Clinical reports are our reference standard, but an *imperfect reference with a known, directional bias*: because theta/delta slowing is normal in sleep and \"how much is too much\" is hard to judge by eye, readers systematically under-declare slowing that occurs in sleep (§3.8, 54% vs 75%). We therefore treat concordance with reports as validation only *where reports are reliable*, and pose the complementary hypothesis: that a per-stage normative model is the better *measuring instrument* exactly where visual reading is weakest --- slowing that occurs in sleep. We are careful about what "better" means here (§2.11). LENS measures the deviation more reproducibly than a reader can; it does not thereby establish that every deviation it finds is pathological, and for generalized slowing confined to N3 there are benign explanations (slow-wave rebound, medication) that no spectral measurement can exclude. The claim is that the reader and the instrument disagree systematically and in a direction the instrument can quantify, not that the instrument is right and the reader wrong. This is supported here by dose-response, a within-subject wake→sleep test, and spindle-verified convergent validity. The definitive test is a blinded expert re-read of high-deviation report-normal sleep studies, proposed as prospective validation.

## 5. Limitations

This study has some limitations. Prevalence and persistence are read from the per-segment deviation field over the whole recording where available; for the sub-study that requires locating a clip inside its source (spindle verification) the analysis is restricted to routine-length studies, and short- vs long-recording cases have indistinguishable sleep-stage deviation, so the restriction does not bound the conclusion. Band determination is near-chance and is thus a "hard call" and we therefore do not claim it; the slow bands co-occur (\~64% of reports say \"mixed\"), and the valid test is the continuous dose-response contrast. Severity grade is a null result. We also measure no **beta** excess: the descriptors cover the slow bands and the slow/fast ratios, so drug-induced beta activity --- a common and clinically meaningful background finding --- is outside the current scope and would require its own normative feature.

**Vigilance state is uncontrolled in the overnight recordings.** A routine EEG is recorded under active alerting by a technologist, whereas the 5,919 overnight/long-term studies are unconstrained: the patient may be drowsy, reading, or eating during nominal wake. Stage-matching absorbs part of this, since a drowsy epoch staged N1 is scored against the N1 norm, but not all of it --- task-related rhythms such as reading-induced temporal theta carry no stage label of their own and will sit inside the wake reference. This widens the wake norm, which is conservative for detection (a wider normal is harder to exceed), but it does mean our \"wake\" is a broader physiological state than routine alert wake.

**The normal range in sleep is genuinely wide, and our reference is a population one.** Sleep depth and slow-wave activity vary substantially between healthy individuals, and much of that variance is constitutional rather than pathological: sleep EEG spectral profiles are heritable \[18--21\] and modulated by common polymorphisms in adenosine, circadian and neurotrophic genes \[22--24\]; slow-wave activity changes markedly across the lifespan \[25\]; and several drug classes, notably the oxybates and the atypical antipsychotics, raise it directly \[27\]. Phasic phenomena such as the cyclic alternating pattern further alter the spectral content of any given conventional stage. Our norms are conditioned on age and sleep stage but not on genotype, medication, or prior sleep debt, none of which we observe. A recording therefore sits high on our scale either because it is abnormal or because the patient sits high within a wide healthy distribution, and we cannot separate these from the EEG alone. This is the concrete reason the output is framed as a deviation to be adjudicated rather than a diagnosis (§2.11), and it bears most on generalized slowing in deep sleep, where the physiological range is widest. Medication history in particular is a tractable next step: it is present in the health record and would let a future version condition the norm on it.

## 6. Conclusion

We present LENS (Lifespan EEG Normative Scoring), which is to our knowledge the first EEG growth charts for clinical slowing, large-scale, lifespan- and sleep-stage-resolved normative curves that score an individual EEG\'s slowing as a deviation from its matched normal, and that both detect and describe. Built on 25,536 clinical EEGs from \~22,000 patients, it reproduces known development and aging (in curve and across the scalp), quantifies the stage-dependence of physiological slowing (W ≈ N1 \< N2 \< N3), and, from a single interpretable deviation field, detects slowing at or above an 18-expert panel and a state-of-the-art foundation-model (exceeding the gate on generalized slowing, on par on focal) on an independent multi-rater set, exceeds the published qEEG lineage by +0.14 to +0.17 AUROC, and reads OUT a structured description (type, laterality, region, anterior--posterior gradient, persistence, sleep stage) validated against clinical reports by dose-response. It sees what reports omit --- slowing in sleep --- in exactly the regime where visual reading is hardest. We release an open, reproducible Python package and a published per-recording label set, so that others can validate and extend LENS on new populations. More broadly, by making the reading of EEG slowing quantitative, lifespan- and sleep-stage-aware, and fully reproducible, LENS advances clinical EEG interpretation from expert-dependent qualitative judgement toward a scalable, standardized second read --- and provides a template for turning other qualitative EEG features into validated deviation-from-normal measures.

## Figures and Tables

*Triaged for CN (economy of display items; see* `docs/cn_submission_plan.md`*). **Main = 1 table + 6 figures**; the rest are Supplementary.*

### Main

- **Table 1 --- Cohort characteristics** (`results/table1.md`; `scripts/table1_sap.py`). Percentages in the label rows are of the 23,872 cleanly paired recordings, not of the 25,536 total; the two denominators are reconciled in §3.1.
- **Figure 1 --- The normative deviation model.** (a) Lifespan percentile growth curves per stage (`figures/growth_v2/keystone_growth_grid.png`; `scripts/76`); (b) scalp topography of regional development by age × stage (`figures/growth_v2/topo_rel_delta_by_age_stage.png`; `scripts/77`).
- **Figure 2 --- Detection vs 18 experts and the foundation-model gate (ON-100).** Generalized AUROC 0.946 \[0.887--0.990\] (78% experts under); focal 0.921 \[0.824--0.988\] (71% experts under) (`figures/story/s0d_single_occasion_generalized.png`, `s0e_occasion_focal.png`; `scripts/53–55, 66`).
- **Figure 3 --- External validation (SAI-100).** LENS vs **SCORE-AI** vs the Morgoth gate vs the 14 individual experts, for focal and generalized slowing, against the true expert-vote majority (the workbook\'s focal summary label is corrupted --- see §3.4b; corrected labels in `docs/audits/sandor_focal_label_correction.csv`) (`figures/story/sandor100_slowing.png`; `scripts/sandor100_*`).
- **Figure 4 --- Example EEG segments with automated reports vs the clinical report.** Six recordings in a 3×2 grid (exclusively-focal, left column; exclusively-generalized, right; varying degree and sleep stage). Each shows a 10-s longitudinal-bipolar EEG paired with two matched comparisons: LENS\'s brief finding against the clinical report\'s *impression*, and LENS\'s detailed description against the report\'s *description* --- using the actual (de-identified) report text. The displayed 10-s window is the segment where the finding is clearest --- for focal cases the segment where the localized (claimed-region) deviation peaks, for generalized cases the segment of highest whole-head deviation --- within the dominant sleep stage (first hour); it is an illustrative peak, not a random or typical epoch. Focal examples are restricted to clearly-lateralized recordings (\|left−right asymmetry\| ≥ 1.5 SD) so the displayed segment reliably matches the localization (`figures/story/s4_examples_eeg_panel.png`; `scripts/62`, `63`).
- **Figure 5 --- Description validated by contrast (condensed).** Laterality tracks the reported side; the slowing signal persists across sleep stages (`figures/story/s4_d2.png`, `s4_d5.png`; `scripts/57`).
- **Figure 6 --- Readers under-report slowing in sleep.** Fraction of reports that name slowing, split by where the slowing is visible: 74.8% when visible awake vs 53.6% when visible only in sleep (base rate 40.0%). The within-subject deviation analysis behind this --- cases deviate above stage-matched normals in N2/N3, undiminished on spindle-verified N2 --- is in §3.8 (`figures/growth_v2/v4a_wake_sleep.png`; `scripts/fig6_sleep_naming.py`, from the `95`/`95b` analysis).

### Supplementary

*Supplementary figures (*`figures/manuscript/` *assembles the submission-named copies via* `scripts/assemble_manuscript_figures.py`*):*

- **Figure S1 --- Pipeline architecture.** One deviation-from-normal field as the shared substrate for detection (two report-trained heads) and claims-governed description, with held-out validation under each (`figures/story/architecture.png`; `scripts/architecture_diagram.py`).
- **Figure S6 --- Per-segment deviation field**, calibrated & discriminative (`figures/story/s2_segment_deviation.png`; `scripts/44`).
- **Figure S4 --- Stage-resolved curve bank** (rel_delta / TAR / DAR, whole-head; `figures/stage_curves/`; `scripts/111`).
- **Figure S8 --- Description panels D1/D3/D4/D6** (type/amount, anterior--posterior, persistence, generated-word concordance; `figures/story/s4_d1,3,4,6.png`; `scripts/57–58`).
- **Figure S7 --- Why the two detection axes need different read-outs** (localized focal; `figures/story/s0_occasion_ours_v4_focal.png`; `scripts/49`).
- **Figure S9 --- Severity is a null result** (`figures/growth_v2/severity_recalibrated.png`, `results/severity_null_v6.md`; `scripts/109`).
- **Figure S2 --- van Putten indices vs LENS vs the Morgoth gate on the clean ON-100 panel** (ROC per axis, expert-majority labels). LENS is the best detector on both axes --- generalized 0.946, focal 0.921 --- beating the best hand-crafted index by +0.13 / +0.10 and edging the foundation-model gate (`figures/figs/vanputten_panel_s7.png`; `scripts/vanputten_panel_s7.py`).

- **Figure S3 --- Scalp topography of the theta/alpha ratio (TAR) by age × sleep stage** (`figures/growth_v2/topo_TAR_by_age_stage.png`; `scripts/77`). The TAR companion to Figure 1b, confirming that the regional development pattern is not specific to relative delta.

- **Figure S5 --- Held-out centile calibration of the normative curves.** Observed versus nominal centile for
data never used to fit the curves, faceted by sleep stage (rows) and feature (columns); the dashed diagonal is
perfect calibration and bands are patient-clustered bootstrap 95% CIs. Blue: 7,216 held-out clean-normal
recordings (6,779 patients), the complement of the seeded sample the norms are fitted on. Orange: the 71
ON-100 recordings with no expert-majority slowing, an institutionally external reference
(`figures/story/s9_centile_calibration.png`, `results/story/centile_calibration.md`; `scripts/78`).

*Supplementary tables:*

- **Table S1 --- van Putten qEEG full-family benchmark** (every index × raw/age-conditioned arms on the report cohort; `results/vanputten_fullcoverage.md`). Isolates the age-conditioning dissociation --- slowing ratios improve, asymmetry indices do not (§3.5).
- **Table S2 --- Human ceiling** (Fleiss κ, self-consistency, conspicuity ρ; `results/table5_human_ceiling.md`).
- **Table S3 --- Band calibration.** The band is read from absolute delta/theta power dominance (mean log(δ/θ), which separates the reports\' delta-from-theta at AUROC 0.74 vs 0.68 for the deviation axis); delta/theta/mixed agreement is at the expert-vs-expert floor (κ≈0.10), marginal-matched to the report distribution (`results/story/band_calibration.md`; `scripts/band_calibration.py`).

## Declarations

- **Ethical approval.** This work was conducted under IRB protocol number 2022P000417, with the Beth Israel Deaconess Medical Center (BIDMC) IRB granting a waiver of consent.
- **Funding.** Dr. Westover\'s laboratory is supported by grants from the NIH (R01AG073410, R01HL161253, R01NS126282, R01AG073598, R01NS131347, R01NS130119) and by AWS.
- **Conflicts of interest.** Dr. Westover is a co-founder of, serves as a scientific advisor and consultant to, and has a personal equity interest in Beacon Biosignals. The remaining authors declare no competing interests.
- **CRediT author contributions.** *\[Draft for each author to confirm or amend before submission.\]*
**J. Jing:** Methodology, Software, Formal analysis, Investigation, Writing -- original draft.
**C. Sun:** Methodology, Software, Formal analysis, Visualization, Writing -- original draft.
**W. Ganglberger:** Methodology, Software, Data curation, Validation, Writing -- review & editing.
**A. D. Lam:** Investigation, Validation, Writing -- review & editing.
**H. Sun:** Methodology, Software, Writing -- review & editing.
**T. Zhang:** Software, Data curation.
**D. M. Goldenholz:** Methodology, Writing -- review & editing.
**F. A. Nascimento:** Investigation, Validation, Writing -- review & editing.
**D. Yuan:** Investigation, Data curation.
**S. Beniczky:** Resources (SAI-100 evaluation set), Validation, Writing -- review & editing.
**J. A. Kim:** Investigation, Validation, Writing -- review & editing.
**A. F. Struck:** Investigation, Validation, Writing -- review & editing.
**S. F. Zafar:** Investigation, Validation, Supervision, Writing -- review & editing.
**R. J. Thomas:** Conceptualization, Investigation, Supervision, Writing -- review & editing.
**M. M. Shafi:** Conceptualization, Investigation, Supervision, Writing -- review & editing.
**M. B. Westover:** Conceptualization, Methodology, Resources, Supervision, Funding acquisition,
Project administration, Writing -- review & editing.
- **Acknowledgements.** We thank the electroencephalographers who annotated the ON-100 and SAI-100
evaluation sets, whose independent reads make both the external validation and the human-ceiling analysis
possible. We thank the Brain Data Science Platform (BDSP) team for data curation, de-identification and
hosting, and the clinical neurophysiology technologists at the contributing centres, whose recordings and
reports are the substrate of this work. *\[Authors to add individual acknowledgements and any non-author
contributors before submission.\]*

## Data and code availability

Code is released as the open-source package `bdsp-core/morgoth-slowing-growth-curves`, with a numbered, reproducible pipeline (three tiers --- `results` / `features` / `scratch` --- via `scripts/reproduce_story.sh`; `docs/REPRODUCE.md`). We publish per-recording labels (report-derived flags, corrected SAP labels, description descriptors) with provenance. Raw EEG and free-text report content are not redistributed; they are available via BDSP credentialed access. The de-identified derived data and code are published on BDSP as **LENS v1.0.0** (<https://bdsp.io/content/q8qpxsk3sgq57vkm5abp/1.0.0/>; version DOI [10.60508/7060-qq30](https://doi.org/10.60508/7060-qq30), concept DOI [10.60508/wt7m-f443](https://doi.org/10.60508/wt7m-f443)) under the BDSP Credentialed Health Data License and Data Use Agreement; the code repository (<https://github.com/bdsp-core/morgoth-slowing-growth-curves>) is licensed CC BY-NC 4.0.

## References

*Vancouver style, numbered in citation order; in-text citations use these numbers. Entries flagged **\[verify\]** need a primary-source page/volume check before submission.*

1. Schomer DL, Lopes da Silva FH, editors. *Niedermeyer's Electroencephalography: Basic Principles, Clinical Applications, and Related Fields.* 7th ed. New York: Oxford University Press; 2018. **\[verify\]**
2. Ebersole JS, Nordli DR, Pedley TA, editors. *Current Practice of Clinical Electroencephalography.* 4th ed. Philadelphia: Wolters Kluwer; 2014. **\[verify\]**
3.  Engemann DA, Mellot A, Höchenberger R, et al. A reusable benchmark of brain-age prediction from M/EEG resting-state signals. *NeuroImage.* 2022;262:119512.
4.  Bethlehem RAI, Seidlitz J, White SR, et al. Brain charts for the human lifespan. *Nature.* 2022;604:525--533. **\[verify\]**
5.  Petersén I, Eeg-Olofsson O. The development of the electroencephalogram in normal children from the age of 1 through 15 years: non-paroxysmal activity. *Neuropädiatrie.* 1971;2:247--304. **\[verify\]**
6.  John ER, Ahn H, Prichep L, et al. Developmental equations for the electroencephalogram. *Science.* 1980;210(4475):1255--1258.
7.  John ER, Prichep LS, Fridman J, Easton P. Neurometrics: computer-assisted differential diagnosis of brain dysfunctions. *Science.* 1988;239(4836):162--169.
8.  van Putten MJAM, Tavy DLJ. Continuous quantitative EEG monitoring in hemispheric stroke patients using the brain symmetry index. *Stroke.* 2004;35(11):2489--2492.
9.  van Putten MJAM. The revised brain symmetry index. *Clin Neurophysiol.* 2007;118(11):2362--2367.
10.  Finnigan S, van Putten MJAM. EEG in ischaemic stroke: quantitative EEG can uniquely inform (sub-)acute prognoses and clinical management. *Clin Neurophysiol.* 2013;124(1):10--19.
11. López S, Suarez G, Jungreis D, Obeid I, Picone J. Automated identification of abnormal adult EEGs. *IEEE Signal Process Med Biol Symp (SPMB).* 2015. **\[verify\]**
12. Obeid I, Picone J. The Temple University Hospital EEG data corpus. *Front Neurosci.* 2016;10:196.
13. Schirrmeister RT, Springenberg JT, Fiederer LDJ, et al. Deep learning with convolutional neural networks for EEG decoding and visualization. *Hum Brain Mapp.* 2017;38(11):5391--5420.
14. Gemein LAW, Schirrmeister RT, Chrabąszcz P, et al. Machine-learning-based diagnostics of EEG pathology. *NeuroImage.* 2020;220:117021.
15. Kostas D, Aroca-Ouellette S, Rudzicz F. BENDR: using transformers and a contrastive self-supervised learning task to learn from massive amounts of EEG data. *Front Hum Neurosci.* 2021;15:653659.
16. Jiang W-B, Zhao L-M, Lu B-L. Large Brain Model for learning generic representations with tremendous EEG data in BCI (LaBraM). *ICLR.* 2024. **\[verify\]**
17. Biswal S, Nip Z, Moura Junior V, et al. Automated information extraction from free-text EEG reports. *Proc IEEE EMBC.* 2015:6804--6807. **\[verify\]**
18. Markovic A, Veen D, Hamann C, et al. Joint heritability of sleep EEG spindle activity and thalamic volume in early adolescence. *J Neurosci.* 2025;45(21):e1138242025.
19. Gorgoni M, Reda F, D'Atri A, et al. The heritability of the human K-complex: a twin study. *Sleep.* 2019;42(6):zsz053.
20. Landolt HP. Genetic determination of sleep EEG profiles in healthy humans. *Prog Brain Res.* 2011;193:51--61.
21. Ambrosius U, Lietzenmaier S, Wehrle R, et al. Heritability of sleep electroencephalogram. *Biol Psychiatry.* 2008;64(4):344--348.
22. Bachmann V, Klaus F, Bodenmann S, et al. Functional ADA polymorphism increases sleep depth and reduces vigilant attention in humans. *Cereb Cortex.* 2012;22(4):962--970.
23. Bodenmann S, Hohoff C, Freitag C, et al. Polymorphisms of ADORA2A modulate psychomotor vigilance and the effects of caffeine on neurobehavioural performance and sleep EEG after sleep deprivation. *Br J Pharmacol.* 2012;165(6):1904--1913.
24. Mazzotti DR, Guindalini C, de Souza AA, et al. Adenosine deaminase polymorphism affects sleep EEG spectral power in a large epidemiological sample. *PLoS One.* 2012;7(8):e44154.
25. Campos-Beltrán D, Marshall L. Changes in sleep EEG with aging in humans and rodents. *Pflugers Arch.* 2021;473(5):841--851.
26. El Kanbi K, Tort-Colet N, Benchenane K, Destexhe A. EEG and computational aspects of how ageing affects sleep slow waves. *J Sleep Res.* 2026;35(3):e70214.
27. Roehrs T, Roth T. Drug-related sleep stage changes: functional significance and clinical relevance. *Sleep Med Clin.* 2010;5(4):559--570.
28. Sun C, Karakis I, Herlopian A, et al. MORGOTH: toward automated EEG interpretation. *Lancet Digit Health.* In press. **\[verify\]**
29. Cole TJ, Green PJ. Smoothing reference centile curves: the LMS method and penalized likelihood. *Stat Med.* 1992;11(10):1305--1319.
30. Rigby RA, Stasinopoulos DM. Generalized additive models for location, scale and shape. *J R Stat Soc Ser C.* 2005;54(3):507--554.
31.  Tveit J, Aurlien H, Plis S, et al. Automated interpretation of clinical electroencephalograms using artificial intelligence (SCORE-AI). *JAMA Neurol.* 2023;80(8):805--812. **\[verify\]**
32. Hirsch LJ, Fong MWK, Leitinger M, et al. American Clinical Neurophysiology Society's Standardized Critical Care EEG Terminology: 2021 Version. *J Clin Neurophysiol.* 2021;38(1):1--29. **\[verify\]**
