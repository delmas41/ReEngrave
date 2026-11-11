"""2.280 r3: counts from heads.py rows. usage: tally.py HEADS.jsonl [PAGES]
Populations (the 2.280 p12 definition): KEPT = NOTEHEAD_IS_NOT_A_NOTEHEAD decided 'notehead'; minus COPIES (fate owned_by_another_staff /
mark_group_duplicate: the stem lives in the other staff's cell) and minus WHOLE-REST INK (whole_rest decided True or fate ink_is_a_whole_rest).
Twins (two kept boxes over one ink, page_box IoU >= 0.5) are folded to one."""
import collections
import json
import sys

rows = [json.loads(l) for l in open(sys.argv[1])]
if len(sys.argv) > 2:
    pg = {int(p) for p in sys.argv[2].split(",")}
    rows = [r for r in rows if r["page"] in pg]
COPY = ("owned_by_another_staff", "mark_group_duplicate")


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u else 0


def fold(rs):
    out = []
    for r in sorted(rs, key=lambda r: -(r["conf"] or 0)):
        if r["page_box"] and any(o["page"] == r["page"] and o["page_box"] and iou(o["page_box"], r["page_box"]) >= 0.5 for o in out):
            continue
        out.append(r)
    return out


kept = [r for r in rows if r["kept"]]
copies = [r for r in kept if r["fate"] in COPY]
wr = [r for r in kept if r["fate"] not in COPY and ((r["whole_rest"] and r["whole_rest"][0] == "decided" and r["whole_rest"][2] == "True")
                                                    or r["fate"] == "ink_is_a_whole_rest")]
real = [r for r in kept if r not in copies and r not in wr]
real_f = fold(real)
nos = [r for r in real_f if r["n_stem"] == 0]
print("rows (notehead-classed boxes) %d | KEPT %d | copies %d | whole-rest ink %d | real candidates %d (after twin fold %d)" % (
    len(rows), len(kept), len(copies), len(wr), len(real), len(real_f)))
print("NO STEM ROW among real candidates: %d (%.1f%%)" % (len(nos), 100.0 * len(nos) / max(1, len(real_f))))
print("  by HEAD_STEM verdict:", collections.Counter((r["head_stem"] or [None, None])[0:2] and tuple((r["head_stem"] or [None, None])[0:2]) for r in nos).most_common(6))
print("  by duration verdict:", collections.Counter(tuple((r["duration"] or [None, None])[0:2]) for r in nos).most_common(8))
print("  by fate:", collections.Counter(r["fate"] for r in nos).most_common(8))
print("ALL real candidates by HEAD_STEM verdict:", collections.Counter(tuple((r["head_stem"] or [None, None])[0:2]) for r in real_f).most_common(8))
print("  by page (real, no_stem):", sorted(collections.Counter(r["page"] for r in nos).items()), "of", sorted(collections.Counter(r["page"] for r in real_f).items()))
