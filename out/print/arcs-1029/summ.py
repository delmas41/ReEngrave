import json, sys, collections
for plate in ("litolff","brahms"):
    d = json.load(open("/private/tmp/claude-501/arcs/%s.json"%plate))
    pages = d["pages"]; n=len(pages)
    print("=====", plate, "pages", pages)
    print("report arcs_not_written", d["report_arcs_not_written"], "total", d["report_total"])
    print("xml tied", d["xml_tied"], "slur", d["xml_slur"], "tie_pairing", d["tie_pairing"], d["counters"])
    # boxes by fate per page
    def grp(f):
        if f.startswith("refused:not_an_arc"): return "not_an_arc("+f.split(":",2)[2]+")"
        return f
    for label, items in (("BOXES", d["rows"]), ("CLUSTERS(true curves)", d["clusters"])):
        c = collections.defaultdict(collections.Counter)
        for r in items: c[grp(r["fate"])][r["page"]] += 1
        print("--", label)
        for f,pc in sorted(c.items(), key=lambda kv:-sum(kv[1].values())):
            print("  %-48s total %5d  /pg %6.1f  | %s" % (f, sum(pc.values()), sum(pc.values())/n, " ".join("p%d:%d"%(p,pc.get(p,0)) for p in pages)))
    # not-written, true: clusters not marked and not staff-line/keysig
    bad = [c for c in d["clusters"] if not c["fate"].endswith("_marked") and not c["fate"].startswith("refused:not_an_arc")]
    print("TRUE unwritten curves:", len(bad), "per page %.1f" % (len(bad)/n), " (clusters: written %d)" % sum(1 for c in d["clusters"] if c["fate"].endswith("_marked")))
    dup_boxes = sum(1 for r in d["rows"] if r["fate"].startswith("merged_duplicate"))
    print("boxes in non-written fate (excl staff line/keysig):", sum(1 for r in d["rows"] if not r["fate"].endswith("_marked") and not r["fate"].startswith("refused:not_an_arc")))
