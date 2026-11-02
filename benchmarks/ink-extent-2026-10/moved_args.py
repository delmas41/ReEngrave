"""2.248 private look helper: print look.py args for heads whose position the ON arm moved (largest moves first, then a sample).
usage: moved_args.py ON_RECORD PDF OUT.png"""
import json
import random
import sys


def main(path, pdf, out):
    r = json.load(open(path))
    r = r.get("record", r)
    box = {o["subject"]: o["detail"]["bbox_page_px"] for o in r["observations"]
           if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px")}
    mv = []
    for o in r["observations"]:
        d = o.get("detail") or {}
        if o["quantity"] == "notehead_staff_position" and "from_head_ink" in d:
            mv.append((abs(round(o["value"]) - round(d["detector_position_float"])), o["subject"], d["from_head_ink"]))
    mv.sort(reverse=True)
    sel = mv[:4]
    rest = mv[4:]
    random.Random(3).shuffle(rest)
    sel += rest[:6]
    sys.stderr.write("\n".join(str(s) for s in sel) + "\n")
    print(pdf, out, " ".join("%s:%s:%s" % (s.split("/")[1], ",".join(map(str, box[s])), ",".join(map(str, e))) for _, s, e in sel))


if __name__ == "__main__":
    main(*sys.argv[1:])
