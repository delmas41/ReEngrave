# What is this staff? — a multi-signal identity audit, measured

2026-09-04. Based on `a66f2569` (the condensed-parts merge on the local
integration line). Branch `claude/staff-identity-audit-2026-09-04`.
Specification: [`docs/staff-identity-audit-plan-2026-09-04.md`](../../docs/staff-identity-audit-plan-2026-09-04.md).

**MEASUREMENT ONLY. No pipeline behaviour changed, no classifier shipped, no
canonical benchmark result touched.** Everything here reads the scan
benchmark's already-committed `..graft09` transcriptions — no detector time was
spent, and the evidence is exactly what the shipped scan weights produced.

The audit emits one evidence row per staff per system over the 11-row scan
benchmark — **193 rows, 156 with hand-verified truth, 155 with an identity
truth** — and scores nine signals against it for identity, multiplicity and
continuity.

---

## The four answers, up front

| the question | the answer | the number |
|---|---|---|
| Does S3 (printed key vs the page's concert key) beat the S5 score-order prior alone? | **NO — killed by its own criterion, and by a mechanism worth keeping** | S3 exact **0.645** vs S5 **0.784**; head-to-head where both speak, S3 **28/48** vs S5 **46/48**. On BRASS — the class S3 exists for — S3 speaks on **2 of 36 staves (5.6%)** against the plan's ≥60% bar. |
| Does scoring the other signals WITHIN an S8 bracket block beat page-wide? | **YES, decisively — and it is the audit's one positive result** | Leave-one-out family prediction **0.857 within-block vs 0.039 page-wide**, Δ +0.818. Block boundaries are **22/22 precise** and 22/39 recalled. |
| Can multiplicity be answered without a dossier — does S7+S8+S9+S1-plurality reach a count rule that would not have cost Dvořák its +2,181? | **NO, and this is now a proof rather than a caution** | On 134 staves carrying the SAME printed section labels across the editions — 62 encoded as 1 part, 72 as >1 — **not one of eleven page-side signals separates them.** Every distribution overlaps; several run the wrong way. The best page-side ensemble scores **0.526**, worse than the shipped `always 1` baseline's **0.538**. |
| Where does it collapse to "labels remain the binding constraint"? | **Identity — exactly as CLAUDE.md already concludes for clefs** | S1 is the only identity signal with high precision (**0.982**) and its problem is COVERAGE (**0.710**). Nothing else rescues a staff S1 misses without also contradicting one it gets right, except the block frame — which supplies a family, not an instrument. |

---

## 0. The placement-convention survey (Phase 0) — and why it disqualifies itself

`probe_placement_survey.py` swept **all 1,745 reference encodings, 0 parse
failures, ~76 s** (`placement-survey.json`).

| question | measured |
|---|---|
| multi-staff parts | 1,192 of 7,118 parts; `<staves>` 2 → 1,170, 3 → 17, 4 → 4, 5 → 1. **The braced case is essentially N=2.** |
| `<direction>` total | 328,205. placement `below` 263,023 / `above` 51,505 / absent 13,677. Explicit `<staff>` child on 108,999 (33.2%) — but on 2-staff parts only **18 of 98,815** lack one. |
| the gap position | on 2-staff parts, **staff 1 + `below` = 58,813 of 98,815 (59.5%)**; restricted to dynamics + wedges, **51,465 of 64,511 (79.8%)**. `words` is NOT one-sided (above/1 5,431 vs below/1 5,342) — direction type matters. |
| duplication over section pairs | 960 consecutive same-stem part pairs. Dynamics: both parts 29,123 / first only 6,588 / second only 3,047 → **75% duplicated**. Wedges 61%. |
| cross-staff arcs | slurs **3,007 of 233,768 (1.29%)**, ties **4,504 of 141,443 (3.18%)**. Ownership is written on the NOTE (`<staff>`), never on the `<slur>`/`<tied>`. |
| by publisher | **it cannot be read this way.** `catalog.json` carries two `source` values for all 1,745 files — `gradus-assets` (1,185) and `gradus` (560) — and the encoder families are **MuseScore 1,269 · music21 387 · Finale 83**. Not one historical publisher appears. |

⚠️ **The survey measures ENCODING convention in modern digital files, not
printed-page convention in the historical editions the OMR reads.** All five
scan-benchmark works are MuseScore exports. The visible variation is by
**encoder**, not publisher — Finale writes `<staff>` on 99.0% of directions,
MuseScore 32.7%, music21 0.0% — and even the staff-1-below share moves with the
tool (Finale 46.2%, MuseScore 59.9%). So "79.8% of dynamics on a braced pair sit
in the gap" is a fact about MuseScore's default placement.

⚠️ **And the case S9 targets is barely in the ground truth at all.** Only 1,170
parts in the whole library are 2-staff, dominated by keyboard and harp
encodings; the orchestral references are almost entirely one staff per part. The
condensed wind pair on a conductor's page is precisely what these encoders
*un-condensed*.

Elaine Gould's *Behind Bars* is not on this machine (re-checked); nothing here
is attributed to it.

---

## 1. Identity scorecard

n = 155 staves with an identity truth; clef **read** on 138, **defaulted** on 17.

| signal | coverage | precision | spoke |
|---|--:|--:|--:|
| S1 margin label (pipeline reader) | 0.710 | **0.982** | 110 |
| S2 clef — reading accuracy | 0.890 | 0.848 | 138 |
| S2 clef — family narrowing | 0.890 | **0.993** | 138 |
| S3 key-signature offset — candidate set contains truth | 0.490 | 0.658 | 76 |
| S4 pitch envelope — range admits truth | 0.748 | 0.819 | 116 |
| S5 score-order prior — set contains truth | 0.626 | 0.753 | 97 |
| S6 slot/layout instrument (**fused**, not independent) | 0.729 | 0.956 | 113 |

Conditioned on the clef, as the plan requires (S3 and S4 inherit S2's errors
through the pipeline):

| signal | clef READ | clef DEFAULTED |
|---|---|---|
| S1 | 0.979 (94) | 1.000 (16) |
| S3 | 0.676 (74) | **0.000 (2)** |
| S4 | 0.806 (108) | 1.000 (8) |
| S5 | 0.747 (95) | 1.000 (2) |

⚠️ The defaulted column is too small to read as a rate (2–16 staves) — what it
shows is that **S3's two defaulted-clef staves are both wrong**, which is the
documented dependency behaving exactly as documented, not a measurement.

**What each signal ADDS over the cheapest one it could replace** (S5, free and
positional):

| signal | rescued | contradicted a correct S5 | net |
|---|--:|--:|--:|
| S3 | 26 | 15 | **+11** |
| S4 | 50 | 12 | +38 |
| S1 | 54 | **0** | **+54** |

S1 is the only signal that never contradicts a correct cheaper one.

---

## 2. S3 — the kill criterion, and the mechanism behind it

**S3 fails the criterion the plan stated in advance.**

| | spoke | exact | precision | "does it transpose" |
|---|--:|--:|--:|--:|
| S3 implied offset | 76 | 49 | **0.645** | 0.658 |
| S5 order prior | 97 | 76 | **0.784** | 0.845 |
| head-to-head, both speaking | 48 | S3 **28** / S5 **46** | | |

But the reason is sharper than the ratio, and it is the finding worth keeping.

### A transposing brass staff prints NO key signature, so S3 is silent on exactly the staves it exists for

Coverage by family, strict arm:

| family | n | S3 spoke | coverage | precision |
|---|--:|--:|--:|--:|
| woodwind | 51 | 35 | 0.686 | 0.600 |
| **brass** | 36 | **2** | **0.056** | 1.000 |
| string | 53 | 35 | 0.660 | 0.686 |
| percussion | 12 | 2 | 0.167 | 0.000 |

The truth offsets on the 155 staves are `{0: 126, +2: 11, +3: 9, −4: 4, −3: 3,
+1: 2}` — **29 genuinely transposing staves**. S3 read a printed signature on
**three** of them. In this repertoire a natural horn or trumpet part is engraved
with an *empty* key signature and its accidentals written inline; the timpani
likewise. The reader is not failing — there is nothing printed to read.

### The corroboration arrived from the other direction, in the truth itself

The reference-derived-truth control (`build_evidence.validate_reference_truth`)
compares the hand-read clef and key of the 24 staves that carry both against the
Gradus reference's own written values:

* **clef 24/24 agree** — reference-derived clef truth is validated, and is what
  extends clef truth to the 125 staves works.json does not hand-read.
* **key 20/24 agree**, and all four disagreements are the same class:
  `Trombe in C` and `Timpani in C.G.` hand-read **0** on the page and are
  encoded **−3** in the file.

⚠️ **So reference-derived KEY truth is wrong for precisely the staves S3 is
about, and it is not used for them.** The page prints no signature; the encoder
supplies the concert one. This is a second instance of the condensed-parts
lesson — the encoding and the engraving disagree, and only one of them is what
a reader sees.

### The obvious repair was measured and is REFUSED

If an unread signature were taken at face value as an empty printed one, S3
would speak on 140 of 155 instead of 76. Measured:

| arm | spoke | exact | precision | on transposing staves |
|---|--:|--:|--:|--:|
| strict (`key_signature_read`) | 76 | 49 | **0.645** | 2/3 |
| permissive (unread ≡ empty) | 140 | 57 | **0.407** | 10/26 |

Coverage nearly doubles and precision falls by a third; the transposing arm
lands at 0.385. The permissive arm collects every genuine read failure as a
false transposition. Recorded refused, with the numbers.

⚠️ And the mechanism has a floor under it: `signed_fifths` returns **0** both
for "C major printed" and for "nothing read". **A printed empty signature and a
failed read are the same bytes in the transcription** — `key_signature_read` is
the only thing separating them, and it is a property of the reader, not of the
page. Any future S3 needs the pipeline to distinguish *this staff prints no
signature* from *I could not read this staff*, and it does not today.

---

## 3. S8 — the one positive result

**The bracket block is the right frame, and it is free.** `Staff.group_index` is
already computed by `system_grouping._assign_groups` and surfaced in the
transcription as `contextual.reference[slot].group`; nothing downstream reads it
for identity.

Leave-one-out family prediction — predict a staff's family from the modal family
of the OTHER members of its group, versus of the other staves on its page.
Neither ever sees the staff being predicted:

| frame | correct | n | accuracy |
|---|--:|--:|--:|
| page-wide | 6 | 155 | **0.039** |
| **within block** | 132 | 154 | **0.857** |

(Exact instrument under the same protocol: 0.000 page-wide vs 0.156 in-block —
a block supplies a FAMILY, not a name.)

**Block boundaries are precise and under-recalled**, which is the veto shape
this repo keeps arriving at:

| | value |
|---|--:|
| true family boundaries hit | 22 |
| true family boundaries | 39 |
| **recall** | **0.564** |
| boundaries predicted | 22 |
| **precision** | **1.000** |

Every bracket boundary the grouper finds is a real family boundary — on 12
systems across 5 publishers it never split a family in two. It finds a little
over half of them: Brahms 1 is read as **2 blocks against 4 truth family runs**
on all three of its systems, Beethoven 5 as 3 against 5.

⚠️ **Do not read "0.039 page-wide" as a claim that vertical position is
useless.** It is the accuracy of one specific estimator — the modal family of
the rest of the page — which on a conductor's score is a coin-flip between
winds and strings by construction. The S5 order prior, which uses position
properly, scores 0.753. The comparison is between two FRAMES for the same
estimator, and that is what it says.

Block purity, for completeness: 34 blocks, **20 fully family-pure (58.8%)**,
mean purity **0.877** — just under the plan's ≥90% bar, and the shortfall is
the same under-recall (a block that merges winds and brass is impure but has
made no wrong split).

---

## 4. Multiplicity — the question Sean most wants answered

**Answer: no page-side rule reaches the count, and the reason is that the
distinguishing fact is not on the page.** That was the condensed-parts session's
conclusion from one rule's failure; this is the same conclusion from a
distributional test over eleven signals.

Truth over 156 staves: `{1: 84, 2: 68, 3: 3, 4: 1}`.

| rule | spoke | exact | over | under | accuracy |
|---|--:|--:|--:|--:|--:|
| **always 1** (shipped default; what Audiveris does too) | 156 | 84 | 0 | 72 | **0.538** |
| S7 texture: ≥1 dyad or divisi bar ⇒ 2 | 156 | 76 | 60 | 20 | 0.487 |
| S7 stricter: ≥25% of note bars carry a dyad ⇒ 2 | 156 | 90 | 37 | 29 | 0.577 |
| S8 block size > 1 ⇒ 2 | 156 | 69 | 83 | 4 | 0.442 |
| S8 brace detected ⇒ 1 | 18 | 5 | 0 | 13 | 0.278 |
| S9 dynamic in the gap nearer the neighbour ⇒ 2 | 156 | 85 | 10 | 61 | 0.545 |
| **S1 label plurality (CEILING: hand-read string)** | 156 | 131 | 23 | 2 | **0.840** |
| **S7+S8+S9+S1 combined (any says >1)** | 156 | 82 | 70 | 4 | **0.526** |
| S7 AND S1 (both must agree on >1) | 156 | 126 | 10 | 20 | 0.808 |

**The page-side ensemble is worse than doing nothing** (0.526 against 0.538),
and worse than the label rule alone. Adding S7/S8/S9 to S1 makes it worse in
both directions: the OR-ensemble converts S1's 131 exact into 82, and the
AND-ensemble converts them into 126.

⚠️ There is no PIPELINE-reader arm for the label rule here, and that is a real
limit: the transcription retains the RESOLVED instrument, not the raw margin
string, and `players_for_label` needs the string (`2 Flöten` → 2 is invisible
once it has become `Flute`). The reader's own accuracy was measured by the
condensed-parts session (`probe_real_labels.py`, 12/12 on Beethoven 984073 p1)
and is not re-derived. Every S1 row above is therefore the CEILING arm.

Per row, the two Dvořák rows are the test:

| row | always 1 | S1 label | S7 stricter | S7 AND S1 | combined | S9 |
|---|---|---|---|---|---|---|
| dvořák p5 | **15/15** | 7/15 **+8** | 11/15 +4 | 11/15 +4 | 4/15 **+11** | 15/15 |
| dvořák p6 | **15/15** | 7/15 **+8** | 8/15 +7 | 10/15 +5 | 4/15 **+11** | 15/15 |
| beethoven 984073 p1 | 6/12 −6 | **12/12** | 6/12 −6 | 7/12 −5 | 7/12 +5 | 5/12 |
| brahms p1 | 7/14 −7 | **14/14** | 10/14 +4 | **14/14** | 7/14 +7 | 5/14 |
| mahler p2 | 5/17 −12 | 8/17 +7−2 | 4/17 +3−10 | 6/17 +1−10 | 9/17 +4−4 | 6/17 −11 |

S9 scores 15/15 on both Dvořák rows by **staying silent**, not by knowing
anything — Dvořák's truth is all-1s, so any silent rule is perfect there. That
is the trap, and the next section is the test that avoids it.

### The proof: matched printed labels, and eleven signals that cannot tell them apart

`probe_matched_labels.py` pairs staves carrying the **same printed section
label** across editions and asks whether any page-side signal separates the
truth-1 members from the truth-2 members. **62 staves encoded as 1 part, 72 as
>1, same labels.**

| signal | 1-part range (median) | >1-part range (median) | separates? |
|---|---|---|---|
| S7 bars carrying a dyad | 0..8 (1) | 0..11 (2) | no |
| S7 bars with stems both ways | 0..2 (0) | 0..2 (0) | no |
| S7 rest-only bars | 0..11 (1) | 0..16 (5) | no |
| S7 bars carrying notes | 0..16 (7) | 0..14 (6) | no |
| S8 bracket-block size | 4..6 (5) | 3..9 (4) | no |
| S8 brace detections | 0..1 (0) | 0..1 (0) | no |
| S9 dynamics filed here | 0..13 (3) | 0..16 (3) | no |
| S9 dynamics in the gap, nearer the neighbour | 0..3 (0) | 0..2 (0) | no |
| S9 arcs reaching a neighbour's band | 0..1 (0) | 0..7 (0) | no |
| S4 largest interior pitch gap | 0..20 (4) | 0..32 (5) | no |
| S4 notes read | 0..55 (26) | 0..72 (14) | no |
| S7 dyad SHARE of note bars | 0.0..1.0 | 0.0..1.0 | no |
| S7 divisi SHARE of note bars | 0.0..0.5 | 0.0..0.333 | no |
| S9 ambiguous SHARE of dynamics | 0.0..0.667 | 0.0..1.0 | no |

**Not one is disjoint, and four run the wrong way** — the 1-part staves have
MORE notes (median 26 vs 14), a WIDER divisi share and a wider ambiguous-dynamic
share than the 2-part staves. That is not a weak signal; it is the absence of
one.

The worked case is the Viola. `Viola` / `Bratsche` is **one** part in the
Litolff Beethoven, the Simrock Dvořák and the Breitkopf Brahms, and `Violen` is
**two** in the Peters Mahler. `Violino I` is one part in three editions;
`Erste Violinen` is two, and `Zweite Violinen` is **three**. Nothing on those
pages differs. The number is the encoder's decision.

⚠️ **No combiner over these nine signals can succeed, and that is a statement
about the signals rather than about the search over them.** A dossier — or an
explicit encoding convention supplied by the operator — remains the only source
of the count. The oracle arm's **−4,557 edits stands as a ceiling with no
page-side route to it.**

---

## 5. Continuity — and one thing the exporter is leaving on the floor

Four rows have more than one system. Slot continuity, checked against the
printed truth (do two staves sharing a slot carry the same instrument?):

| row | system sizes | shared slots | same instrument | different |
|---|---|--:|--:|--:|
| beethoven 984073 p2 | 11, 11 | 11 | **11** | 0 |
| beethoven 575951 p2 | 11, 11 | 11 | **11** | 0 |
| **brahms p2** | **14, 13** | 13 | **12** | **1** |
| bach p1 | 12,3,3,3,1,2 | 0 | — | — (no truth) |

⚠️ **Brahms 1 p.2 is the interesting one.** Its two systems disagree about staff
count (14 then 13, because system 2 suppresses the tacet trumpets), which is
exactly the case where `export._stitch_slots` **refuses** the ordinal join — and
the condensed-parts session measured that refusal costing that row 27 fragments
against a truth of 21. But the slot ALIGNER, a different mechanism, is **12 of
13 right on the same page**: it inserts the gap one staff early, giving
`4 Hörner in Es 3./4.` the trumpets' slot and leaving the horn slot empty, and
gets every other staff right.

So the exporter's conservatism is not calibrated to the aligner's accuracy on
the one corpus page that exercises it. The condensed-parts session already
measured what closing it is worth on that row: **`slot stitch` + `condensed
split` together take it from 6,562 edits / ES 715 to 6,200 / ES 0 at the truth's
own part count of 21.** ⚠️ That is one row, and its single error is adjacent to
the omitted staff — the failure mode a wider corpus would be needed to price.

Bach Brandenburg 3 p.1 segments as **six "systems" of sizes [12, 3, 3, 3, 1, 2]**
on a page that prints one. No signal in this audit is meaningful on that row and
none is scored there; it is a phase-1 segmentation failure, not an identity one.

---

## 6. S9 — the signal that could not be priced, and why that is the finding

S9 was Sean's addition and the audit could not price it, for three independent
reasons, each of which is itself a measurement:

1. **The detector emits zero hairpins on this corpus.**
   `dynamicCrescendoHairpin` and `dynamicDiminuendoHairpin` are in the DSv2
   class space; across all 11 scan pages and 17,079 detections the count is
   **0**. CLAUDE.md's `KNOWN_GAPS` already records hairpins as 6 in the truth /
   4 detected on the *engraved* benchmark; on scans it is 0 detected. "A hairpin
   drawn once between a braced pair" cannot be evidence on a page where no
   hairpin is found.
2. **The placement convention the survey measured is a MuseScore artifact**
   (§0), so calibrating a gap rule on it would be calibrating on the encoder.
3. **The dynamics that ARE detected do not separate** (§4): the share of a
   staff's dynamics that land in a contested gap is no different between 1-part
   and 2-part staves, and its range is wider on the 1-part side.

⚠️ What the audit CAN say is that the ownership ambiguity is real but small on
this corpus: **29 of 554 dynamics (5.2%)** sit in a shared gap closer to the
neighbouring staff than to the one they were filed under, and **44 arcs** reach
into a neighbour's band. Those are the marks with no arbitration today. Fixing
their *ownership* is a rendering-correctness question worth its own
measurement; it is not a multiplicity signal.

⚠️ Also honest: S9 here measures whether a mark the PIPELINE already gave to a
staff is printed in a contested gap. It is not an independent re-attribution,
because nothing in the pipeline arbitrates these marks — which is the taxonomy
doc's point, restated with a count.

---

## 7. What I would build next, and what I would refuse

**Build — S8 as a family frame, as a VETO.** It is free (already computed,
already in the JSON), its boundaries are 22/22 precise, and it lifts family
prediction 0.039 → 0.857 leave-one-out. The natural shape is the one this repo
keeps landing on: a bracket block **vetoes** a cross-family assignment inside
it, never proposes one. Concretely — `contextual`'s layout fit and
`_dedupe_cross_staff_detections`'s range veto should both be scored within the
block instead of across the page. ⚠️ Price it against the pooled scan figure
before shipping; §3's numbers are about a family label, not about edits, and
this audit deliberately did not run the exporter.

**Build — separate "no key signature printed" from "no key signature read."**
A one-field change in the transcription, and the precondition for any future S3,
for the reference-truth mismatch in §2, and for a reader that can say a brass
staff is *correctly* empty. Its value is not measured here and should not be
assumed to be S3's.

**Investigate — the Brahms p2 stitch refusal (§5).** The aligner is 12/13 where
the exporter refuses outright, and closing it was already priced at −362 edits
and ES 715 → 0 on that row. One row is not a corpus; what is needed first is
more multi-system scan rows, not more logic.

**Refuse — S3 as an identity signal.** It fails its stated kill criterion by
every reading (exact 0.645 vs 0.784; head-to-head 28/48 vs 46/48; brass coverage
5.6% against a 60% bar), and the permissive repair measures worse (0.407).

**Refuse — any page-side multiplicity rule, including the ensemble Sean hoped
for.** §4's matched-label test is the reason: 62 vs 72 staves under identical
printed labels and **not one of eleven signals separates them**. The label rule
is the best page-side estimator at 0.840 and it is the one already shipped
default-OFF for costing Dvořák +2,181. `OMR_CONDENSED_PARTS` still wants an
oracle.

**Refuse — calibrating S9 on the reference encodings.** §0.

**Deliberately not done, with the reason.** The plan offers two secondary
identity corpora and neither would move a conclusion: the 166-staff clef ground
truth widens **S2 only**, which is already the best-covered signal here (0.890 /
0.848) and is documented at 92% end-to-end in CLAUDE.md; the 1,380 margin labels
measure **S1's OCR rung**, a reader question already owned by
`benchmarks/omr-margin-labels-2026-08`, which does not bear on S1's *precision*
(0.982) or on why the ensemble fails. Both cost a full pipeline re-run over 10+
pages. Recorded as a deferral, not as coverage.

---

## Reproducing

```bash
python3 benchmarks/omr-staff-identity-2026-09/probe_placement_survey.py   # Phase 0
python3 benchmarks/omr-staff-identity-2026-09/build_evidence.py           # Phase 1
python3 benchmarks/omr-staff-identity-2026-09/score_signals.py            # Phase 2
python3 benchmarks/omr-staff-identity-2026-09/probe_s3_and_multiplicity.py
python3 benchmarks/omr-staff-identity-2026-09/probe_matched_labels.py
python3 benchmarks/omr-staff-identity-2026-09/probe_block_frame.py
```

`evidence.json` / `evidence.csv` hold every signal beside its truth, so a later
session can re-score without re-deriving. `build_evidence.py` reads the scan
benchmark's `..graft09` fixtures from the main checkout (they are gitignored
build products); regenerate them with `scan_eval.py` if they are gone.

**Answer-key discipline, as implemented.** `works.json` and the reference `.mxl`
are read only into `TRUTH_*` and `CEILING_hand_label` fields; no signal function
receives them. Dossiers are not read at all. The one place the reference feeds a
truth field — clef, for the 125 staves works.json does not hand-read — is
validated against the 24 that it does (24/24), and the same validation is what
disqualified it for KEY.
