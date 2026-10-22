"""Import shim: `benchmarks/omr-ledger-extrapolation-2026-09` is not a package
name Python can import (hyphens), so the streamer is loaded by path.

⚠️ IMPORTED RATHER THAN RESTATED. The 443 MB Breitkopf record needs the
streaming reader that lane already paid for; a second copy of it here would be
free to drift from the one whose failure mode is documented.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_p = (Path(__file__).resolve().parent
      / "omr-ledger-extrapolation-2026-09" / "recordstream.py")
_spec = importlib.util.spec_from_file_location("_recordstream", _p)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
stream_array = _mod.stream_array
