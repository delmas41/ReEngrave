"""ROADMAP 2.304 step 0: the counts, from `owned_probe.py` outputs.

    python3 benchmarks/text-reader-owned-ink-2026-11/step0_table.py PROBE.json [PROBE.json ...]

Per text candidate: status = READ (a reading the lexicon accepted), REFUSED (the OCR said something, the lexicon accepted none), NO_READING (no rung spoke).
A candidate "carries" an owner's ink when that owner's ink inside the crop window is at least MIN_SP2 staff-space squares. `own` = inside the candidate's own box
(`crop_for` never whites it), `pad` = in the crop's padding (detector boxes are already whited there; a barline or a staff line is not, except by the 2.254 r3 retry).
EARLIER owners = the page-wide marks claimed before words (CLAUDE.md 3, claim order): barline, staff line, bracket/brace/key/meter ('structural'), clef. The
detector's notehead / accidental / stem / rest / ornament / dynamic boxes are PER-CELL readers (claim AFTER words); listed for information only.
"""
import json
import sys
from collections import Counter, defaultdict

MIN_SP2 = 0.1
EARLIER = ("barline", "staff_line", "det:structural", "det:clef")


def earlier(k):
    return any(k.startswith(e) for e in EARLIER)


def shown(k):
    """still shown to the reader today: a detector's ink in the padding is already whited by `crop_for`."""
    return not (k.startswith("det:") and k.endswith("_pad"))


def overlap(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    return w / max(1.0, min(a[2] - a[0], b[2] - b[0]))


c = Counter()
rows = []
for path in sys.argv[1:]:
    for page in json.load(open(path)):
        acc = defaultdict(list)
        for r in page["readings"]:
            acc[r["candidate"]].append(r)
        for cd in page["candidates"]:
            rs = acc.get(cd["i"], [])
            status = "READ" if any(r["accepted"] for r in rs) else ("REFUSED" if rs else "NO_READING")
            sp2 = cd["sp"] ** 2
            kinds = sorted(k for k, v in (cd.get("owned") or {}).items() if v >= MIN_SP2 * sp2)
            rows.append((page["page"], cd, status, kinds, rs))
            c[("ALL candidates", status)] += 1
            for k in kinds:
                c[(("EARLIER  " if earlier(k) else "later    ") + k, status)] += 1
            if any(earlier(k) and shown(k) for k in kinds):
                c[("ANY EARLIER owner's ink still shown", status)] += 1
            if any(earlier(k) and shown(k) and not k.startswith("staff_line") for k in kinds):
                c[("  ... excluding staff lines", status)] += 1
            if cd.get("through_line"):
                c[("(2.254 r3 retry sees a line come into the box)", status)] += 1
keys = sorted({k for k, _ in c}, key=lambda k: (not k[0].startswith(("ALL", "ANY", "  ...", "(")), k[0]))
print("%-52s %6s %8s %11s" % ("owner kind (own = inside the box, pad = crop padding)", "READ", "REFUSED", "NO_READING"))
for k in keys:
    print("%-52s %6d %8d %11d" % (k, c[(k, "READ")], c[(k, "REFUSED")], c[(k, "NO_READING")]))
print()
# a refused window is a KNOWN word (proxy, not truth) when a READ word stands on another staff of the page at the same x-extent (>= 0.7 of the narrower width)
readw = [(pg, cd) for pg, cd, st, ks, rs in rows if st == "READ"]
known = Counter()
print("REFUSED windows (>= 3 spaces wide) with a READ word at the same x on another staff: a word printed there that we failed on (proxy, not judged):")
for page, cd, status, kinds, rs in rows:
    if status != "REFUSED" or cd["box"][2] - cd["box"][0] < 3 * cd["sp"]:
        continue
    sib = [o for pg, o in readw if pg == page and o["staff"] != cd["staff"] and overlap(cd["box"], o["box"]) >= 0.7]
    if not sib:
        continue
    rem = sorted(k for k in kinds if earlier(k) and shown(k))
    known["windows"] += 1
    known["carrying earlier ink"] += bool(rem)
    known["carrying earlier ink, not staff lines"] += any(not k.startswith("staff_line") for k in rem)
    for k in rem:
        known[k] += 1
    print("  p%s staff %s m%s box %s earlier=%s | read %s | READ on staff %s" % (
        page, cd["staff"], cd["measure"], [int(v) for v in cd["box"]], rem, sorted({r["text"] for r in rs})[:3], sorted({o["staff"] for o in sib})[:3]))
print(dict(known))
