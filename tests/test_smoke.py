"""Smoke tests for the deterministic, data-free pieces already implemented."""
import numpy as np
from morgoth_slowing.scoring import burden, patient_z
from morgoth_slowing.report import phrase


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


def test_phrase_render():
    f = phrase.StateFinding(state="Awake", prevalence=0.34, patient_z=4.1,
                            location="right temporal", band="delta slowing", burden=0.8,
                            median_abn_z=3.4, max_run_min=5.0, asymmetry_z=3.3)
    out = phrase.render(f)
    assert "frequent" in out and "moderate" in out and "4.1 SD" in out


def test_phrase_normal():
    f = phrase.StateFinding("Awake", 0.0, 0.5, "generalized", "delta slowing", 0, 0, 0)
    assert "no significant slowing" in phrase.render(f)
