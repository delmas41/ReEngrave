"""A/B the roster flag on every row whose identity rests on an unsettleable alias.

Re-runs ONLY the contextual pass, over each row's own stored transcription, once
with `OMR_ROSTER=1` and once with `0`. Nothing else differs — same page dicts,
same page image, same label ladder — so a difference in the instrument at an
ambiguous slot is attributable to the flag and to nothing else.

⚠️ Only the AFFECTED rows are run. The audit already says which those are from
stored output at no cost, and re-running the other 22 would cost an hour to
confirm they are unchanged at a slot they do not have.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

RUNNER = HERE / "_ab_one.py"


def pdf_for(row: str) -> Path:
    from tools.library.score_library import library_root
    if row.startswith("engraved--"):
        w = row[len("engraved--"):]
        local = REPO / "benchmarks/omr-orchestral-e2e/fixtures"
        base = local if any(local.glob("*.pdf")) else (
            library_root().parent / "benchmarks/omr-orchestral-e2e/fixtures")
        return base / f"{w}.pdf"
    rid = row[len("scan--"):]
    works = json.loads(
        (REPO / "benchmarks/omr-scan-e2e-2026-09/works.json").read_text())
    for r in works["rows"]:
        if r["row_id"] == rid:
            return library_root() / r["edition"]["catalog_path"]
    raise KeyError(row)


def arm(reading: Path, pdf: Path, roster: str) -> dict:
    env = dict(os.environ, OMR_ROSTER=roster, OMP_NUM_THREADS="2",
               MKL_NUM_THREADS="2")
    p = subprocess.run([sys.executable, "-u", str(RUNNER),
                        str(reading), str(pdf)],
                       cwd=REPO, env=env, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"{reading.name} roster={roster}:\n{p.stderr[-2000:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def main() -> int:
    audit = json.loads((HERE / "ambiguous_audit.json").read_text())
    affected = [r for r in audit
                if any(h["is_voice_on_orchestral"] for h in r["hits"])]
    print(f"rows with a voice-on-orchestral staff: {len(affected)}", flush=True)
    if not affected:
        print("REFUSING: nothing to A/B — run audit_ambiguous.py first",
              file=sys.stderr)
        return 2

    flipped = same = 0
    out = []
    for rec in affected:
        row = rec["row"].replace(".omr.json", "")
        reading = HERE / "readings" / rec["row"]
        pdf = pdf_for(row)
        on = arm(reading, pdf, "1")
        off = arm(reading, pdf, "0")
        for h in rec["hits"]:
            if not h["is_voice_on_orchestral"]:
                continue
            o = h["ordinal"]
            a, b = on.get(str(o)), off.get(str(o))
            changed = a != b
            flipped += changed
            same += not changed
            print(f"  {row:44s} ord {o:3d} {h['text']!r:16s} "
                  f"roster_on={a!s:12s} roster_off={b!s:12s}"
                  f"{'   FLIPS' if changed else ''}", flush=True)
            out.append({"row": row, "ordinal": o, "text": h["text"],
                        "roster_on": a, "roster_off": b, "flips": changed})
    print(f"\nvoice-on-orchestral staves: {flipped + same}; "
          f"corrected by OMR_ROSTER=0: {flipped}")
    (HERE / "ab_roster_ambiguity.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
