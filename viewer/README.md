# EEG description review viewer (validation V3)

A self-contained, offline app for neurophysiologists to validate our auto-generated
slowing descriptions against the raw EEG. See `docs/validation_plan.md` (V3).

For each case the rater reads the EEG in a standard **double-banana longitudinal-bipolar
montage** (pageable, adjustable sensitivity / timebase, HP/LP/notch filters) and scores our
generated sentence **Accurate** (one click) or **Not accurate**; if not accurate they edit
the sentence and save the correction. Every response is appended server-side to a JSONL.

Single-file Flask + vanilla-JS canvas. No build step, no npm, no CDN — works fully offline.

## Run (one command each)

```bash
# 1. build the 100-case review set + private case_id->bdsp_id crosswalk (already PHI-safe)
python scripts/98_build_review_set.py --select

# 2. pre-export EEG clips from S3 (resumable; ~90 s/case; needs rclone remote `s3:`).
#    Each case -> viewer/data/signals/<case_id>.npz (18 bipolar ch, 200 Hz, int16 uV).
python scripts/98_build_review_set.py --fetch --limit 100

# 3. launch the viewer (opens on http://127.0.0.1:5000)
python viewer/app.py
```

Options: `python viewer/app.py --port 5050 --rater rater_a`. The app only shows cases whose
`.npz` clip has actually been exported, so you can review a partial set while more download.

## Controls

| action | keys |
|---|---|
| Accurate (saves, advances) | `1` |
| Not accurate (opens edit box) | `2` |
| Save correction | `⌘/Ctrl+Enter` in the box |
| Page within the ~4-min clip | `←` / `→` (or the scrollbar) |
| Previous / next case | `Shift+←` / `Shift+→` |
| Sensitivity up / down | `↑` / `↓` |

Timebase (5–30 s/page, default 10), sensitivity (µV/mm, default 7), and HP / LP / notch
filters are dropdowns in the toolbar. Filtering is applied server-side (scipy) on the raw
clip and cached; the red L-shaped marker is a calibration bar (`N µV` vertical, `1 s`
horizontal). Resuming is automatic: on load the app jumps to the first un-scored case, and a
prior verdict/edit for a case is restored when you return to it. Progress shows `n / 100`.

## What it records

`viewer/data/responses.jsonl` — one line per submit (gitignored):

```json
{"case_id":"case_017","rater_id":"rater_1","verdict":"not_accurate",
 "shown_sentence":"Frequent mild left temporal ...","edited_text":"Frequent mild left temporal delta slowing ...",
 "source":"generated","ts_iso":"2026-07-09T12:34:56-0400"}
```

`verdict` is `accurate` or `not_accurate`; `edited_text` is the corrected wording (empty when
accurate). Re-scoring a case appends a new line; the analysis / resume logic uses the latest
per `(rater_id, case_id)`.

## Optional blinded head-to-head mode

`python viewer/app.py --blinded` randomizes, per (rater, case), whether the shown sentence is
**ours** or the **clinical-report** sentence, keeping the source hidden from the rater (the
source is still recorded for analysis). This requires a `report_sentence` field per case in
`data/derived/review_set.jsonl`; the plain mode MBW asked for (our sentence only) needs
nothing extra and is the default.

## PHI / safety

- Cases are opaque `case_001…case_100`. Nothing under `viewer/` or `data/derived/review_set.jsonl`
  carries a patient id, a date, raw report text, or an EDF header.
- The only `case_id -> bdsp_id` link is `case_crosswalk.jsonl`, written to the **scratchpad**
  (outside the repo) by `scripts/98`, never committed.
- Clips are stored as bare int16 µV arrays (`.npz`); no EDF headers ship. `viewer/data/` is
  gitignored.
- At review time the app touches **no S3** and reads no EDF — only the local `.npz` clips.

## Files

| path | what |
|---|---|
| `viewer/app.py` | Flask app: serves cases, filtered signal, saves responses |
| `viewer/static/index.html` / `style.css` / `viewer.js` | canvas EEG renderer + scoring UI |
| `scripts/98_build_review_set.py` | builds the review set and pre-exports the clips |
| `viewer/data/signals/*.npz` | per-case EEG clips (gitignored) |
| `viewer/data/responses.jsonl` | rater responses (gitignored) |

The canvas renderer and the montage/clip-extraction were adapted from the review viewers in
`bdsp-core/teleEEG-wrangling` (`pipeline/viewers/build_viewers.py`, `render_eeg.py`).
