"""2306 r11: the wide-chord and end-to-end controls -- every head of the window: reading without and with the contact pass (stroke, direction, how).
Usage (cwd = tree): r11_wide.py FX.json NAME ..."""
import sys, os, json
sys.path.insert(0, os.getcwd())
from tools.omr.staged import page_stems as PS
fx = json.load(open(sys.argv[1]))
for name in sys.argv[2:]:
    c = fx[name]
    heads = [dict(h, box=tuple(h["box"])) for h in c["heads"]]
    verts = [dict(v, box=tuple(v["box"])) for v in c["verticals"]]
    cross = [dict(x, box=tuple(x["box"])) for x in c["crossers"]]
    held = {int(k): v for k, v in c["held"].items()}
    strokes = {int(k): dict(v, box=tuple(v["box"])) for k, v in c["strokes"].items()}
    a = PS.read(heads, verts, held, crossers=cross)
    b = PS.read(heads, verts, held, crossers=cross, strokes=strokes)
    print("##", name, c["glyph"], c["sean"])
    for h in sorted(heads, key=lambda h: h["box"][1]):
        ra, rb = a["heads"][h["id"]], b["heads"][h["id"]]
        print("   head %-5s %-34s y %4d-%4d | before %-24s %-5s %s | after %-24s %-5s %s %s" % (
            h["id"], ",".join(m.split("/", 1)[1] for m in h["members"])[:34], h["box"][1], h["box"][3], ra["how"], ra.get("direction"), ra.get("stroke"),
            rb["how"], rb.get("direction"), rb.get("stroke"), rb.get("via") or ""))
    print("   stems after:", {o: (s["direction"], s["members"], sorted(map(str, s["heads"]))) for o, s in b["stems"].items()})
