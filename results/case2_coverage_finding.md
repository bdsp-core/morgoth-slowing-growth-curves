# The case-2 "floor" is largely a WINDOW / COVERAGE mismatch (2026-07-10)

MBW review (case 14 = a flat EEG; recurring "is this sleep?") led to the real cause.

**Mechanism (confirmed in code).**
- The Morgoth **gate** (`scripts/30_ingest_worker.py::run_gate`) runs on `load_edf_referential(full EDF)` —
  the **whole recording**, up to the size guard (~55 h).
- Our **deviation field** comes from the Growth_curves `.mat` `res` table — the **first 600 s only**.

**So for a long continuous EEG, Morgoth sees hours and our field sees the first 10 minutes.** If slowing
occurs anywhere outside that first 10 min, Morgoth fires and our field says nothing — with no feature failure,
no norm problem, and no physiology involved.

**Scale (the 40-case review set).** Recording durations (from EDF headers):
- median **2.5 h**; **39 / 40 are longer than our 600 s window**; **18 / 40 are > 6 h** (up to 24 h);
  only 1 is routine-length.

The case-2 set self-selects for long cEEG precisely because that is where the two windows diverge most.

**Consequence for the round-1 review.** 16 of MBW's 17 round-1 verdicts were made on a viewer clip taken
from a window > 600 s into the recording (my clip-picker chose the "longest clean stretch", which on a 24 h
cEEG lands hours downstream). So MBW adjudicated *a window our field never analyzed*. The 7 "our age-norm
over-corrects" and 3 "genuine miss" verdicts are therefore confounded: MBW correctly saw slowing in a later
window, but our "nothing" came from the first 10 min. Round-1 verdicts saved to
`results/case2_responses_round1.jsonl` with a `window_mismatch` flag; they should not be used as-is.

**What this is NOT.** It is not the age-norm over-correcting (the set is younger than captured), not primarily
physiologic sleep (though many are sleep), and not a feature failure. It is a **coverage limitation**: the
Growth_curves pipeline analyses only the first 600 s of each recording.

**Fixes.**
1. *Pipeline (the real fix):* extract features across the whole recording (or a representative time sample),
   not just the first 600 s, so our field and the gate see the same data. For routine EEG (~20–30 min) this
   is a non-issue; it matters only for cEEG.
2. *This review:* the viewer now shows **REC LENGTH (h)** and **WE ANALYZED (first 10 min / whole)**, plus a
   **COVERAGE** verdict, so MBW can re-classify the long-cEEG cases correctly.

**Also surfaced (QC).** cEEG recordings contain flat/suppressed stretches (case 14 = a fully flat window at
2.4 h). Our first-600 s flat guard did not catch them because the first 600 s was active; a whole-recording
pipeline must carry the flat/suppression guard across the entire record (and route burst-suppression /
disconnection to the dedicated detector, per MBW).
