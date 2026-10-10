#!/usr/bin/env python3
"""l283_compare: BASE vs ARM, two records of one tree each (GATHER+ADJUDICATE only, CLAUDE.md 6b), for ROADMAP 2.83.

Counts off `tools.omr.staged.readout`'s own `Run` (never re-derived):
  1. the `Q.STEM_TIP_INK` census: rows True / False and abstentions by reason, base and arm;
  2. every note head's standing ADJUDICATE `Q.DURATION` verdict, base -> arm (outcome:reason and the beam levels the
     candidates allow), by transition, over the heads present in BOTH (matched by glyph key, with the box checked equal);
  3. the 2.81 population P = base `beam_discounted_uncertain`: what each member became in the arm (decided eighth,
     decided quarter, still narrowed and over which levels);
  4. `--list-changed` writes the changed heads (key, base, arm) as JSON for the tile cutter.

    python3 l283_compare.py --base base.record.json --arm arm.record.json [--pages 2,7] [--list-changed out.json]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def levels_of(v):
    """The set of beam levels a duration verdict allows, and its outcome word."""
    if v is None:
        return None, frozenset()
    if v["outcome"] == "decided":
        val = v.get("value")
        return "decided", frozenset([val.get("beam_levels")] if isinstance(val, dict) else [])
    if v["outcome"] == "narrowed":
        out = set()
        for c in v.get("candidates") or []:
            val = c.get("value") if isinstance(c, dict) else None
            if isinstance(val, dict):
                out.add(val.get("beam_levels"))
        return "narrowed", frozenset(out)
    return v["outcome"], frozenset()


def head_rows(run, pages=None):
    out = {}
    for key, g in run.glyphs.items():
        if not (g.cls or "").startswith("notehead"):
            continue
        if pages is not None and g.page not in pages:
            continue
        v = run.standing(key, Q.DURATION, "ADJUDICATE")
        if v is None:
            continue
        status, _why = RD.adjudicate_status(run, g)
        outcome, lv = levels_of(v)
        out[key] = {"key": key, "page": g.page, "cls": g.cls, "box_page": g.box_page, "outcome": outcome,
                    "reason": v.get("reason"), "levels": sorted(x for x in lv if x is not None),
                    "status": status, "value": v.get("value")}
    return out


def tip_census(run, pages=None):
    c = collections.Counter()
    for o in run.observations:
        if o["quantity"] == Q.STEM_TIP_INK and _page(o["subject"], pages):
            c["observed:" + ("flag" if o["value"] else "none")] += 1
    for a in run.abstentions:
        if a["quantity"] == Q.STEM_TIP_INK and _page(a["subject"], pages):
            why = (a.get("detail") or {}).get("why")
            c["abstained:" + a["reason"] + (":" + why if why else "")] += 1
    return c


def _page(subject, pages):
    if pages is None:
        return True
    p = subject.split("/")
    try:
        return int(p[1]) in pages
    except (IndexError, ValueError):
        return False


def label(h):
    return f"{h['outcome']}:{h['reason']}{{{','.join(map(str, h['levels']))}}}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None, help="a base record (this tree, before the change)")
    ap.add_argument("--base-overnight", default=None,
                    help="`l283_overnight_base.py` JSON: standing duration verdicts of pages the base record does not hold "
                         "(same GATHER+ADJUDICATE code, FINDINGS 2.83)")
    ap.add_argument("--arm", required=True)
    ap.add_argument("--pages", default=None)
    ap.add_argument("--list-changed", default=None)
    ap.add_argument("--top", type=int, default=25)
    a = ap.parse_args()
    pages = {int(x) for x in a.pages.split(",")} if a.pages else None
    A = RD.load_run(a.arm)
    print(f"arm  {a.arm}\n   provenance {A.provenance.get('commit')} dirty={A.provenance.get('dirty')}")
    ha = head_rows(A, pages)
    hb = {}
    B = None
    if a.base:
        B = RD.load_run(a.base)
        print(f"base {a.base}\n   provenance {B.provenance.get('commit')} dirty={B.provenance.get('dirty')}")
        hb = head_rows(B, pages)
    if a.base_overnight:
        on = json.loads(Path(a.base_overnight).read_text())
        for k, v in on.items():
            if k in hb or k not in ha:
                continue
            hb[k] = {"key": k, "page": ha[k]["page"], "cls": ha[k]["cls"], "box_page": ha[k]["box_page"],
                     "outcome": v["outcome"], "reason": v["reason"], "levels": v["levels"], "status": ha[k]["status"],
                     "value": None}
        print(f"base (overnight verdicts, same code) {a.base_overnight}: {len(on)} verdicts")
    both = sorted(set(hb) & set(ha))
    box_mismatch = [k for k in both if hb[k]["box_page"] != ha[k]["box_page"]
                    and (hb[k]["box_page"] is None or ha[k]["box_page"] is None
                         or max(abs(x - y) for x, y in zip(hb[k]["box_page"], ha[k]["box_page"])) > 1.0)]
    print(f"\nheads with a standing duration verdict: base {len(hb)}  arm {len(ha)}  in both {len(both)} "
          f"(only base {len(set(hb) - set(ha))}, only arm {len(set(ha) - set(hb))}); box moved > 1px in {len(box_mismatch)}")
    print("\nQ.STEM_TIP_INK census")
    cb, ca = (tip_census(B, pages) if B is not None else collections.Counter()), tip_census(A, pages)
    for k in sorted(set(cb) | set(ca)):
        print(f"  {k:55s} base {cb.get(k, 0):6d}   arm {ca.get(k, 0):6d}")
    kept = [k for k in both if hb[k]["status"] == ha[k]["status"] and k not in box_mismatch]
    trans = collections.Counter()
    changed = []
    for k in both:
        if k in box_mismatch:
            continue
        lb, la = label(hb[k]), label(ha[k])
        if lb != la:
            trans[(lb, la)] += 1
            changed.append({"key": k, "page": hb[k]["page"], "base": lb, "arm": la, "base_status": hb[k]["status"],
                            "arm_status": ha[k]["status"], "box_page": ha[k]["box_page"]})
    print(f"\nduration verdicts changed (matched heads): {sum(trans.values())} of {len(both) - len(box_mismatch)}")
    for (lb, la), n in trans.most_common(a.top):
        print(f"  {n:5d}  {lb}  ->  {la}")
    # the 2.81 population
    P = [k for k in both if hb[k]["reason"] == "beam_discounted_uncertain" and hb[k]["outcome"] == "narrowed"
         and hb[k]["status"] not in ("refused", "given_away")]
    print(f"\n2.81 population P (base beam_discounted_uncertain, kept by ADJUDICATE): {len(P)}")
    res = collections.Counter()
    for k in P:
        h = ha[k]
        if h["outcome"] == "decided":
            lv = h["levels"][0] if h["levels"] else None
            res[f"decided level {lv} ({h['reason']})"] += 1
        elif h["outcome"] == "narrowed":
            res[f"narrowed {h['reason']} levels {h['levels']}"] += 1
        else:
            res[f"{h['outcome']}:{h['reason']}"] += 1
    for k, n in res.most_common():
        print(f"  {n:5d}  {k}")
    arm_status = collections.Counter(RD.adjudicate_status(A, A.glyphs[k])[0] for k in P)
    print("  (status of those heads in the arm:", dict(arm_status), ")")
    if a.list_changed:
        Path(a.list_changed).write_text(json.dumps(changed, indent=1, default=str))
        print("wrote", a.list_changed, len(changed))


if __name__ == "__main__":
    main()
