# Nine drafted rows, and the minutes each needs — 2026-09-05

Nine candidate rows for the scan gate live in
[works-drafts-2.json](works-drafts-2.json) (full evidence per row in its
`window.verified_by`). None of them touches the gate: scan_eval.py reads only
works.json, which is unchanged, and the widened 10-row baselines
(WIDENED_BASELINE_2026-09-04.md: prior-prod 0.8457 / 29081, production
0.8387 / 29082) stand.

**Your job per row is only what is listed under "confirm."** Everything else —
reference trims, activity grids, pipeline counts, plate fingerprints — is
already run and recorded in the draft. Every page chains from a window verified
on 09-04 (or from an earlier row in THIS list, marked where so), and seven of
the nine carry the engraver's own measure numbers. **Every number you are asked
to read has a committed crop in [crops-2026-09-05/](crops-2026-09-05/)** — you
verified the last tranche entirely from such crops, and these are cut the same
way (400–450 dpi, clipped to the number and the bar it sits over). Open the
crop first; open the PDF only if a crop looks wrong.

**To promote a row:** confirm its items, move the row from works-drafts-2.json
into works.json's `rows`, set `window.confidence` to `"verified"`, and note
what you confirmed in `verified_by` (VERIFICATION.md gets the story). No row
here replaces an existing works.json row — all nine are new pages. ⚠️ Do not
move a row across with `confidence` still `"draft"`: scan_eval runs any row
with a complete window and then withholds the pooled figure while any scored
row is unverified.

⚠️ Two rows chain from OTHER DRAFTS in this file (marked below): 984073-p4
chains from 984073-p3, and mahler-p5 from mahler-p4. Verify those pairs in
order; a failed p3/p4 verification moves its successor's window too. (In both
cases the successor's own printed opening number would still pin it absolutely
— the chain is corroboration, not the only witness.)

Viewing tip: `pdf_page_index` is 0-based; `open <pdf>` and go to PDF page
(index+1). The printed page number is given per row so you know you are on the
right leaf.

---

## 1. beethoven-sym5-mvt1-984073-p3 — read three numbers (~2 min)

**PDF:** `library/editions/beethoven/symphony-5-op67/...imslp984073.pdf`,
PDF page 4 (index 3, printed page "3").

**The draft claims:** mm **49–82** (34 measures; system 1 = 49–64 with 11
staves, system 2 = 65–82 with **8 staves — Oboi, Trombe and Timpani
suppressed**).

**Confirm:**
1. The printed **49** above system 1 — crop
   [b984073-p3-sys1-opens-49.png](crops-2026-09-05/b984073-p3-sys1-opens-49.png)
   — and **65** above system 2 —
   [b984073-p3-sys2-opens-65.png](crops-2026-09-05/b984073-p3-sys2-opens-65.png).
2. PDF page 5 (index 4) opens printing **83** —
   [b984073-p4-sys1-opens-83.png](crops-2026-09-05/b984073-p4-sys1-opens-83.png).
3. System 2 has **8 staves**, margins Fl. / Cl. / Fag. / Cor. then four
   unlabeled string staves — no Ob., no Tr., no Tp.
4. Sanity glance (optional, 10 s): in system 1, bar 9 is an **empty G.P.
   bar**, bar 10 a **single ff chord**, bar 11 the **horns alone** — crop
   [b984073-p3-mm56-59-gp-chord-horncall.png](crops-2026-09-05/b984073-p3-mm56-59-gp-chord-horncall.png).

**Flagged:** nothing uncertain. The pipeline agrees with the engraver
unanimously (16+18), and the drafter's instrument pairing of the short system
was corroborated against the reference (the three dropped staves are exactly
the parts silent through mm 65–82).

---

## 2. beethoven-sym5-mvt1-575951-p3 — one glance, right after row 1 (~1 min)

**PDF:** `...imslp575951.pdf`, PDF page 3 (index 2, printed page 3).

**The draft claims:** same plates, same page break, same window **49–82**, same
11+8 staves as row 1.

**Confirm:**
1. Side by side with row 1's page: **same engraving** — crops
   [b575951-p3-mm56-59-same-engraving.png](crops-2026-09-05/b575951-p3-mm56-59-same-engraving.png)
   vs
   [b984073-p3-mm56-59-gp-chord-horncall.png](crops-2026-09-05/b984073-p3-mm56-59-gp-chord-horncall.png)
   (the same G.P. / chord / horn-call bars).
2. This printing has **no marginal measure numbers** at either system start —
   crops
   [b575951-p3-sys1-no-number.png](crops-2026-09-05/b575951-p3-sys1-no-number.png),
   [b575951-p3-sys2-no-number.png](crops-2026-09-05/b575951-p3-sys2-no-number.png)
   (recorded so nobody later "corrects" the row against a number that is not
   there).

**Already measured:** the boundary fingerprint across the two scans is the
cleanest of any page pair yet — every boundary matched, ZERO unmatched either
side, max disagreement 0.0014 of system width. Its own pipeline reads 16+18
unanimously, chaining 48→49…82 with no help from the twin.

---

## 3. beethoven-sym5-mvt1-984073-p4 — three numbers, one margin sweep (~3 min)
*(chains from row 1 — verify row 1 first)*

**PDF:** `...imslp984073.pdf`, PDF page 5 (index 4, printed page "4").

**The draft claims:** mm **83–112** (30 measures; 15+15). Both systems print
**11 staves but different lineups**: system 1 has **no Tp.** and splits the
bottom staff into **Vcl. and Basso**; system 2 has **Tp.** and re-condenses
the bottom staff, printed **"Bassi."**

**Confirm:**
1. The printed **83** over system 1 and **98** over system 2 — crops
   [b984073-p4-sys1-opens-83.png](crops-2026-09-05/b984073-p4-sys1-opens-83.png),
   [b984073-p4-sys2-opens-98.png](crops-2026-09-05/b984073-p4-sys2-opens-98.png)
   — and **113** opening PDF page 6 —
   [b984073-p5-sys1-opens-113.png](crops-2026-09-05/b984073-p5-sys1-opens-113.png).
2. System 1's margins: Fl. / Ob. / Cl. / Fag. / Cor. / Tr., then five string
   staves with the words **"Vcl."** and **"Basso"** printed at the two lowest —
   and **no Tp.** Crop:
   [b984073-p4-margins-sys1-no-Tp-split-VclBasso.png](crops-2026-09-05/b984073-p4-margins-sys1-no-Tp-split-VclBasso.png)
   (also shows the reference-predicted first bar: Viola rest / Vcl. notes /
   Basso rest at m83).
3. System 2's margins: Fl. / Ob. / Cl. / Fag. / Cor. / Tr. / **Tp.**, then
   four string staves, the lowest printed **"Bassi."** Crop:
   [b984073-p4-margins-sys2-with-Tp-Bassi.png](crops-2026-09-05/b984073-p4-margins-sys2-with-Tp-Bassi.png).

**Flagged — the one draft a tool got wrong in this tranche:** with 11 staves
in each system, draft_windows paired both positionally against p.2's 11-staff
lineup and silently put 'Timpani in C.G.' on the staff the print gives to
Violino I (it flagged only two staves). The row's `systems_as_printed` is the
hand-corrected mapping read off the print's margins — **item 2 and 3 above
verify the correction, not the drafter.** The lineup change is
reference-corroborated: Timpani's first note after m56 is m98, exactly the bar
system 2 opens on; and at m83 the reference has Vcl. sounding while Viola and
Basso rest — visible in the print's first bar (rest / notes / rest).

---

## 4. beethoven-sym5-mvt1-575951-p4 — one glance, right after row 3 (~2 min)

**PDF:** `...imslp575951.pdf`, PDF page 4 (index 3, printed page 4).

**The draft claims:** same plates, same window **83–112**, same
different-lineup 11+11 as row 3.

**Confirm:**
1. Side by side with row 3's page: **same engraving** (any bar or two).
2. No marginal measure numbers at either system start — crops
   [b575951-p4-sys1-no-number.png](crops-2026-09-05/b575951-p4-sys1-no-number.png),
   [b575951-p4-sys2-no-number.png](crops-2026-09-05/b575951-p4-sys2-no-number.png).
3. Same lineup facts as row 3 (no Tp. + Vcl./Basso split in system 1; Tp. +
   "Bassi." in system 2) — this scan's system 1 margins re-read at 200 dpi:
   [b575951-p4-margins-sys1-same-as-twin.png](crops-2026-09-05/b575951-p4-margins-sys1-same-as-twin.png).

**Flagged, nothing to resolve:** this scan's pipeline reads system 1 as **16
bars — one long**. The fingerprint localizes it: between the twin-shared
boundaries at 0.740 and 0.863 of the system, the twin (agreeing with the
printed 15) has ONE boundary and this scan has TWO — bars 12–13, mm 94–95,
the trumpets' f entry, a stem column read as a barline. Expect `detected`
31/30 when the row runs. (The twin pair now shows both failure directions on
the same plates: low-res loses a barline on p.2, high-res gains one on p.4.)
Also: this scan's text layer mis-anchors a 'Tp.' label onto system 1 — the
margins themselves (item 3) are what rule.

---

## 5. mahler-sym5-mvt1-local-p4 — two numbers, one counting strip (~2 min)

**PDF:** `library/editions/mahler/symphony-5/mahler--symphony-5--unidentified-scan-2016--local.pdf`,
PDF page 4 (index 3, printed page "5").

**The draft claims:** mm **17–23** (7 measures, one system). **18 five-line
staves + 3 one-line rules** (Becken, Gr. Tr., Kl. Tr.). Hoboen and Pauken are
back (vs p.3's 13 staves); Vcelle and Bässe are divisi ("get.") on two staves
each; no Tamtam rule yet.

**Confirm:**
1. The printed **17** at the page's start — printed twice: crops
   [mahler-p4-opens-17-top.png](crops-2026-09-05/mahler-p4-opens-17-top.png)
   (above Hoboen) and
   [mahler-p4-opens-17-strings.png](crops-2026-09-05/mahler-p4-opens-17-strings.png)
   (above Erste Viol.) — and **24** opening PDF page 5:
   [mahler-p5-opens-24-top.png](crops-2026-09-05/mahler-p5-opens-24-top.png).
2. **7 bars**, against the stamped strip
   [mahler-p4-counting-strip-mm17-23.png](crops-2026-09-05/mahler-p4-counting-strip-mm17-23.png)
   (ticks on barlines, numbers 17–23 over the bars).
3. The three one-line percussion rules read **Becken / Gr. Tr. / Kl. Tr.** —
   crop
   [mahler-p4-oneline-percussion-band.png](crops-2026-09-05/mahler-p4-oneline-percussion-band.png).

**Flagged:** the pipeline reads **8 cells per staff, unanimous — one more than
the printed 7**, and the unanimity is worthless in exactly the
0.8706-against-17 way (every staff shares the same phantom). It is localized:
each staff's first "cell" is a **59 px sliver** between the system's opening
rule and the clef (real bars are 404–671 px) — header furniture cut as a bar.
The window is from the print; expect `detected` 8/7. Don't let the pipeline's
8 shake the printed 7.

---

## 6. mahler-sym5-mvt1-local-p5 — two numbers (~2 min)
*(chains from row 5 — verify row 5 first)*

**PDF:** same, PDF page 5 (index 4, printed page "6").

**The draft claims:** mm **24–31** (8 measures, one system). **17 five-line
staves + 4 one-line rules** — Hoboen's staff is gone (silent from m21),
**Tamtam's rule appears** (its first note of the movement is m27).

**Confirm:**
1. The printed **24** at the page start — twice:
   [mahler-p5-opens-24-top.png](crops-2026-09-05/mahler-p5-opens-24-top.png),
   [mahler-p5-opens-24-strings.png](crops-2026-09-05/mahler-p5-opens-24-strings.png)
   — and **32** opening PDF page 6:
   [mahler-p6-opens-32-top.png](crops-2026-09-05/mahler-p6-opens-32-top.png).
2. **Four** one-line rules, now including **Tamtam** —
   [mahler-p5-oneline-percussion-band.png](crops-2026-09-05/mahler-p5-oneline-percussion-band.png)
   — and no Hoboen staff in the margins.

**Flagged:** nothing. This page has no header-sliver artifact; the pipeline's
8 agrees with the engraver. (PDF page 6 is a two-system page printing 32 and
41 — the 41 is a free anchor for a future row.)

---

## 7. brahms-sym1-mvt1-317803-p3 — three numbers, one double bar (~3 min)

**PDF:** `library/editions/brahms/symphony-1-op68/...imslp317803.pdf`,
PDF page 3 (index 2, printed page "3").

**The draft claims:** mm **23–37** (15 measures; system 1 = 23–28, system 2 =
29–37). Both systems print the **full 14-staff lineup — the Trpt. staff is
back** (p.2's system 2 had suppressed it), because the trumpets sound
mm 28–29 and nowhere else in the window.

**Confirm:**
1. The printed **23** over system 1 and **29** over system 2 — crops
   [brahms-p3-sys1-opens-23.png](crops-2026-09-05/brahms-p3-sys1-opens-23.png),
   [brahms-p3-sys2-opens-29.png](crops-2026-09-05/brahms-p3-sys2-opens-29.png)
   — and **38** opening PDF page 4:
   [brahms-p4-sys1-opens-38-allegro.png](crops-2026-09-05/brahms-p4-sys1-opens-38-allegro.png).
2. Both systems' margins are the full p.1 column (incl. **Trpt.**) — and the
   Trpt. staff's only notes are system 1's **last** bar + system 2's **first**
   (mm 28–29), rests everywhere else.
3. The page's **final barline is a double bar** (the introduction closes;
   the reference has the double bar at m37 and the Allegro at m38) — crop
   [brahms-p3-system2-final-doublebar.png](crops-2026-09-05/brahms-p3-system2-final-doublebar.png).

**Flagged:** the two documented lexicon misreads (K-Fag.→'Bassoon',
(Es) Hr.→'Trumpet') fired again as cross-check flags on both systems; the
positional placement stands, as on p.1/p.2 — nothing to correct.

---

## 8. brahms-sym1-mvt1-317803-p4 — three numbers, one repeat bar (~3 min)

**PDF:** same, PDF page 4 (index 3, printed page "4").

**The draft claims:** mm **38–58** (21 measures; system 1 = 38–47, system 2 =
48–58). The **Allegro** opens the page at m38; the **exposition start-repeat**
(reference: heavy-light + repeat at m40-left, end at m190) is printed after
the system's second bar.

**Confirm:**
1. The printed **38** (with **"Allegro"** over it) and **48** — crops
   [brahms-p4-sys1-opens-38-allegro.png](crops-2026-09-05/brahms-p4-sys1-opens-38-allegro.png),
   [brahms-p4-sys2-opens-48.png](crops-2026-09-05/brahms-p4-sys2-opens-48.png)
   — and **59** opening PDF page 5:
   [brahms-p5-sys1-opens-59.png](crops-2026-09-05/brahms-p5-sys1-opens-59.png).
2. The **heavy double bar with repeat dots after system 1's SECOND bar**
   (m39|40) — crop
   [brahms-p4-m39-40-repeat-doublebar.png](crops-2026-09-05/brahms-p4-m39-40-repeat-doublebar.png).
3. Full 14-staff lineup in both systems.
4. Bonus, 5 s, already cut: p.5's system 2 prints **70** with the boxed
   rehearsal **B** —
   [brahms-p5-sys2-opens-70-rehearsalB.png](crops-2026-09-05/brahms-p5-sys2-opens-70-rehearsalB.png)
   — 59+11=70 closes the arithmetic one page further (free anchor for a
   future p.5 row).

**Flagged:** the trim strips 21 unmatched repeat marks — that is the m40
start-repeat once per part (21 parts), end far outside the window; content
intact. "Allegro" is also printed over system 2 (a running reminder, not a
second tempo change). Same two lexicon flags as row 7; position stands.

---

## 9. dvorak-sym9-mvt1-405834-p7 — the counting row (~4 min)

**PDF:** `library/editions/dvorak/symphony-9-op95/...imslp405834.pdf`,
PDF page 7 (index 6, printed page "185").

**The draft claims:** mm **16–30** (15 measures; system 1 = 16–20 with 5
bars, system 2 = 21–30 with 10). First two-system page of this edition in the
table; same 15 staves per system in p.183's order. The Adagio's last bars
close into the **Allegro molto**: the reference has, all AT m24, a heavy-light
barline + exposition **start-repeat** + **2/4** + "Allegro molto" + MM ♩=136 —
printed at **system 2's fourth bar** (21+3 = 24).

**Confirm** (no printed numbers on this plate — this is the one row you count,
and the strips do the bookkeeping):
1. **5 bars in system 1** against
   [dvorak-p7-sys1-counting-strip-mm16-20.png](crops-2026-09-05/dvorak-p7-sys1-counting-strip-mm16-20.png)
   and **10 in system 2** against
   [dvorak-p7-sys2-counting-strip-mm21-30.png](crops-2026-09-05/dvorak-p7-sys2-counting-strip-mm21-30.png)
   — check the red ticks sit ON barlines, no bar skipped or doubled.
2. The **heavy double bar + repeat dots + 2/4 + "Allegro molto. M.M. ♩=136"**
   at system 2's fourth bar — crop
   [dvorak-p7-m23-24-doublebar-24-allegro-molto.png](crops-2026-09-05/dvorak-p7-m23-24-doublebar-24-allegro-molto.png).
   If the bar count were off by one either side, this complex would sit off
   m24, contradicting the reference.
3. The page's **first bar is the busy horn/viola/cello bar** (m16 — the very
   bar your p.6 verification confirmed was NOT on p.184), and the
   **trombones' first notes of the movement** land at system 1's fourth bar
   (m19; they rested through all of pp.183–184).
4. 15 staves per system, p.183's order (margins print only on p.183).

**Flagged:** the trim strips 15 unmatched repeat marks — the m24 start-repeat
once per part, end at m180; explained, content intact. The pipeline agrees
5+10 unanimously across all 30 staves.

---

## What was drafted but NOT included, and why

- **Mahler pdf index 5 (printed 7):** a two-system page printing 32 and 41 —
  chainable the same way, but the tranche already carries nine rows and an
  honest nine beats a rushed ten. Its opening number is already sighted (crop
  committed), so it is the cheapest next draft.
- **Brahms p.5 (printed 59–?):** same — its three anchors (59, 70+boxed B) are
  already sighted and cropped; next tranche.
- **Beethoven p.5s (113–?):** same chain, same economics.
- **Dvorak p.8:** the next Simrock page has no printed numbers either and its
  window would open mid-Allegro (m31) with no meter-change anchor mid-page —
  a pure counting row with thinner closure evidence; deferred until the
  cheaper rows are through.
- **No row was dropped for reference reach:** every window above trims cleanly
  (trim_reference), with the two repeat-strip counts explained per row.
