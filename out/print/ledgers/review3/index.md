# lane-ledger-rungs round 3 review crops (2026-10-01)

Every truth-set head still wrong or abstaining after round 2's four fixes (gate, gap arithmetic, stub exclusion, per-page frame). Measurement/drawing only.

- `beethoven5-litolff-glyph-1-0-10-14-1.png` — glyph/1/0/10/14/1 (beethoven5-litolff, wrong): truth=[-1] geom=-2 rungs-after=-2. cause: rung matched as through-head but lands on the wrong ledger -- count or walk may be off by one rung
- `beethoven5-litolff-glyph-1-0-10-7-1.png` — glyph/1/0/10/7/1 (beethoven5-litolff, wrong): truth=[-2] geom=-3 rungs-after=-3. cause: classified as touching (space) but reference disagrees -- gap measurement or reference mapping
- `beethoven5-litolff-glyph-1-0-10-8-1.png` — glyph/1/0/10/8/1 (beethoven5-litolff, abstain): truth=[-2] geom=-3 rungs-after=None. cause: reader abstained -- no_rungs
- `beethoven5-litolff-glyph-1-0-3-7-3.png` — glyph/1/0/3/7/3 (beethoven5-litolff, abstain): truth=[-2] geom=-3 rungs-after=None. cause: reader abstained -- no_rungs
- `beethoven5-litolff-glyph-3-0-0-2-1.png` — glyph/3/0/0/2/1 (beethoven5-litolff, wrong): truth=[-6] geom=-7 rungs-after=-4. cause: rung matched as through-head but lands on the wrong ledger -- count or walk may be off by one rung
- `beethoven5-litolff-glyph-3-0-0-2-4.png` — glyph/3/0/0/2/4 (beethoven5-litolff, wrong): truth=[-7] geom=-7 rungs-after=-4. cause: rung matched as through-head but lands on the wrong ledger -- count or walk may be off by one rung
- `beethoven5-litolff-glyph-3-0-0-2-9.png` — glyph/3/0/0/2/9 (beethoven5-litolff, wrong): truth=[-5] geom=-6 rungs-after=-4. cause: classified as on-the-next-ledger (half-space rule) but reference disagrees -- gap measurement or reference mapping
- `beethoven5-litolff-glyph-3-0-0-6-2.png` — glyph/3/0/0/6/2 (beethoven5-litolff, wrong): truth=[-4] geom=-5 rungs-after=-5. cause: classified as touching (space) but reference disagrees -- gap measurement or reference mapping
- `beethoven5-litolff-glyph-3-0-0-7-2.png` — glyph/3/0/0/7/2 (beethoven5-litolff, wrong): truth=[-2] geom=-3 rungs-after=-6. cause: rung matched as through-head but lands on the wrong ledger -- count or walk may be off by one rung
- `beethoven5-litolff-glyph-3-0-7-0-7.png` — glyph/3/0/7/0/7 (beethoven5-litolff, wrong): truth=[-3] geom=-3 rungs-after=-2. cause: rung matched as through-head but lands on the wrong ledger -- count or walk may be off by one rung
- `beethoven5-litolff-glyph-3-0-7-3-1.png` — glyph/3/0/7/3/1 (beethoven5-litolff, abstain): truth=[-6] geom=-6 rungs-after=None. cause: reader abstained -- ambiguous gap 0.33 sp (between touching and half a space)
- `beethoven5-litolff-glyph-3-0-7-3-4.png` — glyph/3/0/7/3/4 (beethoven5-litolff, abstain): truth=[-6] geom=-6 rungs-after=None. cause: reader abstained -- ambiguous gap 0.28 sp (between touching and half a space)
- `beethoven5-litolff-glyph-3-0-8-9-0.png` — glyph/3/0/8/9/0 (beethoven5-litolff, wrong): truth=[11] geom=12 rungs-after=10. cause: rung matched as through-head but lands on the wrong ledger -- count or walk may be off by one rung
- `beethoven5-litolff-glyph-3-0-9-2-0.png` — glyph/3/0/9/2/0 (beethoven5-litolff, abstain): truth=[11] geom=12 rungs-after=None. cause: reader abstained -- no_rungs
- `beethoven5-litolff-glyph-3-0-9-3-5.png` — glyph/3/0/9/3/5 (beethoven5-litolff, abstain): truth=[11] geom=12 rungs-after=None. cause: reader abstained -- no_rungs
- `brahms1-breitkopf-glyph-1-1-8-4-4.png` — glyph/1/1/8/4/4 (brahms1-breitkopf, abstain): truth=[-2] geom=-2 rungs-after=None. cause: reader abstained -- no_rungs
  pixel-check issues: ['staff_line y=5990.0 coverage=0.17 MISS']
- `brahms1-breitkopf-glyph-1-1-8-5-0.png` — glyph/1/1/8/5/0 (brahms1-breitkopf, wrong): truth=[12] geom=12 rungs-after=10. cause: rung matched as through-head but lands on the wrong ledger -- count or walk may be off by one rung
  pixel-check issues: ['staff_line y=5990.0 coverage=0.12 MISS', 'staff_line y=6014.0 coverage=0.00 MISS', 'staff_line y=6043.0 coverage=0.17 MISS', 'staff_line y=6069.0 coverage=0.17 MISS', 'staff_line y=6097.0 coverage=0.15 MISS']
- `brahms1-breitkopf-glyph-1-1-8-6-0.png` — glyph/1/1/8/6/0 (brahms1-breitkopf, wrong): truth=[13] geom=13 rungs-after=11. cause: classified as touching (space) but reference disagrees -- gap measurement or reference mapping
  pixel-check issues: ['staff_line y=5990.0 coverage=0.00 MISS', 'staff_line y=6014.0 coverage=0.00 MISS', 'staff_line y=6043.0 coverage=0.10 MISS', 'staff_line y=6069.0 coverage=0.12 MISS', 'staff_line y=6097.0 coverage=0.12 MISS']
- `brahms1-breitkopf-glyph-1-1-8-7-4.png` — glyph/1/1/8/7/4 (brahms1-breitkopf, wrong): truth=[13] geom=13 rungs-after=14. cause: rung matched as through-head but lands on the wrong ledger -- count or walk may be off by one rung
  pixel-check issues: ['staff_line y=5990.0 coverage=0.00 MISS', 'staff_line y=6043.0 coverage=0.15 MISS', 'staff_line y=6069.0 coverage=0.12 MISS', 'staff_line y=6097.0 coverage=0.12 MISS']

## Cause counts
- 8: rung matched as through-head but lands on the wrong ledger -- count or walk may be off by one rung
- 5: reader abstained -- no_rungs
- 3: classified as touching (space) but reference disagrees -- gap measurement or reference mapping
- 1: classified as on-the-next-ledger (half-space rule) but reference disagrees -- gap measurement or reference mapping
- 1: reader abstained -- ambiguous gap 0.33 sp (between touching and half a space)
- 1: reader abstained -- ambiguous gap 0.28 sp (between touching and half a space)
