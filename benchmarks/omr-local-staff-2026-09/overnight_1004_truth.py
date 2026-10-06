"""overnight 2026-10-04, step 0: dump the truth-set far heads (44 Litolff p3, 11 Brahms p1) with the
reference positions exactly as `farhead_all_wired_eval.py` / `jut_from_ink_eval.py` use them
(`score_standard_box.build(doc)["far"]`; `3/0/0/6/2` reference is -6 per Sean; `1/0/10/14/1` is excluded
inside `build`). Needs the truth-set records symlinked into benchmarks/acceptance/quick/out/<doc>/.

  python3 overnight_1004_truth.py <out.json>
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import score_standard_box as sb

SEAN = {"glyph/3/0/0/6/2": [-6]}

if __name__ == "__main__":
    out = {}
    for doc in ("beethoven5-litolff", "brahms1-breitkopf"):
        D = sb.build(doc)
        out[doc] = [dict(subject=h["subject"], page=h["page"], box=list(h["box"]), cls=h["cls"],
                         truth=SEAN.get(h["subject"], h["truth"])) for h in D["far"]]
        print(doc, len(out[doc]), "pages", sorted({h["page"] for h in out[doc]}))
    Path(sys.argv[1]).write_text(json.dumps(out))
