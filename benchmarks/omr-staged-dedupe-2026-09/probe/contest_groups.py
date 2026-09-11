"""Is "keep the copy whose OWN staff is the owner" safe — i.e. does every contest keep one?

⚠️ THE STRUCTURAL CLAIM THIS TESTS. `adjudicate_glyph_owner`'s domain is
`subjects_from=Q.GLYPH_BAND_DISTANCE`, and `gather_contested_glyphs` emits a
band-distance row only for a glyph that OVERLAPS A SAME-CLASS GLYPH ON ANOTHER
STAFF. So a contested glyph always has a twin, and the owner staff always holds
one of the contest's own copies. Relocating a contested glyph can therefore only
ever ADD a second copy to a staff that already has one — unlike `arc_owner`,
whose domain is every `Q.ARC_BOX` and which CLAUDE.md records rescuing six arcs
that cover nothing on their own staff.

The rule that follows needs no new data: keep a contested copy iff its owner is
its OWN staff. The one way it can lose ink is a SWAP — every member of a
contest naming somebody else — so this probe counts those directly rather than
assuming they cannot happen.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from reach import addr, duplicate_pairs  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    args = ap.parse_args(argv)

    d = json.load(open(args.record))
    obs = d["record"]["observations"]

    owner = {}
    for v in d["record"]["verdicts"]:
        if v["quantity"] == "glyph_owner":
            owner[v["subject"]] = v

    print(f"glyph_owner verdicts: {len(owner)}")
    by_reason = collections.Counter(v["reason"] for v in owner.values())
    for k, n in by_reason.most_common():
        print(f"  {k:<14} {n}")

    def own_staff(sub):
        p = sub.split("/")
        return f"staff/{p[1]}/{p[2]}/{p[3]}"

    moved = [s for s, v in owner.items()
             if isinstance(v.get("value"), str) and v["value"] != own_staff(s)]
    stayed = [s for s, v in owner.items()
              if isinstance(v.get("value"), str) and v["value"] == own_staff(s)]
    print(f"\nowner names ANOTHER staff (today: RELOCATED) : {len(moved)}")
    print(f"owner names its OWN staff                    : {len(stayed)}")

    # ⚠️ THE CLAIM: a relocated glyph always has a twin. Checked, not assumed.
    no_contest = [s for s in moved if owner[s]["reason"] == "no_contest"]
    print(f"  of the relocated, reason == no_contest      : {len(no_contest)}"
          "   (must be 0 — a no_contest glyph names its own staff)")

    # Contest GROUPS: transitive closure over overlapping same-family pairs
    # that cross a staff, built the same way `gather_contested_glyphs` builds
    # them so the two cannot drift in kind.
    _subjects, family, pairs = duplicate_pairs(obs)
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    cross = [p for p in pairs if p["scope"] == "same_system_other_staff"]
    for p in cross:
        union(p["a"], p["b"])
    groups = collections.defaultdict(set)
    for s in list(parent):
        groups[find(s)].add(s)

    print(f"\ncross-staff contest GROUPS: {len(groups)}"
          f"  over {sum(len(g) for g in groups.values())} subjects")

    kept_hist = collections.Counter()
    lost = []
    for root, members in groups.items():
        kept = [s for s in members
                if s in owner and isinstance(owner[s].get("value"), str)
                and owner[s]["value"] == own_staff(s)]
        undecided = [s for s in members if s not in owner]
        kept_hist[len(kept)] += 1
        if not kept and not undecided:
            lost.append(sorted(members))

    print("\nunder 'keep iff owner == own staff', members kept per group:")
    for k in sorted(kept_hist):
        print(f"  {k} kept : {kept_hist[k]} groups")
    print(f"\n⚠️ GROUPS THAT WOULD KEEP NOTHING (a SWAP — ink lost): "
          f"{len(lost)}")
    for g in lost[:10]:
        for s in g:
            print(f"    {s}  owner={owner[s]['value'] if s in owner else '-'} "
                  f"own={own_staff(s)}  family={family.get(s)}")
        print()

    # Groups keeping MORE than one: two copies on the owner staff, which is
    # the SAME-CELL population and a different cause.
    multi = sum(n for k, n in kept_hist.items() if k > 1)
    print(f"groups that would still keep >1 copy: {multi}"
          "   (same-cell duplicates — a different cause, see FINDINGS §3)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
