"""Look up age-at-EEG (and sex) from the BDSP OMOP database.

Age is the x-axis of every growth curve, so this is required before any subject is used.
BDSP id == OMOP `person_id`. See docs/omop-query-instructions.txt for connection details
(SSH tunnel to localhost:5433, db `bdsp_omop`, read-only role, schema `omop_prod`/`work_meem`).

Age-at-EEG strategy (dates are de-identified but per-patient *consistent*, so within-patient
date arithmetic is valid):
  1. EEG procedure date  <- omop_prod.procedure_occurrence (concept 4181917 EEG / 4189015 PSG),
     preferably via work_meem.bdsp_recording_detail.start_time (one row per EDF, has s3_path).
  2. Birth  <- omop_prod.person (birth_datetime, or year/month/day_of_birth).
  3. age_at_eeg = (eeg_date - birth_date) / 365.25 ; sex <- person.gender_concept_id.
Match the EEG recording to the exact segment source via s3_path in bdsp_recording_detail.
"""
from __future__ import annotations
import pandas as pd

# OMOP standard concept ids (from docs/omop-query-instructions.txt)
EEG_CONCEPT_ID = 4181917
PSG_CONCEPT_ID = 4189015

AGE_AT_EEG_SQL = """
SET statement_timeout = '300s';
SELECT r.person_id,
       r.procedure_occurrence_id,
       r.s3_path,
       r.start_time                                   AS eeg_time,
       p.birth_datetime,
       EXTRACT(EPOCH FROM (r.start_time - p.birth_datetime)) / (365.25*24*3600) AS age_at_eeg,
       p.gender_concept_id
FROM work_meem.bdsp_recording_detail r
JOIN omop_prod.person p USING (person_id)
WHERE r.person_id = ANY(%(person_ids)s)
  AND r.modality = 'EEG';
"""


def connect(host="localhost", port=5433, dbname="bdsp_omop", user=None, password=None):
    """psycopg v3 connection through the SSH tunnel. Credentials come from env/args, never
    committed (config.yaml is gitignored). Requires the tunnel to be up."""
    import psycopg
    return psycopg.connect(host=host, port=port, dbname=dbname, user=user, password=password)


def age_at_eeg(conn, person_ids: "list[int]") -> pd.DataFrame:
    """Return one row per EEG recording: person_id, s3_path, eeg_time, age_at_eeg, sex.

    Filters by person_id (indexed) — never scans unfiltered. Falls back to
    year/month/day_of_birth if birth_datetime is null.
    """
    df = pd.read_sql(AGE_AT_EEG_SQL, conn, params={"person_ids": list(person_ids)})
    df["sex"] = df["gender_concept_id"].map({8532: "F", 8507: "M"})
    return df
