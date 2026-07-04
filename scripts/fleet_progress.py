"""Fleet progress tracker -> burndown. Counts S3 .done markers under the Growth_curves/expansion output
and appends a timestamped event to data/derived/fleet_progress.jsonl, then rebuilds the burndown HTML.
Run each poll (I redeploy the Artifact). Uses the BDSP keys for the credentialed bucket.

Run: python scripts/fleet_progress.py [TOTAL]     (default TOTAL=13034)
"""
from __future__ import annotations
import csv, glob, json, os, subprocess, sys, time
from pathlib import Path

TOTAL = int(sys.argv[1]) if len(sys.argv) > 1 else 13034
DONE_PREFIX = "bdsp:bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/expansion/done/"
PROG = Path("data/derived/fleet_progress.jsonl")
RC = os.path.expanduser("~/.local/bin/rclone")


def bdsp_env():
    f = glob.glob("/Users/mbwest/Desktop/GithubRepos/AWSKeys/bdsp_opendata_write_accessKeys.csv")[0]
    r = list(csv.DictReader(open(f, encoding="utf-8-sig")))[0]
    e = dict(os.environ)
    e["AWS_ACCESS_KEY_ID"] = r["Access key ID"]; e["AWS_SECRET_ACCESS_KEY"] = r["Secret access key"]
    return e


def main():
    out = subprocess.run([RC, "lsf", DONE_PREFIX], capture_output=True, text=True, env=bdsp_env())
    done = sum(1 for l in out.stdout.splitlines() if l.strip().endswith(".done"))
    PROG.parent.mkdir(parents=True, exist_ok=True)
    if not PROG.exists():
        PROG.write_text(json.dumps({"t": time.time(), "event": "start", "total": TOTAL, "done": 0}) + "\n")
    with open(PROG, "a") as fh:
        fh.write(json.dumps({"t": time.time(), "event": "done", "done": done, "total": TOTAL}) + "\n")
    subprocess.run([sys.executable, "scripts/build_burndown.py", str(PROG), "results/fleet_burndown.html"], check=True)
    print(f"fleet done: {done}/{TOTAL}")


if __name__ == "__main__":
    main()
