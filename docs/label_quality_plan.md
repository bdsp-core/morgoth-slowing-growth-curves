# Label re-derivation & cleanup plan (from raw reports) — foundational for (a) and (b)

Today's audit showed the labels have real defects; several are fixed, the hardest is open. Both the
per-stage cohort analysis (a) and the expansion integration (b) must sit on **cleanly re-derived labels
from the raw reports** — otherwise we don't know who is normal, which corrupts the normative reference.

## Sources (we have them; coverage confirmed)
- Raw report text: `EEGs_And_Reports.csv` (1.1 GB, on Box+S3). Structured findings: per-site `*_findings.csv`
  (224,526 rows, 68,742 patients — covers **all** sites, not just the cohort).
- **Expansion patients are recoverable:** 100% of the 5,759 expansion pids are in the findings, 95% in the
  raw reports. So labels can be derived for cohort **and** expansion from the same sources.

## Defects found today
1. **Side/region extractor was broken** — scoped only to "slow" sentences, bilateral-before-side, ignored
   electrodes. **FIXED (v2):** per-clause, 10-20 electrode→side/region, R>L/L>R, side-wins-over-diffuse
   (unilateral sides 555→~2,000; AUROC 0.87→0.93). *(committed)*
2. **Class-flag under-count** — `.contains("report")` dropped `verified`/`annotation`-only findings
   (~8% focal, ~5% gen). **FIXED.** *(committed)*
3. **Normal reference contaminated (57%)** — priority cascade let "normal" win over slowing. **FIXED:**
   clean-normal = normal & ~abnormal & ~focal & ~gen. *(committed)*
4. **Band extractor** — same clause-scoping issue; **FIXED (v2).** *(committed)*
5. **OPEN — generalized-slowing conflates pathologic with physiologic/sleep slowing.** The `gen slowing`
   flag is positive in ~77% of recordings — implausible for pathology; it is a whole-recording,
   stage-agnostic flag that sweeps in drowsy/sleep delta. This is the crux and needs design + clinical input.

## The open problem: pathologic vs physiologic generalized slowing
A report/flag that says "generalized slowing" may describe (i) true diffuse encephalopathy, or (ii) normal
drowsy/sleep slowing. Candidate signals to separate them (to be validated with Brandon):
- **Report qualifiers:** phrases like "consistent with drowsiness/sleep", "drowsy state", "state-dependent"
  → physiologic; "abnormal", "excessive for age/state", "encephalopathy" → pathologic.
- **Flag co-occurrence:** `gen slowing` **with** the `abnormal` flag → pathologic; gen-slowing **with**
  `normal` flag and intact `spindles`/`k_complexes` → physiologic (Brandon's spindle intuition;
  gen-slow-with-spindles was 75% abnormal vs 83% without).
- **State scoping:** slowing reported **in wakefulness** is more reliably pathologic; slowing only in sleep
  is the human-hard case → defer to our per-stage normative model.
- **Quantitative arbiter (the thesis):** ultimately, deviation **above the stage-matched clean-normal**
  band is our pathology criterion, independent of the noisy report flag (see `normative_deviation_plan.md`).
**Decision needed from Brandon:** the rule set for calling generalized slowing pathologic vs physiologic
(qualifier lists, whether to require the abnormal flag, how to treat sleep-only slowing).

## The re-derivation (cohort + expansion, one pass)
1. Extend `scripts/52` to derive labels for **every patient with features** (cohort + expansion), keyed by
   (site, pid, date), from findings (corrected flags) + report text (v2 side/region/band + drowsy/abnormal
   qualifiers), not just the cohort. Emit `labels_canonical` covering both, with a `phys_vs_path` field for
   generalized slowing per the agreed rules.
2. Rebuild the clean-normal reference on the union; re-fit growth curves; re-run one-vs-normal + localization.
3. Provenance for every label back to the source note (as now).

## How this feeds (a) and (b)
- **(a) per-stage on the paper cohort:** also requires merging the **abnormal sleep stages** — the 7,464
  `original_abnormal_stages/` predictions were never merged into `segment_stages` (only ~5k normals are
  staged), so the current stage table (N3=396) is missing all abnormal sleep. Merge them → full cohort
  stage table → per-stage pathology on the cohort. *(staging assembly is label-independent; can proceed)*
- **(b) expansion integration:** re-derive expansion labels (above) → build expansion derived tables with
  correct patient ids → **merge into the cohort norms**, which is what actually fills N3 (expansion has
  10,300 recordings with N3). Only valid once labels + clean-normal are established for the expansion.

## Sequencing
clean labels (this plan, incl. the gen phys/path rule) → clean-normal reference → growth curves →
(a) cohort per-stage  and  (b) expansion merge. Label quality is the gate; everything else follows.
