"""Assemble the night's README.txt (20261022-night README style) from what compare_20261029.sh wrote.

Mechanical only: every number is copied from a file the script made, none is typed here. The sections are
  headline lines (per plate: acceptance, judged, exported-file changes, first-two-stages families, ranking),
  "Surprising / worse" (RULE-DERIVED candidates: anything that got worse or that a control says is off -- a human still reads them),
  the process section (commits, flags, wall, settings, what is NOT recorded) and the apples-to-oranges list.
python3 readme_20261029.py TAG BASE R SUMDIR "doc doc"
"""
import json
import re
import sys
from pathlib import Path

TAG, BASE, R, SUM, DOCS = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5].split()
import os
OUT = Path(os.environ.get("COMPARE_OUT") or R / ("overnight-%s" % TAG) / "compare")
SHORT = {"beethoven5-litolff": "litolff", "brahms1-breitkopf": "brahms"}
NAME = {"litolff": "Litolff", "brahms": "Brahms "}
lines, worse = [], []


def P(s=""):
    lines.append(s)


def jload(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def head(cur, doc):
    s = ((cur or {}).get("summary") or {}).get(doc)
    if not s or s.get("status") != "ok":
        return None
    return dict(notes=s["notes_reaching_file"]["n"], of=s["notes_reaching_file"]["of"], frac=s["notes_reaching_file"]["fraction"],
                held=s["bars_held_out_sum"]["n"], red=s["bars_add_up_control"]["written_red"], addup=s["bars_add_up_control"]["exact"],
                unread=s["unread_bars"]["empty_bars_padded"], parts=s["parts_named"]["n"], partsof=s["parts_named"]["of"])


def arrow(a, b, fmt="%d"):
    return (fmt + " -> " + fmt) % (a, b)


def read(p):
    try:
        return Path(p).read_text()
    except OSError:
        return ""


base_cur = jload(R / ("overnight-%s" % BASE) / "compare" / "current.json")
base_re = jload(OUT / "base-rescored.current.json")
tag_cur = jload(OUT / "current.json")
slog = read(R / ("overnight-%s" % TAG) / "summary.txt")

P(read(SUM / "run-log.txt").splitlines()[0] if read(SUM / "run-log.txt") else "compare %s vs %s" % (TAG, BASE))
P()
P("== Manager summary (machine-assembled from the files named; rule-derived flags are CANDIDATES for a human reading)")
P("Acceptance (%s as run | %s re-exported by THIS tree | %s):" % (BASE, BASE, TAG))
for doc in DOCS:
    a, r, b = head(base_cur, doc), head(base_re, doc), head(tag_cur, doc)
    sh = NAME[SHORT[doc]]
    if not b:
        P("  %s: no %s acceptance result (see %s)" % (sh, TAG, OUT / "acceptance.log"))
        continue
    cmp_ = r or a
    if cmp_:
        P("  %s notes reaching file %d/%d -> %d/%d (%.3f -> %.3f); held-out bars %d -> %d; red bars %d -> %d; bars add up %d -> %d; unread bars %d -> %d; parts named %d/%d -> %d/%d" % (
            sh, cmp_["notes"], cmp_["of"], b["notes"], b["of"], cmp_["frac"], b["frac"], cmp_["held"], b["held"], cmp_["red"], b["red"],
            cmp_["addup"], b["addup"], cmp_["unread"], b["unread"], cmp_["parts"], cmp_["partsof"], b["parts"], b["partsof"]))
        if a and r and a != r:
            P("      (like with like = the middle column; the BASE as it was run on its own night differs from its re-export by: %s)" % (
                ", ".join("%s %s->%s" % (k, a[k], r[k]) for k in a if a[k] != r[k])))
        if b["held"]:
            worse.append("%s: %d bars HELD OUT (was %d)" % (sh, b["held"], cmp_["held"]))
        if b["red"] > cmp_["red"]:
            worse.append("%s: red bars UP %d -> %d" % (sh, cmp_["red"], b["red"]))
        if b["addup"] < cmp_["addup"]:
            worse.append("%s: bars that add up DOWN %d -> %d" % (sh, cmp_["addup"], b["addup"]))
        if b["notes"] < cmp_["notes"]:
            worse.append("%s: notes reaching the file DOWN %d -> %d" % (sh, cmp_["notes"], b["notes"]))
        if b["of"] != cmp_["of"]:
            P("      noteheads logged changed %d -> %d (GATHER saw a different number of heads)" % (cmp_["of"], b["of"]))
        if b["unread"] > cmp_["unread"]:
            worse.append("%s: unread bars UP %d -> %d" % (sh, cmp_["unread"], b["unread"]))

P("Sean's judged tiles, SAME current index, today's scorer on BOTH records (right/wrong/narrowed):")
for doc in DOCS:
    j = jload(OUT / ("judged-%s.json" % SHORT[doc]))
    if not j:
        P("  %s: not scored" % NAME[SHORT[doc]])
        continue
    mv = j["moves"]
    b, t = j["base"], j["tag"]
    P("  %s %d/%d/%d -> %d/%d/%d ; right->wrong %d, right->gone %d, wrong->right %d, unwritten->wrong %d, unwritten->right %d" % (
        NAME[SHORT[doc]], b.get("right", 0), b.get("wrong", 0), b.get("narrowed", 0), t.get("right", 0), t.get("wrong", 0), t.get("narrowed", 0),
        len(mv["worse"]), len(mv["lost"]), len(mv["better"]), len(mv["unwritten_wrong"]), len(mv["unwritten_right"])))
    if mv["worse"]:
        worse.append("%s: %d judged answers went RIGHT -> WRONG (must be 0): %s" % (NAME[SHORT[doc]], len(mv["worse"]),
                                                                                 "; ".join("%s tile %s" % (r["item"], r["tile"]) for r in mv["worse"][:6])))
    if mv["lost"]:
        worse.append("%s: %d judged answers went RIGHT -> gone (narrowed/abstained/not found)" % (NAME[SHORT[doc]], len(mv["lost"])))
    if mv["unwritten_wrong"]:
        worse.append("%s: %d judged answers went unwritten -> WRONG" % (NAME[SHORT[doc]], len(mv["unwritten_wrong"])))

P("What changed in the exported file (gained/lost by kind; place-matched, lane_report.diff_arms; BASE and TAG both exported by THIS tree from SAVED verdicts):")
for doc in DOCS:
    sh = SHORT[doc]
    for kind, label in (("all", "whole movement"), ("sample", "frozen sample pages")):
        t = read(OUT / "rank" / ("compare-%s-%s.txt" % (kind, sh))).strip().splitlines()
        if t:
            P("  %s %s:" % (NAME[sh], label))
            for l in t[1:4]:
                P("     " + l[:240])
        else:
            P("  %s %s: not produced" % (NAME[sh], label))

P("First two stages (GATHER + ADJUDICATE), readout diff per family (a diff exits 1 when the records differ -- that is its normal 'differences found', not a failure):")
for doc in DOCS:
    d = jload(OUT / ("%s-first-two-stages.json" % doc))
    if not d:
        P("  %s: no diff (see %s-diff.log)" % (NAME[SHORT[doc]], doc))
        continue
    ch = {}
    for c in d["changed_pairs"]:
        ch[c["family"]] = ch.get(c["family"], 0) + 1
    P("  %s: %d differences in all; provenance differences: %s" % (NAME[SHORT[doc]], d["n_differences"],
                                                                  json.dumps(d["provenance_differences"])[:300]))
    for fam, v in d["families"].items():
        mv = ch.get(fam, 0)
        if v["only_a"] or v["only_b"] or mv or v["gathered_a"] != v["gathered_b"] or v.get("class_changed"):
            P("     %-18s gathered %d -> %d, matched %d, only-BASE %d, only-TAG %d, pairs with a changed answer %d" % (
                fam, v["gathered_a"], v["gathered_b"], v["matched"], v["only_a"], v["only_b"], mv))
            if v["only_a"] or v["only_b"]:
                worse.append("%s %s: GATHER boxes only-BASE %d / only-TAG %d" % (NAME[SHORT[doc]], fam, v["only_a"], v["only_b"]))
    quiet = [fam for fam, v in d["families"].items() if not (v["only_a"] or v["only_b"] or ch.get(fam, 0) or v["gathered_a"] != v["gathered_b"])]
    P("     matched 1:1, nothing changed: %s" % ", ".join(quiet))

P("Abstention reasons that moved (old -> new; logs_diff.txt has all; decided verdicts that moved are listed there too):")
ld = read(SUM / "logs-diff.txt")
for blk in re.split(r"\n(?=== )", ld):
    if blk.startswith("== "):
        P("  " + blk.splitlines()[0][3:])
        rows = [l for l in blk.splitlines() if re.match(r"\s{4}\S+\s+\S+\s+\d+\s+\d+\s+[+-]\d+", l)]
        for l in rows[:14]:
            P("   " + l.strip())
        for l in blk.splitlines():
            if "DECIDED verdicts that moved" in l or l.strip().startswith("ABSTENTIONS"):
                P("   " + l.strip()[:300])
        ups = sorted(((int(r.split()[-1]), r) for r in rows), reverse=True)
        for dlt, r in ups[:3]:
            if dlt >= 200:
                worse.append("abstention reason grew by %+d: %s" % (dlt, " ".join(r.split())))

P("The 2.229 product ranking on the new records (fix-actions per page, biggest first; the '10-29 rank' column is FINDINGS.md quoted, not recomputed):")
for doc in DOCS:
    t = read(OUT / "rank" / ("rank-table-%s.txt" % SHORT[doc]))
    if t:
        for l in t.splitlines():
            P("  " + l)
            m = re.match(r"(.+?)\s{2,}([\d.]+)\s+([\d.]+)\s+([+-][\d.]+)", l)
            if m and "check load" not in m.group(1) and float(m.group(4)) > 0.5:
                worse.append("%s ranking: '%s' UP %.1f -> %.1f per page" % (NAME[SHORT[doc]], m.group(1).strip(), float(m.group(2)), float(m.group(3))))
    else:
        P("  %s: not produced" % NAME[SHORT[doc]])

P("Files (machine-local, %s):" % OUT)
for doc in DOCS:
    for ext in ("musicxml", "ly", "pdf"):
        f = OUT / ("%s.%s" % (doc, ext))
        P("  %s %s%s" % (doc, ext, "  %.1f MB" % (f.stat().st_size / 1e6) if f.exists() else "  MISSING"))
        if not f.exists() and ext != "ly":
            worse.append("%s.%s was not produced" % (doc, ext))
P()
P("Surprising / worse (rule-derived candidates; a human reads each against the print):")
if not worse:
    P("  - none of the rules fired: no held-out bars, no red-bar rise, no right->wrong, no judged loss, no GATHER box lost/gained, no reason up by 200+")
for w in worse:
    P("  - " + w)
P()
P("== Process: how we got it")
proc = read(SUM / "process.txt")
for blk in re.split(r"\n\n(?=== )", proc):
    first = blk.splitlines()[0] if blk.strip() else ""
    if first.startswith("== ROADMAP items"):
        ids = re.findall(r"^  (\d\.\d+[a-z0-9]*)\s", blk, re.M)
        P("== ROADMAP items named in commit subjects (%d; one line each, with the commit, in %s):" % (len(ids), SUM / "process.txt"))
        P("  " + " ".join(ids))
    else:
        P(blk.rstrip())
        P()
P()
P("-- the two runs, from their logs and records")
P(read(SUM / "logs-wall.txt").rstrip())
for blk in re.split(r"\n(?=== )", ld):
    if blk.startswith("== "):
        P(blk.splitlines()[0])
        for l in blk.splitlines()[1:]:
            if re.match(r"\s+(wall min|── |->|LOG warnings|TAG:)", l) or l.startswith("     ->"):
                P("  " + l.strip()[:230])
P(read(SUM / "prov.txt").rstrip())
P()
P("-- record size and what grew (record_growth.py; rows by array and quantity, ~bytes = len(json) of each row)")
P(read(SUM / "record-growth.txt").rstrip())
P()
P("What the logs and records do NOT carry, so it is not estimated here: per-stage wall time (the run prints none), detector or OCR call counts, ")
P("peak memory. Proxies that ARE recorded: pages, record size, row counts (above), EVALUATE fired/skipped and INFER inferred/skipped (logs_diff).")
P()
P("== Apples to oranges (read before believing any delta above)")
for l in read(SUM / "apples.txt").rstrip().splitlines():
    P(l)
(SUM / "README.txt").write_text("\n".join(lines) + "\n")
print("wrote", SUM / "README.txt", len(lines), "lines;", len(worse), "candidate(s) under Surprising / worse")
