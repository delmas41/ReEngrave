"""Every structural finding this repo's own instruments can state, in one table.

    python3 benchmarks/omr-plumbing-2026-09/probe/collect.py [--edges EDGES.json]

⚠️ THIS DOES NOT RANK. Sean, 2026-09-16: *"big picture fixes that get
prioritized once we have them all."* Collecting and ranking are separate acts
and the plan says why: the moment a count becomes a number to drive down it is
gamed, and ranking by the loudest bucket is the failure this project already
paid for twice (musicdiff's buckets are unrankable; attributing structural work
by `entire staff` alone systematically under-counts fragmentation).

## The taxonomy is the point, because each KIND is a different cost

  VOCABULARY   no category exists for the ink            (GATHER)
  WIRING       the value exists and nothing reads it     (any seam)
  FRAME        the value exists in units the reader cannot answer in
  SHAPE        the record has nowhere to PUT the fact    (spans)
  REACH        the wire is sound; nothing is supplied    (a READING problem)
  ARCHITECTURE the fix crosses a stage boundary, or needs a stage
  INSTRUMENT   the measuring tool is wrong — a finding about what we can SEE

⚠️⚠️ THE KINDS ARE ORDERED BY DEPENDENCY, AND THAT IS WHAT MAKES THE TABLE A
PRIORITISATION TOOL RATHER THAN A LIST. A category costs nothing until a
reader would have filled it; a reader costs nothing until something consumes
it. So VOCABULARY < WIRING < REACH: a fix only pays once everything
DOWNSTREAM of it is already connected. This is the wire-first plan's own
argument, arriving from the instruments.

Sources, all derived:
  reach --json          quantities nothing reads
  wiring --json         frame / detail / roundtrip faults
  no_producer           a parameter threaded with no supplier
  gather_coverage       ungathered quantities, families with no quantity
  edges.py --json       connections that never carried, measured over the matrix
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def _run_json(mod: str) -> dict:
    p = subprocess.run([sys.executable, "-m", mod, "--json"],
                       capture_output=True, text=True, cwd=ROOT)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {}


def collect(edges_path: str | None) -> list:
    out = []

    reach = _run_json("tools.omr.staged.reach")
    from tools.omr.staged import reach as reach_mod
    for r in reach.get("rows", []):
        if r["state"] == "LIVE":
            continue
        known = reach_mod.KNOWN_GAPS.get(r["quantity"], "")
        owned = "OPEN FINDING" not in known
        out.append({
            "id": f"REACH/{r['quantity']}",
            "kind": "VOCABULARY" if r["state"] == "GHOST" else "WIRING",
            "stage": ",".join(r["produced"]) or "—",
            "what": f"Q.{r['quantity'].upper()} is {r['state']}: "
                    f"produced by {','.join(r['produced']) or 'nothing'}, "
                    f"read by {','.join(r['read']) or 'nothing'}",
            "evidence": "python3 -m tools.omr.staged.reach",
            "status": "owned by a sibling instrument" if owned and known
                      else ("OPEN" if known else "UNACCOUNTED"),
            "source": "reach",
        })

    wiring = _run_json("tools.omr.staged.wiring")
    ev = "python3 -m tools.omr.staged.wiring --check"
    for f in (wiring.get("frames", {}).get("broken") or []):
        out.append({"id": f"FRAME/{f['decision']}/{f['quantity']}", "kind": "FRAME",
                    "stage": "ADJUDICATE", "evidence": ev, "status": "BROKEN", "source": "wiring",
                    "what": f"{f['decision']} reads Q.{f['quantity']} at "
                            f"{f['reads_at']}, filed at {','.join(f['filed_at'])} "
                            f"— the read returns nothing"})
    for f in (wiring.get("frames", {}).get("latent") or []):
        out.append({"id": f"FRAME/{f['decision']}/{f['quantity']}", "kind": "FRAME",
                    "stage": "ADJUDICATE", "evidence": ev, "status": "LATENT", "source": "wiring",
                    "what": f"{f['decision']} declares Q.{f['quantity']} (scope "
                            f"{f['reads_at']}) filed at {','.join(f['filed_at'])} — "
                            f"a trap armed for whoever wires it (needs {f['fix']})"})
    for f in (wiring.get("details", {}).get("unread") or []):
        out.append({"id": f"DETAIL/{f['key']}", "kind": "WIRING", "stage": "GATHER",
                    "evidence": ev, "status": "UNREAD", "source": "wiring",
                    "what": f"row field written at {f['sites'][0]} and read by nobody"})
    for f in (wiring.get("roundtrip", {}).get("dropped") or []):
        out.append({"id": f"ROUNDTRIP/{f['class']}.{f['field']}", "kind": "WIRING",
                    "stage": "HARNESS", "evidence": ev,
                    "status": "READ BUT DROPPED" if f.get("read") else "DROPPED", "source": "wiring",
                    "what": f"{f['class']}.{f['field']} is declared at "
                            f"{f['file']}:{f['line']}, READ in {f.get('uses',0)} places, "
                            f"and absent from its own to_json — a saved record "
                            f"cannot carry it"})

    if edges_path and pathlib.Path(edges_path).exists():
        e = json.loads(pathlib.Path(edges_path).read_text())
        by_state = collections.defaultdict(list)
        for row in e["rows"]:
            by_state[row["state"]].append(row)
        for state, kind, note in (
                ("NEVER_ASKED", "WIRING", "the consumer RAN and never asked for it"),
                ("CONSUMER_DEAD", "WIRING", "the consumer produced no verdict, and its subjects were there"),
                ("PRODUCER_DEAD", "REACH", "nothing produced the value in ANY arm"),
                ("NOT_EXERCISED", "REACH", "untested: no fixture printed this ink")):
            for row in by_state.get(state, []):
                out.append({
                    "id": f"EDGE/{row['producer']}->{row['consumer']}",
                    "kind": kind, "stage": row["stage"],
                    "what": f"{note} ({row['kind']})",
                    "evidence": "probe/edges.py out/matrix/*.record.json",
                    "status": state, "source": "edges",
                })
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--edges")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    rows = collect(args.edges)

    by_kind = collections.Counter(r["kind"] for r in rows)
    print("═══ STRUCTURAL FINDINGS — COLLECTED, NOT RANKED ══════════════════")
    print(f"{len(rows)} findings\n")
    ORDER = ["VOCABULARY", "WIRING", "FRAME", "SHAPE", "REACH", "ARCHITECTURE", "INSTRUMENT"]
    for kind in ORDER:
        group = [r for r in rows if r["kind"] == kind]
        if not group:
            continue
        print(f"── {kind}  ({len(group)})")
        for r in sorted(group, key=lambda x: x["id"])[:80]:
            print(f"   [{r['status']:22}] {r['id']}")
            print(f"       {r['what']}")
    print("\n── BY KIND")
    for kind in ORDER:
        print(f"   {kind:14} {by_kind.get(kind, 0)}")
    print("\n── POSITIVE CONTROL")
    got = {r.get("source") for r in rows}
    for src in ("reach", "wiring", "edges"):
        n = sum(1 for r in rows if r.get("source") == src)
        mark = "  " if src in got else "⚠️"
        print(f" {mark} {src:8} {n} findings" + ("" if src in got else
              "  — SOURCE SILENT: it did not run, which is NOT the same as "
              "finding nothing"))
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(rows, indent=2))
    return 0 if rows else 2


if __name__ == "__main__":
    sys.exit(main())
