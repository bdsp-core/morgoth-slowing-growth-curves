# Literature Review: Normative Growth Curves for qEEG Slowing and Deviation-from-Normal Scoring

*Prepared for the "morgoth-slowing-growth-curves" methods paper. All citations below were located and, where noted, verified against primary sources via web search. Where a figure or attribution is uncertain, this is flagged explicitly.*

## Scope

This review situates our work — normative age × sex × sleep-stage percentile "growth curves" for quantitative EEG (qEEG) slowing features (absolute/relative delta and theta power, delta/alpha ratio [DAR], theta/alpha ratio [TAR], and left–right homologous-channel asymmetry), built on 12,379 routine clinical EEGs from ~12,000 MGB patients spanning infancy to >90 years, with per-recording deviation-from-normal scoring, Morgoth foundation-model gating, and machine-generated clinician-style report sentences validated against free-text clinical reports. We survey four literatures: (1) lifespan/normative qEEG and EEG "brain age"; (2) the classic small-sample developmental norms clinicians still rely on; (3) qEEG abnormality/slowing quantification (van Putten and others); and (4) automated EEG interpretation and report generation.

## Comparison Table of Key Prior Work

| First author (year) | What they measured | Population / setting | Age range | N (subjects) | Quantitative vs qualitative | Normal-only vs deviation-from-normal | Sleep-stage-specific? | Key limitation |
|---|---|---|---|---|---|---|---|---|
| Petersén & Eeg-Olofsson (1971), *Neuropädiatrie* | Non-paroxysmal EEG features, alpha frequency/voltage | Healthy children | 1–15 yr | ~743 (widely cited figure) | Semi-quantitative / visual | Normal-only (age norms) | No (awake focus) | Small by modern standards; visual; children only |
| John et al. (1980), *Science* 210:1255 | 32 band-power regressions ("developmental equations") | Healthy US + Swedish children | ~6–16 yr | ~600+ combined | Quantitative (linear age regressions) | Normal-only; companion paper flags deviation | No | Narrow age band; eyes-closed rest; small N |
| John et al. (1988), *Science* 239:162 ("Neurometrics") / NeuroGuide, NxLink lineage | Age-regressed, z-scored spectral features | Healthy + clinical | Childhood–adult | Hundreds per norm set | Quantitative; z-scores vs norms | Deviation-from-normal (z-scores) | No | Wake resting only; modest N; database opacity |
| Bethlehem et al. (2022), *Nature* 604:525 | MRI brain morphology centile "brain charts" | Aggregated cohorts | 115 d post-conception–100 yr | 101,457 | Quantitative (GAMLSS centiles) | Deviation-from-normal (centiles) | N/A (MRI) | Not EEG; structural, not functional |
| Engemann/Sabbagh benchmark — Engemann et al. (2022), *NeuroImage* 262:119512 | Brain-age from M/EEG resting spectra | Research + clinical | Adult | Hundreds–thousands | Quantitative (regression) | Deviation (brain-age gap) | No | Single scalar (age); not slowing-specific |
| van Putten & Tavy (2004), *Stroke* 35:2489 | Brain Symmetry Index (BSI) | Acute hemispheric stroke | Adult | 21 | Quantitative (0–1 index) | Abnormality index (not age-normed) | No | Tiny N; asymmetry only; no age norms |
| van Putten (2007), *Clin Neurophysiol* 118:2362 | Revised/pairwise-derived BSI (pBSI) | Stroke / monitoring | Adult | Small cohorts | Quantitative | Abnormality index | No | Asymmetry only; not lifespan-normed |
| Finnigan & van Putten (2013), *Clin Neurophysiol* 124:10 (review) + Finnigan et al. (2016) | DAR, (D+T)/(A+B), BSI in ischemia | Acute/subacute stroke | Adult | Cohorts (tens–hundreds) | Quantitative (ratios) | Correlates w/ severity; not age-normed | No | Small; single population; thresholds not lifespan-calibrated |
| ICU delirium qEEG (e.g., 2022–2023 signatures/DeltaScan studies) | Relative delta/theta, alpha-delta ratio | ICU, mechanically ventilated | Adult | ~tens–hundreds | Quantitative | Case-control discrimination | No (illness state, not sleep) | Not age/sex/stage normed; illness-specific |
| López et al. (2015/16), IEEE SPMB; Obeid & Picone (2016), *Front Neurosci* (TUAB corpus) | Binary normal vs abnormal | TUH clinical EEG | Adult | 2,383 subj / 2,993 recs (TUAB) | Quantitative (ML) | Binary label (not graded deviation) | No | Coarse binary; no localization/band; no norms |
| Schirrmeister et al. (2017), arXiv 1708.08012; Gemein et al. (2020), *NeuroImage* 220:117021 | ConvNet pathology decoding | TUAB | Adult | 2,383 subj | Quantitative (deep learning) | Binary pathology | No | Binary; limited interpretability; no report text |
| Biswal et al. (2015), *IEEE EMBC* 2015:6804 (incl. Westover) | NLP extraction of seizures/IEDs from reports | 3,277 EEG reports | Mixed | 3,277 docs | Quantitative (NLP) | Extraction, not generation | No | Extracts from, does not generate, reports |
| **This work (2026)** | Delta/theta abs+rel power, DAR, TAR, L–R asymmetry; deviation scores | Routine clinical EEG, MGB | Infancy–>90 yr | **12,379 EEGs / ~12,000 pts** | **Quantitative (percentile curves + z/burden/prevalence/persistence)** | **Deviation-from-normal, per recording** | **Yes (per sleep stage)** | New; single health system; needs external validation |

*Notes on uncertain figures:* Petersén & Eeg-Olofsson's exact N (often cited ~700+ children) and the precise N in each John et al. norm set are reported variably in secondary sources; treat as approximate. The ICU delirium row aggregates several recent studies rather than one canonical paper, so no single N is authoritative.

## (i) What was already known — and how well was it quantified

The direction of lifespan spectral change is textbook-settled: low-frequency (delta, theta) power dominates in infancy and early childhood and declines with maturation, while faster rhythms increase, the posterior dominant rhythm accelerating from ~3–4 Hz in infancy toward the adult 8–12 Hz alpha by adolescence (multiple developmental qEEG studies converge on this "slow-to-fast" shift). Aperiodic (1/f) activity flattens with development. In aging, the picture is subtler and health-dependent: absolute low-frequency power tends to decline into old age in healthy individuals, alpha frequency slows modestly, and much apparent "aging slowing" reflects comorbidity rather than healthy aging.

Modern quantification of this trajectory has taken two forms. First, **EEG "brain age"** regresses chronological age on resting spectral (and aperiodic) features; a reusable M/EEG benchmark by Engemann and colleagues (Engemann et al., 2022, *NeuroImage*) formalized the pipeline, and infant work predicts age within ~3 months from resting power in the first three years of life (medRxiv/PMC, 2024). Second, and conceptually closest to us, **normative centile modeling** of brain measures: Bethlehem et al. (2022, *Nature*) built MRI "brain charts" across the lifespan (n = 101,457) using GAMLSS to yield individual centile/deviation scores — the structural-imaging analog of what we do functionally with EEG.

Crucially, almost all of this lifespan qEEG literature reports **normal values** (means, regressions, centiles of healthy people), not **per-recording deviation of a clinical EEG from its matched norm**, and essentially none is **sleep-stage-specific**. Brain-age collapses the spectrum to a single scalar (predicted age) and is not slowing-localized. So the raw phenomenology was known; a lifespan-wide, stage-resolved, deviation-scoring instrument for clinical slowing features was not.

## (ii) The historical small-sample basis clinicians still rely on

Day-to-day clinical EEG reading rests on age-dependent norms established decades ago on modest samples, largely by visual/semi-quantitative analysis:

- **Petersén & Eeg-Olofsson (1971, *Neuropädiatrie*)**, "The development of the electroencephalogram in normal children from the age of 1 through 15 years," is a foundational pediatric reference for age-expected background and alpha voltage/frequency. It is qualitative-to-semiquantitative, awake-focused, and limited to children.
- **John et al. (1980, *Science* 210:1255–1258)**, "Developmental equations for the electroencephalogram," gave 32 linear age regressions of band power across four bilateral regions, replicated across US and Swedish children — an elegant early quantification, but over a narrow age band, eyes-closed rest only, and a few hundred subjects. The companion paper (John et al., 1980, *Science* 210:1258) explicitly used deviation from these equations to flag brain dysfunction — an important early precedent for our deviation framing, at far smaller scale.
- **John et al. (1988, *Science* 239:162), "Neurometrics,"** and the commercial normative databases it seeded (NeuroGuide/Applied Neuroscience; NxLink) generalized age-regressed z-scoring. These remain wake-resting, adult/child-segmented, and of modest and somewhat opaque N.
- The **textbook/atlas lineage** (Niedermeyer & Lopes da Silva, *Electroencephalography*; Blume's atlas of pediatric/adult EEG) codifies these norms narratively.

The through-line: the normative substrate clinicians actually use is small-N, mostly qualitative, wake-only, and stitched together across age bands — precisely the substrate a large, stage-resolved, continuous-lifespan model can replace.

## (iii) qEEG abnormality and slowing quantification (van Putten et al. and others)

A separate literature quantifies *pathological* EEG directly, without lifespan normalization:

- **Brain Symmetry Index (BSI).** van Putten & Tavy (2004, *Stroke* 35:2489) introduced the BSI, a single 0–1 measure of interhemispheric spectral power asymmetry, and showed a strong correlation with NIHSS stroke severity (ρ ≈ 0.86) in 21 acute stroke patients. van Putten (2007, *Clin Neurophysiol* 118:2362) published the revised/pairwise BSI to sharpen spatial-temporal sensitivity for carotid endarterectomy, acute stroke, and seizure detection. This is the intellectual ancestor of our left–right homologous-channel asymmetry feature — but the BSI is a bare abnormality index, not age/sex/stage-normed.
- **Slowing ratios in ischemia.** DAR and related indices ((delta+theta)/(alpha+beta)) correlate with acute-stroke severity and outcome (Finnigan & van Putten, 2013, *Clin Neurophysiol* 124:10, review; and related correlation studies). Again: single-population, threshold-based, not lifespan-calibrated.
- **Encephalopathy / coma prognosis.** The Twente group (Tjepkema-Cloostermans, Hofmeijer, Ruijter, van Putten) developed the Cerebral Recovery Index and used early qEEG/background patterns for outcome prediction in postanoxic coma. These reduce a recording to a prognostic score for a specific critical-illness context.
- **ICU delirium/encephalopathy.** Relative delta/theta power and the alpha-delta ratio discriminate delirium and coma in ventilated ICU patients (recent qEEG-signature studies report AUCs ~0.94), and single-/few-channel devices (DeltaScan lineage; van der Kooi/Slooter group) operationalize polymorphic delta detection at the bedside.

Collectively, this literature proves that **slowing and asymmetry are quantifiable and clinically meaningful**, but every instrument is tied to one disease/setting, uses fixed thresholds, ignores age/sex, and — universally — ignores sleep stage. None asks "how far does this recording deviate from the age/sex/stage-matched normal population?"

## (iv) Automated EEG interpretation and report generation

- **Binary normal/abnormal classification.** The Temple University Hospital Abnormal corpus (TUAB; López et al., 2015/16; Obeid & Picone) — ~2,993 recordings from ~2,383 subjects — became the standard benchmark. Schirrmeister et al. (2017; and Gemein et al., 2020, *NeuroImage* 220:117021) reached ~85% with deep ConvNets; many later models report higher on TUAB. These give a coarse binary label with no localization, band, severity, or narrative.
- **EEG foundation models.** Self-supervised pretraining now dominates: BENDR (Kostas et al., 2021), LaBraM (Jiang et al., ICLR 2024, ~2,500 h pretraining), EEGFormer, REVE, and clinically grounded variants (CLEF, EEG-CLIP) that align EEG embeddings to neurologist reports/EHR. Our **Morgoth** heads sit in this family but are used differently — as a calibrated *gate* on reporting rather than an end-to-end black box.
- **NLP of and generation from reports.** Biswal et al. (2015, *IEEE EMBC*; senior author Westover) extracted seizures/IEDs from 3,277 free-text EEG reports with >96–99% AUC; later hierarchical/BERT pipelines convert reports to structured data at >98% accuracy for focal/generalized labels. Report *generation* is newer: a hybrid AI system for automated EEG background analysis and LLM report generation (2024) and EEG-to-language models (e.g., CELM, 2026) generate narrative from signal. These validate that report text can be produced/parsed — but do not tie generated findings to a lifespan-normative deviation model, nor validate stage-specific slowing sentences against the actual clinical report corpus.

## (v) The gap — and how our work advances it

**The gap.** No prior work combines (a) lifespan-continuous, (b) sex-specific, and (c) sleep-stage-specific normative modeling of clinical slowing features with (d) per-recording deviation-from-normal scoring, (e) at a scale of ~12,000 patients drawn from routine clinical practice, and (f) closes the loop to clinician-style narrative validated against real reports. Lifespan qEEG describes normal values; classic norms are tiny, wake-only, and qualitative; abnormality indices (BSI/DAR) are disease-specific and un-normed; automated interpreters output binary labels or ungrounded text.

**Our specific contributions in this context:**

- **Deviation-from-normal, not normal values.** Every recording is scored against age/sex/stage-matched norms (z-scores, burden, prevalence, persistence, stage-accentuation) — extending the John et al. (1980/1988) deviation idea to a modern scale and to slowing features and asymmetry specifically.
- **Lifespan-continuous AND sleep-stage-specific.** Curves span infancy to >90 years and are resolved per sleep stage via a deep-learning stager — a combination absent from all prior norms (which are wake-only and age-banded) and from all abnormality indices.
- **Scale and ecological validity.** 12,379 routine clinical EEGs (~12,000 patients) dwarf the classic norm sets (hundreds) and approach imaging "brain-chart" scale (Bethlehem et al., 2022) while being functional and clinical rather than research MRI.
- **Feature breadth tied to clinical semantics.** Absolute/relative delta and theta, DAR, TAR, and homologous-channel asymmetry map directly onto how clinicians describe slowing and asymmetry (cf. van Putten's BSI, stroke DAR), but now age/sex/stage-normed.
- **Discrimination of normal vs focal vs generalized slowing** from the deviation profile — beyond binary normal/abnormal (TUAB lineage).
- **Foundation-model gating (Morgoth).** EEG foundation-model heads calibrated to expert reads gate reporting, coupling self-supervised representation learning (LaBraM/BENDR family) to a normative, interpretable output.
- **Recapitulating and validating expert report language.** We generate clinician-style sentences (e.g., "frequent mild left temporal delta slowing, present only in sleep, accentuated in N2") and validate them against free-text clinical reports (agreement: region 0.91, side 0.78, band 0.74) — moving beyond report *extraction* (Biswal et al., 2015) and ungrounded report *generation* to normatively grounded, validated generation.
- **Fully reproducible Python pipeline**, in contrast to the opaque commercial normative databases (NeuroGuide/NxLink lineage).

In short, prior literature separately established the phenomenology (lifespan slowing), a small qualitative normative substrate, disease-specific abnormality indices, and automated binary classifiers/report tools. Our work unifies these into a single, large-scale, lifespan- and stage-resolved, deviation-scoring instrument whose outputs are expressed in — and validated against — the language of clinical EEG reports.

---

### Selected references (verify page-level details before submission)

1. Petersén I, Eeg-Olofsson O. The development of the electroencephalogram in normal children from the age of 1 through 15 years: non-paroxysmal activity. *Neuropädiatrie*. 1971. (Classic pediatric norms.)
2. John ER, Ahn H, Prichep L, et al. Developmental equations for the electroencephalogram. *Science*. 1980;210(4475):1255–1258. https://www.science.org/doi/10.1126/science.7434026
3. John ER, et al. Developmental equations reflect brain dysfunctions. *Science*. 1980;210:1258–1260. https://www.science.org/doi/10.1126/science.7434027
4. John ER, Prichep LS, Fridman J, Easton P. Neurometrics: computer-assisted differential diagnosis of brain dysfunctions. *Science*. 1988;239:162–169. https://www.science.org/doi/10.1126/science.3336779
5. Bethlehem RAI, Seidlitz J, et al. Brain charts for the human lifespan. *Nature*. 2022;604:525–533. https://www.nature.com/articles/s41586-022-04554-y
6. Engemann DA, et al. A reusable benchmark of brain-age prediction from M/EEG resting-state signals. *NeuroImage*. 2022. https://www.sciencedirect.com/science/article/pii/S105381192200636X
7. van Putten MJAM, Tavy DLJ. Continuous quantitative EEG monitoring in hemispheric stroke patients using the brain symmetry index. *Stroke*. 2004;35(11):2489–2492. https://www.ahajournals.org/doi/10.1161/01.str.0000144649.49861.1d
8. van Putten MJAM. The revised brain symmetry index. *Clin Neurophysiol*. 2007;118(11):2362–2367. https://pubmed.ncbi.nlm.nih.gov/17888719/
9. Finnigan S, van Putten MJAM. EEG in ischaemic stroke: quantitative EEG can uniquely inform (sub-)acute prognoses and clinical management. *Clin Neurophysiol*. 2013. https://www.sciencedirect.com/science/article/abs/pii/S1388245710006528
10. López S, Suarez G, Jungreis D, Obeid I, Picone J. Automated identification of abnormal adult EEGs. *IEEE SPMB*. 2015. https://pmc.ncbi.nlm.nih.gov/articles/PMC4868184/
11. Schirrmeister RT, Gemein L, Eggensperger K, Hutter F, Ball T. Deep learning with convolutional neural networks for decoding and visualization of EEG pathology. arXiv:1708.08012 (2017); see also Gemein et al., *NeuroImage* 2020;220:117021. https://arxiv.org/abs/1708.08012
12. Jiang W-B, Zhao L-M, Lu B-L. Large Brain Model (LaBraM) for learning generic representations with tremendous EEG data in BCI. *ICLR* 2024. https://github.com/935963004/LaBraM
13. Kostas D, Aroca-Ouellette S, Rudzicz F. BENDR: using transformers and a contrastive self-supervised learning task to learn from massive amounts of EEG data. *Front Hum Neurosci*. 2021. https://www.frontiersin.org/articles/10.3389/fnhum.2021.653659/full
14. Biswal S, Nip Z, Moura Junior V, Bianchi MT, Rosenthal ES, Westover MB. Automated information extraction from free-text EEG reports. *IEEE EMBC*. 2015:6804–6807. https://pubmed.ncbi.nlm.nih.gov/26737856/
