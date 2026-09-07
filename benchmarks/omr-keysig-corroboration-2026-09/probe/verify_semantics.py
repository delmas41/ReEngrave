"""What actually changed, read with an XML PARSER rather than off a line diff.

The raw line diff shows `<note>`, `<step>`, `<beam>` and `<voice>` lines
moving, which reads as notes being reordered. They are not: difflib aligns an
`<alter>` inserted into a RUN OF IDENTICAL NOTES across the note boundary. This
parses both exports and compares the note streams element by element, so the
claim "only `<key>` and `<alter>` moved" is checked instead of eyeballed.

Reports, per changed file:
  * `<key><fifths>` per part before/after
  * every note whose (step, alter, octave, duration, type) tuple differs
  * a hard assertion that the note COUNT and the (step, octave) sequence of
    every part are unchanged — if either moved, the re-spell did more than
    re-spell and the run exits non-zero.

⚠️ Fails loudly (exit 2) on an empty fixture set — see `_fixtures`.
"""
import json
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "omr-pipeline-audit-2026-09", "probe"))
from _fixtures import fixtures, SCAN, ENGRAVED  # noqa: E402  fail-loud

_WORKTREE = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, _WORKTREE)

from tools.omr.export import to_musicxml  # noqa: E402
from tools.omr.key_signature_corroboration import (  # noqa: E402
    drop_uncorroborated_key_changes,
)


def notes_and_keys(xml: str):
    """(note tuples per part, fifths sequence per part)."""
    root = ET.fromstring(xml)
    notes: dict[str, list[tuple]] = {}
    keys: dict[str, list[str]] = {}
    for part in root.iter("part"):
        pid = part.get("id") or "?"
        ns, ks = [], []
        for measure in part.iter("measure"):
            for f in measure.iter("fifths"):
                ks.append(f"m{measure.get('number')}:{f.text}")
            for note in measure.iter("note"):
                pitch = note.find("pitch")
                step = pitch.findtext("step") if pitch is not None else None
                alter = pitch.findtext("alter") if pitch is not None else None
                octave = pitch.findtext("octave") if pitch is not None else None
                ns.append((measure.get("number"), step, alter, octave,
                           note.findtext("duration"), note.findtext("type")))
        notes[pid], keys[pid] = ns, ks
    return notes, keys


def main() -> int:
    rc = 0
    changed_files = 0
    pooled_alter = pooled_key = 0
    for fam, files in (("scan", fixtures(SCAN, expect_at_least=11)),
                       ("engraved", fixtures(ENGRAVED, expect_at_least=11))):
        print(f"\n=== {fam}")
        for path in files:
            name = os.path.basename(path).split(".")[0]
            before_xml = to_musicxml(json.load(open(path)))
            result = json.load(open(path))
            for page in result.get("pages", []):
                drop_uncorroborated_key_changes(page)
            after_xml = to_musicxml(result)
            if before_xml == after_xml:
                continue
            changed_files += 1
            bn, bk = notes_and_keys(before_xml)
            an, ak = notes_and_keys(after_xml)

            if set(bn) != set(an):
                print(f"  !! {name}: the PART SET changed")
                rc = 1
                continue
            fields: Counter[str] = Counter()
            for pid in bn:
                if len(bn[pid]) != len(an[pid]):
                    print(f"  !! {name} {pid}: note COUNT "
                          f"{len(bn[pid])} -> {len(an[pid])}")
                    rc = 1
                    continue
                for b, a in zip(bn[pid], an[pid]):
                    if b == a:
                        continue
                    for i, label in enumerate(
                            ("measure", "step", "alter", "octave",
                             "duration", "type")):
                        if b[i] != a[i]:
                            fields[label] += 1
                if bk[pid] != ak[pid]:
                    pooled_key += 1
                    print(f"  {name} {pid}: fifths {bk[pid]} -> {ak[pid]}")
            other = {k: v for k, v in fields.items() if k != "alter"}
            pooled_alter += fields.get("alter", 0)
            print(f"  {name}: note fields that moved = {dict(fields)}")
            if other:
                print(f"  !! {name}: something other than `alter` moved: {other}")
                rc = 1
    if not changed_files:
        sys.stderr.write("FATAL: no export changed; the probe measured nothing.\n")
        return 2
    print(f"\nPOOLED over {changed_files} changed files: "
          f"{pooled_alter} notes re-spelled (alter only), "
          f"{pooled_key} parts whose <key> sequence changed")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
