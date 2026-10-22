"""Where does L - C actually go? -- run AFTER the arms, never during.

Part A says `--surya --ocr` is worth ~18 s/page attributable, so ~73 s over
four pages. Part B's first pair says 227 s. The residue is ~155 s and it is
a finding rather than an error bar, so this asks the records what the two
arms DID differently rather than guessing.

⚠️ THE LEADING HYPOTHESIS, WRITTEN BEFORE THE NUMBERS ARE READ, so it can be
refuted rather than confirmed: *the residue is not the reader, it is
everything the pipeline does once identity is DECIDED*. In the C arm
`Q.INSTRUMENT` abstains on all 75 staves, so `slot_index` falls back to the
ordinal, `part_partition` refuses, and the exporter emits fragments -- all
cheap. In the L arm 50 instruments resolve, the name-based join runs, and
CLAUDE.md records that taking the document from 75 fragments to 37 parts.
More parts joined is more cross-system comparison in `groups`, more verdicts
in ADJUDICATE, and a bigger record to serialise.

If that is right, the residue is the pipeline doing the job the flag exists
to enable, not an unexplained tax on the reader -- and it belongs on the
BENEFIT side of the decision, not the cost side. If it is wrong, the numbers
below will not show the extra work.

⚠️ IT READS, IT DOES NOT TIME. Nothing here can say how many SECONDS each
extra verdict cost; it can only say whether the extra work exists and how
big it is. Turning that into seconds needs per-stage timing, which is a
change to the CLI and another pair of arms.

    python3 benchmarks/omr-surya-staged-cost-2026-09/decompose.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def grab(path: Path, key: str) -> dict | None:
    """One top-level object out of a ~130 MB record, without parsing it.

    Streamed for the reason census.py is: `json.load` on one of these costs
    multiple GB, and these files exist in pairs.
    """
    buf: list[str] = []
    depth = 0
    want = f'"{key}": {{'
    with path.open() as fh:
        for line in fh:
            if not buf:
                if line.lstrip().startswith(want):
                    buf = [line.lstrip()]
                    depth = line.count("{") - line.count("}")
                    if depth <= 0:
                        break
                continue
            buf.append(line)
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                break
    if not buf:
        return None
    try:
        return json.loads("{" + "".join(buf).rstrip().rstrip(",") + "}")[key]
    except Exception:                                         # noqa: BLE001
        return None


def main() -> int:
    arms = [a for a in ("L1", "C1", "L2", "C2", "LD")
            if (OUT / f"record-{a}.json").is_file()]
    if not arms:
        print("no arm records yet")
        return 2

    summaries, adjud = {}, {}
    for a in arms:
        p = OUT / f"record-{a}.json"
        summaries[a] = grab(p, "summary") or {}
        adjud[a] = grab(p, "adjudication") or {}
        print("%s: record %.0f MB" % (a, p.stat().st_size / 1e6))

    print()
    print("── ADJUDICATE ─────────────────────────────────────────")
    for a in arms:
        d = adjud[a]
        print("  %-3s decided %-6s abstained %-6s"
              % (a, d.get("decided"), d.get("abstained")))

    print()
    print("── per-quantity rows, where the arms DIFFER ───────────")
    keys = sorted({k for a in arms for k in summaries[a]})
    ref = arms[0]
    print("  %-26s %s" % ("quantity", "  ".join("%9s" % a for a in arms)))
    for k in keys:
        cells = []
        for a in arms:
            s = summaries[a].get(k, {})
            cells.append("%4s/%-4s" % (s.get("read", "-"),
                                       s.get("declined", "-")))
        vals = {tuple(sorted(summaries[a].get(k, {}).items())) for a in arms}
        if len(vals) > 1:
            print("  %-26s %s   <- differs" % (k, "  ".join("%9s" % c
                                                            for c in cells)))
    print()
    print("  (cells are read/declined)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
