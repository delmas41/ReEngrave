"""How well does the dossier's part list join to a page's staves?

`dossier.join_parts_to_slots` is what lets the dossier speak about a page whose
staff count does not equal the work's part count — which is almost every
orchestral page, because printed scores condense (Flauti 1 and 2 onto one staff)
and divide (violins across several). It is the gate on all slot-level dossier
facts, and `benchmarks/omr-clef-geometry/PIPELINE_CLEF_RESULTS.md` records it as
the thing the last clef errors are waiting on.

`benchmarks/omr-key-signature/ground_truth.json` already carries a hand-read
instrument for every staff of two pages, so the join can be scored directly.

Three label conditions, because they separate two different failures:

  NO labels        what the join can do from score order alone
  PERFECT labels   whether the ALGORITHM is sound, given evidence
  REALISTIC        what it does with the labels these editions actually print
                   (winds and brass; the strings are never labelled — see
                   benchmarks/omr-margin-labels-2026-08/VISION_CEILING_2026-08-30.md)

    python3 benchmarks/omr-part-staff-join-2026-08/eval_join.py
"""
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.omr.dossier import join_parts_to_slots
from tools.omr.instruments import lookup

ROOT = Path(__file__).resolve().parents[2]
GT=json.load(open(ROOT/"benchmarks/omr-key-signature/ground_truth.json"))
WORK={"beet5-p2":"beethoven-sym5-mvt1","pastoral-p2":"beethoven-sym6-mvt1"}

def canon(name):
    m=lookup(name or "")
    return m.instrument.name if m else (name or "")

for page in GT["pages"]:
    pid=page["id"]
    if pid not in WORK: continue
    dossier=json.load(open(ROOT/f"data/dossiers/{WORK[pid]}.json"))
    truth=[s["instrument"] for s in page["staves"]]
    n=len(truth)
    print(f"\n=== {pid}: {len(dossier['parts'])} parts -> {n} staves ===")
    for arm, labels in (("NO labels", {}),
                        ("PERFECT labels (every staff)", {i:t for i,t in enumerate(truth)}),
                        ("REALISTIC (winds only, as printed)",
                         {i:t for i,t in enumerate(truth) if i < 6})):
        facts=join_parts_to_slots(n, dossier, labels or None)
        ok=anch_ok=anch=0
        rows=[]
        for i,(t,f) in enumerate(zip(truth,facts)):
            got=f["part"] if f else None
            good = got is not None and canon(got)==canon(t)
            ok+=good
            if f and f.get("anchored"):
                anch+=1; anch_ok+=good
            rows.append((i,t,got,good,bool(f and f.get("anchored"))))
        print(f"  {arm:<36} {ok}/{n} correct   (anchored {anch_ok}/{anch})")
        if arm.startswith("REALISTIC"):
            for i,t,got,good,a in rows:
                mark = "ok " if good else "XX "
                print(f"       {mark}slot {i:>2} {t:<22} -> {str(got):<22} {'anchored' if a else ''}")
