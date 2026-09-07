"""STEP 2b — on REAL music, what would the delta CONJUNCT cost?

The shipped guard keeps a mid-staff key change where >= 2 staves of the system
change at the same bar. Adding "and by the same delta" makes the condition
strictly stronger, so it can only revert MORE. This measures how much more, on
ground truth: for every staff that genuinely changes key in the reference
corpus, is there another staff at that bar with the same delta?

Also does the two things a rate needs to be believable:

* **dedupe.** `library/reference/` holds several encodings of the same music
  (`holst--the-planets--full` and `holst--the-planets--mvt3` overlap), and an
  undeduped rate is a rate over encodings, not over music.
* **an independent cross-check of the work count**, by a route that shares no
  code with the parser: a regex over the decompressed bytes.
"""
from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _refs import encodings, root            # noqa: E402  fail-loud
from keys import load_keys, read_xml_bytes   # noqa: E402
from probe_shared_delta import analyse       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")

_FIFTHS_RE = re.compile(rb"<fifths[^>]*>\s*(-?\d+)\s*</fifths>")


def regex_has_key_change(path: str) -> bool:
    """Independent of `keys.py`: >1 distinct `<fifths>` value in the bytes.

    Deliberately crude and deliberately NOT structural — it shares no code
    with the ElementTree walk, so agreement between the two is evidence and
    not a tautology. It over-counts (a transposing part legitimately carries a
    different value from a non-transposing one at the SAME key), so it is a
    CEILING on the work count, which is the useful direction for a check that
    the parser is not missing changes.
    """
    try:
        blob = read_xml_bytes(__import__("pathlib").Path(path))
    except (OSError, ValueError, zipfile.BadZipFile):
        return False
    return len(set(_FIFTHS_RE.findall(blob))) > 1


def work_key(path: str) -> str:
    """`library/reference/<composer>/<work>/<file>` → `<composer>/<work>`."""
    parts = os.path.normpath(path).split(os.sep)
    return "/".join(parts[-3:-1])


def main() -> int:
    files = encodings()
    sys.stderr.write(f"reading {len(files)} encodings under {root()}\n")

    per_file = {}
    regex_flag = {}
    for i, f in enumerate(files):
        if i % 300 == 0:
            sys.stderr.write(f"  {i}/{len(files)}\n")
        regex_flag[f] = regex_has_key_change(f)
        try:
            per_file[f] = analyse(load_keys(f))
        except Exception as exc:              # noqa: BLE001
            sys.stderr.write(f"  parse failed {f}: {exc}\n")

    if not per_file:
        sys.stderr.write("FATAL: parsed nothing.\n")
        return 2

    # ── cross-check the work count by an independent route ──────────────
    parser_yes = {f for f, w in per_file.items() if w["events"]}
    regex_yes = {f for f, v in regex_flag.items() if v}
    print("=" * 72)
    print("CROSS-CHECK of 'which encodings hold a mid-score key change'")
    print(f"  ElementTree walk (keys.py)   : {len(parser_yes)}")
    print(f"  regex over the raw bytes     : {len(regex_yes)}  "
          f"(a CEILING — it also fires on transposed parts at one key)")
    print(f"  parser-yes not in regex-yes  : {len(parser_yes - regex_yes)}"
          f"   <- must be 0; a change implies >1 distinct <fifths>")
    only_regex = regex_yes - parser_yes
    print(f"  regex-yes not in parser-yes  : {len(only_regex)}")
    if parser_yes - regex_yes:
        for f in sorted(parser_yes - regex_yes)[:10]:
            print(f"      !! {os.path.basename(f)}")

    # Explain the regex-only set: it should be transposing scores at ONE key.
    sampled = []
    for f in sorted(only_regex)[:400]:
        w = per_file[f]
        sk_staves = w["n_staves"]
        sampled.append((os.path.basename(f), sk_staves))
    multi_staff_only_regex = sum(1 for _n, s in sampled if s > 1)
    print(f"      of {len(sampled)} sampled, {multi_staff_only_regex} have "
          f">1 staff (a transposing score at a constant key)")

    # ── dedupe ──────────────────────────────────────────────────────────
    by_work = defaultdict(list)
    for f in per_file:
        by_work[work_key(f)].append(f)
    works_with = {work_key(f) for f in parser_yes}
    print()
    print(f"  encodings                     : {len(per_file)}")
    print(f"  distinct <composer>/<work>    : {len(by_work)}")
    print(f"  encodings with a key change   : {len(parser_yes)}")
    print(f"  DISTINCT WORKS with a change  : {len(works_with)}")

    # ── the witness question, per changing staff ────────────────────────
    def witness_table(paths):
        n_changing = same_bar = same_bar_delta = 0
        per_bar_full = 0
        bars = 0
        for f in paths:
            for e in per_file[f]["events"]:
                if e["n_changing"] < 2:
                    # a solo change has no witness under EITHER rule
                    n_changing += e["n_changing"]
                    bars += 1
                    continue
                bars += 1
                counts = Counter(c["delta"] for c in e["changers"])
                for c in e["changers"]:
                    n_changing += 1
                    same_bar += 1
                    if counts[c["delta"]] >= 2:
                        same_bar_delta += 1
                if len(counts) == 1:
                    per_bar_full += 1
        return n_changing, same_bar, same_bar_delta, bars, per_bar_full

    # one encoding per distinct work — the alphabetically first, a fixed rule
    deduped = [sorted(by_work[w])[0] for w in sorted(by_work)]
    for label, paths in (("all encodings", sorted(per_file)),
                         ("deduped by work", deduped)):
        n, sb, sbd, bars, full = witness_table(paths)
        if not n:
            continue
        print()
        print(f"--- {label}: {bars} change bars, {n} changing staves")
        print(f"  staff has >=1 witness at the same BAR      : {sb}/{n} = "
              f"{sb/n:.4f}")
        print(f"  ... and by the same DELTA                  : {sbd}/{n} = "
              f"{sbd/n:.4f}")
        print(f"  => the delta conjunct would additionally revert "
              f"{sb - sbd} of {n} genuine staff changes "
              f"({(sb - sbd)/n:.4%})")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "witness-availability.json"), "w") as fh:
        json.dump({
            "n_encodings": len(per_file),
            "n_distinct_works": len(by_work),
            "n_encodings_with_change": len(parser_yes),
            "n_distinct_works_with_change": len(works_with),
            "regex_yes": len(regex_yes),
            "parser_yes_not_regex": sorted(
                os.path.basename(f) for f in parser_yes - regex_yes),
            "witness_all": witness_table(sorted(per_file)),
            "witness_deduped": witness_table(deduped),
        }, fh, indent=1)
    print(f"\nwrote {OUT}/witness-availability.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
