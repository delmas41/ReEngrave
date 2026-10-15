"""Readable view of table2.py (round 2) for Sean. DERIVED from the table. '(rare)' = kept but a low prior (Sean's 'not standard / exceptions')."""
import table2 as T
from cellview import SHAPES
PLACES = [("in the staff, mid-bar", dict(loc="IN", zone="BODY", edge=False, left_edge=False)),
          ("just outside the staff (ledger range)", dict(loc="NEAR", zone="BODY", edge=False, left_edge=False)),
          ("far from any staff", dict(loc="FAR", zone="BODY", edge=False, left_edge=False)),
          ("in the clef/key slots", dict(loc="IN", zone="KEYSLOT", edge=False, left_edge=False)),
          ("at the head of a bar", dict(loc="IN", zone="BARHEAD", edge=False, left_edge=False)),
          ("on a barline", dict(loc="IN", zone="BODY", edge=True, left_edge=False)),
          ("at the far right of a system", dict(loc="IN", zone="BARTAIL", edge=True, left_edge=False)),
          ("in the left margin / at the system's left edge", dict(loc="IN", zone="MARGIN", edge=False, left_edge=True))]
W = {k: v["words"] for k, v in T.SYMBOLS.items()}
if __name__ == "__main__":
    for sn, sd in SHAPES:
        print("### A %s\n" % sn)
        for pn, pd in PLACES:
            c, _ = T.candidates({**sd, **pd})
            names = sorted(W[s] + (" (rare)" if s in c["rare"] else "") for s in c["all"])
            print("- %s: %s" % (pn, "; ".join(names) if names else "**nothing** (a piece of something, or unread)"))
        print()
