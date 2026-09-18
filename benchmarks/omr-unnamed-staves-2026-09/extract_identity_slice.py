"""Extract the small identity-relevant slice from the shared staged record.

The record is ~146 MB and every question in this benchmark needs only a few
hundred rows of it, so it is read ONCE here and cached. Everything downstream
reads the cache, which makes each probe a second rather than a minute.

WHAT IS TAKEN, and why each: per STAFF subject --
  instrument / slot_index   the decision under study and its input
  clef / key_signature      the two candidate witnesses the brief names
  staff_ordinal             the staff's position inside its own system
  system_staff_count        how many staves the system prints
plus the document-level roster_entry, because a roster that names no string
family cannot name a string staff and that is checkable rather than arguable.

NOTHING IS FILTERED on value: an abstention is a row here exactly as a decision
is, because the whole question is which staves have no answer.
"""
import json
import sys
import hashlib
from pathlib import Path

RECORD = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/"
              "beethoven5-p1-p4-ink-identity.record.json")
EXPECT_MD5 = "ea80ae5908288c76baaa502054a37d43"
#   ⚠️ `clef_glyph` / `clef_position` are GATHER OBSERVATIONS, not the clef
#   VERDICT (`gather.py:1687` and `:1705` call `log.observe` at gather time on
#   the staff subject). That distinction is load-bearing here: the verdict
#   `clef` is ORDER position 9 and `instrument` is 5, so a decision at 5
#   reading the VERDICT reads None and closes a cycle -- `adjudicate_clef`
#   weights the instrument at 1.0 in the other direction. The RAW readings are
#   available to every decision at every position with no cycle, which is why
#   Sean's rule can consult them and `Q.CLEF` cannot be consulted.
WANT = {"instrument", "slot_index", "clef", "key_signature", "staff_ordinal",
        "system_staff_count", "roster_entry", "margin_label", "part_partition",
        "keysig_template_fit", "keysig_clef_fit",
        "clef_glyph", "clef_position"}
OUT = Path(__file__).parent / "out" / "identity-slice.json"


def main() -> int:
    if not RECORD.is_file():
        print("DEAD: no record at %s" % RECORD, file=sys.stderr)
        return 2
    h = hashlib.md5()
    with RECORD.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != EXPECT_MD5:
        # A different record is a different measurement. Refuse rather than
        # silently report numbers nobody can reproduce.
        print("DEAD: record md5 %s != %s" % (h.hexdigest(), EXPECT_MD5),
              file=sys.stderr)
        return 2
    print("record md5 %s OK" % h.hexdigest(), file=sys.stderr)

    doc = json.loads(RECORD.read_text())
    rec = doc.get("record", doc)
    verdicts = [v for v in rec.get("verdicts", []) if v.get("quantity") in WANT]
    obs = [o for o in rec.get("observations", []) if o.get("quantity") in WANT]
    print("verdicts kept %d  observations kept %d" % (len(verdicts), len(obs)),
          file=sys.stderr)
    if not verdicts:
        print("DEAD: no verdicts of any wanted quantity -- wrong shape?",
              file=sys.stderr)
        return 2
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"_record_md5": EXPECT_MD5, "verdicts": verdicts, "observations": obs},
        indent=1))
    print("wrote %s (%.2f MB)" % (OUT, OUT.stat().st_size / 1e6), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
