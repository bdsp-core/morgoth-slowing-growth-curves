#!/usr/bin/env python3
"""SAP companion adapter #4 — per-segment sidecars for the deviation-field / severity / v4a chain,
streamed to bound memory (whole-recording 24h coverage => ~12M segments; SAP PITFALL 2).

  segment_features.parquet         per (eeg_id, region, segment): region = whole_head + 5 clinical regions
  segment_stages.parquet           per (eeg_id, segment): stage         (all recordings)
  segment_stages_abnormal.parquet  per (eeg_id, segment): stage         (is_abnormal recordings only)
  report_ordinals.parquet          per bdsp_id: rep_sev, rep_frq   (severity/freq adjective ordinals from manifest text; SAP §11 permits de-id text)
  v4a_report_flags.parquet         per bdsp_id: names_slowing, mentions_sleep_slowing   (from manifest text)

Region grain = 6 (not 18 channels) because the consumers (107 REGIONS, 86 FOCAL_REGIONS) only use those.
NEW-DATA-ONLY: segment_master + report_manifest_v6.
Run: PYTHONPATH=src python scratchpad/adapter_segment_tables.py
"""
import glob, re, sys
import numpy as np, pandas as pd
import pyarrow as pa, pyarrow.parquet as pq
sys.path.insert(0, "src")
from morgoth_slowing.features.recording import CH_NAMES, _AGG

REPO = "/Users/mbwest/Desktop/GithubRepos/morgoth-slowing-growth-curves"
SM = f"{REPO}/data/derived/segment_master"; DER = f"{REPO}/data/derived"
MAN = f"{REPO}/data/manifest/report_manifest_v6.parquet"
CHAN_REGION = {CH_NAMES[i]: reg for reg, ch in _AGG.items() if reg != "whole_head" for i in ch}
FEATS = ["log_delta", "log_theta", "log_alpha", "log_beta", "log_total", "rel_delta", "DAR", "TAR", "low_freq_rel"]


def region_seg(df):
    for r, l in [("DAR", "log_DAR"), ("TAR", "log_TAR")]:
        if l in df:
            df[r] = np.exp(df[l])
    parts = []
    dd = df.assign(region=df.channel.map(CHAN_REGION)).dropna(subset=["region"])
    g = dd.groupby(["segment", "region"], observed=True)[FEATS].median().reset_index()
    parts.append(g)
    wh = df.groupby("segment", observed=True)[FEATS].median().reset_index(); wh["region"] = "whole_head"
    parts.append(wh)
    return pd.concat(parts, ignore_index=True)


def build_segment_tables():
    man = pd.read_parquet(MAN).drop_duplicates("eeg_id").set_index("eeg_id")
    abn_ids = set(man.index[man.is_abnormal == 1])
    files = sorted(glob.glob(f"{SM}/eeg_id=*/part.parquet"))
    print(f"segment tables: {len(files)} recordings", flush=True)
    sf_writer = None
    stg_rows, abn_rows = [], []
    for i, f in enumerate(files):
        eid = f.split("eeg_id=")[1].split("/")[0]
        d = pd.read_parquet(f, columns=["segment", "channel", "stage", "artifact_flag",
                                        "log_delta", "log_theta", "log_alpha", "log_beta", "log_total",
                                        "rel_delta", "low_freq_rel", "log_DAR", "log_TAR"])
        # stage per segment (from any channel row)
        st = d.drop_duplicates("segment")[["segment", "stage"]].copy(); st["bdsp_id"] = eid
        stg_rows.append(st[["bdsp_id", "segment", "stage"]])
        if eid in abn_ids:
            abn_rows.append(st[["bdsp_id", "segment", "stage"]])
        d = d[d.artifact_flag == False]
        if d.empty:
            continue
        rs = region_seg(d); rs["bdsp_id"] = eid
        tbl = pa.Table.from_pandas(rs[["bdsp_id", "segment", "region"] + FEATS], preserve_index=False)
        if sf_writer is None:
            sf_writer = pq.ParquetWriter(f"{DER}/segment_features.parquet", tbl.schema)
        sf_writer.write_table(tbl)
        if (i + 1) % 2000 == 0:
            print(f"  {i+1}/{len(files)}", flush=True)
    sf_writer.close()
    pd.concat(stg_rows, ignore_index=True).to_parquet(f"{DER}/segment_stages.parquet", index=False)
    pd.concat(abn_rows, ignore_index=True).to_parquet(f"{DER}/segment_stages_abnormal.parquet", index=False)
    print(f"segment_features written; segment_stages {sum(len(x) for x in stg_rows):,} rows; "
          f"abnormal {sum(len(x) for x in abn_rows):,}", flush=True)


# ---- report text ordinals / flags from manifest (SAP §11: de-identified text may be used) ----
SEV = [("marked", 3), ("severe", 3), ("moderate", 2), ("mild", 1), ("slight", 1), ("minimal", 1)]
FRQ = [("continuous", 4), ("abundant", 4), ("frequent", 3), ("intermittent", 2),
       ("occasional", 1), ("rare", 1), ("infrequent", 1)]
SLOW_RE = re.compile(r"slow", re.I)
SLEEP_RE = re.compile(r"\b(sleep|drows|N2|N3|stage 2|stage 3|spindle|K.?complex)\b", re.I)
NEG_RE = re.compile(r"no\s+\w{0,12}slow|without\s+\w{0,12}slow|absence of\s+\w{0,12}slow", re.I)


def _ord(text, table):
    t = str(text).lower()
    best = 0
    for w, v in table:
        if w in t and SLOW_RE.search(t):
            best = max(best, v)
    return best


def build_text_tables():
    man = pd.read_parquet(MAN).drop_duplicates("eeg_id")
    txt = (man.report_text.fillna("") + " " + man.report_impression.fillna("")).astype(str)
    names_slow = txt.apply(lambda s: bool(SLOW_RE.search(s)) and not bool(NEG_RE.search(s)))
    # mentions_sleep_slowing = a slowing mention co-occurring with a sleep word (sentence-level approx)
    def sleep_slow(s):
        for sent in re.split(r"[.;\n]", str(s)):
            if SLOW_RE.search(sent) and SLEEP_RE.search(sent) and not NEG_RE.search(sent):
                return True
        return False
    mss = txt.apply(sleep_slow)
    v4a = pd.DataFrame({"bdsp_id": man.eeg_id, "date": man.eeg_datetime.astype(str).str[:8],
                        "names_slowing": names_slow.values, "mentions_sleep_slowing": mss.values})
    v4a.to_parquet(f"{DER}/v4a_report_flags.parquet", index=False)
    ordn = pd.DataFrame({"bdsp_id": man.eeg_id, "date": man.eeg_datetime.astype(str).str[:8],
                         "rep_sev": txt.apply(lambda s: _ord(s, SEV)).values,
                         "rep_frq": txt.apply(lambda s: _ord(s, FRQ)).values})
    ordn.to_parquet(f"{DER}/report_ordinals.parquet", index=False)
    print(f"v4a_report_flags {v4a.shape} (names_slowing={int(names_slow.sum())}, "
          f"sleep_slowing={int(mss.sum())}); report_ordinals {ordn.shape} "
          f"(sev>0={int((ordn.rep_sev>0).sum())}, frq>0={int((ordn.rep_frq>0).sum())})")


if __name__ == "__main__":
    build_segment_tables()
