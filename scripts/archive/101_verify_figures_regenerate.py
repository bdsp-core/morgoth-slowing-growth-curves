"""Verify every MAIN figure regenerates from data in the repo, with no scratchpad and no network.

Run with the scratchpad renamed away to make the guarantee real:
    PYTHONPATH=src python scripts/101_verify_figures_regenerate.py --check-only
    PYTHONPATH=src python scripts/101_verify_figures_regenerate.py            # regenerate + verify
"""
from __future__ import annotations
import subprocess, sys, os
from pathlib import Path

FIGS = [
    # Every producer below reads ONLY v6 canonical tables + genuine inputs. The previous list pointed at
    # scripts whose inputs (segment_features, report_ordinals, occasion_features, report_pairing) were
    # quarantined with the legacy tables, so "Figure 4/6/S1" could not in fact be regenerated — the harness
    # reported them as fine because it never got as far as running them.
    ("Figure 1", "figures/growth_v2/keystone_growth_grid.png", "scripts/76_keystone_growth_grid.py",
     ["data/derived/channel_stage_features.parquet", "data/derived/labels_unified.parquet"]),
    ("Figure 2", "figures/growth_v2/vigilance_matched_detection.png", "scripts/84_vigilance_matched_detection.py",
     ["data/derived/channel_stage_features.parquet", "data/derived/labels_unified.parquet"]),
    ("Figure 3", "figures/growth_v2/dose_response.png", "scripts/85_table1_and_dose_response.py",
     ["data/derived/channel_stage_features.parquet", "data/derived/labels_unified.parquet"]),
    ("Figure 4", "figures/growth_v2/two_stage_gate_and_quantify.png", "scripts/105_two_stage_figure.py",
     ["data/derived/occasion_features.parquet", "data/derived/occasion_expert_votes.parquet",
      "data/derived/occasion_morgoth_preds.parquet", "data/derived/sparse_score_coefs.json"]),
    ("Figure 5", None, None, []),   # artist schematic
    ("Figure 6", "figures/growth_v2/sparse_score_external.png", "scripts/104_sparse_score_external.py",
     ["data/derived/occasion_features.parquet", "data/derived/occasion_expert_votes.parquet",
      "data/derived/sparse_score_coefs.json"]),
    ("Figure S1", "figures/growth_v2/severity_recalibrated.png", "scripts/109_severity_null_v6.py",
     ["data/derived/channel_stage_features.parquet", "data/derived/recording_labels_sap.parquet"]),
    # supplementary appendix (F1-F4b), all from one v6 producer
    ("Figure F1-F4b", "results/figs/age_auroc.png", "scripts/106_appendix_figures_v6.py",
     ["data/derived/channel_stage_features.parquet", "data/derived/recording_labels_sap.parquet",
      "data/derived/_vp_per_recording.parquet", "metadata/ages_v6.parquet"]),
]


def main():
    check_only = "--check-only" in sys.argv
    env = {**os.environ, "PYTHONPATH": "src", "KMP_DUPLICATE_LIB_OK": "TRUE"}
    bad = 0
    for name, fig, script, inputs in FIGS:
        if script is None:
            print(f"{name:10s} SKIP  (artist schematic; brief at docs/figure5_pipeline_schematic_brief.md)")
            continue
        missing = [i for i in inputs if not Path(i).exists()]
        if missing:
            print(f"{name:10s} INPUTS MISSING: {missing}")
            bad += 1
            continue
        if check_only:
            ok = Path(fig).exists()
            print(f"{name:10s} inputs OK ({len(inputs)})  figure {'present' if ok else 'MISSING'}  <- {script}")
            bad += 0 if ok else 1
            continue
        before = Path(fig).stat().st_mtime if Path(fig).exists() else 0
        r = subprocess.run([sys.executable, script], env=env, capture_output=True, text=True)
        after = Path(fig).stat().st_mtime if Path(fig).exists() else 0
        if r.returncode != 0 or after <= before:
            tail = (r.stderr or "").strip().splitlines()[-1:] or ["(no stderr)"]
            print(f"{name:10s} FAILED rc={r.returncode}  {tail[0][:90]}")
            bad += 1
        else:
            print(f"{name:10s} regenerated OK  ({Path(fig).stat().st_size:,} B)  <- {script}")
    print(f"\n{'ALL MAIN FIGURES REGENERABLE FROM THE REPO' if bad == 0 else f'{bad} FIGURE(S) NOT REGENERABLE'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
