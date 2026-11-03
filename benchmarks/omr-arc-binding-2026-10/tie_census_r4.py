"""ROADMAP 2.252 r4 -- every PROBABLE tie on a page and the stage that kept it out of the file (STAGED).

A probable tie is MY geometric reading, never Sean's: one printed arc (`Q.SYSTEM_ARC`'s joined pieces, else one arc box)
whose two ends each lie beside a head of the same staff, the two heads' OWN INK (`Q.HEAD_INK` trimmed extent, page
raster) standing at one height (|dy| <= 0.3 sp) -- the convention a tie is checked by (page-facts: two adjacent notes,
one pitch). It says where to look; it never says what is right.

Each probable tie not written in the file (tie start on the first head, tie stop on the second, any voice, a mark's
other box counted as the same head) is traced to the first stage that dropped it:
  not an arc -> kind slur (head steps read off the boxes differ: is either box TALL or CLIPPED?) -> kind slur, arc never
  joined -> tie pair refused (reason) -> paired other heads -> decided, not written (pitch / spelling / unison).

    python3 benchmarks/omr-arc-binding-2026-10/tie_census_r4.py REC.json --sp 15.75 [--xml FILE] [--json OUT]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as E            # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

DY_MAX_SP = 0.40          # own-ink centres at one height (a step is 0.5 sp; the ink extent is noisy)
TALL_HEADS = 1.6          # a head box this many standard head heights tall (1.0 sp) is TALL
CLIP_SP = 0.15            # the head's own ink runs this far past the box (top or bottom): the box is CLIPPED


def _p(key):
    return tuple(int(x) for x in str(key).split("/")[1:])


def written(xml):
    out = collections.defaultdict(list)
    for n in ET.fromstring(xml).iter("note"):
        rg = n.get("rg")
        if not rg:
            continue
        p = n.find("pitch")
        pitch = None if p is None else (p.findtext("step"), p.findtext("alter") or "0", p.findtext("octave"))
        out[rg].append(dict(tie=[t.get("type") for t in n.findall("tie")], pitch=pitch, voice=n.findtext("voice")))
    return out


def census(result, xml, sp):
    rec = E.Record(result)
    _REC["rec"] = rec
    std = lambda q: {v["subject"]: v for v in rec.verdicts_of(q) if rec.verdict(q, v["subject"]) is v}
    notarc, kinds, tiep, nothead = std("arc_is_not_an_arc"), std("arc_kind"), std("tie_pair"), std("notehead_is_not_a_notehead")
    wr = written(xml)
    boxes, cls, pos, ink = {}, {}, {}, {}
    sysarc, sys_abst, group = {}, {}, {}
    for o in rec.observations:
        q, s, d = o["quantity"], o["subject"], o.get("detail") or {}
        if q == "glyph_box" and d.get("bbox_page_px"):
            boxes[s], cls[s] = d["bbox_page_px"], str((o.get("value") or [""])[0])
        elif q == "notehead_staff_position":
            pos[s] = o["value"]
        elif q == "head_ink" and d.get("trimmed"):
            ink[s] = d["trimmed"]
        elif q == "system_arc":
            sysarc[s] = o
        elif q == "mark_group":
            group[s] = str(o["value"])
    for a in rec.abstentions:
        if a.get("quantity") == "system_arc":
            sys_abst[a["subject"]] = (a.get("detail") or {}).get("note") or a.get("reason")
    members = collections.defaultdict(list)
    for s, g in group.items():
        members[g].append(s)
    same_mark = lambda s: set(members.get(group.get(s), [s])) | {s}
    heads = [s for s, c in cls.items() if c.startswith("notehead") and not ((nothead.get(s) or {}).get("value") is True)]
    by_staff = collections.defaultdict(list)
    for h in heads:
        by_staff[_p(h)[:3]].append(h)
    # one printed arc: a system arc's pieces, else one arc box
    arcs, done = [], set()
    for s, c in cls.items():
        if c not in ("tie", "slur") or s in done:
            continue
        o = sysarc.get(s)
        pieces = list((o.get("detail") or {}).get("pieces") or [s]) if o else [s]
        pieces = [p for p in pieces if p in boxes] or [s]
        done.update(pieces)
        bb = [boxes[p] for p in pieces]
        arcs.append(dict(pieces=pieces, box=[min(b[0] for b in bb), min(b[1] for b in bb), max(b[2] for b in bb), max(b[3] for b in bb)],
                         sysarc=(o or {}).get("value") if o else None, sys_note=None if o else sys_abst.get(s)))

    def cy(h):
        t = ink.get(h) or boxes[h]
        return (t[1] + t[3]) / 2.0

    def end_head(a, left):
        x0, y0, x1, y1 = a["box"]
        pg, sy, st = _p(a["pieces"][0])[:3]
        best = None
        for h in by_staff[(pg, sy, st)] + by_staff[(pg, sy, st + 1)] + by_staff[(pg, sy, st - 1)]:
            hb = boxes[h]
            if left and not (x0 - 1.5 * sp <= hb[2] <= x0 + 1.5 * sp):
                continue
            if not left and not (x1 - 1.5 * sp <= hb[0] <= x1 + 1.5 * sp):
                continue
            c = cy(h)
            if not (y0 - 2.5 * sp <= c <= y1 + 2.5 * sp):
                continue
            ends_y = y1 if c > y1 else (y0 if c < y0 else c)
            d = abs((hb[2] if left else hb[0]) - (x0 if left else x1)) / sp + abs(c - ends_y) / sp
            if best is None or d < best[0]:
                best = (d, h)
        return best[1] if best else None

    out, seen = [], set()
    for a in arcs:
        hl, hr = end_head(a, True), end_head(a, False)
        if not hl or not hr or hl in same_mark(hr):
            continue
        side = "above" if (a["box"][1] + a["box"][3]) / 2.0 < cy(hl) else "below"
        key = (min(same_mark(hl)), min(same_mark(hr)), side)
        dy = (cy(hr) - cy(hl)) / sp
        if abs(dy) > DY_MAX_SP:
            continue
        def carries(h, want):
            notes = [n for m in same_mark(h) for n in wr.get(m, [])]
            if len(notes) == 2:          # a unison written as two voices (2.175: up first): the arc's side names the voice
                notes = notes[:1] if side == "above" else notes[1:]
            return any(want in n["tie"] for n in notes)
        ok = carries(hl, "start") and carries(hr, "stop")
        cause = "written" if ok else _cause(a, hl, hr, notarc, kinds, tiep, wr, same_mark, boxes, ink, pos, sp)
        out.append(dict(arc=a["pieces"][0], pieces=a["pieces"], left=hl, right=hr, dy_ink_sp=round(dy, 3), side=side,
                        ink_both=(hl in ink and hr in ink), key=key,
                        pos=(pos.get(hl), pos.get(hr)), cause=cause))
    best = {}
    for r in out:                       # one printed tie read by several arc boxes: counted once, its best fate
        k = r["key"]
        if k not in best or (r["cause"] == "written" and best[k]["cause"] != "written"):
            best[k] = r
    return list(best.values())


_REC = {}


def _why_unwritten(h):
    """The first standing verdict on `h` that keeps a note out of the file."""
    rec = _REC.get("rec")
    if rec is None:
        return "?"
    for q, bad in (("notehead_is_not_a_notehead", lambda v: v.get("value") is True),
                   ("glyph_owner", lambda v: v.get("outcome") != "decided"),
                   ("duration", lambda v: v.get("outcome") != "decided"),
                   ("pitch", lambda v: v.get("outcome") != "decided")):
        v = rec.verdict(q, h)
        if v is not None and bad(v):
            return "%s %s %s" % (q, v.get("outcome"), v.get("reason"))
    return "no verdict keeps it out"


def box_fault(h, boxes, ink, sp):
    b, t = boxes[h], ink.get(h)
    if (b[3] - b[1]) >= TALL_HEADS * sp:
        return "TALL"
    if t and (b[1] - t[1] > CLIP_SP * sp or t[3] - b[3] > CLIP_SP * sp):
        return "CLIPPED"
    return "box ok"


def _cause(a, hl, hr, notarc, kinds, tiep, wr, same_mark, boxes, ink, pos, sp):
    ps = a["pieces"]
    if all((notarc.get(p) or {}).get("value") is True for p in ps):
        return "ADJUDICATE not an arc: %s" % (notarc.get(ps[0]) or {}).get("reason")
    for h in (hl, hr):
        if not any(wr.get(m) for m in same_mark(h)):
            return "EXPORT: an end note is not written (%s)" % _why_unwritten(h)
    steps = tuple(int(round(pos[h])) if pos.get(h) is not None else None for h in (hl, hr))
    faults = "/".join(box_fault(h, boxes, ink, sp) for h in (hl, hr))
    dec = [tiep[p] for p in ps if (tiep.get(p) or {}).get("outcome") == "decided"]
    if dec:
        v = dec[0]["value"]
        if not ({v["start"]} & same_mark(hl) and {v["stop"]} & same_mark(hr)):
            return "ADJUDICATE paired other heads"
        p0 = [n["pitch"] for m in same_mark(hl) for n in wr.get(m, [])]
        p1 = [n["pitch"] for m in same_mark(hr) for n in wr.get(m, [])]
        if p0 and p1 and not (set(p0) & set(p1)):
            if {(x[0], x[2]) for x in p0} & {(x[0], x[2]) for x in p1}:
                return "EXPORT: spelling differs (%s -> %s)" % (p0[0], p1[0])
            return "EXPORT: pitch contradiction, steps %s, boxes %s" % (steps, faults)
        return "EXPORT: decided, not written (voices / unison)"
    for p in ps:
        k = kinds.get(p) or {}
        if k.get("value") == "slur":
            pb = ((k.get("detail") or {}).get("grammar") or {}).get("page_binding") or {}
            rule = pb.get("rule") or pb.get("why")
            if steps[0] is not None and steps[0] != steps[1]:
                return "ADJUDICATE kind slur: box steps differ %s, boxes %s" % (steps, faults)
            if pb.get("sysarc_id") or a["sysarc"]:
                return "ADJUDICATE kind slur (system arc %s; binding %s)" % (a["sysarc"], str(rule)[:40])
            return "ADJUDICATE kind slur: arc never joined (%s)" % (a["sys_note"],)
    for p in ps:
        t = tiep.get(p) or {}
        if t.get("outcome") in ("abstained", "narrowed") and t.get("reason") not in ("not_a_tie", "not_an_arc"):
            extra = (" steps %s, boxes %s" % (steps, faults)) if t.get("reason") in ("no_pair_at_one_position",) else ""
            return "ADJUDICATE tie pair %s: %s%s" % (t.get("outcome"), t.get("reason"), extra)
    k = kinds.get(ps[0]) or {}
    return "other (kind %s/%s)" % (k.get("outcome"), k.get("value") or k.get("reason"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--sp", type=float, required=True)
    ap.add_argument("--xml", default="")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    result = load_record(a.record)
    if "record" not in result:
        result = {"record": result, "summary": {}}
    if a.xml and pathlib.Path(a.xml).exists():
        xml = pathlib.Path(a.xml).read_text()
    else:
        from tools.omr.staged.lane_report import traced_export
        with traced_export():
            xml, _r = E.to_musicxml(result)
        if a.xml:
            pathlib.Path(a.xml).write_text(xml)
    rows = census(result, xml, a.sp)
    for r in rows:
        if r["cause"] != "written":
            print("%-22s %-22s -> %-22s dy %+.2f | %s" % (r["arc"], r["left"], r["right"], r["dy_ink_sp"], r["cause"]))
    c = collections.Counter(r["cause"] for r in rows)
    print("probable ties (my reading): %d; written %d" % (len(rows), c.get("written", 0)))
    for k, n in c.most_common():
        print("  %3d  %s" % (n, k))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(dict(rows=rows, counts=c), default=str, indent=1))


if __name__ == "__main__":
    main()
