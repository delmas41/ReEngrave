"""2.220 m2: one saved GATHER per plate (flag ON, so Q.HEAD_INK rows are filed) cut into lane_report slices
(`OUTROOT/<plate>/{observations,abstentions,verdicts}.jsonl`), and the subset sample file the report reads
(`LANE_REPORT_SAMPLE`). Both arms then replay the SAME gather rows (`--replay-gathered --tag OUTROOT`): OFF ignores the rows.
usage: m2_slices.py GATHERDIR OUTROOT SAMPLE_JSON"""
import json, pathlib, sys
from tools.omr.staged import lane_report as LR
from tools.omr.staged.record_io import load_record

G, OUT, SAMPLE = (pathlib.Path(a) for a in sys.argv[1:4])
SUB = {"litolff": ([4, 6], [1]), "brahms": ([5, 14], [0])}
for plate in SUB:
    rp = G / ("%s.record.json" % plate)
    if not rp.exists():
        continue
    r = load_record(str(rp))
    r = r.get("record", r)
    d = OUT / plate
    d.mkdir(parents=True, exist_ok=True)
    for kind in ("observations", "abstentions", "verdicts"):
        rows = list(r.get(kind) or ())
        if kind == "verdicts":
            rows = [v for v in rows if v.get("quantity") in LR.STORED_QUANTITIES]
        with open(d / ("%s.jsonl" % kind), "w") as fh:
            for it in rows:
                fh.write(json.dumps(it, default=str) + "\n")
    hi = sum(1 for k in ("observations", "abstentions") for o in (r.get(k) or ()) if o.get("quantity") == "head_ink")
    print(plate, {k: len(r.get(k) or ()) for k in ("observations", "abstentions", "verdicts")}, "head_ink rows", hi)
s = LR.load_sample(LR.ROOT / "benchmarks" / "lane-report" / "sample.json")
s["what"] = "2.220 m2 subset (NOT the frozen sample): Litolff 4, 6 / Brahms 5, 14, the m1 pages"
for p, (pages, ctx) in SUB.items():
    s["plates"][p]["pages"], s["plates"][p]["context_pages"] = pages, ctx
SAMPLE.write_text(json.dumps(s, indent=1))
