"""The thresholds for `Q.LEDGER_INK_UNDER`, MEASURED — ROADMAP 3.4g-3.

    python3 .../ledger_ink_hist.py <record-with-ink-rows.json> --out <json>

Joins every `Q.LEDGER_INK_UNDER` row to its glyph's ledger verdict and
reports p5/p25/p50/p75/p95 of three numbers per population:

  under       the filed value (best of the three head windows)
  background  the control window one space away (the smaller side)
  contrast    under - background (`LEDGER_INK_KEPT_CONTRAST_MIN`)

POPULATIONS (by the verdict the SAME record carries, which is the tree's
3.4g-2 geometry — position, shape, boxed heads — none of which reads ink):

  POS_on        kept `ledger_line` with a notehead box ON the rung box
  POS_near      kept `ledger_line` with the nearest head <= 0.75 space
  POS_kept      every kept `ledger_line` (includes inner ladder rungs)
  NEG_inside    refused `inside_the_staff`
  NEG_online    refused `on_a_staff_line`
  TARGET        no boxed head (`rung_without_boxed_head`,
                `no_head_on_the_rung`, `ink_under_the_rung`) — the
                population the witness exists for

⚠️ RED: the same tables with the windows SWAPPED — `background` read as if
it were `under`. If the swapped measure separates the populations as well as
the real one, the window is not measuring a head and nothing here may set a
threshold.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record import Q                      # noqa: E402
from tools.omr.staged.record_io import load_record         # noqa: E402

TARGET_REASONS = ("rung_without_boxed_head", "no_head_on_the_rung",
                  "ink_under_the_rung")


def pct(xs, ps=(5, 25, 50, 75, 95)):
    xs = sorted(xs)
    if not xs:
        return {f"p{p}": None for p in ps} | {"n": 0}
    out = {"n": len(xs)}
    for p in ps:
        k = (len(xs) - 1) * p / 100.0
        lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
        out[f"p{p}"] = round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 4)
    return out


def hist(xs, edges=(0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6,
                    0.7, 0.8, 1.01)):
    c = collections.Counter()
    for x in xs:
        for lo, hi in zip(edges, edges[1:]):
            if lo <= x < hi:
                c[f"[{lo:.2f},{hi:.2f})"] += 1
                break
    return {f"[{lo:.2f},{hi:.2f})": c.get(f"[{lo:.2f},{hi:.2f})", 0)
            for lo, hi in zip(edges, edges[1:])}


def populations(rec: dict):
    ink = {}
    for o in rec["observations"]:
        if o.get("quantity") == Q.LEDGER_INK_UNDER:
            d = o.get("detail") or {}
            ink[o["subject"]] = (float(o["value"]), d.get("ink_background"),
                                 d.get("ink_best_window"))
    pops = collections.defaultdict(list)
    for v in rec["verdicts"]:
        if v["quantity"] != Q.LEDGER_IS_NOT_A_LEDGER:
            continue
        m = ink.get(v["subject"])
        if m is None:
            continue
        d = v.get("detail") or {}
        reason = v.get("reason")
        row = (v["subject"], m[0], m[1], m[2], d.get("staff_step"))
        if reason == "ledger_line":
            pops["POS_kept"].append(row)
            if d.get("head_on_the_box"):
                pops["POS_on"].append(row)
            hd = d.get("head_distance_spaces")
            if hd is not None and hd <= 0.75:
                pops["POS_near"].append(row)
        elif reason == "inside_the_staff":
            pops["NEG_inside"].append(row)
        elif reason == "on_a_staff_line":
            pops["NEG_online"].append(row)
        elif reason in TARGET_REASONS:
            pops["TARGET"].append(row)
        else:
            pops[f"other:{reason}"].append(row)
    return ink, pops


def table(pops, which):
    out = {}
    for name, rows in sorted(pops.items()):
        if which == "under":
            xs = [r[1] for r in rows]
        elif which == "background":
            xs = [r[2] for r in rows if r[2] is not None]
        else:
            xs = [r[1] - r[2] for r in rows if r[2] is not None]
        out[name] = {"pct": pct(xs), "hist": hist(xs)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rec = load_record(a.record)["record"]
    ink, pops = populations(rec)
    print(f"POPULATION FIRST: {len(ink)} Q.LEDGER_INK_UNDER rows; "
          + ", ".join(f"{k} {len(v)}" for k, v in sorted(pops.items())))
    if not ink:
        print("DEAD AT ZERO — no ink rows on this record.")
        return 2
    out = {
        "record": pathlib.Path(a.record).name,
        "n_rows": len(ink),
        "populations": {k: len(v) for k, v in sorted(pops.items())},
        "under": table(pops, "under"),
        "contrast": table(pops, "contrast"),
        "RED_swapped_background_as_under": table(pops, "background"),
        "TARGET_rows": [
            {"subject": r[0], "under": r[1], "background": r[2],
             "best_window": r[3], "staff_step": r[4]}
            for r in sorted(pops.get("TARGET", []))],
    }
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    for k in ("under", "contrast", "RED_swapped_background_as_under"):
        print(f"\n── {k}")
        for name, t in out[k].items():
            print(f"  {name:14s} {t['pct']}")
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
