"""The apples-to-oranges list, each line DERIVED from a file the compare wrote (CLAUDE.md section 6: like with like).

python3 apples.py TAG BASE R SUMDIR "doc doc"      prints the section body.
"""
import hashlib
import json
import mmap
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prov_peek as PP                                    # noqa: E402

TAG, BASE, R, SUM, DOCS = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5].split()
import os
OUT = Path(os.environ.get("COMPARE_OUT") or R / ("overnight-%s" % TAG) / "compare")


def read(p):
    try:
        return Path(p).read_text()
    except OSError:
        return ""


def jl(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


n = 0


def L(s):
    global n
    n += 1
    print("%d. %s" % (n, s))


proc = read(SUM / "process.txt")
gather = [l.split()[0] for l in proc.splitlines() if re.match(r"OMR_\S+\s+\S+\s+\S+\s+YES", l)]
newflags = [l.split()[0] for l in proc.splitlines() if re.match(r"OMR_\S+\s+absent\s+\S+", l)]
gather_unscanned = re.findall(r"^\s+\+ (OMR_\S+)\s+GATHER", proc, re.M)
L("The TAG tree is NOT the BASE tree plus one change: %s. That is the point of the night, but it means no delta below has ONE cause; "
  "causes come from `readout diff` per family and the lanes' own reports." % (re.search(r"git log --oneline .*", proc).group(0) if re.search(r"git log --oneline .*", proc) else "see the process section"))
L("Flags that act in GATHER and did not exist (or were off) at BASE -- the records differ in what was SEEN, not only decided: %s%s" % (
    ", ".join(gather) or "none", ("; read-but-unscanned: " + ", ".join(gather_unscanned)) if gather_unscanned else ""))
L("Flags absent at BASE (the baseline lacked the mechanism entirely): %d (%s)" % (len(newflags), ", ".join(newflags[:30])))
base_cur = jl(R / ("overnight-%s" % BASE) / "compare" / "current.json")
base_re = jl(OUT / "base-rescored.current.json")
tag_cur = jl(OUT / "current.json")
if base_cur and base_re:
    diffs = []
    for doc in DOCS:
        a, b = (base_cur.get("summary") or {}).get(doc), (base_re.get("summary") or {}).get(doc)
        if a and b and a != b:
            for k in a:
                if a[k] != b.get(k) and k != "parts_named":
                    diffs.append("%s.%s" % (doc.split("-")[0], k))
    L("BASE as run (tree %s) vs the same BASE record re-exported by this tree (%s): %s" % (
        str(base_cur.get("tree"))[:9], str((tag_cur or {}).get("tree"))[:9],
        ("they DIFFER in " + ", ".join(diffs) + " -- exporter/acceptance changes move the headline with NO new gather; the middle column in the headline is the fair BASE") if diffs
        else "IDENTICAL headline (exporter/acceptance changes between the commits do not move these numbers)"))
else:
    L("BASE was not re-exported by this tree (base-rescored.current.json missing): the headline compares a record exported by the BASE tree with one exported by the TAG tree.")
L("Judged tiles: BASE and TAG both scored NOW by the same scorer on the same index (judged_compare.py), so the d51e3967c scorer change (written values incl. blue) cannot show up as a move. "
  "The numbers in the 20261022-night README (159/32/6 Litolff, 142/21/5 Brahms) were the old scorer and are NOT comparable with the ones above.")
L("Ranking and 'what changed in the file': both arms exported by THIS tree's exporter from the records' SAVED verdicts (no re-adjudication), so an exporter change between the commits is in neither delta. "
  "The ranking's page sample is the frozen one (benchmarks/lane-report/sample.json); 'whole movement' lines use every page holding staves. The '10-29 rank' column came from a DIFFERENT gather (main 1b47854a4, sample pages only) and is quoted, not recomputed.")
pk = read(SUM / "prov.txt")
m = re.search(r"SETTINGS/ENV difference.*", pk)
L("Settings/env: %s Provenance records only explicit env overrides (OMR_SURYA_KEEP_ALIVE) and CLI args, NOT the whole shell environment: an inherited OMR_* variable at BASE cannot be ruled out. "
  "The TAG process's environment snapshot: %s" % (("the provenance " + m.group(0)[:120].replace("SETTINGS/ENV difference", "settings/env difference").rstrip()) if m else "not read.", read(SUM / "env-snapshot.txt").strip() or "not captured (the gather had already exited)"))
wts = []
for tag in (BASE, TAG):
    for doc in DOCS[:1]:
        p = R / ("%s-mvt1-whole-%s.record.json" % (doc, tag))
        if p.exists():
            with open(p, "rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                wr = PP.tail_key(mm, b"weight_routing") or {}
            wts.append((tag, Path(wr.get("weights", "?")).name, wr.get("reason")))
same = len({w[1] for w in wts}) == 1
w0 = Path("/Users/seanjohnson/Desktop/ReEngrave/omr-weights") / (wts[0][1] if wts else "x")
L("Detector weights: %s; %s. %s" % ("; ".join("%s -> %s" % (a, b) for a, b, _ in wts), "same file name" if same else "DIFFERENT file",
                                  ("that file's mtime is %s (before both nights) -> unchanged on disk" % __import__("time").strftime("%F", __import__("time").localtime(w0.stat().st_mtime))) if w0.exists() else "weights file not found to date-check"))
L("Walls are single runs on a shared box: the overnight box load (other lanes, the web app, other agents) is not recorded, so a wall-minute delta of a few minutes is noise.")
sample = Path(__file__).resolve().parents[2] / "lane-report" / "sample.json"
L("Machine-local inputs not versioned here: the PDFs under library/ and omr-weights/ (same paths both nights); page range comes from each record's provenance args.pages (SETTINGS diff above).")
