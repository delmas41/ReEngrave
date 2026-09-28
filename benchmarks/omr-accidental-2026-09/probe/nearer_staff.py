"""ROADMAP 2.7b — measure the heads filed on a staff they do not belong to.

Sean's five 'wrong staff above' heads (crops 4, 13, 20, 23, 26 of the 2.7
adjudication) and every other notehead on a record, measured in the PAGE
frame against every staff of its own system:

  * `filed_spaces`   distance from the head's centre to the nearest line of
                     the staff whose CELL it was cut from (0 inside the band);
  * `near_spaces`    the same distance to the nearest OTHER staff of the
                     system, and which staff that is (`near_staff`, `near_side`
                     below/above);
  * `contested`      whether the head carries a `Q.GLYPH_BAND_DISTANCE` row
                     (2.6's contest domain: a same-category twin with IoU > 0.3
                     on another staff) and the candidates it names;
  * `glyph_owner`    the standing verdict, if any: value + reason;
  * `npv`            the standing `notehead_is_not_a_notehead` verdict: value,
                     reason, and its `unladdered_signal`;
  * rungs            every `ledgerLine` glyph of the SAME CELL whose page
                     centre lies strictly between the filed staff's outer line
                     (on the head's side) and the head, x-overlapping the
                     head's page box, split by its standing
                     `ledger_is_not_a_ledger` verdict (3.4g-2's kept set is
                     `value is False`). The same count toward the near staff.

⚠️ The distances are recomputed from `Q.STAFF_LINES` and `bbox_page_px`; the
CONTROL is that they reproduce every `Q.GLYPH_BAND_DISTANCE` row GATHER wrote
(exact to 1e-6), and `--break-control` perturbs the spacing by 1 % so the
control goes RED first.

    python3 benchmarks/omr-accidental-2026-09/probe/nearer_staff.py \\
        <record.json> --label litolff --out <json> [--break-control]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.adjudicators.notehead_precision import (  # noqa: E402
    OWN_LEDGER_MAX_SPACES)

#: The heads Sean adjudicated (2.7, `out/print/ADJUDICATION-sean-2026-09-27.json`).
ADJ = HERE.parent / "out" / "print" / "ADJUDICATION-sean-2026-09-27.json"
WRONG_STAFF_DECIDED = (4, 13, 20, 23, 26)
WRONG_STAFF_CONTROL = (2,)       # abstained control, same finding
NOT_A_HEAD = (3,)                # the tremolo slash


def band(y, lines, sp):
    top, bot = min(lines), max(lines)
    if top <= y <= bot:
        return 0.0
    return ((top - y) if y < top else (y - bot)) / sp


def standing(verdicts):
    sup = {v.get("supersedes") for v in verdicts if v.get("supersedes")}
    out = {}
    for v in verdicts:
        if v["id"] in sup:
            continue
        out[(v["subject"], v["quantity"])] = v
    return out


def named_heads():
    a = json.loads(ADJ.read_text())
    neg, pos, other = {}, {}, {}
    for v in a["verdicts"]:
        n = int(v["crop"][4:6])
        if n in WRONG_STAFF_DECIDED or n in WRONG_STAFF_CONTROL:
            neg.setdefault(v["head"], []).append(n)
        elif n in NOT_A_HEAD:
            other.setdefault(v["head"], []).append(n)
        else:
            pos.setdefault(v["head"], []).append(n)
    return neg, pos, other


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--break-control", action="store_true")
    a = ap.parse_args()

    rec = load_record(a.record)["record"]
    obs = rec["observations"]
    V = standing(rec["verdicts"])

    lines = {}
    for o in obs:
        if o["quantity"] == "staff_lines" and len(o["value"]) >= 2:
            ys = sorted(float(y) for y in o["value"])
            sp = (ys[-1] - ys[0]) / (len(ys) - 1)
            if a.break_control:
                sp *= 1.01
            if sp > 0:
                lines[o["subject"]] = (ys, sp)
    staves_of = collections.defaultdict(list)
    for k in lines:
        p, s, st = k.split("/")[1:4]
        staves_of[(p, s)].append(k)

    heads = set(o["subject"] for o in obs if o["quantity"] == "notehead_class")
    box = {}
    ledgers = collections.defaultdict(list)   # cell -> [(sub, pb)]
    for o in obs:
        if o["quantity"] != "glyph_box":
            continue
        pb = (o.get("detail") or {}).get("bbox_page_px")
        if not pb:
            continue
        box[o["subject"]] = (o["value"][0], [float(v) for v in pb])
        if o["value"][0] == "ledgerLine":
            cell = "cell/" + "/".join(o["subject"].split("/")[1:5])
            ledgers[cell].append((o["subject"], [float(v) for v in pb]))
    bands = collections.defaultdict(list)
    for o in obs:
        if o["quantity"] == "glyph_band_distance":
            bands[o["subject"]].append(o)

    # ── CONTROL: reproduce GATHER's band rows ───────────────────────────────
    checked = bad = 0
    for sub, rows in bands.items():
        if sub not in box:
            continue
        pb = box[sub][1]
        y = (pb[1] + pb[3]) / 2.0
        for r in rows:
            c = (r.get("detail") or {}).get("candidate")
            if c not in lines:
                continue
            checked += 1
            if abs(band(y, *lines[c]) - float(r["value"])) > 1e-6:
                bad += 1
    control = {"band_rows_checked": checked, "band_rows_differing": bad,
               "break_control": a.break_control}
    print(json.dumps(control), flush=True)

    def rungs_between(sub, pb, staff_key, cell):
        """kept / refused ledger boxes between the head and `staff_key`."""
        ys, sp = lines[staff_key]
        y = (pb[1] + pb[3]) / 2.0
        top, bot = ys[0], ys[-1]
        if top <= y <= bot:
            return {"kept": 0, "refused": {}, "first_kept": False}
        lo, hi = (y, top) if y < top else (bot, y)
        edge = top if y < top else bot
        kept = 0
        first = False
        refused = collections.Counter()
        for lsub, lb in ledgers.get(cell, ()):
            ly = (lb[1] + lb[3]) / 2.0
            if not (lo < ly < hi):
                continue
            if min(lb[2], pb[2]) - max(lb[0], pb[0]) <= 0:
                continue
            # the head's OWN ledger line joins it to no staff in particular
            # (`notehead_precision.OWN_LEDGER_MAX_SPACES`, imported)
            if abs(ly - y) / sp <= OWN_LEDGER_MAX_SPACES:
                continue
            lv = V.get((lsub, "ledger_is_not_a_ledger"))
            if lv is not None and lv.get("outcome") == "decided" \
                    and lv.get("value") is True:
                refused[lv.get("reason")] += 1
                continue
            kept += 1
            if abs(abs(ly - edge) / sp - 1.0) <= 0.5:
                first = True
        return {"kept": kept, "refused": dict(refused), "first_kept": first}

    neg, pos, other = named_heads()
    rows = []
    for sub in sorted(heads):
        if sub not in box:
            continue
        name, pb = box[sub]
        parts = sub.split("/")
        p, s, st, c = parts[1:5]
        filed = f"staff/{p}/{s}/{st}"
        if filed not in lines:
            continue
        cell = f"cell/{p}/{s}/{st}/{c}"
        y = (pb[1] + pb[3]) / 2.0
        ys, sp = lines[filed]
        d_filed = band(y, ys, sp)
        side = "inside" if d_filed == 0 else ("above" if y < ys[0] else "below")
        near = None
        for k in staves_of[(p, s)]:
            if k == filed:
                continue
            d = band(y, *lines[k])
            if near is None or d < near[0]:
                near = (d, k)
        npv = V.get((sub, "notehead_is_not_a_notehead"))
        own = V.get((sub, "glyph_owner"))
        cands = sorted({(r.get("detail") or {}).get("candidate")
                        for r in bands.get(sub, ())} - {filed})
        row = {
            "subject": sub, "class": name,
            "filed_spaces": round(d_filed, 3), "filed_side": side,
            "near_staff": near[1] if near else None,
            "near_spaces": round(near[0], 3) if near else None,
            "near_side": (None if not near else
                          ("below" if int(near[1].split("/")[3]) > int(st)
                           else "above")),
            "contested": bool(bands.get(sub)),
            "contest_candidates": cands,
            "twin_on_near": bool(near and near[1] in cands),
            "glyph_owner": (None if own is None else
                            [own.get("outcome"), own.get("value"),
                             own.get("reason")]),
            "npv": (None if npv is None else
                    [npv.get("outcome"), npv.get("value"), npv.get("reason")]),
            "unladdered_signal": (None if npv is None else
                                  (npv.get("detail") or {})
                                  .get("unladdered_signal")),
            "rungs_to_filed": rungs_between(sub, pb, filed, cell),
            "rungs_to_near": (rungs_between(sub, pb, near[1], cell)
                              if near else None),
            "named": ("wrong_staff" if sub in neg else
                      "confirmed" if sub in pos else
                      "not_a_head" if sub in other else None),
            "crops": neg.get(sub) or pos.get(sub) or other.get(sub),
        }
        rows.append(row)

    # ── the population, on a grid of bands ─────────────────────────────────
    def sig(r, n, m):
        return (r["filed_spaces"] > n and r["near_spaces"] is not None
                and r["near_spaces"] <= m and r["near_spaces"] < r["filed_spaces"]
                and r["rungs_to_filed"]["kept"] == 0)

    grid = {}
    own_key = lambda r: "/".join(["staff"] + r["subject"].split("/")[1:4])
    for n in (2.0, 2.5, 2.75, 3.0, 3.25, 3.5):
        for m in (0.0, 1.0, 2.0, 2.5, 2.75, 3.0, 3.5):
            hit = [r for r in rows if sig(r, n, m)]
            grid[f"N>{n} M<={m}"] = {
                "heads": len(hit),
                "twin_on_near": sum(r["twin_on_near"] for r in hit),
                "no_twin": sum(not r["twin_on_near"] for r in hit),
                "already_refused": sum(1 for r in hit if r["npv"]
                                       and r["npv"][1] is True),
                "owner_elsewhere": sum(1 for r in hit if r["glyph_owner"]
                                       and r["glyph_owner"][0] == "decided"
                                       and r["glyph_owner"][1] != own_key(r)),
                # what THIS rule would newly refuse: not already refused, and
                # no twin on the near staff (there `glyph_owner` decides)
                "newly_refused": sum(1 for r in hit if not r["twin_on_near"]
                                     and not (r["npv"] and r["npv"][1] is True)),
                "newly_refused_with_kept_rung_to_near": sum(
                    1 for r in hit if not r["twin_on_near"]
                    and not (r["npv"] and r["npv"][1] is True)
                    and (r["rungs_to_near"] or {}).get("kept", 0) > 0),
                "confirmed_hit": sum(r["named"] == "confirmed" for r in hit),
                "wrong_staff_hit": sum(r["named"] == "wrong_staff"
                                       for r in hit),
            }
    hist = collections.Counter()
    for r in rows:
        if r["near_spaces"] is not None and r["near_spaces"] < r["filed_spaces"]:
            hist[(round(r["filed_spaces"] * 2) / 2,
                  round(r["near_spaces"] * 2) / 2)] += 1
    out = {"label": a.label, "record": a.record, "control": control,
           "heads": len(rows),
           "named": [r for r in rows if r["named"]],
           "grid": grid,
           "hist_filed_near_nearer_other": {f"{k[0]}|{k[1]}": v for k, v in
                                            sorted(hist.items())},
           "signature_rows_N2_M3.5": [r for r in rows if sig(r, 2.0, 3.5)]}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    for r in out["named"]:
        print(r["named"], r["crops"], r["subject"], "filed", r["filed_spaces"],
              r["filed_side"], "near", r["near_staff"], r["near_spaces"],
              "cont", r["contested"], r["contest_candidates"], "own",
              r["glyph_owner"], "npv", r["npv"], "rungs", r["rungs_to_filed"],
              "unl", r["unladdered_signal"])
    for k, v in grid.items():
        print(k, json.dumps(v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
