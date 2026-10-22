"""SEAN'S RULE, which is narrower than the one probe_forced_by_clef measured.

Verbatim: "If we had 4 or 5 staves that showed up last in the system without a
name in the margin they are almost surely strings. If the first 2 clefs are
treble the 3rd is alto and the 4th is bass clef it is further reinforcement."

⚠️⚠️ THIS IS A CLAIM ABOUT THE SUFFIX OF A SYSTEM, NOT A FIT OVER THE WHOLE OF
IT, AND THE DIFFERENCE IS WHY MY EARLIER "ORDER ALONE FORCES ZERO" DID NOT
PRICE IT. That arm enumerated monotone assignments of EVERY staff into the
12-slot reference and asked what was forced; on `p3/s1` the system above the
block also suppresses Trombe and Timpani, so the whole-system fit has 35
candidates and forces almost nothing. Sean's rule never looks above the block.
It identifies NOTHING above the strings, so what happens up there cannot
weaken it.

THE RULE, in three parts, measured apart because they can fail apart:
  A  FAMILY   -- a bottom-contiguous unnamed block of 4-5 staves is the string
                 section. This names a FAMILY and cannot graft an instrument.
  B  SLOT     -- within that block, position names the part: the block maps
                 onto the reference's string slots in order. NO CLEF IS READ,
                 which is the whole point: a wrong clef cannot move it.
  C  CLEF     -- the glyph sequence treble/treble/alto/bass CORROBORATES. It
                 is a TERM, never a gate (`adjudicate_instrument` is already
                 `Mode.ADDITIVE`), so it may raise support and may not veto.

⚠️ A 4-BLOCK AND A 5-BLOCK ARE NOT THE SAME LINEUP. Five printed string staves
become four by CONDENSATION (`Violoncello e Basso`), so the last member of a
4-block covers TWO reference slots and the rule ABSTAINS on which rather than
picking one. Scored with the 2026-09-15 membership test, not a new one.

⚠️ THE CLEF ROWS READ HERE ARE `Q.CLEF_GLYPH`, THE GATHER OBSERVATION, never
the `Q.CLEF` VERDICT. The verdict is ORDER 9 and `adjudicate_instrument` is 5,
so reading it would read None and close a cycle -- `adjudicate_clef` weights
the instrument at 1.0 in the other direction. `inventory --check` says exactly
that, and says nothing about the raw rows, which are observed at gather time.
"""
import collections
import json
import sys

import table
from probe_forced_by_clef import classify

# The detector's clef class -> the clef it names. Derived from the glyph name
# itself, not from a table of instruments, so this is a reading and not a
# prior.
#
# ⚠️ THE FIRST DRAFT OF THIS MAP USED SMuFL SPELLINGS (`gClef`, `fClef`,
# `cClef`) AND MATCHED NOTHING, so the probe reported "0 of 0 spoke" on a
# document holding 91 glyph rows -- a clef corroboration that was silent
# because of the map, not because of the page. It read exactly like a page
# that prints no clef. Corrected against the record's own values.
#
# ⚠️⚠️ AND THE CORRECTION EXPOSED THE REAL FINDING: the record holds 74
# `clefG` and 17 `clefF` and ZERO C CLEFS. The ALTO clef -- the one clef that
# uniquely names the Viola, and the only member of the string block a clef
# could identify on its own -- IS NEVER DETECTED on this document. So the
# corroboration term can confirm the violins and the bass and can never
# confirm the viola.
GLYPH_CLEF = {"clefG": "treble", "clefF": "bass", "clefC": "alto"}

MIN_BLOCK, MAX_BLOCK = 4, 5

# The reference's string slots, in printed order. Taken from the document's
# own widest system rather than asserted: the strings are the slots at and
# below the first one whose printed name is a string.
STRING_WORDS = ("Violino", "Viola", "Violoncello", "Basso", "Contrabass")


def string_slots(ref_names):
    return [i for i, n in enumerate(ref_names)
            if any(w in n for w in STRING_WORDS)]


def clef_seq(staff, glyphs):
    """This staff's clef from its RAW glyph rows, or None."""
    rows = glyphs.get(staff.subject) or []
    vals = {GLYPH_CLEF.get(str(v)) for v in rows}
    vals.discard(None)
    return vals.pop() if len(vals) == 1 else None


def main() -> int:
    staves, printed_lineups, raw = table.load()
    ref_names = table.reference_lineup()
    slots = string_slots(ref_names)

    glyphs = collections.defaultdict(list)
    for o in raw["observations"]:
        if o.get("quantity") == "clef_glyph":
            glyphs[o["subject"]].append(o.get("value"))

    print("=" * 74)
    print("SETUP")
    print("=" * 74)
    print("   reference string slots: %s" % [(i, ref_names[i]) for i in slots])
    print("   staves carrying a raw clef_glyph row: %d of %d"
          % (sum(1 for s in staves if s.subject in glyphs), len(staves)))

    unnamed = [s for s in staves if not s.named]
    tallyA = collections.Counter()
    tallyB = collections.Counter()
    tallyC = collections.Counter()
    rows = []

    print()
    print("=" * 74)
    print("PER SYSTEM")
    print("=" * 74)
    for key in sorted(printed_lineups):
        grp = sorted([s for s in staves if s.sys_key == key],
                     key=lambda s: s.ordinal)
        block = [s for s in grp if not s.named]
        if not block:
            continue
        # (A) is the block a bottom-contiguous suffix of the right size?
        suffix = grp[len(grp) - len(block):]
        contiguous = [s.subject for s in suffix] == [s.subject for s in block]
        in_range = MIN_BLOCK <= len(block) <= MAX_BLOCK
        fires = contiguous and in_range
        print()
        print("--- p%d/s%d  block of %d, contiguous=%s, 4<=n<=5 %s -> %s"
              % (key[0], key[1], len(block), contiguous, in_range,
                 "FIRES" if fires else "DOES NOT FIRE"))
        if not fires:
            for s in block:
                tallyA["not_fired"] += 1
                rows.append((s, None, "not_fired", None))
            continue

        # (B) position within the block names the slot; a SHORT block's last
        #     member covers the condensed pair and is abstained on.
        n_slot = len(slots)
        for i, s in enumerate(block):
            cl = clef_seq(s, glyphs)
            # family claim
            truth_is_string = any(w in (s.printed or "") for w in STRING_WORDS)
            tallyA["ok" if truth_is_string else "WRONG"] += 1

            if len(block) == n_slot:
                slot = slots[i]
                cls = classify(s.printed, ref_names[slot])
                tallyB[cls] += 1
                rows.append((s, slot, cls, cl))
                print("    B slot %2d %-14s printed=%-20s clef=%-7s [%s]"
                      % (slot, ref_names[slot], s.printed, cl, cls))
            elif len(block) == n_slot - 1 and i < len(block) - 1:
                slot = slots[i]
                cls = classify(s.printed, ref_names[slot])
                tallyB[cls] += 1
                rows.append((s, slot, cls, cl))
                print("    B slot %2d %-14s printed=%-20s clef=%-7s [%s]"
                      % (slot, ref_names[slot], s.printed, cl, cls))
            else:
                tallyB["abstain_condensed"] += 1
                rows.append((s, None, "abstain_condensed", cl))
                print("    B ABSTAIN (condensed pair) printed=%-20s clef=%s"
                      % (s.printed, cl))

        # (C) does the clef sequence corroborate?
        seq = [clef_seq(s, glyphs) for s in block]
        expect = [ref_names[i] for i in slots]
        want = [table.PRINTED_CLEF.get(n, ("?",))[0] for n in expect]
        if len(block) == n_slot - 1:
            want = want[:len(block) - 1] + ["bass"]
        agree = sum(1 for a, b in zip(seq, want) if a == b)
        spoke = sum(1 for a in seq if a is not None)
        tallyC["agree"] += agree
        tallyC["spoke"] += spoke
        tallyC["silent"] += len(block) - spoke
        print("    C clefs read %s vs expected %s -> %d/%d agree, %d silent"
              % (seq, want, agree, spoke, len(block) - spoke))

    print()
    print("=" * 74)
    print("RESULT")
    print("=" * 74)
    print("A  FAMILY (block of 4-5 at the bottom is the string section)")
    print("     correct %d   WRONG %d   rule did not fire %d"
          % (tallyA["ok"], tallyA["WRONG"], tallyA["not_fired"]))
    print()
    print("B  SLOT by position within the block, NO CLEF READ")
    print("     correct              %d" % tallyB["ok"])
    print("     condensation         %d" % tallyB["condensation"])
    print("     ** GRAFTS **         %d" % tallyB["graft"])
    print("     abstained (condensed pair) %d" % tallyB["abstain_condensed"])
    print()
    print("C  CLEF as CORROBORATION (a term, never a gate)")
    print("     agreed with the expected sequence %d of %d that spoke"
          % (tallyC["agree"], tallyC["spoke"]))
    print("     silent (no raw clef glyph)        %d" % tallyC["silent"])

    out = table.HERE / "out" / "suffix-rule.json"
    out.write_text(json.dumps(
        {"A": dict(tallyA), "B": dict(tallyB), "C": dict(tallyC),
         "rows": [{"subject": s.subject, "printed": s.printed, "slot": sl,
                   "class": c, "clef_glyph": cl} for s, sl, c, cl in rows]},
        indent=1))
    print()
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
