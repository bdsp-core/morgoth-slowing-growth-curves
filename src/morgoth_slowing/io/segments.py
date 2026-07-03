"""Load Dr. Jing's Growth_curves .mat feature files.

Format (docs/data_dictionary.md): one file per recording,
`sub-<BDSP_ID>_<YYYYMMDDHHMMSS>.mat`, containing a table `res` with one row per 15-s segment:
  col0 sleep_stage (0=W,1=N1,2=N2,3=N3,4=REM,5=Other)
  col1 start, col2 end
  col3 feature array, 18 bipolar channels x 31 power features
"""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np
import pandas as pd

STAGE_MAP = {0: "W", 1: "N1", 2: "N2", 3: "N3", 4: "REM", 5: "Other"}
# sub-<PID>[_ses-<N>]_<YYYYMMDDHHMMSS>.<ext>  (session optional; .mat/.csv/etc.)
_FNAME_RE = re.compile(r"sub-(?P<pid>[A-Za-z0-9]+)(?:_ses-(?P<ses>[A-Za-z0-9]+))?_(?P<ts>\d{14})\.[A-Za-z0-9]+$")

# 31 feature names in array order (docs/data_dictionary.md). Verify tail ratios against read_me.txt.
FEATURE_NAMES = [
    "delta_power", "theta_power", "alpha_power", "beta_power", "gamma_power", "total_power",
    "delta/total", "theta/total", "alpha/total", "beta/total", "gamma/total",
    "delta/theta", "delta/alpha", "delta/beta", "delta/gamma",
    "theta/delta", "theta/alpha", "theta/beta", "theta/gamma",
    "alpha/delta", "alpha/theta", "alpha/beta", "alpha/gamma",
    "beta/delta", "beta/theta", "beta/alpha", "beta/gamma",
    "gamma/delta", "gamma/theta", "gamma/alpha", "gamma/beta",
]


def parse_filename(path) -> dict:
    """-> {bdsp_id, person_id, eeg_datetime(str YYYYMMDDHHMMSS)} from a Growth_curves filename."""
    m = _FNAME_RE.search(Path(path).name)
    if not m:
        raise ValueError(f"unexpected filename: {path}")
    return {"bdsp_id": m["pid"], "person_id": m["pid"], "session": m["ses"],
            "eeg_datetime": m["ts"]}


def load_mat(path) -> dict:
    """Load a Growth_curves .mat. Keys: res (n_seg x 4), age (int), channels (18),
    feature_names (31), res_hdr. NOTE: sleep stage is 'Other' (5) throughout this set."""
    from scipy.io import loadmat
    return loadmat(path, squeeze_me=True, struct_as_record=False)


def load_segments(path, channel_order=None) -> pd.DataFrame:
    """Tidy long DataFrame: one row per (segment, channel) with stage, start, end, age, features.

    Uses the file's *embedded* channels/feature_names (authoritative) unless channel_order given.
    Adds person_id, eeg_datetime (from filename) and age (from the file).
    """
    meta = parse_filename(path)
    mat = load_mat(path)
    res = mat["res"]
    age = int(mat["age"]) if "age" in mat and np.size(mat["age"]) else None
    chans = channel_order or [str(c) for c in np.atleast_1d(mat.get("channels", []))] or None
    fnames = [str(n).replace("-", "_") for n in np.atleast_1d(mat["feature_names"])] \
        if "feature_names" in mat else FEATURE_NAMES
    rows = []
    for seg in res:  # each row: [stage, start, end, 18x31 array]
        stage, start, end, feat = seg[0], seg[1], seg[2], np.asarray(seg[3], float)
        for ch in range(feat.shape[0]):
            rec = {"person_id": meta["person_id"], "eeg_datetime": meta["eeg_datetime"],
                   "age": age, "stage": STAGE_MAP.get(int(np.ravel(stage)[0]), "Other"),
                   "start": start, "end": end,
                   "channel": chans[ch] if chans else ch}
            rec.update(dict(zip(fnames, feat[ch])))
            rows.append(rec)
    return pd.DataFrame(rows)


def iter_label_dirs(root) -> "list[tuple[str, Path]]":
    """Yield (label, dir) for normal/focal_slow/general_slow under Growth_curves/features/."""
    feats = Path(root) / "features"
    return [(lbl, feats / lbl) for lbl in ("normal", "focal_slow", "general_slow")
            if (feats / lbl).is_dir()]


def load_metadata(config: dict, with_age: bool = True) -> pd.DataFrame:
    """Subject-level table: person_id, eeg_datetime, label, age, path.

    age is read from each .mat (fast: variable_names=['age']). SEX is not in the files —
    join from io.omop if sex-stratified curves are needed (see PLAN.md §2.1)."""
    from scipy.io import loadmat
    root = Path(config["data"]["local"]["raw"]) / "Growth_curves"
    rows = []
    for label, d in iter_label_dirs(root):
        for f in sorted(d.glob("sub-*.mat")):
            m = parse_filename(f)
            age = None
            if with_age:
                try:
                    a = loadmat(f, squeeze_me=True, variable_names=["age"]).get("age")
                    age = int(a) if a is not None and np.size(a) else None
                except Exception:
                    age = None
            rows.append({**m, "label": label, "age": age, "path": str(f)})
    return pd.DataFrame(rows)
