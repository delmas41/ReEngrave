"""2.251 step 2's pitch witness: the heads the carry re-pitched (ON arm: Q.PITCH reason `position_and_clef_change`), each scored
against the REFERENCE ENCODING (Gradus MXL, a truth file used for measurement only): is the written pitch (step + octave, accidental
ignored) among the pitches the encoded part plays in that bar? Same heads, same test, on the OFF arm (no carry).

python3 work-2.251/pitchwit.py PLATE ON.record.json OFF.record.json
Staff -> parts: by the staff's local index from the bottom / top (Litolff: Fag = local 3 -> P7+P8; Vc = the Vcl. staff -> P17).
"""
import json, os, re, sys, zipfile
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
import barmap  # noqa: E402

MXL = {"litolff": "library/reference/beethoven/symphony-5/beethoven--symphony-5--mvt1--gradus.mxl",
       "brahms": "library/reference/brahms/symphony-1/brahms--symphony-1--mvt1--gradus.mxl"}


def enc_pitches(plate):
    z = zipfile.ZipFile(MXL[plate])
    root = ET.fromstring(z.read([n for n in z.namelist() if n.endswith(".xml") and not n.startswith("META")][0]))
    out = {}
    for part in root.iter("part"):
        for m in part.iter("measure"):
            s = out.setdefault((part.get("id"), int(re.sub(r"\D", "", m.get("number")) or 0)), set())
            for n in m.iter("note"):
                p = n.find("pitch")
                if p is not None:
                    s.add(p.findtext("step") + p.findtext("octave"))
    return out


def bar_of(plate):
    first = {}
    b = 1
    for pg, si, nst, nc in barmap.layout(plate):
        first[(pg, si)] = b
        b += nc
    return first


def load(path):
    r = json.load(open(path))["record"]
    return {v["subject"]: v for v in r["verdicts"] if v["quantity"] == "pitch" and v["outcome"] == "decided"}


def main():
    plate, on_p, off_p = sys.argv[1], sys.argv[2], sys.argv[3]
    enc = enc_pitches(plate)
    first = bar_of(plate)
    on, off = load(on_p), load(off_p)
    tally = {"on_right": 0, "on_wrong": 0, "off_right": 0, "off_wrong": 0, "off_none": 0, "no_part": 0}
    for subj, v in on.items():
        if v.get("reason") != "position_and_clef_change":
            continue
        _, pg, s, st, c, g = subj.split("/")
        pg, s, st, c = int(pg), int(s), int(st), int(c)
        bar = first.get((pg, s), 0) + c
        parts = {"litolff": {3: ("P7", "P8")}, "brahms": {3: ("P7", "P8")}}[plate].get(st)
        if parts is None:
            parts = ("P17",) if plate == "litolff" else ("P20",)       # the cello staff (the only other staff a change stands on)
        truth = set().union(*[enc.get((p, bar), set()) for p in parts])
        if not truth:
            tally["no_part"] += 1
            continue
        nm = re.sub(r"[#b]|-?\d$", "", str(v["value"])) + str(v["value"])[-1]
        tally["on_right" if _step_oct(v["value"]) in truth else "on_wrong"] += 1
        w = off.get(subj)
        if w is None:
            tally["off_none"] += 1
        else:
            tally["off_right" if _step_oct(w["value"]) in truth else "off_wrong"] += 1
    print(plate, tally)


def _step_oct(name):
    s = str(name)
    m = re.match(r"([A-G])[#b♯♭x]*(-?\d+)", s)
    return (m.group(1) + m.group(2)) if m else s


main()
