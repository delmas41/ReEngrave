"""Do dynamic LETTERS and HAIRPINS corroborate each other?

Sean, 2026-09-09: *"we will obviously need to have both read and able to
interact with each other in the adjudication stage."*

Both halves are right. This probe asks the third question — **in WHICH
direction can they interact** — and the musically obvious answer does not
survive contact with the truth.

THE TEMPTING CHECK, AND WHY IT MUST NOT BE A VETO
-------------------------------------------------
A crescendo runs from a quieter dynamic to a louder one. So a hairpin flanked
by `p ... f` corroborates a `crescendo` reading and contradicts a
`diminuendo` one — an implication test of exactly the shape
`staged/groups.py` is built for.

⚠️⚠️ **THE RULE'S ACCURACY IS ENTIRELY A FUNCTION OF ITS REACH, and that —
not any single rate — is the finding.** Swept over the window either side of a
hairpin end (`--window`), on 683 hairpins of one reference encoding:

    window   hairpins it can speak about        wrong about the truth
    +/-1        34  ( 5.3% of hairpins)          0 / 34   =  0.0%
    +/-2        68  (13.5%)                      9 / 68   = 13.2%
    +/-3       108  (23.4%)                     26 / 108  = 24.1%
    +/-4       132  (28.4%)                     42 / 132  = 31.8%

**At one measure it is EXACT — 34 for 34 — and at four measures it is wrong
about a third of the time.** So the coupling between a hairpin and a dynamic
is real and strictly LOCAL: a dynamic one bar from a hairpin end genuinely
belongs to it; one four bars away is a different musical event that the
window merely reached. `cresc.` into a subito `p` is a standard gesture, and a
`dim.` from an `f` resolving onto no new marking is commoner still — both
appear the moment the window is loosened.

⚠️ **So the constant is not tuned, it is a cliff**: keep the check at +/-1
measure, where it is exact, and ABSTAIN beyond it rather than trading accuracy
for reach. Even there it is ADDITIVE evidence over 5% of hairpins, never a
veto — `groups.py`'s own stated failure mode is what a loosened window
produces:

    A wrong `reading` manufactures disagreement out of correct engraving.

⚠️ An earlier draft of this file quoted "wrong roughly three times in ten" as
*the* rate. That came from a single run with an ASYMMETRIC window (+/-2
behind, +5 ahead) and is a point on the curve above, not a property of the
rule. The sweep is the result; a single rate from a single window is not.

WHAT THIS PROBE DOES NOT MEASURE
--------------------------------
⚠️ **n = 1 work.** The score library is machine-local and gitignored, so the
only reference encoding committed to the repo is Brahms 1 / Breitkopf. Brahms
is a HEAVY hairpin user, so if this figure is biased it is biased toward
*over*-stating the coupling — which makes a weak result here weaker still
elsewhere, not stronger.

⚠️ **It measures the ENCODING, not the page.** A hairpin the engraver printed
and the encoder omitted is invisible here, and the encoder's placement of a
`<dynamics>` need not be where the ink stands.

⚠️ **Measure-level granularity.** Two directions in one bar are "together"
whatever their offsets. That is deliberately generous: a tighter window can
only lower the coupling, so the numbers below are a CEILING on it.

    python3 benchmarks/omr-dynamics-coupling-2026-09/probe_letter_wedge_coupling.py
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

#: Committed reference encoding. Any `.mxl`/`.musicxml` works via --truth.
DEFAULT_TRUTH = Path(
    "benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/reference.mxl")

#: Loudness order. `<other-dynamics>` strings (sf, fp, rfz) are deliberately
#: NOT ranked — an `sf` is an accent, not a level, and giving it a rank would
#: invent a direction for a marking that states none.
RANK = {"pppp": 0, "ppp": 1, "pp": 2, "p": 3, "mp": 4,
        "mf": 5, "f": 6, "ff": 7, "fff": 8, "ffff": 9}


def load_score(path: Path) -> ET.Element:
    if path.suffix == ".mxl":
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.endswith(".xml") or "META" in name:
                    continue
                root = ET.fromstring(z.read(name))
                if root.tag.endswith("score-partwise"):
                    return root
        raise SystemExit(f"no score-partwise inside {path}")
    return ET.parse(path).getroot()


def _dynamic_text(node: ET.Element) -> str:
    """The word inside a `<dynamics>` — its child's tag, or the free text."""
    for child in node:
        tag = child.tag.split("}")[-1]
        if tag == "other-dynamics":
            return (child.text or "").strip().lower()
        return tag
    return ""


def timelines(root: ET.Element) -> list[list[tuple[int, str, str | None]]]:
    """Per part, `(measure_index, kind, value)` in document order.

    `kind` is `dyn` | `crescendo` | `diminuendo` | `stop`.
    """
    out = []
    for part in root.findall("part"):
        events: list[tuple[int, str, str | None]] = []
        for m_i, measure in enumerate(part.findall("measure")):
            for direction in measure.iter("direction"):
                for dtype in direction.findall("direction-type"):
                    dyn = dtype.find("dynamics")
                    if dyn is not None:
                        events.append((m_i, "dyn", _dynamic_text(dyn)))
                    wedge = dtype.find("wedge")
                    if wedge is not None:
                        kind = (wedge.get("type") or "").lower()
                        events.append(
                            (m_i, "stop" if kind == "stop" else kind, None))
        out.append(events)
    return out


def _nearest_dynamic(events, i, window, step):
    """The nearest ranked dynamic within `window` measures, or None."""
    home = events[i][0]
    rng = range(i - 1, -1, -1) if step < 0 else range(i + 1, len(events))
    for j in rng:
        if abs(events[j][0] - home) > window:
            return None
        if events[j][1] == "dyn" and events[j][2] in RANK:
            return RANK[events[j][2]]
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth", type=Path, default=DEFAULT_TRUTH)
    ap.add_argument("--window", type=int, default=2,
                    help="measures either side of a hairpin end")
    args = ap.parse_args()

    root = load_score(args.truth)
    parts = timelines(root)

    n_dyn = sum(1 for ev in parts for e in ev if e[1] == "dyn")
    n_wedge = sum(1 for ev in parts for e in ev
                  if e[1] in ("crescendo", "diminuendo"))
    print(f"{args.truth.name}: {len(parts)} parts, "
          f"{n_dyn} <dynamics>, {n_wedge} hairpins\n")

    # ── 1. co-location ────────────────────────────────────────────────────
    print("CO-LOCATION — a hairpin end with any dynamic nearby, in its part")
    for win in (0, 1, 2):
        hit = tot = 0
        for events in parts:
            for i, (_m, kind, _v) in enumerate(events):
                if kind not in ("crescendo", "diminuendo"):
                    continue
                tot += 1
                if (_nearest_dynamic(events, i, win, -1) is not None
                        or _nearest_dynamic(events, i, win, +1) is not None):
                    hit += 1
        print(f"  within +/-{win} measures: {hit:>4}/{tot} = {hit / tot:.1%}")

    # ── 2. does the DIRECTION agree? ──────────────────────────────────────
    agree = contradict = flat = one_sided = neither = 0
    for events in parts:
        for i, (_m, kind, _v) in enumerate(events):
            if kind not in ("crescendo", "diminuendo"):
                continue
            before = _nearest_dynamic(events, i, args.window, -1)
            after = _nearest_dynamic(events, i, args.window, +1)
            if before is None and after is None:
                neither += 1
            elif before is None or after is None:
                one_sided += 1
            elif after == before:
                flat += 1
            elif (after > before) == (kind == "crescendo"):
                agree += 1
            else:
                contradict += 1

    total = agree + contradict + flat + one_sided + neither
    checkable = agree + contradict + flat
    print(f"\nDIRECTION AGREEMENT (window +/-{args.window} measures)")
    print(f"  a dynamic at BOTH ends (checkable) : {checkable:>4}"
          f"  ({checkable / total:.1%})")
    print(f"     direction agrees                : {agree:>4}")
    print(f"     direction CONTRADICTS           : {contradict:>4}")
    print(f"     equal both sides (no direction) : {flat:>4}")
    print(f"  only ONE end has a dynamic         : {one_sided:>4}"
          f"  ({one_sided / total:.1%})")
    print(f"  NEITHER end                        : {neither:>4}"
          f"  ({neither / total:.1%})")
    if agree + contradict:
        rate = contradict / (agree + contradict)
        print(f"\n  ⚠️ Of the {agree + contradict} hairpins the rule can speak "
              f"about, it is WRONG about the truth {rate:.1%} of the time.")

    # ⚠️ THE SWEEP IS THE RESULT. A single window's rate is a point on this
    # curve and must never be quoted as a property of the rule.
    print("\nREACH vs ACCURACY — swept, because one window is not the rule")
    print(f"  {'window':>7} {'can speak about':>17} {'wrong':>16}")
    for win in (1, 2, 3, 4):
        a = c = 0
        for events in parts:
            for i, (_m, kind, _v) in enumerate(events):
                if kind not in ("crescendo", "diminuendo"):
                    continue
                lo = _nearest_dynamic(events, i, win, -1)
                hi = _nearest_dynamic(events, i, win, +1)
                if lo is None or hi is None or lo == hi:
                    continue
                if (hi > lo) == (kind == "crescendo"):
                    a += 1
                else:
                    c += 1
        n = a + c
        share = n / n_wedge if n_wedge else 0.0
        print(f"  +/-{win:<4} {n:>6} ({share:5.1%} of hairpins) "
              f"{c:>6} / {n} = {c / n:.1%}" if n else f"  +/-{win:<4}  none")
    print("\n  ⚠️ Exact where it is TIGHT, worthless where it REACHES. Keep it "
          "at +/-1 and abstain\n     beyond — additive evidence over ~5% of "
          "hairpins, never a veto.")


if __name__ == "__main__":
    main()
