"""lane-arcs-1029: PER-ARC fate list (STAGED). Exports a saved record's own verdicts (no re-adjudication) while instrumenting,
read-only, the exporter's arc pass: the merge groups (_arcs_by_kind) and, per slur group, a one-group call of the legacy
_paired_spans. Then assigns every Q.ARC_BOX subject a fate.
usage: arcfates.py RECORD OUTJSON PLATE PAGES"""
import json, sys, collections
from tools.omr.staged import lane_report as L, export as E
from tools.omr.staged.record_io import load_record
from tools.omr.staged.record import Q
Record = E.Record
import tools.omr.export as LEG

rec_path, outp, plate, pages = sys.argv[1], sys.argv[2], sys.argv[3], {int(x) for x in sys.argv[4].split(",")}
with L.record_lock():
    res = load_record(rec_path)
    r = res["record"] if "record" in res else res
    if "record" not in res:
        res = {"record": res, "summary": {}}
    keep = lambda it: (lambda pg: pg is None or pg in pages)(L.page_of(it.get("subject")))
    for k in ("observations", "abstentions", "verdicts"):
        r[k] = [x for x in r[k] if keep(x)]

    GROUPS = []
    orig_abk = E._arcs_by_kind

    def abk(measures, arcs, kinds, spacings, tops, breaks, groups_by_kind=None):
        for segs in LEG._merge_arcs_across_barlines(measures, arcs, spacings, tops, breaks):
            seen = {kinds.get(id(b)) for _m, b in segs}
            kind = "tie" if "tie" in seen else "slur"
            GROUPS.append(dict(kind=kind, segs=[(m, tuple(b)) for m, b in segs], nspans=None))
        return orig_abk(measures, arcs, kinds, spacings, tops, breaks, groups_by_kind=groups_by_kind)

    orig_ps = LEG._paired_spans

    def ps(measures, pools, spacings, tops, breaks, voice_of, *a, **kw):
        for segs in LEG._merge_arcs_across_barlines(measures, pools, spacings, tops, breaks):
            one = [[] for _ in measures]
            for m, b in segs:
                one[m].append(b)
            n = len(orig_ps(measures, one, spacings, tops, breaks, voice_of, *a, **kw))
            key = [(m, tuple(b)) for m, b in segs]
            for g in GROUPS:
                if g["nspans"] is None and g["kind"] == "slur" and g["segs"] == key:
                    g["nspans"] = n
                    break
        return orig_ps(measures, pools, spacings, tops, breaks, voice_of, *a, **kw)

    E._arcs_by_kind = abk
    E._legacy._paired_spans = ps
    try:
        with L.traced_export():
            xml, report = E.to_musicxml(res)
    finally:
        E._arcs_by_kind = orig_abk
        E._legacy._paired_spans = orig_ps

    # ---- per-arc rows
    rec = Record(res)
    box2sub = collections.defaultdict(list)
    rows = {}
    for o in rec.obs_of(Q.ARC_BOX):
        sub = o["subject"]
        s = E._parse_subject(sub)
        if s["glyph"] is None:
            continue
        pb = E._corners_to_wh(E._page_box_of(o))
        row = dict(sub=sub, page=s["page"], system=s["system"], staff=s["staff"], cell=s["cell"],
                   box=list(pb) if pb else None, fate=None, kind=None, group=None)
        anv = rec.verdict(Q.ARC_IS_NOT_AN_ARC, sub)
        kv = rec.verdict(Q.ARC_KIND, sub)
        row["kind"] = kv["value"] if kv and kv["outcome"] == "decided" else None
        if anv is not None and anv["outcome"] == "decided" and anv["value"] is True:
            row["fate"] = "refused:not_an_arc:%s" % anv.get("reason", "?")
        elif not kv or kv["outcome"] != "decided":
            row["fate"] = "refused:kind_%s" % (kv["reason"] if kv else "absent")
        elif str(kv["value"]) not in ("slur", "tie"):
            row["fate"] = "refused:kind_not_an_arc"
        elif pb is None:
            row["fate"] = "refused:arc_no_page_frame"
        else:
            box2sub[tuple(pb)].append(sub)
        rows[sub] = row
    # tie facts from the record and the report
    tp = {}
    for v in rec.verdicts_of(Q.TIE_PAIR):
        if rec.verdict(Q.TIE_PAIR, v["subject"]) is v:
            tp[v["subject"]] = v
    linked_arcs = {a for l in (report.get("tie_links") or []) for a in l["arcs"]}
    contra_arcs = {a: c["kind"] for c in (report.get("tie_contradictions") or []) for a in c["arcs"]}
    # attach groups to rows
    gi = 0
    for g in GROUPS:
        subs = []
        for m, b in g["segs"]:
            for s in box2sub.get(b, []):
                if s not in subs:
                    subs.append(s)
        g["subs"] = subs
        g["id"] = gi; gi += 1
        for s in subs:
            rows[s]["group"] = g["id"]
    # group-level fate
    for g in GROUPS:
        if g["kind"] == "slur":
            g["fate"] = "slur_marked" if g["nspans"] else "refused:slur_binds_fewer_than_two_notes"
            for s in g["subs"]:
                rows[s]["fate"] = g["fate"]
        else:
            seen_pair = {}
            for s in g["subs"]:
                v = tp.get(s)
                if v is None:
                    f = "refused:tie_pair_absent"
                elif v["outcome"] == "decided" and isinstance(v.get("value"), dict):
                    key = (v["value"]["start"], v["value"]["stop"])
                    if s in linked_arcs:
                        f = "tie_marked"
                    elif s in contra_arcs:
                        f = "refused:" + contra_arcs[s]
                    else:
                        f = "refused:tie_pair_decided_not_in_file"
                    if key in seen_pair:
                        f = "merged_duplicate(same pair)"
                    seen_pair.setdefault(key, s)
                elif v["outcome"] == "narrowed":
                    f = "refused:tie_pair_narrowed"
                else:
                    f = "refused:tie_pair_%s" % v.get("reason")
                rows[s]["fate"] = f
            g["fate"] = "tie"
    for row in rows.values():
        if row["fate"] is None:
            row["fate"] = "refused:unplaced(no group)"
    # ---- place clusters: twins (same page, overlapping boxes) -> one curve
    def iou(a, b):
        ax1, ay1, ax2, ay2 = a[0], a[1], a[0] + a[2], a[1] + a[3]
        bx1, by1, bx2, by2 = b[0], b[1], b[0] + b[2], b[1] + b[3]
        iw, ih = min(ax2, bx2) - max(ax1, bx1), min(ay2, by2) - max(ay1, by1)
        if iw <= 0 or ih <= 0:
            return 0.0
        i = iw * ih
        return i / (a[2] * a[3] + b[2] * b[3] - i)
    live = [r_ for r_ in rows.values() if r_["box"]]
    par = list(range(len(live)))
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    bypage = collections.defaultdict(list)
    for i, r_ in enumerate(live):
        bypage[r_["page"]].append(i)
    for pg, idx in bypage.items():
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                if iou(live[idx[a]]["box"], live[idx[b]]["box"]) > 0.5:
                    par[find(idx[a])] = find(idx[b])
    # also tie a cross-barline group's pieces together
    gfirst = {}
    for i, r_ in enumerate(live):
        if r_["group"] is not None:
            if r_["group"] in gfirst:
                par[find(i)] = find(gfirst[r_["group"]])
            else:
                gfirst[r_["group"]] = i
    clusters = collections.defaultdict(list)
    for i in range(len(live)):
        clusters[find(i)].append(i)
    RANK = {"tie_marked": 0, "slur_marked": 0}
    out_clusters = []
    for cid, members in clusters.items():
        ms = [live[i] for i in members]
        best = min(ms, key=lambda m: (RANK.get(m["fate"], 1 if not m["fate"].startswith("refused:not_an_arc") else 2)))
        out_clusters.append(dict(page=best["page"], system=best["system"], fate=best["fate"], n_boxes=len(ms),
                                 subs=[m["sub"] for m in ms], fates=sorted({m["fate"] for m in ms}), box=best["box"]))
    out = dict(plate=plate, pages=sorted(pages), rows=list(rows.values()), clusters=out_clusters,
               groups=[{k: v for k, v in g.items() if k != "segs"} for g in GROUPS],
               report_arcs_not_written=report.get("arcs_not_written"), report_total=report.get("arcs_not_written_total"),
               tie_pairing=report.get("tie_pairing"),
               tied_start=xml.count('<tied type="start"'), slur_start=xml.count('<slur type="start"') + xml.count('<slur number'),
               xml_tied=xml.count("<tied "), xml_slur=xml.count("<slur "),
               counters={k: report.get(k) for k in ("slurs", "ties")})
    json.dump(out, open(outp, "w"), default=str)
    open(outp.replace(".json", ".musicxml"), "w").write(xml)
    json.dump({k: v for k, v in L.glyph_boxes(r["observations"]).items() if (v["cls"] or "").startswith(("notehead", "rest"))},
              open(outp.replace(".json", ".glyphboxes.json"), "w"))
    print(plate, "arc boxes", len(rows), "groups", len(GROUPS), "clusters", len(out_clusters), "not_written", report.get("arcs_not_written_total"))
    print(collections.Counter(r_["fate"] for r_ in rows.values()).most_common())
