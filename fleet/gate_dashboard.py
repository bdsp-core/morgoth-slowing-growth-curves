#!/usr/bin/env python3
"""Live dashboard for the gate re-run fleet. Polls S3, renders a self-refreshing HTML page.

Run:  PYTHONPATH=src python fleet/gate_dashboard.py            # one snapshot -> results/gate_run_dashboard.html
      PYTHONPATH=src python fleet/gate_dashboard.py --loop 60  # refresh every 60 s until Ctrl-C
"""
import argparse, subprocess, time, os, datetime, json
from pathlib import Path

PROFILE = "bdspwrite"
BASE = "s3://bdsp-opendata-credentialed/morgoth2/data/internal_dataset/Growth_curves/gate_rerun_v1"
TOTAL = 27478           # re-gateable recordings (cohort 25617 + MoE 1761 + ON 100)
OUT = Path("results/gate_run_dashboard.html")


def s3_ls(prefix):
    r = subprocess.run(["aws", "s3", "ls", f"{BASE}/{prefix}", "--profile", PROFILE],
                       capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l.strip()]


def workers():
    r = subprocess.run(["aws", "ec2", "describe-instances", "--profile", "fleet", "--region", "us-east-1",
                        "--filters", "Name=tag:fleet,Values=morgoth-gate-rerun",
                        "Name=instance-state-name,Values=pending,running",
                        "--query", "Reservations[].Instances[].LaunchTime", "--output", "text"],
                       capture_output=True, text=True)
    return [x for x in r.stdout.split() if x]


def snapshot():
    wg = s3_ls("window_gate/")                 # one dir line per completed recording
    done = s3_ls("_done/")
    status = s3_ls("_status/")
    ids = [l.split("eeg_id=")[-1].rstrip("/") for l in wg if "eeg_id=" in l]
    src = {"cohort": 0, "MoE": 0, "ON": 0}
    for i in ids:
        src["MoE" if i.startswith("MOE_") else "ON" if i.startswith("ON_") else "cohort"] += 1
    # failure reasons from _status bodies (cheap: just count files, sample a few reasons)
    return {"done_real": len(ids), "done_markers": len(done), "status": len(status),
            "src": src, "workers": len(workers()), "t": time.time()}


HIST = Path("results/.gate_hist.json")


def render(s):
    now = datetime.datetime.now()
    hist = json.loads(HIST.read_text()) if HIST.exists() else []
    hist.append({"t": s["t"], "n": s["done_real"]})
    hist = hist[-240:]
    HIST.write_text(json.dumps(hist))
    # rate from the last ~15 min of history
    rate = eta = None
    old = [h for h in hist if s["t"] - h["t"] >= 300]
    if old:
        h0 = old[-1]
        dt = (s["t"] - h0["t"]) / 60.0
        dn = s["done_real"] - h0["n"]
        if dt > 0 and dn > 0:
            rate = dn / dt
            eta = (TOTAL - s["done_real"]) / rate
    pct = 100 * s["done_real"] / TOTAL
    bar = f'<div style="background:#e5e7eb;border-radius:8px;height:26px;overflow:hidden">' \
          f'<div style="width:{pct:.2f}%;background:linear-gradient(90deg,#2563eb,#22c55e);height:100%"></div></div>'
    rate_s = f"{rate:.0f}/min" if rate else "—"
    eta_s = (f"{eta/60:.1f} h" if eta and eta > 90 else f"{eta:.0f} min") if eta else "—"
    cards = "".join(
        f'<div class="card"><div class="v">{v}</div><div class="k">{k}</div></div>'
        for k, v in [("recordings done", f"{s['done_real']:,}"), ("of target", f"{TOTAL:,}"),
                     ("workers up", s["workers"]), ("throughput", rate_s), ("ETA", eta_s),
                     ("failures logged", s["status"])])
    srcrows = "".join(f"<tr><td>{k}</td><td style='text-align:right'>{v:,}</td></tr>"
                      for k, v in s["src"].items())
    OUT.write_text(f"""<!doctype html><html><head><meta charset=utf-8>
<meta http-equiv="refresh" content="30">
<title>Gate re-run — live</title>
<style>
 body{{font:15px -apple-system,system-ui,sans-serif;margin:0;background:#0f172a;color:#e2e8f0}}
 .wrap{{max-width:820px;margin:0 auto;padding:28px}}
 h1{{font-size:20px;margin:0 0 4px}} .sub{{color:#94a3b8;font-size:13px;margin-bottom:20px}}
 .cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}}
 .card{{background:#1e293b;border-radius:10px;padding:14px}}
 .v{{font-size:24px;font-weight:700}} .k{{color:#94a3b8;font-size:12px;margin-top:2px}}
 table{{width:100%;border-collapse:collapse;background:#1e293b;border-radius:10px;overflow:hidden}}
 td{{padding:8px 14px;border-top:1px solid #334155}}
 .big{{font-size:15px;margin:6px 0 4px;color:#cbd5e1}}
</style></head><body><div class=wrap>
<h1>Morgoth gate re-run — 1&nbsp;s step, full raw output</h1>
<div class=sub>updates every 30&nbsp;s · {now:%Y-%m-%d %H:%M:%S} · writing to gate_rerun_v1/</div>
<div class=big><b>{pct:.1f}%</b> — {s['done_real']:,} / {TOTAL:,} recordings</div>
{bar}
<div class=cards>{cards}</div>
<div class=big>by source</div>
<table>{srcrows}</table>
<div class=sub style="margin-top:18px">Each recording writes window_gate (per-second 3-class softmax + p_abnormal)
and segment_gate (independent P(focal)/P(generalized) at 30/60/120&nbsp;s). Workers self-terminate when the
manifest is covered.</div>
</div></body></html>""")
    return pct, eta_s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--loop", type=int, default=0); a = ap.parse_args()
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    while True:
        s = snapshot(); pct, eta = render(s)
        print(f"{datetime.datetime.now():%H:%M:%S}  {s['done_real']:,}/{TOTAL:,} ({pct:.1f}%)  "
              f"workers={s['workers']}  ETA {eta}  -> {OUT}")
        if not a.loop:
            break
        time.sleep(a.loop)


if __name__ == "__main__":
    main()
