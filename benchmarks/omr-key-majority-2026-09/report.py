"""The base-vs-arm table for one document: verdicts, keys written, notes.

    python3 benchmarks/omr-key-majority-2026-09/report.py <tag> [--truth <kind>]

Reads `out/<tag>-base.json`, `out/<tag>-arm.json` and the two MusicXML files
beside them. Prints, for one document:

  * key verdicts before/after, by outcome and by reason;
  * `<note>` count before/after — it MUST NOT MOVE, because nothing here
    touches a notehead;
  * `<key>` elements written, and every CHANGE with the bar it stands at;
  * where a truth kind is given, right/wrong/abstained by instrument.

⚠️ THE KEY COUNT AND THE CHANGE COUNT ARE DIFFERENT QUESTIONS. MusicXML
carries the last stated key forward, so a part that states one key writes one
`<key>`; a CHANGE is a second `<key>` in the same part with a different
`<fifths>`, and it is the change count that says whether we invented key
changes the plate does not print.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr import key_consensus as KC           # noqa: E402
from tools.omr import instruments as _inst          # noqa: E402

sys.path.insert(0, str(HERE))
from simulate import TRUTHS, CONCERT, fields        # noqa: E402


def key_rows(path):
    root = ET.parse(path).getroot()
    names = {sp.get("id"): (sp.findtext("part-name") or "").strip()
             for sp in root.iter("score-part")}
    out = []
    for part in root.iter("part"):
        seq = []
        for measure in part.findall("measure"):
            for attrs in measure.findall("attributes"):
                f = attrs.findtext("key/fifths")
                if f is not None:
                    seq.append((measure.get("number"), int(f)))
        changes = [(n, v) for (n, v), (_, prev) in zip(seq[1:], seq[:-1])
                   if v != prev]
        out.append((part.get("id"), names.get(part.get("id"), ""), seq, changes))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--truth", default=None, choices=sorted(TRUTHS))
    a = ap.parse_args()
    out = HERE / "out"

    print(f"== {a.tag}")
    for arm in ("base", "arm"):
        rec = load_record(out / f"{a.tag}-{arm}.json")["record"]
        kv = [v for v in rec["verdicts"] if v["quantity"] == "key_signature"]
        print(f"-- {arm}: {len(kv)} key verdicts  "
              f"{dict(collections.Counter(v['outcome'] for v in kv))}")
        print(f"   reasons {dict(collections.Counter(v.get('reason') for v in kv))}")
        sv = [v for v in rec["verdicts"] if v["quantity"] == "system_key"]
        if sv:
            print(f"   system_key {len(sv)}: "
                  f"{dict(collections.Counter(v.get('reason') for v in sv))}")
        if a.truth:
            label = {}
            for o in rec["observations"]:
                if o["quantity"] == "margin_label":
                    _, p, s, st, _ = fields(o["subject"])
                    label[(p, s, st)] = str(o["value"])
            right = wrong = abst = unscored = 0
            for v in kv:
                _, p, s, st, _ = fields(v["subject"])
                text = label.get((p, s, st))
                m = _inst.lookup(text) if text else None
                if m is None:
                    unscored += 1
                    continue
                table = TRUTHS[a.truth]
                t = table.get(m.instrument.name, CONCERT)
                if t is None:
                    unscored += 1
                    continue
                got = v.get("value") if v["outcome"] == "decided" else None
                if got is None:
                    abst += 1
                elif got == t:
                    right += 1
                else:
                    wrong += 1
            print(f"   vs truth({a.truth}): right {right} wrong {wrong} "
                  f"abstained {abst}  (unscored {unscored})")

        xml = out / f"{a.tag}-{arm}.musicxml"
        if not xml.exists():
            continue
        text = xml.read_text()
        rows = key_rows(xml)
        n_changes = sum(len(c) for _, _, _, c in rows)
        print(f"   file: {text.count('<note>')} <note>, "
              f"{text.count('<key>')} <key>, {n_changes} key CHANGES")
        for pid, name, seq, changes in rows:
            if changes:
                print(f"      {pid} {name[:22]:<24} opens {seq[0][1]:>3}  "
                      + " ".join(f"m{n}={v}" for n, v in changes))
        cov = out / f"{a.tag}-{arm}.coverage.json"
        if cov.exists():
            c = json.loads(cov.read_text()).get("status_census") or {}
            print(f"   census balanced={c.get('balanced')} "
                  f"unaccounted={c.get('unaccounted')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
