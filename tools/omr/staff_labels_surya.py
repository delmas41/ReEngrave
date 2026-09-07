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
(`MARGIN_SPACINGS`, 14 -> 20, then 20 -> 30 on 2026-09-02 when four more
publishers showed 20 still cutting) removed most of that, but the asymmetry is
structural: an OCR engine reads, a vision model reads *and infers*.

⚠️ **A clipped label is the free reader's problem and nobody else's**, which is
why it stayed invisible for so long: the paid reader scored byte-identical
tallies at every crop width ever tried. Do not read "Claude and Surya disagree
about nothing" as "the crop is wide enough".

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
import re
import shutil
import subprocess
import sys
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

#: Keep the llama.cpp server alive between runs. OFF by default because the
#: resident process holds ~1.7 GB and appearing unbidden on someone's machine is
#: not a decision a library gets to make. Measured on a 17-staff page, three
#: consecutive reads:
#:
#:     off (spawn + load + kill each time)   17.5s   15.9s   15.8s
#:     on  (server survives, next run attaches) 5.9s    4.7s    4.7s
#:
#: Surya implements the persistence itself — a sentinel file plus a health probe
#: (`surya.inference.backends.spawn.attach_or_spawn`) — so this is a flag, not a
#: server we have to write. The residue at 4.7 s is the worker's own torch
#: import, which only a long-lived PYTHON process would remove.
KEEP_ALIVE = os.environ.get("OMR_SURYA_KEEP_ALIVE", "").lower() in ("1", "true", "yes")

#: Where Surya records the running server. Read directly rather than through
#: surya's private `_sentinel_path`, because `--stop` has to work from the
#: host's 3.9 where surya is not importable.
SENTINEL = Path(os.environ.get(
    "OMR_SURYA_SENTINEL",
    os.path.expanduser("~/.cache/datalab/surya/llamacpp_server.json"),
))


#: Longest string `read_crops_text` will accept as a reading of one crop.
#:
#: The rung is a generative 650M model driven by llama.cpp, and it degenerates:
#: asked what a crop a few staff spaces tall says, it has returned an English
#: essay ("1. A statistical analysis of the data is conducted…", repeated to
#: item 64) and, on another page, `'- 8 - - 9 - - 10 - …'`. Neither is in the
#: crop. Nothing here controls decode — `temperature`, `top_p`, `seed`,
#: `n_predict` and `repeat_penalty` appear nowhere in `tools/omr` — so this is
#: a guard, not a fix for the cause.
#:
#: MEASURED over all committed transcriptions carrying a `direction_text` block
#: (113 files scanned, 45 have one; 438 strings reached the lexicon). The
#: distinct string lengths at 30 characters and above are
#:
#:     34, 41, 47, 48, 55, 144, 854
#:
#: Everything at or below 55 is a plausible reading of ink really on the page —
#: the 47/48s are a LilyPond fixture's own `CC0 1.0 Universal` footer, the 41s
#: and 55 a repeated `Cresc.` — while 144 and 854 are the two runaways. The
#: widest empty interval is (55, 144); ANY cap in 56..143 gives the identical
#: verdict on all 438 measured strings. 120 is chosen inside it.
#:
#: ⚠️ **The 55 is the wrong number to size the headroom against, and sizing
#: against it UNDERSTATES the margin.** 55 is itself a decoder repetition the
#: lexicon refuses; it is a plausible reading of ink, not a reading anything
#: kept. The collateral question — can this cap cost a real direction? — is
#: answered by the strings the pipeline ACCEPTED AND PLACED: n=86, lengths
#: 3..17 with distinct values {3,4,5,6,7,14,16,17}, the longest being
#: `'Un poco sostenuto'` and `'Allegro con brio.'` at 17 characters, and **none
#: over 120**. So against genuine directions the headroom is **7x**, not the
#: 2.2x a comparison with 55 suggests. That is the check that shows the cap
#: cannot cost a reading, and it is the one to re-run if the cap is ever moved.
#:
#: Unlike `_surya_worker._RUNAWAY_HEIGHT_FRACTION`, which had to be expressed
#: as a ratio to the system's own tick span, this needs no scale term: a
#: character count is already dimensionless, and a printed direction is a short
#: phrase whatever the DPI or the staff space.
#:
#: ⚠️ This is a READER-side sanity check and stops there. Whether a string is
#: MUSICAL is `direction_lexicon`'s question — including decoder repetition
#: (`'Cresc. Cresc. Cresc. …'`, 55 chars), which the lexicon already refuses by
#: name. Do not grow this into a semantic filter.
#:
#: ⚠️ **A live Surya run would not test this and is not the missing evidence.**
#: The guard is a pure length test AFTER the subprocess boundary and depends on
#: nothing the model does except how long its string is, which is why the tests
#: stub the worker. What a live run WOULD buy is a bigger sample of runaway
#: lengths, i.e. the only thing that could move this constant. To collect it:
#: on a PRIVATE `llama-server` — never the shared resident one, see the
#: keep-alive warning in CLAUDE.md — run `OMR_DIRECTION_READERS=surya` over the
#: 11 scan-benchmark pages N times and record the length of every string.
RUNAWAY_TEXT_MAX_CHARS = 120


def is_runaway_read(text: str) -> bool:
    """True when a crop's reading is too long to be a reading of that crop.

    Public so the boundary it draws can be tested directly, for the same reason
    `staff_labels_tesseract.strip_line_fragments` is —
    `TestThePredicateItself` in `tests/test_surya_runaway_read.py` does exactly
    that, separately from the tests that drive it through `read_crops_text`.
    """
    return len(text) > RUNAWAY_TEXT_MAX_CHARS


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


def resident_server() -> dict | None:
    """The keep-alive server Surya has running, or None.

    The sentinel outlives a crash, so a live PID is checked rather than trusted.
    """
    try:
        info = json.loads(SENTINEL.read_text())
        pid = int(info["pid"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    try:
        os.kill(pid, 0)          # signal 0 = "does this process exist"
    except OSError:
        return None
    return info


def stop_server() -> bool:
    """Stop the resident server and clear its sentinel. True if one was running."""
    import signal

    info = resident_server()
    if info is None:
        SENTINEL.unlink(missing_ok=True)
        return False
    try:
        os.kill(int(info["pid"]), signal.SIGTERM)
    except OSError as exc:
        raise SuryaLabelError(f"could not stop pid {info['pid']}: {exc}") from exc
    SENTINEL.unlink(missing_ok=True)
    return True


#: Surya writes a STACKED pair of numerals as a LaTeX fraction, because a stack
#: is what the page prints: Breitkopf's Brahms 1 puts the horn part numbers
#: "1." over "2." beside "in C", and the reader returns `in C \frac{1}{2}`.
#:
#: They are PART NUMBERS, which `instruments.normalize_label` already exists to
#: drop — but the CONTROL WORD is not a number, so it survives into the matched
#: string and dilutes `coverage`: `Clar. \frac{1}{2}` resolves to Clarinet at
#: **medium** where `Clar. 1.2.` resolves at high (coverage 0.5 against 1.0).
#:
#: This is folded HERE and not in the lexicon on purpose. LaTeX is Surya's
#: output format, not something a printed margin contains, and `_surya_worker`
#: already turns that worker's HTML into plain text at this same boundary; the
#: lexicon's job is to match printed strings, and teaching it markup would put a
#: reader's quirk in the one module every reader shares. It also means the raw
#: `StaffLabel.text` a human reads back is the label, not the markup.
_LATEX_CONTROL = re.compile(r"\\[dt]?frac(?![a-z])")

#: Only stripped from strings that actually carry the control word. `|` is a
#: character `instruments._OCR_FOLD` reads as an `i` — a part number `II.` comes
#: back as `||.` often enough to matter — so deleting bars everywhere would cost
#: more than the markup does.
_MATH_PUNCTUATION = re.compile(r"[{}|｜]+")


def _plain_text(text: str) -> str:
    """Fold Surya's LaTeX markup back to the characters it stands for."""
    if not _LATEX_CONTROL.search(text):
        return text
    folded = _MATH_PUNCTUATION.sub(" ", _LATEX_CONTROL.sub(" ", text))
    return re.sub(r"\s+", " ", folded).strip()


def read_crops_surya(crops: list[MarginCrop], *,
                     timeout_s: float | None = None,
                     keep_alive: bool | None = None) -> list[dict[int, str]]:
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
    env = dict(os.environ)
    if KEEP_ALIVE if keep_alive is None else keep_alive:
        env["SURYA_INFERENCE_KEEP_ALIVE"] = "true"
    try:
        proc = subprocess.run(
            [str(python), str(_WORKER)],
            input=json.dumps(job), capture_output=True, text=True, env=env,
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
        out.append({int(k): _plain_text(v)
                    for k, v in (entry.get("labels") or {}).items()})
    return out


def read_crops_text(crops: list, *,
                    timeout_s: float | None = None,
                    keep_alive: bool | None = None) -> list[str]:
    """Plain OCR for a list of BGR image arrays — one string per crop.

    The second thing this venv is good for. `direction_text` needs to read a
    word out of a crop it cut itself, which is the same model on a different
    shape of input, so it goes through the same subprocess rather than standing
    up a second one: the 650M GGUF load dominates either caller's cost and is
    paid once per process, not once per crop.

    A crop that reads as nothing comes back as `""`, never as an exception —
    the caller's job is to gate what was read, and a blank crop is a legitimate
    answer to "what does this say".
    """
    if not crops:
        return []
    import cv2                                              # noqa: PLC0415

    encoded = []
    for crop in crops:
        ok, buf = cv2.imencode(".png", crop)
        encoded.append(base64.standard_b64encode(buf.tobytes()).decode("ascii")
                       if ok else "")

    python = interpreter()
    env = dict(os.environ)
    if KEEP_ALIVE if keep_alive is None else keep_alive:
        env["SURYA_INFERENCE_KEEP_ALIVE"] = "true"
    try:
        proc = subprocess.run(
            [str(python), str(_WORKER)],
            input=json.dumps({"crops": encoded}), capture_output=True,
            text=True, env=env,
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

    out = []
    n_runaway = 0
    for entry in payload.get("crops", []):
        if entry.get("error"):
            logger.warning("surya failed on one crop: %s", entry["error"])
            out.append("")
            continue
        text = entry.get("text") or ""
        # Refused LOUDLY and per crop, never quietly and never for the batch:
        # a runaway is the model generating instead of transcribing, and it is
        # indistinguishable downstream from a crop that legitimately says
        # nothing. `n_read` in the direction report counts a crop as read the
        # moment any rung returns a non-empty string, so leaving it in makes
        # "the OCR wrote an essay" look like "the OCR read this".
        #
        # ⚠️ THE WHOLE STRING GOES, INCLUDING A REAL-LOOKING PREFIX. The
        # 854-character essay opens `'cresc. '`, and that word was on the page,
        # so refusing it costs a direction. Keeping the prefix is still wrong
        # three ways: it would trust exactly the string this line has just
        # declared untrustworthy; nothing establishes that a runaway always
        # BEGINS with the real reading; and the other measured runaway (144
        # chars, `'- 8 - - 9 - …'`) has no real prefix at all — so the
        # counter-example is already in the corpus and the case that has one is
        # n=1. It is also `strip_line_fragments`' line: cleaning a reading and
        # REPAIRING one are different, and only the first is free. Revisit on a
        # measurement of how runaways begin, not on the next sighting.
        if is_runaway_read(text):
            n_runaway += 1
            logger.warning(
                "surya: REFUSED a runaway read — %d chars, cap %d. A crop a "
                "few staff spaces tall cannot print this, so the decoder "
                "generated rather than transcribed. First 60: %r",
                len(text), RUNAWAY_TEXT_MAX_CHARS, text[:60])
            out.append("")
            continue
        out.append(text)
    if n_runaway:
        logger.warning("surya: %d of %d crops refused as runaway reads",
                       n_runaway, len(out))
    return out


def read_staff_labels_surya(pws: PageWithStaves, *,
                            timeout_s: float | None = None,
                            keep_alive: bool | None = None) -> list[StaffLabel]:
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

    per_crop = read_crops_surya(crops, timeout_s=timeout_s,
                                keep_alive=keep_alive)

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
    ap.add_argument("--serve", action="store_true",
                    help="start a persistent llama.cpp server and warm it, so "
                         "later runs skip the ~11s spawn-and-load. Holds about "
                         "1.7 GB until --stop.")
    ap.add_argument("--stop", action="store_true",
                    help="stop the persistent server started by --serve")
    args = ap.parse_args(argv)

    if args.bootstrap:
        print(f"surya venv ready: {bootstrap(force=args.force)}")
        return 0

    if args.stop:
        print("stopped the persistent server" if stop_server()
              else "no persistent server was running")
        return 0

    if args.serve:
        # Warming it here rather than telling the user to run a transcription
        # means --serve leaves the model LOADED, not merely the process up.
        from PIL import Image
        import io as _io

        buf = _io.BytesIO()
        Image.new("RGB", (240, 400), (255, 255, 255)).save(buf, format="PNG")
        warm = MarginCrop(png=buf.getvalue(), staff_indices=[0],
                          tick_ys=(200.0,), gutter_px=0)
        read_crops_surya([warm], keep_alive=True)
        info = resident_server()
        if info is None:
            print("server did not stay up — check `llama-server` is installed",
                  file=sys.stderr)
            return 1
        print(f"persistent server on port {info['port']} (pid {info['pid']})")
        print("set OMR_SURYA_KEEP_ALIVE=1 so runs attach to it instead of "
              "spawning their own; `--stop` when done.")
        return 0

    if args.check:
        ok = available()
        print(f"surya interpreter: {'yes' if ok else 'NO'}")
        print(f"llama.cpp backend: {'yes' if shutil.which('llama-server') else 'NO'}")
        info = resident_server()
        print(f"persistent server: "
              + (f"yes, port {info['port']} (pid {info['pid']})" if info else "no"))
        print(f"keep-alive default: {'on' if KEEP_ALIVE else 'off'} "
              "(OMR_SURYA_KEEP_ALIVE)")
        return 0 if ok else 1

    ap.error("give --bootstrap, --check, --serve or --stop")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
