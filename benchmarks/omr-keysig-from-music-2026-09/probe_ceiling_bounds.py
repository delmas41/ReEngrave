"""The strongest form of "infer the signature from the music", bounded on
ground truth.

`probe_ceiling_from_truth.py` scores hypotheses. This one does not score at
all — it derives an INTERVAL and speaks only when the interval has one member,
which is what a rule required to be 0-wrong would actually have to do. Three
constraints, each of which is a fact about engraving rather than a statistic:

  lower bound   every letter carrying a CLEAN natural must be altered by the
                signature, and a signature alters a PREFIX of the circle order,
                so the deepest such letter sets a floor.
  upper bound   a letter carrying a CLEAN flat is not already flattened by the
                signature, so it sets a ceiling one short of its own slot.
  courtesy      an accidental on the same pitch in the PREVIOUS bar makes the
                next bar's natural a courtesy, not a signature cancellation.
                Orchestral engraving is full of these and they are the single
                largest source of a wrong floor.

    python3 benchmarks/omr-keysig-from-music-2026-09/probe_ceiling_bounds.py \
        --works 120 --window 8
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from probe_ceiling_from_truth import load_musicxml, parts_of  # noqa: E402

FLAT_ORDER = "BEADGCF"
SHARP_ORDER = "FCGDAEB"


def evidence_for(part: ET.Element) -> tuple[int | None, list[dict]]:
    """[(measure, kind, letter, clean, courtesy)] plus the opening key."""
    fifths_seen: list[int] = []
    out: list[dict] = []
    prev_bar: dict[tuple[str, str], str] = {}
    for ordinal, m in enumerate(part.findall("measure")):
        for k in m.findall("attributes/key"):
            t = k.findtext("fifths")
            if t is not None:
                try:
                    fifths_seen.append(int(t))
                except ValueError:
                    pass
        bar: dict[tuple[str, str], str] = {}
        for n in m.findall("note"):
            step, octv = n.findtext("pitch/step"), n.findtext("pitch/octave") or ""
            acc = n.findtext("accidental")
            if not step or not acc:
                continue
            letter = step.strip().upper()
            a = acc.strip().lower()
            kind = ("#" if "sharp" in a else "b" if "flat" in a
                    else "n" if a == "natural" else None)
            if not kind:
                continue
            key = (letter, octv)
            out.append({"m": ordinal, "kind": kind, "letter": letter,
                        "clean": key not in bar,
                        "courtesy": key in prev_bar})
            bar[key] = kind
        prev_bar = bar
    if not fifths_seen or len(set(fifths_seen)) > 1:
        return None, out
    return fifths_seen[0], out


def bounds(ev: list[dict], drop_courtesy: bool) -> tuple[int, int, dict]:
    """(lo, hi) over fifths, in the flat direction and the sharp direction
    together. Returns the surviving interval as (lo, hi) inclusive; lo > hi
    means the evidence is self-contradictory."""
    used = [e for e in ev if e["clean"] and not (drop_courtesy and e["courtesy"])]
    nat = {e["letter"] for e in used if e["kind"] == "n"}
    flat = {e["letter"] for e in used if e["kind"] == "b"}
    sharp = {e["letter"] for e in used if e["kind"] == "#"}

    # Flat direction: signature = FLAT_ORDER[:k], k >= 0.
    def span(order: str, cancel: set[str], assert_: set[str]) -> tuple[int, int]:
        lo, hi = 0, 7
        for l in cancel:                      # a natural on l => l is altered
            if l in order:
                lo = max(lo, order.index(l) + 1)
            else:
                lo = 99                       # impossible letter: contradiction
        for l in assert_:                     # a flat on l => l NOT yet flat
            if l in order:
                hi = min(hi, order.index(l))
        return lo, hi

    flo, fhi = span(FLAT_ORDER, nat, flat)
    slo, shi = span(SHARP_ORDER, nat, sharp)
    survivors = set()
    if flo <= fhi:
        survivors |= {-k for k in range(flo, fhi + 1)}
    if slo <= shi:
        survivors |= {k for k in range(slo, shi + 1)}
    if not survivors:
        return 1, 0, {"n_nat": len(nat), "n_flat": len(flat), "n_sharp": len(sharp)}
    return min(survivors), max(survivors), {
        "survivors": sorted(survivors), "n_nat": len(nat),
        "n_flat": len(flat), "n_sharp": len(sharp)}


def judge(ev: list[dict], truth: int, drop_courtesy: bool) -> str:
    lo, hi, info = bounds(ev, drop_courtesy)
    surv = info.get("survivors")
    if not surv:
        return "contradiction"
    if len(surv) != 1:
        return "silent"
    return "correct" if surv[0] == truth else "wrong"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores-dir",
                    default="/Users/seanjohnson/Desktop/gradus-vercel/public/scores")
    ap.add_argument("--works", type=int, default=120)
    ap.add_argument("--window", type=int, default=8)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    files = sorted(Path(args.scores_dir).glob("*.mxl"))
    random.Random(args.seed).shuffle(files)
    files = files[: args.works]

    tal: dict[str, Counter] = defaultdict(Counter)
    by_truth: dict[tuple[str, int], Counter] = defaultdict(Counter)
    n_works = n_parts = 0

    for f in files:
        root = load_musicxml(f)
        if root is None:
            continue
        rows = []
        for name, part in parts_of(root):
            t, ev = evidence_for(part)
            if t is not None:
                rows.append((name, t, ev))
        if len(rows) < 2:
            continue
        n_works += 1
        n_parts += len(rows)
        n_meas = max((e["m"] for _, _, ev in rows for e in ev), default=0) + 1
        starts = list(range(0, max(1, n_meas - args.window), args.window))

        for cz in (False, True):
            tag = "courtesy-dropped" if cz else "courtesy-kept"
            for name, truth, ev in rows:
                tal[f"movement/{tag}"][judge(ev, truth, cz)] += 1
                by_truth[(tag, truth)][judge(ev, truth, cz)] += 1
                for s in starts:
                    w = [e for e in ev if s <= e["m"] < s + args.window]
                    tal[f"window{args.window}/{tag}"][judge(w, truth, cz)] += 1

    print(f"\n{n_works} works, {n_parts} parts, window {args.window}\n")
    print(f"{'scope':<34} {'correct':>8} {'wrong':>7} {'silent':>8} "
          f"{'contra':>7} {'acc(spoken)':>12} {'spoke on':>9}")
    for key in sorted(tal):
        t = tal[key]
        spoken = t["correct"] + t["wrong"]
        total = sum(t.values())
        print(f"{key:<34} {t['correct']:>8} {t['wrong']:>7} {t['silent']:>8} "
              f"{t['contradiction']:>7} "
              f"{(t['correct']/spoken if spoken else 0):>11.1%} "
              f"{(spoken/total if total else 0):>8.1%}")

    print("\n-- movement scope, courtesy dropped, by TRUE signature --")
    print(f"{'true':>6} {'parts':>6} {'correct':>8} {'wrong':>6} {'silent':>7} "
          f"{'contra':>7}")
    for (tag, truth) in sorted(k for k in by_truth if k[0] == "courtesy-dropped"):
        c = by_truth[(tag, truth)]
        print(f"{truth:>6} {sum(c.values()):>6} {c['correct']:>8} {c['wrong']:>6} "
              f"{c['silent']:>7} {c['contradiction']:>7}")

    (HERE / "artifacts").mkdir(parents=True, exist_ok=True)
    (HERE / "artifacts" / "ceiling_bounds.json").write_text(json.dumps(
        {"works": n_works, "parts": n_parts, "window": args.window,
         "tallies": {k: dict(v) for k, v in tal.items()},
         "by_truth": {f"{a}|{b}": dict(v) for (a, b), v in by_truth.items()}}))


if __name__ == "__main__":
    main()
