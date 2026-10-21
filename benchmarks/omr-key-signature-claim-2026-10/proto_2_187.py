"""2.187 prototype: per system on given pages, key columns from the raster; where the 24 known flat boxes fall.
usage: proto_2_187.py DOC SLICEDIR PAGE[,PAGE..]"""
import collections, glob, json, os, sys
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.staged import key_object as KO
DOC, SD, PAGES = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(",")]
PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
flats = json.load(open("benchmarks/omr-key-signature-claim-2026-10/key_flats_written_as_rests_litolff.json")) if DOC == "litolff" else []
flatg = {f["g"]: f for f in flats}
for pg in PAGES:
    obs = [json.loads(l) for l in open(os.path.join(SD, DOC, "p%02d.observations.jsonl" % pg))]
    lines, cellbox, boxes, meter = {}, {}, collections.defaultdict(dict), {}
    for o in obs:
        s = o["subject"].split("/"); q = o["quantity"]
        if q == "staff_lines" and s[0] == "staff": lines[(int(s[2]), int(s[3]))] = o["value"]
        elif q == "cell_box" and s[0] == "cell" and len(s) == 5: cellbox[(int(s[2]), int(s[3]), int(s[4]))] = o["value"]
        elif q == "glyph_box" and s[0] == "glyph" and len(s) == 6:
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb: boxes[(int(s[2]), int(s[3]), int(s[4]))][int(s[5])] = (str(o["value"][0]), pb)
        elif q == "claimed_area" and (o.get("detail") or {}).get("owner") == "meter" and (o["detail"].get("cell") == 0):
            meter[(int(s[2]), int(s[3]))] = o["value"]
    binary = render_page(PDFS[DOC], pg, dpi=600).binary
    systems = collections.defaultdict(list)
    for (sy, li), ly in sorted(lines.items()): systems[sy].append(li)
    for sy, lis in sorted(systems.items()):
        staves = []
        for li in lis:
            cb = cellbox.get((sy, li, 0)); ly = lines[(sy, li)]
            if not cb: continue
            sp = (ly[-1] - ly[0]) / 4.0
            clefs = [pb for (nm, pb) in boxes[(sy, li, 0)].values() if nm.startswith(("clef", "gClef", "fClef", "cClef")) and (pb[3] - pb[1]) / sp >= 2.0]
            xs = min(clefs, key=lambda b: b[0])[2] if clefs else None
            xh = meter[(sy, li)][0] if (sy, li) in meter else (xs or 0) + KO.WINDOW_REACH_SPACES * sp
            kb = [pb for (nm, pb) in boxes[(sy, li, 0)].values() if nm.startswith(("key", "accidental"))]
            staves.append(dict(key=li, lines=ly, spacing=sp, x_start=xs, x_hi=(min(xh, xs + KO.WINDOW_REACH_SPACES * sp) if xs else None), boxes=kb))
        known = sorted(s_["x_start"] for s_ in staves if s_["x_start"] is not None)
        med = known[len(known) // 2] if known else None
        for s_ in staves:
            if s_["x_start"] is None:
                s_["x_start"] = med; s_["x_hi"] = med + KO.WINDOW_REACH_SPACES * s_["spacing"]; s_["clef_fallback"] = True
        ok = [s_ for s_ in staves if s_["x_start"] is not None]
        dj = json.load(open("data/dossiers/%s.json" % {"litolff": "beethoven-sym5-mvt1", "brahms": "brahms-sym1-mvt1"}[DOC]))
        allowed = sorted({abs(p_["written_fifths"]) for p_ in dj["parts"]})
        obj = KO.find_object(binary, ok, allowed_counts=allowed)
        print("p%d s%d staves %d N %d status %s pitch %s counts %s" % (pg, sy, len(lis), obj["N"], obj["status"], obj["pitch_spaces"], obj["counts"]))
        for k, v in []: print("      staff", k, [(int(q["cx"]), q["src"][0]) for q in v["pieces"]], "xs", [int(s_["x_start"]) for s_ in ok if s_["key"] == k])
        for k, v in obj["by_staff"].items(): print("      staff", k, [(int(q["cx"]), int(q["x1"]), q["src"][0]) for q in v["pieces"]], "xs", int(v["x_start"]))
        for li in lis:
            for gi, (nm, pb) in boxes[(sy, li, 0)].items():
                g = "glyph/%d/%d/%d/0/%d" % (pg, sy, li, gi)
                if g in flatg:
                    st = next((s for s in ok if s["key"] == li), None)
                    c = KO.claim_for_staff(obj, li, st["lines"], st["spacing"]) if st else None
                    cx = (pb[0] + pb[2]) / 2; cy = (pb[1] + pb[3]) / 2
                    inside = bool(c and c["area"][0] <= cx <= c["area"][2] and c["area"][1] <= cy <= c["area"][3])
                    print("    KNOWN FLAT", g, nm, "claim", c and (c["area"], c["standing"], c["own"], c["placed"]), "inside", inside)
