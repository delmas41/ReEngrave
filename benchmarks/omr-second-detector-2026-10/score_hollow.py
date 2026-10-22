"""2.110: Litolff TEST hollow recall/precision (score_ab.score_litolff, unchanged) on (a) all 104 TEST cells and (b) the CLEAN cells = the 104 minus
every cell whose (system, staff, measure) is also a TRAINING cell of the mix (leakage.py found 9: v13 beet5-p2 cells, same page, same cell key; one
pixel-identical, the rest the same cell re-cut -- see FINDINGS). Brahms hollow via score_ab.score_brahms. Same controls as score_ab.
usage: score_hollow.py label=lit.json:bra.json ... [--out f]"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
import importlib.util
spec = importlib.util.spec_from_file_location("score_ab", "benchmarks/omr-labeling-hollow4-2026-10/score_ab.py"); S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
from tools.omr.hand_truth import store as ST
from tools.omr.staged import readout as RO


def leaked_keys():
    keys = set()
    for lst in ("_catalog_train.txt", "_catalog_val.txt"):
        for l in open(f"runs/2.110/cat-old/{lst}"):
            m = re.search(r"/images/beet5-p2-sys(\d+)-s(\d+)-m(\d+)\.png", l)  # Beethoven 5 Litolff, page index 1 (1-based p2)
            if m:
                keys.add(tuple(int(x) for x in m.groups()))
    return keys


def main():
    arms = [a.split("=", 1) for a in sys.argv[1:] if "=" in a and not a.startswith("--")]
    truth, n_truth, cellset = S.litolff_truth()
    leak = leaked_keys() & cellset
    clean = cellset - leak
    n_leak_heads = sum(len(truth.get(k, [])) for k in leak)
    print(f"TEST cells {len(cellset)} ({n_truth} truth heads); leaked cell keys {len(leak)} holding {n_leak_heads} truth heads; clean {len(clean)} cells, {n_truth - n_leak_heads} heads")
    page = ST.load(Path("data/hand-truth/pages/imslp317803/0.json"))
    res = {"leaked_cells": sorted(leak), "leaked_truth_heads": n_leak_heads}
    for lab, v in arms:
        lit, bra = v.split(":")
        run = RO.load_run(lit)
        row = {}
        for tag, cs in (("all104", cellset), ("clean", clean)):
            tt = {k: x for k, x in truth.items() if k in cs}
            r = S.score_litolff(run, tt, cs)
            r.pop("extra_boxes", None); row[tag] = r
            print(f"[{lab} litolff {tag}] recall {r['found']}/{r['truth_heads']}={100*r['recall']:.1f}%  precision {r['hollow_boxes_on_a_truth_head']}/{r['hollow_boxes']}={100*r['precision']:.1f}%  missed {r['missed_truth_heads_by']}")
        b = S.score_brahms(RO.load_run(bra), page); row["brahms"] = b
        print(f"[{lab} brahms] hollow found {b['found_hollow']}/{b['truth_hollow']} boxes {b['hollow_boxes']} extra {b['extra_hollow_boxes']} on {b['extra_sits_on']} filled-called-hollow {b['filled_heads_called_hollow']}")
        res[lab] = row
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(json.dumps(res, indent=1, default=str))

main()
