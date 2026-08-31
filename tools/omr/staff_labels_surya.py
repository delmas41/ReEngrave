"""Read instrument labels off the page margin with Surya 2 — the free tier.

Three readers now sit under one question, "which instrument is this staff", and
they differ only in what they cost:

    staff_labels.read_staff_labels          PDF text layer   free, 18 of 65 PDFs
    staff_labels_surya.read_staff_labels_surya   Surya 2     free, needs a venv
    staff_labels_vision.read_staff_labels_vision  Claude     ~1 cent a system

`contextual._labels_for_page` runs them in that order and only pays when the
free ones come back empty.

## Why this is worth a rung of its own

Measured 2026-08-31 on the same crops and the same free ground truth as the
paid reader (`benchmarks/omr-margin-labels-2026-08/SURYA_BAKEOFF_2026-08-31.md`):
Surya and Claude both scored **zero disagreements** against the text layer, and
Surya resolved 49 staves to Claude's 55 — 89% of the yield, for nothing, locally,
at about 1.5 s a system against roughly a cent.

So this is not a worse reader that happens to be free. On everything the ground
truth can check it is exactly as accurate; what it gives up is a little reach.

## What it cannot do, and why the paid rung stays

Claude repairs a damaged label from the running order — it reads a clipped
"arinetti" as Clarinetti because Fl./Ob. sit above it. Surya transcribes what is
in the image and the lexicon then rejects the fragment. Widening the crop
(`MARGIN_SPACINGS`, 14 -> 20) removed most of that, but the asymmetry is
structural: an OCR engine reads, a vision model reads *and infers*.

## Setup

    python3 -m tools.omr.staff_labels_surya --bootstrap    # makes .venv-surya
    brew install llama.cpp                                 # the CPU backend

Surya auto-spawns the llama.cpp server and pulls a 650M GGUF on first use.
Everything is host-side: the backend container has no Node for the Maestro
bridge and it has no Surya either, by the same personal-use logic.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .instruments import lookup
from .staff_labels import StaffLabel
from .staff_labels_vision import MarginCrop, build_margin_crop
from .types import PageWithStaves, Staff

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKER = Path(__file__).resolve().parent / "_surya_worker.py"

#: Where `--bootstrap` puts the venv, and where the bridge looks for it.
VENV_DIR = _REPO_ROOT / ".venv-surya"

REQUIREMENT = "surya-ocr>=0.22"

#: Generous because the FIRST call pays for spawning llama.cpp and loading a
#: 650M GGUF — about 70 s — while each system after it takes ~1.5 s.
DEFAULT_TIMEOUT_S = float(os.environ.get("OMR_SURYA_TIMEOUT_S", "900"))


class SuryaLabelError(RuntimeError):
    """The reader could not run — bad input, or the venv is missing."""


def interpreter() -> Path:
    """The Python that has surya, or an error saying how to make one."""
    override = os.environ.get("OMR_SURYA_PYTHON")
    for candidate in ([Path(override)] if override else []) + [VENV_DIR / "bin" / "python"]:
        if candidate.is_file():
            return candidate
    raise SuryaLabelError(
        "no surya interpreter found.\n"
        f"  expected: {VENV_DIR / 'bin' / 'python'}\n"
        "  create it with: python3 -m tools.omr.staff_labels_surya --bootstrap\n"
        "  and install the CPU backend: brew install llama.cpp\n"
        f"  or point OMR_SURYA_PYTHON at a Python >= 3.10 with {REQUIREMENT!r}."
    )


def available() -> bool:
    """True when the free reader can run — callers degrade rather than fail."""
    try:
        interpreter()
    except SuryaLabelError:
        return False
    return True


def _base_python_for_venv() -> str:
    for minor in range(14, 9, -1):
        found = shutil.which(f"python3.{minor}")
        if found:
            return found
    raise SuryaLabelError(
        "no Python >= 3.10 on PATH; surya-ocr requires it (the host's is 3.9). "
        "Install one, e.g. `brew install python@3.13`."
    )


def bootstrap(*, force: bool = False) -> Path:
    """Create `.venv-surya` and install surya-ocr into it."""
    python = VENV_DIR / "bin" / "python"
    if python.is_file() and not force:
        return python
    base = _base_python_for_venv()
    subprocess.run([base, "-m", "venv", str(VENV_DIR)], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--quiet",
                    "--upgrade", "pip"], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--quiet",
                    REQUIREMENT], check=True)
    if not shutil.which("llama-server"):
        logger.warning("surya venv is ready but llama.cpp is not installed; "
                       "run `brew install llama.cpp` before reading a page")
    return python


def read_crops_surya(crops: list[MarginCrop], *,
                     timeout_s: float | None = None) -> list[dict[int, str]]:
    """`{staff_index: printed label}` per crop, in one subprocess.

    One process for every crop on the page on purpose: the model load dominates
    and is paid once.
    """
    if not crops:
        return []
    job = {"systems": [{
        "png_b64": base64.standard_b64encode(crop.png).decode("ascii"),
        "staff_indices": list(crop.staff_indices),
        "tick_ys": list(crop.tick_ys),
        "gutter_px": crop.gutter_px,
    } for crop in crops]}

    python = interpreter()
    try:
        proc = subprocess.run(
            [str(python), str(_WORKER)],
            input=json.dumps(job), capture_output=True, text=True,
            timeout=timeout_s if timeout_s is not None else DEFAULT_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise SuryaLabelError(f"surya timed out after {exc.timeout}s") from exc

    if proc.returncode != 0 and not proc.stdout.strip():
        raise SuryaLabelError(
            f"surya worker failed (exit {proc.returncode}):\n"
            f"{proc.stderr.strip()[-2000:]}"
        )
    try:
        payload: dict[str, Any] = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SuryaLabelError(
            "surya worker returned non-JSON:\n"
            f"stdout: {proc.stdout.strip()[:400]}\n"
            f"stderr: {proc.stderr.strip()[-1200:]}"
        ) from exc
    if "error" in payload:
        raise SuryaLabelError(payload["error"])

    out: list[dict[int, str]] = []
    for entry in payload.get("systems", []):
        if entry.get("error"):
            logger.warning("surya failed on one system: %s", entry["error"])
            out.append({})
            continue
        out.append({int(k): v for k, v in (entry.get("labels") or {}).items()})
    return out


def read_staff_labels_surya(pws: PageWithStaves, *,
                            timeout_s: float | None = None) -> list[StaffLabel]:
    """Instrument labels for a page, read from the margin with Surya.

    Same return shape as `staff_labels.read_staff_labels` and
    `staff_labels_vision.read_staff_labels_vision`, so the three are
    interchangeable and a caller can fall through free -> free -> paid.
    """
    by_system: dict[int, list[Staff]] = {}
    for staff in sorted(pws.staves, key=lambda s: s.top_y):
        by_system.setdefault(staff.system_index, []).append(staff)

    ordered = sorted(by_system.items())
    crops, staves_for_crop = [], []
    for _system_index, staves in ordered:
        crop = build_margin_crop(pws, staves)
        if crop is None:
            continue
        crops.append(crop)
        staves_for_crop.append(staves)
    if not crops:
        return []

    per_crop = read_crops_surya(crops, timeout_s=timeout_s)

    out: list[StaffLabel] = []
    for staves, texts in zip(staves_for_crop, per_crop):
        for staff in staves:
            text = texts.get(staff.staff_index)
            if not text:
                continue
            hit = lookup(text)
            out.append(StaffLabel(
                staff_index=staff.staff_index,
                text=text,
                instrument=hit.instrument if hit else None,
                fifths_offset=hit.fifths_offset if hit else 0,
                y_center_px=(staff.top_y + staff.bottom_y) / 2.0,
                confidence=hit.confidence if hit else "none",
                alias=hit.alias if hit else "",
            ))
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bootstrap", action="store_true",
                    help="create .venv-surya and install surya-ocr, then exit")
    ap.add_argument("--force", action="store_true",
                    help="with --bootstrap, rebuild an existing venv")
    ap.add_argument("--check", action="store_true",
                    help="report whether the free reader is usable here")
    args = ap.parse_args(argv)

    if args.bootstrap:
        print(f"surya venv ready: {bootstrap(force=args.force)}")
        return 0
    if args.check:
        ok = available()
        print(f"surya interpreter: {'yes' if ok else 'NO'}")
        print(f"llama.cpp backend: {'yes' if shutil.which('llama-server') else 'NO'}")
        return 0 if ok else 1
    ap.error("give --bootstrap or --check")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
