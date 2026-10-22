"""REACH FIRST: what each candidate witness can even SAY about the 25 unnamed.

⚠️ THIS PROBE DELIBERATELY SCORES NO RULE. It asks only, per candidate, "is
this reading present, and is it right", because a witness that is absent or
wrong on the population cannot name a staff however the rule around it is
written -- and measuring reach before accuracy is this repo's own standing
order. The rule itself is scored in probe_forced_by_clef.py.

The truth is the PRINT (`printed-lineups.json`, a human corroborated by the
margin OCR), joined on the subject address (page, system, ordinal), so no
geometry and no page-pixel frame enters.
"""
import collections
import json
import sys

import table

# What Sean read off the print, quoted in CLAUDE.md: "they should all be 3 flats
# (Cm/Eb maj) except Cl. which is 1 flat and the tr and cor which have no key
# signature". Stated per printed name so the key witness can be scored at all.
TRUE_KEY = {
    "Flauti": -3, "Oboi": -3, "Clarinetti": -1, "Fagotti": -3,
    "Corni": 0, "Trombe": 0, "Timpani": 0,
    "Violino I": -3, "Violino II": -3, "Viola": -3,
    "Violoncello": -3, "Basso": -3, "Violoncello e Basso": -3,
}


def main() -> int:
    staves, printed, raw = table.load()
    unnamed = [s for s in staves if not s.named]

    print("=" * 74)
    print("REACH -- the population")
    print("=" * 74)
    print("staff-systems            %d" % len(staves))
    print("named by the margin      %d" % (len(staves) - len(unnamed)))
    print("UNNAMED (the question)   %d" % len(unnamed))
    if not unnamed:
        print("DEAD: nothing is unnamed -- this probe measures nothing",
              file=sys.stderr)
        return 2

    print()
    print("what the PRINT says the 25 are:")
    for name, n in collections.Counter(s.printed for s in unnamed).most_common():
        print("   %-24s %d" % (name, n))
    strings = [s for s in unnamed
               if s.printed and ("Violino" in s.printed or "Viola" in s.printed
                                 or "Violoncello" in s.printed
                                 or "Basso" in s.printed)]
    print("   -> of 25, STRINGS: %d" % len(strings))

    print()
    print("are the unnamed a CONTIGUOUS BLOCK at the bottom of their system?")
    interleaved = 0
    for key in sorted(printed):
        grp = [s for s in staves if s.sys_key == key]
        if all(s.named for s in grp):
            continue
        flags = [s.named for s in grp]
        # contiguous-at-the-bottom == every named staff precedes every unnamed
        if any(flags[i] and not flags[i - 1] for i in range(1, len(flags))):
            interleaved += 1
            print("   p%d/s%d INTERLEAVED %s" % (key[0], key[1], flags))
        else:
            print("   p%d/s%d block: %d named then %d unnamed"
                  % (key[0], key[1], sum(flags), len(flags) - sum(flags)))
    print("   -> systems with an interleaved gap: %d" % interleaved)

    print()
    print("=" * 74)
    print("WITNESS 1 -- the CATALOG ROSTER")
    print("=" * 74)
    roster = [o for o in raw["observations"] if o["quantity"] == "roster_entry"]
    if not roster:
        print("   no roster_entry on the record")
    for o in roster:
        val = o.get("value") or {}
        names = val.get("instruments") or []
        print("   work_id     %s" % val.get("work_id"))
        print("   source_kind %s   complete=%s" % (val.get("source_kind"),
                                                   val.get("complete")))
        print("   families    %s" % (val.get("families"),))
        print("   instruments %s" % (names,))
        got = [n for n in names
               if n.lower() in {"violin", "viola", "cello", "violoncello",
                                "contrabass", "double bass", "bass"}]
        print("   -> STRING instruments named by the roster: %d %s"
              % (len(got), got))

    print()
    print("=" * 74)
    print("WITNESS 2 -- the CLEF, on the 25")
    print("=" * 74)
    ok = bad = absent = 0
    for s in unnamed:
        want = table.PRINTED_CLEF.get(s.printed or "", ())
        if s.clef is None:
            absent += 1
        elif s.clef in want:
            ok += 1
        else:
            bad += 1
            print("   WRONG p%d/s%d st%d printed=%-20s read=%s want=%s"
                  % (s.page, s.system, s.ordinal, s.printed, s.clef, want))
    print("   decided and AGREEING with the print   %d" % ok)
    print("   decided and DISAGREEING               %d" % bad)
    print("   abstained                             %d" % absent)

    print()
    print("   and on the REFERENCE system (p1/s0), which a continuity rule "
          "would read:")
    rok = rbad = rabsent = 0
    for s in [x for x in staves if x.sys_key == (1, 0)]:
        want = table.PRINTED_CLEF.get(s.printed or "", ())
        if s.clef is None:
            rabsent += 1
            print("      ABSENT  st%-2d %-14s" % (s.ordinal, s.printed))
        elif s.clef in want:
            rok += 1
        else:
            rbad += 1
            print("      WRONG   st%-2d %-14s read=%s want=%s"
                  % (s.ordinal, s.printed, s.clef, want))
    print("      agreeing %d  disagreeing %d  abstained %d" % (rok, rbad, rabsent))

    print()
    print("=" * 74)
    print("WITNESS 3 -- the KEY SIGNATURE as a transposition fingerprint")
    print("=" * 74)
    kok = kbad = kabsent = 0
    for s in unnamed:
        want = TRUE_KEY.get(s.printed or "")
        if s.key is None:
            kabsent += 1
        elif s.key == want:
            kok += 1
        else:
            kbad += 1
    print("   decided and AGREEING with the print   %d" % kok)
    print("   decided and DISAGREEING               %d" % kbad)
    print("   abstained                             %d" % kabsent)
    print("   the disagreeing readings, in full:")
    for s in unnamed:
        want = TRUE_KEY.get(s.printed or "")
        if s.key is not None and s.key != want:
            print("      p%d/s%d st%-2d %-20s read=%-4s truth=%s"
                  % (s.page, s.system, s.ordinal, s.printed, s.key, want))
    print()
    print("   ALL 75 staves, for context (the same reading, wider population):")
    aok = abad = aabsent = 0
    for s in staves:
        want = TRUE_KEY.get(s.printed or "")
        if s.key is None:
            aabsent += 1
        elif s.key == want:
            aok += 1
        else:
            abad += 1
    print("      agreeing %d  disagreeing %d  abstained %d" % (aok, abad, aabsent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
