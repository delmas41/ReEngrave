"""lane-slur-not-ledger: what Sean's tile 6 (Litolff p16 `glyph/16/0/0/0/2`) does with the rule OFF and ON: the count,
the position, and the ownership-by-ledgers witness.   python3 slur_not_ledger_tile6.py <scratch dir with x/*.json>"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import offbox_measured as OM
import slur_not_ledger_oos as O
from tools.omr.annotate import far_head_reader as FH, far_head_owner as FO

doc, page, s = "beethoven5-litolff", 16, "glyph/16/0/0/0/2"
data = json.load(open(Path(sys.argv[1]) / "x" / f"{doc}-{O.NEWTAG}.json"))
g = data["glyphs"][s]
rep = OM.CachedReplay(doc, data)
ctx = rep.adopt_for(page, g["fh"]["shape_source"])
key = "staff/16/0/0"
cls = next(c for (ss, c, b) in rep.boxes_by_page[page] if ss == s)
staves = O.staves_of(data, page)
print("recorded far-head position", g["fh"]["value"], "| recorded owner", g["own"])
for on in (False, True):
    FH.READER_KEYWORDS["slur_not_ledger"] = on
    r = ctx.read(s, tuple(g["box"]), cls, data["staff_lines"][key])
    nf = r["detail"]["note_first"]
    print("ON " if on else "OFF", "position", r["pos"], "|", r["reason"])
    print("     edge", r["detail"].get("edge_y"), "line", nf.get("line_y"), "between", nf.get("between"), "k", nf.get("k"), "gaps", nf.get("gaps"))
    for x in nf.get("refused_rungs") or []:
        print("     refused", round(x["y"], 1), x["why"], {k: (round(v, 2) if isinstance(v, float) else v) for k, v in (x.get("shape") or {}).items()})
    o = FO.owner_by_ledgers(ctx, s, tuple(g["box"]), cls, key, staves)
    print("     owner witness:", o["owner"], o["word"], {k: (v["fits"], v["pos"], (v["reason"] or "")[:60]) for k, v in o["candidates"].items()})
print("---- the staff BELOW as candidate, in detail")
below = [x for x in staves if x["key"] == "staff/16/0/1"][0]
print("record lines", below["lines"])
for on in (False, True):
    FH.READER_KEYWORDS["slur_not_ledger"] = on
    rb = ctx.read(s, tuple(g["box"]), cls, below["lines"])
    nf = rb["detail"]["note_first"]
    print("ON " if on else "OFF", rb["pos"], rb["reason"][:90], "| edge", rb["detail"].get("edge_y"), "line", nf.get("line_y"),
          "between", nf.get("between"), "gaps", nf.get("gaps"), "lines_used", [round(v, 1) for v in rb.get("lines_used", [])])
    for x in nf.get("refused_rungs") or []:
        print("     refused", round(x["y"], 1), x["why"], {k: (round(v, 2) if isinstance(v, float) else v) for k, v in (x.get("shape") or {}).items()})
