"""Re-adjudicate a saved lane-report slice with the CURRENT tree and count every verdict (ROADMAP 2.237).

No re-gather, no whole record: the slice (`library/_shared-records/lane-report-slices-<tag>/<plate>/`, the frozen page sample plus
each plate's opening page) is rebuilt into a Log with `review.rerun.rebuild_gather`, the stages run with `pipeline.decide`, and
the verdicts on the SAMPLE pages are (a) counted by (decider, outcome, reason, value) into `fires-<plate>-<tag>.json`, the same
rows `count_fires.py` writes for a whole-movement record, and (b) dumped as JSON lines for the parity / margin analysis.

    OMR_SURYA_KEEP_ALIVE=0 python3 benchmarks/rule-page/replay_slice.py litolff 20261029-night DUMP_DIR
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))


def count_verdicts(verdicts):
    """Same row shape as `count_fires.count`, from an in-memory verdict list (the live chain: every verdict counted once)."""
    seen, superseded = {}, set()
    for v in verdicts:
        val = v.get("value")
        vb = val if isinstance(val, bool) else None
        seen[v["id"]] = (v.get("decider"), v.get("outcome"), v.get("reason"), vb)
        s = v.get("supersedes")
        if s:
            for x in (s if isinstance(s, list) else [s]):
                superseded.add(x)
    c = collections.Counter(seen.values())
    rows = [{"decider": d, "outcome": o, "reason": r, "value": b, "n": n}
            for (d, o, r, b), n in sorted(c.items(), key=lambda kv: (str(kv[0][0]), -kv[1]))]
    return {"verdicts_total": len(seen), "superseded": len(superseded & set(seen)), "rows": rows}


def main(plate, tag, dump_dir):
    from tools.omr.staged import lane_report as LR
    from tools.omr.staged.review import rerun as RR
    sample = json.load(open(ROOT / "benchmarks" / "lane-report" / "sample.json"))["plates"][plate]["pages"]
    keep = set(sample)
    rec = LR.load_slices(LR.slice_dir(plate, tag))
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    del rec
    RR.run_stages(log)
    vs = [v for v in log.to_json()["verdicts"] if LR.page_of(v.get("subject")) in keep]
    out = count_verdicts(vs)
    out["pages"] = sorted(keep)
    json.dump(out, open(HERE / f"fires-{plate}-{tag}.json", "w"), separators=(",", ":"))
    d = pathlib.Path(dump_dir)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / f"{plate}.verdicts.jsonl", "w") as fh:
        for v in vs:
            fh.write(json.dumps(v, default=str) + "\n")
    print(plate, tag, "verdicts", out["verdicts_total"], "rows", len(out["rows"]))


if __name__ == "__main__":
    main(*sys.argv[1:4])
