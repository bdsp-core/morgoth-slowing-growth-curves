"use strict";
// EEG review viewer: double-banana canvas renderer + scoring logic. Vanilla JS, offline.

const BIPOLAR = ['Fp1-F7','F7-T3','T3-T5','T5-O1','Fp2-F8','F8-T4','T4-T6','T6-O2',
  'Fp1-F3','F3-C3','C3-P3','P3-O1','Fp2-F4','F4-C4','C4-P4','P4-O2','Fz-Cz','Cz-Pz'];
// display rows (clinical order); -1 = blank spacer between chains
const DISPLAY = [0,1,2,3, -1, 8,9,10,11, -1, 16,17, -1, 12,13,14,15, -1, 4,5,6,7];
const PX_PER_MM = 96 / 25.4;
const M = { L: 74, R: 16, T: 22, B: 26 };

const S = {                       // app state
  cases: [], idx: 0, rater: 'rater_1',
  sig: null, fs: 200, clipDur: 0, pageStart: 0,
  pageSec: 10, sens: 7,          // uV per mm
  hp: '1', lp: '70', notch: '60',
  blinded: false, source: 'generated', sentence: '', shown: '',
};

const $ = id => document.getElementById(id);
const qs = () => `hp=${S.hp}&lp=${S.lp}&notch=${S.notch}`;

// ---------------------------------------------------------------- rendering
function draw() {
  const cv = $('eeg'), wrap = $('canvaswrap');
  const W = Math.max(720, wrap.clientWidth);
  const nRows = DISPLAY.length;
  const H = M.T + M.B + nRows * 33;
  const dpr = window.devicePixelRatio || 1;
  cv.width = W * dpr; cv.height = H * dpr;
  cv.style.width = W + 'px'; cv.style.height = H + 'px';
  const ctx = cv.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H);
  const pL = M.L, pR = W - M.R, pW = pR - pL;
  const plotTop = M.T, plotBot = H - M.B, rowSp = (plotBot - plotTop) / nRows;
  if (!S.sig) return;

  const t0 = S.pageStart, t1 = t0 + S.pageSec;
  const i0 = Math.max(0, Math.floor(t0 * S.fs)), i1 = Math.floor(t1 * S.fs);
  const pxPerUv = PX_PER_MM / S.sens;
  const xAt = t => pL + ((t - t0) / S.pageSec) * pW;

  // vertical 1 s gridlines + time labels
  ctx.strokeStyle = '#e3e3e3'; ctx.lineWidth = 1; ctx.fillStyle = '#888';
  ctx.font = '10px monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  for (let s = Math.ceil(t0); s <= t1 + 1e-6; s++) {
    const x = xAt(s); ctx.beginPath(); ctx.moveTo(x, plotTop); ctx.lineTo(x, plotBot); ctx.stroke();
    ctx.fillText(s.toFixed(0) + 's', x, plotBot + 4);
  }

  // traces
  ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
  for (let r = 0; r < nRows; r++) {
    const ch = DISPLAY[r]; if (ch < 0) continue;
    const yC = plotTop + rowSp * (r + 0.5);
    ctx.fillStyle = '#333'; ctx.font = '11px monospace';
    ctx.fillText(BIPOLAR[ch], pL - 6, yC);
    const tr = S.sig[ch], clampPx = rowSp * 1.3;
    ctx.strokeStyle = '#1a3a6d'; ctx.lineWidth = 0.7; ctx.beginPath();
    let first = true;
    for (let i = i0; i < i1 && i < tr.length; i++) {
      const x = pL + ((i / S.fs - t0) / S.pageSec) * pW;
      let dy = tr[i] * pxPerUv; if (dy > clampPx) dy = clampPx; if (dy < -clampPx) dy = -clampPx;
      const y = yC - dy;
      if (first) { ctx.moveTo(x, y); first = false; } else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  // calibration bar (bottom-left): sensitivity * (10 mm) uV vertical, 1 s horizontal
  const calUv = Math.round(S.sens * 10), calY = plotBot - 6, calX = pL + 6;
  const secPx = pW / S.pageSec;   // width of 1 second
  ctx.strokeStyle = '#b4453e'; ctx.lineWidth = 1.4; ctx.beginPath();
  ctx.moveTo(calX, calY - calUv * pxPerUv); ctx.lineTo(calX, calY); ctx.lineTo(calX + secPx, calY);
  ctx.stroke();
  ctx.fillStyle = '#b4453e'; ctx.font = '10px monospace'; ctx.textAlign = 'left'; ctx.textBaseline = 'bottom';
  ctx.fillText(`${calUv}µV / 1s`, calX + 4, calY - 2);
}

// ---------------------------------------------------------------- data flow
async function loadCaseList() {
  const r = await fetch(`/api/cases?rater=${encodeURIComponent(S.rater)}`);
  const j = await r.json();
  S.cases = j.cases; S.blinded = j.blinded;
  updateProgress();
  let start = S.cases.findIndex(c => !c.done);
  S.idx = start < 0 ? 0 : start;
  await loadCase();
}

async function loadSignal() {
  $('loading').textContent = 'filtering…';
  const c = S.cases[S.idx];
  const r = await fetch(`/api/signal?case_id=${c.case_id}&${qs()}`);
  const j = await r.json();
  S.sig = j.data; S.fs = j.fs;
  S.clipDur = j.data[0].length / j.fs;
  const scrub = $('scrub'); scrub.max = Math.max(0, S.clipDur - S.pageSec).toFixed(1);
  if (S.pageStart > scrub.max) S.pageStart = 0;
  $('loading').textContent = '';
  draw();
}

async function loadSentence() {
  const c = S.cases[S.idx];
  if (S.mode === 'case2') { renderCase2(c); return; }
  const r = await fetch(`/api/sentence?case_id=${c.case_id}&rater=${encodeURIComponent(S.rater)}`);
  const j = await r.json();
  S.sentence = j.sentence; S.shown = j.sentence; S.source = j.source;
  $('sentence').textContent = j.sentence;
  $('stratum').textContent = S.blinded ? '' : (c.stratum || '');
}

// ---- case-2 morphology review: show the numbers, ask for one of 4 labels + notes ----
async function setupCase2() {
  const r = await fetch('/api/config'); const cfg = await r.json();
  S.mode = cfg.mode; S.verdicts = cfg.verdicts || []; S.caseFields = cfg.case_fields || [];
  if (S.mode !== 'case2') return;
  $('paneltitle').innerHTML = 'Case-2 adjudication: Morgoth + report say generalized slowing, our field measured nothing &mdash; <b>why?</b> <span id="stratum" class="tag"></span>';
  $('verdictrow').innerHTML = S.verdicts.map((v, i) =>
    `<button class="c2btn" data-v="${v}">${v} <span class="k">${i + 1}</span></button>`).join(' ')
    + ' <span id="verdictState" class="muted"></span>';
  $('sentence').innerHTML = '<div id="c2fields" class="small"></div>';
  const eb = $('editbox'); eb.hidden = false;
  const m = eb.querySelector('.muted'); if (m) m.textContent = 'Notes (optional): morphology seen (FIRDA/GRDA runs?) or why the model missed it.';
  document.querySelectorAll('.c2btn').forEach(b => b.onclick = () => saveCase2(b.dataset.v));
}

function renderCase2(c) {
  const f = c.fields || {};
  const fmt = (k) => (typeof f[k] === 'number' ? f[k].toFixed(k === 'age' ? 0 : 2) : f[k]);
  const labels = { age: 'age', dominant_stage: 'STAGE (ours)', stage_mix: 'stage mix',
    report_gen_band: 'report band', amount_median: 'our amount (SD)', amount_p90: 'our p90 (SD)',
    prevalence: 'our prevalence', p_generalized: 'Morgoth p(gen)' };
  const el = $('c2fields'); if (el) el.innerHTML = S.caseFields.map(k =>
    `<span class="c2f"><b>${labels[k] || k}</b>: ${fmt(k)}</span>`).join(' &nbsp;&middot;&nbsp; ');
  if ($('stratum')) $('stratum').textContent = c.stratum || '';
  document.querySelectorAll('.c2btn').forEach(b => b.classList.toggle('sel', c.verdict === b.dataset.v));
  if ($('verdictState')) $('verdictState').textContent = c.done ? ('✓ ' + c.verdict) : 'not yet scored';
  if ($('edit')) $('edit').value = c.edited_text || '';
}

async function saveCase2(verdict) {
  if (await save(verdict, $('edit').value.trim())) {
    document.querySelectorAll('.c2btn').forEach(b => b.classList.toggle('sel', verdict === b.dataset.v));
    setTimeout(nextCase, 250);
  }
}

async function loadCase() {
  S.pageStart = 0;
  const c = S.cases[S.idx];
  $('pos').textContent = `${S.idx + 1} / ${S.cases.length}`;
  showVerdict(c);
  await Promise.all([loadSignal(), loadSentence()]);
  // restore prior edit text if this case was marked not_accurate
  $('edit').value = c.edited_text || '';
  $('editbox').hidden = !(c.verdict === 'not_accurate');
}

function showVerdict(c) {
  if (S.mode === 'case2') return;   // case2 verdict state is set in renderCase2
  $('btnAcc').classList.toggle('sel', c.verdict === 'accurate');
  $('btnNot').classList.toggle('sel', c.verdict === 'not_accurate');
  $('verdictState').textContent = c.done
    ? (c.verdict === 'accurate' ? '✓ accurate' : '✎ corrected') : 'not yet scored';
}

function updateProgress() {
  const n = S.cases.filter(c => c.done).length, tot = S.cases.length;
  $('cnt').textContent = `${n} / ${tot} scored`;
  $('fill').style.width = tot ? (100 * n / tot) + '%' : '0';
}

async function save(verdict, editedText) {
  const c = S.cases[S.idx];
  const body = { case_id: c.case_id, rater_id: S.rater, verdict,
    shown_sentence: S.shown, edited_text: editedText || '', source: S.source };
  const r = await fetch('/api/save', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!r.ok) { flash('save FAILED'); return false; }
  c.done = true; c.verdict = verdict; c.edited_text = editedText || '';
  updateProgress(); showVerdict(c); flash('saved');
  return true;
}

function flash(m) { const s = $('status'); s.textContent = m; setTimeout(() => s.textContent = '', 900); }

function nextCase() { if (S.idx < S.cases.length - 1) { S.idx++; loadCase(); } }
function prevCase() { if (S.idx > 0) { S.idx--; loadCase(); } }
function pageBy(n) {
  const max = Math.max(0, S.clipDur - S.pageSec);
  S.pageStart = Math.min(max, Math.max(0, S.pageStart + n * S.pageSec));
  $('scrub').value = S.pageStart; draw();
}

async function onAccurate() { if (await save('accurate', '')) { $('editbox').hidden = true; setTimeout(nextCase, 250); } }
function onNotAccurate() {
  const c = S.cases[S.idx];
  $('editbox').hidden = false;
  if (!$('edit').value) $('edit').value = c.edited_text || S.sentence;
  $('edit').focus();
}
async function onSaveEdit() { if (await save('not_accurate', $('edit').value.trim())) setTimeout(nextCase, 250); }

// ---------------------------------------------------------------- wiring
function initControls() {
  $('rater').value = localStorage.getItem('rater') || S.rater;
  S.rater = $('rater').value;
  $('rater').addEventListener('change', e => {
    S.rater = e.target.value.trim() || 'rater_1';
    localStorage.setItem('rater', S.rater); loadCaseList();
  });
  $('prevCase').onclick = prevCase; $('nextCase').onclick = nextCase;
  $('prevPage').onclick = () => pageBy(-1); $('nextPage').onclick = () => pageBy(1);
  $('scrub').addEventListener('input', e => { S.pageStart = parseFloat(e.target.value); draw(); });
  $('timebase').addEventListener('change', e => { S.pageSec = parseFloat(e.target.value); pageBy(0); });
  $('sens').addEventListener('change', e => { S.sens = parseFloat(e.target.value); draw(); });
  for (const f of ['hp', 'lp', 'notch'])
    $(f).addEventListener('change', e => { S[f] = e.target.value; loadSignal(); });
  if ($('btnAcc')) { $('btnAcc').onclick = onAccurate; $('btnNot').onclick = onNotAccurate; }
  if ($('btnSave')) $('btnSave').onclick = onSaveEdit;
  window.addEventListener('resize', draw);

  document.addEventListener('keydown', e => {
    const t = e.target.tagName;
    if (t === 'TEXTAREA') { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); onSaveEdit(); } return; }
    if (t === 'INPUT' || t === 'SELECT') return;
    if (S.mode === 'case2') {
      const i = parseInt(e.key, 10) - 1;
      if (i >= 0 && i < S.verdicts.length) { e.preventDefault(); saveCase2(S.verdicts[i]); return; }
    }
    if (e.key === '1') onAccurate();
    else if (e.key === '2') onNotAccurate();
    else if (e.key === 'ArrowLeft') { e.preventDefault(); e.shiftKey ? prevCase() : pageBy(-1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); e.shiftKey ? nextCase() : pageBy(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); stepSens(-1); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); stepSens(1); }
  });
}
function stepSens(dir) {
  const opts = [...$('sens').options].map(o => o.value);
  let i = opts.indexOf(String(S.sens)) + dir;
  i = Math.max(0, Math.min(opts.length - 1, i));
  $('sens').value = opts[i]; S.sens = parseFloat(opts[i]); draw();
}

initControls();
setupCase2()
  .then(loadCaseList)
  .catch(e => { $('sentence').textContent = 'load error: ' + e; });
