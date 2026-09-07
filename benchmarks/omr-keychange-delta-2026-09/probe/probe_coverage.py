"""STEP 1c — Q2 coverage: which staves DON'T move at a key change, and why.

Q1 (`probe_shared_delta` / `probe_delta_mechanism`) asks whether the staves
that DO change share a delta. Q2 asks whether every staff changes at all —
which is what a corroboration rule needs, since a witness has to exist before
its delta can be compared.

The residual bucket `PRESENT_AND_SILENT` from `probe_shared_delta` is split
here, because its two halves mean opposite things:

  key 0 : the staff is notated with NO key signature (horns, trumpets,
          timpani — the standard 19th-century convention) and therefore does
          not participate in a key change AT ALL. A page fact.
  key !=0: the staff carries a real signature and simply does not change it —
          a partial / sectional key change, or a bitonal passage.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _refs import encodings, root        # noqa: E402  fail-loud
from keys import load_keys               # noqa: E402
from probe_shared_delta import analyse   # noqa: E402

OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")



def work_key(path: str) -> str:
    parts = os.path.normpath(path).split(os.sep)
    return "/".join(parts[-3:-1])


def main() -> int:
    files = encodings()
    by_work = defaultdict(list)
    for f in files:
        by_work[work_key(f)].append(f)
    deduped = {sorted(v)[0] for v in by_work.values()}

    tallies = {"all": Counter(), "deduped": Counter()}
    bars = {"all": 0, "deduped": 0}
    full_change = {"all": 0, "deduped": 0}
    n_slots = {"all": 0, "deduped": 0}

    for i, f in enumerate(files):
        if i % 300 == 0:
            sys.stderr.write(f"  {i}/{len(files)}\n")
        try:
            w = analyse(load_keys(f))
        except Exception as exc:            # noqa: BLE001
            sys.stderr.write(f"  parse failed {f}: {exc}\n")
            continue
        scopes = ["all"] + (["deduped"] if f in deduped else [])
        for e in w["events"]:
            if e["n_changing"] < 2:
                continue
            for scope in scopes:
                bars[scope] += 1
                n_slots[scope] += e["n_staves"]
                if e["n_changing"] == e["n_staves"]:
                    full_change[scope] += 1
                tallies[scope]["CHANGES"] += e["n_changing"]
                for s in e["silent"]:
                    if "PRESENT_AND_SILENT" in s["reasons"]:
                        key = ("silent_UNSIGNATURED_STAFF"
                               if s["key_here"] == 0
                               else "silent_KEEPS_ITS_OWN_KEY")
                        tallies[scope][key] += 1
                    else:
                        for r in s["reasons"]:
                            tallies[scope]["silent_" + r] += 1

    if not bars["all"]:
        sys.stderr.write("FATAL: no multi-staff key-change bars found — "
                         "refusing to report a clean zero.\n")
        return 2

    for scope in ("all", "deduped"):
        t = tallies[scope]
        print("=" * 72)
        print(f"{scope}: {bars[scope]} multi-staff key-change bars, "
              f"{n_slots[scope]} staff-slots at those bars")
        print(f"  bars where EVERY staff changes: {full_change[scope]} "
              f"({full_change[scope] / bars[scope]:.4f})")
        for k, v in t.most_common():
            print(f"    {k:34s} {v:6d}  "
                  f"({v / n_slots[scope]:.4f} of staff-slots)")
        print()

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "coverage.json"), "w") as fh:
        json.dump({"bars": bars, "full_change": full_change,
                   "staff_slots": n_slots,
                   "tallies": {k: dict(v) for k, v in tallies.items()}},
                  fh, indent=1)
    print(f"wrote {OUT}/coverage.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
