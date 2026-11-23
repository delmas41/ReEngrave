"""2.306 r19 REACH: of the heads whose `Q.HEAD_STEM` the old cell join still decides with the page stem reader ON, why the page reader had no say.
Usage: r19_reach.py GATHERED.record.json PAGES DUMP_DIR [--list N]
DUMP_DIR holds `page_stems.read`'s exact inputs per page (pickled by the lane's gather hook). Causes, first that applies:
  refused_as_head     -- the box is decided not a notehead (no note is lost)
  copy_on_other_staff -- the head is on the page head list but filed only with the staff it belongs to (2.306 r7, Sean): the box is a copy
  not_on_head_list    -- the box is on no page head (the 2.290 one-head groups)
  page_abstained:<how>-- the page read the head and named no stem (the cell join answered after it)
  page_filed_row      -- the page named a stem the cell join did not use (the row not in the cell)
Heads decided by the page (reason page_*, or a page two-voice narrowing) are counted apart."""
import collections
import glob
import os
import pickle
import sys

sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record  # noqa: E402

rec = load_record(sys.argv[1])
rec = rec.get("record", rec)
pages = {int(x) for x in sys.argv[2].split(",")}
dumps = {}
for f in sorted(glob.glob(os.path.join(sys.argv[3], "p*.pkl"))):
    D = pickle.load(open(f, "rb"))
    if D["page"] in pages:
        dumps[D["page"]] = D             # the last read of the page (one per gather)
member_of = {}
for p, D in dumps.items():
    for h in D["heads"]:
        for m in h["members"]:
            member_of[m] = h
if not dumps:       # no dump: the page head groups as the record files them (the 2.290 head `Q.PAGE_MARK` rows)
    for o in rec["observations"]:
        d = o.get("detail") or {}
        if o["quantity"] == "page_mark" and d.get("family") == "head":
            for m in d.get("members") or ():
                member_of[m] = d
ps = collections.defaultdict(list)
for o in rec["observations"]:
    if o["quantity"] == "page_stem":
        ps[o["subject"]].append(("row", None))
for a in rec.get("abstentions") or []:
    if a.get("quantity") == "page_stem":
        ps[a["subject"]].append(("abst", "%s/%s" % ((a.get("detail") or {}).get("how") or (a.get("detail") or {}).get("note") or a.get("reason"), (a.get("detail") or {}).get("why"))))
notn = {v["subject"] for v in rec["verdicts"] if v["quantity"] == "notehead_is_not_a_notehead" and v.get("outcome") == "decided" and v.get("value")}
cls = {o["subject"]: o["value"][0] for o in rec["observations"] if o["quantity"] == "glyph_box" and isinstance(o.get("value"), list)}
reader = {o["subject"]: o.get("reader") for o in rec["observations"] if o["quantity"] == "glyph_box"}
tot, why, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
for v in rec["verdicts"]:
    if v["quantity"] != "head_stem" or int(v["subject"].split("/")[1]) not in pages:
        continue
    s, d = v["subject"], v.get("detail") or {}
    if (v.get("reason") or "").startswith("page") or d.get("page_voices"):
        tot["page"] += 1
        continue
    tot["cell"] += 1
    if s in notn:
        k = "refused_as_head"
    elif s in ps and any(t == "abst" for t, _ in ps[s]):
        k = "page_abstained:" + str(next(w for t, w in ps[s] if t == "abst"))
    elif s in ps:
        k = "page_filed_row"
    elif s in member_of:
        k = "copy_on_other_staff"
    else:
        k = "not_on_head_list:" + str(reader.get(s))
    k = "%s | %s %s" % (k, v.get("outcome"), v.get("reason"))
    why[k] += 1
    ex[k].append(s + " " + str(cls.get(s)))
print(dict(tot))
n = int(sys.argv[sys.argv.index("--list") + 1]) if "--list" in sys.argv else 0
for k, c in why.most_common():
    print("%5d  %s" % (c, k))
    for e in ex[k][:n]:
        print("         ", e)
# copies: does the box's own owner verdict keep it on this staff (then the cell join's stem reaches the file)?
own = {v["subject"]: v.get("value") for v in rec["verdicts"] if v["quantity"] == "glyph_owner" and v.get("outcome") == "decided"}
cop = [e.split()[0] for k, es in ex.items() if k.startswith("copy_on_other_staff") for e in es]
stay = [s for s in cop if own.get(s) == "staff/" + "/".join(s.split("/")[1:4])]
print("copies %d: owner verdict keeps on this staff %d, another staff %d, no owner verdict %d" % (
    len(cop), len(stay), sum(1 for s in cop if s in own and s not in stay), sum(1 for s in cop if s not in own)))
for s in stay[:n]:
    print("    stays", s)
