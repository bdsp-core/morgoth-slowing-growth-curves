# P6 — do readers under-report SLEEP slowing? (SAP §10; rebuilt on v6)

The evidence file for this prediction (`v4a_wake_sleep`) was deleted in the results purge and had not been regenerated, leaving P6 unevaluated. Rebuilt here from v6 fleet output only.

**Avoiding the circularity trap.** Asking 'how much sleep slowing do we see in report-normals?' is vacuous — the norms are fit on the clean-normals *per stage*, so ~5% of them exceed the 95th centile in every stage by construction. Instead we ask: **when slowing is visible only once the patient is asleep, do readers still name it?** The report label is the OUTCOME, not the reference, so the normative fit cannot manufacture the effect.

Stage-matched age-conditioned z on `TAR` (whole-head), τ = 1.645 (95th centile), `clean_pair` only (n = 19,395).

| group | n | report names slowing |
|---|---|---|
| slowing visible in **wake** | 4,282 | **74.8%** |
| slowing visible **only in sleep** | 709 | **53.6%** |
| visible in neither (base rate) | 14,400 | 40.0% |

Our sleep-slowing detection rate **15.6%** vs the report's slowing rate **48.2%**.

**P6 → FALSIFIED.** Readers name slowing in 74.8% of recordings where it is visible awake, but only 53.6% when it is visible only in sleep.
