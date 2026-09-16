"""What a SHARED staged record contains — reach first, so the next job can
tell from the repo alone whether it can answer its question without
re-gathering.

⚠️ REACH BEFORE ACCURACY, and the FIRST number is the LABEL REACH per system:
without the OCR rungs `Q.MARGIN_LABEL` is empty, `instrument` abstains
`no_evidence` on every staff, `slot_index` collapses to the staff ordinal and
the part join grafts. A record gathered without labels is worth much less, and
nothing else in the report says so.

    python3 .../inventory_probe.py <record.json> [--expect 14,27,28,28]

Exits non-zero when it measured NOTHING — a dead instrument must not read as a
clean result.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys


def load(path):
    with open(path) as f:
        return json.load(f)


def staff_key(subject):
    # subject is like "staff/<page>/<system>/<staff>"
    parts = str(subject).split("/")
    return parts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--expect", default="",
                    help="comma list of PRINTED staff counts per page, "
                         "hand-read (Brahms 1 Breitkopf p0-3: 14,27,28,28)")
    args = ap.parse_args()

    d = load(args.record)
    rec = d["record"]
    obs = rec["observations"]
    verdicts = rec["verdicts"]

    print("=" * 66)
    print("PROVENANCE:", json.dumps(d.get("provenance")))
    prov = d.get("provenance") or {}
    if prov.get("dirty") is not False:
        print("  ⚠️ NOT a clean tree — this record's value as a shared")
        print("     BASELINE is reduced: no later job can say which tree made it.")
    print("=" * 66)

    # ---- 1. REACH: margin labels, per SYSTEM ------------------------------
    labels = [o for o in obs if o["quantity"] == "margin_label"]
    by_system = collections.defaultdict(list)
    staves_by_system = collections.defaultdict(set)
    for o in obs:
        p = staff_key(o["subject"])
        if p and p[0] == "staff" and len(p) >= 4:
            staves_by_system[(p[1], p[2])].add(p[3])
    for o in labels:
        p = staff_key(o["subject"])
        if len(p) >= 4:
            by_system[(p[1], p[2])].append(o)

    print("\n── 1. LABEL REACH per system (the number that says whether this")
    print("      record is useful at all) ─────────────────────────────────")
    total_lab = total_st = 0
    for key in sorted(staves_by_system, key=lambda k: (int(k[0]), int(k[1]))):
        n_st = len(staves_by_system[key])
        got = [o for o in by_system.get(key, []) if str(o.get("value") or "").strip()]
        total_lab += len(got)
        total_st += n_st
        print("  page %s system %s: %2d staves, %2d labels  %s"
              % (key[0], key[1], n_st, len(got),
                 [str(o["value"]) for o in got][:14]))
    print("  TOTAL: %d labels over %d staves" % (total_lab, total_st))
    if total_st == 0:
        print("  ⚠️ NOTHING MEASURED — instrument DEAD")
        return 2

    # the abstention reasons, which say WHICH rung was the limit
    lab_abst = collections.Counter()
    for a in rec.get("abstentions", []):
        if a.get("quantity") == "margin_label":
            lab_abst[a.get("reason")] += 1
    if lab_abst:
        print("  margin_label abstentions:", dict(lab_abst))

    # ---- 2. STAFF COUNTS vs the PRINT ------------------------------------
    print("\n── 2. STAFF COUNTS vs the print ───────────────────────────────")
    per_page = collections.Counter()
    for (pg, _sys), sts in staves_by_system.items():
        per_page[int(pg)] += len(sts)
    expect = [int(x) for x in args.expect.split(",") if x.strip()]
    pages = sorted(per_page)
    print("  read   :", [per_page[p] for p in pages], "(pages %s)" % pages)
    if expect:
        got = [per_page[p] for p in pages]
        print("  printed:", expect)
        if got == expect:
            print("  ✅ AGREES with the hand-read print on every page")
        else:
            print("  ⚠️⚠️ DISAGREES — this is a SEGMENTATION result and it")
            print("       changes what the record is good for.")

    # ---- 3. What the record DECIDED --------------------------------------
    print("\n── 3. ADJUDICATION ────────────────────────────────────────────")
    adj = d["adjudication"]
    for k in sorted(adj["decided"]):
        print("  %-24s decided %5d" % (k, adj["decided"][k]))
    print("  -- abstentions --")
    for k in sorted(adj["abstained"]):
        print("  %-24s %s" % (k, adj["abstained"][k]))
    if adj.get("excluded_as_circular"):
        print("  ⚠️ excluded as circular:", len(adj["excluded_as_circular"]))

    # ---- 4. Quantities present, with counts ------------------------------
    print("\n── 4. QUANTITIES OBSERVED (what a later job can read) ─────────")
    q = collections.Counter(o["quantity"] for o in obs)
    for name, n in sorted(q.items()):
        print("  %-28s %6d" % (name, n))

    print("\n── 5. VERDICT quantities ──────────────────────────────────────")
    qv = collections.Counter(v["quantity"] for v in verdicts)
    for name, n in sorted(qv.items()):
        print("  %-28s %6d" % (name, n))

    # ---- 6. The METER, which this document is the KNOWN-BAD arm for ------
    print("\n── 6. THE METER — this document is the KNOWN-BAD arm ──────────")
    for v in verdicts:
        if v["quantity"] in ("meter",):
            print("  %-22s %s  reason=%s support=%s"
                  % (v["subject"], v.get("value"), v.get("reason"),
                     (v.get("detail") or {}).get("support")))
    mg = [o for o in obs if o["quantity"] == "meter_glyph"]
    print("  meter_glyph observations:", len(mg))

    print("\n── 7. STUBS ───────────────────────────────────────────────────")
    print(" ", json.dumps(d.get("stubs")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
