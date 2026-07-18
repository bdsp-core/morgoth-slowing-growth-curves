"""Assemble the submission figure set into figures/manuscript/ with manuscript figure-number names.

The figures are PRODUCED in their own dirs (figures/growth_v2, figures/story, figures/stage_curves,
results/figs); this gathers the final ones into one clean, submission-ready folder named by figure number,
matching the Figures section of docs/manuscript_draft.md, and writes a MANIFEST mapping each to its source +
producing script. Re-run any time (it's part of the `results` reproduce tier). Missing sources are reported,
not fatal.

Run: PYTHONPATH=src python3 scripts/assemble_manuscript_figures.py
"""
from __future__ import annotations
import shutil
from pathlib import Path

OUT = Path("figures/manuscript")
# submission figure name -> (source path, producing script). Names track docs/manuscript_draft.md §Figures
# EXACTLY (6 main figures + supplementary). Keep this list the single source of truth; the output folder is
# wiped and rebuilt on every run, so a rename here never leaves an orphan behind.
FIGS = [
    # ---- MAIN (1 table + 6 figures) ----
    ("Figure1a_growth_curves.png",         "figures/growth_v2/keystone_growth_grid.png",        "76_keystone_growth_grid.py"),
    ("Figure1b_topoplot_rel_delta.png",    "figures/growth_v2/topo_rel_delta_by_age_stage.png", "77_topoplots_by_age.py"),
    ("Figure1b_topoplot_TAR.png",          "figures/growth_v2/topo_TAR_by_age_stage.png",       "77_topoplots_by_age.py"),
    ("Figure2a_detection_generalized.png", "figures/story/s0d_single_occasion_generalized.png", "54_single_model_train_eval.py"),
    ("Figure2b_detection_focal.png",       "figures/story/s0e_occasion_focal.png",              "55_recording_model.py"),
    ("Figure3_sandor_external.png",        "figures/story/sandor100_slowing.png",               "sandor100_external_validation.py"),
    ("Figure4_example_eeg_reports.png",    "figures/story/s4_examples_eeg_panel.png",           "63_example_eeg_traces.py"),
    ("Figure5a_laterality_region.png",     "figures/story/s4_d2.png",                           "57_description_panels.py"),
    ("Figure5b_by_sleep_stage.png",        "figures/story/s4_d5.png",                           "57_description_panels.py"),
    ("Figure6_sleep_underreporting.png",   "figures/growth_v2/v4a_wake_sleep.png",              "95_v4a_wake_sleep.py"),
    # ---- SUPPLEMENTARY FIGURES ----
    ("FigureS1_architecture.png",          "figures/story/architecture.png",                    "architecture_diagram.py"),
    ("FigureS2_deviation_field.png",       "figures/story/s2_segment_deviation.png",            "44_segment_deviation_summary.py"),
    ("FigureS3a_curvebank_rel_delta.png",  "figures/stage_curves/rel_delta__whole_head.png",    "111_curve_bank_v6.py"),
    ("FigureS3b_curvebank_TAR.png",        "figures/stage_curves/TAR__whole_head.png",          "111_curve_bank_v6.py"),
    ("FigureS3c_curvebank_DAR.png",        "figures/stage_curves/DAR__whole_head.png",          "111_curve_bank_v6.py"),
    ("FigureS4a_D1_type_amount.png",       "figures/story/s4_d1.png",                           "57_description_panels.py"),
    ("FigureS4b_D3_anteroposterior.png",   "figures/story/s4_d3.png",                           "57_description_panels.py"),
    ("FigureS4c_D4_persistence.png",       "figures/story/s4_d4.png",                           "57_description_panels.py"),
    ("FigureS4d_D6_generated_words.png",   "figures/story/s4_d6.png",                           "58_description_words.py"),
    ("FigureS5_localized_focal.png",       "figures/story/s0_occasion_ours_v4_focal.png",       "49_occasion_allstage_localized.py"),
    ("FigureS6_severity_null.png",         "figures/growth_v2/severity_recalibrated.png",       "109_severity_null_v6.py"),
    ("FigureS7_vanputten_benchmark.png",   "results/figs/vanputten_comparison.png",             "recompute_vanputten_fullcov.py"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):                        # wipe first so a rename never leaves an orphan
        old.unlink()
    lines = ["# Manuscript figures — assembled set", "",
             "Gathered by `scripts/assemble_manuscript_figures.py` from the producing directories; each is a "
             "copy of the current canonical figure. Regenerate the sources via the `results` reproduce tier, "
             "then re-run this.", "", "| manuscript figure | source | producing script |", "|---|---|---|"]
    have = miss = 0
    for name, src, script in FIGS:
        s = Path(src)
        if s.exists():
            shutil.copy2(s, OUT / name); have += 1
            lines.append(f"| `{name}` | `{src}` | `scripts/{script}` |")
        else:
            miss += 1
            lines.append(f"| `{name}` | *(missing: {src})* | `scripts/{script}` |")
    (OUT / "MANIFEST.md").write_text("\n".join(lines) + "\n")
    print(f"assembled {have} figures into {OUT}/ ({miss} sources missing) + MANIFEST.md")
    if miss:
        print("  missing sources (run their producing script / reproduce tier):")
        for name, src, _ in FIGS:
            if not Path(src).exists():
                print(f"    {name} <- {src}")


if __name__ == "__main__":
    main()
