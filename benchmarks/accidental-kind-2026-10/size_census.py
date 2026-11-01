"""2.247 (2.245 hand-off): every accidental-family DETECTOR box on the night slices (frozen sample pages), its page height in spaces
(lane_report.PLATES unit) against its class's SMuFL glyph height, by class and by the 2.201 stroke type. Asks whether "a box much taller
than its glyph" and "the class names a kind the shape does not show" are one cause. usage: size_census.py"""
import collections
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged import lane_report as LR  # noqa: E402

ROOT = "library/_shared-records/lane-report-slices-20261029-night"
#: SMuFL Bravura glyphBBoxes heights (spaces)
GLYPH_H = {"accidentalflat": 2.456, "accidentalnatural": 2.688, "accidentalsharp": 2.796, "accidentaldoublesharp": 1.004,
           "accidentaldoubleflat": 2.456, "keyflat": 2.456, "keynatural": 2.688, "keysharp": 2.796}


def main():
    for plate in ("litolff", "brahms"):
        u = LR.PLATES[plate]["unit"]
        boxes, fam = {}, {}
        with open(f"{ROOT}/{plate}/observations.jsonl") as f:
            for line in f:
                if '"accidental_staff_position"' in line:
                    r = json.loads(line)
                    fam[r["subject"]] = (r.get("detail") or {}).get("family") or {}
                elif '"glyph_box"' in line:
                    r = json.loads(line)
                    if str(r["value"][0]).lower() in GLYPH_H and (r.get("detail") or {}).get("bbox_page_px"):
                        boxes[r["subject"]] = (str(r["value"][0]).lower(), (r["detail"]["bbox_page_px"]))
        tab = collections.defaultdict(collections.Counter)
        for s, (cls, b) in boxes.items():
            ratio = (b[3] - b[1]) / u / GLYPH_H[cls]
            band = "h>1.5x glyph" if ratio > 1.5 else ("h<0.7x glyph" if ratio < 0.7 else "glyph-sized")
            t = fam.get(s, {}).get("type", "no family row")
            tab[(cls, band)][t] += 1
        print(plate, "unit", u)
        for k, c in sorted(tab.items()):
            print("   %-24s %-14s %s" % (k[0], k[1], dict(c)))


if __name__ == "__main__":
    main(*sys.argv[1:])
