"""⚠️ A DISCRIMINATOR THAT DOES SEPARATE, found by opening the negative.

§5's negative is that a barline's ends are the CROP's, not the staff's. Turned
round, THAT IS THE SIGNATURE: a clipped barline reaches BOTH crop edges. It is
computable from the row (`d_top` ~ -4.0 and `d_bot` ~ +4.0 staff spaces, i.e.
the cell's own padding) and needs nothing new.

Scored against the crop pass's blind print verdicts on both publishers:
barlines as the positive class, the eye's own `stem_printed_*` heads as the
control. ⚠️ REACH first, and the two publishers APART.

⚠️⚠️ THE `too TALL` COLUMN IS CIRCULAR ON THE BARLINE ROW AND IS PRINTED
ANYWAY, LABELLED. The crop pass SAMPLED its 12 (Breitkopf) and 7 (Litolff)
adjudicated barlines FROM the `too TALL` bucket, so "100% of them are
`too TALL`" is true BY CONSTRUCTION OF THE SAMPLE and is not evidence. It is
printed because omitting it would leave a reader to assume it, and because the
STEM row of the same column is NOT circular: the 58 adjudicated stems were
sampled across all six buckets, and 1 of 58 is `too TALL`.

⚠️ The "spans the WHOLE cell" row is not circular in either direction -- it is
a FINER cut inside the bucket the barlines were sampled from, and the stems
were never selected on it at all. That is the one line here that is a
measurement rather than a restatement.

⚠️ The HEIGHT range is circular on the barline side (sampled at h > 8.0) and
not on the stem side, so the usable half of it is that the eye's stems top out
at 9.56 (Litolff) and 6.58 (Breitkopf).
"""
import json, sys

PAD, TOL = 4.0, 0.25   # the cell's reach, and how near an end must be to it

for f, label in (("litolff", "Litolff Beethoven 5 pp.1-4"),
                 ("breitkopf", "Breitkopf Brahms 1 pp.0-3")):
    d = json.load(open(f"benchmarks/omr-vertical-runs-2026-09/out/{f}.json"))
    pj = d.get("print_join") or {}
    if not pj:
        print(f"{label}: DEAD -- no print join in the artefact"); continue
    print(f"\n{label}")
    for name in ("barlines", "stems"):
        rows = [r for r in pj.get(name, ()) if r["n_runs"]]
        if not rows:
            print(f"  {name}: DEAD -- 0 joined to a run"); continue
        # the tallest run under the adjudicated head, as the arm recorded it
        hs = [r["h_spaces"] for r in rows if r.get("h_spaces")]
        # "reaches both crop edges" <=> its height is the whole cell, which is
        # 2*PAD + 4 staff spaces = 12.0. Expressed as a height test so it needs
        # only the row, never the staff lines it has already failed against.
        both = [r for r in rows if r.get("h_spaces")
                and abs(r["h_spaces"] - (2 * PAD + 4.0)) <= TOL]
        tall = [r for r in rows if r.get("outcome", "").startswith("too TALL")]
        print(f"  {name:<10} joined {len(rows):>3}   "
              f"h min {min(hs):.2f} median {sorted(hs)[len(hs)//2]:.2f} "
              f"max {max(hs):.2f}")
        print(f"  {'':<10} `too TALL`            {len(tall):>3} of {len(rows)}"
              f"  ({len(tall)/len(rows):.0%})")
        print(f"  {'':<10} spans the WHOLE cell  {len(both):>3} of {len(rows)}"
              f"  ({len(both)/len(rows):.0%})")
