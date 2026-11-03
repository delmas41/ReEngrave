"""ROADMAP 2.252 r4 -- 12 blind tiles at named heads, cut from the page where the ON file wrote them (STAGED).

Each tile: one staff, ONE thin orange box on the head the ON file wrote, nothing of ours drawn, +-11 spaces wide so the notes
before and after and both ends of every arc between them show (r3's `cut`). The key (outside the folder) holds what the OFF and
ON files wrote at that head (pitch, ties) and the role.

    python3 benchmarks/omr-arc-binding-2026-10/tiles_2252_r4.py OUT_DIR KEY.json SPEC.json
SPEC: [{"plate", "record" (ON gather), "off_xml", "on_xml", "rg", "role"}, ...] in tile order.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record_io import load_record   # noqa: E402

_spec = importlib.util.spec_from_file_location("tiles_r3", pathlib.Path(__file__).with_name("tiles_2252_r3.py"))
T3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T3)

T3.README = """# 2.252 round 4 tiles -- tied notes and their pitch

Each picture is a piece of a scanned score page, one staff, with ONE thin orange box and nothing else drawn. The box only
says where to look; it says nothing about what we read. Each picture shows the notes before and after the box and the whole
of every arc between them.

**Question, for every tile:** which note is in the orange box -- on which line or in which space of its staff (count from the
top line), with its sharp or flat if it sounds one (a tie carries one across the barline) -- and is it tied (the same note held)
to the note before it, the note after it, both, or neither? If there are two notes in the box, answer for each.

Answer by tile number.
"""


def _written(xml_path):
    out = {}
    for n in ET.parse(xml_path).iter("note"):
        rg = n.get("rg")
        if not rg:
            continue
        p = n.find("pitch")
        pitch = None if p is None else "%s%s%s" % (p.findtext("step"), {"-1": "b", "1": "#"}.get(p.findtext("alter") or "", ""),
                                                   p.findtext("octave"))
        out.setdefault(rg, []).append(dict(pitch=pitch, tie=[t.get("type") for t in n.findall("tie")]))
    return out


def main():
    out_dir, key_path, spec = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), json.load(open(sys.argv[3]))
    recs, xmls, items = {}, {}, []
    for s in spec:
        if s["record"] not in recs:
            r = load_record(s["record"])
            r = r.get("record", r)
            recs[s["record"]] = {o["subject"]: o["detail"]["bbox_page_px"] for o in r["observations"]
                                 if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px")}
        for x in (s["off_xml"], s["on_xml"]):
            if x not in xmls:
                xmls[x] = _written(x)
        on = xmls[s["on_xml"]].get(s["rg"])
        if not on:
            raise SystemExit("not written in the ON file: %s" % s["rg"])
        items.append(dict(plate=s["plate"], page=int(s["rg"].split("/")[1]), rg=s["rg"], box=recs[s["record"]][s["rg"]],
                          role=s["role"], written=dict(off=xmls[s["off_xml"]].get(s["rg"], []), on=on)))
    T3.cut(items, out_dir, key_path)


if __name__ == "__main__":
    main()
