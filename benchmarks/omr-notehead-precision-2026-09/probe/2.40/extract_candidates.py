import json
from tools.omr.staged import record_io

REC = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a212d008990c6b49a/out/2.40/litolff-p3-evaluate.json"

d = record_io.load_record(REC)
rec = d["record"]
obs = rec["observations"]
verdicts = rec["verdicts"]

by_subj_q = {}
for o in obs:
    by_subj_q.setdefault((o["subject"], o["quantity"]), []).append(o)

vby_subj_q = {}
for v in verdicts:
    vby_subj_q.setdefault((v["subject"], v["quantity"]), []).append(v)


def cell_key(page, system, staff, cell):
    return f"cell/{page}/{system}/{staff}/{cell}"


def staff_key(page, system, staff):
    return f"staff/{page}/{system}/{staff}"


TARGETS = [
    ("Oboe", 3, 0, 1, 0, 49),
    ("Oboe", 3, 0, 1, 4, 53),
    ("Clarinet", 3, 0, 2, 0, 49),
    ("Clarinet", 3, 0, 2, 5, 54),
    ("Bassoon", 3, 0, 3, 0, 49),
    ("Bassoon", 3, 1, 2, 2, 67),
    ("Horn", 3, 0, 4, 0, 49),
    ("Trumpet", 3, 0, 5, 2, 51),
]

out = []
for fam, page, system, staff, cell, bar in TARGETS:
    ck = cell_key(page, system, staff, cell)
    sk = staff_key(page, system, staff)
    cell_box = by_subj_q.get((ck, "cell_box"))
    staff_lines = by_subj_q.get((sk, "staff_lines"))
    staff_spacing = by_subj_q.get((sk, "staff_spacing"))
    cell_space = by_subj_q.get((ck, "cell_staff_space"))
    glyphs = []
    for (subj, q), rows in by_subj_q.items():
        if q != "glyph_box":
            continue
        if not subj.startswith(f"glyph/{page}/{system}/{staff}/{cell}/"):
            continue
        row = rows[-1]
        nh_is_not = vby_subj_q.get((subj, "notehead_is_not_a_notehead"))
        v = nh_is_not[-1] if nh_is_not else None
        glyphs.append(dict(
            subject=subj, cls=row["value"][0],
            box_page=row["detail"].get("bbox_page_px"),
            box_canon=row["value"][1:],
            refused=(v.get("value") if v else None),
            reason=(v.get("reason") if v else None),
        ))
    out.append(dict(
        family=fam, page=page, system=system, staff=staff, cell=cell, bar=bar,
        cell_box_page=(cell_box[-1]["value"] if cell_box else None),
        staff_lines=(staff_lines[-1]["value"] if staff_lines else None),
        staff_spacing=(staff_spacing[-1]["value"] if staff_spacing else None),
        glyphs=glyphs,
    ))

json.dump(out, open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/candidates_extracted.json", "w"), indent=1)
for o in out:
    print(o["family"], o["bar"], o["staff"], o["cell"], "n_glyphs=", len(o["glyphs"]), "cell_box=", o["cell_box_page"])
    for g in o["glyphs"]:
        print("   ", g["subject"], g["cls"], g["refused"], g["reason"])
