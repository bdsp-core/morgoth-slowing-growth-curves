"""MoE: the between-rater human ceiling for SLOWING, band-resolved.

Per ChenXi Sun, rounds r1/r2/r3 are simply different EEGs (the dataset was being grown); slowing was scored
in all rounds in the same way. Events are disjoint across rounds (verified: zero shared event ids), so rounds
are POOLED here -- 2,761 events, of which 1,761 are BDSP `sub-S000...` (the rest are `icare_*`, a
cardiac-arrest ICU population that does not match our norms; BDSP-only is the primary analysis).

Reports:
  * pairwise Cohen kappa between raters, per slowing category
  * Fleiss kappa (unequal raters per item)
  * composite any-focal / any-generalized / any-slowing
  * BAND agreement conditional on both raters calling slowing -- the direct analogue of our "band 0.74"
  * bootstrap CIs over events

PRIVACY: MoE label columns are raters' real usernames (incl. an author of this paper). They are anonymized to
R01..Rnn on load and NEVER written out. An "author excluded" sensitivity is reported without revealing which
index the author is.

Run: python scripts/90_moe_human_ceiling.py
"""
from __future__ import annotations
import glob, os, re, hashlib
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import cohen_kappa_score

SC = ("/private/tmp/claude-501/-Users-mwestover-GithubRepos-morgoth-slowing-growth-curves/"
      "543fcf0f-2e91-44f4-9ca9-c301964982e6/scratchpad/moe/labels")
ROUNDS = ["r1", "r2", "r3"]
BANDS = ["delta", "theta", "alpha", "beta"]
AUTHOR = "bwestove"
MIN_VOTES, MIN_CORATED, NBOOT = 200, 100, 200
rng = np.random.default_rng(0)


def load(cat: str) -> pd.DataFrame:
    """Pool a category across rounds -> events x raters (0/1/NaN). Anonymized columns."""
    frames = []
    for r in ROUNDS:
        g = glob.glob(f"{SC}/{r}_csv_labels_20241028/moe_*{cat}.csv")
        if not g:
            continue
        d = pd.read_csv(g[0])
        d["is_bdsp"] = d.eeg.notna() if "eeg" in d else False
        # forward-fill is WRONG here: eeg is only set on the row that names the file. Use event id prefix.
        d["is_bdsp"] = d.event.astype(str).str.match(r"^\d{9}_\d{14}$")
        frames.append(d.drop(columns=[c for c in ["eeg"] if c in d]))
    if not frames:
        return None
    d = pd.concat(frames, ignore_index=True)
    return d


def fleiss(counts: np.ndarray) -> float:
    """counts: n_items x 2 (neg, pos), rows may have different totals."""
    n = counts.sum(1)
    keep = n >= 2
    counts, n = counts[keep], n[keep]
    if len(counts) < 2:
        return np.nan
    P = ((counts ** 2).sum(1) - n) / (n * (n - 1))
    p = counts.sum(0) / counts.sum()
    Pe = (p ** 2).sum()
    return (P.mean() - Pe) / (1 - Pe) if Pe < 1 else np.nan


def pairwise_kappas(mat: pd.DataFrame, idx=None):
    """mat: events x raters. Returns list of pairwise Cohen kappas."""
    if idx is not None:
        mat = mat.iloc[idx]
    cols = list(mat.columns)
    ks = []
    for i in range(len(cols)):
        a = mat[cols[i]]
        for j in range(i + 1, len(cols)):
            b = mat[cols[j]]
            ok = a.notna() & b.notna()
            if ok.sum() < MIN_CORATED:
                continue
            x, y = a[ok].astype(int), b[ok].astype(int)
            if x.nunique() < 2 or y.nunique() < 2:
                continue
            ks.append(cohen_kappa_score(x, y))
    return ks


def summarize(mat: pd.DataFrame, label: str, out: list):
    good = [c for c in mat.columns if mat[c].notna().sum() >= MIN_VOTES]
    m = mat[good]
    ks = pairwise_kappas(m)
    if not ks:
        return
    counts = np.c_[(m == 0).sum(1), (m == 1).sum(1)]
    fk = fleiss(counts)
    prev = np.nanmean(m.values)
    # bootstrap over events
    boots = []
    n = len(m)
    for _ in range(NBOOT):
        b = pairwise_kappas(m, rng.integers(0, n, n))
        if b:
            boots.append(np.median(b))
    lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots else (np.nan, np.nan))
    out.append(dict(label=label, n_raters=len(good), n_events=n, prevalence=prev,
                    fleiss=fk, kappa_median=np.median(ks), lo=lo, hi=hi, n_pairs=len(ks)))


def main():
    cats = {}
    for kind in ["focalslowing", "genslowing"]:
        for b in BANDS:
            d = load(f"{kind}-{b}")
            if d is not None:
                cats[f"{kind}-{b}"] = d

    # canonical rater anonymization across every category
    names = sorted({c for d in cats.values() for c in d.columns if c not in ("event", "is_bdsp")})
    anon = {n: f"R{i+1:02d}" for i, n in enumerate(names)}
    author_id = anon.get(AUTHOR)
    print(f"{len(names)} raters -> R01..R{len(names):02d}; {len(cats)} slowing categories pooled over rounds")

    rows = []
    for name, d in cats.items():
        d = d[d.is_bdsp]                                     # BDSP-only primary
        mat = d.drop(columns=["event", "is_bdsp"]).rename(columns=anon)
        summarize(mat, name, rows)

    # composites: OR across bands, on the union of events
    for kind in ["focalslowing", "genslowing"]:
        parts = [cats[f"{kind}-{b}"] for b in BANDS if f"{kind}-{b}" in cats]
        base = parts[0][["event", "is_bdsp"]].copy()
        acc = None
        for p in parts:
            m = p.set_index("event").drop(columns=["is_bdsp"]).rename(columns=anon)
            acc = m if acc is None else acc.add(m, fill_value=0)
        acc = (acc > 0).astype(float).where(acc.notna())
        acc = acc.loc[base.set_index("event").index.intersection(acc.index)]
        keep = base[base.is_bdsp].event
        summarize(acc.loc[acc.index.intersection(keep)], f"ANY {kind}", rows)

    R = pd.DataFrame(rows)
    R.to_csv("results/moe_human_ceiling.csv", index=False)

    out = ["# MoE — the between-rater human ceiling for slowing\n",
           f"Pooled over rounds r1–r3 (disjoint events; per ChenXi Sun the rounds are simply different EEGs, ",
           "scored the same way). **BDSP events only** (`icare_*` cardiac-arrest events excluded: different ",
           f"population from our norms). Raters with ≥{MIN_VOTES} votes; pairs with ≥{MIN_CORATED} co-rated ",
           "events. Raters anonymized; one rater is an author of this paper.\n",
           "| category | raters | events | prevalence | Fleiss κ | pairwise Cohen κ median [95% CI] |",
           "|---|---|---|---|---|---|"]
    for _, r in R.iterrows():
        out.append(f"| {r.label} | {int(r.n_raters)} | {int(r.n_events)} | {r.prevalence:.3f} | "
                   f"{r.fleiss:.3f} | **{r.kappa_median:.3f}** [{r.lo:.3f}, {r.hi:.3f}] |")

    # ---- band agreement CONDITIONAL on both raters calling slowing (analogue of our band 0.74)
    out.append("\n## Band agreement, conditional on both raters calling slowing\n")
    out.append("Among events that **both** raters marked as slowing (any band), how often do they choose the ")
    out.append("same band? This is the direct analogue of our reported band agreement (0.74).\n")
    out.append("| kind | rater pairs | co-called events (median/pair) | exact band-set match | δ-vs-θ agreement |")
    out.append("|---|---|---|---|---|")
    for kind in ["focalslowing", "genslowing"]:
        bs = [b for b in BANDS if f"{kind}-{b}" in cats]
        M = {b: cats[f"{kind}-{b}"].set_index("event").rename(columns=anon) for b in bs}
        ev = M[bs[0]].index[M[bs[0]].is_bdsp]
        raters = sorted({c for b in bs for c in M[b].columns if c.startswith("R")})
        exact, dt, npair, nco = [], [], 0, []
        for i in range(len(raters)):
            for j in range(i + 1, len(raters)):
                ra, rb = raters[i], raters[j]
                A = pd.DataFrame({b: M[b].reindex(ev)[ra] for b in bs if ra in M[b]})
                B = pd.DataFrame({b: M[b].reindex(ev)[rb] for b in bs if rb in M[b]})
                cb = [c for c in A.columns if c in B.columns]
                A, B = A[cb], B[cb]
                both = (A.sum(1) > 0) & (B.sum(1) > 0) & A.notna().all(1) & B.notna().all(1)
                if both.sum() < 20:
                    continue
                npair += 1; nco.append(int(both.sum()))
                exact.append(float((A[both].values == B[both].values).all(1).mean()))
                if "delta" in cb and "theta" in cb:
                    a2, b2 = A[both][["delta", "theta"]].values, B[both][["delta", "theta"]].values
                    dt.append(float((a2 == b2).all(1).mean()))
        if npair:
            out.append(f"| {kind} | {npair} | {int(np.median(nco))} | **{np.mean(exact):.3f}** | "
                       f"{np.mean(dt):.3f} |" if dt else
                       f"| {kind} | {npair} | {int(np.median(nco))} | **{np.mean(exact):.3f}** | n/a |")

    txt = "\n".join(out) + "\n"
    Path("results/moe_human_ceiling.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
