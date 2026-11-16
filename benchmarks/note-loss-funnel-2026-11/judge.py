"""ROADMAP 2.311 -- THE COUNT THAT JUDGES A READER: right / wrong / unread per kind of mark, on the cells Sean fully judged.

    # one record -> facts (export with the record's own flags in the environment; run from the tree that made the record)
    PYTHONPATH=. python3 benchmarks/note-loss-funnel-2026-11/extract.py REC.record.json REC.facts.json
    # the count (any tree; reads only the facts file and the page file)
    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/judge.py REC.facts.json \
        [--truth data/hand-truth/pages/imslp317803/0.json] [--arcs PAGEPASS.json] [--json OUT] [--examples N]

docs/measuring.md §0 (Sean 2026-11-16): "Only cells that I've actually fully judged everything in them." TRUTH is every
box of the page file whose cell is a MEASURE cell whose `inspected` holds `all-ink` (cell_id; Brahms p0: 104 of 112 cells,
1,456 boxes). A written mark is in scope when its box centre lies in such a cell and in no unswept measure cell. Every
match is BY PLACE (page pixels; `judged.boxes_overlap` for marks of one box, the rules below for attachments), never by id.

  RIGHT   written, and it is what he labelled
  WRONG   written, and it is not: a fake (no label of that kind under it), a wrong value / kind / owner staff
  UNREAD  he labelled it, the file does not carry it
WRONG is printed first. For an UNREAD note the funnel's first stage that lost it (funnel.py, the exporter's own fate name);
for a WRONG mark what Sean's labels say is there and what the record's other boxes there were.

WHAT IS OURS, NOT HIS (said wherever a number rests on it): his boxes carry no value, owner or pitch. The scorer ATTACHES his
boxes by geometry -- a stem to a head (its x within 0.45 sp of the head's side edge, overlapping it in y), a beam to a stem
(the beam box spans the stem's x and meets its y-range), a flag to a stem (starts at the stem's x), a dot to a head (right of
it within 2 sp, |dy| <= 0.6 sp), an accidental to a head (left of it within 2.5 sp, |dy| <= 0.6 sp) -- and derives a value
(hollow -> half, black -> quarter halved per beam/flag level, x1.5 per dot), a stem direction (the stem's far end above or
below the head) and an owner staff (`hand_truth.score.truth_items(derive=True)`: the staff the head sits in, or for a far head
the staff his ledger lines lead to -- Sean judged all 92 far heads of this page connected to the right staff, 2026-10-10).
Pitch is NOT scored: his labels state no pitch, and clef/key-free position checks would be ours.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from tools.omr.hand_truth import score as S
from tools.omr.hand_truth import store
from tools.omr.staged.judged import boxes_overlap

import funnel as F  # noqa: E402

TRUTH = "data/hand-truth/pages/imslp317803/0.json"
ARCS = "/Users/seanjohnson/Desktop/ReEngrave/out/print-from-worktrees/2.287-r1/0.pagepass.sean-snapshot2.json"
SP = 32.0      # Brahms 317803 at 600 dpi (lane_report.PLATES unit)
BEATS = {"whole": 4.0, "half": 2.0, "quarter": 1.0, "eighth": 0.5, "16th": 0.25, "32nd": 0.125}
ACC = {"accidentalSharp": "sharp", "accidentalFlat": "flat", "accidentalNatural": "natural",
       "accidentalDoubleSharp": "double-sharp", "accidentalDoubleFlat": "flat-flat"}
CLEF = {"clefG": "G2", "clefF": "F4", "clefCAlto": "C3", "clefCTenor": "C4"}


def cx(r):
    return (r[0] + r[2]) / 2


def cy(r):
    return (r[1] + r[3]) / 2


class Count:
    def __init__(self):
        self.n = collections.Counter()
        self.ex = collections.defaultdict(list)

    def add(self, what, why, item=None):
        self.n[what] += 1
        self.ex[(what, why)].append(item)


# ───────────────────────── the truth side (his boxes; attachments are ours) ─────────────────────────

def load_truth(path):
    page = store.load(Path(path))
    swept = [c for c in page.cells if c.kind == "measure" and "all-ink" in c.inspected]
    unswept = [c for c in page.cells if c.kind == "measure" and "all-ink" not in c.inspected]
    ids = {c.id for c in swept}
    items = S.truth_items(page, derive=True)
    truth = [it for it in items if it.cell_id in ids]
    unit = SP     # the page file's staff_line_ys are in the cell's canonical frame, not page pixels

    def in_scope(box):
        x, y = cx(box), cy(box)
        inside = lambda c: c.rect[0] <= x < c.rect[2] and c.rect[1] <= y < c.rect[3]
        return any(inside(c) for c in swept) and not any(inside(c) for c in unswept)
    return page, truth, unit, in_scope, swept


def attach(truth, u):
    heads = [it for it in truth if it.family == "notehead"]
    stems = [it for it in truth if it.family == "stem"]
    beams = [it for it in truth if it.family == "beam"]
    flags = [it for it in truth if it.family == "flag"]
    dots = [it for it in truth if it.family == "augmentation_dot"]
    accs = [it for it in truth if it.family == "accidental"]
    att = {}
    for h in heads:
        r = h.rect
        st = []
        for s in stems:
            sx = cx(s.rect)
            side = "R" if abs(sx - r[2]) <= 0.45 * u else ("L" if abs(sx - r[0]) <= 0.45 * u else None)
            if side and s.rect[1] <= r[3] + 0.3 * u and s.rect[3] >= r[1] - 0.3 * u:
                st.append(s)
        a = dict(stem=None, direction=None, levels=0, beam_levels=0, flag_levels=0, dots=0, acc=None)
        if st:
            # the stem nearest an edge of THIS head (a neighbour's stem can stand within reach of the other edge)
            s = min(st, key=lambda s: min(abs(cx(s.rect) - r[2]), abs(cx(s.rect) - r[0])))
            a["stem"] = s
            # page-facts §5: stem up -> at the head's right, down -> at its left (a stem that runs through a head, as in two
            # voices or a chord's inner head, has no "far end" to read, so the side decides)
            a["direction"] = "up" if abs(cx(s.rect) - r[2]) < abs(cx(s.rect) - r[0]) else "down"
            sx = cx(s.rect)
            a["beam_levels"] = sum(1 for b in beams if b.rect[0] - 0.4 * u <= sx <= b.rect[2] + 0.4 * u
                                   and b.rect[1] <= s.rect[3] + 1.0 * u and b.rect[3] >= s.rect[1] - 1.0 * u)
            a["flag_levels"] = sum(1 for f in flags if f.rect[0] - 0.6 * u <= sx <= f.rect[2]
                                   and f.rect[1] <= s.rect[3] + 1.0 * u and f.rect[3] >= s.rect[1] - 1.0 * u)
        att[h.id] = a
    # a dot belongs to the ONE head nearest on its left (a chord's dots stack, one per head)
    for d in dots:
        best = None
        for h in heads:
            dx, dy = (cx(d.rect) - h.rect[2]) / u, abs(cy(d.rect) - cy(h.rect)) / u
            if -0.2 <= dx <= 2.0 and dy <= 0.8 and (best is None or dx + dy < best[0]):
                best = (dx + dy, h)
        if best:
            att[best[1].id].setdefault("dot_x", []).append(cx(d.rect))
    for h in heads:     # dots side by side are a double dot; dots stacked over a chord are one dot per head
        xs = sorted(att[h.id].pop("dot_x", []))
        att[h.id]["dots"] = sum(1 for i, x in enumerate(xs) if i == 0 or x - xs[i - 1] > 0.5 * u)
        att[h.id]["_dx"] = xs
    # every head on one stem shares one written value (page-facts): beams, flags and dots are the stem's
    mates = collections.defaultdict(list)
    for h in heads:
        if att[h.id]["stem"] is not None:
            mates[att[h.id]["stem"].id].append(h.id)
    for ids in mates.values():
        for key in ("beam_levels", "flag_levels", "dots"):
            m = max(att[i][key] for i in ids)
            for i in ids:
                att[i][key] = m
    for h in heads:
        a = att[h.id]
        a["levels"] = max(a["beam_levels"], a["flag_levels"])
        # his boxes say beam or flag PRESENT, not how many levels (one box may hold two beams): the value is a CLASS
        k = F.kind_of_cls(h.cls)
        a["value"] = (k if k in ("whole", "half") else ("short" if a["levels"] else "quarter"), min(a["dots"], 2))
    for ac in accs:
        best = None
        for h in heads:
            dx = (h.rect[0] - ac.rect[2]) / u
            dy = abs(cy(h.rect) - cy(ac.rect)) / u
            if -0.4 <= dx <= 3.0 and dy <= 0.6:
                if best is None or dy + 0.2 * dx < best[0]:     # the head at the accidental's own height first
                    best = (dy + 0.2 * dx, h)
        if best:
            att[best[1].id]["acc"] = ACC.get(ac.cls, ac.cls)
    return heads, att


# ───────────────────────── the written side (the exported file, traced to page places) ─────────────────────────

def written_beats(h):
    b = BEATS.get(h.get("type"))
    if b is None:
        return None
    return b * (2 - 0.5 ** len((h.get("sub") or {}).get("dot") or []))


def written_staff(h, glyphs):
    """The staff the written note stands on: its glyph key's, or the owner a relocation wrote it to."""
    g = glyphs.get(h["rg"]) or {}
    p = h["rg"].split("/")
    own = (int(p[2]), int(p[3]))
    if g.get("fate") == "written_relocated":
        v = ((g.get("v") or {}).get("glyph_owner") or {}).get("value")
        m = re.search(r"staff/\d+/(\d+)/(\d+)", str(v))
        if m:
            own = (int(m.group(1)), int(m.group(2)))
    return own


def xml_arcs(xml, glyph_box):
    """Written ties and slurs as (kind, start rg, stop rg or None): ties paired by part + pitch, slurs by part + number."""
    root = ET.fromstring(xml)
    out = []
    for part in root.iter("part"):
        open_tie, open_slur = {}, {}
        for note in part.iter("note"):
            rg = note.get("rg")
            p = note.find("pitch")
            pitch = None if p is None else (p.findtext("step"), p.findtext("alter"), p.findtext("octave"))
            for t in note.findall("tie"):
                if t.get("type") == "start":
                    open_tie[pitch] = rg
                elif t.get("type") == "stop":
                    out.append(("tie", open_tie.pop(pitch, None), rg))
            nt = note.find("notations")
            if nt is not None:
                for s in nt.findall("slur"):
                    n = s.get("number", "1")
                    if s.get("type") == "start":
                        open_slur[n] = rg
                    elif s.get("type") == "stop":
                        out.append(("slur", open_slur.pop(n, None), rg))
        out += [("tie", rg, None) for rg in open_tie.values()] + [("slur", rg, None) for rg in open_slur.values()]
    return [(k, a, b, glyph_box(a), glyph_box(b)) for k, a, b in out]


def header_xml(xml):
    """{part: [(measure, kind, value)]} for clef / key / time in the written file."""
    root = ET.fromstring(xml)
    out = collections.defaultdict(list)
    for part in root.iter("part"):
        for m in part.findall("measure"):
            for at in m.findall("attributes"):
                for c in at.findall("clef"):
                    out[part.get("id")].append((m.get("number"), "clef", "%s%s" % (c.findtext("sign"), c.findtext("line"))))
                for c in at.findall("key"):
                    out[part.get("id")].append((m.get("number"), "key", c.findtext("fifths")))
                for c in at.findall("time"):
                    out[part.get("id")].append((m.get("number"), "time", "%s/%s" % (c.findtext("beats"), c.findtext("beat-type"))))
    return out


# ───────────────────────── the count ─────────────────────────

def judge(facts, truth_path=TRUTH, arcs_path=ARCS, page_no=0):
    page, truth, u, in_scope, swept = load_truth(truth_path)
    heads, att = attach(truth, u)
    glyphs = facts["glyphs"]
    pg = {k: g for k, g in glyphs.items() if g["page"] == page_no}
    # MusicXML puts <beam> on a chord's FIRST note only; a chord member is drawn on that stem, so it takes that note's beam
    # / flag (lane_report.parse_symbols reads a beamed chord member as "flag": a parse artefact, not a written flag)
    main = None
    for h in facts["written"]:
        if h["kind"] != "note":
            continue
        if not h.get("chord"):
            main = h
        elif main is not None:
            sub = dict(h.get("sub") or {})
            sub.pop("beam", None)
            sub.pop("flag", None)
            for k in ("beam", "flag"):
                if (main.get("sub") or {}).get(k):
                    sub[k] = main["sub"][k]
            h["sub"] = sub
    written = [h for h in facts["written"] if h["page"] == page_no]
    wnotes = [h for h in written if h["kind"] == "note"]
    wrests = [h for h in written if h["kind"] == "rest"]
    C = collections.defaultdict(Count)

    # notes: one written note answers one head, best overlap first
    pairs = sorted(((boxes_overlap(h["box"], t.rect)[1], i, j) for i, t in enumerate(heads) for j, h in enumerate(wnotes)
                    if boxes_overlap(h["box"], t.rect)[0]), reverse=True)
    t2w, used = {}, set()
    for _iou, i, j in pairs:
        if i in t2w or j in used:
            continue
        t2w[i] = j
        used.add(j)
    funnel_rows = {r["id"]: r for r in F.run(facts, page_no)["rows"]} if hasattr(F, "run") else {}
    for i, t in enumerate(heads):
        a = att[t.id]
        if i not in t2w:
            fr = funnel_rows.get(t.id) or {}
            why = "%s: %s" % (fr.get("bucket", "?"), fr.get("reason", "?"))
            for kind in ("note", "note value"):
                C[kind].add("unread", why, t.id)
            if a["acc"]:
                C["accidental"].add("unread", "head not written", t.id)
            if a["dots"]:
                C["dot"].add("unread", "head not written", t.id)
            if a["stem"] is not None:
                C["stem"].add("unread", "head not written", t.id)
            if a["beam_levels"]:
                C["beam"].add("unread", "head not written", t.id)
            if a["flag_levels"]:
                C["flag"].add("unread", "head not written", t.id)
            continue
        h = wnotes[t2w[i]]
        g = pg.get(h["rg"]) or {}
        own, truth_own = written_staff(h, glyphs), t.derived_owner
        if truth_own is not None and tuple(truth_own) != tuple(own):
            C["note"].add("wrong", "written on staff %s, his ledgers/staff say %s" % (own, tuple(truth_own)), t.id)
        elif F.kind_of_type(h["type"]) != F.kind_of_cls(t.cls):
            C["note"].add("wrong", "head kind: his %s, written %s" % (t.cls, h["type"]), t.id)
        else:
            C["note"].add("right", "", t.id)
        wd0 = min(len((h.get("sub") or {}).get("dot") or []), 2)
        wcls = h["type"] if h["type"] in ("whole", "half", "quarter") else "short"
        if (wcls, wd0) == a["value"]:
            C["note value"].add("right", "", t.id)
        else:
            C["note value"].add("wrong", "his %s%s, written %s%s" % (a["value"][0], "." * a["value"][1], h["type"], "." * wd0), t.id)
        wacc = ((h.get("sub") or {}).get("accidental") or [None])[0]
        if a["acc"]:
            if wacc == a["acc"]:
                C["accidental"].add("right", "", t.id)
            elif wacc:
                C["accidental"].add("wrong", "his %s, written %s" % (a["acc"], wacc), t.id)
            else:
                C["accidental"].add("unread", "note written, no accidental", t.id)
        elif wacc:
            C["accidental"].add("wrong", "fake: written %s, no accidental labelled before the head" % wacc, t.id)
        wd = len((h.get("sub") or {}).get("dot") or [])
        if a["dots"]:
            C["dot"].add("right" if wd == a["dots"] else ("wrong" if wd else "unread"),
                         "" if wd == a["dots"] else ("his %d, written %d" % (a["dots"], wd) if wd else "note written undotted"), t.id)
        elif wd:
            C["dot"].add("wrong", "fake: written dotted, no dot labelled beside the head", t.id)
        sd = ((g.get("v") or {}).get("stem_direction") or {})
        rd = sd.get("value") if sd.get("outcome") == "decided" else None
        if a["stem"] is not None:
            C["stem"].add("right" if rd == a["direction"] else ("wrong" if rd else "unread"),
                          "" if rd == a["direction"] else ("his %s, record %s" % (a["direction"], rd) if rd else
                                                           "stem direction %s (%s)" % (sd.get("outcome"), sd.get("reason"))), t.id)
        elif rd and F.kind_of_cls(t.cls) != "whole":
            C["stem"].add("wrong", "fake: record decided a stem %s, none labelled at the head" % rd, t.id)
        bl = (h.get("sub") or {}).get("beam") or []
        nb = len(str(bl[0]).split("/")) if bl else 0
        wf = 1 if (h.get("sub") or {}).get("flag") else 0
        if a["beam_levels"]:
            if nb:       # presence only: one of his beam boxes may hold two beams, so levels are not compared
                C["beam"].add("right", "", t.id)
            elif wf:     # a short note written with no <beam> is drawn with a FLAG: a written mark that is not on the page
                C["beam"].add("wrong", "written as a flagged %s; he labelled a beam" % h["type"], t.id)
            else:
                C["beam"].add("unread", "written %s, no beam" % h["type"], t.id)
        elif nb:
            C["beam"].add("wrong", "fake: written beamed (%d), no beam labelled on its stem" % nb, t.id)
        if a["beam_levels"]:
            pass         # a beamed note's flag question is the beam's (counted once, above)
        elif a["flag_levels"]:
            C["flag"].add("right" if wf and not nb else ("wrong" if nb else "unread"),
                          "" if wf and not nb else ("written beamed" if nb else "written %s, no flag" % h["type"]), t.id)
        elif wf:
            C["flag"].add("wrong", "fake: written flagged %s, no flag labelled on its stem" % h["type"], t.id)
    # fake notes: written in scope, answering no head
    tall = [t for t in truth]
    for j, h in enumerate(wnotes):
        if j in used or not in_scope(h["box"]):
            continue
        under = sorted({t.cls for t in tall if boxes_overlap(h["box"], t.rect)[0]})
        if any(t.family == "notehead" and boxes_overlap(h["box"], t.rect)[0] for t in heads):
            why = "second note written on one labelled head"
        else:
            why = "fake: under it he labelled " + (",".join(under) if under else "nothing")
        C["note"].add("wrong", why, h["rg"])
    # rests
    trests = [t for t in truth if t.family == "rest"]
    rp = sorted(((boxes_overlap(h["box"], t.rect)[1], i, j) for i, t in enumerate(trests) for j, h in enumerate(wrests)
                 if boxes_overlap(h["box"], t.rect)[0]), reverse=True)
    r2w, rused = {}, set()
    for _iou, i, j in rp:
        if i in r2w or j in rused:
            continue
        r2w[i] = j
        rused.add(j)
    want = {"restWhole": ("whole", "?"), "restQuarter": ("quarter",), "rest8th": ("eighth",), "rest16th": ("16th",), "restHalf": ("half",)}
    for i, t in enumerate(trests):
        if i in r2w:
            h = wrests[r2w[i]]
            ok = h["type"] in want.get(t.cls, ())
            C["rest"].add("right" if ok else "wrong", "" if ok else "his %s, written %s" % (t.cls, h["type"]), t.id)
        else:
            asnote = [h for h in wnotes if boxes_overlap(h["box"], t.rect)[0]]
            if asnote:
                C["rest"].add("wrong", "written as a %s note" % asnote[0]["type"], t.id)
            else:
                cp = [g["fate"] for g in pg.values() if (g["rest"] or g["head"]) and boxes_overlap(g["box"], t.rect)[0]]
                C["rest"].add("unread", ("fates: " + ",".join(sorted({str(x) for x in cp}))) if cp else "no box", t.id)
    for j, h in enumerate(wrests):
        if j in rused or not in_scope(h["box"]):
            continue
        under = sorted({t.cls for t in tall if boxes_overlap(h["box"], t.rect)[0]})
        C["rest"].add("wrong", "fake rest: under it he labelled " + (",".join(under) if under else "nothing"), h["rg"])
    # arcs: his PAGE-PASS arcs (DECISIONS 2026-11-10: per-cell arc labels are cut pieces), both ends in swept cells
    arcs_note = None
    try:
        pp = json.load(open(arcs_path))
        tarcs = [x for x in pp["labels"] if x["kind"] == "arc" and x["state"] == "confirmed"]
    except OSError:
        tarcs, arcs_note = [], "page-pass arc file not found: ties/slurs not scored"
    gb = lambda rg: (glyphs.get(rg) or {}).get("box") if rg else None
    warcs = xml_arcs(facts["xml"], gb) if facts.get("xml") else []
    tol = 2.0 * u

    def near(box, x, y0, y1):
        return box is not None and abs(cx(box) - x) <= tol and y0 - 3 * u <= cy(box) <= y1 + 3 * u
    used_w = set()
    for ta in tarcs:
        r = ta["shape"]["rect"]
        if not (in_scope([r[0], r[1], r[0] + 1, r[3]]) and in_scope([r[2] - 1, r[1], r[2], r[3]])):
            continue
        kind = ta.get("sub")
        hit = None
        for n, (k, a, b, ba, bb) in enumerate(warcs):
            ends = (near(ba, r[0], r[1], r[3]), near(bb, r[2], r[1], r[3]))
            if (ends[0] and ends[1]) or (ends[0] and bb is None) or (ends[1] and ba is None):
                if hit is None or k == kind:
                    hit = (n, k)
        if hit is None:
            C[kind].add("unread", "no written %s or %s with these ends" % ("tie", "slur"), ta["id"])
        else:
            used_w.add(hit[0])
            C[kind].add("right" if hit[1] == kind else "wrong", "" if hit[1] == kind else "written as a %s" % hit[1], ta["id"])
    for n, (k, a, b, ba, bb) in enumerate(warcs):
        if n in used_w or ba is None or bb is None or not (in_scope(ba) and in_scope(bb)):
            continue
        if (glyphs.get(a) or {}).get("page") != page_no:
            continue
        twin = any(m in used_w and {warcs[m][1], warcs[m][2]} == {a, b} for m in range(len(warcs)))
        twin = twin or any(m != n and {warcs[m][1], warcs[m][2]} == {a, b} for m in range(n))
        C[k].add("wrong", "a second arc written on the same two notes" if twin else "no arc of his joins these two notes (wrong ends, or a fake)",
                 "%s->%s" % (a, b))
    # clef / key / meter: per staff, from his header boxes in a swept cell, against the part that staff is written into
    hdr = header_xml(facts["xml"]) if facts.get("xml") else {}
    part_of = collections.defaultdict(collections.Counter)
    for h in written:
        p = h["rg"].split("/")
        part_of[(int(p[2]), int(p[3]))][h["part"]] += 1
    measure_of = collections.defaultdict(collections.Counter)     # (system, staff, cell) -> written measure number
    for h in written:
        p = h["rg"].split("/")
        measure_of[(int(p[2]), int(p[3]), int(p[4]))][h["measure"]] += 1
    cell_by_id = {c.id: c for c in page.cells}
    by_staff = collections.defaultdict(list)
    for t in truth:
        c = cell_by_id.get(t.cell_id)
        if t.family in ("clef", "key_accidental", "time_signature_digit") and c is not None:
            by_staff[(c.system, c.staff, c.measure)].append(t)
    for key, ts in sorted(by_staff.items()):
        st = key[:2]
        part = part_of[st].most_common(1)[0][0] if part_of[st] else None
        attrs = hdr.get(part, [])
        mm = measure_of[key].most_common(1)[0][0] if measure_of[key] else None
        num = lambda m: int(re.sub(r"\D", "", str(m)) or 0)

        def first(kind):
            """The value in force at this bar in the written part (the last one written at or before it)."""
            got = None
            for m, k, v in attrs:
                if k == kind and (mm is None or num(m) <= num(mm)):
                    got = v
                if mm is None and got is not None:
                    break
            return got
        cl = [t for t in ts if t.family == "clef"]
        if cl:
            want = CLEF.get(cl[0].cls)
            got = first("clef") if part else None
            C["clef"].add("unread" if got is None else ("right" if got == want else "wrong"),
                          "" if got == want else "his %s, written %s (part %s)" % (want, got, part), key)
        ks = [t for t in ts if t.family == "key_accidental"]
        if ks:
            want = str(-len(ks) if all("Flat" in t.cls for t in ks) else len(ks))
            got = first("key") if part else None
            C["key"].add("unread" if got is None else ("right" if got == want else "wrong"),
                         "" if got == want else "his %s, written %s (part %s)" % (want, got, part), key)
        ds = sorted([t for t in ts if t.family == "time_signature_digit"], key=lambda t: cy(t.rect))
        last_cell = max((c.measure for c in page.cells if c.kind == "measure" and (c.system, c.staff) == st), default=None)
        heads_here = any(t.family == "notehead" and cell_by_id.get(t.cell_id) is not None
                         and (cell_by_id[t.cell_id].system, cell_by_id[t.cell_id].staff, cell_by_id[t.cell_id].measure) == key
                         for t in truth)
        if len(ds) >= 2 and key[2] == last_cell and not heads_here:
            # a meter alone in the system's last bar is the COURTESY for the next page: it is in force there, not here
            C["meter"].n["courtesy, applies to the next page (not scored here)"] += 1
        elif len(ds) >= 2:
            want = "%s/%s" % (ds[0].cls.replace("timeSig", ""), ds[-1].cls.replace("timeSig", ""))
            got = first("time") if part else None
            C["meter"].add("unread" if got is None else ("right" if got == want else "wrong"),
                           "" if got == want else "his %s, written %s (part %s)" % (want, got, part), key)
    return dict(C=C, unit=u, n_truth=len(truth), n_cells=len(swept), arcs_note=arcs_note,
                truth_kinds=collections.Counter(t.family for t in truth))


ORDER = ("note", "note value", "rest", "accidental", "dot", "stem", "beam", "flag", "tie", "slur", "clef", "key", "meter")
NOT_SCORED = {
    "ledger_line": "a ledger line is not written; it only places a far head (scored inside 'note' as its owner staff)",
    "barline": "the file's bars carry no page place; a barline is not a written mark of its own",
    "text": "words are written at the bar head with no page place of their own",
    "dynamic_letter": "dynamics are written at the bar head, with the host note's box (no place of their own)",
    "brace": "a brace is the part grouping, not a mark the file places",
    "tremolo": "the staged file writes no tremolo element",
}


def render(res, examples=3):
    out = ["Cells Sean swept completely: %d measure cells, %d boxes; staff space %.1f px" % (res["n_cells"], res["n_truth"], res["unit"]),
           "%-11s %6s %6s %6s   (WRONG first; per head for note/value/stem/beam/flag/dot/accidental; per arc; per staff header)" % (
               "kind", "WRONG", "RIGHT", "UNREAD")]
    for k in ORDER:
        c = res["C"].get(k)
        if not c:
            continue
        out.append("%-11s %6d %6d %6d" % (k, c.n["wrong"], c.n["right"], c.n["unread"]))
    for k in ORDER:
        c = res["C"].get(k)
        if not c:
            continue
        for what in ("wrong", "unread"):
            whys = collections.Counter()
            for (w, why), items in c.ex.items():
                if w == what:
                    whys[why.split(" (")[0] if what == "unread" else re.sub(r"\d+(\.\d+)?", "#", why)] += len(items)
            if whys:
                out.append("  %s %s: %s" % (k, what.upper(), "; ".join("%s x%d" % kv for kv in whys.most_common(examples + 3))))
    if res["arcs_note"]:
        out.append(res["arcs_note"])
    out.append("NOT SCORED (in his cells, but the file cannot express them by place): " + "; ".join(
        "%s %d -- %s" % (k, res["truth_kinds"].get(k, 0), v) for k, v in NOT_SCORED.items()))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("facts")
    ap.add_argument("--truth", default=TRUTH)
    ap.add_argument("--arcs", default=ARCS)
    ap.add_argument("--json")
    ap.add_argument("--examples", type=int, default=3)
    a = ap.parse_args()
    res = judge(json.load(open(a.facts)), a.truth, a.arcs)
    print(render(res, a.examples))
    if a.json:
        Path(a.json).write_text(json.dumps({k: {"n": dict(v.n), "ex": {"%s|%s" % kk: vv for kk, vv in v.ex.items()}}
                                            for k, v in res["C"].items()}, default=str, indent=0))


if __name__ == "__main__":
    main()
