# Data sources & access

**Moved.** The canonical, up-to-date data-source and provenance description is
[`DATA_SOURCE.md`](../DATA_SOURCE.md) at the repo root (BDSP release standard):

- **Source EEGs** are referenced from the published BDSP EEG dataset (`s3://bdsp-opendata-repository/EEG/bids/`),
  not re-hosted.
- **Derived data** (the reproduce cache) lives in this project's credentialed prefix,
  `s3://bdsp-opendata-credentialed/morgoth-slowing/`.
- Access is credentialed + DUA-governed via the project's bdsp.io page.

See [`DATA_SOURCE.md`](../DATA_SOURCE.md) for the full two-tier layout, the raw→derived pipeline, and the
de-identification status; see [`REPRODUCE.md`](../REPRODUCE.md) for the figure/table → script → input map.
