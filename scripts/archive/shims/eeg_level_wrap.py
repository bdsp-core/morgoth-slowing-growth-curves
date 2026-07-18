"""Run morgoth2's EEG_level_head.py with the TransformerEncoder nested-tensor fast path DISABLED — it calls
torch._nested_tensor_from_mask_left_aligned, which fails on MPS with a padding mask (real multi-window
recordings). Scoped to the EEG-level head only (disabling it globally breaks the window head/stager).
See docs/fleet_dependencies.md §8. Usage: python eeg_level_wrap.py <EEG_level_head args...>

torch-version-robust: `set_fastpath_enabled` may be absent/renamed across torch versions (this repo's pin
is soft — see requirements.txt). If the API isn't present we continue: the crash is MPS-specific, so on the
CUDA fleet box the fast path typically works anyway. The smoke test (BOOTSTRAP) confirms the gate on the box."""
import os, sys, runpy
import torch
try:
    torch.backends.mha.set_fastpath_enabled(False)
except AttributeError:
    pass  # older/newer torch without this toggle; MPS-only crash, so CUDA is unaffected
os.chdir(os.environ["MORGOTH2_DIR"])
sys.argv[0] = "EEG_level_head.py"
runpy.run_path("EEG_level_head.py", run_name="__main__")
