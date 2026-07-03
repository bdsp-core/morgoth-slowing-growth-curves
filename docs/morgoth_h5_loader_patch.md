# Patch: make morgoth's H5 loader read lossless int16+gain storage

To roll out the space-saving int16 H5 cleanup (see source_data_cleanup_plan.md), morgoth's `_load_h5`
needs a **~3-line, backward-compatible** change: if a signal dataset carries `gain`/`offset` attrs
(int16 storage), reconstruct Volts as `digital*gain + offset`. Datasets without those attrs (today's
float64-Volt H5) are read exactly as before, so **no existing file breaks**.

Validated: int16-H5 reconstructs mne's Volts to **1.7e-18 V** (bit-exact) → morgoth inference is
byte-identical to the float64 path. Storage: **~0.13–0.27× the EDF** (vs float64-H5 ~1.6× the EDF).

## File(s) to change
- `morgoth2/infer_sleep_staging.py` → `_load_h5()` (and the equivalent reader in `morgoth-viewer`).

## Change (in the `for ch_name in src['signals']` loop)

```python
# BEFORE
for ch_name in src['signals']:
    arr   = src['signals'][ch_name][:, 0].astype(np.float64)  # V
    ...

# AFTER  (backward-compatible: applies only when gain/offset are present)
for ch_name in src['signals']:
    ds  = src['signals'][ch_name]
    arr = ds[:, 0].astype(np.float64)
    if 'gain' in ds.attrs:                                    # int16 digital -> Volts (lossless)
        arr = arr * float(ds.attrs['gain']) + float(ds.attrs['offset'])
    ...
```

That's the entire change. `gain`/`offset` are written by `morgoth_slowing.io.h5_int16.edf_to_h5_int16`
(gain/offset already folded to Volts, so no unit handling needed on read). Reference loader:
`morgoth_slowing.io.h5_int16.load_h5_int16`.

## Suggested rollout
1. Land this patch behind the existing reader (no-op for float64 files).
2. Run morgoth on a handful of recordings via **both** the float64-H5 and the int16-H5 of the same
   source → confirm identical predictions (guaranteed by the 1.7e-18 V reconstruction, but verify).
3. Then the cleanup can write int16-H5 as the archival format.
