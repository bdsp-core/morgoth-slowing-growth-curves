"""EDF -> morgoth-format H5 lossless source-data cleanup.

Implements the design in docs/source_data_cleanup_plan.md:

  * classify_file(raw)      -> 'scalp' | 'intracranial' | 'ambiguous'  (§1.1 file gate)
  * channel_usefulness(raw) -> per-channel {keep, reason, ...}          (§1.2/1.3)
  * edf_to_h5(edf, h5)      -> lossless morgoth H5 at NATIVE fs         (§2)
  * qc_reconstruction(edf,h5) / qc_stats(edf,h5)                        (§3 gates A/B)

Cardinal principle: never lose real signal. Uncertain channels are KEPT.
Intracranial (sEEG/iEEG/ECoG) files are left intact (skipped). No resampling,
no re-referencing, no filtering in the archival converter.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re

import numpy as np

CONVERTER_VERSION = "h5_convert/0.1.0-pilot"

# ---------------------------------------------------------------------------
# label normalization + canonical 10-20 sets (§1.1)
# ---------------------------------------------------------------------------

# canonical 10-20 (old T3/T5/T4/T6 and new T7/P7/T8/P8), normalized upper-case
_CANON_1020 = {
    "FP1", "F3", "C3", "P3", "F7", "T3", "T5", "O1", "FZ", "CZ", "PZ",
    "FP2", "F4", "C4", "P4", "F8", "T4", "T6", "O2",
    # new-nomenclature equivalents
    "T7", "P7", "T8", "P8",
}
# extended scalp positions that also count as scalp evidence
_SCALP_EXTRA = {
    "FPZ", "OZ", "NZ", "F9", "F10", "P9", "P10", "T1", "T2",
    "A1", "A2", "M1", "M2", "FC1", "FC2", "CP1", "CP2", "FC5", "FC6",
    "CP5", "CP6", "AF7", "AF8", "PO7", "PO8", "TP7", "TP8", "AF3", "AF4",
    "PO3", "PO4", "F5", "F6", "C5", "C6", "P5", "P6", "FT7", "FT8",
}
_SCALP_ALL = _CANON_1020 | _SCALP_EXTRA

# keep-list membership for non-EEG physiologic leads (§1.2)
_ECG = {"ECG", "EKG", "EKG1", "EKG2", "ECGL", "ECGR", "EKGL", "EKGR"}
_EOG = {"EOG", "LOC", "ROC", "E1", "E2", "LEOG", "REOG", "LEOG1", "REOG1"}
_EMG = {"EMG", "CHIN", "CHIN1", "CHIN2", "LAT", "RAT", "LAT1", "LAT2",
        "RAT1", "RAT2", "EMG1", "EMG2", "SUBMENTAL"}
# other physiologic leads worth keeping when present
_OTHER_PHYSIO = {"OSAT", "SPO2", "PLETH", "FLOW", "SNORE", "RESP", "ABDO",
                 "THOR", "CHEST", "AIRFLOW", "PR", "HR", "CO2"}

_INTRACRANIAL_TOKENS = ("SEEG", "ECOG", "DEPTH", "GRID", "STRIP")
# contact-style label: letter prefix + index, not a 10-20 name (e.g. LAH1, RER2, GRID12)
_CONTACT_RE = re.compile(r"^[A-Z]{1,4}\d{1,2}$")
# reference / bookkeeping suffixes stripped during normalization
_SUFFIX_RE = re.compile(r"-(REF|AVG|LE|A1|A2|M1|M2)$")


def normalize_label(name: str) -> str:
    """Uppercase, strip leading EEG/POL/REF token and trailing ref suffixes."""
    n = str(name).upper().strip()
    n = re.sub(r"^(EEG|POL|REF)\s+", "", n)   # leading modality token
    n = re.sub(r"^(EEG|POL|REF)-", "", n)
    n = _SUFFIX_RE.sub("", n)
    n = n.split("-")[0].strip()               # "C3-A1" -> "C3"
    n = re.sub(r"[\s.]+", "", n)
    # trailing bare reference tokens e.g. "C3A1"
    for suf in ("A1", "A2", "M1", "M2"):
        if n.endswith(suf) and n not in _CANON_1020 and len(n) > len(suf):
            n = n[: -len(suf)]
    return n


def _is_contact_style(norm: str) -> bool:
    if norm in _SCALP_ALL:
        return False
    return bool(_CONTACT_RE.match(norm))


def keep_list_category(norm: str) -> str | None:
    """Return keep-list category for a normalized label, or None if unlisted."""
    if norm in _SCALP_ALL:
        return "scalp_eeg"
    if norm in _ECG:
        return "ecg"
    if norm in _EOG:
        return "eog"
    if norm in _EMG:
        return "emg"
    if norm in _OTHER_PHYSIO:
        return "other_physio"
    return None


# ---------------------------------------------------------------------------
# §1.1 file-level scalp vs intracranial gate
# ---------------------------------------------------------------------------

def classify_file(raw):
    """Classify an mne Raw (or a list of channel labels) as scalp / intracranial /
    ambiguous. Returns dict {classification, n_1020, n_contact, n_channels, labels}."""
    labels = raw if isinstance(raw, (list, tuple)) else list(raw.ch_names)
    norms = [normalize_label(x) for x in labels]

    n_1020 = sum(1 for n in norms if n in _CANON_1020)
    n_contact = sum(1 for n in norms if _is_contact_style(n))
    has_token = any(any(t in n for t in _INTRACRANIAL_TOKENS) for n in norms)

    if n_1020 >= 8 and n_contact < n_1020:
        cls = "scalp"
    elif has_token or (n_contact >= 32 and n_1020 < 8):
        cls = "intracranial"
    else:
        cls = "ambiguous"

    return {
        "classification": cls,
        "n_1020": n_1020,
        "n_contact": n_contact,
        "n_channels": len(labels),
        "has_intracranial_token": has_token,
        "labels": list(labels),
    }


# ---------------------------------------------------------------------------
# §1.3 per-channel deadness detectors (work in µV on the full record)
# ---------------------------------------------------------------------------

def _bandpower(x, fs, lo, hi):
    from scipy.signal import welch
    nper = int(min(len(x), max(256, fs * 4)))
    if nper < 16:
        return 0.0
    f, pxx = welch(x, fs=fs, nperseg=nper)
    m = (f >= lo) & (f < hi)
    if not np.any(m):
        return 0.0
    return float(np.trapz(pxx[m], f[m]))


def hi_nyq(fs):
    return max(0.2, 0.5 * fs - 1e-6)


def _window_alive(w_uv, fs):
    """Does one probe window carry genuine (non-dead) signal? µV, finite samples."""
    if w_uv.size < max(8, int(0.5 * fs)):
        return False
    xmax, xmin = w_uv.max(), w_uv.min()
    if xmax == xmin:                              # constant window
        return False
    if max(np.mean(w_uv == xmax), np.mean(w_uv == xmin)) >= 0.20:  # railed (D4)
        return False
    if w_uv.size > 1 and np.mean(np.diff(w_uv) == 0) >= 0.999:     # flatline (D2)
        return False
    med = np.median(w_uv)
    mad = 1.4826 * np.median(np.abs(w_uv - med))
    if mad < 0.5 and float(w_uv.std()) < 0.5:    # near-zero variance (D3)
        return False
    return True


def _assess_channel(x_uv, fs, win_sec=10.0):
    """Windowed deadness assessment honoring 'never lose real signal': a channel is
    ALIVE if ANY probe window shows genuine signal. Returns
    (alive, hard_codes, active_mask, n_windows, n_alive) with active_mask marking the
    samples that belong to alive windows (used for duplicate co-activity)."""
    n = x_uv.size
    finite = np.isfinite(x_uv)
    active_mask = np.zeros(n, dtype=bool)
    if n == 0:
        return False, {"D1"}, active_mask, 0, 0

    w = max(1, int(round(win_sec * fs)))
    n_win = n_alive = 0
    alive = False
    for s in range(0, n, w):
        e = min(n, s + w)
        n_win += 1
        seg = x_uv[s:e]
        segf = seg[np.isfinite(seg)]
        if _window_alive(segf, fs):
            alive = True
            n_alive += 1
            active_mask[s:e] = finite[s:e]

    # aggregate HARD deadness reason (only meaningful when the channel is dead)
    hard = set()
    xf = x_uv[finite]
    nan_frac = 1.0 - finite.mean()
    if nan_frac >= 0.99 or xf.size < 8:
        hard.add("D1")
    else:
        if xf.size > 1 and np.mean(np.diff(xf) == 0) >= 0.999:
            hard.add("D2")
        med = np.median(xf)
        if 1.4826 * np.median(np.abs(xf - med)) < 0.5 and float(xf.std()) < 0.5:
            hard.add("D3")
        xmax, xmin = xf.max(), xf.min()
        if xmax != xmin and max(np.mean(xf == xmax), np.mean(xf == xmin)) >= 0.20:
            hard.add("D4")
    if not hard:                                  # dead but no specific code -> generic
        hard.add("D3")
    return alive, hard, active_mask, n_win, n_alive


def _soft_flags(x_uv, active_mask, fs):
    """Soft flags (D5 line-only, D7 DC-only) computed on the channel's ALIVE portion,
    so a railed-but-real electrode is judged on its genuine signal, not its plateaus."""
    soft = set()
    if not (fs and fs > 4):
        return soft
    x = x_uv[active_mask]
    x = x[np.isfinite(x)]
    if x.size <= 32:
        return soft
    total = _bandpower(x, fs, 0.5, 70.0)
    p_1_20 = _bandpower(x, fs, 1.0, 20.0)
    line = max(_bandpower(x, fs, f0 - 1, f0 + 1) for f0 in (50.0, 60.0))
    if total > 0 and (line / total) >= 0.8 and p_1_20 < 1.0:
        soft.add("D5")
    p_dc = _bandpower(x, fs, 0.0, 0.1)
    p_all = _bandpower(x, fs, 0.0, hi_nyq(fs))
    if p_all > 0 and (p_dc / p_all) >= 0.99:
        soft.add("D7")
    return soft


def channel_usefulness(raw, corr_thresh=0.999):
    """Per-channel keep/drop decision (§1.2/1.3).

    Returns dict: normalized_label -> {keep, reason, listed, category, flags, orig_label}.
    Keys are the *upper-cased normalized* labels used as H5 dataset names; on a name
    collision the first occurrence wins and later twins are marked duplicate.
    """
    labels = list(raw.ch_names)
    fs = float(raw.info["sfreq"])
    data = raw.get_data()  # (n_ch, n_samp) volts

    # first pass: windowed deadness assessment (keep-if-any-window-alive) + soft flags
    recs = []
    for i, lab in enumerate(labels):
        norm = normalize_label(lab)
        cat = keep_list_category(norm)
        listed = cat is not None
        x_uv = data[i] * 1e6
        alive, hard, active_mask, n_win, n_alive = _assess_channel(x_uv, fs)
        soft = _soft_flags(x_uv, active_mask, fs) if alive else set()
        recs.append({
            "orig_label": lab, "norm": norm, "category": cat, "listed": listed,
            "alive": alive, "hard": sorted(hard), "soft": sorted(soft),
            "n_win": n_win, "n_alive": n_alive, "active_mask": active_mask, "idx": i,
        })

    # second pass: D6 duplicate detection among ALIVE channels, correlating only over
    # samples where BOTH channels are active (so shared flat/rail plateaus can't fake a
    # duplicate). Only an UNLISTED redundant twin is dropped (soft flags never drop a
    # keep-listed lead — §1.3 unanimity rule).
    alive_idx = [r["idx"] for r in recs if r["alive"]]
    dup_of = {}  # idx -> idx it duplicates
    if len(alive_idx) > 1:
        min_common = int(10 * fs)
        for a_i in range(len(alive_idx)):
            ii = alive_idx[a_i]
            if ii in dup_of:
                continue
            for b_j in range(a_i + 1, len(alive_idx)):
                jj = alive_idx[b_j]
                if jj in dup_of:
                    continue
                common = recs[ii]["active_mask"] & recs[jj]["active_mask"]
                if common.sum() < min_common:
                    continue
                if np.array_equal(data[ii], data[jj]):
                    corr = 1.0
                else:
                    xi = data[ii][common]
                    xj = data[jj][common]
                    si, sj = xi.std(), xj.std()
                    if si == 0 or sj == 0:
                        continue
                    corr = abs(float(np.corrcoef(xi, xj)[0, 1]))
                if corr >= corr_thresh:
                    keep_one, drop_one = _prefer(recs[ii], recs[jj])
                    if not drop_one["listed"]:          # never drop a listed lead on D6
                        dup_of[drop_one["idx"]] = keep_one["idx"]

    # finalize decisions
    out = {}
    used_names = {}
    for r in recs:
        idx = r["idx"]
        listed, alive, hard, soft = r["listed"], r["alive"], r["hard"], r["soft"]
        if not alive:                               # dead everywhere -> drop (hard)
            keep, reason = False, "dropped:hard:" + "+".join(hard)
        elif idx in dup_of:                         # unlisted exact/near duplicate
            keep, reason = False, f"dropped:duplicate_of:{recs[dup_of[idx]]['norm']}"
        elif not listed and soft:                   # unlisted junk (line-/DC-only)
            keep, reason = False, "dropped:soft:" + "+".join(soft)
        elif listed and soft:
            keep, reason = True, "kept:review_soft:" + "+".join(soft)
        elif not listed:
            keep, reason = True, "kept:unknown_label_review"
        else:
            keep, reason = True, f"kept:listed:{r['category']}"

        name = r["norm"] or f"CH{idx}"
        # ensure unique dataset name for kept channels
        if keep and name in used_names:
            name = f"{name}_{idx}"
        used_names[name] = idx
        out[name] = {
            "keep": keep, "reason": reason, "listed": listed,
            "category": r["category"], "alive": alive,
            "flags": sorted(set(r["hard"]) | set(r["soft"])),
            "n_alive_windows": r["n_alive"], "n_windows": r["n_win"],
            "orig_label": r["orig_label"], "idx": idx,
        }
    return out


def _prefer(ri, rj):
    """Given two duplicate records, return (keep, drop) preferring the more
    standard/informative label (10-20 name > listed > raw reference)."""
    def rank(r):
        if r["norm"] in _CANON_1020:
            return 3
        if r["listed"]:
            return 2
        if r["norm"] in {"A1", "A2", "M1", "M2", "REF"}:
            return 0
        return 1
    return (ri, rj) if rank(ri) >= rank(rj) else (rj, ri)


# ---------------------------------------------------------------------------
# helpers: read EDF + hashing
# ---------------------------------------------------------------------------

def read_raw(edf_path, max_duration=None, verbose="ERROR"):
    """Read an EDF with mne (physical units, native fs). Optional crop to
    max_duration seconds (applied identically by converter and QC so QC stays exact)."""
    import mne
    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=verbose)
    if max_duration is not None:
        dur = raw.n_times / raw.info["sfreq"]
        if dur > max_duration:
            raw.crop(tmax=max_duration - 1.0 / raw.info["sfreq"])
    return raw


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()


def _iso_start(raw):
    m = raw.info.get("meas_date")
    if m is None:
        return ""
    if isinstance(m, _dt.datetime):
        return m.isoformat()
    return str(m)


# ---------------------------------------------------------------------------
# §2 converter
# ---------------------------------------------------------------------------

def edf_to_h5(edf_path, h5_path, max_duration=None, raw=None, decisions=None,
              classification=None, compression_opts=4):
    """Convert one scalp EDF to a morgoth-format H5, LOSSLESS at native fs.

    Writes signals/<NAME> shape (T,1) float64 in VOLTS (as mne returns), keeping
    only the useful channels, plus provenance attrs and a reserved annotations/ group.
    Returns a summary dict. Atomic (.tmp then rename)."""
    import h5py

    if raw is None:
        raw = read_raw(edf_path, max_duration=max_duration)
    if classification is None:
        classification = classify_file(raw)["classification"]
    if decisions is None:
        decisions = channel_usefulness(raw)

    fs = float(raw.info["sfreq"])
    data = raw.get_data()  # (n_ch, n_samp) volts
    labels = list(raw.ch_names)

    kept = {name: d for name, d in decisions.items() if d["keep"]}
    dropped = {d["orig_label"]: d["reason"] for name, d in decisions.items() if not d["keep"]}

    tmp = str(h5_path) + ".tmp"
    with h5py.File(tmp, "w") as h5:
        h5.attrs["sampling_rate"] = int(round(fs))
        h5.attrs["start_time"] = _iso_start(raw)
        h5.attrs["n_samples"] = int(data.shape[1])
        h5.attrs["duration_sec"] = float(data.shape[1] / fs)
        h5.attrs["source_edf"] = os.path.basename(str(edf_path))
        h5.attrs["source_edf_sha256"] = sha256_file(edf_path) if os.path.exists(edf_path) else ""
        h5.attrs["classification"] = classification
        h5.attrs["dropped_channels"] = json.dumps(dropped)
        h5.attrs["original_channels"] = json.dumps(labels)
        h5.attrs["converter_version"] = CONVERTER_VERSION
        h5.attrs["conversion_utc"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
        h5.attrs["conversion_params"] = json.dumps({
            "max_duration": max_duration, "resampled": False, "rereferenced": False,
            "filtered": False, "compression": "gzip", "compression_opts": compression_opts,
            "shuffle": True, "units": "V",
        })
        h5.attrs["plan_json"] = json.dumps({
            "keep": sorted(kept.keys()),
            "drop": {name: d["reason"] for name, d in decisions.items() if not d["keep"]},
        })

        g = h5.create_group("signals")
        for name, d in kept.items():
            v = data[d["idx"]].astype(np.float64).reshape(-1, 1)  # volts
            ds = g.create_dataset(name, data=v, compression="gzip",
                                  compression_opts=compression_opts, shuffle=True)
            ds.attrs["orig_label"] = d["orig_label"]
            ds.attrs["unit"] = "V"
            ds.attrs["fs"] = fs
            ds.attrs["keep_reason"] = d["reason"]
        h5.create_group("annotations")  # reserved, empty

    os.replace(tmp, h5_path)
    return {
        "n_in": len(labels), "n_kept": len(kept), "n_dropped": len(dropped),
        "kept": {n: d["reason"] for n, d in kept.items()},
        "dropped": dropped, "classification": classification,
    }


# ---------------------------------------------------------------------------
# §3 QC gates A & B
# ---------------------------------------------------------------------------

def _load_h5_signals(h5_path):
    import h5py
    out = {}
    with h5py.File(h5_path, "r") as h5:
        fs = float(h5.attrs["sampling_rate"])
        for name in h5["signals"]:
            ds = h5["signals"][name]
            out[name] = (np.asarray(ds[:, 0], dtype=np.float64),
                         ds.attrs.get("orig_label", name))
    return out, fs


def qc_reconstruction(edf_path, h5_path, max_duration=None, raw=None):
    """Gate A: per-kept-channel max-abs-diff & MSE between source EDF and H5 (in µV).
    Must be ~0. Returns {ok, per_channel, max_abs_diff_uv, max_mse_uv2, length_ok}."""
    if raw is None:
        raw = read_raw(edf_path, max_duration=max_duration)
    labels = list(raw.ch_names)
    data = raw.get_data()  # volts
    by_orig = {}
    for i, lab in enumerate(labels):
        by_orig.setdefault(lab, i)

    sig, _ = _load_h5_signals(h5_path)
    per = {}
    max_abs = 0.0
    max_mse = 0.0
    length_ok = True
    for name, (h5v, orig) in sig.items():
        i = by_orig.get(orig)
        if i is None:
            per[name] = {"error": f"orig_label {orig!r} not in EDF"}
            length_ok = False
            continue
        edf_uv = data[i] * 1e6
        h5_uv = h5v * 1e6
        if edf_uv.shape[0] != h5_uv.shape[0]:
            per[name] = {"error": "length_mismatch",
                         "n_edf": int(edf_uv.shape[0]), "n_h5": int(h5_uv.shape[0])}
            length_ok = False
            continue
        d = np.abs(edf_uv - h5_uv)
        mad = float(np.nanmax(d)) if d.size else 0.0
        mse = float(np.nanmean(d ** 2)) if d.size else 0.0
        per[name] = {"max_abs_diff_uv": mad, "mse_uv2": mse, "n": int(edf_uv.shape[0])}
        max_abs = max(max_abs, mad)
        max_mse = max(max_mse, mse)
    ok = length_ok and max_abs <= 1e-6 and max_mse <= 1e-12
    return {"ok": ok, "per_channel": per, "max_abs_diff_uv": max_abs,
            "max_mse_uv2": max_mse, "length_ok": length_ok}


def qc_stats(edf_path, h5_path, max_duration=None, raw=None, rtol_stat=1e-9,
             rtol_band=1e-6):
    """Gate B: per-channel mean/std/min/max/median + band-power parity (EDF vs H5)."""
    if raw is None:
        raw = read_raw(edf_path, max_duration=max_duration)
    labels = list(raw.ch_names)
    data = raw.get_data()
    fs = float(raw.info["sfreq"])
    by_orig = {}
    for i, lab in enumerate(labels):
        by_orig.setdefault(lab, i)

    sig, _ = _load_h5_signals(h5_path)
    bands = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13),
             "beta": (13, 30), "line60": (59, 61)}

    def _stats(x_uv):
        s = {"mean": float(np.nanmean(x_uv)), "std": float(np.nanstd(x_uv)),
             "min": float(np.nanmin(x_uv)), "max": float(np.nanmax(x_uv)),
             "median": float(np.nanmedian(x_uv))}
        xf = x_uv[np.isfinite(x_uv)]
        for bn, (lo, hi) in bands.items():
            s["bp_" + bn] = _bandpower(xf, fs, lo, hi) if xf.size > 16 else 0.0
        return s

    def _rel(a, b):
        denom = max(abs(a), abs(b), 1e-30)
        return abs(a - b) / denom

    per = {}
    worst_stat = 0.0
    worst_band = 0.0
    ok = True
    for name, (h5v, orig) in sig.items():
        i = by_orig.get(orig)
        if i is None:
            per[name] = {"error": "missing_in_edf"}
            ok = False
            continue
        se = _stats(data[i] * 1e6)
        sh = _stats(h5v * 1e6)
        rd = {k: _rel(se[k], sh[k]) for k in se}
        st = max(rd[k] for k in ("mean", "std", "min", "max", "median"))
        bd = max(rd[k] for k in rd if k.startswith("bp_"))
        worst_stat = max(worst_stat, st)
        worst_band = max(worst_band, bd)
        chan_ok = st <= rtol_stat and bd <= rtol_band
        ok = ok and chan_ok
        per[name] = {"stat_rel": st, "band_rel": bd, "ok": chan_ok}
    return {"ok": ok, "per_channel": per, "worst_stat_rel": worst_stat,
            "worst_band_rel": worst_band}
