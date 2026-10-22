"""Duration-vs-pitch from ONE clean arm CSV. See run_one_arm.py for why the
arm must be scored in its own process.

Pitch mass is reported in two forms because one of the three Voicing-only
columns is arguable:
  * `wrong pitch`        (pitchnameedit/pitchtypeedit) -- unambiguously spelling
  * `pitch insert/delete`(inspitch/delpitch) -- a CHORD gained or lost a pitch;
    that is chord CONTENT, closer to a note ins/del than to a spelling error,
    so it is reported separately and not folded in silently.
  * `voice insert/delete` is voice STRUCTURE and is in neither family.
"""
import csv, os, sys, collections
DUR = ['wrong note head OMR-ED','wrong flag/beam OMR-ED','wrong dot OMR-ED',
       'wrong tuplet OMR-ED']
PITCH_CORE = ['wrong pitch OMR-ED','wrong accidental OMR-ED']
PITCH_WIDE = PITCH_CORE + ['pitch insert/delete OMR-ED']

def read(p):
    rows=list(csv.reader(open(p))); hdr=[h.strip() for h in rows[0]]; i=hdr.index('gtpath')
    out={}
    for r in rows[1:]:
        if len(r)<=i: continue
        g=r[i].strip()
        if not g.endswith('.musicxml'): continue
        out[os.path.basename(g).replace('.musicxml','')]={h:v.strip() for h,v in zip(hdr,r)}
    if not out: sys.exit(f"FATAL: 0 data rows parsed from {p}")
    return hdr,out
def num(v):
    try: return float(v)
    except Exception: return 0.0

hdr,rows = read(sys.argv[1])
label = sys.argv[2] if len(sys.argv)>2 else os.path.basename(sys.argv[1])
present = lambda c: c in hdr
tot=collections.Counter()
for n in rows:
    for c in hdr:
        if c.endswith('OMR-ED'): tot[c]+=num(rows[n].get(c,0))
print(f"=== {label}   ({len(hdr)} columns, {len(rows)} rows)")
missing=[c for c in PITCH_WIDE+DUR if not present(c)]
print(f"    Voicing-only columns present: "
      f"{[c for c in ['wrong pitch OMR-ED','pitch insert/delete OMR-ED','voice insert/delete OMR-ED'] if present(c)]}")
if 'wrong pitch OMR-ED' not in hdr:
    print("    ⚠️ NO `wrong pitch` COLUMN — this arm is CONTAMINATED or is not a Voicing arm.")
d = sum(tot[c] for c in DUR if present(c))
pc = sum(tot[c] for c in PITCH_CORE if present(c))
pw = sum(tot[c] for c in PITCH_WIDE if present(c))
print(f"    duration/head family      {d:8.0f}   ({', '.join(c.replace(' OMR-ED','') for c in DUR)})")
print(f"    pitch spelling (core)     {pc:8.0f}   (wrong pitch + wrong accidental)")
print(f"    pitch incl. chord content {pw:8.0f}   (+ pitch insert/delete)")
print(f"    RATIO duration : pitch(core) = {d/max(1,pc):6.2f} : 1")
print(f"    RATIO duration : pitch(wide) = {d/max(1,pw):6.2f} : 1")
for c in ['wrong direction OMR-ED','wrong note OMR-ED','entire measure insert/delete OMR-ED',
          'voice insert/delete OMR-ED']:
    if present(c): print(f"    {c.replace(' OMR-ED',''):34s}{tot[c]:9.0f}")
print(f"    TOTAL summed buckets      {sum(v for k,v in tot.items() if 'bad kern' not in k):8.0f}")
