"""Does `<measure number="N">` name ONE INSTANT of music across the parts?

⚠️⚠️ READ THIS BEFORE QUOTING THE VEROVIO RESULT. Rendering the WHOLE file
raises nothing in either arm -- measured, both arms, 0 `Mismatching measure
number` lines -- because Verovio lays a full score out by each part's own
measure ORDER and never has to reconcile two parts' numbers. The recorded
`Mismatching measure number 87` came from `build_sidebyside.py`, which asks
the harder and more honest question: *take the bars that belong to ONE PRINTED
SYSTEM, by NUMBER, from every part.* That is the only operation that can tell
a numbering defect from a healthy file, so it is what this probe does.

The side-by-side works around the defect by renumbering each slice 1..n and
says so in its own comment. This probe deliberately does NOT renumber: it
slices by number and hands Verovio the raw result.

    python3 benchmarks/omr-measure-numbering-2026-09/probe/slice_by_number.py \
        out/before.musicxml --lo 82 --hi 96

⚠️ A SLICE IS NOT A SCORE, so a clean render here is not a claim the file is
correct -- only that the bars a NUMBER selects line up across the parts.
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from witnesses import verovio_log                     # noqa: E402


def slice_by_number(xml_text: str, windows) -> str:
    """`windows` is `{part_id: (lo, hi)}`, or a single `(lo, hi)` for all."""
    root = ET.fromstring(xml_text)
    out = ET.Element("score-partwise", {"version": "4.0"})
    pl = root.find("part-list")
    if pl is not None:
        out.append(pl)
    kept_per_part = {}
    for part in root.findall("part"):
        pid = part.get("id")
        win = windows.get(pid) if isinstance(windows, dict) else windows
        dst = ET.SubElement(out, "part", {"id": pid})
        kept = []
        if win is not None:
            lo, hi = win
            for m in part.findall("measure"):
                try:
                    n = int(m.get("number"))
                except (TypeError, ValueError):
                    continue
                if lo <= n <= hi:
                    kept.append(m)
                    dst.append(m)
        kept_per_part[pid] = [m.get("number") for m in kept]
    return ET.tostring(out, encoding="unicode"), kept_per_part


def _parse_windows(spec):
    out = {}
    for item in spec.split(","):
        pid, rng = item.split("=")
        lo, hi = rng.split(":")
        out[pid.strip()] = (int(lo), int(hi))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("xml")
    ap.add_argument("--lo", type=int)
    ap.add_argument("--hi", type=int)
    ap.add_argument("--windows",
                    help="PER-PART windows, `P1=82:96,P9=64:78` -- what "
                         "`build_sidebyside.py` asks for when it wants ONE "
                         "printed system out of a file whose parts disagree.")
    args = ap.parse_args(argv)

    text = Path(args.xml).read_text()
    if args.windows:
        windows = _parse_windows(args.windows)
        label = args.windows
    else:
        windows = (args.lo, args.hi)
        label = "%d..%d" % (args.lo, args.hi)
    sliced, kept = slice_by_number(text, windows)

    tmp = Path(args.xml).with_suffix(".slice.musicxml")
    tmp.write_text(sliced)

    print("=" * 74)
    print("SLICE %s  measures %s" % (Path(args.xml).name, label))
    print("=" * 74)
    widths = set()
    for pid, nums in kept.items():
        widths.add(len(nums))
        print("  %-4s %2d measures  %s" % (pid, len(nums),
                                           " ".join(nums) if nums else "(none)"))
    print("  distinct slice widths across the parts: %s" % sorted(widths))

    log = verovio_log(tmp)
    mism = [ln.strip() for ln in log.splitlines() if "ismatching measure" in ln]
    print("  Verovio 'Mismatching measure number' lines: %d" % len(mism))
    for ln in mism[:12]:
        print("     " + ln)
    tmp.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
