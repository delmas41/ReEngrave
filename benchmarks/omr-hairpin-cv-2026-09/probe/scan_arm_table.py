"""The CV-hairpin scan arm, PER ROW — and deliberately never pooled.

⚠️ **THIS PROBE REFUSES TO COMPUTE A POOLED FIGURE, and that is the finding it
is built around**, not a caution attached to one:

  * the two Mahler rows err in OPPOSITE DIRECTIONS — one misses fifteen
    hairpins, the other invents two — and a mean of an over-emission and an
    under-emission is true of neither page while being quotable about both;
  * **6 of the 11 hairpin-bearing-era rows carry ZERO truth hairpins**, and on
    the widened 20-row gate more still. They contribute a full denominator to
    any pool while the feature can only ever hurt them.

The general rule this arm supplied, which outlives it: **an edition effect is
attributable to the EDITION only once its rows agree in DIRECTION; otherwise it
is a row effect wearing the edition's name.**

    python3 benchmarks/omr-hairpin-cv-2026-09/probe/scan_arm_table.py \
        --off <off.json> --on <on.json>
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

WEDGE_CATS = ("wrong crescendo", "wrong diminuendo", "wrong direction")


def _rows(path: pathlib.Path, tag: str) -> dict[str, dict]:
    d = json.loads(path.read_text())
    out = {}
    for r in d["rows"]:
        out[r["row_id"].replace(f".{tag}", "")] = r
    if not out:
        sys.stderr.write(f"FATAL: no rows in {path}\n")
        raise SystemExit(2)
    return out


def _must(p: pathlib.Path) -> pathlib.Path:
    """⚠️ A missing fixture must ABORT, never read as a zero.

    The first cut of this probe built its paths as `{row}-hpon.omr.json` when
    `scan_eval` writes `{row}.-hpon.omr.json` — the row_id already carries the
    separator. Every file missed, every count came back 0, and the table said
    "the flag changed nothing" in a clean grid with no gaps in it. The OMR-NED
    column beside it was non-zero the whole time, which is the only reason it
    was caught. Same failure `_fixtures.fixtures()` exists to prevent.
    """
    if not p.is_file():
        sys.stderr.write(
            f"FATAL: {p} does not exist. A missing fixture reads as a zero and "
            "a zero reads as 'the flag did nothing'.\n")
        raise SystemExit(2)
    return p


def _wedges(p: pathlib.Path) -> int:
    return _must(p).read_text().count("<wedge ")


def _validity(fixtures: pathlib.Path, rids: list[str]) -> int:
    """⚠️ COMPARISON VALIDITY, checked before the deltas are read at all.

    Sean's standing rule for a worse score is to ask what ELSE is wrong before
    condemning the mechanism, and the first question is whether the arms differ
    only in the thing under test. So this counts every detection of every class
    in both arms and requires the two multisets to be identical once the CV
    hairpins are set aside. A run where some other class moved is not an A/B of
    this flag and its deltas mean nothing.
    """
    import collections
    hp = {"dynamicCrescendoHairpin", "dynamicDiminuendoHairpin"}

    def counts(path):
        d = json.loads(_must(path).read_text())
        c, n = collections.Counter(), 0
        for pg in d["pages"]:
            for sy in pg["systems"]:
                for st in sy["staves"]:
                    for m in st["measures"]:
                        for det in m["detections"]:
                            cl = det.get("class") or ""
                            if cl in hp and det.get("detector") == "cv":
                                n += 1
                            else:
                                c[cl] += 1
        return c, n

    bad = []
    for rid in rids:
        a, _ = counts(fixtures / f"{rid}.-hpoff.omr.json")
        b, _ = counts(fixtures / f"{rid}.-hpon.omr.json")
        if a != b:
            bad.append((rid, {k: (a[k], b[k]) for k in set(a) | set(b)
                              if a[k] != b[k]}))
    if bad:
        sys.stderr.write(
            "FATAL: the arms differ in NON-hairpin detections, so their "
            f"OMR-NED deltas are not attributable to this flag:\n{bad}\n")
        raise SystemExit(2)
    print(f"validity: {len(rids)} of {len(rids)} rows differ ONLY in CV "
          "hairpins — the deltas below are attributable to the flag.\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", type=pathlib.Path, required=True)
    ap.add_argument("--on", type=pathlib.Path, required=True)
    ap.add_argument("--fixtures", type=pathlib.Path,
                    default=pathlib.Path(__file__).resolve().parents[2]
                    / "omr-scan-e2e-2026-09" / "fixtures")
    args = ap.parse_args()

    off, on = _rows(args.off, "-hpoff"), _rows(args.on, "-hpon")
    common = sorted(set(off) & set(on))
    if len(common) < 20:
        sys.stderr.write(
            f"FATAL: {len(common)} rows in both arms; expected the 20-row gate. "
            "A short arm is the shape a cached or crashed run makes.\n")
        raise SystemExit(2)

    _validity(args.fixtures, common)
    print(f"{'row':34s} {'truthHP':>7s} {'cv+':>4s} {'wOFF':>5s} {'wON':>4s} "
          f"{'edOFF':>6s} {'edON':>6s} {'delta':>6s}  wedge-buckets")
    n_blank_silent = n_blank = 0
    for rid in common:
        a, b = off[rid], on[rid]
        raw = _must(args.fixtures / f"{rid}.-hpon.omr.json")
        added = json.loads(raw.read_text()).get("n_cv_hairpins_added", 0)
        thp = _wedges(args.fixtures / f"{rid}.truth.musicxml") // 2
        wo = _wedges(args.fixtures / f"{rid}.-hpoff.omr.musicxml")
        wn = _wedges(args.fixtures / f"{rid}.-hpon.omr.musicxml")
        ea = a["omr_ned"]["omr_ed"]
        eb = b["omr_ned"]["omr_ed"]
        ca, cb = a["omr_ned"]["categories"], b["omr_ned"]["categories"]
        buck = " ".join(f"{k.split()[-1][:4]} {ca.get(k,0)}->{cb.get(k,0)}"
                        for k in WEDGE_CATS
                        if ca.get(k, 0) or cb.get(k, 0))
        if thp == 0:
            n_blank += 1
            n_blank_silent += (added == 0)
        print(f"{rid:34s} {thp:7d} {added:4d} {wo:5d} {wn:4d} "
              f"{ea:6d} {eb:6d} {eb-ea:+6d}  {buck}")

    print(f"\nPRECISION SIGNAL: {n_blank_silent} of the {n_blank} rows whose "
          f"truth carries NO hairpin stayed silent; "
          f"{n_blank - n_blank_silent} invented one.")
    print("NO POOLED FIGURE IS PRODUCED — see this file's docstring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
