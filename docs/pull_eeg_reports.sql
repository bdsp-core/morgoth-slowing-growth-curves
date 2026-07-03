-- Pull the free-text EEG reports for the slowing cohort, to evaluate our band/location statements.
-- Run with a role that can read omop_prod.note (e.g. inside the prod container via the AURORA creds),
-- NOT the myelin read-only role (note/note_nlp are blocked there).
-- Person-id list is in data/derived/cohort_person_ids.txt (paste into the ARRAY, or \copy a temp table).
\set statement_timeout '600s'
COPY (
  SELECT n.person_id,
         n.note_date,
         n.note_title,
         left(n.note_text, 6000) AS report_text
  FROM omop_prod.note n
  WHERE n.person_id = ANY(ARRAY[ /* paste cohort person_ids here */ ]::bigint[])
    AND ( n.note_title ILIKE '%EEG%'
       OR n.note_title ILIKE '%electroencephalogram%'
       OR n.note_title ILIKE '%EMU%' )
) TO STDOUT WITH CSV HEADER;
