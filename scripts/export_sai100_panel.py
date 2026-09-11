"""Export the SAI-100 panel to ONE de-identified, publishable table.

Why this exists. Figure 3 -- the paper's second external validation, including the negative result -- was
the only display item that could not be rebuilt from git + S3: it read the SCORE-AI validation study's Excel
workbooks straight off one developer's Box mount, so it reproduced on exactly one machine. The EEG signal is
DUA-governed and stays where it is; the small derived table of expert votes and comparator predictions is
not, and publishing it closes the gap.

What is exported, and what is deliberately not:

  KEPT   study pseudonym (ID001..ID100), the anonymous per-rater binary calls per axis (a 14-rater pool, 11
         calls per recording), SCORE-AI's and the Morgoth gate's scores and classes, the derived workbook's
         `majority` column (see below), and
         age + sex, which the pipeline needs because every score is age-matched.
  DROPPED  everything else in the workbooks. There are no rater names in the source to begin with --
         `human_expert_id` is an integer 0-14 -- and this script ASSERTS that, rather than assuming it.
  BINNED   any age above 89 is set to 90 (HIPAA Safe Harbor), matching the rule the main cohort already
         uses. One SAI-100 recording is affected (95.0 -> 90).

On the focal sheet of the DERIVED FocalSlowingOutput workbook, `majority` carries the focal interictal
EPILEPTIFORM consensus (he_con_intictepifoc), not focal slowing. The source workbook,
validation_study_excel_export.xlsx, is internally consistent: its he_con_nonepifoc matches the individual
slowing votes on 100/100. The column is exported only so that check stays reproducible; ground truth is
recomputed from the individual votes by the consumer.

Run: SANDOR_DIR=... PYTHONPATH=src python3 scripts/export_sai100_panel.py
"""
from __future__ import annotations
import os
import re
import sys
from pathlib import Path
import pandas as pd

OUT = Path("data/derived/sai100_panel.parquet")
AXES = {"focal": "FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx",
        "generalized": "GenSlowingOutput_Morgoth_ScoreAI_experts.xlsx"}
NAMEY = re.compile(r"name|first|last|surname|initial|email|mrn|dob|birth|address|phone|site|hospital|centre|center",
                   re.I)


def _sandor_dir() -> Path:
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("m_sandor", "scripts/sandor100_external_validation.py")
    # the resolver lives with the consumer; import just that function without running the module
    src = Path("scripts/sandor100_external_validation.py").read_text()
    ns: dict = {}
    body = src[src.index("def _resolve_sandor_dir"):src.index("SB_DIR = Path(")]
    exec(compile(body, "sandor_resolver", "exec"), ns)
    return Path(os.environ.get("SANDOR_DIR") or ns["_resolve_sandor_dir"]())


def main() -> int:
    sb = _sandor_dir()
    mr = sb / "Morgoth_results"
    print(f"reading SAI-100 source from {sb}")

    frames = []
    for axis, fn in AXES.items():
        d = pd.read_excel(mr / fn)
        experts = [c for c in d.columns if c.startswith("expert_")]
        keep = ["file_name", "S_pred", "S_pred_class", "M_pred", "M_pred_class", "majority"] + experts
        extra = [c for c in d.columns if c not in keep]
        if extra:
            print(f"  {axis}: dropping {len(extra)} unused column(s): {extra}")
        d = d[keep].copy()
        d.insert(1, "axis", axis)
        frames.append(d)
        print(f"  {axis}: {len(d)} recordings x {len(experts)} raters "
              f"({int(d[experts].notna().sum(axis=1).min())} calls per recording)")

    panel = pd.concat(frames, ignore_index=True)

    demo = pd.read_excel(sb / "validation_study_excel_export.xlsx", sheet_name="Demographics")
    demo = demo.rename(columns={demo.columns[0]: "file_name"})[["file_name", "gender", "age_years"]].copy()
    n_binned = int((demo.age_years > 89).sum())
    demo["age_years"] = demo.age_years.clip(upper=90.0).round(2)
    print(f"  demographics: {len(demo)} recordings; {n_binned} age(s) above 89 binned to 90")
    panel = panel.merge(demo, on="file_name", how="left")

    # --- the de-identification assertions. Fail loudly rather than publish something unchecked. ---
    SAFE = {"file_name"}          # the study pseudonym column; its VALUES are checked below
    bad_cols = [c for c in panel.columns if c not in SAFE and NAMEY.search(c)]
    assert not bad_cols, f"column name suggests an identifier: {bad_cols}"
    for c in panel.columns:
        if panel[c].dtype == object:
            vals = panel[c].dropna().astype(str)
            assert c in ("file_name", "axis", "gender"), f"unexpected free-text column: {c}"
            if c == "file_name":
                assert vals.str.fullmatch(r"ID\d{3}").all(), "file_name is not a bare study pseudonym"
            if c == "gender":
                assert set(vals) <= {"male", "female"}, f"unexpected gender values: {set(vals)}"
    assert panel.age_years.max() <= 90.0, "an age above 90 survived binning"
    print("  de-identification checks passed: pseudonymous IDs, anonymous raters, ages capped at 90")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUT, index=False)
    print(f"wrote {OUT}  ({len(panel)} rows = {panel.file_name.nunique()} recordings x {panel.axis.nunique()} axes)")
    print("\nPublish with:\n"
          f"  aws s3 cp {OUT} s3://bdsp-opendata-credentialed/morgoth-slowing/derived/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
