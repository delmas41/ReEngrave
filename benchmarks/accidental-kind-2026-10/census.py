"""2.247 step 1: detector class vs the 2.201 stroke type, per accidental-family box, on the saved 20261029-night gather slices
(the frozen sample pages; GATHER rows only, nothing re-run). usage: python3 census.py [OUT.json]"""
import collections
import json
import sys

ROOT = "library/_shared-records/lane-report-slices-20261029-night"


def main(out_path="benchmarks/accidental-kind-2026-10/data/census.json"):
    out = []
    for plate in ("litolff", "brahms"):
        c, why = collections.Counter(), collections.Counter()
        page_box = {}
        with open(f"{ROOT}/{plate}/observations.jsonl") as f:
            for line in f:
                if '"glyph_box"' in line and '"bbox_page_px"' in line:
                    r = json.loads(line)
                    page_box[r["subject"]] = r["detail"]["bbox_page_px"]
        with open(f"{ROOT}/{plate}/observations.jsonl") as f:
            for line in f:
                if '"accidental_staff_position"' not in line:
                    continue
                r = json.loads(line)
                d = r.get("detail") or {}
                fam = d.get("family")
                if not fam:
                    c[("nofam", d.get("detector_class"))] += 1
                    continue
                dt, t = fam.get("detector_type"), fam.get("type")
                c[(dt, t)] += 1
                if t != dt:
                    why[(dt, t, fam.get("why"))] += 1
                out.append({"plate": plate, "subject": r["subject"], "dt": dt, "t": t, "why": fam.get("why"), "cls": d.get("detector_class"),
                            "box": [d.get("x0"), d.get("y0"), d.get("x1"), d.get("y1")], "features": fam.get("features"),
                            "margin": fam.get("margin"), "cands": fam.get("candidates"), "conf": d.get("confidence"),
                            "page": int(r["subject"].split("/")[1]), "page_box": page_box.get(r["subject"])})
        print(plate)
        for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
            print("  ", k, v)
        print(" disagreements by why:")
        for k, v in sorted(why.items(), key=lambda kv: -kv[1]):
            print("  ", k, v)
    import os
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path, "w"))


if __name__ == "__main__":
    main(*sys.argv[1:])
