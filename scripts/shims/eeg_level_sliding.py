"""Run Morgoth's EEG-level FOC/GEN heads over ARBITRARY SLICES of a window-probability matrix — with the
low-signal short-circuit DISABLED, so every slice gets a real forward pass and a real sigmoid.

WHY THIS EXISTS, AND WHY IT IS A SHIM
  * TWO-VENV RULE (docs/fleet_dependencies.md §4): the worker venv imports NEITHER torch NOR timm. Torch
    lives only in Morgoth's venv. So anything that touches a checkpoint must run under PILOT_VENV, in a
    subprocess — exactly like scripts/shims/eeg_level_wrap.py. An earlier draft of scripts/32 called torch
    directly from the worker and would have died on the fleet with a bare ImportError.
  * Morgoth's own EEG_level_head.py CLI cannot do what we need:
      - it SHORT-CIRCUITS to probability=0 with NO forward pass when the head's class column never exceeds
        1/3 (EEG_level_head.py:579,677) — that is where 20.6% of our p_focal zeros came from;
      - it PADS sequences under 30 rows with their own column means — fabricating input;
      - it only scores whole files, not sliding windows.
    So we import the model class and drive it ourselves. Nothing is thresholded, zeroed or padded.

CONTRACT (all arrays .npy, passed through a scratch dir so no torch object crosses the venv boundary)
  in : W.npy       float32 (T, 3)   the 1 s-step SLOWING softmax: class_0/1/2
       slices.npy  int64   (S, 2)   [lo, hi) row ranges. Caller guarantees hi-lo >= 30 (the CNN's floor)
  out: probs.npy   float32 (S, 2)   column 0 = P(focal), column 1 = P(generalized)  -- RAW sigmoids

Usage (from the worker, under PILOT_VENV):
    python eeg_level_sliding.py --scratch <dir> --ckpt-dir <morgoth2/checkpoints> [--batch 512]
"""
import argparse, os, sys

import numpy as np
import torch

MIN_ROWS = 30          # CNN reduces length 30x (MaxPool 10 then 3): under 30 rows -> 0 transformer tokens
HEADS = [("FOC_SLOWING_EEGlevel.pth", 1), ("GEN_SLOWING_EEGlevel.pth", 2)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--ckpt-dir", required=True)
    ap.add_argument("--batch", type=int, default=512)
    a = ap.parse_args()

    m2 = os.environ.get("MORGOTH2_DIR")
    if not m2:
        sys.exit("MORGOTH2_DIR is not set — the two-venv contract requires it")
    sys.path.insert(0, m2)
    try:
        torch.backends.mha.set_fastpath_enabled(False)     # same MPS guard as eeg_level_wrap.py
    except AttributeError:
        pass
    from EEG_level_head import CNNTransformerClassifier, load_model_parameters

    W = np.load(os.path.join(a.scratch, "W.npy")).astype(np.float32)
    sl = np.load(os.path.join(a.scratch, "slices.npy")).astype(np.int64)
    assert W.ndim == 2 and W.shape[1] == 3, f"W must be (T,3), got {W.shape}"
    if len(sl):
        assert (sl[:, 1] - sl[:, 0]).min() >= MIN_ROWS, "a slice is under the 30-row CNN floor"

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    out = np.full((len(sl), 2), np.nan, dtype=np.float32)

    for h, (ckpt, _class_idx) in enumerate(HEADS):
        model = CNNTransformerClassifier(input_dim=3, output_dim=1, pe_max_length=15000).to(dev)
        load_model_parameters(model, os.path.join(a.ckpt_dir, ckpt), device=torch.device(dev))
        model.eval()
        with torch.no_grad():
            for i in range(0, len(sl), a.batch):
                chunk = sl[i:i + a.batch]
                L = int((chunk[:, 1] - chunk[:, 0]).max())
                X = np.zeros((len(chunk), L, 3), dtype=np.float32)
                lens = np.zeros(len(chunk), dtype=np.int64)
                for j, (lo, hi) in enumerate(chunk):
                    seq = W[lo:hi]
                    X[j, :len(seq)] = seq          # zero-fill ONLY to square the batch; masked by `lengths`
                    lens[j] = len(seq)
                logits = model(torch.from_numpy(X).to(dev),
                               lengths=torch.from_numpy(lens).to(dev))
                # RAW sigmoid. No guard, no threshold, no zeroing. This is the whole point of the shim.
                out[i:i + len(chunk), h] = torch.sigmoid(logits).view(-1).float().cpu().numpy()
        del model
        if dev == "cuda":
            torch.cuda.empty_cache()

    np.save(os.path.join(a.scratch, "probs.npy"), out)
    print(f"eeg_level_sliding: {len(sl)} slices x 2 heads on {dev}; "
          f"focal[{np.nanmin(out[:,0]):.3f},{np.nanmax(out[:,0]):.3f}] "
          f"gen[{np.nanmin(out[:,1]):.3f},{np.nanmax(out[:,1]):.3f}]")


if __name__ == "__main__":
    main()
