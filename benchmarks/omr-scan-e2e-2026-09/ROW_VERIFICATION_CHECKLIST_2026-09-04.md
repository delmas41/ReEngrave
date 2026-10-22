# Six drafted rows, and the minutes each needs — 2026-09-04

Six candidate rows for the scan gate live in [works-drafts.json](works-drafts.json)
(full evidence per row in its `window.verified_by`). None of them touches the
gate: scan_eval.py reads only works.json, which is unchanged, and the pooled
production figure (results-round3-prodbase.json, 0.7517 / 7894) stands.

**Your job per row is only what is listed under "confirm".** Everything else —
reference trims, activity grids, pipeline counts, plate fingerprints — is
already run and recorded in the draft. Every page below chains from a window
you already verified, and four of the six carry the engraver's own measure
numbers, so most rows are "read two printed numbers off the page".

**To promote a row:** confirm its items, move the row from works-drafts.json
into works.json's `rows`, set `window.confidence` to `"verified"`, and note
what you confirmed in `verified_by` (VERIFICATION.md gets the story). The Bach
row REPLACES the parked works.json row with the same id — do not end up with
two. ⚠️ Do not move a row across with `confidence` still `"draft"`: scan_eval
runs any row with a complete window and then withholds the pooled figure while
any scored row is unverified — a half-promoted row takes the gate number away
from every session.

Viewing tip: `pdf_page_index` is 0-based. `open <pdf>` and go to PDF page
(index+1); the printed page number is also given so you know you are looking
at the right leaf.

---

## 1. beethoven-sym5-mvt1-984073-p2 — read three numbers (~2 min)

**PDF:** `library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf`, PDF page 3 (index 2, printed page "2").

**The draft claims:** mm **17–48** (32 measures; system 1 = 17–33, system 2 =
34–48). Two systems of 11 staves; same lineup as p.1 except **Violoncello and
Basso now share the bottom staff** (parts 16+17 on one staff).

**Confirm:**
1. The printed **17** above system 1's first bar and **34** above system 2's.
2. PDF page 4 (index 3) opens printing **49**.
3. The bottom string staff opens with the printed word "Basso" and is the only
   bass string staff — the condensed Vc+Cb (p.1 printed them separately).

**Flagged:** the pipeline reads system 1 as 16 bars — one short (it drops the
m19|m20 barline on this low-res raster; the high-res twin reads 17 and the
boundary fingerprint localizes the miss). The WINDOW is from the print; expect
`detected` 31/32 when the row runs. Nothing for you to resolve — just don't
let the pipeline's 31 shake the printed 32.

---

## 2. beethoven-sym5-mvt1-575951-p2 — one glance, right after row 1 (~1 min)

**PDF:** `...beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp575951.pdf`, PDF page 2 (index 1, printed page 2 — foot reads "2 SYMPHONY NO. 5 (1)").

**The draft claims:** same plates, same page break, same window **17–48** as
row 1. Staves `same-as` row 1.

**Confirm:**
1. Side by side with row 1's page: **same engraving** (any bar or two).
2. This printing has **no marginal measure numbers** (the 17/34 live only on
   the 984073 copy — recorded so nobody later "corrects" this row against a
   number that is not there).

**Already measured:** boundary fingerprint across the two scans agrees to
0.0024 of system width (16 boundaries, system 2) and 0.0018 (system 1), with
exactly one extra high-res boundary — the barline the low-res twin drops. Its
own pipeline run reads 17+15 unanimously, which chains 16→17…48 with no help
from the twin.

---

## 3. mahler-sym5-mvt1-local-p3 — read two numbers, count staves (~3 min)

**PDF:** `library/editions/mahler/symphony-5/mahler--symphony-5--unidentified-scan-2016--local.pdf`, PDF page 3 (index 2, printed page "4").

**The draft claims:** mm **9–16** (8 measures, one system). **13 five-line
staves + 2 one-line staves** (Becken, Gr. Tr.) — the lineup is
tacet-suppressed from p.2's 22. No staves map drafted (38 parts vs 13 staves);
OMR-NED only, like the verified p.2 row.

**Confirm:**
1. The printed **9** at the page's start (above Fag. 1/2, again above Erste
   Viol.) and **17** opening PDF page 4 (index 3).
2. **13 five-line staves**, margins: Fag.1/2, Contraf., F-Hörner 1/3/5,
   F-Hörner 2/4/6, B-Tromp.1/2, B-Tromp.3/4, Posaunen, Tuba, then strings
   (Erste/Zweite Viol., Violen, Vcelle., Bässe) — plus the two one-line rules
   for Becken and Gr. Tr.
3. Sanity glance: bars 1–4 near-silent (solo trumpet fanfare only), the big
   ff tutti at bar 5 with "nicht teilen!" over the strings — that is m13.

**Flagged:** nothing uncertain in the window. The condensation map is
deliberately not drafted; the row scores OMR-NED only until one is built
(notes in the draft carry a starting allocation from p.2's).

---

## 4. brahms-sym1-mvt1-317803-p2 — three numbers, one meter, one margin sweep (~4 min)

**PDF:** `library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf`, PDF page 2 (index 1, printed page "2").

**The draft claims:** mm **8–22** (15 measures; system 1 = 8–14 with 14
staves, system 2 = 15–22 with **13 staves — the 2 Trompeten in C staff is
suppressed**). First bar is the reference's 9/8 bar (m8), second bar returns
to 6/8.

**Confirm:**
1. The printed **8** over system 1 and **15** over system 2; PDF page 3
   (index 2) opens printing **23**.
2. The first bar prints **9/8**, the second **6/8** (this is the same m8 meter
   change whose cautionary signature closed p.1's window from the other side).
3. System 2's margins run Fl. / Ob. / Klar.(B) / Fag. / K-Fag. /
   (C) Hr. (Es) / Pk. / 1.Viol. / 2.Viol. / Br. / Vcl. / K.-B. — **no Trpt.**
   The horn pair and Pauken must be there: the reference has Eb Horn 4 and
   Timpani re-entering pp at mm 21–22, printed just before rehearsal A.

**Flagged — the one draft a tool got wrong:** draft_windows paired system 2's
misread 'Trumpet' margin (the printed **(Es) Hr.** staff) to '2 Trompeten in
C' and silently dropped the Es-horn staff — the documented
Hörner-in-Es→Trumpet lexicon misread, invisible because the pairing
"succeeded". The draft's `systems_as_printed.system_2` is the hand-corrected
mapping; item 3 above is what verifies the correction. The window itself was
drafted correctly and agrees with the print everywhere.

---

## 5. dvorak-sym9-mvt1-405834-p6 — count 7 bars on a resting staff (~4 min)

**PDF:** `library/editions/dvorak/symphony-9-op95/dvorak--symphony-9-op95--simrock-1894--imslp405834.pdf`, PDF page 6 (index 5, printed page "184").

**The draft claims:** mm **9–15** (7 measures, one system, 15 staves — the
1:1 lineup of p.183 continued, staves map copied verbatim from the verified
p.5 row).

**Confirm** (no printed numbers on this plate — this is the one row you count):
1. **7 bars**, counted on a staff that rests the whole page: Trombe in E
   (staff 7) or either Tromboni staff. (The automated band finder returns 0
   bands on this scan — faint lines — so your count is the ink witness.)
2. First bar = the **Violini I/II ff entry**, second bar adds **Timpani** —
   the exact m9/m10 predictions your p.5 verification used in the negative
   ("neither appears anywhere on the page" — well, here they are).
3. Last bar = the flute/oboe beamed flourish entering **p** over pp string
   tremolos (m15). An eighth bar would be a busy horn/viola bar (m16); there
   is none.
4. 15 staves, p.183's order (margins print only on p.183).

**Flagged:** the italic **"32"** over the Viola near the page's end is a
tremolo-subdivision marking (thirty-seconds, between two tied half notes) —
NOT a measure number. Recorded in the draft so it cannot mislead anyone later.
The measured-tremolo notation may matter for note-recall reading; it does not
touch the window.

---

## 6. bach-brandenburg3-mvt1-468678-p1 — the parked row, completed by a boxed 10 (~4 min)

**PDF:** `library/editions/bach/brandenburg-concerto-3-in-g-major-bwv1048/bach--brandenburg-concerto-3-in-g-major-bwv1048--edition-peters-nr-4412--imslp468678.pdf`, PDF page 1 (index 0, printed page 59).

**The draft claims:** mm **1–10** in the reference's numbering (pickup = m1,
print runs one behind). System 1 = pickup cell + printed 1–4 (ref 1–5, as the
parked row already established); system 2 = printed 5–9 (ref 6–10), **5
bars**, bounded by the boxed **10** opening PDF page 2. Two systems of **12**
staves (3 Vni, 3 Vle, 3 Vc, Cb, Cembalo×2).

**Confirm:**
1. The boxed **5** at system 2 (printed twice — over the strings block AND
   over the Cembalo block; the "three blocks" of the parked note are one
   system with the Cembalo set apart by a gap).
2. The boxed **10** opening PDF page 2 (index 1).
3. Count system 2's **5 bars** by eye (barlines shared across strings and
   Cembalo blocks).
4. **12 staves per system** — and correct the parked row's `n_staves: 13` to
   24 (page total) on promotion; VERIFICATION.md itself says 24 five-line
   bands, so the 13 was a first-pass eyeball slip.

**Flagged:** expectation, not uncertainty — the current pipeline shatters this
page (system 2 becomes four fragments reading 28/29/25/24 "bars"; stem columns
read as barlines once grouping broke). The row will score terribly and
honestly; stress is its purpose, along with being the corpus's only +1
numbering. Nothing about the window depends on the pipeline.

---

## What was drafted but NOT included, and why

- **Dvorak p.1-of-movement alternatives / other adjacent pages:** p.6 chains
  directly and keeps the 1:1 pairing; nothing else about 405834 is cheaper.
- **Further pages of each PDF (p.3s, p.7, …):** the same chaining works and
  the same printed numbers exist — once these six are verified, the next
  batch costs the same few minutes each. Not drafted now to keep this
  verification pass short.
- **No row was dropped for reference reach:** every window above was trimmed
  against its reference (trim_reference) and exists in full, with no
  unmatched repeats anywhere.
