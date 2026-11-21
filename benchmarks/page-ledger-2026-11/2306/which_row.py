"""For glyph keys: the cell Q.STEM row their Q.PAGE_STEM names -- the cell reader's (cv_lines) or a page view (cv_page_stems) -- its box, and its
Q.STEM_TIP_INK / Q.BEAM_STEM_LEVELS / Q.BEAM_STEM_JOIN rows. Also, over the whole record: page stems named views vs cell rows, and how many views
carry tip ink / beam levels. Usage: which_row.py REC.json [glyph ...]"""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record

r = load_record(sys.argv[1])["record"]
obs = r["observations"]
row = {o["id"]: o for o in obs if o["quantity"] == "stem"}
ps = {o["subject"]: o for o in obs if o["quantity"] == "page_stem"}
tip = collections.defaultdict(list)
lev = collections.defaultdict(list)
for o in obs + r["abstentions"]:
    d = o.get("detail") or {}
    sid = d.get("stem_row_id") or d.get("stem_row") or d.get("stem")
    if o["quantity"] == "stem_tip_ink" and sid:
        tip[sid].append(o.get("value", "abst:" + str(o.get("reason"))))
    if o["quantity"] == "beam_stem_levels" and sid:
        lev[sid].append(o.get("value"))
named = collections.Counter()
for s, o in ps.items():
    rr = row.get(o["value"])
    named[rr["reader"] if rr else "?"] += 1
print("page stems name:", dict(named))
views = [o for o in row.values() if o["reader"] == "cv_page_stems"]
print("views", len(views), "with tip ink rows", sum(1 for v in views if tip.get(v["id"])), "with beam levels", sum(1 for v in views if lev.get(v["id"])))
for k in sys.argv[2:]:
    o = ps.get(k)
    if not o:
        print(k, "no page stem row")
        continue
    rr = row.get(o["value"])
    print(k, o["value"], rr and rr["reader"], rr and [round(x) for x in rr["value"]], "tip", tip.get(o["value"]), "levels", lev.get(o["value"]))
