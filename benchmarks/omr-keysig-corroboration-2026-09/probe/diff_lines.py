"""WHAT changed in the exported MusicXML when the flag goes on — line by line.

The A/B says the export differs on five scanned rows. This says in what, so a
reviewer can see whether anything moved beyond the `<key>` element and the
notes that were spelled against it. Also counts the noteheads standing in
every reverted range, so a `respelled = 0` can be told apart from a re-spell
that silently did nothing.

⚠️ Fails loudly (exit 2) on an empty fixture set — see `_fixtures`.
"""
import difflib
import json
import os
import re
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "omr-pipeline-audit-2026-09", "probe"))
from _fixtures import fixtures, SCAN, ENGRAVED  # noqa: E402  fail-loud

_WORKTREE = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, _WORKTREE)

from tools.omr.export import to_musicxml  # noqa: E402
from tools.omr.key_signature_corroboration import (  # noqa: E402
    _changes_in_staff, drop_uncorroborated_key_changes,
)

TAG = re.compile(r"<([a-zA-Z-]+)")


def tag_of(line: str) -> str:
    m = TAG.search(line)
    return m.group(1) if m else line.strip()[:20] or "(blank)"


def main() -> int:
    seen_any = False
    for fam, files in (("scan", fixtures(SCAN, expect_at_least=11)),
                       ("engraved", fixtures(ENGRAVED, expect_at_least=11))):
        print(f"\n=== {fam}")
        pooled: Counter[str] = Counter()
        for path in files:
            name = os.path.basename(path).split(".")[0]
            before = to_musicxml(json.load(open(path)))

            after_result = json.load(open(path))
            # Count the noteheads standing in every range this will revert,
            # BEFORE reverting, so `respelled = 0` is checkable.
            exposed = 0
            for page in after_result.get("pages", []):
                for system in page.get("systems", []):
                    staves = system.get("staves", [])
                    positions: Counter[int] = Counter()
                    per = {id(s): _changes_in_staff(s) for s in staves}
                    for ch in per.values():
                        for c in ch:
                            positions[c["measure_index"]] += 1
                    for staff in staves:
                        for c in per[id(staff)]:
                            if positions[c["measure_index"]] >= 2:
                                continue
                            after_key = (c["after"].get("sharps"),
                                         c["after"].get("flats"))
                            for m in staff["measures"][c["ordinal"]:]:
                                k = m.get("key_signature")
                                if k is None:
                                    continue
                                if (k.get("sharps"), k.get("flats")) != after_key:
                                    break
                                exposed += sum(
                                    1 for d in m.get("detections", [])
                                    if d.get("category") == "notehead"
                                    and d.get("pitch"))
            totals = {"reverted": 0, "respelled": 0}
            for page in after_result.get("pages", []):
                got = drop_uncorroborated_key_changes(page)
                totals["reverted"] += got["reverted"]
                totals["respelled"] += got["respelled"]
            after = to_musicxml(after_result)
            if before == after:
                continue
            seen_any = True
            local: Counter[str] = Counter()
            for line in difflib.unified_diff(before.splitlines(),
                                             after.splitlines(), n=0, lineterm=""):
                if line.startswith(("---", "+++", "@@")):
                    continue
                local[f"{line[0]} {tag_of(line[1:])}"] += 1
            pooled.update(local)
            print(f"  {name}: reverted={totals['reverted']} "
                  f"respelled={totals['respelled']} of {exposed} noteheads "
                  f"standing in the reverted ranges")
            for k, v in sorted(local.items()):
                print(f"      {k:<24} {v}")
        print(f"  POOLED changed lines: {dict(sorted(pooled.items()))}")
    if not seen_any:
        sys.stderr.write("FATAL: no export changed under the flag; the probe "
                         "is measuring nothing.\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
