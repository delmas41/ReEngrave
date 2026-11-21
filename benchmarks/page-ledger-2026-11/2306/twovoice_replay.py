"""2.306 two-voice piece: ONE saved gather (OMR_PAGE_STEMS on), re-adjudicated twice in this tree -- "base" as gathered, "new" with the page
reader's two-voice filing (`page_stems._unison_heads`) re-applied OFFLINE to every head the gather filed `two_voices` -- and exported the way
`lane_report --from adjudicate` exports. Like with like: same gather, same pages, same tree; only the re-filed `Q.PAGE_STEM` rows differ.

What is re-applied offline, from the record's own rows: the head's ink (its 2.290 claim strokes + unheld non-upright strokes centred in it), the
page map's contacts (`Q.PAGE_STROKE` touches), the collinear runs (`join_runs` on the record's strokes; held = the record's page-stroke claims only),
the stems other heads hold (`owner: stem` claims). A stroke with no cell `Q.STEM` row is not filed (the gather files a view; counted).
Writes <out>/<plate>.<arm>.symbols.json, .mini-record.json, .musicxml, the new arm's full record, and <plate>.refile.json.
Usage: twovoice_replay.py PLATE GATHERED.record.json OUTDIR PAGES(comma)"""
import os, sys, json, pathlib, collections
from types import SimpleNamespace
sys.path.insert(0, os.getcwd())
os.environ["OMR_PAGE_STEMS"] = "1"
from tools.omr.staged import lane_report as L
from tools.omr.staged.record_io import load_record
from tools.omr.staged import export as E
from tools.omr.staged.review import rerun as RR
from tools.omr.staged import page_stems as PS
from tools.omr.staged import record as R
from tools.omr.staged.record import Q, READERS, ABSTAIN

plate, recp, out, pages = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]), [int(p) for p in sys.argv[4].split(',')]
out.mkdir(parents=True, exist_ok=True)
pg = lambda s: int(s.split("/")[1])


def refile(rec, log):
    """Re-apply the two-voice filing to the gather's `two_voices` heads; returns a census and the per-head outcome."""
    obs, ab = rec["observations"], rec.get("abstentions") or []
    strokes = collections.defaultdict(dict)
    for o in obs:
        if o["quantity"] == "page_stroke":
            d = o["detail"]
            strokes[pg(o["subject"])][int(d["ordinal"])] = dict(box=tuple(d["bbox_page_px"]), kind=o["value"], touches=d.get("touches") or [],
                                                             sp=d.get("staff_space_local_px") or 16.0)
    held = collections.defaultdict(dict)
    claim_of, stem_dirs = {}, collections.defaultdict(dict)
    for o in obs:
        d = o.get("detail") or {}
        if o["quantity"] != "claimed_area":
            continue
        if d.get("source") == "page_head_one":
            for m in d.get("members") or ():
                claim_of[m] = d
        elif d.get("source") == PS.SOURCE and d.get("owner") == PS.OWNER and d.get("page_strokes"):
            stem_dirs[pg(o["subject"])][int(o["value"])] = d.get("direction")
        elif d.get("page_strokes") and d.get("standing", "READ") == "READ" and d.get("owner") not in ("head", "stem"):
            for i in d["page_strokes"]:
                held[pg(o["subject"])].setdefault(int(i), d.get("owner"))
    gbox = {o["subject"]: o["detail"]["bbox_page_px"] for o in obs if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px")}
    gcanon = {o["subject"]: o["value"] for o in obs if o["quantity"] == "glyph_box"}
    cellbox = {o["subject"]: o["value"] for o in obs if o["quantity"] == "cell_box"}
    tv = collections.defaultdict(list)          # (page, head) -> [abstention]
    for a in ab:
        d = a.get("detail") or {}
        if a["quantity"] == "page_stem" and d.get("how") == "two_voices" and pg(a["subject"]) in pages:
            tv[(pg(a["subject"]), d.get("head"))].append(a)
    cen = collections.Counter()
    outcome = {}
    runs_of = {}
    for (p, hid), rows in sorted(tv.items(), key=lambda t: (t[0][0], str(t[0][1]))):
        S = strokes[p]
        if p not in runs_of:
            verts = [dict(ord=o, box=s["box"], sp=s["sp"]) for o, s in S.items() if s["kind"] == "vertical"]
            heads_all = [dict(id=m, box=tuple(d["oval"])) for m, d in claim_of.items() if pg(m) == p and d.get("oval")]
            cross = [dict(ord=o, box=s["box"], kind=s["kind"]) for o, s in S.items() if s["kind"] != "vertical"]
            runs, _ = PS.join_runs(verts, heads_all, cross, held[p])
            vbox = {o: dict(box=s["box"], sp=s["sp"]) for o, s in S.items() if s["kind"] == "vertical"}
            vbox.update({r["ord"]: dict(box=r["box"], sp=r["sp"]) for r in runs})
            runs_of[p] = ({r["ord"]: r["members"] for r in runs}, PS.touch_map(S), heads_all, vbox)
        members_of, tch, heads_all, vbox = runs_of[p]
        g0 = rows[0]["subject"]
        members = sorted({a["subject"] for a in rows})
        hd = next((claim_of[m] for m in members if m in claim_of), None)
        box = tuple(hd["oval"]) if hd and hd.get("oval") else tuple(gbox[g0])
        head = dict(id=hid, members=members, box=box, sp=16.0, strokes=list((hd or {}).get("page_strokes") or ()))
        hink = PS.head_ink([head], S, held[p])

        def touches_ink(h, o):
            mine = hink.get(h) or set()
            return any(t in mine for m in members_of.get(int(o), [int(o)]) for t in tch.get(int(m), ()))
        reading = dict(state="two_voices", candidates=rows[0]["detail"]["candidates"], how="two_voices")
        stems = {o: dict(ord=o, heads=[], directions={d}) for o, d in stem_dirs[p].items() if d in ("up", "down")}
        others = [dict(id=("other", k["id"]), box=k["box"]) for k in heads_all if k["id"] not in members]
        PS._unison_heads([head] + others, {hid: reading}, stems, hink, touches_ink, vbox)
        key = reading["how"] + (("/" + reading["why"]) if isinstance(reading.get("why"), str) else "")
        cen["heads:" + key] += 1
        outcome["%d/%s" % (p, hid)] = dict(members=members, how=key, voices=reading.get("voices"), stroke=reading.get("stroke"))
        if reading["how"] not in (PS.UNISON_HOW, "one_of_two_by_ink", "two_voices_stroke_read_other_way"):
            continue
        for a in rows:
            g = a["subject"]
            gs = R.Subject.from_key(g)
            ck = "cell/%d/%d/%d/%d" % (gs.page, gs.system, gs.staff, gs.cell)
            pb, v = gbox[g], gcanon[g]
            up = float(v[3]) / max(1e-6, pb[2] - pb[0])
            c = SimpleNamespace(bbox_page_px=cellbox[ck], upscale_factor=up, measure_index=gs.cell, page_index=gs.page)
            csub = R.cell(gs.page, gs.system, gs.staff, gs.cell)
            common = dict(reader=READERS.CV_PAGE_STEMS, frame=a["frame"], head=hid, how=reading["how"], candidates=reading["candidates"],
                          held=a["detail"].get("held"), near=a["detail"].get("near"), margin=reading.get("margin"))
            if reading["how"] == "two_voices_stroke_read_other_way":
                log.abstain(gs, Q.PAGE_STEM, reason=ABSTAIN.AMBIGUOUS, note=reading["how"], **common)
                cen["keys:abstain_other_way"] += 1
                continue
            want = ([(d, reading["voices"][d]["stroke"], reading["voices"][d]["side"]) for d in ("up", "down")] if reading["how"] == PS.UNISON_HOW
                    else [(reading["direction"], reading["stroke"], reading["side"])])
            rid = {}
            for d, o, side in want:
                try:
                    rid[d], from_a = PS._cell_row_for(log, c, csub, list(S[int(o)]["box"]))
                    cen["rows:" + ("cell_reader" if from_a else "view")] += 1
                except Exception as e:          # noqa: BLE001 -- a view needs the raster: counted, not filed
                    cen["rows:no_cell_row_offline"] += 1
            if len(rid) != len(want):
                continue
            for d, o, side in want:
                extra = dict(voice=d) if reading["how"] == PS.UNISON_HOW else {}
                log.observe(gs, Q.PAGE_STEM, rid[d], page_stroke=int(o), direction=d, side=side, **extra, **common)
            cen["keys:filed_" + reading["how"]] += 1
    return dict(cen), outcome


syms, fates_by_arm = {}, {}
_got = {}
_orig_mc = E.marks_census


def _capture(rec, fates):
    _got["fates"] = dict(fates)
    return _orig_mc(rec, fates)


E.marks_census = _capture
for arm in ("base", "new"):
    res = load_record(recp)
    rec = res.get("record", res)
    boxes = L.glyph_boxes(rec["observations"])
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    if arm == "new":
        cen, outcome = refile(rec, log)
        print(plate, "refile", cen)
        (out / ("%s.refile.json" % plate)).write_text(json.dumps(dict(census=cen, heads=outcome), indent=0))
    del res, rec
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    from tools.omr.staged.judged import _QUANTITIES as _JQ
    _obs = [o for o in result["record"]["observations"] if o.get("quantity") == "glyph_box"]
    (out / ("%s.%s.mini-record.json" % (plate, arm))).write_text(json.dumps(
        {"observations": _obs, "abstentions": [], "verdicts": [v for v in result["record"]["verdicts"] if v["quantity"] in _JQ]}))
    if arm == "new":
        (out / ("%s.new.record.json" % plate)).write_text(json.dumps(result["record"]))
    del log
    with L.traced_export():
        xml, _rep = E.to_musicxml(result)
    (out / ("%s.%s.musicxml" % (plate, arm))).write_text(xml)
    sym = L.parse_symbols(xml, boxes)
    cp = set(pages)
    sym["hosts"] = [h for h in sym["hosts"] if h.get("page") is None or h.get("page") in cp]
    sym["loose"] = [h for h in sym.get("loose", []) if h.get("page") is None or h.get("page") in cp]
    sym["red_bars"] = L._count(((_rep.get("bars_written_red") or {}).get("bars")))
    fates_by_arm[arm] = {k: v for k, v in _got.get("fates", {}).items() if k.startswith("glyph/") and int(k.split("/")[1]) in cp}
    (out / ("%s.%s.symbols.json" % (plate, arm))).write_text(json.dumps(sym))
    syms[arm] = sym
    del result
import pickle
pickle.dump(fates_by_arm, open(out / ("%s.fates.pkl" % plate), "wb"))
d = L.diff_arms(syms["base"], syms["new"], L.PLATES[plate]["unit"])
print(plate, "red bars", syms["base"].get("red_bars"), "->", syms["new"].get("red_bars"), "hosts", len(syms["base"]["hosts"]), "->",
      len(syms["new"]["hosts"]), {k: {kk: vv for kk, vv in v.items() if vv} for k, v in d["counts"].items() if any(v.values())})
jm = L.judged_moves(out / ("%s.base.mini-record.json" % plate), out / ("%s.new.mini-record.json" % plate), plate,
                    syms["base"]["hosts"], syms["new"]["hosts"])
print(plate, "judged:", {k: v for k, v in jm.items() if not isinstance(v, (list, dict))})
