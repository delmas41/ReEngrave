"""2.139 step 1: for each blue `dyn.` (dynamic unspellable) on the cached rows, what the
dynamic reader saw, and which OCR word (direction_word obs) overlaps those letters and
whether the lexicon knows it. usage: 2.139_count.py NAME  (reads out/2.139/NAME_{ver,obs}.json)"""
import sys, json, collections
sys.path.insert(0, ".")
from tools.omr import direction_lexicon as L
O = "benchmarks/omr-direction-text-2026-09/out/2.139/"
name = sys.argv[1]
ver = json.load(open(O + name + "_ver.json")); obs = json.load(open(O + name + "_obs.json"))
byid = {o["id"]: o for o in obs}
words = [o for o in obs if o["quantity"] == "direction_word" and (o.get("detail") or {}).get("bbox_page_px")]
def page(s): return s.split("/")[1]
rows = []
for v in ver:
    if v["quantity"] != "dynamic" or v.get("reason") != "unspellable": continue
    d = v["detail"]; letters = [byid[i] for w in d["words"] for i in w["letters"] if i in byid]
    boxes = [l["detail"]["bbox_page_px"] for l in letters if (l.get("detail") or {}).get("bbox_page_px")]
    pg = page(v["subject"])
    hit = []
    for w in words:
        if page(w["subject"]) != pg: continue
        wb = w["detail"]["bbox_page_px"]
        for b in boxes:
            ix = min(b[2], wb[2]) - max(b[0], wb[0]); iy = min(b[3], wb[3]) - max(b[1], wb[1])
            if ix > 0 and iy > 0 and ix * iy >= 0.5 * (b[2]-b[0]) * (b[3]-b[1]):
                hit.append(w); break
    rows.append({"cell": v["subject"], "outcome": v["outcome"],
        "run": [w["text"] for w in d["words"]], "completions": d.get("completions"),
        "n_letters": len(boxes), "letter_cls": [str(l["value"]) for l in letters],
        "ocr": [(w["value"], w["detail"].get("category"), w["reader"]) for w in hit],
        "inside_read_word": d.get("letters_inside_a_read_word"),
        "at_dyn_token": d.get("letters_at_a_words_dynamic_token"),
        "bbox": [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)] if boxes else None})
json.dump(rows, open(O + name + "_unspellable.json", "w"), indent=1)
print(name, len(rows), "with an OCR direction word over the letters:", sum(1 for r in rows if r["ocr"]))
c = collections.Counter(tuple(r["run"]) for r in rows); print(c.most_common(12))
for r in rows:
    if r["ocr"]: print(r["cell"], r["run"], r["ocr"])
