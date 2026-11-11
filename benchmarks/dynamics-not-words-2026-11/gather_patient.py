"""ROADMAP 2.296 measurement control: `python3 -m tools.omr.staged` with a LONGER per-crop OCR deadline, the same for both arms.

    python3 benchmarks/dynamics-not-words-2026-11/gather_patient.py PDF --pages ... [every `tools.omr.staged` argument]

Three gathers from other lanes shared the machine, and `direction_text.DIRECTION_CROP_TIMEOUT_S` (20 s a crop) starved Surya in some arms ("worker silent for 20.0s": the crop falls
back to Tesseract and the arm's words, margin labels and bars change), so an OFF and an ON gather of the same page read different words and the file diff measured the OCR, not the flag.
This sets that one constant to 120 s in the process (no tool file is edited) and then runs the pipeline unchanged. On an idle machine the two behave identically: a crop that answers
in under 20 s is read the same way. Both arms of every comparison in this lane are gathered through this wrapper.
"""
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
import tools.omr.direction_text as DT  # noqa: E402

DT.DIRECTION_CROP_TIMEOUT_S = 120.0
sys.argv = ["tools.omr.staged"] + sys.argv[1:]
runpy.run_module("tools.omr.staged", run_name="__main__")
