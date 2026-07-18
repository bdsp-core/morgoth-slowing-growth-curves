"""Fleet progress tracker -> burndown. Counts S3 .done markers under the Growth_curves/expansion output
and appends a timestamped event to data/derived/fleet_progress.jsonl, then rebuilds the burndown HTML.
Run each poll (I redeploy the Artifact). Uses the BDSP keys for the credentialed bucket.

Run: python scripts/fleet_progress.py [TOTAL]     (default TOTAL=13034)
"""
from __future__ import annotations
import csv, glob, json, os, subprocess, sys, time
from pathlib import Path

TOTAL = int(sys.argv[1]) if len(sys.argv) > 1 else 13034
BASE = os.environ.get("FLEET_S3_BASE",
    "bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/expansion")
DONE_PREFIX = f"{BASE}/done/"
GATE_PREFIX = f"{BASE}/gate/"
PROV_PREFIX = f"{BASE}/provenance/"
PROG = Path(os.environ.get("FLEET_PROG", "data/derived/fleet_progress.jsonl"))
RC = os.environ.get("RCLONE_BIN", os.path.expanduser("~/.local/bin/rclone"))


def bdsp_env():
    # If the BDSP write-key CSV isn't present, fall back to the ambient env (the rclone remote in
    # FLEET_S3_BASE already carries its own keys, e.g. the `s3:` remote on this machine).
    fs = glob.glob("/Users/mbwest/Desktop/GithubRepos/AWSKeys/bdsp_opendata_write_accessKeys.csv")
    if not fs:
        return dict(os.environ)
    r = list(csv.DictReader(open(fs[0], encoding="utf-8-sig")))[0]
    e = dict(os.environ)
    e["AWS_ACCESS_KEY_ID"] = r["Access key ID"]; e["AWS_SECRET_ACCESS_KEY"] = r["Secret access key"]
    return e


def latest_card(env):
    """Detail of the most-recently-completed recording (for the dashboard's 'Completed' feed)."""
    r = subprocess.run([RC, "lsf", "--format", "tp", GATE_PREFIX], capture_output=True, text=True, env=env)
    lines = sorted((l for l in r.stdout.splitlines() if l.endswith(".json")), reverse=True)  # newest first
    if not lines:
        return {}
    rid = lines[0].split(";", 1)[1][:-5]
    def cat(p):
        return json.loads(subprocess.run([RC, "cat", p], capture_output=True, text=True, env=env).stdout or "{}")
    try:
        g = cat(f"{GATE_PREFIX}{rid}.json"); p = cat(f"{PROV_PREFIX}{rid}.json")
    except Exception:
        return {"rid": rid}
    lab = ("focal_slow" if g.get("focal_pred_class") == 1 else
           "general_slow" if g.get("generalized_pred_class") == 1 else
           "normal" if g.get("normal_pred_class") == 1 else "")
    return {"rid": rid, "label": lab,
            "usable": p.get("usable_segments", 0), "seg_total": p.get("total_segments", 0)}


def main():
    env = bdsp_env()
    out = subprocess.run([RC, "lsf", DONE_PREFIX], capture_output=True, text=True, env=env)
    done = sum(1 for l in out.stdout.splitlines() if l.strip().endswith(".done"))
    PROG.parent.mkdir(parents=True, exist_ok=True)
    if not PROG.exists():
        PROG.write_text(json.dumps({"t": time.time(), "event": "start", "total": TOTAL, "done": 0}) + "\n")
    evt = {"t": time.time(), "event": "done", "done": done, "total": TOTAL, **latest_card(env)}
    with open(PROG, "a") as fh:
        fh.write(json.dumps(evt) + "\n")
    subprocess.run([sys.executable, "scripts/build_burndown.py", str(PROG), "results/fleet_burndown.html"], check=True)
    print(f"fleet done: {done}/{TOTAL}  latest={evt.get('rid','?')} ({evt.get('label','')})")


if __name__ == "__main__":
    main()
