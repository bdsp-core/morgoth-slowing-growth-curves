"""Build a self-contained HTML report-labeling tool for ~1,000 cohort cases that mention slowing.

Shows each report's IMPRESSION + full text with trigger phrases highlighted (normal / abnormal / slowing /
drowsy-sleep qualifiers / side / 10-20 electrodes / band), the auto-derived flags, and label buttons
(Normal / Pathologic slowing / Physiologic (drowsy/sleep) slowing / Unsure) that persist to localStorage
and export to CSV. Brandon's rule: a NORMAL impression == ground-truth normal (shown prominently).

Also writes results/labeling_cases.csv (the selected cases + raw impression/report text) so the raw text
is available for offline work.

Run: python scripts/56_build_report_labeler.py
"""
from __future__ import annotations
import html, json, re
from pathlib import Path
import numpy as np, pandas as pd

SC = "/private/tmp/claude-503/-Users-mbwest/7f57b202-b703-4b7d-b490-920bc2680984/scratchpad"
N_CASES = 1000

# highlight categories -> (regex, css class)
PATS = [
    ("imp-normal", r"\b(normal (?:eeg|study|awake and (?:drowsy|asleep)|awake)|within normal limits|no (?:abnormalit|epileptiform))\w*"),
    ("abnormal", r"\b(abnormal|encephalopath\w*|dysfunction|cerebral dysfunction)"),
    ("slowing", r"\bslow\w*"),
    ("drowsy", r"\b(drows\w*|sleep|asleep|somnolen\w*|state[- ]dependent|consistent with (?:drows|sleep))\w*"),
    ("side", r"\b(left|right|bilateral|diffuse|generali[sz]ed|independent)\b|\b[lr]\s*>\s*[lr]\b"),
    ("electrode", r"\b(fp1|fp2|f7|f8|f3|f4|t1|t2|t3|t4|t5|t6|c3|c4|p3|p4|o1|o2|a1|a2)\b"),
    ("band", r"\b(delta|theta)\b"),
]
COMPILED = [(c, re.compile(p, re.I)) for c, p in PATS]


def highlight(text):
    """Wrap matched spans in <mark class=...>. Non-overlapping, first-match-wins by category order."""
    text = text or ""
    spans = []  # (start, end, cls)
    for cls, rx in COMPILED:
        for m in rx.finditer(text):
            spans.append((m.start(), m.end(), cls))
    spans.sort()
    out, i, occupied = [], 0, []
    for s, e, cls in spans:
        if s < i:
            continue  # overlap -> skip
        out.append(html.escape(text[i:s]))
        out.append(f'<mark class="hl-{cls}">{html.escape(text[s:e])}</mark>')
        i = e
    out.append(html.escape(text[i:]))
    return "".join(out)


def imp_normal(imp):
    t = (imp or "").lower()
    return bool(re.search(r"\bnormal (eeg|study|awake)|within normal limits|this is a normal\b", t)) and not re.search(r"\babnormal\b", t)


def main():
    rep = pd.read_csv(f"{SC}/reports/EEGs_And_Reports.csv",
                      usecols=lambda c: c in ["SiteID", "BDSPPatientID", "StartTime", "impression", "reports"],
                      low_memory=False, dtype=str)
    rep["pid"] = rep.BDSPPatientID.astype(str).str.replace(r"\.0$", "", regex=True)
    rep["date"] = pd.to_datetime(rep.StartTime, errors="coerce").dt.strftime("%Y%m%d")
    rep["impression"] = rep.impression.fillna(""); rep["reports"] = rep.reports.fillna("")
    rep["full"] = rep.impression + " || " + rep.reports
    rep = rep[rep.full.str.contains("slow", case=False, na=False)].dropna(subset=["date"])

    # join to cohort (so labels feed the cohort classifier) via report_extracted_labels
    rl = pd.read_csv("results/report_extracted_labels.csv")
    rl["pid"] = rl.bdsp_id.str.replace(r"^S000\d", "", regex=True); rl["date"] = rl.eeg_datetime.astype(str).str[:8]
    j = rl.merge(rep, on=["pid", "date"], how="inner").drop_duplicates("bdsp_id")
    j["imp_normal"] = j.impression.map(imp_normal)

    # stratified ~N: slowing cases, balanced across impression-normal vs not, and label groups
    j["stratum"] = np.where(j.imp_normal, "imp_normal", j.label.astype(str))
    per = max(1, N_CASES // max(1, j.stratum.nunique()))
    sel = j.groupby("stratum", group_keys=False).apply(lambda g: g.head(per)).head(N_CASES)
    print(f"selected {len(sel)} cases; strata: {sel.stratum.value_counts().to_dict()}")

    # write raw-text CSV (offline availability)
    sel[["bdsp_id", "eeg_datetime", "label", "side", "region", "band", "imp_normal", "impression", "reports"]] \
        .to_csv("results/labeling_cases.csv", index=False)

    cases = []
    for _, r in sel.iterrows():
        cases.append({"id": r.bdsp_id, "imp_normal": bool(r.imp_normal),
                      "auto": f"label={r.label} side={r.side} region={r.region} band={r.band}",
                      "imp_html": highlight(r.impression[:4000]),
                      "rep_html": highlight(r.reports[:8000])})
    Path("results").mkdir(exist_ok=True)
    Path("results/report_labeler.html").write_text(TEMPLATE.replace("/*CASES*/", json.dumps(cases)))
    print(f"wrote results/report_labeler.html ({len(cases)} cases) + results/labeling_cases.csv")


TEMPLATE = r"""<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>EEG report labeler</title>
<style>
 body{font:15px/1.55 -apple-system,system-ui,sans-serif;margin:0;background:#0f1420;color:#e8eef7}
 .wrap{max-width:900px;margin:0 auto;padding:16px}
 .bar{position:sticky;top:0;background:#0f1420;padding:10px 0;border-bottom:1px solid #243049;z-index:5}
 .btns{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
 button{font:14px system-ui;padding:8px 12px;border-radius:8px;border:1px solid #2c3a57;background:#18213200;color:#e8eef7;cursor:pointer}
 button.sel{outline:2px solid #35e0c4}
 .b-normal{background:#12351f}.b-path{background:#3a1720}.b-phys{background:#15243f}.b-uns{background:#2a2a2a}
 .card{background:#141c2c;border:1px solid #243049;border-radius:12px;padding:14px;margin:12px 0}
 h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;color:#8798b3;margin:0 0 6px}
 .imp{background:#0c1526;border-left:3px solid #4a90e2;padding:8px 10px;border-radius:6px;white-space:pre-wrap}
 .rep{white-space:pre-wrap;color:#cdd8ea;max-height:340px;overflow:auto;background:#0c1220;padding:8px 10px;border-radius:6px}
 mark{border-radius:3px;padding:0 2px;color:#0b0f17}
 .hl-imp-normal{background:#43e08a}.hl-abnormal{background:#ff6b7d}.hl-slowing{background:#f5b13a}
 .hl-drowsy{background:#6db1ff}.hl-side{background:#c58cff}.hl-electrode{background:#4bd6c6}.hl-band{background:#e0b060}
 .pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:.72rem;margin-left:6px}
 .yes{background:#12351f;color:#43e08a}.no{background:#2a2a2a;color:#8798b3}
 .legend span{margin-right:10px;font-size:.75rem}.small{color:#8798b3;font-size:.8rem}
</style>
<div class="wrap">
 <div class="bar">
   <b>EEG report labeler</b> <span id="prog" class="small"></span>
   <div class="legend">
     <span><mark class="hl-imp-normal">impression-normal</mark></span><span><mark class="hl-abnormal">abnormal</mark></span>
     <span><mark class="hl-slowing">slowing</mark></span><span><mark class="hl-drowsy">drowsy/sleep</mark></span>
     <span><mark class="hl-side">side</mark></span><span><mark class="hl-electrode">electrode</mark></span><span><mark class="hl-band">band</mark></span>
   </div>
   <div class="btns">
     <button class="b-normal" onclick="lab('normal')">1 · Normal (N)</button>
     <button class="b-path" onclick="lab('pathologic')">2 · Pathologic slowing (P)</button>
     <button class="b-phys" onclick="lab('physiologic')">3 · Physiologic/drowsy slowing (D)</button>
     <button class="b-uns" onclick="lab('unsure')">4 · Unsure (U)</button>
     <button onclick="prev()">&larr; Prev</button><button onclick="next()">Next &rarr;</button>
     <button onclick="dl()">⬇ Download labels CSV</button>
   </div>
 </div>
 <div id="view"></div>
</div>
<script>
const CASES = /*CASES*/;
const KEY='eeg_labels_v1';
let labels = JSON.parse(localStorage.getItem(KEY)||'{}');
let i = parseInt(localStorage.getItem(KEY+'_idx')||'0');
const $=id=>document.getElementById(id);
function render(){
 const c=CASES[i];
 $('prog').textContent=`case ${i+1}/${CASES.length} · labeled ${Object.keys(labels).length} · id ${c.id}`;
 $('view').innerHTML=`<div class="card">
   <h2>Impression <span class="pill ${c.imp_normal?'yes':'no'}">${c.imp_normal?'IMPRESSION = NORMAL (ground truth)':'impression not normal'}</span></h2>
   <div class="imp">${c.imp_html||'(none)'}</div>
   <h2 style="margin-top:12px">Auto-extracted</h2><div class="small">${c.auto}</div>
   <h2 style="margin-top:12px">Full report</h2><div class="rep">${c.rep_html||'(none)'}</div>
   <div class="small" style="margin-top:8px">Your label: <b id="cur">${labels[c.id]||'—'}</b></div>
 </div>`;
 document.querySelectorAll('.btns button').forEach(b=>b.classList.remove('sel'));
}
function lab(v){labels[CASES[i].id]=v;localStorage.setItem(KEY,JSON.stringify(labels));$('cur').textContent=v;next();}
function next(){i=Math.min(CASES.length-1,i+1);localStorage.setItem(KEY+'_idx',i);render();}
function prev(){i=Math.max(0,i-1);localStorage.setItem(KEY+'_idx',i);render();}
function dl(){let s='bdsp_id,label\n';for(const k in labels)s+=`${k},${labels[k]}\n`;
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([s],{type:'text/csv'}));
 a.download='eeg_labels.csv';a.click();}
document.addEventListener('keydown',e=>{const m={'1':'normal','2':'pathologic','3':'physiologic','4':'unsure',
 'n':'normal','p':'pathologic','d':'physiologic','u':'unsure'};
 if(m[e.key])lab(m[e.key]);else if(e.key==='ArrowRight')next();else if(e.key==='ArrowLeft')prev();});
render();
</script>"""


if __name__ == "__main__":
    main()
