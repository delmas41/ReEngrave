"""lane-farhead-5-6: the in-sample truth set (Litolff p3 + Brahms p1 far heads, `truth.json`) replayed on the 10-07 extracts with the
reader's flag OFF then ON. Control: the OFF arm must equal the 10-07 record's own answers (repro count printed). Read only.
  python3 farhead_5_6_truthset.py <truth.json> <x7 litolff> <x7 brahms> [flag=1 ...]"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_5_6_diag as D
import edge_census as ec
import overnight_1004_report as R

SEAN = {"glyph/3/0/0/6/2": [-6]}
EXCLUDE = {"glyph/1/0/10/14/1"}


def tally(rows):
    return ec.tally([r["v"] for r in rows.values()])


def run(data, rep, heads, flags):
    for k, v in flags.items():
        D.FH.READER_KEYWORDS[k] = v
    out = {}
    for h in heads:
        s = h["subject"]
        g, r, cap, gl, ctx = D.read_one(rep, data, s)
        truth = SEAN.get(s, h["truth"])
        out[s] = dict(pos=r["pos"], reason=r["reason"], truth=truth, v=ec.verdict(r["pos"], truth))
    return out


if __name__ == "__main__":
    truth = json.loads(Path(sys.argv[1]).read_text())
    flags = {}
    for kw in sys.argv[4:]:
        k, v = kw.split("=")
        flags[k] = v == "1"
    summary = {}
    for doc, src, page in (("beethoven5-litolff", sys.argv[2], 3), ("brahms1-breitkopf", sys.argv[3], 1)):
        data, rep = D.load(src, doc)
        G = data["glyphs"]
        heads = [h for h in truth[doc] if h["page"] == page and h["subject"] not in EXCLUDE
                 and h["subject"] in G and "box" in G[h["subject"]]]
        off = run(data, rep, heads, {k: False for k in flags})
        rec_ok = sum(1 for h in heads if ((G[h["subject"]].get("fh") or {}).get("value")) == off[h["subject"]]["pos"]
                     or (G[h["subject"]].get("fh") is None and off[h["subject"]]["pos"] is None))
        on = run(data, rep, heads, flags)
        print("==", doc, "p%d" % page, "n", len(heads), "OFF", tally(off), "ON", tally(on), "| OFF reproduces the record on", rec_ok, "of", len(heads))
        broken = []
        for s in off:
            if off[s]["pos"] != on[s]["pos"]:
                print("  ", s, "truth", off[s]["truth"], off[s]["pos"], off[s]["v"], "->", on[s]["pos"], on[s]["v"], on[s]["reason"][:60])
            if off[s]["v"] == "right" and on[s]["v"] != "right":
                broken.append(s)
        print("  right heads broken:", broken)
        summary[doc] = dict(off=off, on=on, broken=broken)
    Path(HERE / "out/farhead_5_6_truthset.json").write_text(json.dumps(summary, default=str))
