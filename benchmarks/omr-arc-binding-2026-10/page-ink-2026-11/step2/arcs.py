"""2.274 step 2: the arcs of a written MusicXML, by their two notes' glyph keys (`rg`, stamped by `lane_report.traced_export`), and the per-run readout.

    arcs_of_xml(xml)  ->  [{kind, start, stop, part}]     (a slur pairs by number inside a part; a tie by pitch inside a part's voice, in file order)
    per_run(extra, off_arcs, on_arcs, boxes)  ->  one record per witnessed run: status, OFF arcs it overlaps, whether OFF wrote it whole / cut / not at all

An arc of OFF *overlaps* a run when both ends of the arc stand on the run's staff (the glyph key's system and staff) and the arc's x extent covers at least half of the run's.
"""
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict


def arcs_of_xml(xml):
    root = ET.fromstring(xml)
    out = []
    for part in root.iter("part"):
        pid = part.get("id")
        slur_open = {}          # (voice, number) -> rg
        tie_open = {}           # (voice, pitch) -> rg
        for m in part.findall("measure"):
            for el in m.findall("note"):
                rg = el.get("rg")
                voice = el.findtext("voice") or "1"
                p = el.find("pitch")
                pitch = None if p is None else "%s%s%s" % (p.findtext("step"), p.findtext("alter") or "", p.findtext("octave"))
                notations = el.find("notations")
                if notations is not None:
                    for s in notations.findall("slur"):
                        key = (voice, s.get("number") or "1")
                        if s.get("type") == "start":
                            slur_open[key] = rg
                        elif s.get("type") == "stop" and key in slur_open:
                            out.append(dict(kind="slur", start=slur_open.pop(key), stop=rg, part=pid))
                    for t in notations.findall("tied"):
                        if t.get("type") == "stop" and (voice, pitch) in tie_open:
                            out.append(dict(kind="tie", start=tie_open.pop((voice, pitch)), stop=rg, part=pid))
                    for t in notations.findall("tied"):
                        if t.get("type") == "start":
                            tie_open[(voice, pitch)] = rg
    return out


def staff_of(key):
    m = re.match(r"glyph/(\d+)/(\d+)/(\d+)/(\d+)/\d+$", key or "")
    return None if not m else (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def span_of(arc, boxes):
    a, b = boxes.get(arc["start"]), boxes.get(arc["stop"])
    if not a or not b:
        return None
    ca, cb = (a["box"][0] + a["box"][2]) / 2, (b["box"][0] + b["box"][2]) / 2
    return (min(ca, cb), max(ca, cb))


def per_run(extra, off_arcs, boxes, runs_by_ordinal):
    """`extra` = the `<plate>.on.extra.json` verdicts. `runs_by_ordinal[(page, ordinal)]` = the step-1 row detail (points) for the x extent."""
    recs = []
    for v in extra:
        sub = v["subject"]
        page = int(sub.split("/")[1])
        for r in (v.get("detail") or {}).get("runs") or ():
            if not r.get("witnesses"):
                continue
            row = runs_by_ordinal.get((page, r.get("ordinal")))
            if not row:
                continue
            xs = [p[0] for p in row["points"]]
            x0, x1 = min(xs), max(xs)
            st = tuple(row.get("staff") or ())
            rec = dict(page=page, ordinal=r.get("ordinal"), status=r["status"], kind=r.get("kind"), why=r.get("why"), start=r.get("start"), stop=r.get("stop"),
                       x0=x0, x1=x1, staff=st, witnesses=r["witnesses"], closest=r.get("closest"), edge=r.get("edge"))
            ov = []
            for a in off_arcs:
                sa, sz = staff_of(a["start"]), staff_of(a["stop"])
                if sa is None or sz is None or sa[0] != page or sa != sz:
                    continue
                if st and (sa[1], sa[2]) != st:
                    continue
                sp = span_of(a, boxes)
                if not sp:
                    continue
                inter = min(sp[1], x1) - max(sp[0], x0)
                if inter > 0.5 * (x1 - x0):
                    ov.append(a)
            rec["off_overlap"] = ov
            if r["status"] == "written":
                exact = [a for a in ov if (a["start"], a["stop"]) == (r["start"], r["stop"])]
                same_kind = [a for a in exact if a["kind"] == r["kind"]]
                if same_kind:
                    rec["off"] = "whole"
                elif exact:
                    rec["off"] = "same_notes_other_kind"
                elif ov:
                    rec["off"] = "cut_or_short"
                else:
                    rec["off"] = "none"
            recs.append(rec)
    return recs
