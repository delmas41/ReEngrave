"""2.277 hold rule: every place where ON turns a BLUE note/rest plain while the bar's sum is wrong (ON bar 'does not add up'), unless OFF was already wrong.
usage: blue_plain.py OFF.musicxml ON.musicxml [LABEL]   -> prints counts and every place; also notes/rests gained or lost per measure"""
import re, sys, collections


def parse(path):
    x = open(path).read()
    out = {}
    for pm in re.finditer(r'<part id="(P\d+)">(.*?)</part>', x, re.S):
        for mm in re.finditer(r'<measure number="([^"]+)"[^>]*>(.*?)</measure>', pm.group(2), re.S):
            b = mm.group(2)
            items = []
            for nm in re.finditer(r'<note([^>]*)>(.*?)</note>', b, re.S):
                attrs, body = nm.group(1), nm.group(2)
                kind = "rest" if "<rest" in body else "note"
                step = re.search(r"<step>(\w)</step>", body)
                alt = re.search(r"<alter>(-?\d)</alter>", body)
                octv = re.search(r"<octave>(\d)</octave>", body)
                typ = re.search(r"<type>(\w+)</type>", body)
                items.append((kind, (step.group(1) if step else "") + (alt.group(1) if alt else "") + (octv.group(1) if octv else ""),
                              typ.group(1) if typ else "?", "<dot" in body, "color=" in attrs))
            out[(pm.group(1), mm.group(1))] = (items, "does not add up" in b)
    return out


off, on = parse(sys.argv[1]), parse(sys.argv[2])
label = sys.argv[3] if len(sys.argv) > 3 else ""
flips, already, changed_bars = [], [], 0
gained = lost = 0
for k in sorted(set(off) & set(on)):
    (a, aw), (b, bw) = off[k], on[k]
    if a == b and aw == bw:
        continue
    changed_bars += 1
    ca = collections.Counter((i[0], i[1], i[2], i[3]) for i in a)
    cb = collections.Counter((i[0], i[1], i[2], i[3]) for i in b)
    gained += sum((cb - ca).values())
    lost += sum((ca - cb).values())
    # blue in OFF, plain in ON, same symbol
    blue_off = collections.Counter((i[0], i[1], i[2], i[3]) for i in a if i[4])
    plain_on = collections.Counter((i[0], i[1], i[2], i[3]) for i in b if not i[4])
    n = sum((blue_off & plain_on).values())
    if n:
        (already if aw else flips if bw else []).append((k, n, aw, bw)) if (aw or bw) else None
print(label, "measures that differ:", changed_bars, " notes+rests gained:", gained, "lost:", lost)
print(label, "blue -> plain while the ON bar does not add up and OFF added up (MUST be 0):", len(flips))
for f in flips:
    print("   ", f)
print(label, "blue -> plain where OFF was already wrong (listed):", len(already))
for f in already[:20]:
    print("   ", f)
