"""ROADMAP 2.186 -- replay a night record (per-page slices from slices_2_186.py; no gather, no detector) through ADJUDICATE..INFER..second
EVALUATE (review.rerun.run_stages) and EXPORT, `OMR_ONE_INK_ONE_MARK` off vs on, and measure the EXPORTED FILE.
The ON arm first applies the SAME merge the live gather applies (`one_ink.plan`, on the stored production-detector boxes of each cell: reader
`detector`, IoU/class rules identical) to the stored rows: an absorbed box's rows are dropped, the winner's GLYPH_BOX and
ACCIDENTAL_STAFF_POSITION rows get `detail.one_ink`, MARK_GROUP rows are patched. The live == replay equality is checked separately
(live_check_2_186.py re-runs the detector on pages).
Control: the OFF arm's live verdicts (rest_is_not_a_rest, duration, accidental_owner) must equal the record's stored ones.
usage: replay_2_186.py DOC SLICEDIR OUTDIR ARM[,ARM...] [PAGES=p04,p07]"""
import collections, glob, json, os, re, sys, time
sys.path.insert(0, ".")
from tools.omr import acceptance as A  # noqa: E402
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged import one_ink as OI  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SD, OUTDIR, ARMS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
PAGES = set(sys.argv[5].split(",")) if len(sys.argv) > 5 else None
D = os.path.join(SD, DOC)
os.makedirs(OUTDIR, exist_ok=True)
QS = ("rest_is_not_a_rest", "accidental_owner", "accidental", "duration", "key_signature")


def rows(kind):
    out = []
    for p in sorted(glob.glob(os.path.join(D, "*.%s.jsonl" % kind))):
        if PAGES and not (os.path.basename(p).split(".")[0] in PAGES or os.path.basename(p).startswith(("common", "g."))):
            continue
        out += [json.loads(l) for l in open(p)]
    return out


def live(verdicts, quantity):
    chains = collections.defaultdict(list)
    for v in verdicts:
        if v["quantity"] == quantity and v["subject"].startswith("glyph/"):
            chains[v["subject"]].append(v)
    out = {}
    for g, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        out[g] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
    return out


def merged_rows(obs, abst):
    """Apply the live merge to stored rows. Returns (obs, abst, stats)."""
    cells = collections.defaultdict(list)
    for o in obs:
        if o["quantity"] == "glyph_box" and o["reader"] == "detector" and isinstance(o["value"], list):
            parts = o["subject"].split("/")
            cells["/".join(parts[:5])].append(o)
    drop, win, stats = set(), {}, collections.Counter()
    for cell, bs in cells.items():
        bs.sort(key=lambda o: int(o["subject"].split("/")[5]))
        boxes = [(o["value"][0], o["value"][1], o["value"][2], o["value"][3], o["value"][4], o["score"] or 0.0) for o in bs]
        p = OI.plan(boxes)
        for i, info in p.items():
            win[bs[i]["subject"]] = OI.detail_of(info, bs[i]["value"][0], bs[i]["score"] or 0.0)
            fam = OI.family_of(bs[i]["value"][0])
            stats["merged_" + fam] += 1
            stats["absorbed_" + fam] += len(info["absorbed"])
            for j in info["absorbed"]:
                drop.add(bs[j]["subject"])
    # patch MARK_GROUP
    gid_of = {o["subject"]: o["value"] for o in obs if o["quantity"] == "mark_group"}
    members = collections.defaultdict(list)
    for s, g in gid_of.items():
        members[g].append(s)
    newobs = []
    for o in obs:
        s = o["subject"]
        if s in drop:
            continue
        if o["quantity"] in ("glyph_box", "accidental_staff_position") and s in win and o["quantity"] != "mark_group":
            if o["quantity"] == "glyph_box" and o["reader"] != "detector":
                newobs.append(o); continue
            o = dict(o); o["detail"] = dict(o.get("detail") or {}); o["detail"].update(win[s])
        if o["quantity"] == "mark_group":
            g = o["value"]
            left = [m for m in members[g] if m not in drop]
            if len(left) != len(members[g]):
                o = dict(o); d = dict(o["detail"]); d["size"] = len(left)
                if len(left) > 1:
                    d["members"] = left
                else:
                    d.pop("members", None)
                if d.get("rep") in drop:
                    d["rep"] = left[0] if left else d["rep"]
                o["detail"] = d
        newobs.append(o)
    newabs = [a for a in abst if a["subject"] not in drop]
    stats["rows_dropped"] = len(obs) - len(newobs) + len(abst) - len(newabs)
    return newobs, newabs, dict(stats)


t0 = time.time()
OBS, ABS = rows("observations"), rows("abstentions")
stored = {q: live(rows("verdicts"), q) for q in QS}
print(DOC, "rows", len(OBS), "%.0fs" % (time.time() - t0), flush=True)
for arm in ARMS:
    os.environ[OI.ONE_INK_ENV] = "1" if arm == "on" else "0"
    o2, a2, mstats = (merged_rows(OBS, ABS) if arm == "on" else (OBS, ABS, {}))
    log, _ = RR.rebuild_gather({"observations": o2, "abstentions": a2, "verdicts": []})
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    del log
    vs = result["record"]["verdicts"]
    brief = {}
    for q in QS:
        for g, v in live(vs, q).items():
            brief.setdefault(q, {})[g] = [v["outcome"][:4], v.get("value") if q != "duration" else None, v.get("reason"), v.get("margin"),
                                           (v.get("detail") or {}).get("one_ink"), v.get("detail", {}).get("alteration") if q == "accidental_owner" else None]
    t1 = time.time()
    xml, report = E.to_musicxml(result)
    notes = re.findall(r"<note\b.*?</note>", xml, flags=re.S)
    rests = [n for n in notes if "<rest" in n]
    R = E.Record({"record": {"observations": [], "abstentions": [], "verdicts": vs}})
    guessed = collections.Counter()
    for q in ("rest_is_not_a_rest", "accidental"):
        for g in live(vs, q):
            gs = E.one_ink_guess_of(R, g)
            if gs:
                guessed[gs["rule"] + ":" + q] += 1
    red = report.get("bars_written_red") or {}
    try:
        bau = {k: v for k, v in A.bars_add_up(xml).items() if not isinstance(v, (list, dict))}
    except Exception as e:
        bau = {"error": str(e)[:200]}
    ctl = None
    if arm == "off":
        ctl = {}
        for q in QS:
            st, lv = stored[q], brief.get(q, {})
            ctl[q] = dict(stored=len(st), live=len(lv), same=sum(1 for g, v in st.items() if g in lv and (v["outcome"][:4], v.get("reason")) == (lv[g][0], lv[g][2])))
    out = dict(doc=DOC, arm=arm, pages=sorted(PAGES) if PAGES else "all", merge=mstats, control=ctl, verdicts=brief,
               xml=dict(notes=len(notes), rests=len(rests), pitched=len(notes) - len(rests), guessed_notes_blue=sum(1 for n in notes if "reengrave:guessed" in n and "<rest" not in n),
                        guessed_rests=sum(1 for n in rests if "reengrave:guessed" in n), accidentals=len(re.findall(r"<accidental>", xml)),
                        beams=len(re.findall(r"<beam ", xml))),
               written=report.get("written"), bars_written_red=red.get("bars"), red_rows=red.get("noteheads_and_rests"),
               notes_not_written_total=report.get("notes_not_written_total"), notes_not_written=report.get("notes_not_written"),
               accidental_census=report.get("accidentals") or report.get("accidental_census"), guessed_by_one_ink=dict(guessed),
               guessed_report=report.get("guessed"), bars_add_up=bau, report_keys=sorted(report.keys()))
    tag = "" if not PAGES else "." + "-".join(sorted(PAGES))
    json.dump(out, open(os.path.join(OUTDIR, "%s.%s%s.json" % (DOC, arm, tag)), "w"), default=str)
    open(os.path.join(OUTDIR, "%s.%s%s.musicxml" % (DOC, arm, tag)), "w").write(xml)
    print(DOC, arm, "control", ctl, "merge", mstats, "rests", len(rests), "guessed rests", out["xml"]["guessed_rests"], "red", red.get("bars"),
          "acc", out["xml"]["accidentals"], "export %.0fs" % (time.time() - t1), "total %.0fs" % (time.time() - t0), flush=True)
    del vs, result, xml
