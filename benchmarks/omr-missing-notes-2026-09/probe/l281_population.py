#!/usr/bin/env python3
"""l281_population: the ROADMAP 2.81 "bare stem" population, defined from the tree,
split by what the stem-tip reader says, and followed to its final duration verdict.

Reads the three `l281_extract.py` JSONs of one record (obs, abs, ver). A reading
probe: it decides nothing.

THE POPULATION (stated once, here and in FINDINGS 2.81):
  P  = a note head ADJUDICATE KEPT as a note (not refused as `not a notehead`, not read
       as a whole rest, not given to another staff's contest) whose standing
       `Q.DURATION` verdict is NARROWED with reason `beam_discounted_uncertain`
       (`rhythm.adjudicate_duration`: every beam candidate on its stem was refused --
       a neighbour's beam, a decided arc, a far-side stroke, or 2.74/2.77's ink
       refusals -- and nothing is left over the head), HEAD FILLED
       (`head_is_open` False; an open head is a half, decided by fill, and the code
       never reaches this branch for one: `not hollow` is in its gate).
  Its two candidates are always `level 0` (the head's own value, dotted if dotted) and
  `level 1` (one beam level over it): a quarter (1.0) or an eighth (0.5), a dotted
  quarter (1.5) or a dotted eighth (0.75).

THE TIP STATUS of a member -- what `Q.STEM_TIP_INK` says at the end of ITS OWN stem
the head's stem points to (top for an up-stem, bottom for a down-stem), for the stem
row `Q.HEAD_STEM` names:
  hook_seen     the row's value is True (flag-shaped ink in the window)
  clean         the row's value is False AND the right band is below the density cut
                (`STEM_TIP_INK_DENSE` 0.30): a window READ, with no ink in it
  left_inked    value False because ink also stands on the stem's LEFT (the guard);
                the right band reads dense -- NOT clean
  occupied      the reader ABSTAINED `occupied` (a beam stroke box or another
                detection lies in the window: the refused strokes themselves)
  other_abst    abstained for another reason (no mask, no staff geometry)
  no_row        neither a row nor an abstention at that end
  no_side       the head's stem direction is unknown
  no_stem       `Q.HEAD_STEM` did not decide ONE stem

THE FINAL STATE follows `supersedes` from the ADJUDICATE verdict to the one nothing
supersedes.

    python3 l281_population.py --tag litolff --ext DIR [--csv out.csv]
"""
import argparse
import collections
import csv
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged.record import Q  # noqa: E402

TIP_DENSE = 0.30            # gather.STEM_TIP_INK_DENSE -- restated only to name a cut
REASON = "beam_discounted_uncertain"


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def load(ext, tag):
    ext = Path(ext)
    d = {}
    for w in ("obs", "abs", "ver", "prov"):
        d[w] = json.loads((ext / f"{tag}-{w}.json").read_text())
    return d


def standing(rows, quantity, stage=None):
    """The last row of `quantity` (at `stage`) not superseded by a later one."""
    rs = [r for r in rows if r["q"] == quantity and (stage is None or r["stage"] == stage)]
    sup = {r["supersedes"] for r in rs if r.get("supersedes")}
    live = [r for r in rs if r["id"] not in sup]
    return live[-1] if live else (rs[-1] if rs else None)


def current_duration(rows):
    """The duration verdict nothing supersedes, over ALL stages, plus the chain."""
    rs = [r for r in rows if r["q"] == Q.DURATION]
    sup = {r["supersedes"] for r in rs if r.get("supersedes")}
    live = [r for r in rs if r["id"] not in sup]
    chain = [r["decider"] for r in sorted(rs, key=lambda r: r["id"])]
    return (live[-1] if live else None), chain


def adj_status(rows, glyph_key):
    """`readout.adjudicate_status`, over the extract's ADJUDICATE rows: (status, why)."""
    adj = [r for r in rows if r["stage"] == "ADJUDICATE"]
    last = {}
    for r in adj:
        last[r["q"]] = r
    n = last.get(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD)
    if n and n["outcome"] == "decided" and n.get("value") is True:
        return "refused", "not_a_notehead"
    wr = last.get(Q.NOTEHEAD_IS_A_WHOLE_REST)
    if wr and wr["outcome"] == "decided" and wr.get("value") is True:
        return "refused", "whole_rest"
    own = last.get(Q.GLYPH_OWNER)
    if own and own["outcome"] == "decided" and isinstance(own.get("value"), str):
        staff = "staff/" + "/".join(glyph_key.split("/")[1:4])
        if own["value"] != staff:
            return "given_away", own["value"]
    dur = last.get(Q.DURATION)
    if dur is None:
        return "abstained", "no_duration"
    return dur["outcome"], dur.get("reason")


def tip_status(glyph_key, rows, obs, absn):
    """(status, detail) -- see the module docstring."""
    cell = "cell/" + "/".join(glyph_key.split("/")[1:5])
    hs = standing(rows, Q.HEAD_STEM, "ADJUDICATE")
    if hs is None or hs["outcome"] != "decided" or not hs.get("value"):
        return "no_stem", {"head_stem": (hs or {}).get("outcome"),
                           "why": (hs or {}).get("reason")}
    stem = hs["value"]
    # the side the duration verdict itself used
    adj = standing(rows, Q.DURATION, "ADJUDICATE")
    side = ((adj or {}).get("detail") or {}).get("beam_side")
    if side not in ("up", "down"):
        sd = standing(rows, Q.STEM_DIRECTION, "ADJUDICATE")
        if sd and sd["outcome"] == "decided" and sd.get("value") in ("up", "down"):
            side = sd["value"]
        else:
            r = obs["reach"].get(glyph_key)
            side = r if r in ("up", "down") else None
    if side not in ("up", "down"):
        return "no_side", {}
    end = "top" if side == "up" else "bottom"
    tr = [t for t in obs["tips"].get(cell, []) if t["stem"] == stem and t["end"] == end]
    if tr:
        t = tr[-1]
        d = {"side": side, "end": end, "right": t["right"], "left": t["left"],
             "hooks": t["hooks"], "hmin": t["hmin"], "hmax": t["hmax"], "hwhy": t["hwhy"]}
        if t["value"]:
            return "hook_seen", d
        if t["right"] is not None and t["right"] >= TIP_DENSE:
            return "left_inked", d
        return "clean", d
    ab = [t for t in absn["tips_abs"].get(cell, []) if t["stem"] == stem and t["end"] == end]
    if ab:
        why = ab[-1]["reason"]
        return ("occupied" if why == "occupied" else "other_abst"), {"side": side, "end": end,
                                                                     "why": why}
    return "no_row", {"side": side, "end": end}


TIP_BAND_SPACES = 0.6       # a stroke whose box reaches within this of the stem's tip is AT the tip
TIP_X_SPACES = 0.3          # ... and whose x-span reaches within this of the stem's own x-span


def stroke_at_tip(glyph_key, rows, obs):
    """Does any `Q.BEAM_STROKE` row in the head's cell (CV or detector, accepted or refused) stand
    at the tip of the stem the head stands on? `None` where it cannot be asked (no decided stem,
    no side, no staff-space unit in the cell) -- never False by default.

    A probe-side definition built from rows the record already holds (it is NOT a gather reading):
    the stem's tip end is `top` for an up-stem and `bottom` for a down-stem (the side the duration
    verdict itself used); a stroke is AT the tip when its x-span reaches the stem's x-span within
    `TIP_X_SPACES` and its y-span intersects the band `TIP_BAND_SPACES` either side of the tip.
    All in the cell's canonical frame (stem boxes are `[x, y, w, h]`, `Q.CELL_STAFF_SPACE` is the
    unit)."""
    cell = "cell/" + "/".join(glyph_key.split("/")[1:5])
    hs = standing(rows, Q.HEAD_STEM, "ADJUDICATE")
    if hs is None or hs["outcome"] != "decided" or not hs.get("value"):
        return None, {}
    adj = standing(rows, Q.DURATION, "ADJUDICATE")
    side = ((adj or {}).get("detail") or {}).get("beam_side")
    if side not in ("up", "down"):
        return None, {}
    sp = obs["space"].get(cell)
    box = (obs["stems"].get(cell) or {}).get(hs["value"])
    if not sp or not box:
        return None, {}
    sx0, sy0, sw, sh = box
    sx1 = sx0 + sw
    tip = sy0 if side == "up" else sy0 + sh
    hit = []
    for bid, b in (obs["beams"].get(cell) or {}).items():
        bx, by, bw, bh = b["box"]
        if bx - TIP_X_SPACES * sp <= sx1 and bx + bw + TIP_X_SPACES * sp >= sx0 \
                and by <= tip + TIP_BAND_SPACES * sp and by + bh >= tip - TIP_BAND_SPACES * sp:
            hit.append({"id": bid, "reader": b["reader"],
                        "ink": obs["beam_ink"].get(bid)})
    return bool(hit), {"strokes_at_tip": hit}


def build(ext, tag):
    d = load(ext, tag)
    out = []
    n_heads = len(d["obs"]["heads"])
    status_counts = collections.Counter()
    for key, h in d["obs"]["heads"].items():
        rows = d["ver"]["verdicts"].get(key, [])
        st, why = adj_status(rows, key)
        status_counts[(st, why if st == "narrowed" else None)] += 1
        if st != "narrowed" or why != REASON:
            continue
        adj = standing(rows, Q.DURATION, "ADJUDICATE")
        det = adj.get("detail") or {}
        if det.get("head_is_open"):
            continue
        tip, tipd = tip_status(key, rows, d["obs"], d["abs"])
        at_tip, at_tip_d = stroke_at_tip(key, rows, d["obs"])
        cur, chain = current_duration(rows)
        out.append({
            "key": key, "cls": h["cls"], "page": int(key.split("/")[1]),
            "tip": tip, "tipd": tipd, "at_tip": at_tip, "at_tip_d": at_tip_d,
            "dots": det.get("dots_attached"),
            "ink_why": det.get("beams_not_by_ink_why"),
            "n_ink": det.get("beams_not_by_ink"),
            "neigh": det.get("beams_neighbour_staff"), "arc": det.get("beams_decided_arc"),
            "far": det.get("beams_far_side"), "stems_att": det.get("stems_attached"),
            "side": det.get("beam_side"),
            "cands": adj.get("cands"),
            "final_decider": cur["decider"] if cur else None,
            "final_stage": cur["stage"] if cur else None,
            "final_outcome": cur["outcome"] if cur else None,
            "final_reason": cur.get("reason") if cur else None,
            "final_value": (cur.get("value") if cur else None),
            "final_cands": (cur.get("cands") if cur else None),
            "chain": chain,
            "page_box": h["page"],
        })
    return d, out, n_heads, status_counts


def level_of(v):
    return None if not isinstance(v, dict) else v.get("beam_levels")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--ext", required=True)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    d, pop, n_heads, sc = build(a.ext, a.tag)
    print(f"== {a.tag}: record {d['prov'].get('commit')} dirty={d['prov'].get('dirty')}")
    print(f"heads (note glyph boxes): {n_heads}")
    nar = collections.Counter()
    for (st, why), c in sc.items():
        if st == "narrowed":
            nar[why] += c
    print(f"ADJUDICATE statuses: " + ", ".join(
        f"{k}={sum(c for (s, w), c in sc.items() if s == k)}"
        for k in ("decided", "narrowed", "abstained", "refused", "given_away")))
    print("narrowed by reason:", dict(nar.most_common()))
    print(f"\nPOPULATION P (filled head, narrowed {REASON}): {len(pop)}")
    for k, v in collections.Counter(m["tip"] for m in pop).most_common():
        print(f"  tip {k:12s} {v:5d}")
    print("  (window clean) x (a stroke box at the stem tip):",
          dict(collections.Counter((m["tip"], m["at_tip"]) for m in pop if m["tip"] == "clean")))
    print("  dots attached:", dict(collections.Counter(m["dots"] for m in pop)))
    print("  ink refusal reasons (any):", dict(collections.Counter(
        w for m in pop for w in (m["ink_why"] or {}))))
    print("  stroke classes: ink>0 %d  neighbour>0 %d  arc>0 %d  far>0 %d  none %d" % (
        sum(1 for m in pop if (m["n_ink"] or 0) > 0), sum(1 for m in pop if (m["neigh"] or 0) > 0),
        sum(1 for m in pop if (m["arc"] or 0) > 0), sum(1 for m in pop if (m["far"] or 0) > 0),
        sum(1 for m in pop if not any((m[k] or 0) > 0 for k in ("n_ink", "neigh", "arc", "far")))))
    print("\nFINAL STATE of P (what the later stages did):")
    fin = collections.Counter((m["final_stage"], m["final_decider"], m["final_outcome"]) for m in pop)
    for k, v in fin.most_common():
        print(f"  {str(k):70s} {v}")
    print("\nFINAL beam level where decided:")
    lv = collections.Counter(level_of(m["final_value"]) for m in pop if m["final_outcome"] == "decided")
    print("  ", dict(lv))
    if a.csv:
        with open(a.csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["key", "tip", "stroke_at_tip", "dots", "ink_why", "final_stage", "final_decider",
                        "final_outcome", "final_level"])
            for m in pop:
                w.writerow([m["key"], m["tip"], m["at_tip"], m["dots"], json.dumps(m["ink_why"]),
                            m["final_stage"], m["final_decider"], m["final_outcome"],
                            level_of(m["final_value"])])
    if a.json:
        Path(a.json).write_text(json.dumps(pop, separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
