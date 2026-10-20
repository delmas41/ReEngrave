"""2.172 step 4: full-movement Litolff numbers: notes/rests in the exported files (OFF, small ON, the 20261018-night export) and the log accounting lines."""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NIGHT = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/overnight-20261018-night/compare")


def mx(p):
    n = r = 0
    for x in ET.parse(p).getroot().iter("note"):
        if x.find("rest") is not None:
            r += 1
        else:
            n += 1
    return n, r


def acct(p):
    out = []
    for line in open(p, errors="replace"):
        if re.search(r"unread bars|held-out bars|bars marked red|notes the record holds", line):
            out.append(line.strip()[:110])
        m = re.search(r"'duration_narrowed': (\d+)", line)
        if m:
            out.append("duration_narrowed " + m.group(1))
    return out


for name, x, log in (("OFF", ROOT / "rec172/litfull-off.musicxml", ROOT / "rec172/litfull-off.log"),
                     ("small ON", ROOT / "rec172/litfull-small.musicxml", ROOT / "rec172/litfull-small.log"),
                     ("night export", NIGHT / "beethoven5-litolff.musicxml", NIGHT / "beethoven5-litolff-export.log")):
    print("==", name, "notes/rests", mx(x))
    for a in acct(log):
        print("   ", a)
