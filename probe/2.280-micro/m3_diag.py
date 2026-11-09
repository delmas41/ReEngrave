"""2.280 micro test, DIAGNOSIS of the failures (after the registered run; nothing here changes a number in m2_score).
usage: m3_diag.py plate"""
import collections
import json
import sys

plate = sys.argv[1]
SL = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261104-night/"
OWN = {"barline", "clef", "key_signature", "meter", "leading_column", "bracket", "word"}
MASKF = {"accidental", "clef", "meter", "text", "dynamic", "rest", "whole_rest"}
res = json.load(open("out/2.280-micro/proto_%s.json" % plate))["results"]
claims, glyph, family = [], {}, {}
for line in open(SL + plate + "/observations.jsonl"):
    if '"claimed_area"' in line:
        o = json.loads(line)
        d = o["detail"]
        if o["quantity"] == "claimed_area" and d.get("unit") == "area" and d.get("owner") in OWN:
            claims.append(dict(owner=d["owner"], source=d.get("source"), standing=d.get("standing"), box=o["value"], page=int(o["subject"].split("/")[1])))
    elif '"glyph_box"' in line or '"page_mark"' in line:
        o = json.loads(line)
        if o["quantity"] == "glyph_box" and o["detail"].get("bbox_page_px"):
            glyph[o["subject"]] = dict(cls=o["value"][0], page=o["detail"]["bbox_page_px"], cat=o["detail"].get("category"), score=o.get("score"))
        elif o["quantity"] == "page_mark":
            family[o["subject"]] = o["detail"].get("family")


def ov(a, b):
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


print("=== (a) real heads that arm B lost to the claim mask (filed unmasked, not filed masked): what covers the stem box")
for s, r in res.items():
    if "real51" in r["groups"] and r["B_noclaims"]["status"] == "filed" and r["B"]["status"] != "filed":
        box = r["B_noclaims"]["box"]
        pg = r["page"]
        hit = [(c["owner"], c["source"], c["standing"]) for c in claims if c["page"] == pg and ov(c["box"], box)]
        gl = [(g["cls"], family.get(k)) for k, g in glyph.items() if k.startswith("glyph/%d/" % pg) and ov(g["page"], box) and (family.get(k) in MASKF or g["cat"] in ("accidental", "clef"))]
        print(" ", s, r["label"], "unmasked", r["B_noclaims"]["direction"], r["B_noclaims"].get("kind"), "claims:", collections.Counter(hit), "glyph claims:", gl[:4])

print("\n=== (b) not-note heads arm B still stems: what ink IS there (glyph boxes overlapping the head box, by class/category/family)")
for s, r in res.items():
    if "notnote30" in r["groups"] and r["B"]["status"] == "filed":
        pg = r["page"]
        hb = r["page_box"]
        near = [(g["cls"], g["cat"], family.get(k), round(g["score"] or 0, 2)) for k, g in glyph.items() if k.startswith("glyph/%d/" % pg) and ov(g["page"], hb)]
        print(" ", s, r["label"], r["B"]["direction"], r["B"].get("kind"), "boxes at the head:", near)
print("  and the 9 N heads arm B (unmasked, = noclaims) filed that the mask removed:")
for s, r in res.items():
    if "notnote30" in r["groups"] and r["B_noclaims"]["status"] == "filed" and r["B"]["status"] != "filed":
        pg = r["page"]
        hb = r["page_box"]
        near = [(g["cls"], g["cat"], family.get(k)) for k, g in glyph.items() if k.startswith("glyph/%d/" % pg) and ov(g["page"], hb)]
        print("   ", s, r["label"], "boxes:", near)

print("\n=== (c) real heads arm B abstains on, by label and why")
c = collections.Counter()
for s, r in res.items():
    if "real51" in r["groups"] and r["B"]["status"] != "filed":
        c[(r["label"], r["B"].get("why"), r["A_ship"], r["C_flip"]["status"])] += 1
for k, v in sorted(c.items(), key=str):
    print("  label=%s why=%s A=%s flip_filed=%s : %d" % (k[0], k[1], k[2], k[3], v))

print("\n=== (d) agreement: box geometry of filed vs record row (sp units): dy_top, dy_bot, dx_center, widths")
rows = []
for s, r in res.items():
    if "agree200" in r["groups"] and r["B"]["status"] == "filed" and r["row_boxes"]:
        B = r["B"]["box"]
        sp = r["sp"]
        best = max(r["row_boxes"], key=lambda rb: max(0.0, min(B[3], rb[3]) - max(B[1], rb[1])))
        rows.append(((B[1] - best[1]) / sp, (B[3] - best[3]) / sp, ((B[0] + B[2]) / 2 - (best[0] + best[2]) / 2) / sp, (B[2] - B[0]) / sp, (best[2] - best[0]) / sp))
import statistics as st
for i, nm in enumerate(("dy_top", "dy_bot", "dx_center", "w_filed", "w_row")):
    v = [x[i] for x in rows]
    q = sorted(v)
    print("  %-9s n=%d median %.2f  p10 %.2f  p90 %.2f" % (nm, len(v), st.median(v), q[len(q) // 10], q[9 * len(q) // 10]))

print("\n=== (e) agreement: heads where the DIRECTION differs, and abstentions, by why")
c = collections.Counter()
for s, r in res.items():
    if "agree200" in r["groups"] and r["B"]["status"] != "filed":
        c[("abstain", r["B"].get("why"), r["A_ship"])] += 1
for k, v in sorted(c.items(), key=str):
    print("  ", k, v)
