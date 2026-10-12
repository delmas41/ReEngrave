"""ROADMAP 2.95 -- base vs arm on ONE saved GATHER: re-decide the identity
chain (`instrument`, `slot_index`, `part_partition` and what they read) with
this tree's code, once on the record's own margin labels (BASE) and once with
the shared-word rule applied to them (ARM), and write one row per staff.

    python3 probe_shared_word_2_95.py REC.json PROBE.json --out base.json
    python3 probe_shared_word_2_95.py REC.json PROBE.json --arm --out arm.json
    python3 probe_shared_word_2_95.py --diff base.json arm.json

PROBE.json is the output of a FRESH Surya read of the same pages (the margin
crops of every page, `between` as the worker now reports it); the labels both
arms decide on are the RECORD's own, so the only thing that differs is the
rule. A page whose record label is not a bare crook is not touched (a fresh
read of the same crop is not byte-identical: Surya drifts run to run).

A record this size (5.9 GB) is STREAMED, never loaded: only the observations
the chain wants are kept. ADJUDICATE only, GATHER fixed -- the change that is
being priced is a GATHER change (the reader), so this prices what the rule
does downstream of a label, not the reader's reach; the reach is the fresh
read in PROBE.json.

THE CONTROL THAT CAN FAIL: the BASE rebuild's `instrument`/`slot_index`
verdicts are compared with the saved record's. Anything but ~equal means the
replay dropped a prerequisite.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

JSON_DEC = json.JSONDecoder()


def stream_array(path, key, chunk=1 << 26):
    pat = ('"%s":[' % key).encode()
    f = open(path, "rb")
    tail, pos, start = b"", 0, None
    while True:
        b = f.read(chunk)
        if not b:
            return
        buf = tail + b
        i = buf.find(pat)
        if i >= 0:
            start = pos - len(tail) + i + len(pat)
            break
        tail = buf[-len(pat):]
        pos += len(b)
    f.seek(start)
    s, idx = "", 0
    while True:
        while idx < len(s) and s[idx] in ", \n":
            idx += 1
        if idx < len(s) and s[idx] == "]":
            return
        try:
            obj, end = JSON_DEC.raw_decode(s, idx)
            idx = end
            yield obj
            continue
        except json.JSONDecodeError:
            pass
        b = f.read(1 << 24)
        if not b:
            return
        s = s[idx:] + b.decode("utf8", "replace")
        idx = 0


def _chain():
    from tools.omr.staged import adjudicate, adjudicators  # noqa: F401
    from tools.omr.staged.record import Q
    adjudicate._ensure_decisions()
    chain = {Q.INSTRUMENT, Q.SLOT_INDEX, Q.PART_PARTITION}
    if os.environ.get("KEYS"):                  # 2.95 transposition follow-up
        chain |= {Q.KEY_SIGNATURE, Q.PART_KEY, Q.CLEF}
    todo = list(chain)
    while todo:
        spec = adjudicate.REGISTRY.get(todo.pop())
        if spec is None:
            continue
        for w in spec.wants:
            if w in adjudicate.REGISTRY and w not in chain:
                chain.add(w)
                todo.append(w)
    order = [q for q in adjudicate.ORDER if q in chain]
    keep = set()
    for q in order:
        keep.update(adjudicate.REGISTRY[q].wants)
        keep.add(adjudicate.REGISTRY[q].subjects_from or q)
    keep.discard(None)
    return adjudicate, order, keep


def _spread_for_record(rows, probe):
    """`{subject: (new text, shared word)}` for record labels the rule completes."""
    from tools.omr import staff_labels_surya as sls
    texts = collections.defaultdict(dict)       # (page, system) -> {ordinal: text}
    for r in rows:
        _, p, s, i = r["subject"].split("/")
        texts[(int(p), int(s))][int(i)] = r["value"]
    out = {}
    for pr in probe:
        key = (pr["page"], pr["system"])
        sidx = pr["staff_indices"]
        t = texts.get(key, {})
        between = []
        for b in pr["between"]:
            if b["upper"] in sidx and b["lower"] in sidx:
                between.append(dict(b, upper=sidx.index(b["upper"]),
                                    lower=sidx.index(b["lower"]),
                                    assigned_to=(sidx.index(b["assigned_to"])
                                                 if b.get("assigned_to") in sidx
                                                 else None)))
        new, shared = sls.spread_shared_words(t, between)
        for o, w in shared.items():
            out["staff/%d/%d/%d" % (key[0], key[1], o)] = (new[o], w)
    return out


def _replay(record, probe_path, arm):
    adjudicate, order, keep = _chain()
    from tools.omr.staged.record import Log, Q, Subject
    rows = [("obs", r) for r in stream_array(record, "observations")
            if r["quantity"] in keep]
    rows += [("abs", r) for r in stream_array(record, "abstentions")
             if r["quantity"] in keep]
    rows.sort(key=lambda t: t[1]["id"])
    swapped = {}
    if arm:
        probe = json.load(open(probe_path))
        swapped = _spread_for_record(
            [r for k, r in rows if k == "obs" and r["quantity"] == Q.MARGIN_LABEL],
            probe)
    log = Log()
    for kind, r in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            val = r["value"]
            if r["quantity"] == Q.MARGIN_LABEL and r["subject"] in swapped:
                val, w = swapped[r["subject"]]
                detail["shared_word"] = w
            log.observe(sub, r["quantity"], val, reader=r["reader"],
                        frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)
    log.freeze()
    adjudicate.run(log, order=order)

    gaps = {}
    if os.environ.get("KEYS"):
        from tools.omr.staged import inferences
        for g in inferences.part_key_census(log):
            gaps[g.staff.to_key()] = {"outcome": g.outcome, "value": g.value,
                                      "offset": (g.detail or {}).get("fifths_offset"),
                                      "tier": (g.detail or {}).get("tier")}
    saved = {}
    for v in stream_array(record, "verdicts"):
        if v["quantity"] in (Q.INSTRUMENT, Q.SLOT_INDEX):
            saved[(v["subject"], v["quantity"])] = (v["outcome"], json.dumps(
                v.get("value"), sort_keys=True), v.get("reason"))
    staves = []
    same = tot = 0
    for (sub, q), sv in saved.items():
        m = log.verdict(q, Subject.from_key(sub))
        cur = None if m is None else (m.outcome.value, json.dumps(
            m.value, sort_keys=True, default=str), m.reason)
        tot += 1
        same += int(cur == sv)
    for sub in sorted({k[0] for k in saved}):
        row = {"subject": sub}
        for q in (Q.INSTRUMENT, Q.SLOT_INDEX):
            m = log.verdict(q, Subject.from_key(sub))
            row[q] = None if m is None else {
                "outcome": m.outcome.value, "reason": m.reason,
                "value": (m.value.get("name") if isinstance(m.value, dict)
                          else m.value)}
        if os.environ.get("KEYS"):
            row["part_key_fill"] = gaps.get(sub)
            for q in (Q.KEY_SIGNATURE, Q.CLEF):
                m = log.verdict(q, Subject.from_key(sub))
                row[q] = None if m is None else {
                    "outcome": m.outcome.value, "reason": m.reason,
                    "value": m.value if not isinstance(m.value, dict) else str(m.value)}
        lr = log.rows(Q.MARGIN_LABEL, Subject.from_key(sub))
        row["label"] = lr[-1].value if lr else None
        staves.append(row)
    return {"record": record, "arm": arm, "n_swapped": len(swapped),
            "control_rebuilt_equals_saved": [same, tot], "staves": staves}


def _diff(a, b):
    A, B = json.load(open(a)), json.load(open(b))
    print("control base", A["control_rebuilt_equals_saved"],
          "arm", B["control_rebuilt_equals_saved"],
          "| labels completed in arm:", B["n_swapped"])
    bs = {s["subject"]: s for s in B["staves"]}
    named = collections.Counter()
    t = collections.Counter()
    changed_names = []
    for s in A["staves"]:
        n = bs[s["subject"]]
        for q in ("instrument", "slot_index"):
            x, y = s[q], n[q]
            fx = "None" if x is None else f"{x['outcome']}/{x['reason']}"
            fy = "None" if y is None else f"{y['outcome']}/{y['reason']}"
            if fx != fy or (x and y and x["value"] != y["value"]):
                t[(q, fx, fy)] += 1
            if (x and y and x["outcome"] == "decided" and y["outcome"] == "decided"
                    and x["value"] != y["value"]):
                changed_names.append((s["subject"], q, x["value"], y["value"]))
        named[("base", "slot_decided")] += int(
            bool(s["slot_index"] and s["slot_index"]["outcome"] == "decided"))
        named[("arm", "slot_decided")] += int(
            bool(n["slot_index"] and n["slot_index"]["outcome"] == "decided"))
        named[("base", "instrument_decided")] += int(
            bool(s["instrument"] and s["instrument"]["outcome"] == "decided"))
        named[("arm", "instrument_decided")] += int(
            bool(n["instrument"] and n["instrument"]["outcome"] == "decided"))
    print("staves", len(A["staves"]))
    for k, v in sorted(named.items()):
        print(" ", k, v)
    for (q, x, y), c in sorted(t.items()):
        print(f"{c:5d}  {q:10s} {x:44s} -> {y}")
    print("DECIDED -> DECIDED with a different value:", len(changed_names))
    for c in changed_names[:40]:
        print("   ", c)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record", nargs="?")
    ap.add_argument("probe", nargs="?")
    ap.add_argument("--arm", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--diff", nargs=2)
    a = ap.parse_args(argv)
    if a.diff:
        _diff(*a.diff)
        return 0
    res = _replay(a.record, a.probe, a.arm)
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(a.out, "control", res["control_rebuilt_equals_saved"],
          "swapped", res["n_swapped"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
