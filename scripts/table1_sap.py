"""Table 1 — Cohort description, EXACTLY per SAP §10 (supersedes the old scripts/85 table, which emitted
only n/age/sex with a non-SAP age banding and recording-count stage coverage).

SAP §10 rows: recordings n; patients n (unique); age median[IQR] + decade bands 0-18/18-45/45-60/60-75/75+;
sex n(% female); recording length median[IQR] min + %>1h; usable segments median[IQR] + % artifact-flagged;
stage composition % W/N1/N2/N3/REM (SEGMENT-WEIGHTED); report-available/clean_pair n(%); clean_normal /
is_abnormal n(%); abnormal detail (focal n, generalized n; focal side L/R/bilat; gen topography
ant/post/unspec; band delta/theta/mixed).
Columns: Overall + by src (cohort=routine / expansion=overnight) + clean-normal / abnormal.

SAP §3.3: patient_id is the clustering unit; clean_pair guards report-broadcast contamination — label rows
are computed on clean_pair only, and the number of EEGs dropped by that filter is reported.
Reads ONLY new-run canonical tables: data/derived/recording_meta.parquet + recording_labels.parquet.
Run: PYTHONPATH=src python scripts/table1_sap.py
"""
from __future__ import annotations
import numpy as np, pandas as pd
from pathlib import Path

OUT = Path("results/table1.md")
AGE_BANDS = [0, 18, 45, 60, 75, 200]
AGE_LBL = ["0–18", "18–45", "45–60", "60–75", "75+"]
STAGES = ["W", "N1", "N2", "N3", "REM"]


def med_iqr(s, fmt="{:.1f}"):
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty: return "—"
    return f"{fmt.format(s.median())} [{fmt.format(s.quantile(.25))}–{fmt.format(s.quantile(.75))}]"


def pct(n, d):
    return "—" if not d else f"{n:,} ({100*n/d:.1f}%)"


def stage_composition(d):
    """SEGMENT-WEIGHTED % per stage (SAP §10) — weight each recording's stage_frac by its n_segments."""
    tot = {s: 0.0 for s in STAGES}; denom = 0.0
    for sf, n in zip(d.stage_frac, d.n_segments):
        if not isinstance(sf, dict) or n is None: continue
        try: n = float(n)
        except (TypeError, ValueError): continue
        if not np.isfinite(n) or n <= 0: continue
        for s in STAGES:
            v = sf.get(f"frac_{s}") or 0.0
            try: tot[s] += float(v) * n
            except (TypeError, ValueError): pass
        denom += n
    if denom == 0: return {s: "—" for s in STAGES}
    return {s: f"{100*tot[s]/denom:.1f}%" for s in STAGES}


def column(d, lab):
    """One stratum -> dict of SAP Table-1 rows."""
    n = len(d)
    lp = d[d.clean_pair == True]                       # SAP §3.3: label rows on clean_pair only
    abn = lp[lp.is_abnormal == True]
    c = {}
    c["Recordings, n"] = f"{n:,}"
    c["Patients, n (unique)"] = f"{d.patient_id.nunique():,}"
    c["Age, y — median [IQR]"] = med_iqr(d.age)
    for lo, hi, lbl in zip(AGE_BANDS[:-1], AGE_BANDS[1:], AGE_LBL):
        k = pd.to_numeric(d.age, errors="coerce").between(lo, hi, inclusive="left").sum()
        c[f"  Age band {lbl}"] = pct(int(k), n)
    fem = d.sex.astype(str).str[0].str.upper().eq("F").sum()
    c["Sex — female"] = pct(int(fem), n)
    mins = pd.to_numeric(d.recording_seconds, errors="coerce") / 60
    c["Recording length, min — median [IQR]"] = med_iqr(mins)
    c["  > 1 h (cEEG)"] = pct(int((mins > 60).sum()), n)
    c["Usable segments — median [IQR]"] = med_iqr(d.n_usable, "{:.0f}")
    c["  Artifact-flagged segments"] = (f"{100*pd.to_numeric(d.frac_artifact, errors='coerce').mean():.1f}%"
                                        if d.frac_artifact.notna().any() else "—")
    for s, v in stage_composition(d).items():
        c[f"  Stage {s} (segment-weighted)"] = v
    c["Report paired (clean_pair)"] = pct(int((d.clean_pair == True).sum()), n)
    c["clean_normal"] = pct(int((lp.clean_normal == True).sum()), len(lp))
    c["is_abnormal"] = pct(int((lp.is_abnormal == True).sum()), len(lp))
    c["  Focal slowing"] = pct(int((lp.has_focal_slow == True).sum()), len(lp))
    # SAP §3.5: generalized slowing must be split pathologic vs PHYSIOLOGIC (drowsiness/sleep slowing is
    # normal). gen_class is MISSING from the v6 manifest -> derived here (pathologic = gen_slow & abnormal).
    c["  Generalized slowing — pathologic"] = pct(int(((lp.has_gen_slow == True) & (lp.is_abnormal == True)).sum()), len(lp))
    c["  Generalized slowing — physiologic"] = pct(int(((lp.has_gen_slow == True) & (lp.is_abnormal != True)).sum()), len(lp))
    for side in ["left", "right", "bilateral"]:
        c[f"    Focal side {side}"] = pct(int((abn.focal_side == side).sum()), len(abn))
    for topo in ["anterior", "posterior", "unspec"]:
        c[f"    Gen topography {topo}"] = pct(int((abn.gen_topography == topo).sum()), len(abn))
    for band in ["delta", "theta", "mixed"]:
        k = int(((abn.focal_band == band) | (abn.gen_band == band)).sum())
        c[f"    Band {band}"] = pct(k, len(abn))
    return c


def main():
    m = pd.read_parquet("data/derived/recording_meta.parquet")
    l = pd.read_parquet("data/derived/recording_labels.parquet")
    d = m.merge(l.drop(columns=[c for c in ("panel_set",) if c in l.columns]), on="eeg_id", how="left")
    # SAP §3.2: the analysis set = recordings that passed inclusion. Panels (§3.6) are a separate aim.
    d = d[(d.included == True) & (d.panel != True)]
    dropped = int((d.clean_pair != True).sum())

    strata = [("Overall", d),
              ("Routine (cohort)", d[d.src == "cohort"]),
              ("Overnight (expansion)", d[d.src == "expansion"]),
              ("Clean-normal", d[(d.clean_pair == True) & (d.clean_normal == True)]),
              ("Abnormal", d[(d.clean_pair == True) & (d.is_abnormal == True)])]
    cols = [(lab, column(sub, lab)) for lab, sub in strata]
    rows = list(cols[0][1].keys())

    L = ["# Table 1 — Cohort characteristics (SAP §10)", "",
         f"Analysis set: recordings passing inclusion (SAP §3.2), panels excluded (§3.6 is a separate aim). "
         f"Label rows are computed on `clean_pair` only (SAP §3.3, PITFALL 1 — report-broadcast guard); "
         f"**{dropped:,} EEGs dropped by the clean_pair filter**. CIs elsewhere are patient-clustered on "
         f"`patient_id` (SAP §3.3).", "",
         "| Characteristic | " + " | ".join(lab for lab, _ in cols) + " |",
         "|---|" + "---|" * len(cols)]
    for r in rows:
        L.append(f"| {r} | " + " | ".join(c.get(r, "—") for _, c in cols) + " |")
    L += ["", f"_Generated from the new run's canonical tables (recording_meta + recording_labels); "
              f"n={len(d):,} included recordings, {d.patient_id.nunique():,} unique patients._"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT}  ({len(d):,} recordings, {d.patient_id.nunique():,} patients, clean_pair-dropped={dropped:,})")


if __name__ == "__main__":
    main()
