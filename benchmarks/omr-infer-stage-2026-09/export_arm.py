"""Export ONE record to MusicXML, and stamp the tree that did the exporting.

⚠️ THE TWO ARMS GO THROUGH THIS SAME SCRIPT so the export half carries no
difference of its own: arm OFF is the record as gathered, arm ON is the same
record after `reinfer.py --out`. The gather is shared, the adjudication is
shared, and the exporter is one process invocation apart.

⚠️⚠️ IT STAMPS THE EXPORTING TREE, WHICH CLOSES A RECORDED GAP. CLAUDE.md
notes of the dedupe session that *"the record names the tree that GATHERED it
and nothing names the tree that EXPORTED it, hours later in a separate
process"* — so an artefact's numbers could not be reproduced. The stamp goes
in the coverage JSON beside the file, and is best-effort but ATOMIC: commit
and dirtiness are written together or neither is, because a half-named tree
read as clean is how *"cannot tell"* becomes *"same"*.

    python3 benchmarks/omr-infer-stage-2026-09/export_arm.py \
        <record.json> --out out/export-off.musicxml
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def exporting_tree() -> dict:
    """commit + dirty, together or not at all."""
    def git(*a):
        return subprocess.check_output(["git", *a], cwd=str(ROOT),
                                       stderr=subprocess.DEVNULL).decode().strip()
    try:
        return {"commit": git("rev-parse", "HEAD"),
                "dirty": bool(git("status", "--porcelain"))}
    except Exception as exc:                            # noqa: BLE001
        return {"commit": None, "dirty": None,
                "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    from tools.omr.staged import export as staged_export

    doc = json.load(open(a.record))
    if "record" not in doc:
        doc = {"record": doc}
    xml, report = staged_export.to_musicxml(doc)
    Path(a.out).write_text(xml)

    report["exporting_tree"] = exporting_tree()
    report["source_record"] = a.record
    report["record_provenance"] = doc.get("provenance")
    cov = Path(a.out + ".coverage.json")
    cov.write_text(json.dumps(report, indent=2, default=str))

    print(f"wrote {a.out} and {cov}")
    print(f"  exporting tree: {report['exporting_tree']}")
    for k in ("notes_not_written", "notes_not_written_total"):
        if k in report:
            print(f"  {k}: {report[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
