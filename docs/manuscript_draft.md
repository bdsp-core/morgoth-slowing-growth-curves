# Lifespan and sleep-stage-resolved normative EEG background: deviation-from-normal detection and automated reporting of slowing

**Authors**

Jin Jing^1,\*^, Chenxi Sun^2,\*^, Wolfgang Ganglberger^1,\*^, Alice D. Lam^3^, Haoqi Sun^1^, Tianyu Zhang^1^, Daniel M. Goldenholz^1^, Fabio A. Nascimento^4^, Doyle Yuan^5^, Sándor Beniczky^6^, Jennifer A. Kim^7^, Aaron F. Struck^4^, Sahar F. Zafar^3,†^, Robert J. Thomas^8,†^, Mouhsin M. Shafi^1,†^, M. Brandon Westover^2,†^

\* These authors contributed equally (co-first authors).   † Co-senior authors.

**Affiliations**

1. Department of Neurology, Beth Israel Deaconess Medical Center, Harvard Medical School, Boston, MA, USA
2. Department of Neurology and Neurological Sciences, Stanford University School of Medicine, Stanford, CA, USA
3. Department of Neurology, Massachusetts General Hospital, Harvard Medical School, Boston, MA, USA
4. Department of Neurology, Washington University School of Medicine in St. Louis, St. Louis, MO, USA
5. Department of Neurology, University of Texas Southwestern Medical Center, Dallas, TX, USA
6. Department of Clinical Neurophysiology, Danish Epilepsy Centre, Dianalund, Denmark; and Department of Clinical Medicine, Aarhus University, Aarhus, Denmark
7. Department of Neurology, Yale School of Medicine, New Haven, CT, USA
8. Division of Pulmonary, Critical Care and Sleep Medicine, Department of Medicine, Beth Israel Deaconess Medical Center, Harvard Medical School, Boston, MA, USA

**Author email addresses** *(for the submission system; not for publication)*

Jin Jing <jjing@bidmc.harvard.edu>; Chenxi Sun <cxsun@stanford.edu>; Wolfgang Ganglberger
<wganglbe@bidmc.harvard.edu>; Alice D. Lam <lam.alice@mgh.harvard.edu>; Haoqi Sun
<hsun3@bidmc.harvard.edu>; Tianyu Zhang <tzhang11@bidmc.harvard.edu>; Daniel M. Goldenholz
<daniel.goldenholz@bidmc.harvard.edu>; Fabio A. Nascimento <fabion@wustl.edu>; Doyle Yuan
<dy15@alumni.utsw.edu>; Sándor Beniczky <sbz@filadelfia.dk>; Jennifer A. Kim
<jennifer.a.kim@yale.edu>; Aaron F. Struck <struck@wustl.edu>; Sahar F. Zafar
<sfzafar@bidmc.harvard.edu>; Robert J. Thomas <rthomas1@bidmc.harvard.edu>; Mouhsin M. Shafi
<mshafi@bidmc.harvard.edu>; M. Brandon Westover <mbwest@stanford.edu>.

**ORCID iDs.** Jin Jing 0000-0002-2415-5854; Chenxi Sun 0000-0002-1762-0877; Wolfgang Ganglberger
0000-0002-6029-2450; Alice D. Lam 0000-0001-7754-4637; Haoqi Sun 0000-0002-5041-8312; Daniel M. Goldenholz
0000-0002-8370-2758; Fabio A. Nascimento 0000-0002-7161-6385; Doyle Yuan 0009-0006-0639-644X; Sándor
Beniczky 0000-0002-6035-6581; Jennifer A. Kim 0000-0003-3072-6198; Aaron F. Struck 0000-0002-9103-1798;
Sahar F. Zafar 0000-0001-5252-5376; Robert J. Thomas 0000-0002-5575-3953; Mouhsin M. Shafi
0000-0002-4531-1967; Tianyu Zhang 0009-0005-2621-9929; M. Brandon Westover 0000-0003-4803-312X.

*Corresponding author:* M. Brandon Westover, Department of Neurology and Neurological Sciences, Stanford University School of Medicine, Stanford, CA, USA --- email: <mbwest@stanford.edu>.

## Highlights

- Lifespan × sleep-stage EEG growth charts score slowing as deviation from normal
- LENS detects slowing above experts and a foundation model
- It quantifies sleep slowing that clinical reports less often mention
- It auto-generates slowing reports validated against the clinical record
- Second-site validation (SAI-100) matches experts and performs comparably to SCORE-AI

## Abstract

**Objective.** Norms for abnormal EEG background slowing rest on small, mostly awake samples. We built LENS:
lifespan- and sleep-stage-resolved EEG growth charts and the deviation-from-normal field they yield.

**Methods.** From 25,536 clinical EEGs (21,757 patients; infancy to \>90 y) we estimated age × sleep-stage
percentile curves (GAMLSS) for spectral power and its ratios, scoring each 15-s segment as a deviation z from
its matched normal. Logistic detectors trained on report labels identify, localize and describe slowing. Both
were validated unchanged on two 100-EEG multi-expert sets from outside the training system: ON-100 (18
experts) and SAI-100 (14 experts, plus SCORE-AI).

**Results.** Curves reproduced development and sleep physiology and were calibrated on held-out normals
(median centile error 1.0 point). Against the ON-100 majority LENS reached AUROC 0.961 (generalized) and
0.908 (focal), placing 83% and 53% of experts under its curves and exceeding a foundation model and the best
published index by 0.09--0.14. On SAI-100 it matched experts for focal slowing but ranked last of three for
generalized. Slowing was the least reliable expert judgement (κ 0.37--0.45), and reports named it far less
often when confined to sleep (54% vs 75%).

**Conclusions.** One deviation field, shared by detection and description, identifies slowing at expert level
and yields stage-aware automated reports. As with a growth chart, LENS measures departure from a matched
norm; establishing its cause remains clinical.

**Significance.** The first lifespan- and sleep-stage-resolved deviation-from-normal instrument for EEG.

*Keywords:* EEG; quantitative EEG; slowing; normative modelling; sleep; automated reporting

## 1. Introduction

Slowing of the EEG background is the most common and one of the most clinically consequential abnormalities a neurophysiologist reports. Such slowing takes two forms: focal slowing points to a localized structural or functional lesion; generalized slowing signals diffuse encephalopathy. Yet whether a given rhythm counts as \"slow\" is relative: the posterior dominant rhythm that is normal at 4 Hz in an infant would be markedly abnormal in an adult, and delta activity that is pathological in the waking adult is physiological in deep sleep. Interpretation therefore depends on age and state, and in practice remains qualitative and expert-dependent, causing inter-reader variability and blocking scalable, reproducible second reads.

The direction of lifespan spectral change is settled in the standard clinical references \[1,2\]: low-frequency power dominates in infancy and declines through childhood as the posterior dominant rhythm matures, and sleep further reshapes the spectrum at every age. What is missing is not the direction but a quantitative, lifespan-continuous, stage-resolved reference against which an individual segment can be scored (**Supplementary S23**).

Day-to-day clinical reading still rests on age norms established decades ago on modest, mostly awake samples, none of which is lifespan-continuous or sleep-stage-resolved (**Supplementary S16**).

A separate literature quantifies pathology directly without lifespan normalization. van Putten & Tavy \[8\] introduced the Brain Symmetry Index (BSI), a 0--1 measure of interhemispheric spectral asymmetry correlating strongly with stroke severity (n = 21); the revised pairwise BSI followed \[9\]. This is the intellectual ancestor of our homologous-channel asymmetry feature. Slowing ratios such as DAR (delta/alpha ratio) and (delta+theta)/(alpha+beta) track acute-stroke severity (Finnigan & van Putten \[10\]), and relative delta/theta and alpha-delta ratios discriminate ICU delirium and coma. A parallel line automates the *background* read itself --- characterising the posterior dominant rhythm and quantifying the adult background pattern, then evaluating that read clinically \[11--13\], with fully automatic peak-frequency estimation now demonstrated at hospital-cohort scale \[14\]. However, these instruments are each tied to one disease and setting, use fixed thresholds, and ignore age, sex, and sleep stages; the background-quantification line is closest in spirit to ours but remains awake, adult and single-feature.

Automated interpretation has meanwhile been benchmarked mainly as binary normal/abnormal classification (TUAB \[15,16\]) or as a single brain-age scalar, neither of which localises, grades or describes a finding (**Supplementary S15**).

There are substantial individual differences in sleep depth, slow waves, spindles and phasic events (cyclic alternating pattern, CAP) during normal sleep, which change the visualized frequencies and the interpretation of normal versus pathological slowing \[22--25\]. Sleep EEG slowing is influenced by genetic polymorphisms \[26--28\]. There is a large age-dependency of slow-wave activity \[29,30\]. Several medications, such as the oxybates and atypical antipsychotics, increase slow-wave activity during sleep \[31\]. Thus, in clinical practice, for any given conventional sleep stage, slowing varies widely in health and disease, making the determination of what is normal difficult.

No prior work combines (a) lifespan-continuous and (b) sleep-stage-specific normative modeling of clinical slowing features with (c) per-recording deviation-from-normal scoring, (d) on \>20,000 patients from clinical practice, and (e) closes the loop to clinician-style narrative validated against real reports.

Here we introduce LENS (Lifespan EEG Normative Scoring): lifespan, sleep-stage-resolved EEG growth charts --- the functional-EEG analog of pediatric growth charts --- and the interpretable deviation-from-normal field they yield when a recording is scored against them, which serves both detection and description. Specifically, LENS (1) builds reproducible age × sleep-stage normative growth curves for clinical slowing features across the lifespan, in whole-head, regional, and scalp-topographic form; (2) derives from them a per-segment deviation field (stage- and age-matched z per region × feature), the shared substrate for downstream analysis; (3) detects slowing with an interpretable model based on that deviation field, externally validated on two multi-expert datasets, outperforming the current state-of-the-art foundation-model; (4) generates a structured, validated description (type, laterality, region, anterior--posterior gradient, persistence, sleep stage, electrode) that tracks the report by dose-response contrast; and (5) releases an open Python package with a single-command-reproducible pipeline and a published per-recording label set.

## 2. Methods

The pipeline is organised around a single measurement layer: one age- and sleep-stage-matched deviation-from-normal field, computed per 15-second segment, on which both the detector and the description operate (**Figure S1**).

### 2.1 Cohort and data

The analysis cohort comprises **25,536 recordings from 21,757 patients** at a single academic health system, spanning infancy to over 90 years and combining routine studies with an overnight/long-term expansion that supplies the deep-sleep data. Inclusion criteria and site composition are in **Supplementary S18**; cohort characteristics are in **Table 1**.

Age and sex are taken from the clinical records (49.2% female). Age is the confound that motivates the entire normative design and is handled by conditioning rather than by matching (**Supplementary S20**).

### 2.2 Reproducible feature extraction

To make the pipeline reproducible and extensible to new recordings, extraction is implemented in Python. The pipeline re-montaged the referential 10-20 EEG to 18 bipolar (double-banana) channels, applied a 0.5 Hz high-pass and 50/60 Hz notch, segmented into 15-second windows (3000 samples at 200 Hz, step 2800), and computes a multitaper power spectral density (time-bandwidth NW = 4, 7 tapers). Per segment we derive band powers (delta/theta/alpha/beta/gamma/total), relative powers, and inter-band ratios (DAR = delta/alpha, TAR = theta/alpha), for each of the 18 bipolar channels, plus 8 homologous left--right pairs for focal localization. Channels are aggregated into eleven regions (whole-head; anterior and posterior; left/right temporal; left/right parasagittal; and left/right anterior and left/right posterior, so that a frontal or posterior focus can be lateralised directly rather than inferred from the temporal/parasagittal split) via. Linear powers are log-transformed before z-scoring.

**Calibration and artifact rejection.** The delta band is defined as **1--4 Hz** rather than 0.5--4 Hz, and a per-segment filter marks a segment unusable on three explicit amplitude, flatness and high-frequency criteria; both choices are detailed in **Supplementary S2**.



### 2.3 Sleep staging

Routine EEG feature sets are unstaged. We staged each recording from the raw EEG with the morgoth2 deep-learning automated sleep stager (5-class window-level model), assigning each 15-second feature segment its majority stage (W/N1/N2/N3/REM) \[32\]. The overnight recordings fill the deep-sleep coverage routine clips cannot. Staging runs in a dedicated virtual environment (the stager\'s `pyhealth` dependency pins pandas \<2, incompatible with the analysis stack).

### 2.4 Normative growth curves (GAMLSS)

Each feature × region × sleep stage is fitted separately, giving 11 × 5 × 6 = 330 cells. **The unit of observation is the individual 15-second segment**, with log-transformed age as the single covariate; segments are weighted so that **each recording carries equal total weight** regardless of length, which matters because a 12-hour overnight study would otherwise dominate the deep-sleep cells. Percentile curves are estimated with GAMLSS, the method behind clinical growth charts (Cole & Green \[33\]; Rigby & Stasinopoulos \[34\]), using a Box--Cox-t distribution for positive features and a support-aware model on the real line for log features that take negative values. Every curve is checked against a model-free rolling median and plotted with it in **Figure 1a**, so agreement can be seen rather than asserted; agreement is within 0.04 IQR across the data-dense adult range, with a residual discrepancy confined to the infant peak of the ratio features. Distributional families, the tail parameter used in scoring, the spline degrees-of-freedom sweep and the infant-band bootstrap are given in **Supplementary S1**.

Two points guard against over-reading Figure 1. The displayed curves are fitted on the raw feature, in the units a reader can interpret; the **scoring** norms are fitted on the log-transformed feature, a different parameterisation whose skewness the log transform already absorbs. The scoring norms are therefore validated on their own terms rather than by eye: on held-out clean-normal recordings the median wake deviation sits near zero at every age, including infancy (under 1 year: log DAR +0.20, log TAR +0.32, relative delta −0.18 SD; adults: +0.11, +0.19, +0.07), and their centiles are calibrated against held-out data in **Figure S2**.

**Sex is pooled.** Conditioning norms on sex changes abnormality discrimination by ΔAUROC ≤ 0.002 in every feature × region × contrast we tested; we therefore pool sexes, doubling the effective sample per age.

### 2.5 The per-segment deviation field

Every 15-second segment is scored as a deviation z for each feature × region against its own (sleep-stage, age)-matched normal curve (joinable 1:1 to the segment tables), using a precomputed normal grid (`grid_norm.json` regional, `grid_anorm.json` asymmetry). Because each segment is compared to *its own stage\'s* normal, delta that is abnormal in wake but normal in N2/N3 yields near-zero deviation in normals. This per-segment, per-region field is the single measurement layer both the detector and the description run on; it is unsupervised conditional on a report-defined normal reference --- the scoring itself uses no labels, but the reference population is selected by the clinical report. Its shape is **(segments) × 11 regions × 6 features = 66 deviation z-values per 15-second segment** --- the regions of §2.2, and features log delta, log theta, relative delta, log DAR, log TAR and relative alpha --- stored one partition per recording and joining 1:1 to the segment tables on (`eeg_id`, `segment`). The materialised field spans **14.2 million segments**, i.e. \~939 million individual deviation values.

### 2.6 Report--recording pairing and label provenance

Reports and recordings are joined through the ordering record, not broadcast across a patient. Each clinical report carries an order identifier, and each EEG file carries a patient and a start datetime. Two steps make that join one-to-one. First, **all files sharing a patient and a calendar date are collapsed into a single study**, keeping the file closest in time to the report: a long-term recording is written as several files on one day, and treating those as separate studies would multiply one report across them. Second, an order that still spans more than one study date is assigned to the **single date nearest the report**. A study is marked cleanly paired (`clean_pair`) when its order covers only one study date, or when it is the study that order most plausibly describes; all report-text-derived quantities are computed on `clean_pair` recordings only (1,664 EEGs dropped by the filter). Corrected label rules make focal slowing always pathologic, generalized slowing pathologic only if the report names it among the abnormalities, and abnormal-without-slowing its own stratum.

### 2.7 Detection

Detection and description share the deviation field. We report three detectors.

**2.7a LENS --- the deviation detector (primary).**

*Model class.* LENS is deliberately simple --- an **L2-regularised logistic regression** on standardised deviation features --- so that performance is attributable to the deviation field rather than to model capacity (**Supplementary S5**).

*Two label strategies (LENS-v1 and LENS-v2).* A report label describes a recording, not a segment, and slowing is often intermittent, so most segments of a "focal slowing" recording show nothing. **LENS-v1 (broadcast)** simply gives every segment its recording's label. **LENS-v2 (multiple-instance)** starts from that broadcast initialisation and then iteratively relabels, keeping as positive only the top-k highest-scoring segments within each positive recording (MIL-EM, three iterations), so positive supervision concentrates on the segments that actually carry the finding. **LENS-v2 is LENS**: every headline number in this paper is the v2 model, and v1 is reported alongside it in Figure 2 as the ablation showing what the multiple-instance step buys.

*From segment to recording.* A recording's score is the **mean of its top-20 segment scores**: a report names slowing if it occurs anywhere, so a recording is positive when its *most abnormal* stretch is abnormal, and averaging over all segments would dilute a genuine intermittent finding. Detection improves with k and plateaus by k ≈ 20 (**Supplementary S4**).

*Fitting.* Recordings are divided by a **patient-level split stratified on class and age band**, so no patient appears in both train and test; hyperparameters and the class definitions are in **Supplementary S3**.

**2.7b The Morgoth gate (reference).** A three-tier hierarchical foundation-model gate (abnormal → slowing → focal/generalized EEG-level heads), calibrated against expert reports, serves as the learned-representation reference detector. It is not part of the interpretable pipeline; it is the bar LENS is measured against.

**2.7c The van Putten benchmark.** We recomputed the published van Putten index family (Brain Symmetry Index and its revised pairwise form, Q_SLOWING, Q_APG, Q_ASYM, DAR, DTABR and SEF95), each evaluated as published and again age-conditioned against our normative curves (**Supplementary S6**).

### 2.8 Description: reading the deviation field into words

Once slowing is detected, LENS generates a structured verbal description of its type, location and persistence. Each descriptor is a defined function of the deviation field, and a **claims table** governs clause by clause what may be asserted from it --- magnitude as SD and centile, prevalence as a percentage of analysed segments, no severity adjective --- so the generated text cannot outrun the evidence. Full descriptor definitions and the claims table are in **Supplementary S25**.

### 2.9 Expert panels and the human ceiling

Agreement with a single clinical report is bounded by report reliability. We therefore evaluate against two independent, multiply-read *external* datasets --- **ON-100** (100 EEGs from five US centers, each read by 18 electroencephalographers, a subset re-read) and **SAI-100** (100 EEGs from the SCORE-AI validation study, each read by 14 experts) --- each recording judged for focal and generalized epileptiform and non-epileptiform abnormality. Ground truth is the panel majority. Our primary metric is the percentage of experts under the curve: we place each expert on the model\'s ROC curve (and its precision--recall, PR, curve) as one sensitivity--specificity point --- graded against the leave-one-out consensus of the other readers --- and count how many fall *below* the curve, i.e. how many the model matches or outperforms at that expert\'s own operating point. A model performing at the panel\'s own level would put roughly half of the experts under its curve. Inter-rater reliability (Fleiss κ, chance-corrected agreement) and each reader\'s self-consistency quantify the human ceiling. Band agreement is evaluated against experts\' per-band calls (no text extractor in the loop).

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

The normative curves recapitulate known maturation patterns: at the occipital derivations (O1/O2), the region from which the posterior dominant rhythm is read clinically, relative delta and the theta/alpha and delta/alpha ratios fall steeply through childhood to an adult plateau by \~30 years, and normal-referenced z-scores center on 0 for controls across the lifespan (**Figure 1a**; solid GAMLSS median tracks the model-free rolling median). The scalp-topography rendering makes the spatial story explicit (**Figure 1b**): relative delta is frontal-predominant, highest in infancy across every sleep stage, and declines monotonically toward adulthood, deepest in N3; these are the regional substrate the localization descriptors rely on; the theta/alpha ratio shows the same developmental pattern (**Figure S4**), so the topographic result is not specific to relative delta. Stage-resolved curves quantify the expected physiology: median relative delta rises with sleep depth W ≈ N1 \< N2 \< N3, REM intermediate (**Figure S5**). The direct clinical consequence is that delta which is abnormal in wake is entirely normal in N2/N3.

**The curves are calibrated on held-out data.** Tested where they were not fitted (**Figure S2**) --- 7,216 held-out clean-normal recordings and, as an institutionally external reference, the 71 ON-100 recordings the expert majority called neither focally nor generally slow --- observed and nominal centiles agree closely: median absolute discrepancy **1.1 percentage points** internally (maximum 9.2) and 2.3 points externally. Deep sleep is covered internally (**4,836 held-out N3 observations from 420 patients**) but not externally, since both external cohorts are routine daytime recordings. The one clear exception, N1 log TAR, and the per-stage table are in **Supplementary S19**.

### 3.3 The per-segment deviation field is calibrated and discriminative

Scoring each segment against its own (stage, age) normal yields a field that is both calibrated --- clean-normals sit near z = 0 in every stage (whole-head median +0.24 W to −0.04 N3 for delta excess) --- and discriminative --- abnormal recordings are shifted up in every stage, most in W/N1 (delta excess +0.83 W, +1.57 N1; TAR +1.03 W, +1.25 N1) (**Figure S6**).

### 3.4a Detection --- external validation on the ON-100 panel and the foundation-model gate

A single model trained on report data (patient-stratified, \~16k recordings) when externally validated on the ON-100 panel separated slowing from normal against the panel majority at AUROC 0.961 \[95% CI 0.914--0.994\] (generalized) and 0.908 \[0.815--0.978\] (focal), with average precision (AUPRC) 0.87 (generalized) and 0.71 (focal) against panel base rates of only 18% and 12% positive (recording-level bootstrap; **Figure 2**). This placed 83% of the 18 experts under our generalized ROC curve (78% under PR) and 53% under focal (53% under PR) (panel base rates 18/100 generalized-, 12/100 focal-positive), a majority of the panel on both axes. Against the Morgoth gate the model wins clearly on generalized (0.961 vs 0.853, 83% vs 11% experts under) and is level on focal (0.908 vs 0.908), where it ranks above more of the panel (53% vs 41% experts under) but does not separate the classes better.

**The two axes need different read-outs, and the reason is mechanistic.** Amount of slowing does not separate focal from generalized (both raise it), so the focal head localizes (using peak-region z, focality (peak − median region), asymmetry z, spatial stability, aggregated over the recording); the generalized head pools a diffuse whole-head amount score across segments. Stage-matching unlocks the sleep stages (z-scoring each segment against its own stage\'s norm keeps only abnormal-for-its-stage slowing). To isolate how much of the gain comes from these design choices --- localization and stage-matching --- rather than from the training data, we ran an ablation: a model cross-validated *within the panel itself* (trained and tested on ON-100; this is an ablation, not LENS). It raises focal detection from 24% to 53% of experts under the ROC curve and generalized to 78%, and **Figure S7** shows an intermediate W+N1 localized focal detector at 47% under / AUROC 0.89. Because that ablation trains and tests on the same panel, its numbers are an optimistic upper bound, reported only to attribute the benefit to localization and stage-matching; every headline number above comes from the report-trained detector, which never sees the ON-100 recordings.

### 3.4b Detection --- external validation on SAI-100 (SCORE-AI and 14 experts)

The **second external benchmark, SAI-100**, tests transfer across countries and to an independent scoring system: 100 routine scalp EEGs from the SCORE-AI validation study \[35\], drawn from three hospitals in two countries, with SCORE-AI, the Morgoth gate and 14 expert calls available per recording and no overlap with training or ON-100. The unchanged pipeline ran end-to-end on 98/100 (**Supplementary S17**).

Focal slowing is detected well by all three learned methods (**Figure 3**). LENS reached AUROC **0.938** \[0.870, 0.985\], placing 79% of the individual experts under its ROC curve, against SCORE-AI --- a purpose-built EEG classifier --- at 0.878 \[0.783, 0.955\] (29% under) and the Morgoth foundation-model gate at 0.974 \[0.923, 1.000\] (93% under). For generalized slowing LENS reached 0.908 \[0.803, 0.980\] with 50% of experts under, against SCORE-AI 0.930 \[0.874, 0.971\] (57%) and Morgoth 0.951 \[0.892, 0.991\] (71%). **On this cohort none of these differences is statistically supported.** A paired bootstrap --- the same 4,000 recording-level resamples scoring both models, so the interval is on the difference itself --- puts every comparison's 95% interval across zero: focal LENS − SCORE-AI +0.061 \[−0.036, +0.160\] (p = 0.23), focal LENS − Morgoth −0.037 \[−0.107, +0.024\], generalized LENS − SCORE-AI −0.020 \[−0.122, +0.062\], generalized LENS − Morgoth −0.042 \[−0.151, +0.041\]. With 98 recordings and 25 focal / 24 generalized positives the study is not powered to separate three detectors of this quality, and we therefore claim only that LENS performs comparably to a dedicated EEG classifier and to a foundation-model gate on an unseen cohort, in two countries, with no site-specific refitting. We state the intervals plainly because they bound the claim: on this second external dataset LENS reaches expert-level detection on both axes, but the cohort cannot rank it against SCORE-AI or the gate in either direction. Read together with ON-100, where LENS led on generalized and was level with the gate on focal, the honest summary is that detection transfers to both external datasets while the *ordering* among the three methods is resolved only on ON-100, which is five times larger. Taken together, the two external validations --- **ON-100** (five US centers, 18 experts) and **SAI-100** (three hospitals across two countries, 14 experts, plus SCORE-AI) --- show LENS matching human experts on both axes across institutions, countries, and scoring systems, with no site-specific refitting.

**The detector reads the deviation field, not the patient's age.** Abnormal recordings are on average
17 years older than clean-normals, and chronological age is a feature in both heads, so a classifier could
in principle recover that association and use age as a shortcut. It does not. Dropping age from the heads
entirely costs **0.001** on focal and **0.007** on generalized (report-test), and **0.008** / **0.012** on
ON-100; conversely age *alone* reaches only 0.591 / 0.610 (report-test) and 0.661 / 0.712 (ON-100), so the
deviation field contributes **+0.15 to +0.25** AUROC over what age supplies. Performance also holds *within*
decade bands, where age barely varies and a shortcut has almost nothing to exploit (focal 0.60--0.82 across
nine bands; generalized 0.65--0.76), and survives inverse-propensity reweighting that equalises the age
distributions of positives and negatives (focal 0.737 -> 0.708 report-test, 0.920 -> 0.898 ON-100;
generalized 0.717 -> 0.684 and 0.937 -> 0.944).

### 3.5 Benchmark against the published qEEG literature (van Putten)

On the clean ON-100 expert panel we benchmarked LENS head-to-head against the strongest van Putten index and the Morgoth gate, recomputing every index on the same panel signals against the expert-vote majority (**Figure S3**). LENS is the best detector for generalized slowing and level with the foundation-model gate for focal. For generalized slowing it reaches AUROC 0.961 against the best whole-head slowing ratio (DAR, 0.817) and the Morgoth gate (0.853); for focal slowing 0.908 against the best interhemispheric-asymmetry index (an r-sBSI analog, 0.825), level with Morgoth (0.908). LENS therefore exceeds the published qEEG lineage by +0.14 (generalized) / +0.08 (focal), with non-overlapping confidence intervals, and outperforms the foundation-model gate on generalized slowing (0.961 vs 0.853) while matching it on focal (0.908 vs 0.908). On clean expert labels LENS is therefore the strongest detector of generalized slowing and no worse than the gate on focal. (The comparison is on the panel, not the full report cohort, because single-report labels cap every detector by their own noise, where LENS and the raw indices converge near \~0.73; removing that ceiling with clean expert labels is the fair test, and is where LENS separates.)

A separate full-cohort analysis isolates the *mechanism* of the normative step (Table S1). Age-conditioning the *slowing* ratios on our normative curves improves them --- Q_SLOWING +0.049, DAR +0.037, DTABR +0.046, SEF95 +0.042 (generalized), a clean positive control for the normative framework; whereas age-conditioning the *asymmetry* indices does not (r-sBSI −0.017, Q_ASYM −0.006): interhemispheric symmetry does not vary with age, so an age reference adds variance and no signal. The dissociation is what physiology predicts, confirming that lifespan normalization is a substantial, targeted gain.

### 3.6 The human ceiling for slowing

**Slowing is the least reliable judgement experts make.** In the 18-expert panel, between-rater Fleiss κ was 0.373 (focal) and 0.450 (generalized), against 0.585 and 0.739 for focal/generalized epileptiform discharges; a reader re-reading the same EEG reproduced their own slowing call at only κ = 0.563 / 0.642. Every \"agreement with the report\" figure in this literature is bounded by these numbers, which is why we validate detection against the panel majority and multiple raters. An independent external validation of SCORE-AI reports the same ceiling effect \[37\]. Our continuous score tracks the fraction of the 18 experts who marked slowing at Spearman ρ = 0.652, a measure of conspicuity to trained readers.

### 3.7 Description --- type, location, persistence, and sleep stage, validated by contrast

Six worked recordings set LENS's generated finding and description beside the clinician's own report text for the same study --- three exclusively focal (**Figure 4**) and three exclusively generalized (**Figure 5**). Across the cohort, the deviation field reads OUT into a structured description whose every component tracks the report by dose-response contrast (see contrasts in **Figure 6**; and the full panel set D1--D6 in **Figure S8**). *(All contrasts among report-slowing recordings unless noted; N = 23,869 report recordings.)*

- **D1: type & amount.** Our theta-excess measure is higher when the report names theta (median 1.39 vs 1.08, Cohen d = 0.29, p = 3×10⁻⁴⁵) and our delta-excess measure is higher when the report names delta (1.63 vs 1.32, d = 0.26, p ≈ 0). The measure tracks the band word.
- **D2: laterality & region.** Our signed left-minus-right asymmetry follows the reported side --- left +0.43, bilateral +0.07, right −0.54 (clean monotonic separation). Because temporal delta magnitude runs high everywhere (a temporal-delta attractor), the specific regional descriptor is *relative prominence* (focality): a lobe\'s prominence rises when the report names it, for temporal, frontal, and posterior alike (all p \< 10⁻³).
- **D3: anterior--posterior predominance.** The anterior − posterior gradient is less posterior-predominant in report-anterior than report-posterior cases (−0.07 vs −0.22, p ≈ 9×10⁻⁶), a meaningful but modest gradient, as most generalized slowing is topographically unspecified.
- **D4: persistence.** Prevalence (fraction of abnormal segments) separates report-slowing from clean-normal (median 0.19 vs 0.05), with a fat continuous-prevalence tail; run length and episode counts give an ACNS-style occasional→continuous read-out. (There is no structured report qualifier, so this is shown as internal reasonableness.)
- **D5: by sleep stage.** Slowing prevalence sits above clean-normal at every stage, wake AND sleep (e.g. N2 0.32 vs 0.12); the description is not wake-only.
The delta-versus-theta band call is deliberately calibrated against the reports rather than asserted (**Supplementary S8**).

- **D6: words.** Descriptors are assembled into a compact finding line and a full report-style paragraph, governed clause-by-clause by a claims table so that nothing is asserted beyond what the field supports (**Supplementary S9**).

An example of the generated paragraph, and the clause-by-clause rules governing it, are in **Supplementary S7**.

### 3.8 Sleep-confined LENS deviations are less often mentioned in clinical reports

The dose-response suggests that reports less often mention slowing confined to sleep; a within-subject test supports that reading, with the caveats below. Among recordings whose report names slowing, when the slowing is visible only in sleep the report names it 53.6% of the time, versus 74.8% when it is visible awake (base rate 40.0%; **Figure 7**). At the segment level, recordings the reader called abnormal whose report names slowing but never mentions sleep nonetheless deviate above age- and stage-matched clean-normals in N2/N3 (median sleep-stage z +0.82 log delta, +0.89 DAR, vs −0.05 / −0.08 in held-out controls). Because a slow-wave-keyed stager could reproduce this by misstaging slow wake as N2, we adjudicated with a delta-independent marker, detected sleep spindles, and the elevation is undiminished on **spindle-verified N2** --- segments independently confirmed as true sleep by an 11--16 Hz sigma burst, a marker that does not depend on delta. On 89 cases and 229 age-matched controls whose alignment to the source recording is verified, log delta separates them at AUROC **0.858 \[0.807, 0.905\]** (p = 2×10⁻²²) and DAR at **0.789 \[0.728, 0.850\]** (p = 3×10⁻¹⁵). On the identical recordings the all-N2 AUROC is essentially the same (0.879 and 0.819), so restricting to spindle-verified segments costs nothing --- the effect was never a staging artefact.

**The same holds in deep sleep**, where the staging objection bites hardest: accepting only N3 segments inside a non-wake block containing a spindle-positive N2 segment --- genuine sleep established independently of delta --- cases still separate from controls (log delta AUROC **0.767** \[0.645, 0.870\], DAR **0.784** \[0.671, 0.884\]; **Supplementary S10**).

Thus the model sees what the report omits, in the regime where visual reading is most challenging.

Two readings are possible and these data do not fully separate them: genuine abnormality that visual reading misses, or physiology (slow-wave rebound, medication) the reader correctly declined to call abnormal. Per §2.11 our claim is the weaker, statistical one. The asymmetry is itself informative --- a *focal* deviation confined to sleep has no benign explanation of this kind, whereas a generalized N3 one does (**Supplementary S24**).

### 3.9 Why we do not describe clinical "severity grade"

Among recordings whose report names slowing, our score does not *usefully* recover readers' mild/moderate/marked adjectives (**Figure S9**): Spearman ρ = +0.107 for the fragile max statistic and +0.101 for a robust upper quantile (n = 2,393). An exhaustive sweep over **72 combinations** of feature × normalization × stratum × statistic does not rescue it: the largest \|ρ\| anywhere is **0.182**. We are explicit that the finding is magnitude, not significance --- every combination is positive and 61 of the 72 clear a Bonferroni threshold, because at n ≈ 2,400 even a trivial effect does. The structure is what matters: **mild and moderate are indistinguishable** (median \|z\| 1.13 vs 1.15) and only the small *marked* tail is elevated (2.58). An adjective that cannot separate its own two most common levels is not a quantitative grading. The panel data explain the reason: an adjective attached to a judgement of κ ≈ 0.56--0.64 self-consistency cannot support a strong correlation with any measurement. We report detection, dose-response, localization, persistence, and stage, and avoid severity grading and hard band determination, both of which sit near their (low) human ceilings.

## 4. Discussion

This work unifies four previously separate literatures into a single instrument. Unlike lifespan qEEG that reports *normal values*, we score *deviation from normal* per recording. Unlike classic norms (Petersén & Eeg-Olofsson \[5\]; John et al. \[6\]), which are small-N, wake-only, age-banded, and, in the commercial lineage, opaque, our norms are lifespan-continuous, sleep-stage-resolved, built on \~22,000 patients, and fully reproducible in open Python. Unlike disease-specific abnormality indices, which use fixed thresholds tied to one setting and ignore age and sleep stage, our features are normed against the matched normal population. And unlike binary classifiers or ungrounded report generators, we produce localized, graded, stage-aware descriptions validated against the actual report corpus. This extends the deviation idea of John et al. \[6\] to a modern scale and to slowing and asymmetry specifically, and it is the functional-EEG, sleep-stage-resolved analog of the MRI \"brain charts\" of Bethlehem et al. \[4\] --- in effect, EEG growth charts for clinical slowing.

**Beyond the Brain Symmetry Index.** Our homologous-channel asymmetry feature is a descendant of the van Putten BSI \[8,9\], normed against an age- and stage-matched reference and, for the detection decision, replaced by a learned representation; beyond detection we add lateralisation and regional localisation that a symmetry scalar cannot provide (**Supplementary S14**).

**Age-conditioning helps the slowing ratios but does not close the gap.** Conditioning the published slow/fast ratios on our normative curves improves them, while the asymmetry indices are unaffected --- a dissociation that is exactly what physiology predicts, since interhemispheric symmetry does not vary across the lifespan (**Supplementary S13**).

**The normative lineage.** LENS sits at the confluence of normative deviation scoring (John et al. \[6,7\]; Bethlehem et al.'s MRI brain charts \[4\]) and automated interpretation. What it adds to both is a described, validated, stage-resolved output rather than a label or a scalar (**Supplementary S21**).

**Reports are a directionally biased reference.** They are our reference standard but an imperfect one with a known direction: sleep-confined slowing is named less often than waking slowing (§3.8). We therefore treat report concordance as validation only where reports are reliable, and pose the complementary hypothesis that a per-stage normative model measures more reproducibly exactly where visual reading is weakest. The claim is that reader and instrument disagree systematically and in a quantifiable direction, not that the instrument is right (§2.11); the definitive test is the blinded expert re-read proposed below (**Supplementary S22**).

## 5. Limitations

This study has some limitations. Prevalence and persistence are read from the per-segment deviation field over the whole recording where available; for the sub-study that requires locating a clip inside its source (spindle verification) the analysis is restricted to routine-length studies, and short- vs long-recording cases have indistinguishable sleep-stage deviation, so the restriction does not bound the conclusion. Band determination is near-chance and is thus a "hard call" and we therefore do not claim it; the slow bands co-occur (\~64% of reports say \"mixed\"), and the valid test is the continuous dose-response contrast. Severity grade is a null result. **We report a band, not a frequency.** Clinical reports usually state one --- 5,785 recordings in our corpus state an explicit frequency inside a slowing clause --- whereas LENS reports δ/θ/mixed. We tested whether the frequency can be recovered spectrally and it cannot, at least not this way: a dominant frequency restricted to 1--8 Hz correlates with the stated value at only ρ = 0.13 with a median error of ~2 Hz, and restricting the measurement to the segments that are actually abnormal does not improve it (ρ = 0.04). A raw spectral peak is unusable here because EEG power falls off as roughly 1/f, so the maximum inside any low band sits at its lowest bin; neither an aperiodic-detrended peak nor a band median recovers what a reader writes down. Whether that reflects a limitation of spectral estimation or the unreliability of the stated frequency itself --- band agreement between experts is already at κ ≈ 0.10 --- we cannot say from these data. We also measure no **beta** excess: the descriptors cover the slow bands and the slow/fast ratios, so drug-induced beta activity --- a common and clinically meaningful background finding --- is outside the current scope and would require its own normative feature.

**Deep sleep is validated internally but not across institutions.** The normative curves are held out and well calibrated in every stage including N3 (4,836 held-out N3 observations from 420 patients, median centile discrepancy 3.7 points), but neither external cohort can test N3: ON-100 and SAI-100 are routine daytime recordings in which N3 is only 5.4% of segments. Because our deep-sleep norms come from the overnight expansion, which is single-institution, the cross-institution generalisability of the N3 curves specifically remains untested.

**Vigilance state is uncontrolled in the overnight recordings**, which are not subject to the active alerting a technologist applies during a routine study; the consequences for the wake norms are in **Supplementary S12**.

**The normal range in sleep is genuinely wide, and our reference is a population one.** Sleep depth and slow-wave activity vary substantially between healthy individuals, so a deviation from the population norm is not automatically abnormal for that person; **Supplementary S11** develops this, and §2.11 states what a deviation does and does not assert.

## 6. Conclusion

We present LENS (Lifespan EEG Normative Scoring), which is to our knowledge the first EEG growth charts for clinical slowing, large-scale, lifespan- and sleep-stage-resolved normative curves that score an individual EEG\'s slowing as a deviation from its matched normal, and that both detect and describe. Built on 25,536 clinical EEGs from \~22,000 patients, it reproduces known development and aging (in curve and across the scalp), quantifies the stage-dependence of physiological slowing (W ≈ N1 \< N2 \< N3), and, from a single interpretable deviation field, detects slowing at or above an 18-expert panel and a state-of-the-art foundation-model (exceeding the gate on generalized slowing, on par on focal) on an independent multi-rater set, exceeds the published qEEG lineage by +0.08 to +0.14 AUROC, and reads OUT a structured description (type, laterality, region, anterior--posterior gradient, persistence, sleep stage) validated against clinical reports by dose-response. It sees what reports omit --- slowing in sleep --- in exactly the regime where visual reading is hardest. We release an open, reproducible Python package and a published per-recording label set, so that others can validate and extend LENS on new populations. More broadly, by making the reading of EEG slowing quantitative, lifespan- and sleep-stage-aware, and fully reproducible, LENS advances clinical EEG interpretation from expert-dependent qualitative judgement toward a scalable, standardized second read --- and provides a template for turning other qualitative EEG features into validated deviation-from-normal measures.

## Figures and Tables

*Triaged for CN (economy of display items).* **Main = 1 table + 6 figures**; the rest are Supplementary.*

### Main

- **Table 1 --- Cohort characteristics**. Percentages in the label rows are of the 23,872 cleanly paired recordings, not of the 25,536 total; the two denominators are reconciled in §3.1.
- **Figure 1 --- The normative deviation model.** (a) Lifespan percentile growth curves per stage; (b) scalp topography of regional development by age × stage.
- **Figure 2 --- Detection vs 18 experts and the foundation-model gate (ON-100).** Generalized AUROC 0.961 \[0.914--0.994\] (83% experts under); focal 0.908 \[0.815--0.978\] (53% experts under) (`s0e_occasion_focal.png`).
- **Figure 3 --- External validation (SAI-100).** LENS vs **SCORE-AI** vs the Morgoth gate vs the 14 individual experts, for focal and generalized slowing, against the true expert-vote majority (ground truth recomputed from the individual expert votes --- see §3.4b).
- **Figure 4 --- Example focal slowing: EEG segments with the automated report vs the clinical report.** Two exclusively-focal recordings (marked and moderate); the mildest example is **Figure S10**. Two panels per figure rather than three so the figure prints at full size: three stacked panels plus their report text left each trace block 0.08 in per derivation, which is why the derivation labels collided. Each shows a 10-s longitudinal-bipolar EEG paired with two matched comparisons: LENS's brief finding against the clinical report's *impression*, and LENS's detailed description against the report's *description*, using the actual (de-identified) report text. The displayed window is the segment where the localized (claimed-region) deviation peaks, within the dominant sleep stage; it is an illustrative peak, not a typical epoch. Examples are restricted to clearly-lateralized recordings (|left−right asymmetry| ≥ 1.5 SD) so the displayed segment reliably matches the localization.
- **Figure 5 --- Example generalized slowing: EEG segments with the automated report vs the clinical report.** As Figure 4, for two exclusively-generalized recordings (the mildest is **Figure S10**); the displayed window is the segment of highest whole-head deviation. Splitting the examples across two page-width figures keeps the report text legible in print, which a combined 3×2 grid did not.
- **Figure 6 --- Description validated by contrast (condensed).** Laterality tracks the reported side; the slowing signal persists across sleep stages (`s4_d5.png`).
- **Figure 7 --- Sleep-confined deviations are less often named in reports.** Fraction of reports that name slowing, split by where the slowing is visible: 74.8% when visible awake vs 53.6% when visible only in sleep (base rate 40.0%). The within-subject deviation analysis behind this --- cases deviate above stage-matched normals in N2/N3, undiminished on spindle-verified N2 --- is in §3.8.

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

Code is released as the open-source package `bdsp-core/morgoth-slowing-growth-curves`, with a numbered, reproducible pipeline (three tiers: `results`, `features` and `scratch`). We publish per-recording labels (report-derived flags, corrected SAP labels, description descriptors) with provenance. Raw EEG and free-text report content are not redistributed; they are available via BDSP credentialed access. The de-identified derived data and code are published on BDSP as **LENS v1.0.0** (<https://bdsp.io/content/q8qpxsk3sgq57vkm5abp/1.0.0/>; version DOI [10.60508/7060-qq30](https://doi.org/10.60508/7060-qq30), concept DOI [10.60508/wt7m-f443](https://doi.org/10.60508/wt7m-f443)) under the BDSP Credentialed Health Data License and Data Use Agreement; the code repository (<https://github.com/bdsp-core/morgoth-slowing-growth-curves>) is licensed CC BY-NC 4.0.

## References

*Vancouver style, numbered in citation order; in-text citations use these numbers. All entries have been checked against the primary source (Crossref/PubMed) except reference 28, which is in press and cannot yet be verified.*

1. Schomer DL, Lopes da Silva FH, editors. *Niedermeyer's Electroencephalography: Basic Principles, Clinical Applications, and Related Fields.* 7th ed. New York: Oxford University Press; 2018.
2. Ebersole JS, Husain AM, Nordli DR, editors. *Current Practice of Clinical Electroencephalography.* 4th ed. Philadelphia: Wolters Kluwer; 2014.
3. Engemann DA, Mellot A, Höchenberger R, et al. A reusable benchmark of brain-age prediction from M/EEG resting-state signals. *NeuroImage.* 2022;262:119512.
4. Bethlehem RAI, Seidlitz J, White SR, et al. Brain charts for the human lifespan. *Nature.* 2022;604(7906):525--533.
5. Petersén I, Eeg-Olofsson O. The development of the electroencephalogram in normal children from the age of 1 through 15 years: non-paroxysmal activity. *Neuropädiatrie.* 1971;2:247--304.
6. John ER, Ahn H, Prichep L, et al. Developmental equations for the electroencephalogram. *Science.* 1980;210(4475):1255--1258.
7. John ER, Prichep LS, Fridman J, Easton P. Neurometrics: computer-assisted differential diagnosis of brain dysfunctions. *Science.* 1988;239(4836):162--169.
8. van Putten MJAM, Tavy DLJ. Continuous quantitative EEG monitoring in hemispheric stroke patients using the brain symmetry index. *Stroke.* 2004;35(11):2489--2492.
9. van Putten MJAM. The revised brain symmetry index. *Clin Neurophysiol.* 2007;118(11):2362--2367.
10. Finnigan S, van Putten MJAM. EEG in ischaemic stroke: quantitative EEG can uniquely inform (sub-)acute prognoses and clinical management. *Clin Neurophysiol.* 2013;124(1):10--19.
11. Lodder SS, van Putten MJAM. Automated EEG analysis: characterizing the posterior dominant rhythm. *J Neurosci Methods.* 2011;200(1):86--93.
12. Lodder SS, van Putten MJAM. Quantification of the adult EEG background pattern. *Clin Neurophysiol.* 2013;124(2):228--237.
13. Lodder SS, Askamp J, van Putten MJAM. Computer-assisted interpretation of the EEG background pattern: a clinical evaluation. *PLoS One.* 2014;9(1):e85966.
14. Zibrandtsen IC, Kjaer TW. Fully automatic peak frequency estimation of the posterior dominant rhythm in a large retrospective hospital EEG cohort. *Clin Neurophysiol Pract.* 2021;6:1--9.
15. López S, Suarez G, Jungreis D, Obeid I, Picone J. Automated identification of abnormal adult EEGs. *IEEE Signal Process Med Biol Symp (SPMB).* 2015:1--5.
16. Obeid I, Picone J. The Temple University Hospital EEG data corpus. *Front Neurosci.* 2016;10:196.
17. Schirrmeister RT, Springenberg JT, Fiederer LDJ, et al. Deep learning with convolutional neural networks for EEG decoding and visualization. *Hum Brain Mapp.* 2017;38(11):5391--5420.
18. Gemein LAW, Schirrmeister RT, Chrabąszcz P, et al. Machine-learning-based diagnostics of EEG pathology. *NeuroImage.* 2020;220:117021.
19. Kostas D, Aroca-Ouellette S, Rudzicz F. BENDR: using transformers and a contrastive self-supervised learning task to learn from massive amounts of EEG data. *Front Hum Neurosci.* 2021;15:653659.
20. Jiang W-B, Zhao L-M, Lu B-L. Large Brain Model for learning generic representations with tremendous EEG data in BCI (LaBraM). *ICLR.* 2024.
21. Biswal S, Nip Z, Moura Junior V, et al. Automated information extraction from free-text EEG reports. *Proc IEEE EMBC.* 2015:6804--6807.
22. Markovic A, Veen D, Hamann C, et al. Joint heritability of sleep EEG spindle activity and thalamic volume in early adolescence. *J Neurosci.* 2025;45(21):e1138242025.
23. Gorgoni M, Reda F, D'Atri A, et al. The heritability of the human K-complex: a twin study. *Sleep.* 2019;42(6):zsz053.
24. Landolt HP. Genetic determination of sleep EEG profiles in healthy humans. *Prog Brain Res.* 2011;193:51--61.
25. Ambrosius U, Lietzenmaier S, Wehrle R, et al. Heritability of sleep electroencephalogram. *Biol Psychiatry.* 2008;64(4):344--348.
26. Bachmann V, Klaus F, Bodenmann S, et al. Functional ADA polymorphism increases sleep depth and reduces vigilant attention in humans. *Cereb Cortex.* 2012;22(4):962--970.
27. Bodenmann S, Hohoff C, Freitag C, et al. Polymorphisms of ADORA2A modulate psychomotor vigilance and the effects of caffeine on neurobehavioural performance and sleep EEG after sleep deprivation. *Br J Pharmacol.* 2012;165(6):1904--1913.
28. Mazzotti DR, Guindalini C, de Souza AA, et al. Adenosine deaminase polymorphism affects sleep EEG spectral power in a large epidemiological sample. *PLoS One.* 2012;7(8):e44154.
29. Campos-Beltrán D, Marshall L. Changes in sleep EEG with aging in humans and rodents. *Pflugers Arch.* 2021;473(5):841--851.
30. El Kanbi K, Tort-Colet N, Benchenane K, Destexhe A. EEG and computational aspects of how ageing affects sleep slow waves. *J Sleep Res.* 2026;35(3):e70214.
31. Roehrs T, Roth T. Drug-related sleep stage changes: functional significance and clinical relevance. *Sleep Med Clin.* 2010;5(4):559--570.
32. Sun C, Karakis I, Herlopian A, et al. MORGOTH: toward automated EEG interpretation. *Lancet Digit Health.* In press. **\[verify\]**
33. Cole TJ, Green PJ. Smoothing reference centile curves: the LMS method and penalized likelihood. *Stat Med.* 1992;11(10):1305--1319.
34. Rigby RA, Stasinopoulos DM. Generalized additive models for location, scale and shape. *J R Stat Soc Ser C.* 2005;54(3):507--554.
35. Tveit J, Aurlien H, Plis S, et al. Automated interpretation of clinical electroencephalograms using artificial intelligence (SCORE-AI). *JAMA Neurol.* 2023;80(8):805--812.
36. Hirsch LJ, Fong MWK, Leitinger M, et al. American Clinical Neurophysiology Society's Standardized Critical Care EEG Terminology: 2021 Version. *J Clin Neurophysiol.* 2021;38(1):1--29.
37. Mansilla D, Tveit J, Aurlien H, et al. Generalizability of electroencephalographic interpretation using artificial intelligence: an external validation study. *Epilepsia.* 2024;65(10):3028--3037.
38. Beun AM, van Emde Boas W, Dekker E. Sharp transients in the sleep EEG of healthy adults: a possible pitfall in the diagnostic assessment of seizure disorders. *Electroencephalogr Clin Neurophysiol.* 1998;106(1):44--51.
