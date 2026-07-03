"""Age x sex percentile ("growth") curves via Gaussian-kernel weighted quantiles.

Non-parametric, robust, and smooth without hard age bins — good for v1 and as a QC baseline for any
later parametric (GAMLSS/quantile-regression) fit. Unit of analysis = recording (~1/patient).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

DEFAULT_PCTL = [3, 10, 25, 50, 75, 90, 97]


def weighted_quantile(values, weights, q):
    """Weighted quantile(s) q in [0,1] of values."""
    values = np.asarray(values, float); weights = np.asarray(weights, float)
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cw = np.cumsum(w) - 0.5 * w
    cw /= np.sum(w)
    return np.interp(np.atleast_1d(q), cw, v)


def curve(age, value, ages_grid, percentiles=DEFAULT_PCTL, bandwidth=5.0, min_eff_n=25.0):
    """Return DataFrame (age, n_eff, p{pctl}...) of kernel-weighted percentiles vs age."""
    age = np.asarray(age, float); value = np.asarray(value, float)
    ok = np.isfinite(age) & np.isfinite(value)
    age, value = age[ok], value[ok]
    qs = np.array(percentiles) / 100.0
    rows = []
    for a in ages_grid:
        w = np.exp(-0.5 * ((age - a) / bandwidth) ** 2)
        n_eff = w.sum() ** 2 / np.sum(w ** 2) if w.sum() > 0 else 0.0
        rec = {"age": a, "n_eff": n_eff}
        if w.sum() > 0 and n_eff >= min_eff_n:
            qv = weighted_quantile(value, w, qs)
            rec.update({f"p{p}": qv[i] for i, p in enumerate(percentiles)})
        else:
            rec.update({f"p{p}": np.nan for p in percentiles})
        rows.append(rec)
    return pd.DataFrame(rows)


def fit_by_sex(df, value_col, age_col="age", sex_col="sex",
               ages_grid=None, **kw):
    """Fit curves per sex. Returns tidy DataFrame with a `sex` column."""
    if ages_grid is None:
        ages_grid = np.arange(0, 91, 1.0)
    out = []
    for sex, g in df.groupby(sex_col):
        c = curve(g[age_col], g[value_col], ages_grid, **kw)
        c["sex"] = sex; c["feature"] = value_col
        out.append(c)
    return pd.concat(out, ignore_index=True)
