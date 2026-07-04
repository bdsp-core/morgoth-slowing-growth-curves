"""Combine the per-recording worker outputs into analysis-ready artifacts.

Reads data/derived/expansion/{features,provenance}/ and writes:
  data/derived/expansion_pilot_features.parquet   (concatenated features -> what the dashboard +
                                                    refit read; same schema as the old pilot output)
  results/expansion_provenance.csv                (one row per recording: source EDF, commit, counts)

Idempotent; safe to run anytime while the worker is going. Run: python scripts/combine_expansion.py
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

EXP = Path("data/derived/expansion")
OUT_FEAT = Path("data/derived/expansion_pilot_features.parquet")
OUT_PROV = Path("results/expansion_provenance.csv")


def main():
    feats = sorted((EXP / "features").glob("*.parquet"))
    if feats:
        df = pd.concat([pd.read_parquet(f) for f in feats], ignore_index=True)
        OUT_FEAT.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(OUT_FEAT)
        print(f"features: {len(feats)} recordings, {len(df)} rows -> {OUT_FEAT}")
    else:
        print("no per-recording feature parquets yet")
    provs = sorted((EXP / "provenance").glob("*.json"))
    if provs:
        rows = [json.loads(p.read_text()) for p in provs]
        OUT_PROV.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(OUT_PROV, index=False)
        print(f"provenance: {len(rows)} recordings -> {OUT_PROV}")
    gates = sorted((EXP / "gate").glob("*.json"))
    if gates:
        g = pd.DataFrame([json.loads(p.read_text()) for p in gates])
        out = Path("results/expansion_gate_probs.csv")
        g.to_csv(out, index=False)
        print(f"gate probs: {len(g)} recordings -> {out}")


if __name__ == "__main__":
    main()
