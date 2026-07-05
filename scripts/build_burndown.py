"""Turn the ingestion progress log into a self-contained, mobile-first burndown dashboard.

Reads data/derived/progress.jsonl (written by scripts/26 / the full-wave worker) and emits
results/burndown.html — a single file (no external assets) suitable for publishing as an Artifact and
viewing on a phone. Shows: overall %, ETA, a burndown chart (recordings remaining over time vs an
ideal pace line), throughput, and the completed-recording list colored by label.

Run:  PYTHONPATH=src python scripts/build_burndown.py [progress.jsonl] [out.html]
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path

PROG = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/derived/progress.jsonl")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("results/burndown.html")


def load_events():
    if not PROG.exists():
        return []
    ev = []
    for line in PROG.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                ev.append(json.loads(line))
            except Exception:
                pass
    return ev


def main():
    ev = load_events()
    now = time.time()
    # progress.jsonl accumulates across runs; anchor on the LATEST start event (current run)
    start_idxs = [i for i, e in enumerate(ev) if e.get("event") == "start"]
    si = start_idxs[-1] if start_idxs else 0
    start = ev[si] if start_idxs else None
    ev = ev[si:]                                       # only events from the current run
    total = int(start["total"]) if start else max([e.get("total", 0) for e in ev] + [0])
    t0 = start["t"] if start else (ev[0]["t"] if ev else now)
    done_events = [e for e in ev if e.get("event") in ("done", "finish")]
    done = max([e.get("done", 0) for e in ev] + [0])
    finished = any(e.get("event") == "finish" for e in ev)
    staging = any(e.get("event") == "staging" for e in ev) and not finished
    failed = [e for e in ev if e.get("event") == "fail"]

    elapsed = max(1.0, (done_events[-1]["t"] if done_events else now) - t0)
    # RECENT windowed rate (not cumulative) — a ramp/scale-up makes the lifetime average misleading.
    WINDOW = 2700                                               # ~45 min
    recent = [e for e in done_events if e["t"] >= (done_events[-1]["t"] if done_events else now) - WINDOW]
    if len(recent) < 2 and len(done_events) >= 2:
        recent = done_events[-2:]                               # fall back to last two points
    if len(recent) >= 2:
        dt = max(1.0, recent[-1]["t"] - recent[0]["t"])
        rate = max(0.0, recent[-1].get("done", 0) - recent[0].get("done", 0)) / dt
    else:
        rate = done / elapsed if done else 0.0                  # recordings / sec
    remaining = max(0, total - done)
    eta_sec = remaining / rate if rate > 0 and not finished else 0
    status = "complete" if finished else ("staging" if staging else ("running" if done < total else "running"))

    # burndown series: (elapsed_min, remaining) at each done event, plus origin
    series = [[0.0, total]]
    for e in done_events:
        series.append([round((e["t"] - t0) / 60.0, 2), max(0, total - e.get("done", 0))])
    # completed recording cards
    cards = [{"rid": e.get("rid", "?"), "label": e.get("label", ""),
              "usable": e.get("usable", 0), "seg_total": e.get("seg_total", 0),
              "min": round((e["t"] - t0) / 60.0, 1)}
             for e in ev if e.get("event") == "done" and e.get("rid") and e.get("rid") != "?"]
    cards = cards[-12:]                                 # keep the most-recent dozen

    # throughput series: instantaneous rate (recordings/hr) between consecutive samples
    rate_series, prev = [], None
    for e in done_events:
        if prev is not None:
            dt = e["t"] - prev["t"]
            if dt > 30:                                 # ignore near-duplicate samples
                r = max(0.0, e.get("done", 0) - prev.get("done", 0)) / dt * 3600.0
                rate_series.append([round((e["t"] - t0) / 60.0, 2), round(r, 1)])
        prev = e

    def fmt_dur(s):
        s = int(s)
        h, m = s // 3600, (s % 3600) // 60
        return f"{h}h {m}m" if h else f"{m}m"

    data = {
        "total": total, "done": done, "remaining": remaining,
        "pct": round(100 * done / total) if total else 0,
        "elapsed": fmt_dur(elapsed), "eta": fmt_dur(eta_sec) if eta_sec else ("—" if finished else "estimating…"),
        "rate_hr": round(rate * 3600, 1), "status": status,
        "asof": time.strftime("%Y-%m-%d %H:%M", time.localtime(now)),
        "series": series, "rate_series": rate_series, "cards": cards, "failed": len(failed),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(TEMPLATE.replace("/*DATA*/", json.dumps(data)))
    print(f"wrote {OUT}  ({done}/{total} done, status={status}, eta={data['eta']})")


TEMPLATE = r"""<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EEG ingestion — burndown</title>
<style>
  :root{ --bg:#0e1420; --panel:#161f2f; --line:#233047; --ink:#e8eef7; --dim:#8798b3;
         --accent:#35e0c4; --done:#35e0c4; --normal:#4a90e2; --focal:#f5a623; --gen:#e0568a; --bad:#ff5c6c; }
  *{ box-sizing:border-box }
  body{ margin:0; background:var(--bg); color:var(--ink);
        font:15px/1.5 ui-sans-serif,-apple-system,system-ui,sans-serif; -webkit-font-smoothing:antialiased }
  .wrap{ max-width:640px; margin:0 auto; padding:20px 16px 48px }
  h1{ font-size:1.05rem; font-weight:600; letter-spacing:.02em; margin:0 0 2px }
  .asof{ color:var(--dim); font-size:.78rem; margin-bottom:18px }
  .pill{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:.72rem; font-weight:600;
         text-transform:uppercase; letter-spacing:.06em; vertical-align:middle; margin-left:8px }
  .running{ background:rgba(53,224,196,.15); color:var(--accent) }
  .staging{ background:rgba(245,166,35,.15); color:var(--focal) }
  .complete{ background:rgba(74,144,226,.18); color:var(--normal) }
  .hero{ display:flex; align-items:baseline; gap:10px; margin:6px 0 4px }
  .big{ font-size:3rem; font-weight:700; font-variant-numeric:tabular-nums; line-height:1 }
  .of{ color:var(--dim); font-size:1.1rem; font-variant-numeric:tabular-nums }
  .bar{ height:12px; border-radius:6px; background:var(--line); overflow:hidden; margin:14px 0 6px }
  .bar>i{ display:block; height:100%; background:linear-gradient(90deg,var(--normal),var(--accent)); }
  .grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:18px 0 }
  .stat{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:12px }
  .stat .k{ color:var(--dim); font-size:.72rem; text-transform:uppercase; letter-spacing:.05em }
  .stat .v{ font-size:1.4rem; font-weight:600; font-variant-numeric:tabular-nums; margin-top:2px }
  .card{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:14px 16px; margin-top:16px }
  .card h2{ font-size:.8rem; text-transform:uppercase; letter-spacing:.06em; color:var(--dim); margin:0 0 10px; font-weight:600 }
  canvas{ width:100%; height:200px; display:block }
  .rec{ display:flex; align-items:center; gap:10px; padding:9px 0; border-top:1px solid var(--line); font-size:.9rem }
  .rec:first-of-type{ border-top:none }
  .dot{ width:9px; height:9px; border-radius:50%; flex:none }
  .rid{ font-family:ui-monospace,Menlo,monospace; font-size:.8rem; color:var(--dim);
        overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1 }
  .use{ font-variant-numeric:tabular-nums; font-weight:600 }
  .lab{ font-size:.7rem; text-transform:uppercase; letter-spacing:.04em; color:var(--dim); width:52px; text-align:right }
  .empty{ color:var(--dim); text-align:center; padding:30px 0 }
</style>
<div class="wrap">
  <h1>EEG slowing ingestion<span id="pill" class="pill"></span></h1>
  <div class="asof" id="asof"></div>

  <div class="hero"><span class="big" id="done"></span><span class="of" id="of"></span></div>
  <div class="bar"><i id="fill"></i></div>

  <div class="grid">
    <div class="stat"><div class="k">Remaining</div><div class="v" id="rem"></div></div>
    <div class="stat"><div class="k">ETA</div><div class="v" id="eta"></div></div>
    <div class="stat"><div class="k">Rate /hr</div><div class="v" id="rate"></div></div>
    <div class="stat"><div class="k">Elapsed</div><div class="v" id="elapsed"></div></div>
    <div class="stat"><div class="k">Failed</div><div class="v" id="failed"></div></div>
    <div class="stat"><div class="k">Total</div><div class="v" id="total"></div></div>
  </div>

  <div class="card"><h2>Burndown — recordings remaining</h2><canvas id="chart"></canvas></div>
  <div class="card"><h2>Throughput — recordings / hour</h2><canvas id="ratechart"></canvas></div>
  <div class="card"><h2>Completed recordings</h2><div id="list"></div></div>
</div>
<script>
const D = /*DATA*/;
const $ = id => document.getElementById(id);
const LABC = {normal:'var(--normal)', focal_slow:'var(--focal)', general_slow:'var(--gen)'};
const LABT = {normal:'normal', focal_slow:'focal', general_slow:'gen'};

$('pill').textContent = D.status; $('pill').className = 'pill ' + D.status;
$('asof').textContent = 'as of ' + D.asof + (D.status==='complete' ? '' : ' · updates when checked');
$('done').textContent = D.done; $('of').textContent = '/ ' + D.total;
$('fill').style.width = D.pct + '%';
$('rem').textContent = D.remaining; $('eta').textContent = D.eta; $('rate').textContent = D.rate_hr;
$('elapsed').textContent = D.elapsed; $('failed').textContent = D.failed; $('total').textContent = D.total;

// completed list
const list = $('list');
if(!D.cards.length){ list.innerHTML = '<div class="empty">No recordings completed yet.</div>'; }
else { for(const c of D.cards.slice().reverse()){
  // usable% only applies to the feature-extraction job; staging-only jobs omit it
  const metric = c.seg_total
    ? `${Math.round(100*c.usable/c.seg_total)}%<span style="color:var(--dim);font-weight:400"> usable</span>`
    : `<span style="color:var(--accent)">staged ✓</span>`;
  const el = document.createElement('div'); el.className='rec';
  el.innerHTML = `<span class="dot" style="background:${LABC[c.label]||'var(--dim)'}"></span>`+
    `<span class="rid">${c.rid}</span>`+
    `<span class="use">${metric}</span>`+
    `<span class="lab">${LABT[c.label]||''}</span>`;
  list.appendChild(el);
}}

// burndown chart (canvas, DPR-aware)
const cv = $('chart'), ctx = cv.getContext('2d');
function draw(){
  const dpr = window.devicePixelRatio||1, W = cv.clientWidth, H = 200;
  cv.width = W*dpr; cv.height = H*dpr; ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,W,H);
  const pad = {l:34,r:12,t:12,b:24};
  const S = D.series, xmax = Math.max(1, S[S.length-1][0]), ymax = Math.max(1, D.total);
  const X = v => pad.l + (W-pad.l-pad.r)*(v/xmax);
  const Y = v => pad.t + (H-pad.t-pad.b)*(1 - v/ymax);
  // grid + y labels
  ctx.strokeStyle='#233047'; ctx.fillStyle='#8798b3'; ctx.font='11px ui-sans-serif'; ctx.lineWidth=1;
  for(let i=0;i<=2;i++){ const yv=ymax*i/2, y=Y(yv);
    ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(W-pad.r,y); ctx.stroke();
    ctx.fillText(Math.round(yv), 6, y+3); }
  // ideal pace line (total -> 0 across elapsed), dashed
  ctx.setLineDash([4,4]); ctx.strokeStyle='#3a4a66'; ctx.beginPath();
  ctx.moveTo(X(0),Y(ymax)); ctx.lineTo(X(xmax),Y(0)); ctx.stroke(); ctx.setLineDash([]);
  // actual remaining (step) + area
  ctx.beginPath(); ctx.moveTo(X(S[0][0]),Y(S[0][1]));
  for(const [x,y] of S){ ctx.lineTo(X(x),Y(y)); }
  const grad = ctx.createLinearGradient(0,pad.t,0,H-pad.b);
  grad.addColorStop(0,'rgba(53,224,196,.28)'); grad.addColorStop(1,'rgba(53,224,196,0)');
  ctx.lineTo(X(S[S.length-1][0]),Y(0)); ctx.lineTo(X(S[0][0]),Y(0)); ctx.closePath();
  ctx.fillStyle=grad; ctx.fill();
  ctx.beginPath(); ctx.moveTo(X(S[0][0]),Y(S[0][1]));
  for(const [x,y] of S){ ctx.lineTo(X(x),Y(y)); }
  ctx.strokeStyle='#35e0c4'; ctx.lineWidth=2; ctx.stroke();
  // endpoint dot
  const last = S[S.length-1];
  ctx.fillStyle='#35e0c4'; ctx.beginPath(); ctx.arc(X(last[0]),Y(last[1]),3.5,0,7); ctx.fill();
  // x label
  ctx.fillStyle='#8798b3'; ctx.fillText('minutes', W-pad.r-46, H-6);
}
// throughput chart (instantaneous recordings/hr per sample)
const rcv = $('ratechart'), rctx = rcv && rcv.getContext('2d');
function drawRate(){
  if(!rcv) return;
  const R = D.rate_series || [];
  const dpr = window.devicePixelRatio||1, W = rcv.clientWidth, H = 200;
  rcv.width = W*dpr; rcv.height = H*dpr; rctx.setTransform(dpr,0,0,dpr,0,0);
  rctx.clearRect(0,0,W,H);
  const pad = {l:40,r:12,t:12,b:24};
  if(R.length < 1){ rctx.fillStyle='#8798b3'; rctx.font='12px ui-sans-serif';
    rctx.fillText('collecting samples…', pad.l, H/2); return; }
  const xmax = Math.max(1, R[R.length-1][0]);
  const ymax = Math.max(10, Math.max.apply(null, R.map(p=>p[1]))*1.15);
  const X = v => pad.l + (W-pad.l-pad.r)*(v/xmax);
  const Y = v => pad.t + (H-pad.t-pad.b)*(1 - v/ymax);
  rctx.strokeStyle='#233047'; rctx.fillStyle='#8798b3'; rctx.font='11px ui-sans-serif'; rctx.lineWidth=1;
  for(let i=0;i<=2;i++){ const yv=ymax*i/2, y=Y(yv);
    rctx.beginPath(); rctx.moveTo(pad.l,y); rctx.lineTo(W-pad.r,y); rctx.stroke();
    rctx.fillText(Math.round(yv), 6, y+3); }
  // area + line
  const grad = rctx.createLinearGradient(0,pad.t,0,H-pad.b);
  grad.addColorStop(0,'rgba(74,144,226,.30)'); grad.addColorStop(1,'rgba(74,144,226,0)');
  rctx.beginPath(); rctx.moveTo(X(R[0][0]),Y(R[0][1]));
  for(const [x,y] of R){ rctx.lineTo(X(x),Y(y)); }
  rctx.lineTo(X(R[R.length-1][0]),Y(0)); rctx.lineTo(X(R[0][0]),Y(0)); rctx.closePath();
  rctx.fillStyle=grad; rctx.fill();
  rctx.beginPath(); rctx.moveTo(X(R[0][0]),Y(R[0][1]));
  for(const [x,y] of R){ rctx.lineTo(X(x),Y(y)); }
  rctx.strokeStyle='#4a90e2'; rctx.lineWidth=2; rctx.stroke();
  // dots at each sample
  rctx.fillStyle='#4a90e2';
  for(const [x,y] of R){ rctx.beginPath(); rctx.arc(X(x),Y(y),2.2,0,7); rctx.fill(); }
  rctx.fillStyle='#8798b3'; rctx.fillText('minutes', W-pad.r-46, H-6);
}
draw(); drawRate(); window.addEventListener('resize', ()=>{draw(); drawRate();});
</script>
"""


if __name__ == "__main__":
    main()
