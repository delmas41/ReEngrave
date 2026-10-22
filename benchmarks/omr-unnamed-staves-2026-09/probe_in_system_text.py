"""FACT 1: is the identity printed INSIDE the system, and do we already read it?

Sean, from the print: "Bassi is written above the staff in the first measure
not in the margin." If that is general, the 25 unnamed staves are not unnamed
at all -- their label is simply in a band no identity consumer looks at, and
the whole geometric alignment question is unnecessary.

⚠️ THIS IS A READING QUESTION AND IT HAS A MEASURABLE ANSWER, so it is asked
before any inference is designed. Three numbers, in order, because they fail
differently:
   (a) did the direction-word READER RUN at all on this record -- a reader
       that never ran and a page that prints nothing are the same zero, and
       this repo has been caught by that distinction more than once;
   (b) how many of the 25 carry word-shaped ink the reader accepted;
   (c) of those, how many spell an INSTRUMENT rather than a direction.

(c) is the one that matters, and the lexicon is the discriminator, NOT the
position: the coordinator's own crop of p2/s0's bottom staff shows the text
above it is `cresc.` -- a direction -- on the very staff whose margin is blank.
So the band carries both kinds and a consumer must tell them apart by what the
word IS.
"""
import collections
import json
import sys
from pathlib import Path

RECORD = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/"
              "beethoven5-p1-p4-ink-identity.record.json")
OUT = Path(__file__).parent / "out" / "in-system-text.json"


def main() -> int:
    if not RECORD.is_file():
        print("DEAD: no record", file=sys.stderr)
        return 2
    doc = json.loads(RECORD.read_text())
    rec = doc.get("record", doc)

    words = [o for o in rec["observations"]
             if o.get("quantity") == "direction_word"]
    labels = [o for o in rec["observations"]
              if o.get("quantity") == "margin_label"]
    dverd = [v for v in rec.get("verdicts", [])
             if v.get("quantity") == "direction"]

    print("=" * 74)
    print("(a) DID THE READER RUN?")
    print("=" * 74)
    print("   Q.DIRECTION_WORD observations   %d" % len(words))
    print("   Q.MARGIN_LABEL observations     %d" % len(labels))
    print("   direction verdicts              %d" % len(dverd))
    reasons = collections.Counter(v.get("reason") for v in dverd)
    print("   direction verdict reasons       %s" % dict(reasons))
    outcomes = collections.Counter(v.get("outcome") for v in dverd)
    print("   direction verdict outcomes      %s" % dict(outcomes))
    if not dverd:
        print("   -> the decision produced NO verdict at all")

    # A page that prints nothing and a reader that never ran are the same zero.
    unavailable = reasons.get("reader_unavailable", 0) + \
        reasons.get("READER_UNAVAILABLE", 0)
    if unavailable:
        print("   ⚠️ READER_UNAVAILABLE on %d -- this record cannot answer the "
              "question" % unavailable)

    print()
    print("=" * 74)
    print("(b) WHAT THE READER ACCEPTED, and WHERE")
    print("=" * 74)
    if not words:
        print("   ZERO direction words on the whole record.")
    per_staff = collections.Counter()
    texts = collections.Counter()
    for o in words:
        sub = o.get("subject", "")
        val = o.get("value")
        text = val.get("text") if isinstance(val, dict) else val
        texts[str(text)] += 1
        parts = sub.split("/")
        if len(parts) >= 4:
            per_staff[(int(parts[1]), int(parts[2]), int(parts[3]))] += 1
    print("   distinct accepted words: %d" % len(texts))
    for t, n in texts.most_common(40):
        print("      %-28s %d" % (t, n))

    print()
    print("=" * 74)
    print("(c) DO ANY LAND ON THE 25 UNNAMED STAVES?")
    print("=" * 74)
    import table
    staves, printed_lineups, _ = table.load()
    unnamed = [s for s in staves if not s.named]
    hit = 0
    for s in unnamed:
        key = (s.page, s.system, s.ordinal)
        n = per_staff.get(key, 0)
        if n:
            hit += 1
        print("   p%d/s%d st%-2d printed=%-20s direction words on this staff: %d"
              % (s.page, s.system, s.ordinal, s.printed, n))
    print()
    print("   unnamed staves carrying ANY accepted word: %d of %d"
          % (hit, len(unnamed)))

    # Would any accepted word resolve to an instrument at all?
    print()
    print("=" * 74)
    print("(d) WOULD THE LEXICON READ ANY ACCEPTED WORD AS AN INSTRUMENT?")
    print("=" * 74)
    try:
        from tools.omr import instruments
        named = []
        for t in sorted(texts):
            try:
                m = instruments.lookup(t)
            except Exception as exc:  # a lexicon that raises is a finding
                print("   lookup(%r) raised %s" % (t, exc))
                continue
            if m is not None and getattr(m, "instrument", None) is not None:
                named.append((t, m))
        if not named:
            print("   NONE of the %d accepted words resolves to an instrument."
                  % len(texts))
        for t, m in named:
            print("   %-28s -> %s" % (t, m))
    except ImportError as exc:
        print("   could not import the lexicon: %s" % exc)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n_direction_words": len(words), "n_margin_labels": len(labels),
         "direction_reasons": dict(reasons),
         "accepted_texts": dict(texts),
         "unnamed_with_words": hit}, indent=1))
    print()
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
