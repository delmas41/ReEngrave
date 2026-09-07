"""VERIFIER round 2 — independent recomputation of Agent II's tier-2 reach claims.
Fixtures live only in the MAIN checkout (the worktree gitignores them)."""
import json, glob, os, statistics as S
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), _os.pardir))
from fixture_root import fixture_glob, repo_glob, repo_root, add_repo_to_syspath  # noqa: E402
SCAN = ("benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json", "scan transcriptions")
ENG  = ("benchmarks/omr-orchestral-e2e/fixtures/*.omr.json", "engraved transcriptions")

def load(pat): return [(os.path.basename(f).split('.')[0], json.load(open(f))) for f in fixture_glob(*pat)]

# --- clef_weights null (R4 specialist inertness) ---
for lab, pat in (("scan", SCAN), ("engraved", ENG)):
    vals = {}
    staves = 0
    for nm, d in load(pat):
        vals[nm] = d.get("clef_weights", "<ABSENT>")
        for pg in d.get("pages", []):
            for sy in pg.get("systems", []): staves += len(sy.get("staves", []))
    nn = sum(1 for v in vals.values() if v not in (None, "<ABSENT>"))
    print(f"[clef_weights] {lab}: {len(vals)} files, non-null={nn}, staves={staves}, "
          f"distinct={set(map(str, vals.values()))}")

# --- tie pairing replay (R2.1) ---
def replay(pat, lab):
    tot = both = one = none = 0
    for nm, d in load(pat):
        for pg in d.get("pages", []):
            for sy in pg.get("systems", []):
                for st in sy.get("staves", []):
                    heads = []
                    ties = []
                    for m in st.get("measures", []):
                        for x in m.get("detections", []):
                            if x.get("category") == "notehead" and x.get("bbox_page"):
                                heads.append(x["bbox_page"])
                            elif x.get("class") == "tie" and x.get("bbox_page"):
                                ties.append(x["bbox_page"])
                    if not ties: continue
                    if heads:
                        nhw = S.median([h[2] for h in heads]); nhh = S.median([h[3] for h in heads])
                    else:
                        nhw = nhh = 0
                    win = nhw * 3
                    ytol = max(nhh * 3, 30)
                    for t in ties:
                        tot += 1
                        tx0, ty0, tw, th = t; tx1 = tx0 + tw; tcy = ty0 + th / 2
                        L = [h for h in heads if h[0] + h[2] <= tx0 + 1 and tx0 - (h[0] + h[2]) <= win
                             and abs(h[1] + h[3] / 2 - tcy) <= ytol]
                        Rr = [h for h in heads if h[0] >= tx1 - 1 and h[0] - tx1 <= win
                              and abs(h[1] + h[3] / 2 - tcy) <= ytol]
                        n = (1 if L else 0) + (1 if Rr else 0)
                        both += n == 2; one += n == 1; none += n == 0
    print(f"[ties] {lab}: detections={tot} both={both} one={one} none={none} "
          f"sum={both+one+none} unanchored={one+none} ({(one+none)/max(tot,1):.1%})")
replay(SCAN, "scan"); replay(ENG, "engraved")

# --- *_final staleness (R4.3) ---
for lab, pat in (("scan", SCAN), ("engraved", ENG)):
    staves = tsf = ksf = 0; meter_ch = 0
    for nm, d in load(pat):
        for pg in d.get("pages", []):
            for sy in pg.get("systems", []):
                for st in sy.get("staves", []):
                    staves += 1
                    if "time_signature_final" in st: tsf += 1
                    if "key_signature_final" in st: ksf += 1
                    prev = None
                    for m in st.get("measures", []):
                        ts = m.get("time_signature")
                        cur = (ts.get("numerator"), ts.get("denominator")) if ts else None
                        if cur is not None and prev is not None and cur != prev: meter_ch += 1
                        if cur is not None: prev = cur
    print(f"[*_final] {lab}: staves={staves} time_signature_final={tsf} "
          f"key_signature_final={ksf} surviving per-measure meter changes={meter_ch}")

# --- surya label tiers (R1.4) ---
from collections import Counter
tiers = Counter(); tot_lab = 0
for nm, d in load(SCAN):
    lt = ((d.get("contextual") or {}).get("label_tiers")) or {}
    for k, v in lt.items():
        if isinstance(v, int): tiers[k] += v; tot_lab += v
print(f"[label tiers] scan: {dict(tiers)} total={tot_lab} "
      f"surya share={tiers.get('surya',0)/max(tot_lab,1):.3f}")
