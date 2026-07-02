"""Turn the per-state quantitative scoring table into a clinician-style phrase.

Implements docs/feature_spec.md §8. Deterministic; generated *from* the quantitative
table so the number and the words never disagree.
"""
from __future__ import annotations
from dataclasses import dataclass

# Defaults mirror config/config.example.yaml (ACNS-style prevalence, provisional severity).
PREVALENCE_WORDS = [
    (0.90, "continuous"),
    (0.50, "abundant"),
    (0.10, "frequent"),
    (0.01, "occasional"),
    (0.00, "rare"),
]
SEVERITY_WORDS = [(4.5, "marked"), (3.0, "moderate"), (2.0, "mild"), (0.0, "within normal limits")]


def prevalence_word(fraction: float) -> str:
    for thr, word in PREVALENCE_WORDS:
        if fraction >= thr:
            return word
    return "rare"


def severity_word(patient_z: float) -> str:
    for thr, word in SEVERITY_WORDS:
        if patient_z >= thr:
            return word
    return "within normal limits"


def band_phrase(delta_burden: float, theta_burden: float, *, rhythmic: bool = False) -> str:
    """Delta vs theta vs mixed vs low-frequency, per feature_spec §8."""
    if rhythmic:
        return "rhythmic delta activity"
    d, t = delta_burden, theta_burden
    if d > 0 and t > 0 and min(d, t) / max(d, t) > 0.5:
        return "mixed theta/delta slowing"
    if d >= t:
        return "delta slowing"
    return "theta slowing"


@dataclass
class StateFinding:
    state: str                 # e.g. "Awake"
    prevalence: float          # fraction of usable state time abnormal
    patient_z: float           # patient-level z (severity)
    location: str              # e.g. "right temporal", "generalized"
    band: str                  # from band_phrase()
    burden: float
    median_abn_z: float
    max_run_min: float
    asymmetry_z: float | None = None


def render(f: StateFinding) -> str:
    """Return: '[State]: [prev] [sev] [location] [band] slowing (quantitative parenthetical).'"""
    if f.patient_z < 2.0:
        return f"{f.state}: no significant slowing."
    head = (f"{f.state}: {prevalence_word(f.prevalence)} {severity_word(f.patient_z)} "
            f"{f.location} {f.band}")
    parts = [
        f"present in {f.prevalence*100:.0f}% of artifact-free {f.state.lower()} segments",
        f"{f.location} burden {f.patient_z:.1f} SD above age/state norms",
        f"median abnormal z {f.median_abn_z:.1f}",
        f"maximum continuous run {f.max_run_min:.1f} minutes",
    ]
    if f.asymmetry_z is not None and abs(f.asymmetry_z) >= 2.0:
        parts.insert(2, f"left–right asymmetry {f.asymmetry_z:.1f} SD above normal")
    return head + ", " + "; ".join(parts) + "."


if __name__ == "__main__":  # tiny demo
    print(render(StateFinding(
        state="Awake", prevalence=0.34, patient_z=4.1, location="right temporal",
        band="delta slowing", burden=0.82, median_abn_z=3.4, max_run_min=5.0, asymmetry_z=3.3)))
