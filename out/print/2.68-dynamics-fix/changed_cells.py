"""ROADMAP 2.68 (letter neighbours): bars whose ADJUDICATE `dynamic` verdict differs between the small re-gather on
main 404285f3 (A) and the same re-gather after the fix (B), on the pages both hold. Writes litolff.json / brahms.json
beside this file (cells not already among the ten judged bars in ../2.68-dynamics-back/manifest.json).
python3 changed_cells.py <A litolff record> <B litolff record> <A brahms record> <B brahms record>"""
import json, os, sys
from tools.omr.staged import readout

HERE = os.path.dirname(os.path.abspath(__file__))
judged = {t["cell"] for t in json.load(open(os.path.join(HERE, "../2.68-dynamics-back/manifest.json")))["tiles"]}


def cells(run):
    out = {}
    for v in run.verdicts:
        if v.get("quantity") == "dynamic" and v["subject"].startswith("cell/") and v.get("stage", "ADJUDICATE"):
            out[v["subject"]] = v
    return out


for tag, a_path, b_path in (("litolff", sys.argv[1], sys.argv[2]), ("brahms", sys.argv[3], sys.argv[4])):
    a, b = readout.load_run(a_path), readout.load_run(b_path)
    rows = []
    for k in sorted(set(cells(a)) | set(cells(b)), key=readout._subject_sort_key):
        va = (a.standing(k, "dynamic", "ADJUDICATE") or {}).get("value")
        vb = (b.standing(k, "dynamic", "ADJUDICATE") or {}).get("value")
        if (va or []) != (vb or []):
            rows.append({"cell": k, "before": va, "after": vb, "judged_by_sean_already": k in judged})
    json.dump([r for r in rows if not r["judged_by_sean_already"]], open(os.path.join(HERE, tag + ".json"), "w"), indent=1)
    print(tag, len(rows), "changed;", sum(r["judged_by_sean_already"] for r in rows), "of them among the ten judged bars")
    for r in rows:
        print("  ", r["cell"], r["before"], "->", r["after"], "(judged)" if r["judged_by_sean_already"] else "")
