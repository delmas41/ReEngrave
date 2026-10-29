"""Head trim fix 2 (2026-10-29): every WRITTEN note of the 2.220 m2b ON arm on the given pages, trim_head re-run on the page raster
under three arms -- `old` (OMR_HEAD_TRIM_LINE_ONLY=0), `landed` (=1), `v2` (=1 and OMR_HEAD_TRIM_LINE_ONLY_V2=1) -- with the verdict,
extent and trimmed box of each. Read-only on tools/.
usage: python3 -u linecut_v2.py OUT_DIR [plate:page ...]   (default litolff:4,6,10 brahms:5,14)"""
import collections, json, sys, os
import numpy as np

sys.path.insert(0, os.getcwd())
from tools.omr.staged import head_ink as HI
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves

R = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-abe33f84eed18488d/out/lane-report/2.220-m2"
L = "/Users/seanjohnson/Desktop/ReEngrave/library/editions"
PDF = {"litolff": L + "/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": L + "/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
out_dir = sys.argv[1]
os.makedirs(out_dir, exist_ok=True)
want = [a.split(":") for a in sys.argv[2:]] or [("litolff", "4,6,10"), ("brahms", "5,14")]
want = {pl: {int(x) for x in pg.split(",")} for pl, pg in want}
ARMS = {"old": ("0", "0"), "landed": ("1", "0"), "v2": ("1", "1")}


def arm(a):
    os.environ[HI.TRIM_ENV], os.environ[HI.TRIM_V2_ENV] = ARMS[a]


rows = []
for plate, pages in want.items():
    hi, pos = {}, {}
    for kind in ("observations", "abstentions"):
        for line in open("%s/slices/%s/%s.jsonl" % (R, plate, kind)):
            if '"head_ink"' in line or '"notehead_staff_position"' in line:
                o = json.loads(line)
                if o.get("quantity") == "head_ink":
                    d = dict(o.get("detail") or {})
                    d["value"], d["reason"] = o.get("value"), o.get("reason")
                    hi[o["subject"]] = d
                elif o.get("quantity") == "notehead_staff_position" and "value" in o:
                    pos[o["subject"]] = (o["value"], (o.get("detail") or {}).get("rounded"))
    S = json.load(open("%s/report-b/work/%s.on.symbols.json" % (R, plate)))
    notes = [h for h in S["hosts"] if h.get("kind") == "note"]
    for p in sorted(pages & {h["page"] for h in notes}):
        pb = detect_staves(render_page(PDF[plate], p, dpi=600)).page.binary
        sps = [(d["trimmed"][2] - d["trimmed"][0]) / d["extent_sp"][0] for s, d in hi.items()
               if s.startswith("glyph/%d/" % p) and d.get("trimmed") and d.get("extent_sp")]
        sp_page = float(np.median(sps))
        for h in notes:
            if h["page"] != p:
                continue
            s = h["rg"]
            d = hi.get(s) or {}
            box = d.get("page_box")
            if not box:
                continue
            sp = ((d["trimmed"][2] - d["trimmed"][0]) / d["extent_sp"][0]) if d.get("trimmed") and d.get("extent_sp") else sp_page
            pv, pr = pos.get(s, (None, None))
            r = dict(plate=plate, page=p, sub=s, box=box, sp=sp, pos=pv, rounded=pr, type=h.get("type"))
            for a in ARMS:
                arm(a)
                t = HI.trim_head(pb, box, sp, ())
                r[a] = None if t is None else dict(noh=t["not_one_head"], ext=t["extent_sp"], trimmed=t["trimmed"])
            rows.append(r)
        print(plate, p, "sp", round(sp_page, 2), flush=True)
json.dump(rows, open(out_dir + "/rows_v2.json", "w"))

for plate in want:
    for p in sorted(want[plate]):
        P = [r for r in rows if r["plate"] == plate and r["page"] == p]
        if not P:
            continue
        line = "%s p%d n=%d" % (plate, p, len(P))
        for a in ARMS:
            c = collections.Counter(((r[a] or {}).get("noh") or "one_head") for r in P)
            line += " | %s small=%d tall=%d wide=%d nohink=%d" % (a, c["too_small"], c["too_tall"], c["too_wide"], c["no_head_ink"])
        print(line)
tot = {a: collections.Counter(((r[a] or {}).get("noh") or "one_head") for r in rows) for a in ARMS}
print("TOTAL n=%d" % len(rows), {a: dict(c) for a, c in tot.items()})
print("landed->v2 verdict changes:", dict(collections.Counter(
    (((r["landed"] or {}).get("noh") or "one_head"), ((r["v2"] or {}).get("noh") or "one_head")) for r in rows
    if r["landed"] and r["v2"] and r["landed"]["noh"] != r["v2"]["noh"])))
print("old->landed verdict changes:", dict(collections.Counter(
    (((r["old"] or {}).get("noh") or "one_head"), ((r["landed"] or {}).get("noh") or "one_head")) for r in rows
    if r["old"] and r["landed"] and r["old"]["noh"] != r["landed"]["noh"])))
print("old->v2 verdict changes:", dict(collections.Counter(
    (((r["old"] or {}).get("noh") or "one_head"), ((r["v2"] or {}).get("noh") or "one_head")) for r in rows
    if r["old"] and r["v2"] and r["old"]["noh"] != r["v2"]["noh"])))
newtall = [r for r in rows if r["landed"] and r["old"] and r["landed"]["noh"] == "too_tall" and r["old"]["noh"] != "too_tall"]
print("newly too_tall (landed vs old): %d; v2 heals %d" % (len(newtall), sum(1 for r in newtall if r["v2"]["noh"] != "too_tall")))
for r in newtall:
    print("  ", r["sub"], r["rounded"], "old", r["old"]["ext"], "landed", r["landed"]["ext"], "v2", r["v2"]["ext"], r["v2"]["noh"])
