"""2.180 probe 1: streamed extract (ijson, record-load lock) of what a dot's fate needs. READ-ONLY.
Per glyph: class, page box, conf, aug_dot/dot_staff_position/notehead_staff_position/mark_shape obs; every verdict of
dot_role, duration (whole chain, in file order), stem_value, head_stem, glyph_owner, notehead_is_not_a_notehead.
usage: x1_extract.py RECORD OUT.json"""
import json
import sys
import time

import ijson

sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec  # noqa: E402

path, out = sys.argv[1], sys.argv[2]
OBSQ = {"glyph_box", "glyph_conf", "aug_dot", "dot_staff_position", "notehead_staff_position", "mark_shape"}
VERQ = {"dot_role", "duration", "stem_value", "head_stem", "glyph_owner", "notehead_is_not_a_notehead"}
G = {}
t0 = time.time()


def slim(x, n=600):
    s = json.dumps(x, default=str)
    return json.loads(s) if len(s) < n else s[:n]


with rec.lock():
    with open(path, "rb") as f:
        for o in ijson.items(f, "record.observations.item", use_float=True):
            q = o["quantity"]
            sub = o["subject"]
            if q not in OBSQ or not sub.startswith("glyph/"):
                continue
            g = G.setdefault(sub, {})
            if q == "glyph_box":
                g["cls"] = o["value"][0]
                g["bb"] = [round(v, 1) for v in ((o.get("detail") or {}).get("bbox_page_px") or [])]
            elif q == "glyph_conf":
                g["conf"] = round(o["value"], 3)
            else:
                g.setdefault("O", {})[q] = slim(o["value"], 300)
                if q in ("dot_staff_position", "notehead_staff_position"):
                    g["O"][q + "_d"] = slim(o.get("detail"), 300)
    t1 = time.time()
    with open(path, "rb") as f:
        for v in ijson.items(f, "record.verdicts.item", use_float=True):
            q = v["quantity"]
            sub = v["subject"]
            if q not in VERQ or not sub.startswith("glyph/"):
                continue
            g = G.setdefault(sub, {})
            row = dict(id=v["id"], o=v["outcome"], r=v.get("reason"), dec=v.get("decider"), val=slim(v.get("value"), 400),
                       sup=v.get("supersedes"),
                       c=[slim(c.get("value"), 300) for c in (v.get("candidates") or [])][:8])
            det = v.get("detail") or {}
            if q == "dot_role":
                row["det"] = {k: det[k] for k in ("head", "owner", "articulation", "head_owned_elsewhere", "head_refused",
                                                    "position_admitted", "detector_class", "mark_tip") if k in det}
            elif q == "head_stem":
                row["det"] = slim({k: det[k] for k in ("voices", "stems") if k in det}, 500)
            elif q == "duration":
                row["det"] = slim({k: det[k] for k in ("dots_attached", "was", "one_note_refusal", "stem", "shared_stem",
                                                         "dot_seen", "dot") if k in det}, 400)
            g.setdefault("V", {}).setdefault(q, []).append(row)
json.dump(G, open(out, "w"), default=str)
print("glyphs", len(G), "obs pass %.0fs" % (t1 - t0), "total %.0fs" % (time.time() - t0), flush=True)
