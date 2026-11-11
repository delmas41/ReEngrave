"""2.280 r3: the chain stem -> beam/flag -> written value, counted by distinct ink (twins folded), from heads.py rows.
usage: chain.py HEADS.jsonl [--list OUT.json]

READ heads = KEPT (decided 'notehead'), minus COPIES (owned_by_another_staff / mark_group_duplicate) and whole-rest ink.
Every READ head falls in exactly one line of the first block (outcome), in this order:
  not written, for a VALUE reason (duration_narrowed / duration_abstained / chord_value_undecided)
  inside a red bar (written, drawn red; counted on its own line, Sean 2026-11-10)
  not written, other reason (no_pitch, ink_not_head_shaped, bar held out, ...)
  written BLUE for pitch (INFER fill_part_key / fill_clef_gap)
  written BLUE for value (guess quantity duration: EVALUATE bar_* / reconcile_duration / INFER collapse_*)
  written PLAIN
Then the VALUE-uncertain heads (not written for value + blue for value, red-bar heads that are value-uncertain too) are split by the first
point the chain failed:
  (i)   no stem row                          head_stem abstained no_stem / stems_attached 0
  (ii)  stem row, no beam or flag read       stems_attached > 0, beams_by_stem 0, no certain/possible level, no flag, tip reader sees no beam
  (iii) beam or flag read, not bound         some level / beam / flag / tip_beamed read at the stem, the verdict still narrowed
  (iv)  value known, refused downstream      duration decided (or one candidate) but chord / bar refused or disputed it
  (v)   other                                head fill, class, dot, whole-class, ...
"""
import collections
import json
import sys

rows = [json.loads(l) for l in open(sys.argv[1])]
if "--pages" in sys.argv:
    _pg = {int(p) for p in sys.argv[sys.argv.index("--pages") + 1].split(",")}
    rows = [r for r in rows if r["page"] in _pg]
COPY = ("owned_by_another_staff", "mark_group_duplicate")
VALUE_FATES = ("duration_narrowed", "duration_abstained", "chord_value_undecided")


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


def is_wr(r):
    w = r["whole_rest"]
    return r["fate"] == "ink_is_a_whole_rest" or (w and w[0] == "decided" and w[2] == "True")


real = fold([r for r in rows if r["kept"] and r["fate"] not in COPY and not is_wr(r)])


def outcome(r):
    f = r["fate"]
    if f in VALUE_FATES:
        return "not written: value (%s)" % f
    if f in ("written", "written_relocated") and r.get("red"):
        return "written inside a red bar"
    if f not in ("written", "written_relocated"):
        return "not written: other (%s)" % f.split(":")[0]
    g = r.get("guess")
    if g:
        return "written BLUE for value" if g[2] == "duration" else "written BLUE for pitch/other (%s)" % g[1]
    return "written PLAIN"


def value_uncertain(r):
    if r["fate"] in VALUE_FATES:
        return True
    g = r.get("guess")
    if r["fate"] in ("written", "written_relocated") and g and g[2] == "duration":
        return True
    dv = r["duration"]
    return bool(dv and dv[0] in ("narrowed", "abstained") and r["fate"] in ("written", "written_relocated"))


def klass(r):
    d = r["d"] or {}
    dv = r["duration"] or [None, None]
    bfs = r["bfs"] or {}
    tip = (bfs.get("tip") or {}) if isinstance(bfs, dict) else {}
    if r["n_stem"] == 0 or (r["head_stem"] and r["head_stem"][1] == "no_stem"):
        return "(i) no stem row"
    read = ((d.get("beams_by_stem") or 0) > 0 or (d.get("levels_certain") or 0) > 0 or (d.get("levels_possible") or 0) > 0
            or (d.get("flags_attached") or 0) > 0 or tip.get("stem_beamed") or (bfs.get("tip_levels") or 0) > 0)
    if dv[0] == "decided" or len({tuple(c) for c in r["cands"]}) == 1:
        return "(iv) value known, refused downstream (chord / bar)"
    if dv[1] in ("beams_ambiguous", "beam_discounted_uncertain", "beam_certain_not_joined", "flags_disagree", "flag_ink_unread", "tip_readers_disagree"):
        return "(iii) beam or flag read, not bound / not certain" if read else "(ii) stem row, no beam or flag read"
    return "(v) other (%s)" % dv[1]


oc = collections.Counter(outcome(r) for r in real)
print("READ heads (kept, no copies, no whole-rest ink, twins folded): %d" % len(real))
for k, v in oc.most_common():
    print("  %5d  %5.1f%%  %s" % (v, 100.0 * v / len(real), k))
vu = [r for r in real if value_uncertain(r)]
print("\nVALUE-uncertain READ heads: %d (%.1f%% of READ heads); by the first point the chain failed:" % (len(vu), 100.0 * len(vu) / len(real)))
kc = collections.Counter(klass(r) for r in vu)
for k, v in sorted(kc.items()):
    print("  %5d  %5.1f%%  %s" % (v, 100.0 * v / max(1, len(vu)), k))
print("  of those, by outcome x class:")
x = collections.Counter((outcome(r).split(" (")[0], klass(r)[:5]) for r in vu)
for k, v in sorted(x.items()):
    print("     %4d  %s | %s" % (v, k[0], k[1]))
print("\nheads written inside a red bar: %d; of them value-uncertain %d, blue for pitch %d" % (
    oc["written inside a red bar"], sum(1 for r in vu if outcome(r) == "written inside a red bar"),
    sum(1 for r in real if outcome(r) == "written inside a red bar" and r.get("guess") and r["guess"][2] != "duration")))
if "--list" in sys.argv:
    out = {}
    for r in vu:
        out.setdefault(klass(r)[:5], []).append(r["sub"])
    json.dump(out, open(sys.argv[sys.argv.index("--list") + 1], "w"))
