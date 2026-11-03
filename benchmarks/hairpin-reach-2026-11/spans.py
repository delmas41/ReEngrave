"""ROADMAP 2.254 round 2: our WRITTEN hairpin spans (start note .. stop note, read off the exported MusicXML), for the tiles Sean answered.

    python3 benchmarks/hairpin-reach-2026-11/spans.py KEY.json ON.musicxml [ON2.musicxml ...]

For each tile with a wedge subject: the written `<wedge>` whose start direction precedes the tile's start note (`start_note` in the key, or
for a tile with none, the written start nearest the read box's narrow/opening left edge on the same page and staff), and the note its `stop`
direction follows (the exporter writes the stop AFTER the last event the wedge spans, `export._place_wedges` / the note writer). Prints each spanned onset with its
written type, so the span can be set beside Sean's words in answers-r1.json. Matching to his words is done by eye and said so.
"""
import json
import sys
import xml.etree.ElementTree as ET


def events(xml_path):
    """Per part, the stream of notes/rests in document order with the wedge states that precede each (number, type)."""
    root = ET.parse(xml_path).getroot()
    out = {}
    for part in root.iter("part"):
        pid = part.get("id")
        seq, pending = [], []
        for m in part.findall("measure"):
            for el in m:
                if el.tag == "direction":
                    for w in el.iter("wedge"):
                        if w.get("type") == "stop" and seq:
                            # the exporter writes a stop AFTER the last note it spans (`export._note_xml`: music21 binds a stop to the
                            # last note parsed), so it belongs to the note just written
                            seq[-1]["wedges"].append((w.get("number"), "stop"))
                        else:
                            pending.append((w.get("number"), w.get("type")))
                elif el.tag == "note":
                    typ = el.findtext("type") or "?"
                    dots = len(el.findall("dot"))
                    seq.append({"rg": el.get("rg"), "measure": m.get("number"), "type": typ + "." * dots,
                                "rest": el.find("rest") is not None, "chord": el.find("chord") is not None,
                                "voice": el.findtext("voice"), "wedges": pending})
                    pending = []
        out[pid] = seq
    return out


def spans(xml_path):
    res = []
    for pid, seq in events(xml_path).items():
        open_ = {}
        for i, e in enumerate(seq):
            for num, typ in sorted(e["wedges"], key=lambda w: w[1] == "stop"):     # a one-note wedge opens and stops on one note
                if typ == "stop" and num in open_:
                    s = open_.pop(num)
                    res.append({"part": pid, "kind": s[1], "start": seq[s[0]], "stop": e,
                                "onsets": [x for x in seq[s[0]:i + 1] if not x["chord"]]})
                elif typ != "stop":
                    open_[num] = (i, typ)
    return res


def page_of(rg):
    return int(rg.split("/")[1]) if rg else None


def main(key_path, *xmls):
    key = json.load(open(key_path))
    allsp = []
    for x in xmls:
        allsp += spans(x)
    by_start = {s["start"]["rg"]: s for s in allsp}
    for t in key:
        sn = t.get("start_note")
        s = by_start.get(sn) if sn else None
        if s is None and t.get("subject"):
            # no start note in the key: the written span whose start is on the same page / system / staff, nearest the read box (by cell)
            pg, sy, st, cell = (int(v) for v in t["subject"].split("/")[1:5])
            cands = [q for q in allsp if q["start"]["rg"] and [int(v) for v in q["start"]["rg"].split("/")[1:4]] == [pg, sy, st]
                     and abs(int(q["start"]["rg"].split("/")[4]) - cell) <= 1]
            s = cands[0] if len(cands) == 1 else None
            if len(cands) > 1:
                print("tile %d: %d written spans start near the read on this staff:" % (t["tile"], len(cands)))
                for q in cands:
                    print("    candidate start %s %s m%s -> stop %s %s m%s | %s" % (
                        q["start"]["rg"], q["start"]["type"], q["start"]["measure"], q["stop"]["rg"], q["stop"]["type"],
                        q["stop"]["measure"], " ".join(o["type"] for o in q["onsets"])))
        if s is None:
            print("tile %2d %-7s %s: no written span found" % (t["tile"], t["role"], t["subject"]))
            continue
        on = " ".join("%s%s(m%s)" % ("r:" if o["rest"] else "", o["type"], o["measure"]) for o in s["onsets"])
        print("tile %2d %-7s %s %s: start %s m%s -> stop %s m%s | %s" % (
            t["tile"], t["role"], t["subject"], s["kind"], s["start"]["type"], s["start"]["measure"], s["stop"]["type"],
            s["stop"]["measure"], on))


if __name__ == "__main__":
    main(*sys.argv[1:])
