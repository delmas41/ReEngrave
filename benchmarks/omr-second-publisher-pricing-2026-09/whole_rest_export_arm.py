"""ONE RECORD, EXPORTED TWICE — what `OMR_WHOLE_REST_INK` costs the FILE.

⚠️⚠️ WHY A RE-EXPORT IS THE RIGHT INSTRUMENT HERE, AND WHY THE REBUILD ARM IS
NOT MERELY SLOWER BUT UNNECESSARY. CLAUDE.md's standing rule is that a plain
re-export is BLIND to an ADJUDICATE change, because it replays saved verdicts —
and `notehead_is_a_whole_rest` IS an ADJUDICATE decision. The rule does not
apply to THIS measurement for one checkable reason:

    grep -rn NOTEHEAD_IS_A_WHOLE_REST tools/ --include='*.py' | grep -v tests/

returns the declaration, the producer, the `ORDER` entry and **exactly one
reader: `export.py:542`**. Nothing in ADJUDICATE or EVALUATE consumes the
verdict. And `OMR_WHOLE_REST_INK` is read at EXPORT time by
`export.whole_rest_ink_enabled()`, whose own docstring says off "restores the
pre-2026-09-15 exporter exactly: the verdict is still DECIDED and still on the
record, and only the refusal goes away".

So the two arms differ in exactly the thing under test, and re-adjudicating
2.4 million observations twice to reach the same answer would be paying ~2.5
hours for a number a re-export gives in seconds. ⚠️ The blind spot is REAL and
is why the grep is quoted rather than the conclusion: if anything ever starts
reading that quantity inside ADJUDICATE, this arm stops being valid and
`benchmarks/omr-note-where-silence-2026-09/arm.py` is what to use instead.

⚠️ REACH AND A CONTROL BEFORE ANY DELTA. The reach is how many verdicts the
record holds at `true`; the control is that the two arms MUST DIFFER. Two
identical files are what a dead instrument produces, and on a document where
the rule fires zero times that is exactly what it would produce.

    python3 whole_rest_export_arm.py <record.json> --out-dir D
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as EXPORT              # noqa: E402
from tools.omr.staged.record import Q                      # noqa: E402

FLAG = EXPORT.WHOLE_REST_INK_ENV


def _notes(xml_text):
    """(part, measure, pitch, is_rest, duration) for every `<note>`."""
    out = []
    for part in ET.fromstring(xml_text).findall("part"):
        pid = part.get("id")
        for m in part.findall("measure"):
            num = m.get("number")
            for n in m.findall("note"):
                p = n.find("pitch")
                d = n.find("duration")
                out.append((pid, num,
                            None if p is None else
                            p.find("step").text + p.find("octave").text,
                            n.find("rest") is not None,
                            None if d is None else d.text))
    return out


def _export(result, *, on):
    os.environ[FLAG] = "1" if on else "0"
    assert EXPORT.whole_rest_ink_enabled() is on, "the flag did not take"
    return EXPORT.to_musicxml(result)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    result = json.loads(Path(args.record).read_text())
    rec = result["record"]
    print(f"record provenance {result.get('provenance')}")

    # ── REACH, first ────────────────────────────────────────────────────────
    vs = [v for v in rec["verdicts"]
          if v["quantity"] == Q.NOTEHEAD_IS_A_WHOLE_REST]
    true = [v for v in vs if v.get("value") is True]
    reasons = collections.Counter(v.get("reason") for v in vs)
    witness = collections.Counter((v.get("detail") or {}).get("witness")
                                  for v in true)
    print(f"\nREACH: {len(vs)} verdicts on the record, {len(true)} TRUE")
    for k, n in reasons.most_common():
        print(f"   {k:<36} {n}")
    print(f"   witness: {dict(witness)}")
    if not vs:
        print("INSTRUMENT DEAD: the record holds no verdict for this quantity "
              "at all, so both arms would be identical for a reason that is "
              "not the rule working.", file=sys.stderr)
        return 2
    if not true:
        print("THE RULE FIRES ON NOTHING IN THIS RECORD. That is a real and "
              "reportable answer about this document — and it means the two "
              "arms below are identical BY CONSTRUCTION and say nothing.",
              file=sys.stderr)
        return 2

    on_xml, on_rep = _export(result, on=True)
    off_xml, off_rep = _export(result, on=False)
    (out / "on.musicxml").write_text(on_xml)
    (out / "off.musicxml").write_text(off_xml)

    # ── THE CONTROL: they MUST differ ───────────────────────────────────────
    h_on = hashlib.md5(on_xml.encode()).hexdigest()
    h_off = hashlib.md5(off_xml.encode()).hexdigest()
    print(f"\nmd5 ON  {h_on}\nmd5 OFF {h_off}")
    if h_on == h_off:
        print("CONTROL FAILED: the flag changed nothing while the record "
              "holds TRUE verdicts — the arm is not exercising the rule.",
              file=sys.stderr)
        return 2
    print("control OK: the two arms differ, so the flag is being exercised")

    print("\nWHAT REACHED THE FILE")
    keys = set(off_rep["written"]) | set(on_rep["written"])
    for k in sorted(keys):
        a, b = off_rep["written"].get(k), on_rep["written"].get(k)
        mark = "   <-- MOVED" if a != b else ""
        print(f"   {k:<36} OFF {str(a):>7}  ->  ON {str(b):>7}{mark}")
    print("   notes_not_written buckets:")
    nb = set(off_rep["notes_not_written"]) | set(on_rep["notes_not_written"])
    for k in sorted(nb):
        a = off_rep["notes_not_written"].get(k, 0)
        b = on_rep["notes_not_written"].get(k, 0)
        mark = "   <-- MOVED" if a != b else ""
        print(f"     {k:<34} OFF {a:>7}  ->  ON {b:>7}{mark}")

    off_n, on_n = _notes(off_xml), _notes(on_xml)
    off_p = [n for n in off_n if n[2]]
    on_p = [n for n in on_n if n[2]]
    gone = collections.Counter(off_p) - collections.Counter(on_p)
    added = collections.Counter(on_p) - collections.Counter(off_p)
    print(f"\nPITCHED <note>: OFF {len(off_p)}  ->  ON {len(on_p)}")
    print(f"   removed {sum(gone.values())}, added {sum(added.values())}")
    print("   the notes the rule DELETES, by name:")
    for k, n in sorted(gone.items()):
        print(f"     -{n}  part {k[0]} measure {k[1]:>4}  {k[2]:<4} "
              f"duration {k[4]}")
    if added:
        print("   ⚠️ THE RULE ONLY EVER REFUSES. Anything ADDED is downstream "
              "re-planning and must be explained:")
        for k, n in sorted(added.items()):
            print(f"     +{n}  {k}")

    # ── the structural control: nothing but notes moved ─────────────────────
    # ⚠️ A count can agree while the file is reorganised underneath it, so the
    # SEQUENCE is compared and not only the totals.
    def strip_notes(x):
        return re.sub(r"<note>.*?</note>", "", x, flags=re.S)
    a, b = strip_notes(off_xml).split("\n"), strip_notes(on_xml).split("\n")
    same_outside = a == b
    print(f"\nwith every <note> element removed, the two files are "
          f"{'IDENTICAL' if same_outside else 'DIFFERENT'}")
    residue = []
    if not same_outside:
        import difflib
        residue = [ln.strip() for ln in difflib.unified_diff(a, b, lineterm="",
                                                             n=0)
                   if ln[:1] in "+-" and ln[:3] not in ("---", "+++")
                   and ln.strip() not in ("+", "-")]
        # ⚠️ THE CONTROL IS NOT WIDENED UNTIL IT PASSES. The arc export work
        # records exactly that temptation and refuses it; a strip that grows
        # to swallow whatever differed stops being a control. The residue is
        # PRINTED instead, so a reader adjudicates it rather than trusting a
        # green line — and here it is one `<backup>`, which is the `<note>`
        # the rule removed having been the only member of its voice stream.
        # That is downstream re-planning, and the counters name it
        # independently as `two_voice_bars`.
        print(f"   residue: {len(residue)} lines, and every one of them must "
              f"be explained —")
        for ln in residue[:20]:
            print(f"     {ln[:100]}")
        print(f"   counters say two_voice_bars "
              f"{off_rep['written'].get('two_voice_bars')} -> "
              f"{on_rep['written'].get('two_voice_bars')}, which is the same "
              f"fact from the other side.")

    json.dump({"provenance": result.get("provenance"),
               "reach": {"verdicts": len(vs), "true": len(true),
                         "reasons": dict(reasons),
                         "witness": {str(k): v for k, v in witness.items()}},
               "md5": {"on": h_on, "off": h_off},
               "pitched_notes": {"off": len(off_p), "on": len(on_p)},
               "removed": [list(k) + [n] for k, n in sorted(gone.items())],
               "added": [list(k) + [n] for k, n in sorted(added.items())],
               "identical_outside_notes": same_outside,
               "residue_outside_notes": residue,
               "off": off_rep, "on": on_rep},
              open(out / "arm.json", "w"), indent=1)
    print(f"\nwrote -> {out/'arm.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
