"""The end-to-end arm: does the wired reader reach the join, and what changes?

⚠️ REACH FIRST, AND IT PRINTS THE RUNGS BEFORE ANY RESULT. A record gathered
without `--surya` reads zero margin labels on this edition and would produce a
clean, meaningless zero -- indistinguishable from a page that prints none. So
this exits non-zero declaring itself DEAD when `Q.MARGIN_LABEL` has no
observation on the record it was handed.

⚠️ WHAT IT IS BLIND TO. It reads a SAVED record, so it shows GATHER and
ADJUDICATE as they ran; it cannot show what a different adjudicator would have
decided. The join repair is measured by its unit tests and its mutation
battery, not here -- here it is only OBSERVED, on a record whose tree stamp
says which code produced it.

    python3 benchmarks/omr-part-join-phase2-2026-09/probe/join_arm.py \\
        out/record-labels.json [--musicxml out/beethoven5-p1-p4.musicxml]
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--musicxml", default=None)
    args = ap.parse_args()

    d = json.loads(Path(args.record).read_text())
    rec = d["record"]
    print("provenance:", d.get("provenance"))
    print()

    # ── REACH, before anything else ─────────────────────────────────────────
    labels = [o for o in rec["observations"] if o["quantity"] == "margin_label"]
    refused = [a for a in rec["abstentions"] if a["quantity"] == "margin_label"]
    print("=" * 72)
    print("REACH")
    print("=" * 72)
    print("  Q.MARGIN_LABEL observations : %d" % len(labels))
    print("  Q.MARGIN_LABEL abstentions  : %d  %s"
          % (len(refused),
             dict(collections.Counter(a.get("reason") for a in refused))))
    if not labels:
        print()
        print("DEAD: this record carries NO margin label at all. Either the")
        print("gather predates the pdf_path forward, or it ran without")
        print("--surya on a scan with no text layer. A zero from here would")
        print("say nothing about the join.")
        return 2
    for o in sorted(labels, key=lambda o: o["subject"]):
        print("     %-22s %r" % (o["subject"], o["value"]))

    # ── what identity then did ──────────────────────────────────────────────
    V = rec["verdicts"]
    print()
    print("=" * 72)
    print("IDENTITY AND THE JOIN")
    print("=" * 72)
    for q in ("instrument", "slot_index", "part_partition"):
        vs = [v for v in V if v["quantity"] == q]
        print("  %-16s %3d verdicts  outcomes %s  reasons %s"
              % (q, len(vs),
                 dict(collections.Counter(v["outcome"] for v in vs)),
                 dict(collections.Counter(v.get("reason") for v in vs))))
    for v in (v for v in V if v["quantity"] == "part_partition"):
        print("  part_partition value:", json.dumps(v["value"]))

    # ── and what the exporter does with it ──────────────────────────────────
    if args.musicxml:
        from tools.omr.staged import export as SX
        xml, report = SX.to_musicxml(d)
        Path(args.musicxml).write_text(xml)
        Path(args.musicxml + ".coverage.json").write_text(
            json.dumps(report, indent=2, default=str))
        print()
        print("=" * 72)
        print("THE EXPORT")
        print("=" * 72)
        print("  part_join:", json.dumps(report["part_join"]))
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        parts = root.findall("part")
        counts = collections.Counter(len(p.findall("measure")) for p in parts)
        print("  parts: %d" % len(parts))
        print("  measures-per-part histogram: %s"
              % dict(sorted(counts.items(), reverse=True)))
        print("  total measures: %d"
              % sum(len(p.findall("measure")) for p in parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
