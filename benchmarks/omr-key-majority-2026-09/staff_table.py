"""One row per (system, staff): label, clef, key verdict, and every reading
that fed it — the table the system-majority rule votes over.

    python3 benchmarks/omr-key-majority-2026-09/staff_table.py <record.json> [page/system ...]
"""
from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr.staged.record_io import load_record  # noqa: E402


def fields(key: str):
    head, *rest = key.split("/")
    nums = [int(x) if x.isdigit() else None for x in rest]
    while len(nums) < 4:
        nums.append(None)
    return head, nums[0], nums[1], nums[2], nums[3]


def main(path: str, *wanted: str) -> None:
    r = load_record(path)
    rec = r["record"]
    obs, verds = rec["observations"], rec["verdicts"]

    label, clef, keyv = {}, {}, {}
    marks = collections.Counter()
    fits = collections.defaultdict(list)
    tpl = collections.defaultdict(list)
    runs = {}
    for o in obs:
        q = o["quantity"]
        _, p, s, st, _ = fields(o["subject"])
        if q == "margin_label":
            label[(p, s, st)] = o["value"]
        elif q == "keysig_marker":
            marks[(p, s, st)] += 1
        elif q == "keysig_clef_fit":
            fits[(p, s, st)].append((o["value"], o["detail"].get("n_accidentals"),
                                     o["detail"].get("fifths"),
                                     o["detail"].get("decided_by")))
        elif q == "keysig_template_fit":
            tpl[(p, s, st)].append((o["value"], o["detail"].get("n_accidentals"),
                                    o["detail"].get("fifths")))
        elif q == "keysig_run_position":
            runs[(p, s, st)] = o["value"]
    for v in verds:
        _, p, s, st, _ = fields(v["subject"])
        if v["quantity"] == "clef":
            clef[(p, s, st)] = (v["outcome"], v.get("value"))
        elif v["quantity"] == "key_signature":
            keyv[(p, s, st)] = (v["outcome"], v.get("value"), v.get("reason"))

    keys = sorted(keyv)
    print(f"== {path}")
    print(f"{'subject':>12} {'label':<20} {'clef':<9} {'key':<26} "
          f"{'mark':>4} {'run':>5}  fits / template")
    for k in keys:
        if wanted and f"{k[0]}/{k[1]}" not in wanted:
            continue
        p, s, st = k
        cf = clef.get(k, ("-", None))
        kv = keyv[k]
        f = ";".join(f"{c}:n{n}:f{ff}:{d}" for c, n, ff, d in fits.get(k, []))
        t = ";".join(f"{c}:n{n}:f{ff}" for c, n, ff in tpl.get(k, []))
        print(f"{p}/{s}/{st:>3}   {str(label.get(k, '-'))[:19]:<20} "
              f"{str(cf[1])[:8]:<9} {kv[0][:4]}/{str(kv[1]):>4}/{str(kv[2])[:15]:<16} "
              f"{marks.get(k, 0):>4} {str(runs.get(k, '-'))[:5]:>5}  {f[:60]} | {t[:40]}")


if __name__ == "__main__":
    main(*sys.argv[1:])
