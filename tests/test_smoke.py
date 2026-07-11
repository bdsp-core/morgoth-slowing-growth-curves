"""Smoke tests for the deterministic, data-free pieces already implemented.
(The legacy report.phrase generator — which emitted FORBIDDEN severity/frequency words — is retired;
the claims-gated generator is scripts/110. Its tests were removed.)"""
import numpy as np
from morgoth_slowing.scoring import burden, patient_z


def test_burden_and_prevalence():
    z = np.array([0, 1, 3, 4, 0, 5.0])
    assert burden.prevalence(z, tau=2.0) == 3 / 6
    assert burden.burden(z, tau=2.0) > 0
    assert burden.severity(z, tau=2.0) == 4.0


def test_patient_z_empirical_monotonic():
    null = np.random.RandomState(0).normal(size=500)
    lo = patient_z.patient_z_empirical(0.0, null)
    hi = patient_z.patient_z_empirical(3.0, null)
    assert hi > lo


def test_recording_features_shapes():
    import numpy as np
    from morgoth_slowing.features import recording as rec
    rng = np.random.RandomState(0)
    res = np.empty((5, 4), dtype=object)
    for i in range(5):
        feat = np.abs(rng.rand(18, 31)) + 0.1
        feat[:, 5] = feat[:, :5].sum(axis=1)  # total = sum of 5 bands (so rel powers <= 1)
        res[i] = [5, i * 3000 + 1, (i + 1) * 3000, feat]
    rows, segs, asym = rec.recording_features(res)
    assert len(rows) == len(rec.REGIONS)
    assert 0 <= [r for r in rows if r["region"] == "whole_head"][0]["rel_delta"] <= 1
    assert any(k.startswith("asym_temporal") for k in asym)


def test_topography_classify():
    from morgoth_slowing.scoring import topography as topo
    assert topo.classify({"L_temporal": 0.1, "R_temporal": 0.1}, 0.0) == "none"
    assert topo.classify({"L_temporal": 4.0, "R_temporal": 0.2}, 3.5) == "focal"
    assert topo.classify({"L_temporal": 3.0, "R_temporal": 3.0, "L_parasagittal": 3.0}, 0.0) == "generalized"
