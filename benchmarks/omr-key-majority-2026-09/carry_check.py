"""Does EXPORT CARRY a key where the decision abstained? — the positive control.

    python3 benchmarks/omr-key-majority-2026-09/carry_check.py <file.musicxml>

⚠️ THE CARRY IS MUSICXML'S OWN AND THERE IS NO `OMR_KEY_CARRY`. `staged/
export.py` builds the `<attributes>` block from `_key_dict(run.fifths)`, and a
`None` there makes `_mxl_attributes_block` omit `<key>` entirely — under
MusicXML's rules the part's last stated key then stands. So an abstaining
staff-run emits an `<attributes>` block with a clef and no `<key>`, and the
music that follows keeps the key of the system before it.

This prints every `<attributes>` block per part with the fifths it states or
`OMITTED (carries)`, so the claim is checked rather than asserted.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET


def main(path: str) -> None:
    root = ET.parse(path).getroot()
    names = {sp.get("id"): (sp.findtext("part-name") or "").strip()
             for sp in root.iter("score-part")}
    carried = 0
    for part in root.iter("part"):
        pid = part.get("id")
        for m in part.findall("measure"):
            for at in m.findall("attributes"):
                k = at.find("key")
                if k is None:
                    carried += 1
                    print(f"{pid} {names.get(pid, '')[:20]:<22} "
                          f"measure {m.get('number'):>4}  "
                          f"<key> OMITTED -> carries the part's last key")
                else:
                    print(f"{pid} {names.get(pid, '')[:20]:<22} "
                          f"measure {m.get('number'):>4}  "
                          f"fifths {k.findtext('fifths')}")
    print(f"\n{carried} attributes blocks omit <key> and therefore carry")


if __name__ == "__main__":
    main(sys.argv[1])
