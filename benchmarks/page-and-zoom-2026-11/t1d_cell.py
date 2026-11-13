"""Both arms' duration/rest verdicts and glyph boxes in one cell -- for tracing a bar that got worse. Measure only.

    python3 benchmarks/page-and-zoom-2026-11/t1d_cell.py WORK_DIR PLATE CELL_PREFIX     e.g. glyph/11/1/1/0/
"""
import json
import sys


def main():
    work, plate, pre = sys.argv[1:4]
    arms = {a: json.load(open("%s/%s.%s.mini-record.json" % (work, plate, a))) for a in ("off", "on")}
    boxes = {o["subject"]: (o["value"][0], [round(v) for v in (o.get("detail") or {}).get("bbox_page_px", [])])
             for o in arms["off"]["observations"] if o["subject"].startswith(pre)}
    for sub in sorted(boxes, key=lambda s: int(s.split("/")[-1])):
        line = [sub, boxes[sub][0], boxes[sub][1]]
        for a in ("off", "on"):
            vs = [v for v in arms[a]["verdicts"] if v["subject"] == sub and v["quantity"] in ("duration", "rest_is_not_a_rest")]
            v = vs[-1] if vs else None
            line.append("%s:%s" % (a, (v["outcome"], v.get("reason"), (v.get("value") or {}).get("written") if isinstance(v.get("value"), dict) else v.get("value")) if v else "-"))
        print(*line)


if __name__ == "__main__":
    main()
