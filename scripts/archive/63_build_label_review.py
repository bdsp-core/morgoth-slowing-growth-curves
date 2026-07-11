"""Build a self-contained HTML review tool so Brandon can sanity-check the LLM gen-slowing labels.

Shows a stratified sample (~150) of the labeled cases: impression + report with trigger phrases
highlighted, the LLM's gen_class + confidence + rationale + key_phrase, and Agree / Disagree /
Correct-to buttons that persist to localStorage and export a CSV. Prioritizes the cases most worth
a human eye: low-confidence, 'unsure', and cases where the simple classifier disagrees with the LLM.

Run: python scripts/63_build_label_review.py [n]
"""
from __future__ import annotations
import html, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

DER = Path("data/derived"); RES = Path("results")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 150

PATS = [
    ("imp-normal", r"\b(normal (?:eeg|study|awake and (?:drowsy|asleep)|awake)|within normal limits|no (?:abnormalit|epileptiform))\w*"),
    ("abnormal", r"\b(abnormal|encephalopath\w*|dysfunction|disorganiz\w*|excess\w*|poorly organiz\w*)"),
    ("slowing", r"\bslow\w*"),
    ("drowsy", r"\b(drows\w*|sleep|asleep|somnolen\w*|hyperventilat\w*|state[- ]dependent)"),
    ("side", r"\b(left|right|bilateral|diffuse|generali[sz]ed|anterior|posterior|frontal|background)\b"),
    ("band", r"\b(delta|theta)\b"),
]
COMPILED = [(c, re.compile(p, re.I)) for c, p in PATS]


def highlight(text):
    text = text or ""
    spans = []
    for cls, rx in COMPILED:
        for m in rx.finditer(text):
            spans.append((m.start(), m.end(), cls))
    spans.sort()
    out, i = [], 0
    for s, e, cls in spans:
        if s < i: continue
        out.append(html.escape(text[i:s])); out.append(f'<mark class="hl-{cls}">{html.escape(text[s:e])}</mark>'); i = e
    out.append(html.escape(text[i:]))
    return "".join(out)


def main():
    lab = pd.read_csv(DER / "gen_labels_llm.csv")
    feat = pd.read_parquet(DER / "gen_labeling_set.parquet")
    d = feat.merge(lab, left_on="bdsp_id", right_on="id", how="inner")
    if (DER / "gen_class_predictions.parquet").exists():
        pred = pd.read_parquet(DER / "gen_class_predictions.parquet")[["bdsp_id", "p_pathologic", "gen_class_pred"]]
        d = d.merge(pred, on="bdsp_id", how="left")
    else:
        d["p_pathologic"] = np.nan; d["gen_class_pred"] = ""

    # priority score: unsure, low confidence, LLM/classifier disagreement
    llm_path = (d.gen_class == "pathologic").astype(int)
    clf_path = (d.gen_class_pred == "pathologic").astype(int)
    d["disagree"] = (llm_path != clf_path).astype(int)
    d["conf"] = pd.to_numeric(d.confidence, errors="coerce").fillna(0.5)
    d["priority"] = d.disagree * 2 + (d.gen_class == "unsure").astype(int) * 2 + (1 - d.conf)
    # take the most-worth-reviewing, but keep some easy ones for calibration
    hard = d.sort_values("priority", ascending=False).head(int(N * 0.7))
    easy = d[~d.bdsp_id.isin(hard.bdsp_id)].sample(min(N - len(hard), max(0, len(d) - len(hard))),
                                                   random_state=0) if len(d) > len(hard) else d.head(0)
    sel = pd.concat([hard, easy]).drop_duplicates("bdsp_id")
    print(f"review set: {len(sel)} cases ({int(sel.disagree.sum())} LLM/clf disagreements, "
          f"{int((sel.gen_class=='unsure').sum())} unsure)")

    cases = []
    for r in sel.itertuples():
        cases.append({
            "id": r.bdsp_id, "llm": r.gen_class, "conf": round(float(r.conf), 2),
            "rationale": str(getattr(r, "rationale", "")), "key": str(getattr(r, "key_phrase", "")),
            "clf": str(r.gen_class_pred), "p": None if pd.isna(r.p_pathologic) else round(float(r.p_pathologic), 2),
            "imp": highlight(re.sub(r"\s+", " ", str(r.impression))[:2500]),
            "rep": highlight(re.sub(r"\s+", " ", str(r.reports))[:5000])})
    Path("results").mkdir(exist_ok=True)
    (RES / "gen_label_review.html").write_text(TEMPLATE.replace("/*CASES*/", json.dumps(cases)))
    print(f"wrote results/gen_label_review.html ({len(cases)} cases)")


TEMPLATE = r"""<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gen-slowing label review</title>
<style>
 body{font:15px/1.55 -apple-system,system-ui,sans-serif;margin:0;background:#0f1420;color:#e8eef7}
 .wrap{max-width:920px;margin:0 auto;padding:16px}
 .bar{position:sticky;top:0;background:#0f1420;padding:10px 0;border-bottom:1px solid #243049;z-index:5}
 .btns{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
 button{font:14px system-ui;padding:8px 12px;border-radius:8px;border:1px solid #2c3a57;background:#0000;color:#e8eef7;cursor:pointer}
 .b-ok{background:#12351f}.b-no{background:#3a1720}.b-path{background:#3a2417}.b-phys{background:#15243f}.b-norm{background:#12351f}.b-uns{background:#2a2a2a}
 .card{background:#141c2c;border:1px solid #243049;border-radius:12px;padding:14px;margin:12px 0}
 h2{font-size:.78rem;text-transform:uppercase;letter-spacing:.05em;color:#8798b3;margin:12px 0 6px}
 .imp{background:#0c1526;border-left:3px solid #4a90e2;padding:8px 10px;border-radius:6px;white-space:pre-wrap}
 .rep{white-space:pre-wrap;color:#cdd8ea;max-height:300px;overflow:auto;background:#0c1220;padding:8px 10px;border-radius:6px}
 mark{border-radius:3px;padding:0 2px;color:#0b0f17}
 .hl-imp-normal{background:#43e08a}.hl-abnormal{background:#ff6b7d}.hl-slowing{background:#f5b13a}
 .hl-drowsy{background:#6db1ff}.hl-side{background:#c58cff}.hl-band{background:#e0b060}
 .verdict{font-size:1.05rem}.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.8rem;margin-left:6px}
 .p-path{background:#3a2417;color:#f5b13a}.p-phys{background:#15243f;color:#6db1ff}.p-normal{background:#12351f;color:#43e08a}.p-unsure{background:#2a2a2a;color:#8798b3}
 .small{color:#8798b3;font-size:.82rem}.dis{color:#ff6b7d;font-weight:700}
</style>
<div class="wrap">
 <div class="bar">
   <b>Gen-slowing label review</b> <span id="prog" class="small"></span>
   <div class="btns">
     <button class="b-ok" onclick="agree()">✓ Agree (a)</button>
     <button class="b-path" onclick="fix('pathologic')">→ Pathologic (p)</button>
     <button class="b-phys" onclick="fix('physiologic')">→ Physiologic (h)</button>
     <button class="b-norm" onclick="fix('normal')">→ Normal (n)</button>
     <button class="b-uns" onclick="fix('unsure')">→ Unsure (u)</button>
     <button onclick="prev()">← Prev</button><button onclick="nxt()">Next →</button>
     <button onclick="dl()">⬇ Download review CSV</button>
   </div>
 </div>
 <div id="view"></div>
</div>
<script>
const CASES=/*CASES*/; const KEY='genrev_v1';
let R=JSON.parse(localStorage.getItem(KEY)||'{}');
let i=parseInt(localStorage.getItem(KEY+'_i')||'0');
const $=id=>document.getElementById(id);
function render(){const c=CASES[i];
 const dis=(c.clf&&c.clf!==c.llm)?`<span class="dis">simple-classifier says ${c.clf} (p=${c.p})</span>`:`<span class="small">classifier agrees (${c.clf} p=${c.p})</span>`;
 $('prog').textContent=`case ${i+1}/${CASES.length} · reviewed ${Object.keys(R).length} · id ${c.id}`;
 $('view').innerHTML=`<div class="card">
   <div class="verdict">LLM label: <span class="pill p-${c.llm}">${c.llm}</span> <span class="small">conf ${c.conf}</span> ${dis}</div>
   <div class="small" style="margin:6px 0"><b>rationale:</b> ${c.rationale} &nbsp; <b>key:</b> “${c.key}”</div>
   <h2>Impression</h2><div class="imp">${c.imp||'(none)'}</div>
   <h2>Full report</h2><div class="rep">${c.rep||'(none)'}</div>
   <div class="small" style="margin-top:8px">Your review: <b id="cur">${R[c.id]||'—'}</b></div></div>`;
}
function set(v){R[CASES[i].id]=v;localStorage.setItem(KEY,JSON.stringify(R));$('cur').textContent=v;nxt();}
function agree(){set('agree:'+CASES[i].llm);}
function fix(v){set('fix:'+v);}
function nxt(){i=Math.min(CASES.length-1,i+1);localStorage.setItem(KEY+'_i',i);render();}
function prev(){i=Math.max(0,i-1);localStorage.setItem(KEY+'_i',i);render();}
function dl(){let s='bdsp_id,llm_label,review\n';for(const c of CASES)if(R[c.id])s+=`${c.id},${c.llm},${R[c.id]}\n`;
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([s],{type:'text/csv'}));a.download='gen_label_review.csv';a.click();}
document.addEventListener('keydown',e=>{const m={a:()=>agree(),p:()=>fix('pathologic'),h:()=>fix('physiologic'),n:()=>fix('normal'),u:()=>fix('unsure')};
 if(m[e.key])m[e.key]();else if(e.key==='ArrowRight')nxt();else if(e.key==='ArrowLeft')prev();});
render();
</script>"""


if __name__ == "__main__":
    main()
