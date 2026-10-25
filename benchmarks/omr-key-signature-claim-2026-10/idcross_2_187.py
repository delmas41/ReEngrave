"""2.187 leak control: does the row-id SPELLING ('obs:%06d') change the exported file once ids pass 999999?
Replays the Brahms sample pages from slices with the log's id counter started at an OFFSET (so ids cross 10^6 inside the run), twice:
offset O and O+DELTA (DELTA extra ids == 535 inert claim rows). No flag, no claim: only the ids differ.
usage: idcross_2_187.py SLICEDIR OUTDIR OFFSET DELTA [PAGES]"""
import collections, hashlib, json, os, sys
sys.path.insert(0, ".")
from tools.omr.staged import export as E
from tools.omr.staged.review import rerun as RR
SD, OUT, OFF, DELTA = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
PAGES = [int(x) for x in sys.argv[5].split(",")] if len(sys.argv) > 5 else [0, 4, 5, 8, 12, 14, 19, 25]
os.makedirs(OUT, exist_ok=True)
P = os.path.join(SD, "brahms")
def ld(kind):
    out = []
    for f in [os.path.join(P, n) for n in ["g.%s.jsonl" % kind, "common.%s.jsonl" % kind] + ["p%02d.%s.jsonl" % (p, kind) for p in PAGES]]:
        if os.path.exists(f):
            out += [json.loads(l) for l in open(f)]
    return out
rec = {"observations": ld("observations"), "abstentions": ld("abstentions"), "verdicts": []}
for tag, off in (("A", OFF), ("B", OFF + DELTA), ("A2", OFF)):
    log, _ = RR.rebuild_gather(rec)
    n0 = log._n
    log._n += off
    RR.run_stages(log)
    n1 = log._n
    result = {"record": log.to_json(), "summary": log.summary()}
    xml, report = E.to_musicxml(result)
    open(os.path.join(OUT, tag + ".xml"), "w").write(xml)
    print(tag, "gather rows", n0, "offset", off, "final id counter", n1, "crossed 1e6:", n1 > 999999 and n0 + off <= 999999,
          "xml sha", hashlib.sha1(xml.encode()).hexdigest()[:10], "notes", xml.count("<note"), flush=True)
