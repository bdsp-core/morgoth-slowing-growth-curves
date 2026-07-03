# Agreement with clinical reports
## Part A — focal vs generalized (report-derived label)

**Morgoth (p_focal vs p_gen)** — accuracy 0.831, balanced 0.716

```
morgoth_call  focal  generalized
true                            
focal           939         1128
generalized     124         5217
```

## Part B — band (delta/theta/mixed) + location (side/region)
Needs the free-text EEG report. `note`/`note_nlp` are permission-blocked for the read-only OMOP role; provide a reports CSV (bdsp_id, report_text) or run the prod-path pull (human-run). Parser + comparison implemented (`parse_report`, `part_b`).
