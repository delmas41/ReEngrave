"""ROADMAP 2.184 -- replay a WHOLE 20261020-night record (per-page slices from slices_2_184.py; no gather, no detector) through
ADJUDICATE..INFER..second EVALUATE (review.rerun.run_stages) and EXPORT (export.to_musicxml), OMR_REST_PAIR_STRONGER_BLUE off vs on.
Measures the EXPORTED FILE. Per arm writes OUTDIR/<doc>.<arm>.json (rest verdicts, written/red/guessed counts, xml rest counts) and .musicxml.
Control: the OFF arm's live rest_is_not_a_rest verdicts must equal the record's stored ones.
usage: replay_2_184.py DOC SLICEDIR OUTDIR ARM[,ARM...]     ARM = off | on"""
import collections, glob, json, os, re, sys, time
sys.path.insert(0, ".")
from tools.omr import acceptance as A  # noqa: E402
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SD, OUTDIR, ARMS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
D = os.path.join(SD, DOC)
FLAG = "OMR_REST_PAIR_STRONGER_BLUE"
os.makedirs(OUTDIR, exist_ok=True)


def rows(kind):
    out = []
    for p in sorted(glob.glob(os.path.join(D, "*.%s.jsonl" % kind))):
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


t0 = time.time()
rec = {"observations": rows("observations"), "abstentions": rows("abstentions"), "verdicts": []}
stored = live(rows("verdicts"), "rest_is_not_a_rest")
print(DOC, "rows", len(rec["observations"]), "%.0fs" % (time.time() - t0), flush=True)
for arm in ARMS:
    os.environ[FLAG] = "1" if arm == "on" else "0"
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    del log
    vs = result["record"]["verdicts"]
    rv = live(vs, "rest_is_not_a_rest")
    brief = {g: [v["outcome"][:4], v.get("value"), v.get("reason"), ((v.get("detail") or {}).get("rest_pair") or None),
                 v.get("margin"), (v.get("detail") or {}).get("class")] for g, v in rv.items()}
    t1 = time.time()
    xml, report = E.to_musicxml(result)
    notes = re.findall(r"<note\b.*?</note>", xml, flags=re.S)
    rests = [n for n in notes if "<rest" in n]
    R = E.Record({"record": {"observations": [], "abstentions": [], "verdicts": vs}})
    guessed = collections.Counter()
    for g in rv:
        gs = E.guess_of(R, g) or E.claim_guess_of(R, g) or E.rest_pair_guess_of(R, g)
        if gs:
            guessed[gs["rule"]] += 1
    red = report.get("bars_written_red") or {}
    try:
        bau = {k: v for k, v in A.bars_add_up(xml).items() if not isinstance(v, (list, dict))}
    except Exception as e:
        bau = {"error": str(e)[:200]}
    ctl = None
    if arm == "off":
        same = sum(1 for g, v in stored.items() if g in rv and (v["value"], v.get("reason")) == (rv[g].get("value"), rv[g].get("reason")))
        ctl = dict(stored=len(stored), live=len(rv), same=same)
    out = dict(doc=DOC, arm=arm, control=ctl, rest_verdicts=brief,
               xml=dict(notes=len(notes), rests=len(rests), pitched=len(notes) - len(rests), guessed_rests=sum(1 for n in rests if "reengrave:guessed" in n)),
               written=report.get("written"), bars_written_red=red.get("bars"), red_rows=red.get("noteheads_and_rests"),
               notes_not_written_total=report.get("notes_not_written_total"), notes_not_written=report.get("notes_not_written"),
               guessed_by_rule=dict(guessed), guessed_report=report.get("guessed"), bars_add_up=bau)
    json.dump(out, open(os.path.join(OUTDIR, "%s.%s.json" % (DOC, arm)), "w"), default=str)
    open(os.path.join(OUTDIR, "%s.%s.musicxml" % (DOC, arm)), "w").write(xml)
    print(DOC, arm, "control", ctl, "rests", len(rests), "guessed rests", out["xml"]["guessed_rests"], "red", red.get("bars"),
          "export %.0fs" % (time.time() - t1), "total %.0fs" % (time.time() - t0), flush=True)
    del vs, result, xml
