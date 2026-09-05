# The page-truth structural benchmark — a design

**2026-09-05. DESIGN ONLY. Nothing built, no pipeline code touched.** Written in
response to Sean's redirect:

> "Long-term we will not have MXL to measure against. If the scan comes in with
> 2 parts on a staff I want it to stay 2 parts on a staff — so this is a
> measurement issue against the MXL. We should be determining parts and staves
> off of the original scan or digital engraving, probably based off vision and
> processing. We need to rethink entirely how we benchmark this."

The deliverable is the design. Where the design says *this cannot be scored
without a human*, it says so rather than inventing a proxy.

---

## 0. What the redirect changes, and what it does not

**The structural answer key stops being a MusicXML file.** If the page prints
two players on one staff, that IS the correct output; a reference file's
part-splitting is a typing decision made later by someone else. The multiplicity
work already proved this is not a quibble — the identical printed `Viola` is
**1 part in three editions and 2 in Peters**, `Violino I` is 1 in three editions
and `Zweite Violinen` is **3**, and **eleven page-side signals separate the two
populations no better than chance** (best ensemble 0.526 against an `always 1`
baseline of 0.538).

⚠️ **`OMR_CONDENSED_PARTS` was optimising toward the wrong target for real
use.** It splits a condensed staff to match the encoder. Its measured worth —
oracle **−7,118**, with slot stitch **−9,369** — is a **benchmark artifact, not
user-visible quality**, and it should stop being treated as a goal. ⚠️ **The
work was well measured against a target we now believe is wrong**, which is a
different thing from being wrong: the arms, controls and the superadditivity
finding all stand as measurements. §5 says what to do with the flag rather than
deleting it.

**The `entire staff` bucket dissolves rather than gets solved.** 17,520 edits,
87% condensation, tied with Audiveris to the edit on all seven single-system
rows — under the new model that is not a debt, it is a **units mismatch**.

**What does NOT change: the refuted hypotheses stay refuted.** H1, H1′ and the
page-side multiplicity rules were about *detecting structure from the page*,
which is still exactly the goal. If anything the redirect raises their stakes.

**What is promoted: H0 is already the thing Sean is asking for.** It scores
roster, continuity and identity against **hand-read printed truth**, with no
MusicXML anywhere in the loop, and it emits no edit counts by construction. This
design extends it rather than replacing it.

---

## (a) The truth format

One record per page. Everything is **as printed** — what a reader sees.

```jsonc
{
  "edition_id": "beethoven-sym5-litolff-984073",
  "pdf_page_index": 3,          // 0-based, and the PRINTED page number too
  "printed_page": "47",
  "systems": [
    { "system_index": 0,
      "staves": [
        { "pos": 0,
          "printed_label": "Flauti",        // verbatim, or null if none printed
          "instrument": "Flute",
          "desk": null,                      // "I", "II", "I.II.", "III.IV."
          "named_parts": 2,                  // ⚠️ see below — NOT "players"
          "bracket_id": 0,
          "braced_with": null,
          "provenance": "read_here"          // ⚠️ see (c)
        }
      ],
      "brackets": [ {"id": 0, "from": 0, "to": 3, "kind": "bracket"} ]
    }
  ],
  "continuity": [ {"from": [0, 6], "to": [1, 7], "basis": "label"} ],
  "unreadable": [ {"what": "system 1 staff 9 desk", "why": "no label, music inconclusive"} ]
}
```

### What is genuinely readable by eye

| field | readable? | why |
|---|---|---|
| systems per page | **yes**, trivially | and the pipeline is already **20/20 exact** — see (b) |
| staves per system | **yes** | **26/26 exact** today |
| brackets / braces | **yes** — they are drawn | this is ink, not inference |
| `printed_label` verbatim | **yes** where printed | 115 of 407 staves print none |
| `instrument` | **yes** where labelled; **often** from clef + position otherwise | |
| **`desk`** (`Violino I` vs `II`) | **yes where printed**, and this is the field H0 is currently blind to | see below |
| `named_parts` | **yes where the label declares it** (`Corni I.II.` ⇒ 2); **NO otherwise** | see below |
| `continuity` | **yes where labels are printed**; **sometimes not at all** | see below |

### ⚠️ Three things the format must get right, because H0 got them wrong or could not see them

**1. `desk`, because folding to instrument KIND is H0's single largest
leniency.** H0 compares `Violin` to `Violin`, so **a prediction that swapped the
two horn staves scores perfect**. That leniency touches roster, continuity and
identity alike. A page-truth benchmark whose whole subject is structure cannot
keep it. `desk` is recorded separately from `instrument` so a scorer can report
both a kind-level and a desk-level number, and so today's figures stay
comparable at the kind level.

**2. `named_parts`, and NOT "players" — the word matters.** Sean's "2 parts on a
staff" is right for winds: `Flauti` with two note-columns is two players. It
does **not** transfer to strings: a `Viola` staff is a *section* of a dozen
players printed as one line, and asking a human for "players" there invites a
number nobody can read off the page.

> **The readable fact is how many parts the ENGRAVING NAMES**: `Corni I.II.` ⇒
> 2, `Flauti` with `a 2` ⇒ 2, `Viola` ⇒ 1, `Violoncello e Basso` ⇒ 2 (two named
> instruments on one staff). Where the label declares nothing and the music is
> ambiguous, the honest entry is `null` with an `unreadable` row.

⚠️ This is exactly the boundary in `H4_ROSTER_QUESTION_DRAFT.md`: a human can
answer *what does this staff carry as printed*; they cannot answer *how many
`<part>` elements did the encoder emit* — and if they could, that would be the
answer key.

**3. Continuity has cases the human cannot settle either, and the format must
let them say so.** On a Litolff continuation system the strings print **no
label** and the block is **re-condensed** (12 staves ending `Violoncello`,
`Basso` become 11 ending `Violoncello e Basso`), so deciding which staff
continues which means reading the music, not the margin. That is why
`unreadable[]` is a first-class field rather than an omission: **an abstention
must be recordable, or the corpus will silently acquire guesses.**

---

## (b) How little truth is enough

### Do not spend a minute of human time on counts

**Page cardinality is 20/20 rows and 26/26 systems exact.** Systems-per-page and
staves-per-system are *solved on this corpus*. They must still be recorded —
every other field is positional and therefore conditional on them — but they are
a **precondition to assert**, not a score to improve, and they should never be
pooled into a headline that then looks healthy because of them.

### The corpus is far thinner than its row count, and this is the crux

| | |
|---|--:|
| rows | 20 |
| multi-system rows | 11 |
| rows H0 can score for continuity | 10 |
| rows where the lineups actually **differ** (informative) | **5** |
| **independent pages** behind those 5 | **3** |

The 5 informative rows are two plate-twins of Beethoven p.3, two of p.4, and
Brahms p.2. ⚠️ **The two Litolff scans are the same engraving — a re-print, not
a replication** — so they are a *resolution control*, not new structure. The
effective evidence for the whole continuity question is **three pages**.

H0 says the consequence plainly: 0.8511 over 47 links "is a real number and it
caught a real, documented graft; **it is not a number that will separate two
competing continuity designs**."

### How many pages, and of which kinds

**Kinds first — they matter more than count.** In descending value:

| kind | why it is informative | in corpus today |
|---|---|--:|
| **equal staff counts, different lineups** | the silent mis-join: ordinal joining *succeeds and is wrong*. The hardest case and the one no current signal catches | **1 page** (Beethoven p.4, ×2 prints) |
| **re-condensation across systems** | `Vcl.`+`Basso` ⇒ `Bassi` — the case that defeats both the aligner and H2's roster join | **1 page** (same one) |
| **tacet suppression** | a staff omitted in one system; the case that already works and must not regress | 1 page (Beethoven p.3, ×2) |
| **mid-block suppression** | a staff dropped from the *middle* of a bracket block, which would price H2's forced arm | ⚠️ **0 — the corpus does not contain one** |
| **lineup change across a page turn** | continuity beyond one page; nothing today reasons across pages | **0** |
| more pages of identical lineups | satisfied by ordinal joining by construction | 5 rows |

**Count, with the arithmetic shown and its assumptions flagged.** To separate
two designs differing by ~10 points near 0.85 at conventional power needs on the
order of **200–250 paired link decisions**, against **47** today — roughly
**4–5× the informative evidence**, i.e. **12–15 independent informative pages**
rather than 3.

⚠️ **That figure is an order of magnitude, not a power calculation**, and it
leans on an independence assumption that is false in detail: links within a page
are correlated (one bad join shifts every staff below it — p.4 costs exactly 3
links on each twin). Treat 12–15 as a floor to plan against, and re-estimate
from the first widened batch rather than trusting it.

### ⚠️ Find the informative pages by machine before spending a human on them

`staff_detector.detect_staves` needs **no YOLO**, so phase 1 over hundreds of
library pages is nearly free. Rank candidates automatically:

1. **systems with different staff counts** — catches tacet suppression directly;
2. ⚠️ **equal staff counts with a different CLEF SEQUENCE between systems** —
   this is the screen that matters, because the highest-value kind (Beethoven
   p.4) has **equal counts** and would be invisible to screen 1. On p.4 the
   clef sequences genuinely differ between systems at the contested position;
3. **equal counts with different bracket-block shapes** — a weaker third screen.
   ⚠️ Use it only to *rank candidates for a human*, never as truth: H1′ measured
   `system_grouping` reading `[0×5,1×3,2×6]` against `[0×9,1×5]` on Brahms p.3,
   where the systems are **identical** — detector noise of the same magnitude as
   a real lineup change.

This turns "which pages should Sean read?" from a guess into a ranked queue, and
it is the same move the labeling campaign made with `select_cells_orchestral`.

**Answer-key line:** screens 1–3 read only the PDF. `works.json` and the
reference encodings are not consulted. Clean.

---

## (c) What it costs Sean

### The cost is bimodal, and H2 measured the two modes

| document shape | what a pre-pass arrives with | what the human does |
|---|---|---|
| **Simrock-shaped** (roster printed once, lineup stable) | **45 of 45**, names verified 45/45 against hand truth | confirms a complete draft |
| **Litolff-shaped** (condensation + labels dropped) | winds and brass only — **2 of 50** | supplies the whole string block by hand |

⚠️ **The same engraving decision removes the label AND breaks the join**: the
staff that lost its name is the staff that was merged. So the pre-fill is
weakest exactly where the truth is most valuable — the informative pages of (b)
are Litolff-shaped by definition.

### Estimated human time per page

Not measured; stated as an estimate with its basis, to be replaced by a timed
pilot of ~5 pages before any bulk campaign.

| task | estimate | basis |
|---|--:|---|
| confirm a complete pre-filled roster (Simrock-shaped) | **1–2 min** | a glance per staff, 15 staves |
| supply an unlabelled condensed block (Litolff-shaped) | **5–10 min** | requires reading the music, not the margin |
| brackets + braces | **<1 min** | drawn ink, read directly |
| desks (`Violino I`/`II`) where printed | **<1 min** | reading |
| continuity on a differing-lineup page | **3–8 min** | the judgement call, and the reason the page is in the corpus |

So **12–15 informative pages ≈ 2–4 hours**, plus a re-check pass. That is a
real but bounded ask, and it buys the only instrument that can referee this
work.

### ⚠️ Where a mistake would be silent — and one has already been caught

**The failure mode is a human who assumes continuation instead of reading.** H2
found the live instance: `works.json` carries separate hand-read staff lists for
Dvořák p5, p6 and p7 and **all three are identical**, so *a human who assumed
the lineup continues produces the same file as one who checked*. It was
mitigated only by rendering printed 184 and looking at it.

**Design countermeasure — per-item truth provenance, and it is the single most
important field in the format.** Every staff records how its truth was
established:

| `provenance` | meaning |
|---|---|
| `read_here` | the label is printed on THIS page and was read |
| `inherited` | assumed to continue from an earlier page — **a claim, not an observation** |
| `from_music` | no label; decided by reading the notes |
| `unreadable` | the human could not settle it |

A scorer can then report its figure **excluding `inherited` rows**, which is the
only way to know whether the corpus is measuring the pipeline or measuring an
assumption. This is `instrument_source` applied to the truth instead of the
prediction, and H2's risk #1 is the proof it is needed.

⚠️ A second silent failure: **a pre-filled draft is a suggestion, and a human
confirming a plausible-looking wrong name is the pre-fill campaign's measured
lesson** (assisted labels sit on the suggester's own grid; the blind-labeling
protocol exists because of it). Any page whose truth will be used to *score* a
roster pre-pass should be read **blind** — the same `--blind` discipline
`annotate.server` already has.

---

## (d) The boundary with musicdiff

**Two instruments, two questions. Neither replaces the other.**

| question | instrument | key |
|---|---|---|
| are the NOTES right — pitch, duration, beams, slurs, articulations, directions | **musicdiff / OMR-NED** | reference MusicXML |
| is the STRUCTURE right — systems, staves, instrument, desk, named parts, brackets, continuity | **page-truth score** | hand-read printed truth |

H0 already states the complement precisely: "a pipeline that recovered the
roster perfectly and read no music at all scores 1.0000 on all three." The
converse is equally true, which is why OMR-NED stays.

### Which recorded figures become uninterpretable, and what to do with each

| figure | status under the new model | action |
|---|---|---|
| CLAUDE.md's pooled OMR-NED block (11 works, 0.1306 / 0.1399) | **still valid for note-level accuracy**; must stop being read as an *overall quality* figure, since part of it prices agreement with an encoder's part-splitting | keep, **re-scope the prose around it** |
| `entire staff` bucket, 17,520, 87% condensation | **not a target any more** | stop optimising; keep as a diagnostic |
| `OMR_CONDENSED_PARTS` −7,118 / −9,369 | **a benchmark artifact**, measured correctly against a target now believed wrong | relabel in the record; do **not** delete the measurement |
| slot stitch −242, and its ES/EM repricing | **unaffected** — continuity is right under both models | keep |
| the scan gate's pooled figure | valid at note level; its structural component is now **the wrong units** | report page-truth beside it, never merged |
| `works.json` | **its role SPLITS** | see below |

**`works.json` is promoted, and its two halves separate.** Its hand-read
`staves[]` / `systems_as_printed` blocks become **the seed of the page-truth
key** — they are already exactly that, which is why H0 could be built at all.
Its linkage to reference `.mxl` files stays, for note scoring only. The file
should eventually be split so the two cannot be confused, and **the page-truth
half must never be an input**, exactly as today.

### ⚠️ THE WARNING THAT MUST BE STATED IN ADVANCE

**If the exporter stops splitting condensed staves, OMR-NED will get WORSE on
those rows while the output gets BETTER.** The magnitude is already known — it
is the oracle arm's −7,118, run backwards. Somebody will read that as a
regression. **Predict it, in writing, before the change lands**, or the metric
will veto a correctness improvement. This repo has the precedent both ways: the
articulation work shipped at **+97 pooled edits** because the marks were right,
and the slur `drop` variant scored *better* by deleting 12 real slurs and was
refused.

---

## (e) What changes in the pipeline's target

**If a condensed staff should stay condensed, the exporter should emit one
`<part>` per PRINTED STAFF, with the players as separate `<voice>`s inside it
where the page prints them separately.** That is the engraving's own semantics:
one staff is one line of music, and `a 2` versus two note-columns is a voice
distinction, not a part distinction.

⚠️ **Three things I am NOT asserting**, because they need checking rather than
claiming:

1. whether MusicXML's `<score-part>` machinery (it carries `<player>` elements
   for multi-player parts) is the right vehicle for declaring "this part is two
   players" — **verify against the spec before designing on it**;
2. whether existing consumers (Verovio rendering, LilyPond export, the review
   UI) handle two voices on one staff as well as they handle two parts;
3. what this does to `_stitch_slots`, which becomes *more* clearly right — a
   continuous part is correct under either model — but has never been measured
   with condensation left alone.

**What becomes wrong rather than merely off:**

| flag | today | under the new target |
|---|---|---|
| `OMR_CONDENSED_PARTS` | default off; the thing to turn on given a count source | ⚠️ **an anti-feature for real use.** Reframe as an explicit **benchmark-compatibility mode**: keep the code, keep the measurements, rename the purpose, and never enable it for a user's export |
| `OMR_SLOT_STITCH` | default off, "flip with a count source or not at all" | the count-source condition **dissolves**; it should be re-measured on the page-truth score, where fragments are simply wrong |
| `_condensed_on_fragments` (`=all`) | measured harmful | unchanged, and now clearly so |

⚠️ **`OMR_SLOT_STITCH`'s decision genuinely reopens**, and that is a real
consequence rather than a tidy one: its recorded verdict — "flip it together
with a real count source, or not at all" — was reasoning **about OMR-NED's
part-pairing charges**. Under a page-truth score there is no count source to
wait for, and the structure it produces (Brahms p.2: 27 fragments → 14
continuous parts, correctly leaving the suppressed Trompeten slot short) is
simply the right answer. **Do not flip it on this reasoning alone** — re-measure
it against the page-truth score first, which is the point of having one.

---

## What I would build, in order

1. **Extend the truth format and re-run H0 against it** — add `desk`,
   `named_parts`, brackets and `provenance`. Cheap: the scorer exists, and
   `works.json` already holds most of the fields. This also removes H0's largest
   leniency (kind-folding).
2. **The informativeness pre-screen** (b) — detector-free phase 1 over the
   library, ranked by the three screens, producing a queue of candidate pages.
   No human time, and it decides where human time goes.
3. **A timed 5-page pilot**, blind, to replace (c)'s estimates with measurements
   and to test whether the format is answerable at all.
4. **Then** the widening campaign to 12–15 informative pages.
5. **Only then** re-open `OMR_SLOT_STITCH` and the condensation output question
   against the new score.

⚠️ Nothing here should start before Sean's strategy call. Framing result 4 —
that structure work has almost no edit ceiling on this corpus — plus three
refuted hypotheses, plus condensation owning 87% of a bucket both metrics are
blind to, is a fair case that the remaining win may be elsewhere. **This design
is what structural R&D would need to be *scoreable*; whether it is where the
effort should go is his call, and he should make it with H3's result in hand.**

## Answer-key discipline, per proposal

| proposal | side of the line |
|---|---|
| page-truth format, hand-read | **clean** — the human reads the print |
| informativeness pre-screen | **clean** — reads only the PDF |
| `works.json` promotion | **clean, and unchanged** — scoring only, never input |
| reference `.mxl` for note scoring | **unchanged** — scoring only |
| `OMR_CONDENSED_PARTS` as benchmark-compatibility mode | **clean, if never enabled for a user export** |
| dossiers | **barred**, as today |
