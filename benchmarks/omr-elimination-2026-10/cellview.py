"""Readable view of table.py for Sean: representative shapes x places -> what survives. DERIVED from the table."""
import table as T
SHAPES = [("small round dot", dict(w=0.45, h=0.45, fill=0.6)),
          ("filled oval", dict(w=1.35, h=1.0, fill=0.8)),
          ("hollow oval", dict(w=1.4, h=1.0, fill=0.4)),
          ("flat filled block", dict(w=1.3, h=0.55, fill=0.9)),
          ("short flat stroke", dict(w=1.6, h=0.3, fill=0.6)),
          ("thin tall stroke", dict(w=0.2, h=3.5, fill=0.6)),
          ("long thin curve or wedge", dict(w=4.0, h=1.0, fill=0.12)),
          ("tall glyph, accidental-sized", dict(w=1.0, h=2.7, fill=0.4)),
          ("big tall glyph, clef-sized", dict(w=2.8, h=7.0, fill=0.4))]
PLACES = [("in the staff, mid-bar", dict(loc="IN", zone="BODY", edge=False)),
          ("just outside the staff (ledger range)", dict(loc="NEAR", zone="BODY", edge=False)),
          ("far from any staff", dict(loc="FAR", zone="BODY", edge=False)),
          ("in the clef/key slots", dict(loc="IN", zone="KEYSLOT", edge=False)),
          ("at the head of a bar", dict(loc="IN", zone="BARHEAD", edge=False)),
          ("on a barline", dict(loc="IN", zone="BODY", edge=True)),
          ("in the left margin", dict(loc="NEAR", zone="MARGIN", edge=False))]
W = {k: v["words"] for k, v in T.SYMBOLS.items()}
if __name__ == "__main__":
    for sn, sd in SHAPES:
        print("### A %s\n" % sn)
        for pn, pd in PLACES:
            c, _ = T.candidates({**sd, **pd})
            names = sorted(W[s] for s in c["all"])
            print("- %s: %s" % (pn, "; ".join(names) if names else "**nothing** (today the table would say unread)"))
        print()
