"""The census line for one Part B arm -- and a CORRECTION to the scope's own.

`docs/scope-surya-staged-optin-2026-09-16.md` §9 control 3 says to take it
with `grep -c '"margin_label"' out/record-$arm.json`, asserting `L >= 45` and
`C == 0`.

⚠️⚠️ THAT GREP STOPPED WORKING THE MOMENT STEP 1 LANDED, AND IT FAILS IN THE
DIRECTION THAT HIDES. `gather_margin_labels` now writes an ABSTENTION per
staff (and a page row per absent rung) carrying `"quantity":
"margin_label"` -- so a C arm, which must census ZERO, greps as ~75+ and the
control silently inverts: the arm that is supposed to read nothing looks like
the one that read most. The census has to count OBSERVATIONS, which is what
it always meant.

⚠️ STREAMED, NEVER `json.load`ed. A four-page staged record is ~130 MB on
this document (`library/_shared-records/beethoven5-p1-p4.record.json`), and
parsing one costs multiple GB -- on the machine that is mid-benchmark, which
is the one place a memory spike is guaranteed to corrupt the measurement it
is measuring.

    python3 benchmarks/omr-surya-staged-cost-2026-09/census.py \\
        out/record-L1.json --expect-observations-at-least 45
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

# ⚠️ INDENT-AGNOSTIC, AND THE FIRST DRAFT WAS NOT. The staged CLI writes
# `{"record": {...}, "summary": {...}}`, so the row arrays are one level
# DEEPER than a bare `Log.to_json()` -- and a fixed-indent regex found the
# summary, found zero rows, and printed `census OK: 0`. A census that reports
# a clean zero because it was looking at the wrong indentation is the
# "control that computes the wrong thing" this repo keeps paying for; caught
# by running it against the committed 130 MB record, whose own summary says
# `declined: 75`, and noticing the two disagreed. That disagreement is now
# the VOID check at the bottom of `main`.
_SECTION = re.compile(r'^\s+"(observations|abstentions|verdicts)": \[')
_ITEM = re.compile(r"^\s+\{\s*$")
_KEY = re.compile(r'^\s+"(quantity|reason|reader|subject)": "([^"]*)"')


def census(path: Path) -> dict:
    section = None
    obs = 0
    reasons: Counter = Counter()
    readers: Counter = Counter()
    subjects: Counter = Counter()
    cur: dict = {}
    summary = None
    grab_summary: list[str] | None = None
    depth = 0

    with path.open() as fh:
        for line in fh:
            if grab_summary is not None:
                grab_summary.append(line)
                depth += line.count("{") - line.count("}")
                if depth <= 0:
                    try:
                        summary = json.loads(
                            "{" + "".join(grab_summary).rstrip().rstrip(",")
                            + "}")["summary"]
                    except Exception:                         # noqa: BLE001
                        summary = None
                    grab_summary = None
                continue
            if line.lstrip().startswith('"summary": {'):
                grab_summary = [line.lstrip()]
                depth = line.count("{") - line.count("}")
                continue
            m = _SECTION.match(line)
            if m:
                section = m.group(1)
                continue
            if section is None:
                continue
            if _ITEM.match(line):
                cur = {}
                continue
            k = _KEY.match(line)
            if k:
                cur[k.group(1)] = k.group(2)
                if cur.get("quantity") == "margin_label" and "reason" in cur \
                        and section == "abstentions":
                    reasons[cur["reason"]] += 1
                    readers[cur.get("reader", "?")] += 1
                    subjects[cur.get("subject", "?").split("/")[0]] += 1
                    cur = {"quantity": None}
                elif (cur.get("quantity") == "margin_label"
                      and section == "observations"
                      and "reader" in cur):
                    obs += 1
                    readers["OBS:" + cur.get("reader", "?")] += 1
                    cur = {"quantity": None}
    return {"margin_label_observations": obs,
            "margin_label_abstention_reasons": dict(reasons),
            "readers": dict(readers),
            "abstention_subject_kinds": dict(subjects),
            "summary_margin_label": (summary or {}).get("margin_label"),
            "summary_instrument": (summary or {}).get("instrument")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--expect-observations-at-least", type=int, default=None)
    ap.add_argument("--expect-observations-exactly", type=int, default=None)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    path = Path(args.record)
    if not path.is_file():
        print("VOID: no such record: %s" % path)
        return 2
    out = census(path)
    print(json.dumps(out, indent=2, sort_keys=True))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(out, indent=2,
                                                  sort_keys=True))

    n = out["margin_label_observations"]
    lo = args.expect_observations_at_least
    ex = args.expect_observations_exactly
    if lo is not None and n < lo:
        print("VOID: %d margin_label observations, expected >= %d" % (n, lo))
        return 1
    if ex is not None and n != ex:
        print("VOID: %d margin_label observations, expected exactly %d"
              % (n, ex))
        return 1
    # ⚠️ A CROSS-CHECK, NOT A RESTATEMENT: the streamed count and the record's
    # own `summary` are produced by different code over the same log, so a
    # disagreement is a defect in one of them and not a rounding difference.
    sm = out["summary_margin_label"] or {}
    if sm and sm.get("read", 0) != n:
        print("VOID: streamed %d observations, the record's own summary says "
              "%d" % (n, sm.get("read", 0)))
        return 1
    declined = sum(out["margin_label_abstention_reasons"].values())
    if sm and sm.get("declined", 0) != declined:
        print("VOID: streamed %d abstentions, the record's own summary says "
              "%d -- the streamer is looking at the wrong rows"
              % (declined, sm.get("declined", 0)))
        return 1
    print("census OK: %d margin_label observations" % n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
