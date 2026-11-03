"""ROADMAP 2.254 round 3: READ words per page, OFF vs ON (a lane_report work dir's gathered records), and which were lost or gained,
matched by place (the word's box centre, 1.5 spaces). Gate: no READ word lost.

    python3 benchmarks/hairpin-reach-2026-11/words_read.py WORKDIR brahms litolff
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.judged import iter_array  # noqa: E402

NEAR_PX = 40.0          # ~1.5 sp at 600 dpi


def words(rec):
    out = []
    for it in iter_array(rec, "observations"):
        if it.get("quantity") == "direction_word" and isinstance(it.get("value"), str):
            bb = (it.get("detail") or {}).get("bbox_page_px")
            if bb and len(bb) == 4:
                out.append({"page": int(it["subject"].split("/")[1]), "text": it["value"], "box": bb,
                            "cx": (bb[0] + bb[2]) / 2.0, "cy": (bb[1] + bb[3]) / 2.0, "sub": it["subject"],
                            "ink_boxes": (it.get("detail") or {}).get("ink_boxes")})
    return out


def unmatched(a, b):
    left, used = [], set()
    for w in a:
        hit = None
        for j, v in enumerate(b):
            if j not in used and v["page"] == w["page"] and abs(v["cx"] - w["cx"]) <= NEAR_PX * 3 and abs(v["cy"] - w["cy"]) <= NEAR_PX:
                hit = j
                break
        if hit is None:
            left.append(w)
        else:
            used.add(hit)
    return left


def main(work, *plates):
    work = pathlib.Path(work)
    for plate in plates:
        off, on = words(work / ("%s.off.gathered.record.json" % plate)), words(work / ("%s.on.gathered.record.json" % plate))
        for p in sorted({w["page"] for w in off + on}):
            a, b = [w for w in off if w["page"] == p], [w for w in on if w["page"] == p]
            lost, gained = unmatched(a, b), unmatched(b, a)
            print("%s p%d: READ words OFF %d ON %d | lost %d gained %d | ink_boxes ON %d" % (
                plate, p, len(a), len(b), len(lost), len(gained), sum(1 for w in b if w["ink_boxes"])))
            for w in lost:
                print("    lost   %-22r %s %s" % (w["text"], w["sub"], [round(v) for v in w["box"]]))
            for w in gained:
                print("    gained %-22r %s %s" % (w["text"], w["sub"], [round(v) for v in w["box"]]))
            ch = [(x, y) for x in a for y in b if abs(x["cx"] - y["cx"]) <= NEAR_PX * 3 and abs(x["cy"] - y["cy"]) <= NEAR_PX
                  and x["text"] != y["text"]]
            for x, y in ch:
                print("    text   %r -> %r %s" % (x["text"], y["text"], y["sub"]))


if __name__ == "__main__":
    main(*sys.argv[1:])
