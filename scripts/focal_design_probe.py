"""SCRATCH probe (do NOT commit / do NOT modify production 53/55/64/66).

Investigate how experts detect FOCAL slowing on Sandor_100 that our detector misses, and prototype
design changes: finer spatial focality, per-epoch/window selection with spatial persistence, state
(wake) conditioning, and purely-relative (domain-robust) contrasts.

Feature source = data/derived/segment_master (local, per (segment, channel), 18 bipolar). Labels =
FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx (majority + 14 experts). Eval = AUROC + % experts under
ROC (via scripts/46 expert_points + scripts/54 panel_curve).

Run: PYTHONPATH=src MPLBACKEND=Agg KMP_DUPLICATE_LIB_OK=TRUE python3 scripts/focal_design_probe.py <cmd>
"""
from __future__ import annotations
import os, sys, importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

# ---- house eval helpers ----
m54 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("m54", "scripts/54_single_model_train_eval.py"))
importlib.util.spec_from_file_location("m54", "scripts/54_single_model_train_eval.py").loader.exec_module(m54)
m46 = m54.m49.m46
Head = m54.Head; panel_curve = m54.panel_curve; expert_points = m46.expert_points

SM = "data/derived/segment_master"
SB_DIR = Path("/Users/mwestover/Library/CloudStorage/Box-Box/Brandon - DeID/0_People/ChenXiSun/ChenXiSun/"
              "Morgoth1/Datasets/Sandor_100"); MR = SB_DIR / "Morgoth_results"
CH = ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1", "Fp2-F8", "F8-T4", "T4-T6", "T6-O2",
      "Fp1-F3", "F3-C3", "C3-P3", "P3-O1", "Fp2-F4", "F4-C4", "C4-P4", "P4-O2", "Fz-Cz", "Cz-Pz"]
PAIRS = [("Fp1-F7", "Fp2-F8"), ("F7-T3", "F8-T4"), ("T3-T5", "T4-T6"), ("T5-O1", "T6-O2"),
         ("Fp1-F3", "Fp2-F4"), ("F3-C3", "F4-C4"), ("C3-P3", "C4-P4"), ("P3-O1", "P4-O2")]
# spatial neighbours (share an electrode) in the double-banana — for field/coherence tests
NBR = {c: [] for c in CH}
for a in CH:
    for b in CH:
        if a == b:
            continue
        ea = set(a.split("-")); eb = set(b.split("-"))
        if ea & eb:
            NBR[a].append(b)


# ---------- data ----------
def sb_keys():
    return sorted(Path(SM).glob("eeg_id=SB_*"), key=lambda p: int(p.name.split("=")[1].split("_")[1]))


def labels():
    ff = pd.read_excel(MR / "FocalSlowingOutput_Morgoth_ScoreAI_experts.xlsx")
    ff["key"] = ff.file_name.astype(str).str.strip()
    ec = [c for c in ff.columns if c.startswith("expert_")]
    return ff, ec


def ages():
    demo = pd.read_excel(SB_DIR / "validation_study_excel_export.xlsx", sheet_name="Demographics")
    return {str(r[demo.columns[0]]).strip(): float(r["age_years"]) for _, r in demo.iterrows()}


def load_sb(cols=("segment", "channel", "stage", "artifact_flag", "t_start_s",
                  "log_delta", "log_theta", "log_TAR", "log_DAR", "rel_delta", "log_total")):
    """dict eid -> raw per (segment,channel) frame (artifact-free)."""
    out = {}
    def one(p):
        eid = p.name.split("=")[1]
        try:
            d = pd.read_parquet(f"{p}/part.parquet", columns=list(cols))
        except Exception:
            return None
        d = d[~d.artifact_flag.astype(bool)]
        return eid, d
    with ThreadPoolExecutor(max_workers=12) as ex:
        for r in ex.map(one, sb_keys()):
            if r is not None:
                out[r[0]] = r[1]
    return out


def key_of(eid):
    return f"ID{int(eid.split('_')[1]):03d}"


def evalscore(y, s, wide, tag=""):
    ok = np.isfinite(s) & np.isfinite(y)
    pts = expert_points(wide)
    cur = panel_curve(None, y[ok], np.asarray(s)[ok], pts, "#000", "x")
    # experts' mean operating point + our sens at their mean spec
    espec = np.mean([1 - p["fpr"] for p in pts.values()]); esens = np.mean([p["tpr"] for p in pts.values()])
    fpr, tpr, _ = roc_curve(y[ok], np.asarray(s)[ok]); our_sens = float(np.interp(1 - espec, fpr, tpr))
    return dict(auc=cur["auc"], ur=cur["ur"], espec=espec, esens=esens, oursens=our_sens, n=int(ok.sum()))


def pr(tag, r):
    print(f"  {tag:44s} AUROC {r['auc']:.3f}  {r['ur']:5.0f}% under  "
          f"our-sens@expert-spec({r['espec']:.2f})={r['oursens']:.2f}  (exp-sens {r['esens']:.2f})")


# ---- current-head score (import the diagnostic's builders) ----
_DIAG = None
def diag():
    global _DIAG
    if _DIAG is None:
        _DIAG = importlib.util.module_from_spec(importlib.util.spec_from_file_location("dg", "scripts/sandor100_focal_diagnostic.py"))
        importlib.util.spec_from_file_location("dg", "scripts/sandor100_focal_diagnostic.py").loader.exec_module(_DIAG)
    return _DIAG


def current_head_score():
    """per-SB current focal-head score + merged labels; returns (m, yf, wide, ecols)."""
    dg = diag(); m55 = dg.m55; m54 = dg.m54
    S = pd.read_parquet("data/derived/single_model_segfeats.parquet")
    Rtr = m55.aggregate(S[S.dataset == "report"]); Rtr = Rtr[Rtr.split == "train"]
    sb = dg.sb_features()
    ff, ec = labels()
    gen = pd.read_excel(MR / "GenSlowingOutput_Morgoth_ScoreAI_experts.xlsx"); gen["key"] = gen.file_name.astype(str).str.strip()
    m = sb.merge(ff[["key", "S_pred", "M_pred", "majority"] + ec], on="key") \
          .merge(gen[["key", "majority"]].rename(columns={"majority": "gen_majority"}), on="key")
    cs = [c for c in dg.cols(("peak_", "foc_", "asym_")) if c in Rtr.columns and c in m.columns]
    med = Rtr[cs].median()
    h = m54.Head().fit(Rtr[cs].fillna(med).values, Rtr.y_focal.astype(int).values)
    m["hscore"] = h.score(m[cs].fillna(med).values)
    yf = m.majority.astype(int).values
    wide = m.set_index("key")[ec].apply(pd.to_numeric, errors="coerce")
    return m, yf, wide, ec


def cmd_errors():
    m, yf, wide, ec = current_head_score()
    m["nvote"] = m[ec].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    m["nrater"] = m[ec].apply(pd.to_numeric, errors="coerce").notna().sum(axis=1)
    m["vote_frac"] = m.nvote / m.nrater
    m["rank"] = m.hscore.rank(pct=True)
    pos = m[m.majority == 1].sort_values("hscore")
    neg = m[m.majority == 0].sort_values("hscore", ascending=False)
    print(f"\n=== FALSE NEGATIVES (focal+ by majority, LOW model score) — n_focal={len(pos)} ===")
    print(f"{'key':7s} {'votes':>7s} {'hscore':>7s} {'pctile':>6s} {'M_pred':>7s} {'S_pred':>7s}")
    for _, r in pos.iterrows():
        print(f"{r.key:7s} {int(r.nvote):2d}/{int(r.nrater):<2d}   {r.hscore:7.3f} {r['rank']*100:5.0f}% {r.M_pred:7.3f} {r.S_pred:7.3f}")
    print(f"\n=== FALSE POSITIVES (focal- by majority, HIGH model score) top 12 ===")
    print(f"{'key':7s} {'votes':>7s} {'hscore':>7s} {'pctile':>6s} {'gen+?':>5s}")
    for _, r in neg.head(12).iterrows():
        print(f"{r.key:7s} {int(r.nvote):2d}/{int(r.nrater):<2d}   {r.hscore:7.3f} {r['rank']*100:5.0f}%  {int(r.gen_majority)}")
    m.to_parquet(SCRATCH / "sb_head_scores.parquet")
    print(f"\nsaved -> {SCRATCH/'sb_head_scores.parquet'}")


def _render_panel(ax, data, sr, title, hl=None):
    from scipy.signal import butter, filtfilt, iirnotch
    BIP = ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1", "Fp2-F8", "F8-T4", "T4-T6", "T6-O2",
           "Fp1-F3", "F3-C3", "C3-P3", "P3-O1", "Fp2-F4", "F4-C4", "C4-P4", "P4-O2", "Fz-Cz", "Cz-Pz"]
    SP = 150.0
    idx = {n: i for i, n in enumerate(data[1])}
    mono = data[0]
    rows = [mono[idx[a]].astype(float) - mono[idx[b]].astype(float) for a, b in (p.split("-") for p in BIP)]
    d = np.asarray(rows); nyq = sr / 2
    bb, ab = butter(4, [1/nyq, 30/nyq], btype="band"); d = filtfilt(bb, ab, d, axis=-1)
    bn, an = iirnotch(60, 30, sr); d = filtfilt(bn, an, d, axis=-1)
    t = np.arange(d.shape[1]) / sr
    for i in range(d.shape[0]):
        col = "#c0392b" if (hl and BIP[i] in hl) else "#1a1a80"
        lw = 0.9 if (hl and BIP[i] in hl) else 0.5
        ax.plot(t, (d[i] - d[i].mean()) - i * SP, color=col, linewidth=lw, zorder=2)
    ax.set_yticks([-i * SP for i in range(len(BIP))])
    ax.set_yticklabels([f"{b} *" if (hl and b in hl) else b for b in BIP], fontsize=6.5)
    ax.set_xlim(0, t[-1]); ax.set_ylim(-(len(BIP) - 0.5) * SP, 0.7 * SP)
    ax.set_title(title, fontsize=8.5, fontweight="bold"); ax.set_xlabel("Time (s)", fontsize=8)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(left=False, labelsize=7)


def cmd_render():
    """Render the strong-consensus mislabel confirmations + a residual FP, with the focal channel highlighted."""
    import subprocess, tempfile
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from morgoth_slowing.io.edf import load_edf_referential
    ff, ec = labels()
    E = ff.set_index("key")[ec].apply(pd.to_numeric, errors="coerce")
    m = pd.read_parquet(SCRATCH / "sb_head_scores.parquet").set_index("key")
    # keys to show: (key, note)
    show = [("ID002", "11/11 experts FOCAL, majority-col=0"), ("ID048", "11/11 experts FOCAL, majority-col=0"),
            ("ID077", "0/11 experts, majority-col=1"), ("ID099", "10/11 experts FOCAL, majority-col=1 (ok)"),
            ("ID100", "1/11 experts, our head HIGH (residual FP)")]
    figdir = Path("figures/scratch"); figdir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, len(show), figsize=(4.3 * len(show), 7))
    for ax, (key, note) in zip(np.atleast_1d(axes), show):
        eid = f"SB_{int(key[2:]):03d}"
        d = pd.read_parquet(f"{SM}/eeg_id={eid}/part.parquet",
                            columns=["segment", "channel", "stage", "artifact_flag", "t_start_s", "log_delta"])
        d = d[~d.artifact_flag.astype(bool)]
        dw = d[d.stage == "W"]; dw = dw if len(dw) else d
        # focus channel = highest mean wake delta relative to its homolog
        cmean = dw.groupby("channel").log_delta.mean()
        focus = cmean.reindex(CH).idxmax()
        # best segment: focus-channel delta minus median-channel delta, max
        piv = dw.pivot_table(index="segment", columns="channel", values="log_delta", aggfunc="mean")
        if focus in piv:
            contrast = piv[focus] - piv.median(axis=1)
            seg = contrast.idxmax()
        else:
            seg = dw.segment.iloc[0]
        t0 = float(d[d.segment == seg].t_start_s.iloc[0])
        votes = int(E.loc[key].sum()); nr = int(E.loc[key].notna().sum())
        hs = float(m.loc[key, "hscore"]) if key in m.index else np.nan
        try:
            src = str(SB_DIR / "EDF" / f"ID-{int(key[2:]):03d}.edf")
            with tempfile.TemporaryDirectory() as td:
                loc = os.path.join(td, "r.edf"); subprocess.run(["cp", src, loc], check=True, timeout=180)
                arr, chs, fs = load_edf_referential(loc, max_hours=max(0.1, t0/3600 + 0.05))
            s = int(round(t0 * fs)); n = int(round(15 * fs)); s = min(s, arr.shape[0] - n)
            win = (arr[s:s+n].T, chs)
            title = f"{key}: {votes}/{nr} focal  our={hs:.2f}\n{note}\nfocus~{focus} @ {t0/60:.0f}min (W)"
            _render_panel(ax, win, fs, title, hl={focus})
        except Exception as e:
            ax.text(0.5, 0.5, f"{key}\nEEG unavailable\n{type(e).__name__}", ha="center", va="center", transform=ax.transAxes)
            print(f"{key}: {type(e).__name__}: {e}", flush=True)
    fig.suptitle("Ground-truth-independent check: raw EEG at the most-focal wake epoch "
                 "(focus channel from spectral map, red)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = figdir / "focal_mislabel_confirmation.png"; fig.savefig(out, dpi=140); plt.close(fig)
    print(f"wrote {out}")


def _rec_relative_feats(d, wake_only=True):
    """Purely-relative (within-recording, reference/scale/age-invariant) focal features from one recording's
    per-(segment,channel) frame. Returns dict of candidate scores."""
    if wake_only:
        dw = d[d.stage == "W"]
        d = dw if dw.segment.nunique() >= 4 else d          # fall back if too little wake
    out = {}
    for band in ("log_delta", "log_TAR"):
        piv = d.pivot_table(index="segment", columns="channel", values=band, aggfunc="mean")
        piv = piv.reindex(columns=[c for c in CH if c in piv.columns])
        if piv.shape[0] < 3 or piv.shape[1] < 8:
            continue
        med = piv.median(axis=1)
        # (1) finer per-channel focality: max channel - median channel, per segment -> p90 over segments
        foc = piv.max(axis=1) - med
        out[f"focp90_{band}"] = float(np.nanquantile(foc.dropna(), .9)) if foc.notna().any() else np.nan
        # (2) homologous-pair asymmetry: max |L-R| over pairs, per segment -> p90
        asym = []
        for L, R in PAIRS:
            if L in piv and R in piv:
                asym.append((piv[L] - piv[R]).abs())
        if asym:
            am = pd.concat(asym, axis=1).max(axis=1)
            out[f"asymp90_{band}"] = float(np.nanquantile(am.dropna(), .9))
        # (3) FIELD-COHERENT focality: focus + its neighbours elevated together (rejects single-channel artifact)
        fieldc = []
        for seg in piv.index:
            row = piv.loc[seg].dropna()
            if len(row) < 8:
                continue
            fch = row.idxmax()
            nb = [c for c in NBR[fch] if c in row.index]
            if not nb:
                continue
            fieldc.append(min(row[fch], row[nb].max()) - row.median())   # focus AND best-neighbour above median
        if fieldc:
            out[f"fieldp90_{band}"] = float(np.nanquantile(fieldc, .9))
        # (4) PERSISTENCE-gated focality: is the focus at the SAME channel across segments?
        argmax = piv.idxmax(axis=1).dropna()
        if len(argmax):
            modal = argmax.value_counts(normalize=True)
            persist = float(modal.iloc[0]); modal_ch = modal.index[0]
            out[f"persist_{band}"] = persist
            # median contrast at the persistent focus channel (only counts if it's consistently the focus)
            contrast_at_modal = (piv[modal_ch] - med).dropna()
            out[f"persistfoc_{band}"] = persist * float(np.nanmedian(contrast_at_modal)) if len(contrast_at_modal) else np.nan
    return out


def cmd_design():
    """Do the design levers (wake-conditioning, finer per-channel, field-coherence, persistence) separate
    expert-focal from non-focal at HIGH SPECIFICITY, evaluated against the CORRECT label? These are unsupervised
    single features (no training / no cross-domain fit), so any separation is domain-robust by construction."""
    ff, ec = labels()
    E = ff.set_index("key")[ec].apply(pd.to_numeric, errors="coerce")
    sb = load_sb()
    rows = []
    for eid, d in sb.items():
        k = key_of(eid)
        r_all = _rec_relative_feats(d, wake_only=False)
        r_wk = _rec_relative_feats(d, wake_only=True)
        row = {"key": k}
        row.update({f"all_{kk}": v for kk, v in r_all.items()})
        row.update({f"wk_{kk}": v for kk, v in r_wk.items()})
        rows.append(row)
    F = pd.DataFrame(rows).set_index("key")
    keep = F.index.intersection(E.index)
    F = F.loc[keep]; emaj = (E.loc[keep].mean(axis=1) >= 0.5).astype(int).values
    wide = E.loc[keep]
    print(f"\nn={len(F)}  focal(emaj)+={int(emaj.sum())}   [single unsupervised relative features vs CORRECT label]")
    print(f"{'feature':40s} AUROC  %under  sens@expertspec")
    res = []
    for c in F.columns:
        s = F[c].values
        ok = np.isfinite(s)
        if ok.sum() < 60 or np.unique(emaj[ok]).size < 2:
            continue
        r = evalscore(emaj[ok], s[ok], wide.iloc[ok])
        res.append((c, r["auc"], r["ur"], r["oursens"]))
    for c, au, ur, os_ in sorted(res, key=lambda x: -x[1]):
        star = " <-- wake" if c.startswith("wk_") else ""
        print(f"  {c:40s} {au:.3f}  {ur:4.0f}%   {os_:.2f}{star}")
    F.to_parquet(SCRATCH / "sb_relative_feats.parquet")


def cmd_roc():
    """Before/after figure: ROC of our head / Morgoth / SCORE-AI + expert operating points, evaluated
    against the misaligned `majority` column (left) vs the corrected expert-vote majority (right)."""
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    m, _, wide, ec = current_head_score()
    E = m.set_index("key")[ec].apply(pd.to_numeric, errors="coerce")
    emaj = (E.mean(axis=1) >= 0.5).astype(int).reindex(m.key.values).values
    maj = m.majority.astype(int).values
    pts = expert_points(wide)
    figdir = Path("figures/scratch"); figdir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6))
    for ax, y, ttl in [(axes[0], maj, "vs `majority` column (as used in prior experiments)"),
                       (axes[1], emaj, "vs expert-vote majority (CORRECTED)")]:
        ax.plot([0, 1], [0, 1], "--", color="#ccc", lw=1)
        for nm, s, c in [("our head", m.hscore.values, "#e6550d"), ("Morgoth", m.M_pred.values, "#6a3d9a"),
                         ("SCORE-AI", m.S_pred.values, "#2c7fb8")]:
            r = evalscore(y, s, wide); fpr, tpr, _ = roc_curve(y, s)
            ax.plot(fpr, tpr, color=c, lw=2.3, label=f"{nm} (AUROC {r['auc']:.2f}, {r['ur']:.0f}% under)")
        for p in pts.values():
            ax.plot(p["fpr"], p["tpr"], "o", ms=5, mfc="#999", mec="k", mew=.3, alpha=.75)
        ax.plot([], [], "o", mfc="#999", mec="k", label=f"{len(pts)} experts")
        ax.set_xlabel("1 - specificity"); ax.set_ylabel("sensitivity"); ax.set_title(ttl, fontsize=10)
        ax.legend(frameon=False, fontsize=8.5, loc="lower right"); ax.set_xlim(-.02, 1.02); ax.set_ylim(-.02, 1.02)
    fig.suptitle("Sandor_100 FOCAL slowing: the 'puzzle' is a ground-truth label bug "
                 "(23/100 labels misaligned)", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out = figdir / "focal_label_before_after_roc.png"; fig.savefig(out, dpi=150); plt.close(fig)
    print(f"wrote {out}")


def cmd_fusion():
    """Against the CORRECT label: is there residual design headroom over the current trained head?
    Compare current head, +homologous-asymmetry, and rank-fusion with the Morgoth foundation score."""
    m, _, wide, ec = current_head_score()
    E = m.set_index("key")[ec].apply(pd.to_numeric, errors="coerce")
    emaj = (E.mean(axis=1) >= 0.5).astype(int).reindex(m.key.values).values
    rel = pd.read_parquet(SCRATCH / "sb_relative_feats.parquet") if (SCRATCH/"sb_relative_feats.parquet").exists() else None
    m = m.set_index("key")
    asym = rel["all_asymp90_log_delta"].reindex(m.index) if rel is not None else pd.Series(np.nan, index=m.index)
    rk = lambda x: pd.Series(x, index=m.index).rank(pct=True)
    combos = {
        "current head (spectral, trained)": m.hscore.values,
        "homologous-asymmetry only (unsup)": asym.values,
        "head + asymmetry (rank-avg)": (rk(m.hscore.values) + rk(asym.values)).values,
        "head + Morgoth (rank-avg)": (rk(m.hscore.values) + rk(m.M_pred.values)).values,
        "head + asym + Morgoth (rank-avg)": (rk(m.hscore.values) + rk(asym.values) + rk(m.M_pred.values)).values,
        "Morgoth alone": m.M_pred.values,
    }
    print(f"\nn={len(m)}  focal(emaj)+={int(emaj.sum())}   [vs CORRECT label]")
    print(f"{'model':38s} AUROC  %under  sens@expertspec")
    for nm, s in combos.items():
        ok = np.isfinite(s)
        r = evalscore(emaj[ok], np.asarray(s)[ok], wide.iloc[ok] if hasattr(wide,'iloc') else wide)
        print(f"  {nm:38s} {r['auc']:.3f}  {r['ur']:4.0f}%   {r['oursens']:.2f}")


def cmd_relabel():
    """Re-evaluate our head + Morgoth + SCORE-AI against the CORRECTED label (expert-vote majority)
    vs the misaligned `majority` column that prior experiments used."""
    m, _, wide, ec = current_head_score()
    E = m.set_index("key")[ec].apply(pd.to_numeric, errors="coerce")
    emaj = (E.mean(axis=1) >= 0.5).astype(int).reindex(m.key.values).values
    maj = m.majority.astype(int).values
    print(f"\nprevalence: majority-col focal+={maj.sum()}   expert-vote-majority focal+={int(emaj.sum())}   disagree={int((maj!=emaj).sum())}/{len(m)}")
    print(f"\n{'score':26s} | {'vs majority-col':26s} | {'vs EXPERT-VOTE majority':26s}")
    for nm, s in [("our current head", m.hscore.values), ("Morgoth M_pred", m.M_pred.values), ("SCORE-AI S_pred", m.S_pred.values)]:
        rm = evalscore(maj, s, wide); re = evalscore(emaj, s, wide)
        print(f"{nm:26s} | AUROC {rm['auc']:.3f}  {rm['ur']:3.0f}% under | AUROC {re['auc']:.3f}  {re['ur']:3.0f}% under  (sens@{re['espec']:.2f}spec={re['oursens']:.2f})")
    print("\n(expert points are leave-one-out consensus of OTHER experts — unaffected by the label bug;")
    print(" only the model's own ROC y-label changes. exp-sens target ~0.71.)")


SCRATCH = Path("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
               "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "errors"
    globals()[f"cmd_{cmd}"]()
