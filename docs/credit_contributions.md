# CRediT author contributions

**This file is the source of truth.** Edit the two tables below, then run:

```
python3 scripts/credit_contributions.py --write
```

That re-checks the tables, rewrites the CRediT block inside `docs/manuscript_draft.md`, and refreshes the
generated per-author section at the bottom of this file. Do not edit the manuscript's CRediT block directly —
it is overwritten from here.

Roles use the 14 terms of the CRediT taxonomy, in the taxonomy's canonical order. Contributors are given as
initials, listed in title-page byline order. Every author must appear in at least one role.

---

## 1. Authors and initials

Byline order, exactly as the title page lists them. Initials must be unique.

| Initials | Author | Affiliation |
|---|---|---|
| JJ  | Jin Jing            | BIDMC / Harvard |
| CS  | Chenxi Sun          | Stanford |
| WG  | Wolfgang Ganglberger| BIDMC / Harvard |
| ADL | Alice D. Lam        | MGH / Harvard |
| HS  | Haoqi Sun           | BIDMC / Harvard |
| TZ  | Tianyu Zhang        | BIDMC / Harvard |
| DMG | Daniel M. Goldenholz| BIDMC / Harvard |
| FAN | Fabio A. Nascimento | WashU |
| DY  | Doyle Yuan          | UT Southwestern |
| SB  | Sándor Beniczky     | Danish Epilepsy Centre / Aarhus |
| JAK | Jennifer A. Kim     | Yale |
| AFS | Aaron F. Struck     | WashU |
| SFZ | Sahar F. Zafar      | MGH / Harvard |
| RJT | Robert J. Thomas    | BIDMC / Harvard |
| MMS | Mouhsin M. Shafi    | BIDMC / Harvard |
| MBW | M. Brandon Westover | Stanford |

## 2. Contributions

Add or remove initials in the right-hand column. Order within a cell does not matter — the script re-sorts
into byline order. Leave a cell empty only if genuinely no author filled that role.

| CRediT role | Contributors |
|---|---|
| Conceptualization | RJT, AFS, SFZ, MMS, MBW, JJ, CS, WG |
| Data curation | WG, DY, SB, MBW |
| Formal analysis | JJ, CS, WG, MBW |
| Funding acquisition | RJT, MBW |
| Investigation | ADL, FAN, DY, SB, JAK, AFS, SFZ, RJT, MMS, MBW |
| Methodology | JJ, CS, WG, HS, DMG, MBW |
| Project administration | AFS, SFZ, JAK, RJT, MBW |
| Resources | FAN, DY, SB, RJT, MMS, MBW |
| Software | JJ, CS, WG, HS, MBW |
| Supervision | AFS, JAK, SFZ, RJT, MBW |
| Validation | WG, ADL, FAN, SB, JAK, AFS, SFZ, MBW |
| Visualization | JJ, WG, CS, MBW |
| Writing -- original draft | WG, RJT, JJ, CS, MBW |
| Writing -- review & editing | JJ, CS, WG, ADL, HS, TZ, DMG, FAN, DY, SB, JAK, AFS, SFZ, RJT, MMS, MBW |

## 3. Notes carried into the manuscript

One line per note; each is appended below the CRediT block in the manuscript verbatim.

- Under Resources, S.B. provided the SAI-100 evaluation set and its expert reads (§2.9).

## 4. How the current assignments were arrived at

Stated so each author can check a claim rather than accept it:

- **MBW** holds all 14 roles at the author's own statement, consistent with the repository record: the
  analysis repository's history is 631 commits under a single author.
- **JJ, CS, WG, HS, TZ** — the modelling and engineering contributions, split as the round-1 draft had them.
  CS additionally carries Visualization; TZ and WG carry Data curation.
- **ADL, FAN, DY, JAK, AFS, SFZ** — Investigation and Validation as the reading neurologists.
- **SB** — Resources, for the SAI-100 evaluation set and its expert reads, plus Investigation and Validation.
- **RJT, MMS** — Conceptualization and Supervision as co-senior authors, with Resources.
- **DMG** — Methodology, for statistical input.

Everything except the MBW row is inferred from each author's manuscript-visible part, not from a record of
who did what. Correct your own row; that is what this file is for.

**Worth a deliberate decision:** the title page marks JJ, CS and WG as co-first authors who "contributed
equally," while MBW holds all 14 roles. Both statements can be true — CRediT roles are not authorship
weight — but editors sometimes query the combination, so it is better settled on purpose than by default.

---

<!-- GENERATED BELOW THIS LINE — do not edit; run scripts/credit_contributions.py --write -->

## Per-author rendering (generated)

The form journals typeset. Generated from the table above; edit that, not this.

**Jin Jing (JJ):** Conceptualization, Formal analysis, Methodology, Software, Visualization, Writing -- original draft, Writing -- review & editing.
**Chenxi Sun (CS):** Conceptualization, Formal analysis, Methodology, Software, Visualization, Writing -- original draft, Writing -- review & editing.
**Wolfgang Ganglberger (WG):** Conceptualization, Data curation, Formal analysis, Methodology, Software, Validation, Visualization, Writing -- original draft, Writing -- review & editing.
**Alice D. Lam (ADL):** Investigation, Validation, Writing -- review & editing.
**Haoqi Sun (HS):** Methodology, Software, Writing -- review & editing.
**Tianyu Zhang (TZ):** Writing -- review & editing.
**Daniel M. Goldenholz (DMG):** Methodology, Writing -- review & editing.
**Fabio A. Nascimento (FAN):** Investigation, Resources, Validation, Writing -- review & editing.
**Doyle Yuan (DY):** Data curation, Investigation, Resources, Writing -- review & editing.
**Sándor Beniczky (SB):** Data curation, Investigation, Resources, Validation, Writing -- review & editing.
**Jennifer A. Kim (JAK):** Investigation, Project administration, Supervision, Validation, Writing -- review & editing.
**Aaron F. Struck (AFS):** Conceptualization, Investigation, Project administration, Supervision, Validation, Writing -- review & editing.
**Sahar F. Zafar (SFZ):** Conceptualization, Investigation, Project administration, Supervision, Validation, Writing -- review & editing.
**Robert J. Thomas (RJT):** Conceptualization, Funding acquisition, Investigation, Project administration, Resources, Supervision, Writing -- original draft, Writing -- review & editing.
**Mouhsin M. Shafi (MMS):** Conceptualization, Investigation, Resources, Writing -- review & editing.
**M. Brandon Westover (MBW):** Conceptualization, Data curation, Formal analysis, Funding acquisition, Investigation, Methodology, Project administration, Resources, Software, Supervision, Validation, Visualization, Writing -- original draft, Writing -- review & editing.
