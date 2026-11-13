"""2306 step 0 (b) + (a-ownership): read one finished record (through EXPORT verdicts), print
  - real heads, heads with no stem row (head_stem abstained no_stem), beam-doubt narrowings (duration narrowed
    beams_ambiguous / beam_discounted_uncertain), red bars holding at least one of them;
  - page beams (Q.PAGE_BEAM role beam) and who the 2.284 page ledger says owns their ink (via the cell Q.STROKE page_stroke links
    and the cells' Q.STROKE_OWNER verdicts), by owner family; the census skipped-by-claim counts.
Usage: python3 stem_beam_census.py REC.json [--no-export] [--pages 6,16]"""
import collections
import json
import sys
import os

sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record  # noqa: E402

BEAM_DOUBT = ("beams_ambiguous", "beam_discounted_uncertain")


def pg(s):
    p = (s or "").split("/")
    return int(p[1]) if len(p) > 1 and p[1].lstrip("-").isdigit() else None


def main():
    path = sys.argv[1]
    no_export = "--no-export" in sys.argv
    pages = None
    if "--pages" in sys.argv:
        pages = {int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")}
    res = load_record(path)
    rec = res["record"]
    vs = rec["verdicts"]
    keep = (lambda s: True) if pages is None else (lambda s: pg(s) in pages)
    by = collections.defaultdict(dict)
    for v in vs:
        if keep(v["subject"]):
            by[v["quantity"]][v["subject"]] = v
    heads = set(by["head_stem"])
    refused = {s for s, v in by["notehead_is_not_a_notehead"].items() if v["outcome"] == "decided" and v["value"] is True}
    twin = {s for s, v in by["duration"].items() if v["reason"] == "owned_by_another_staff"}
    real = heads - refused - twin
    nostem = {s for s in real if by["head_stem"][s]["outcome"] == "abstained" and by["head_stem"][s]["reason"] == "no_stem"}
    doubt = {s for s in real if s in by["duration"] and by["duration"][s]["outcome"] == "narrowed" and by["duration"][s]["reason"] in BEAM_DOUBT}
    dr = collections.Counter(by["duration"][s]["reason"] for s in doubt)
    nostem_dur = collections.Counter((by["duration"][s]["outcome"], by["duration"][s]["reason"]) for s in nostem if s in by["duration"])
    print("FILE", path, "pages", sorted({pg(s) for s in heads}))
    print("real heads %d; no stem row %d (%.1f%%); beam-doubt narrowed %d (%s); both %d" % (
        len(real), len(nostem), 100.0 * len(nostem) / max(1, len(real)), len(doubt), dict(dr), len(nostem & doubt)))
    print("  no-stem heads' duration:", nostem_dur.most_common(8))
    per_page = collections.defaultdict(lambda: [0, 0, 0])
    for s in real:
        per_page[pg(s)][0] += 1
    for s in nostem:
        per_page[pg(s)][1] += 1
    for s in doubt:
        per_page[pg(s)][2] += 1
    print("  per page [real, nostem, doubt]:", dict(sorted(per_page.items())))

    # page beams and their ledger owners
    obs = rec["observations"]
    pb = [o for o in obs if o["quantity"] == "page_beam" and keep(o["subject"])]
    census = [o["detail"] for o in pb if o["value"] == "census"]
    roles = collections.Counter(o["value"] for o in pb if o["value"] not in ("census", "views"))
    print("page beam rows by role:", dict(roles))
    skipped = collections.Counter()
    for c in census:
        for k, n in (c.get("claimed_not_read") or {}).items():
            skipped[k] += n
    print("strokes skipped as claimed (by owner):", dict(skipped.most_common()))
    beams = {(pg(o["subject"]), o["detail"]["ordinal"]): o for o in pb if o["value"] == "beam"}
    links = collections.defaultdict(list)       # (page, page ordinal) -> [(cell subject, cell ordinal)]
    for o in obs:
        if o["quantity"] != "stroke" or not keep(o["subject"]):
            continue
        d = o.get("detail") or {}
        ln = d.get("page_stroke")
        if ln and isinstance(ln, list) and (pg(o["subject"]), ln[0]) in beams:
            cord = int(o["subject"].rsplit("/", 1)[1]) - 375000
            links[(pg(o["subject"]), ln[0])].append((o["subject"], cord, ln))
    owners = {}
    for s, v in by["stroke_owner"].items():
        owners[s] = (v.get("detail") or {}).get("strokes") or {}
    fam = collections.Counter()
    fam_ex = collections.defaultdict(list)
    for k, o in beams.items():
        fs = set()
        for subj, cord, ln in links.get(k, ()):
            parts = subj.split("/")
            cell = "cell/" + "/".join(parts[1:5])
            w = owners.get(cell, {}).get(str(cord))
            if w:
                fs.add("%s:%s" % (w[0], w[1]))
            else:
                fs.add("unclaimed")
        if not links.get(k):
            fs.add("no_cell_link")
        key = ",".join(sorted(fs))
        fam[key] += 1
        fam_ex[key].append(k)
    print("page beams (role beam) %d by ledger owner of their linked cell strokes:" % len(beams))
    for k, n in fam.most_common():
        print("   %4d  %s   e.g. %s" % (n, k, fam_ex[k][:3]))
    json.dump({"fam_ex": {k: v for k, v in fam_ex.items()}, "nostem": sorted(nostem), "doubt": sorted(doubt)},
              open(path + ".2306-census.json", "w"), default=str)

    if no_export:
        return
    from tools.omr.staged import export as E
    xml, report = E.to_musicxml(res)
    red = (report.get("bars_written_red") or {}).get("bars_list") or []
    redkeys = {(b["page"], b["system"], b["staff"], b["cell"]) for b in red if pages is None or b["page"] in pages}

    def bar(s):
        p = s.split("/")
        return (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
    red_with = {bar(s) for s in (nostem | doubt)} & redkeys
    red_ns = {bar(s) for s in nostem} & redkeys
    red_db = {bar(s) for s in doubt} & redkeys
    heads_in_red = {bar(s) for s in real} & redkeys
    print("red bars %d (with any real head %d); holding a no-stem head %d, a beam-doubt head %d, either %d" % (
        len(redkeys), len(heads_in_red), len(red_ns), len(red_db), len(red_with)))
    print("notes not written:", report.get("notes_not_written_total"))


if __name__ == "__main__":
    main()
