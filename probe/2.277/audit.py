"""2.277 record-level audit + the before/after picture, from a dump.py table.

usage: audit.py DUMP.json [--list N]
 * survivors  : boxes NOT refused though >= CUT of their own ink is held by a claim that is not consulted elsewhere and not MARK_ONLY
                (`claim_final.survivors`; the derived check's record half).  Must be 0 with the flag ON; the census cases with it OFF.
 * picture    : heads by BOX count (the old figure) and by DISTINCT INK (copies by position = one mark, boxes held by a claim left out), per
                refusal bucket.  Needs the `cf` block (a dump made with OMR_CLAIM_FINAL=1); without it marks are unknown and the distinct count = box count.
"""
import collections
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from tools.omr.staged import claim_final as CF        # noqa: E402
from tools.omr.staged import stroke_owner as SO       # noqa: E402

D = json.load(open(sys.argv[1]))
n_list = int(sys.argv[sys.argv.index("--list") + 1]) if "--list" in sys.argv else 0
rows, cfs = D["rows"], D.get("cf") or {}
FAM = lambda r: SO.family_of(r["cls"], r.get("cat"))


def cell_of(sub):
    return "cell/" + sub.split("/", 1)[1].rsplit("/", 1)[0]


def refused(r):
    return any(v[0] is True for v in r["fate"].values())


def reason(r):
    for v in r["fate"].values():
        return v[1] if v[0] is True else ("kept" if v[0] is False else "abstained:%s" % v[1])
    return "no_verdict"


claims = sorted({"barline", "bracket", "leading_column", "clef", "key_signature", "meter", "word", "arc_trace", "hairpin_trace"})
boxes = []
for r in rows:
    f = FAM(r)
    if f is None or f in SO.CONSUMERS:
        continue
    st = [(o, sh, ink, (own[0] if own else "unclaimed"), (own[1] if own else None)) for o, sh, cov, ink, kind, own in r["strokes"] if ink]
    boxes.append((r["sub"], f, st, refused(r)))
sv = CF.survivors(boxes, claims)
print("plate", D["plate"], "flags", D["flags"], "boxes", len(boxes))
print("SURVIVORS (kept boxes >= %.2f held by a barline / page claim): %d" % (CF.CUT, len(sv)), dict(collections.Counter((s["family"], s["by"]) for s in sv)))
for s in sv[:n_list]:
    print("  ", s)
# the picture, heads
heads = [r for r in rows if FAM(r) == "head"]
marks = {}
for c in cfs.values():
    marks.update(c.get("marks") or {})
held = {}
for c in cfs.values():
    held.update(c.get("held") or {})
by_reason = collections.Counter(reason(r) for r in heads)
print("heads by BOX count:", len(heads), " refused:", sum(refused(r) for r in heads), " kept:", sum(1 for r in heads if reason(r) == "kept"))
cl = [r for r in heads if reason(r).startswith("claimed_by:") or (held.get(r["sub"], {}).get("share", 0) >= CF.CUT and held[r["sub"]]["by"] not in CF.MARK_ONLY)]
unclaimed = [r for r in heads if r not in cl]
distinct = {marks.get(r["sub"], r["sub"]) for r in unclaimed}
print("heads on claimed ink (barline, page claims, clef, key, word ...):", len(cl))
print("heads detected = distinct UNCLAIMED head ink:", len(distinct), "(boxes %d, copies by position collapsed %d)" % (len(unclaimed), len(unclaimed) - len(distinct)))
kept = {marks.get(r["sub"], r["sub"]) for r in unclaimed if reason(r) == "kept"}
print("  of which kept by the precision rules (distinct):", len(kept), " not kept (distinct ink with no kept box):", len(distinct - kept))
nm = collections.Counter(reason(r) for r in unclaimed if marks.get(r["sub"], r["sub"]) not in kept)
print("  not-kept distinct ink by first reason (box-level):", dict(nm.most_common(12)))
print("marks (copies by position) with >1 KEPT box:", len([m for m, c in collections.Counter(marks[r["sub"]] for r in heads if r["sub"] in marks and reason(r) == "kept").items() if c > 1]))
