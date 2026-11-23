"""2.306 r14 tile follow-up (Sean's tiles 2 and 8): count, per page, notes whose duration reads a flag (a) from a flag box standing wholly LEFT of the
note's own page stem (a down-stem flag hangs right of its stem; a box left of it is the note before's flag), and (b) a flag class naming more hooks
than the stem tip's own hook count (`Q.STEM_TIP_INK` hooks). Page px throughout. Usage: r14_flag_cases.py REC.json"""
import collections
import json
import sys

from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1])["record"]
obs_by_id = {o["id"]: o for o in rec["observations"]}
gbox = {o["subject"]: (o.get("detail") or {}).get("bbox_page_px") for o in rec["observations"] if o["quantity"] == "glyph_box"}
pstem = {o["subject"]: (o.get("detail") or {}) for o in rec["observations"] if o["quantity"] == "page_stem"}
tip_hooks = {}
for o in rec["observations"]:
    if o["quantity"] == "stem_tip_ink":
        d = o.get("detail") or {}
        if d.get("hooks") is not None:
            tip_hooks[d.get("stem_row_id")] = d.get("hooks")
c = collections.Counter()
ex = collections.defaultdict(list)
for v in rec["verdicts"]:
    if v["quantity"] != "duration":
        continue
    d = v.get("detail") or {}
    if not d.get("flags_attached"):
        continue
    used = [obs_by_id.get(u) for u in (v.get("used") or []) if isinstance(u, str)]
    flags = [o for o in used if o and o["quantity"] == "flag"]
    ps = pstem.get(v["subject"])
    if ps and ps.get("stem_box"):
        sx = (ps["stem_box"][0] + ps["stem_box"][2]) / 2.0
        for f in flags:
            fb = gbox.get(f["subject"])
            if fb and fb[2] <= sx:
                c["a: flag box wholly left of its own page stem"] += 1
                ex["a"].append((v["subject"], f["subject"]))
    stems = [o for o in used if o and o["quantity"] == "stem"]
    hooks = [tip_hooks[s["id"]] for s in stems if s["id"] in tip_hooks]
    if d.get("flag_levels", 0) >= 2:
        c["flag_levels>=2"] += 1
        if hooks and max(hooks) < d["flag_levels"]:
            c["b: class names more hooks than the tip shows"] += 1
            ex["b"].append((v["subject"], hooks, d["flag_levels"]))
        elif not hooks:
            c["b?: two-level flag, tip hooks not read"] += 1
            ex["b?"].append(v["subject"])
print(dict(c))
for k, v in ex.items():
    print(k, v[:12])
