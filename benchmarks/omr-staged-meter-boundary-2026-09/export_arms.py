"""Export each arm's SAVED RECORD to MusicXML, and count what reached the file.

⚠️ NO RE-TRANSCRIPTION. `staged.export.to_musicxml` takes the run dict, so the
file is produced from the record already on disk -- the export arm cannot
disagree with the arm that was measured, and detector jitter cannot enter
between them.

Reports, per arm: the `<time>` each part declares, the number of measure rests
and their durations, and the export's own coverage report line for bars padded
because nothing was read in them.
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import export as staged_export  # noqa: E402


def main(files):
    for f in files:
        run = json.loads(Path(f).read_text())
        xml, report = staged_export.to_musicxml(run)
        out = Path(f).with_suffix(".musicxml")
        out.write_text(xml)
        root = ET.fromstring(xml)
        times = Counter()
        rest_durs = Counter()
        for part in root.iter("part"):
            div = 1
            for m in part.iter("measure"):
                at = m.find("attributes")
                if at is not None:
                    if at.find("divisions") is not None:
                        div = int(at.find("divisions").text)
                    t = at.find("time")
                    if t is not None:
                        times[f"{t.findtext('beats')}/{t.findtext('beat-type')}"
                              f"{'(' + t.get('symbol') + ')' if t.get('symbol') else ''}"] += 1
                for n in m.iter("note"):
                    r = n.find("rest")
                    if r is not None and r.get("measure") == "yes":
                        d = n.find("duration")
                        if d is not None:
                            rest_durs[round(int(d.text) / div, 3)] += 1
        print(f"\n── {Path(f).name}")
        print(f"   <time> declared: {dict(times)}")
        print(f"   measure-rest durations (quarters): {dict(sorted(rest_durs.items()))}")
        for k in ("empty_bars_padded", "measure_rests_read",
                  "empty_bars_padded_without_meter"):
            if k in report:
                print(f"   {k}: {report[k]}")
        print(f"   -> {out.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    main(ap.parse_args().files)
