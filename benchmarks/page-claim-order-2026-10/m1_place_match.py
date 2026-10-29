"""Place-match every written note/rest OFF vs ON (page + centre within 4 px), report any change of type, pitch, dots or blue; plus gained/lost hosts."""
import json
D = "out/lane-report/2.221-m2/work/"
for pl in ("litolff", "brahms"):
    off = json.load(open(D + f"{pl}.off.symbols.json"))["hosts"]
    on = json.load(open(D + f"{pl}.on.symbols.json"))["hosts"]
    by = {}
    for h in on:
        by.setdefault(h["page"], []).append(h)
    used, changed, lost = set(), [], []
    for h in off:
        best = None
        for g in by.get(h["page"], []):
            d = abs(g["cx"] - h["cx"]) + abs(g["cy"] - h["cy"])
            if d <= 8 and id(g) not in used and (best is None or d < best[0]):
                best = (d, g)
        if best is None:
            lost.append((h["page"], h["kind"], h["type"], h["pitch"], round(h["cx"]), round(h["cy"]), h["blue"]))
            continue
        g = best[1]
        used.add(id(g))
        if (g["type"], g["pitch"], g["blue"], str(g["sub"])) != (h["type"], h["pitch"], h["blue"], str(h["sub"])):
            changed.append((h["page"], round(h["cx"]), round(h["cy"]), (h["type"], h["pitch"], h["blue"]), (g["type"], g["pitch"], g["blue"])))
    gained = [(g["page"], g["kind"], g["type"], g["pitch"], round(g["cx"]), round(g["cy"]), g["blue"]) for g in on if id(g) not in used]
    print(pl, "off", len(off), "on", len(on), "changed-in-place", len(changed), "lost", len(lost), "gained", len(gained))
    print(" changed", changed[:12])
    print(" lost", lost[:8])
    print(" gained", gained[:8])
