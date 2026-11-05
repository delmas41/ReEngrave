"""2.263: stream a saved record once and keep every accidental_family reading (type, why, margin, features, box, place) plus each glyph's page box.
usage: python3 benchmarks/omr-accidental-family-2026-10/margin_extract.py RECORD OUT.jsonl   (observations array only; no gather, no OCR)
Run from the repo root."""
import json, pathlib, sys
sys.path.insert(0, ".")
from tools.omr.staged import judged as J


def main(rec, out):
    n = nf = 0
    boxes = {}
    with open(out, "w") as fh:
        for o in J.iter_array(pathlib.Path(rec), "observations"):
            q = o.get("quantity")
            if q == "glyph_box":
                b = (o.get("detail") or {}).get("bbox_page_px")
                if b:
                    boxes[o["subject"]] = b
            elif q == "accidental_staff_position":
                n += 1
                d = o.get("detail") or {}
                f = d.get("family")
                if not f:
                    continue
                nf += 1
                fh.write(json.dumps({"subject": o["subject"], "id": o.get("id"), "alteration": d.get("alteration"),
                                     "detector_class": d.get("detector_class"), "family": f,
                                     "x0": d.get("x0"), "x1": d.get("x1"), "y0": d.get("y0"), "y1": d.get("y1"),
                                     "absorbed": bool(d.get("one_ink_absorbed"))}) + "\n")
    json.dump(boxes, open(out + ".boxes.json", "w"))
    print(pathlib.Path(rec).name, "accidental positions", n, "with family", nf, flush=True)


if __name__ == "__main__":
    for i in range(1, len(sys.argv), 2):
        main(sys.argv[i], sys.argv[i + 1])
