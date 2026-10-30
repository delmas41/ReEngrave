"""The abstention-reasons table diffed, the stage counts, wall minutes and warnings, from the two nights' LOGS (no record is loaded).

The run log prints the ADJUDICATE `decided:` and `abstained:` dicts exactly as the record's top-level `adjudication` holds them,
plus the GROUPS / EVALUATE / INFER lines; summary.txt holds the wall minutes. Only reasons that MOVED are listed.
python3 logs_diff.py R BASE TAG [doc ...]       (R = library/_shared-records)
"""
import ast
import re
import sys
from pathlib import Path

R, BASE, TAG = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
DOCS = sys.argv[4:] or ["beethoven5-litolff", "brahms1-breitkopf"]


def parse(tag, doc):
    log = R / ("overnight-%s" % tag) / ("%s.log" % doc)
    out = dict(log=log, text="", decided={}, abstained={}, stages=[])
    if not log.exists():
        return out
    t = log.read_text(errors="ignore")
    out["text"] = t
    for line in t.splitlines():
        s = line.strip()
        for key in ("decided", "abstained"):
            if s.startswith(key + ":"):
                try:
                    out[key] = ast.literal_eval(s.split(":", 1)[1].strip())
                except (ValueError, SyntaxError):
                    pass
        if s.startswith("── EVALUATE") or s.startswith("── INFER") or s.startswith("── GROUPS"):
            out["stages"].append(s)
    return out


def wall(tag):
    p = R / ("overnight-%s" % tag) / "summary.txt"
    res = {}
    if not p.exists():
        return res, ""
    t = p.read_text()
    for m in re.finditer(r"^(\S+) pages (\S+) exit (\d+) wall (\d+) min", t, re.M):
        res[m.group(1)] = (int(m.group(4)), int(m.group(3)), m.group(2))
    head = t.splitlines()[0] if t else ""
    done = [l for l in t.splitlines() if l.startswith("done")]
    return res, head + ("  | " + done[-1] if done else "  | NOT DONE")


def main():
    wb, hb = wall(BASE)
    wt, ht = wall(TAG)
    print("wall (summary.txt)   BASE %s\n                     TAG  %s" % (hb, ht))
    for doc in DOCS:
        a, b = parse(BASE, doc), parse(TAG, doc)
        print("\n== %s" % doc)
        print("  wall min  BASE %s  TAG %s   (exit codes %s / %s)" % (wb.get(doc, ("?",))[0], wt.get(doc, ("?",))[0],
                                                                     wb.get(doc, ("?", "?"))[1], wt.get(doc, ("?", "?"))[1]))
        for st_a, st_b in zip(a["stages"], b["stages"]):
            if st_a != st_b:
                print("  %s\n     -> %s" % (st_a[:140], st_b[:140]))
        if not b["abstained"]:
            print("  (no TAG log / no abstained dict yet)")
            continue
        da, db = a["decided"], b["decided"]
        moved = [(q, da.get(q, 0), db.get(q, 0)) for q in sorted(set(da) | set(db)) if da.get(q, 0) != db.get(q, 0)]
        print("  DECIDED verdicts that moved (quantity: base -> tag): " + ("; ".join("%s %d -> %d" % x for x in moved) or "none"))
        aa, ab = a["abstained"], b["abstained"]
        rows = []
        for q in sorted(set(aa) | set(ab)):
            for reason in sorted(set(aa.get(q, {})) | set(ab.get(q, {}))):
                x, y = aa.get(q, {}).get(reason, 0), ab.get(q, {}).get(reason, 0)
                if x != y:
                    rows.append((abs(y - x), q, reason, x, y))
        tot_a = sum(v for d in aa.values() for v in d.values())
        tot_b = sum(v for d in ab.values() for v in d.values())
        print("  ABSTENTIONS %d -> %d; %d reasons moved, %d unchanged" % (
            tot_a, tot_b, len(rows), sum(len(d) for d in ab.values()) - len(rows)))
        print("    %-32s %-38s %8s %8s %8s" % ("quantity", "reason", "base", "tag", "delta"))
        for _d, q, reason, x, y in sorted(rows, reverse=True):
            print("    %-32s %-38s %8d %8d %+8d" % (q, reason, x, y, y - x))
        bad = [l.strip()[:200] for l in b["text"].splitlines()
               if re.search(r"warn|error|traceback|exception|failed|⚠", l, re.I)]
        bad_a = [l.strip()[:200] for l in a["text"].splitlines()
                 if re.search(r"warn|error|traceback|exception|failed|⚠", l, re.I)]
        print("  LOG warnings/errors (lines matching warn|error|traceback|exception|failed|warning sign): BASE %d, TAG %d" % (len(bad_a), len(bad)))
        for l in bad[:12]:
            print("    TAG: " + l)
        if not b["text"].strip():
            print("    (TAG log is empty)")


main()
