# Severity axis sweep — is the null our score, or the adjective?

168 combinations: 7 features x 4 statistics x {raw, z} x {generalized, focal, all}, cleanly-paired recordings, W/N1 only.

**Largest |rho| anywhere in the sweep: 0.179**

## Best 12 combinations

| scale | feature | stat | stratum | rho | p | n |
|---|---|---|---|---|---|---|
| z | rel_theta | p90 | generalized | -0.179 | 6.8e-04 | 358 |
| z | rel_theta | p99 | generalized | -0.168 | 1.4e-03 | 358 |
| raw | TAR | mean | generalized | 0.159 | 2.6e-03 | 358 |
| z | rel_theta | mean | generalized | -0.157 | 3.0e-03 | 358 |
| raw | TAR | mean | all | 0.153 | 2.5e-05 | 753 |
| raw | rel_theta | p99 | generalized | -0.141 | 7.6e-03 | 358 |
| z | TAR | mean | all | 0.136 | 1.8e-04 | 753 |
| z | DAR | p90 | focal | 0.130 | 1.0e-02 | 389 |
| z | rel_theta | median | generalized | -0.129 | 1.5e-02 | 358 |
| raw | TAR | median | all | 0.129 | 3.9e-04 | 753 |
| z | TAR | p99 | focal | 0.129 | 1.1e-02 | 389 |
| raw | TAR | median | generalized | 0.127 | 1.6e-02 | 358 |

## RAW vs Z (the decisive contrast)

| stratum | best |rho| RAW | best |rho| Z |
|---|---|---|
| generalized | 0.159 | 0.179 |
| focal | 0.119 | 0.130 |
| all | 0.153 | 0.136 |
