"""Manager's follow-up: across Litolff p3, how many same-side, same-stem
chord pairs does EVALUATE write a pitch SECOND apart (which Sean's
convention says is impossible -- so each is a duplicate box or a
mis-rounded third)? Classify by ink (one head's worth vs two) and report;
no fix built, per instruction."""
import json
from collections import defaultdict
from tools.omr.staged import record_io

REC = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a212d008990c6b49a/out/2.40/litolff-p3-evaluate.json"
d = record_io.load_record(REC)
rec = d["record"]
obs = rec["observations"]
verdicts = rec["verdicts"]

box_by_subj = {}
for o in obs:
    if o["quantity"] == "glyph_box":
        box_by_subj[o["subject"]] = o
stem_by_cell = defaultdict(list)
for o in obs:
    if o["quantity"] == "stem":
        cell = "/".join(["cell"] + o["subject"].split("/")[1:5])
        stem_by_cell[cell].append(o)

pitch_by_subj = {}
for v in verdicts:
    if v["quantity"] == "pitch" and v.get("value"):
        pitch_by_subj[v["subject"]] = v

nh_verdict = {}
for v in verdicts:
    if v["quantity"] == "notehead_is_not_a_notehead":
        nh_verdict[v["subject"]] = v

STEP_OF = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}


def diatonic_step(pitch_name):
    # pitch value like "C#5" or "C5" -- step letter + octave at the tail
    if not pitch_name:
        return None
    letter = pitch_name[0]
    octv = pitch_name[-1]
    try:
        octv = int(octv)
    except ValueError:
        return None
    if letter not in STEP_OF:
        return None
    return STEP_OF[letter] + 7 * octv


def boxes_overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax <= bx + bw and ax + aw >= bx and ay <= by + bh and ay + ah >= by)


cells = defaultdict(list)
for subj, o in box_by_subj.items():
    if not str(o["value"][0]).lower().startswith("notehead"):
        continue
    cell = "/".join(["cell"] + subj.split("/")[1:5])
    cells[cell].append((subj, o))

results = []
for cell, glyphs in cells.items():
    stems = [(s["subject"], (s["value"][0], s["value"][1], s["value"][2], s["value"][3]))
            for s in stem_by_cell.get(cell, [])]
    for i in range(len(glyphs)):
        for j in range(i + 1, len(glyphs)):
            sa, oa = glyphs[i]
            sb, ob = glyphs[j]
            if oa["value"][0] != ob["value"][0]:
                continue  # same-class only, matching 2.30/2.40's own domain
            boxa = (oa["value"][1], oa["value"][2], oa["value"][3], oa["value"][4])
            boxb = (ob["value"][1], ob["value"][2], ob["value"][3], ob["value"][4])
            # must share a stem
            shared_stem = None
            for stem_subj, sbox in stems:
                if boxes_overlap(sbox, boxa) and boxes_overlap(sbox, boxb):
                    shared_stem = (stem_subj, sbox)
                    break
            if shared_stem is None:
                continue
            scx = shared_stem[1][0] + shared_stem[1][2] / 2.0
            acx = boxa[0] + boxa[2] / 2.0
            bcx = boxb[0] + boxb[2] / 2.0
            same_side = (acx >= scx) == (bcx >= scx)
            if not same_side:
                continue
            pa = pitch_by_subj.get(sa)
            pb = pitch_by_subj.get(sb)
            if not pa or not pb:
                continue
            da = diatonic_step(pa["value"])
            db = diatonic_step(pb["value"])
            if da is None or db is None:
                continue
            if abs(da - db) != 1:
                continue  # exactly a written SECOND apart
            va = nh_verdict.get(sa)
            vb = nh_verdict.get(sb)
            refused_a = va.get("value") if va else None
            refused_b = vb.get("value") if vb else None
            results.append(dict(cell=cell, a=sa, b=sb,
                                pitch_a=pa["value"], pitch_b=pb["value"],
                                refused_a=refused_a, refused_b=refused_b,
                                reason_a=(va or {}).get("reason"),
                                reason_b=(vb or {}).get("reason"),
                                box_a=boxa, box_b=boxb, stem=shared_stem[0]))

print("same-side same-stem written-SECOND pairs on p3:", len(results))
for r in results:
    print(r["cell"], r["a"], r["pitch_a"], r["refused_a"], r["reason_a"],
         "|", r["b"], r["pitch_b"], r["refused_b"], r["reason_b"])

json.dump(results, open(
    "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/same_side_second_survey.json",
    "w"), indent=1, default=str)
