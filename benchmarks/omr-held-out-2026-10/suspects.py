"""2.101 named suspects: where do the held-out marks sit relative to the thresholds that were
set on the two count pages?  python3 suspects.py DOC ARM_REC

2.99: THIN_STROKE_MAX_COLUMN_SHARE 0.45, eighth width 1.1-1.6 / height 1.5-2.5 / step 3.2-4.4,
      quarter width 1.0-1.45 / height 2.65-3.5 / step 3.7-5.3   (adjudicators/unboxed_rest.py)
"""
import sys
from collections import Counter, defaultdict

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

doc, p = sys.argv[1:3]
R = load_record(p)["record"]
last = {}
for v in R["verdicts"]:
    if v["quantity"] == "unboxed_ink_is_a_rest":
        last[v["subject"]] = v
rows = defaultdict(list)
for s, v in last.items():
    d = v.get("detail") or {}
    if d.get("width_spaces") is None:
        continue
    key = ("decided" if str(v["outcome"]) == "decided" else "abstained") + ":" + str(v["reason"])
    rows[key].append(d)
print("==", doc, "unboxed-ink verdicts with a measured shape:", sum(len(x) for x in rows.values()))


def rng(xs):
    xs = sorted(xs)
    return f"{xs[0]:.2f}..{xs[-1]:.2f} (median {xs[len(xs)//2]:.2f})" if xs else "-"


for k, ds in sorted(rows.items(), key=lambda kv: -len(kv[1])):
    if k.endswith("already_read_as_a_glyph"):
        print(f"  {len(ds):4d} {k}")
        continue
    print(f"  {len(ds):4d} {k}\n         width {rng([d['width_spaces'] for d in ds])}  height {rng([d['height_spaces'] for d in ds])}"
          f"  step {rng([d['staff_step'] for d in ds if d.get('staff_step') is not None])}"
          f"  max_col_share {rng([d['max_column_share'] for d in ds if d.get('max_column_share') is not None])}")
dec = [d for k, ds in rows.items() for d in ds if k in ("decided:rest8th_shape", "decided:restQuarter_shape")]
near = 0
for d in dec:
    c = d.get("max_column_share")
    if c is not None and c < 0.55:
        near += 1
print(f"  decided rests whose max_column_share is within 0.10 above the 0.45 cut: {near} of {len(dec)}")
ab = [d for k, ds in rows.items() for d in ds if k == "abstained:shape_cannot_tell"]
thin = [d for d in ab if (d.get("max_column_share") or 1) < 0.45]
rest_sized = [d for d in ab if 1.0 <= d["width_spaces"] <= 1.6 and 1.5 <= d["height_spaces"] <= 3.5]
print(f"  abstained shape_cannot_tell: {len(ab)}; rest-sized (w 1.0-1.6, h 1.5-3.5): {len(rest_sized)}; "
      f"max_col_share < 0.45: {len(thin)}")
