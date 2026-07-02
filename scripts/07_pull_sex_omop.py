"""Pull sex for the Growth_curves cohort from OMOP -> data/derived/sex.parquet.

Working method (verified 2026-07-02):
  - Tunnel: myelin bastion is 35.163.225.34 (NOT the prod web box 35.92.7.76). Forward local 5433:
      ssh -i .../myelin-bastion-userkeys/myelin-bastion-<you>.pem -N \
          -L 5433:bdsp-omop-aurora-instance-1.cz06iykeon5i.us-west-2.rds.amazonaws.com:5432 \
          <you>@35.163.225.34
  - DB: user myelin_<you> (myelin_readers, read-only; password from the Box creds file). Set env
      OMOP_USER / OMOP_PASSWORD before running.
  - ID map: hashid 'S000<site>' + OMOP person_id, so person_id = int(hashid without 'S000<site>').
    Sex from omop_prod.person.gender_concept_id (8507=M, 8532=F). No work_meem needed.

Then: python scripts/07_pull_sex_omop.py
"""
from __future__ import annotations
import os
from pathlib import Path
import pandas as pd

from morgoth_slowing.io import segments, omop


def main():
    meta = segments.load_metadata({"data": {"local": {"raw": "data/raw"}}}, with_age=False)
    meta["omop_person_id"] = meta.bdsp_id.map(omop.hashid_to_person_id)
    ids = sorted(meta.omop_person_id.unique().tolist())
    print(f"{len(ids)} unique person_ids to resolve")

    conn = omop.connect(user=os.environ["OMOP_USER"], password=os.environ["OMOP_PASSWORD"])
    sex = omop.get_sex(conn, ids).rename(columns={"person_id": "omop_person_id"})
    conn.close()

    out = (meta[["bdsp_id", "omop_person_id"]].drop_duplicates()
           .merge(sex, on="omop_person_id", how="left"))
    print("resolved:", int(out.sex.notna().sum()), "/", len(out))
    print(out.sex.value_counts(dropna=False).to_string())

    dst = Path("data/derived"); dst.mkdir(parents=True, exist_ok=True)
    out.to_parquet(dst / "sex.parquet")
    print("wrote", dst / "sex.parquet",
          "-> now: python scripts/build_cohort_metadata.py && python scripts/make_table1.py")


if __name__ == "__main__":
    main()
