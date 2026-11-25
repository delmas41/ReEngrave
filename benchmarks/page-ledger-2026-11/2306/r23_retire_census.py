"""2.306 r23 item 5: the retire table. Of the kept heads on an ON gathered record, which does the OLD cell join still decide (`Q.HEAD_STEM`
not answered by the page: reason not `page_*` and no page two-voice narrowing), by why the page reader did not answer, and how many of those
are WRITTEN in the arm's MusicXML (a note whose `rg` is the head). Streams the record (ijson); never loads it whole.
Usage: r23_retire_census.py GATHERED.record.json ARM.musicxml [--list N]"""
import collections
import sys
import xml.etree.ElementTree as ET

import ijson

rec_p, xml_p = sys.argv[1], sys.argv[2]
n_list = int(sys.argv[sys.argv.index("--list") + 1]) if "--list" in sys.argv else 0
written = collections.Counter(n.get("rg") for n in ET.parse(xml_p).getroot().iter("note") if n.get("rg") and n.find("rest") is None)
ps_obs, ps_ab, group_of = set(), {}, {}
with open(rec_p, "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        q = o.get("quantity")
        if q == "page_stem":
            ps_obs.add(o["subject"])
        elif q == "page_mark" and (o.get("detail") or {}).get("family") in ("head", "notehead"):
            for m in (o.get("detail") or {}).get("members") or ():
                group_of[m] = o["subject"]
with open(rec_p, "rb") as f:
    for a in ijson.items(f, "record.abstentions.item", use_float=True):
        if a.get("quantity") == "page_stem":
            d = a.get("detail") or {}
            ps_ab[a["subject"]] = "page:%s%s" % (d.get("how") or d.get("note"), "/" + d["why"] if d.get("why") else "")
refused, hs = set(), {}
with open(rec_p, "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        q = v.get("quantity")
        if q == "notehead_is_not_a_notehead" and v.get("outcome") == "decided" and v.get("value") is True:
            refused.add(v["subject"])
        elif q == "head_stem":
            hs[v["subject"]] = v
cnt, cost, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
page_answered = 0
for s, v in hs.items():
    if s in refused:
        continue
    d = v.get("detail") or {}
    if str(v.get("reason") or "").startswith("page") or d.get("page_voices"):
        page_answered += 1
        continue
    if s in ps_ab:
        why = ps_ab[s]
    elif s in ps_obs:
        why = "page_row_not_in_cell"
    elif s in group_of:
        why = "copy_or_unread_member"
    else:
        why = "no_page_head"
    stem = v.get("outcome") == "decided" and v.get("value")
    w = written.get(s, 0) > 0
    cnt[(why, "stem" if stem else "no_stem")] += 1
    if stem:
        cost[(why, "written" if w else "unwritten")] += 1
        if w:
            ex[why].append(s)
print("heads the page answered:", page_answered)
print("old join decides (kept heads), by why:")
for k, n in cnt.most_common():
    print("  %5d  %s" % (n, k))
print("given a stem by the old join:")
for k, n in sorted(cost.items(), key=lambda t: (-t[1], t[0])):
    print("  %5d  %s" % (n, k))
    if n_list and k[1] == "written":
        print("         ", ex[k[0]][:n_list])
print("WRITTEN heads the old join gives a stem:", sum(n for k, n in cost.items() if k[1] == "written"))
