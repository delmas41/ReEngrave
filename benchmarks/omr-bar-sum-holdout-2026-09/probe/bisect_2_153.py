"""ROADMAP 2.153 -- which commit moved a judged tile? Re-decide a small slice with the STAGED code AS OF each named commit
(git archive of `tools/` into a scratch dir; the record rows are the same), and print each commit's live reading of the
named tiles against Sean's. usage: bisect_2_153.py SLICE.json DOC SCRATCH_DIR SHA [SHA ...]"""
import json
import os
import subprocess
import sys

SL, DOC, SCR = sys.argv[1:4]
SHAS = sys.argv[4:]
ROOT = os.getcwd()
SCRIPT = os.path.join(ROOT, "benchmarks/omr-bar-sum-holdout-2026-09/probe/tag_notes_2_153.py")
res = {}
for sha in SHAS:
    d = os.path.join(SCR, "tree_" + sha)
    if not os.path.isdir(d):
        os.makedirs(d)
        p = subprocess.Popen(["git", "archive", sha, "tools"], stdout=subprocess.PIPE, cwd=ROOT)
        subprocess.check_call(["tar", "-x", "-C", d], stdin=p.stdout)
        p.wait()
        os.makedirs(os.path.join(d, "out"), exist_ok=True)
        os.symlink(os.path.join(ROOT, "out/2.153"), os.path.join(d, "out/2.153"))
        for extra in ("data", "docs", "library", "benchmarks"):
            if os.path.exists(os.path.join(ROOT, extra)):
                os.symlink(os.path.join(ROOT, extra), os.path.join(d, extra))
    out = os.path.join(SCR, "bis_%s_%s.json" % (DOC, sha))
    r = subprocess.run([sys.executable, SCRIPT, os.path.join(ROOT, SL), DOC, out, "base"], cwd=d, capture_output=True, text=True)
    print(sha, r.stdout.strip().splitlines()[-1:] if r.stdout else r.stderr[-300:], flush=True)
    res[sha] = json.load(open(out))["base"]
glyphs = sorted({g for s in res.values() for g, x in s.items() if not x.get("missing")})
print("%-22s" % "tile", " ".join("%-10s" % s[:8] for s in SHAS))
for g in glyphs:
    x0 = res[SHAS[0]].get(g, {})
    row = []
    for s in SHAS:
        x = res[s].get(g, {})
        if x.get("missing"):
            row.append("-")
            continue
        tag = "R" if x["right"] else "W"
        row.append("%s %s %s" % (tag, x["outcome"][:3], (x["reason"] or "")[:8]))
    print("%-22s" % ("%s %s" % (x0.get("item"), x0.get("n"))), " | ".join(row))
