"""2.233 census from lane_report slices, re-adjudicated (no regather): usage census2.py PLATE TAG OUT.json [FLAG=VAL ...]
Counts every pitched head / rest the exporter refused for a value reason, with the Q.DURATION verdict's reason and detail."""
import sys, json, collections, os, time
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a26d61ddc53de8906')
plate, tag, outp = sys.argv[1], sys.argv[2], sys.argv[3]
for a in sys.argv[4:]:
    k, _, v = a.partition('=')
    os.environ[k] = v
from tools.omr.staged import lane_report as L, export as E
from tools.omr.staged.review import rerun as RR
rec = L.load_slices(L.slice_dir(plate, tag))
sample = L.load_sample()
cp = set(L.counted_pages(sample, plate)) if hasattr(L, 'counted_pages') else None
boxes = L.glyph_boxes(rec["observations"])
t0 = time.time()
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
result = {"record": log.to_json(), "summary": log.summary()}
print('adjudicated', round(time.time() - t0), 's')
cap = {}
orig = E._place_notes
def wrap(*a, **kw):
    cap['fates'] = kw.get('fates')
    return orig(*a, **kw)
E._place_notes = wrap
origc = E._chords_whose_value_would_be_voted
def wrapc(runs):
    o = origc(runs)
    cap['chord'] = [d.get('glyph') for d in o]
    return o
E._chords_whose_value_would_be_voted = wrapc
xml, report = E.to_musicxml(result)
fates = cap['fates']
r = result['record']
V = collections.defaultdict(dict)
for v in r["verdicts"]:
    V[v["subject"]][v["quantity"]] = v
rows = []
for sub, f in fates.items():
    if f in ("duration_narrowed", "duration_abstained", "chord_value_undecided", "rest_duration_abstained", "rest_duration_narrowed", "no_pitch"):
        d = V[sub].get("duration") or {}
        rows.append(dict(sub=sub, fate=f, box=boxes.get(sub), outcome=d.get("outcome"), reason=d.get("reason"),
                         thc=(d.get("detail") or {}).get("tips_honour_claims"), uni=(d.get("detail") or {}).get("unison_beam_tips"), bv=(d.get("detail") or {}).get("beam_voices"),
                         cands=[c.get("value") for c in (d.get("candidates") or []) if isinstance(c, dict)] if d else None))
unis = [dict(sub=s, outcome=q["duration"].get("outcome"), reason=q["duration"].get("reason"), value=q["duration"].get("value"),
             uni=(q["duration"].get("detail") or {}).get("unison_beam_tips"), fate=fates.get(s))
        for s, q in V.items() if "duration" in q and (q["duration"].get("detail") or {}).get("unison_beam_tips")]
for _s in os.environ.get('DBGSUBS', '').split(','):
    if _s:
        print('FATE', _s, fates.get(_s), {q: (v.get('outcome'), v.get('reason')) for q, v in V.get(_s, {}).items()})
tot = collections.Counter(fates.values())
pages = {}
for k, n in tot.items():
    pass
thcs = [dict(sub=s, reason=q["duration"].get("reason"), outcome=q["duration"].get("outcome"), thc=q["duration"]["detail"]["tips_honour_claims"], fate=fates.get(s))
        for s, q in V.items() if "duration" in q and (q["duration"].get("detail") or {}).get("tips_honour_claims")]
json.dump(dict(thcs=thcs, unis=unis, rows=rows, fates=dict(tot), written=tot.get('written', 0), xml_len=len(xml)), open(outp, 'w'), default=str)
c = collections.Counter((x['fate'], x['reason']) for x in rows)
print(dict(tot))
for k, n in c.most_common(40):
    print(n, k)
