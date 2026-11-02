"""Contact sheets of print strips at each ENCODED clef change (encoding = where to look; the print decides).

python3 work-2.251/sheet.py PLATE STAFF_LOCAL BARS(comma) OUTPREFIX [per_sheet]
"""
import os, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
import barmap  # noqa: E402
import crops  # noqa: E402


def locate(plate, bar):
    b = 1
    for pg, si, nst, nc in barmap.layout(plate):
        if b <= bar < b + nc:
            return pg, si, bar - b
        b += nc
    return None


def main():
    plate, staff_local, bars, outp = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    per = int(sys.argv[5]) if len(sys.argv) > 5 else 5
    bars = [int(x) for x in bars.split(",")]
    tiles = []
    for bar in bars:
        pg, si, c = locate(plate, bar)
        sl = staff_local
        st = int(sl.split(":")[1]) if ":" in sl else int(sl)  # "fromtop:N" or "-N" from bottom
        if ":" not in sl and st < 0:
            d = crops.cmap(plate, pg)
            n = len([s for s in d["staves"] if s["system_index"] == si])
            st = n + st
        lab = f"bar {bar} -> p{pg} s{si} c{c} staff{st}"
        W = int(os.environ.get("WIN", "1")); im = crops.strip(plate, pg, si, st, c - W, c + W, lab)
        im = im.resize((im.width * 2 // 3, im.height * 2 // 3))
        hdr = Image.new("RGB", (im.width, 30), "white")
        ImageDraw.Draw(hdr).text((5, 5), lab, fill="red")
        t = Image.new("RGB", (im.width, im.height + 30), "white")
        t.paste(hdr, (0, 0)); t.paste(im, (0, 30))
        tiles.append(t)
    for k in range(0, len(tiles), per):
        grp = tiles[k:k + per]
        W = max(t.width for t in grp); H = sum(t.height for t in grp)
        sh = Image.new("RGB", (W, H), "white")
        y = 0
        for t in grp:
            sh.paste(t, (0, y)); y += t.height
        sh.save(f"{outp}-{k // per}.png")
        print(f"{outp}-{k // per}.png", [bars[i] for i in range(k, min(k + per, len(bars)))])


main()
