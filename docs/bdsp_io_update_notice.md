# Draft: Harvard EEG Database (bdsp.io) update notice

Draft announcement to post on the BDSP / Harvard EEG Database writeup on bdsp.io once the source-data
cleanup + this project's releases are live. (This is a draft for the site maintainers — not the live
page.)

---

## What's new — EEG dataset cleanup & normative-slowing resources

**1. Storage cleanup (scalp EEG).** We are pruning non-recorded/dead channels from scalp EEG files and
re-packaging them from EDF into an annotation-ready **HDF5** format. Scope and guarantees:
- **Only scalp studies** are pruned; **stereo/intracranial (sEEG/iEEG) recordings are left byte-for-byte
  intact.**
- We keep every genuinely-recorded lead — the 10–20 scalp EEG set, **ECG/EKG, EOG (eye leads), EMG**,
  and any other real physiologic channel — and drop only **proven-dead** channels (flatline, railed,
  all-NaN, duplicate-of-reference).
- **No signal is altered:** native sampling rate, no re-referencing/filtering; retained channels are
  preserved bit-exactly.
- **No source is deleted until it passes automated QC** (per-channel exact reconstruction, summary-stat
  & band-power parity, and model-inference parity) **and** a verified backup exists (staged, audited
  delete). Expected ~45–60% storage reduction with zero loss of real signal.
- The H5 format supports adding annotations over time (sleep stages, events, findings).

**2. Normative EEG-slowing resources (new).** A companion open project provides age × sex × sleep-stage
**normative growth curves** for quantitative EEG slowing, deviation-from-normal scoring, and
per-recording labels (focal/generalized slowing, band, location) with provenance back to the source
reports — see the `morgoth-slowing-growth-curves` repository and the accompanying paper.

**Action needed by users:** none — recording IDs and access are unchanged; H5 files carry provenance
back to the original EDF. Questions → BDSP team.

---

### TODO before posting
- [ ] Confirm final storage-savings number from the cleanup pilot.
- [ ] Add links: repo, paper/preprint DOI, H5 format spec.
- [ ] Note the effective date and which sites/date-ranges are converted first.
- [ ] Have BDSP data-governance review the deletion/QC guarantees wording.
