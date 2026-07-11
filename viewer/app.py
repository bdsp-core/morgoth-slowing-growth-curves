#!/usr/bin/env python
"""
EEG review viewer for V3 validation (docs/validation_plan.md).

A neurophysiologist reads the raw EEG (double-banana longitudinal-bipolar montage,
pageable, adjustable sensitivity / timebase, HP/LP/notch toggles) and scores our
auto-generated slowing description as Accurate / Not accurate; if not accurate they
edit the sentence.  Every response is appended to a JSONL we analyze afterwards.

Design goals (per MBW): single-file Flask + vanilla-JS canvas, no build step, no CDN,
works fully offline.  Signals are read from pre-exported PHI-free .npz clips
(viewer/data/signals/), so no S3 access and no EDF headers at review time.

Run:
    python viewer/app.py                       # http://127.0.0.1:5000
    python viewer/app.py --port 5050 --rater rater_a
    python viewer/app.py --blinded             # randomize ours-vs-report per case (optional)

Records (viewer/data/responses.jsonl), one line per submit:
    {case_id, rater_id, verdict("accurate"|"not_accurate"), shown_sentence,
     edited_text, source("generated"|"report"|"blinded_A"...), ts_iso}
"""
from __future__ import annotations
import os, io, json, time, argparse
from pathlib import Path
import numpy as np
from flask import Flask, request, jsonify, send_from_directory, Response

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STATIC = HERE / "static"
RESP_DIR = HERE / "data"

# MODE: "v3" (accurate/not-accurate on a generated sentence) or "case2" (adjudicate the generalized
# case-2 recordings — pick a morphology label). Selected by VIEWER_MODE; drives paths + the UI.
MODE = os.environ.get("VIEWER_MODE", "v3")
if MODE == "case2":
    SIGDIR = HERE / "data" / "signals_case2"
    REVIEW_SET = ROOT / "data" / "derived" / "case2_review_set.jsonl"
    RESP_PATH = RESP_DIR / "responses_case2.jsonl"
    VERDICTS = [
        "WE'RE RIGHT: physiologic sleep slowing (normal sleep, not pathology)",
        "WE'RE RIGHT: age-appropriate (normal for this age; Morgoth/report over-call)",
        "WE MISS IT: rhythmic morphology (GRDA/FIRDA) that doesn't raise mean power",
        "WE'RE WRONG: our age-norm over-corrects genuinely pathological slowing",
        "WE MISS IT: real slowing, no clear reason (genuine miss)",
        "GATE WRONG: Morgoth false-positive (no real slowing)",
    ]
    CASE_FIELDS = ["age", "dominant_stage", "stage_mix", "report_gen_band", "amount_median", "prevalence", "p_generalized"]
else:
    SIGDIR = HERE / "data" / "signals"
    REVIEW_SET = ROOT / "data" / "derived" / "review_set.jsonl"
    RESP_PATH = RESP_DIR / "responses.jsonl"
    VERDICTS = ["accurate", "not_accurate"]
    CASE_FIELDS = []

app = Flask(__name__, static_folder=None)

# --- filter cache: (case_id, hp, lp, notch) -> filtered float array ---------------
_raw_cache: dict[str, tuple[np.ndarray, float, float]] = {}
_filt_cache: dict[tuple, list] = {}


def _load_raw(case_id: str):
    if case_id not in _raw_cache:
        z = np.load(SIGDIR / f"{case_id}.npz")
        _raw_cache[case_id] = (z["data"].astype(np.float64), float(z["fs"]), float(z["t0"]))
    return _raw_cache[case_id]


def _filtered(case_id: str, hp, lp, notch):
    key = (case_id, hp, lp, notch)
    if key in _filt_cache:
        return _filt_cache[key]
    from scipy.signal import butter, filtfilt, iirnotch
    data, fs, t0 = _load_raw(case_id)
    x = data.copy()
    nyq = fs / 2.0
    if hp and hp > 0:
        b, a = butter(2, hp / nyq, btype="high")
        x = filtfilt(b, a, x, axis=1)
    if lp and lp < nyq - 1:
        b, a = butter(4, lp / nyq, btype="low")
        x = filtfilt(b, a, x, axis=1)
    if notch:
        b, a = iirnotch(notch, 30.0, fs)
        x = filtfilt(b, a, x, axis=1)
    # round to int for a compact JSON payload (uV precision is plenty for display)
    out = [[int(round(v)) for v in ch] for ch in x]
    _filt_cache[key] = out
    if len(_filt_cache) > 24:                      # keep memory bounded
        _filt_cache.pop(next(iter(_filt_cache)))
    return out


# --- review set + responses -------------------------------------------------------
def load_cases():
    cases = []
    if REVIEW_SET.exists():
        for line in open(REVIEW_SET):
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    # only expose cases whose signal has actually been exported
    return [c for c in cases if (SIGDIR / f"{c['case_id']}.npz").exists()]


def load_responses():
    """Latest response per (rater_id, case_id) -> verdict record (for resume)."""
    latest = {}
    if RESP_PATH.exists():
        for line in open(RESP_PATH):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            latest[(r.get("rater_id"), r.get("case_id"))] = r
    return latest


# --- routes -----------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.route("/static/<path:fn>")
def static_files(fn):
    resp = send_from_directory(STATIC, fn)
    resp.headers["Cache-Control"] = "no-store, must-revalidate"
    return resp


@app.route("/api/config")
def api_config():
    """Drives the UI: which verdict buttons and which per-case numeric fields to show."""
    return jsonify({"mode": MODE, "verdicts": VERDICTS, "case_fields": CASE_FIELDS})


@app.route("/api/cases")
def api_cases():
    """Cases + this rater's existing verdicts (for resume + progress)."""
    rater = request.args.get("rater", app.config["DEFAULT_RATER"])
    cases = load_cases()
    resp = load_responses()
    blinded = app.config["BLINDED"]
    out = []
    for c in cases:
        prev = resp.get((rater, c["case_id"]))
        item = {"case_id": c["case_id"], "stratum": c.get("stratum", c.get("age_band")),
                "done": prev is not None,
                "verdict": (prev or {}).get("verdict"),
                "edited_text": (prev or {}).get("edited_text", "")}
        if MODE == "case2":
            item["fields"] = {k: c.get(k) for k in CASE_FIELDS}
        elif not blinded:
            item["sentence"] = c["generated_sentence"]
            item["source"] = "generated"
        out.append(item)
    return jsonify({"rater": rater, "blinded": blinded, "cases": out,
                    "n_done": sum(1 for c in out if c["done"]), "n_total": len(out)})


@app.route("/api/sentence")
def api_sentence():
    """Sentence for a case. In --blinded mode the source (ours/report) is chosen
    deterministically per (rater,case) and NOT revealed to the client."""
    rater = request.args.get("rater", app.config["DEFAULT_RATER"])
    cid = request.args["case_id"]
    c = next((x for x in load_cases() if x["case_id"] == cid), None)
    if c is None:
        return jsonify({"error": "unknown case"}), 404
    if not app.config["BLINDED"]:
        return jsonify({"case_id": cid, "sentence": c["generated_sentence"],
                        "source": "generated"})
    # blinded: deterministic coin per (rater,case); report sentence only if present
    import hashlib
    coin = int(hashlib.md5(f"{rater}|{cid}".encode()).hexdigest(), 16) & 1
    rep = c.get("report_sentence")
    if rep and coin:
        return jsonify({"case_id": cid, "sentence": rep, "source": "report"})
    return jsonify({"case_id": cid, "sentence": c["generated_sentence"],
                    "source": "generated"})


@app.route("/api/signal")
def api_signal():
    cid = request.args["case_id"]
    if not (SIGDIR / f"{cid}.npz").exists():
        return jsonify({"error": "no signal"}), 404
    hp = float(request.args.get("hp", 1.0)) if request.args.get("hp") not in ("", "0", None) else 0.0
    lp = float(request.args.get("lp", 70.0)) if request.args.get("lp") not in ("", "0", None) else 0.0
    notch = float(request.args.get("notch", 60.0)) if request.args.get("notch") not in ("", "0", None) else 0.0
    data = _filtered(cid, hp, lp, notch)
    _, fs, t0 = _load_raw(cid)
    return Response(json.dumps({"case_id": cid, "fs": fs, "t0": t0,
                                "channels": BIPOLAR, "data": data}),
                    mimetype="application/json")


@app.route("/api/save", methods=["POST"])
def api_save():
    b = request.get_json(force=True)
    cid = b.get("case_id")
    verdict = b.get("verdict")
    if not cid or verdict not in VERDICTS:
        return jsonify({"error": f"case_id and a valid verdict required ({VERDICTS})"}), 400
    rec = {
        "case_id": cid,
        "rater_id": b.get("rater_id") or app.config["DEFAULT_RATER"],
        "verdict": verdict,
        "notes": b.get("edited_text", ""),
        "shown_sentence": b.get("shown_sentence", ""),
        "edited_text": b.get("edited_text", ""),
        "source": b.get("source", "generated"),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    RESP_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESP_PATH, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    resp = load_responses()
    rater = rec["rater_id"]
    n_done = sum(1 for (rr, _), _ in resp.items() if rr == rater)
    return jsonify({"ok": True, "n_done": n_done})


BIPOLAR = ['Fp1-F7', 'F7-T3', 'T3-T5', 'T5-O1', 'Fp2-F8', 'F8-T4', 'T4-T6', 'T6-O2',
           'Fp1-F3', 'F3-C3', 'C3-P3', 'P3-O1', 'Fp2-F4', 'F4-C4', 'C4-P4', 'P4-O2',
           'Fz-Cz', 'Cz-Pz']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--rater", default=os.environ.get("RATER_ID", "rater_1"))
    ap.add_argument("--blinded", action="store_true",
                    help="randomize ours-vs-report sentence per case (source hidden)")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    app.config["DEFAULT_RATER"] = a.rater
    app.config["BLINDED"] = a.blinded
    n = len(load_cases())
    print(f"EEG review viewer: {n} cases with signals | rater={a.rater} | "
          f"blinded={a.blinded}\n  http://{a.host}:{a.port}\n  responses -> {RESP_PATH}")
    app.run(host=a.host, port=a.port, debug=a.debug)


if __name__ == "__main__":
    main()
