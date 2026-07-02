"""Pull sex for the Growth_curves cohort from OMOP, save data/derived/sex.parquet.

Prereqs (see docs/omop-query-instructions.txt):
  1. Open the SSH tunnel to the myelin bastion:
       ssh -i .../myelin-bastion-userkeys/myelin-bastion-<you>.pem -N \
           -L 5433:bdsp-omop-aurora-instance-1.cz06iykeon5i.us-west-2.rds.amazonaws.com:5432 \
           <you>@<MYELIN_BASTION_HOST>
     NOTE (2026-07-02): tunnel to 35.92.7.76 currently fails 'Permission denied (publickey)' for the
     hanwu key as hanwu/ec2-user/ubuntu — verify the bastion IP, login username, and that the key is
     provisioned on that host before running this.
  2. export OMOP_USER=myelin_<you>  OMOP_PASSWORD=...   (read-only myelin_readers role)
Then: python scripts/07_pull_sex_omop.py
"""
from __future__ import annotations
import os
from pathlib import Path
import pandas as pd

from morgoth_slowing.io import segments, omop


def main():
    cfg = {"data": {"local": {"raw": "data/raw"}}}
    meta = segments.load_metadata(cfg, with_age=False)
    sub_ids = sorted(meta.person_id.unique())
    print(f"{len(sub_ids)} unique sub-ids to resolve")

    conn = omop.connect(user=os.environ["OMOP_USER"], password=os.environ["OMOP_PASSWORD"])
    sex = omop.get_sex(conn, sub_ids)
    print("resolved sex for", sex.person_id.nunique(), "person_ids")
    print(sex.sex.value_counts(dropna=False).to_string())

    out = Path("data/derived"); out.mkdir(parents=True, exist_ok=True)
    sex.to_parquet(out / "sex.parquet")
    print("wrote", out / "sex.parquet", "-> re-run scripts/make_table1.py to add the Sex row")


if __name__ == "__main__":
    main()
