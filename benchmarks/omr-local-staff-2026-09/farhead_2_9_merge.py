"""lane-farhead-2-9: merge the page shards of `farhead_2_9_census.py` into one file and print the same tallies.
  python3 farhead_2_9_merge.py <out.json> <shard.json> [<shard.json> ...]"""
import collections, json, sys
from pathlib import Path

if __name__ == "__main__":
    out, shards = sys.argv[1], sys.argv[2:]
    res, doc = {}, None
    for p in shards:
        d = json.loads(Path(p).read_text())
        doc = d["doc"]
        res.update(d["res"])
    ok = {s: v for s, v in res.items() if "error" not in v}
    dec = lambda arm: sum(1 for v in ok.values() if v[arm][0] is not None)
    resc = [s for s, v in ok.items() if v["off"][0] is None and v["on"][0] is not None]
    lost = [s for s, v in ok.items() if v["off"][0] is not None and v["on"][0] is None]
    chg = [s for s, v in ok.items() if v["off"][0] is not None and v["on"][0] is not None and v["off"][0] != v["on"][0]]
    ctrl = sum(1 for v in ok.values() if (v["rec"] == v["off"][0]) or (v["rec"] is None and v["off"][0] is None))
    print("==", doc, "far heads", len(res), "errors", len(res) - len(ok), "| decided OFF", dec("off"), "ON", dec("on"),
          "| abstain OFF", len(ok) - dec("off"), "ON", len(ok) - dec("on"))
    print("   rescued (abstain -> decided):", len(resc), "by how:", dict(collections.Counter(ok[s]["how"] for s in resc)),
          "jut sides found:", dict(collections.Counter(ok[s]["sides"] for s in resc)))
    print("   decided -> abstain:", len(lost), "| decided -> other answer:", len(chg))
    print("   CONTROL: OFF arm equals the record's own position on", ctrl, "of", len(ok))
    Path(out).write_text(json.dumps(dict(doc=doc, res=res, rescued=resc, lost=lost, changed=chg), default=str))
