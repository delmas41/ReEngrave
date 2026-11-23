"""2.306 r14 (coordinator's question, red-bar ranking 2.311): on a re-adjudicated record, the duration narrowings `beams_ambiguous` and
`beam_discounted_uncertain`, and EXPORT's `chord_value_undecided` drops; for each, what the page stem reader holds at that head (Q.PAGE_STEM how /
direction) and whether its chord mates on the same page stem agree on a value. Counts only.
Usage: r14_value_reasons.py REC.json FACTS.json"""
import collections
import json
import sys

from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1])["record"]
facts = json.load(open(sys.argv[2]))
ps = {}
for o in rec["observations"]:
    if o["quantity"] == "page_stem":
        ps[o["subject"]] = ("read:" + str((o.get("detail") or {}).get("how")), (o.get("detail") or {}).get("page_stroke"))
for a in rec.get("abstentions") or ():
    if a.get("quantity") == "page_stem":
        ps.setdefault(a["subject"], ("refused:" + str((a.get("detail") or {}).get("how")), None))
dur = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "duration"}
by_stroke = collections.defaultdict(list)
for k, (how, st) in ps.items():
    if st is not None:
        by_stroke[(k.split("/")[1], st)].append(k)
c = collections.Counter()
ex = collections.defaultdict(list)
for k, v in dur.items():
    r = v.get("reason")
    if r not in ("beams_ambiguous", "beam_discounted_uncertain"):
        continue
    how, st = ps.get(k, ("no page reading", None))
    mates = [m for m in by_stroke.get((k.split("/")[1], st), []) if m != k] if st is not None else []
    mate_dec = [dur[m]["value"] for m in mates if m in dur and dur[m]["outcome"] == "decided"]
    tag = (r, how.split(":")[0], "mate decided" if mate_dec else ("mates, none decided" if mates else "no mate on the stem"))
    c[tag] += 1
    ex[tag].append(k)
for k, n in sorted(c.items()):
    print(n, k, ex[k][:4])
cv = (facts.get("notes_not_written") or {})
print("EXPORT notes_not_written keys:", {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in (cv.items() if isinstance(cv, dict) else [])})
