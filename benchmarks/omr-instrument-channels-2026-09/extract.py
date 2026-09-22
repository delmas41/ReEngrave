"""Pull the identity-relevant slice out of a shared staged record, ONCE.

⚠️ NOTHING IS FILTERED ON VALUE. An abstention is a row here exactly as a
decision is, because the whole question is which staves have no answer and
what else the record already holds about them.

⚠️ THE FOUR CHANNELS SEAN NAMES ARE THE FOUR QUANTITY GROUPS TAKEN:
  margin_label                 -- the name printed in the margin
  roster_entry                 -- the work's instrumentation list (DOCUMENT)
  staff_ordinal / system_staff_count / instrument
                               -- what ORDER needs: who is named, and where
  staff_group                  -- the family block, from where the interior
                                  barlines STOP (`Q.BRACKET_BLOCK`)
plus the clef, LAST and separately:
  clef / clef_glyph / clef_located / clef_position

⚠️ `clef_located` CARRIES ITS OWN REFUSAL BRANCH and that is why the
abstentions are kept: `locator_branch` is the difference between "this staff
has no C clef" and "the locator could not look".
"""
import hashlib
import json
import sys
from pathlib import Path

WANT = {"instrument", "slot_index", "clef", "clef_glyph", "clef_located",
        "clef_position", "staff_ordinal", "system_staff_count", "staff_group",
        "bracket_block", "margin_label", "roster_entry", "part_partition",
        "part_name", "document_identity"}
#: the quantity names as they appear in the pretty-printed file, for the cheap
#: pre-filter that keeps this from json-parsing 40,000 observations.
_NEEDLES = tuple('"quantity": "%s"' % q for q in WANT)

HERE = Path(__file__).parent
RECORDS = {
    "litolff": Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/"
                    "beethoven5-p1-p4-ink-identity.record.json"),
    "breitkopf": Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/"
                      "brahms1-breitkopf-p0-p3-ink.record.json"),
}


def slice_record(path: Path) -> dict:
    obs, vrd = [], []
    section = None
    depth = 0
    buf = []
    with path.open() as f:
        for line in f:
            if depth == 0:
                if '"observations": [' in line:
                    section = obs
                    continue
                if '"verdicts": [' in line:
                    section = vrd
                    continue
                if line.strip().startswith("{") and section is not None:
                    buf = [line]
                    depth = 1
                    continue
                continue
            buf.append(line)
            depth += line.count("{") - line.count("}")
            if depth:
                continue
            blob = "".join(buf)
            if any(n in blob for n in _NEEDLES):
                try:
                    section.append(json.loads(blob.rstrip().rstrip(",")))
                except ValueError:
                    pass
    return {"observations": obs, "verdicts": vrd}


def main() -> int:
    names = sys.argv[1:] or sorted(RECORDS)
    for name in names:
        path = RECORDS[name]
        if not path.is_file():
            print("MISSING %s -- %s" % (name, path), file=sys.stderr)
            return 2
        md5 = hashlib.md5(path.read_bytes()).hexdigest()
        data = slice_record(path)
        data["_record"] = str(path)
        data["_record_md5"] = md5
        out = HERE / "out" / ("slice-%s.json" % name)
        out.write_text(json.dumps(data, indent=1))
        print("%-10s md5=%s  observations=%d verdicts=%d  -> %s"
              % (name, md5, len(data["observations"]), len(data["verdicts"]),
                 out.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
