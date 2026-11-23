"""2306 r11: bars (page/system/staff/cell) where a glyph's page stem reading differs between the r9 and r11 gathers. Usage: changed_cells.py OUT.json
plate:R9REC:R11REC ..."""
import sys, json, re
out = {}


def readings(path):
    txt = open(path, encoding="utf-8").read()
    r = {}
    for m in re.finditer(r'"subject":"(glyph/[0-9/]+)","quantity":"page_stem","value":"obs:[0-9]+".{0,400}?"how":"([a-z_]+)"', txt):
        r[m.group(1)] = ("read", m.group(2))
    for m in re.finditer(r'"subject":"(glyph/[0-9/]+)","quantity":"page_stem","reader":"cv_page_stems","frame":"[^"]*","reason":"[a-z_]+","detail":\{"note":"([a-z_]+)"', txt):
        r[m.group(1)] = ("abstain", m.group(2))
    return r


for spec in sys.argv[2:]:
    plate, a, b = spec.split(":")
    A, B = readings(a), readings(b)
    cells = sorted({"/".join(g.split("/")[1:5]) for g in set(A) | set(B) if A.get(g) != B.get(g)})
    out[plate] = cells
    print(plate, len(cells), "bars with a changed page stem reading")
json.dump(out, open(sys.argv[1], "w"))
