# The stem exception space — from "here is a vertical run of ink" to what it could and could not be

2026-09-20. Research only — **no production code changes in this document's
branch.** Written to answer Sean's framing directly:

> *"Stems are usually a similar length but not always. They generally go in a
> particular direction based on where the note they are connected to is based
> on the center of the staff — but not always. The stem will be longer if it
> goes through multiple vertical notes that are a chord. All of these feel
> like they fall short… We need to know every possible scenario — I don't know
> of a few single rules that will give us what we need."*

The three rules he names are already in `docs/engraving-conventions.md`
(`[C9]`, `[C10]`, and the chord-length half of `[C13]`). **This document does
not re-harvest them.** Its job is the part his framing asks for and the
registry does not yet have: the complete exception space around each stem
rule, a register — currently absent — for when two stems can sit close enough
to be confused for one, and a grading of every rule by whether it can be used
to RULE OUT a hypothesis on a scan, or only to draw a fresh page.

---

## 0. What the registry already had — read this before anything below

`docs/engraving-conventions.md` "Stems & beams" holds **18 entries** (`[C9]`
–`[C15]`, `[C79]`–`[C80]`, `[L10]`–`[L23]`), 8 of them MEASURED HERE and 10
LITERATURE ONLY, plus scattered stem references inside the arc, dynamics and
key-signature sections. It already states, correctly and (where tested)
measured on this project's own plates:

| already in the registry | id |
|---|---|
| stem attaches RIGHT-and-UP or LEFT-and-DOWN, never right-and-down | `[C9+L10]` |
| single-voice: above the middle line → stem down (and the reversal above the 6th ledger step is a POSITION fault, not a rule fault) | `[C10+L16]` |
| a stem is ~3.5 sp (one octave) by default, and as long as the music needs | `[C13+L11]` |
| a beam joins stem TIPS — one stroke, one direction for every note on it | `[C11]` |
| a beam runs from the FIRST stem it joins to the LAST; a note attaches by its STEM, not its notehead centre (0.35–0.47 nh-width overshoot) | `[C12]` |
| stacked beams sit 0.75 sp apart, centre to centre (0.5 stroke + 0.25 gap) | `[C79+L20]` |
| a flag NAMES a value and hangs on the stem, ~3.5 sp from the head | `[C80+L23]` |
| a stem on ledger lines reaches the middle staff line | `[L12]` |
| a stem is never shorter than 2.5 sp | `[L13]` |
| a stem is ~0.10–0.16 sp thick, indistinguishable from a thin barline by thickness alone | `[L14]` |
| default direction with no case either way: DOWN (except some vocal/edition conventions) | `[L15]` |
| two voices, one staff: upper up, lower down, REGARDLESS of position | `[L17]` |
| stem direction held constant through a beat/half-bar | `[L18]` |
| a chord containing a second straddles the stem (higher right, lower left) | `[L19]` |
| a beam is angled by the OUTER interval; horizontal in three named cases | `[L21]` |
| beaming follows the metre and never crosses the bar's middle (Gould names the Classical/Romantic-era exception explicitly) | `[L22]` |
| two successive notes are set further apart than one accidental's own strokes — **REFUTED as a working rule on this plate below**, not merely "known exception" | `[C14]` |
| no stem → whole note | `[C15]` |

**This document's additions sit beside those 18, never restate them.** Where
a finding below sharpens or overturns one of the 18 (in particular `[C14]`),
it is flagged and cites the id.

---

## 1. THE COMPLETE EXCEPTION SPACE

Organised the way a reader meets it: first by what changes the RULE (the
convention is suspended or altered by context), then by what changes the
MEASUREMENT (the same rule holds, but the ink you would look for is
different).

### 1.1 Direction — every override of "position decides"

The baseline (`[C10]`) — one voice, above the middle line → down, below → up
— is suspended, in documented order of how completely it overrides:

| context | what happens to direction | source | numeric |
|---|---|---|---|
| **Two (or more) voices on one staff** | direction becomes a **voice label**: voice 1 up, voice 2 down, **independent of pitch** — a voice-2 note sitting well above the staff still takes a down-stem | Gould p.14; Wikipedia *Stem (music)*; LilyPond `\voiceOne`/`\voiceTwo` (`[L17]`) | none |
| **A chord** (single voice) | direction is decided by the note **furthest from the middle line**, not by the chord as a whole or its lowest/highest member indiscriminately | Gould p.14; Dorico notation reference ("If the note furthest from the middle line is above the middle line, the stem of the chord points downwards") | none |
| **A chord exactly straddling the middle line** (equidistant top and bottom) | falls back to the plain default-down convention (`[L15]`) in most engraving practice; some houses default up in this exact tie case | Gould p.14 (states the DOWN default applies "when there is no clear-cut case") | none |
| **A beamed group** | direction is decided **once for the whole group**, from the outer notes' average position, not per note — so a single note near the middle line inside a group beamed mostly-high still gets an up-stem if the group is up | Wikipedia *Stem (music)*; `[L21]` (slope) implies the same averaging | "average position of the lowest and highest notes" |
| **Beat / half-bar grouping** | direction is held constant across the beat even where individual notes' positions would flip it mid-beat | Gould p.14 (`[L18]`) | none |
| **Grace notes** | scaled down as a unit; direction still follows voice/position rules at the smaller size — NOT independently governed | Dorico ("Layout of grace expressions can be changed using the Stem direction property") | stem length ≤ **5 vu = 2.5 sp** (MEI; see §1.3) |
| **Vocal music, some editions** | up-stems used throughout regardless of position, "to allow the text to be placed close to the stave" | Gould p.14 | none |
| **Some editions generally** | down-stems used exclusively, again suspending the position rule | Gould p.14 | none |
| **A unison shared by two parts on one staff** (`a2`) | the SAME notehead may carry stems in BOTH directions from one head, which is not "a chord" in the usual sense — two independent voices agreeing on pitch, not one event | `en.wikipedia.org/wiki/A_due`; orchestration practice (`notat.io`, VI-Control) | none |
| **Cue notes** | all cue-note stems in a passage point the SAME direction, deliberately overriding whatever position or voice would otherwise dictate, so the cued line reads as a visually distinct unit | Hansen Media, *Conventions of Notation* | 65–75% of normal notehead size |
| **Double-stemmed writing** (one note voiced into two directions at once, e.g. a note shared by SATB reduced onto one staff) | stems shortened progressively as the note moves outside the staff, rather than reaching the standard ledger-line length | Gould p.15 | — |

**A single stem, mid-run, that reverses which side it attaches to** (right
then left, or vice versa) **is not one note under this convention at all** —
see §2; it is the signature of two fused stems, not a direction exception.

### 1.2 Length — every override of "one octave, or to a beam"

| context | what changes | source | numeric |
|---|---|---|---|
| **Beamed group** | length is not fixed at 3.5 sp; it is whatever reaches the beam, and the beam's own slope (`[L21]`) can make members of one group have visibly different lengths | LilyPond `beamed-lengths . (3.26 3.5 3.6)`; Gould p.14 | 3.26–3.6 sp band around the nominal 3.5 |
| **Beyond one ledger line** | length grows to reach the staff's **middle line** — no cap short of that, so a note 4+ ledger lines out can carry a stem well past 8 sp (`[C13]`'s measured second population) | Gould p.14 (`[L12]`) | "to the middle stave-line" |
| **Beyond one ledger line, in DOUBLE-STEMMED writing** | the opposite: progressively SHORTENED instead of extended, because two directions are already competing for the same vertical space | Gould p.15 | — |
| **Flagged (unbeamed) notes with a longer tail** | LilyPond shortens a forced-direction stem by 1 sp, a flagged one by 0.5 sp from the nominal, relative to a beamed one | LilyPond `(stem-shorten . (1.0 0.5 0.25))` | 0.25–1.0 sp |
| **A note requiring several flags or beam levels** | length grows with the number of hooks/levels — each extra level demands more room, which is why `[L23]`'s flag-per-level counting bug (counting glyphs, not levels) under-measured duration | Gould p.15; SMuFL flag metrics | `flag8thUp` bbox 1.056 × 3.276 sp |
| **Grace notes / cue notes** | scaled down as a unit; MEI caps a grace stem at **5 vu = 2.5 staff spaces** — *coincident with the absolute floor Gould states for an ORDINARY stem* (`[L13]`) | Verovio/MEI guidelines (`rism-digital/verovio#419`); Gould p.14 | ≤ 2.5 sp |
| **The absolute floor** | never shorter than 2.5 sp (a sixth), for ANY note, regardless of how many beams must be accommodated | Gould p.14 (`[L13]`) | 2.5 sp |
| **Cross-staff beaming** | length is not derived from a fixed default at all — "the variable distance between noteheads and staves is calculated automatically" from wherever the beam ends up sitting between the two staves | LilyPond, *Cross-staff stems* | none stated |
| **Whole and double-whole notes** | **no stem at all** — length is not "very short", the rule does not apply | universal (`[C15]`) | n/a |
| **19th-century engraving generally** | the 3.5 sp default and the 2.5 sp floor are typographic/house conventions rather than physical constants of the font; a specific plate's stems cluster around its OWN norm, which this project has never separately measured against Gould's figure (see §4) | — | unmeasured on our plates |

### 1.3 Attachment side and point — every override of "right-up / left-down, at the head's edge"

| context | what changes | source | numeric |
|---|---|---|---|
| **A chord containing a second** | the two adjacent-pitch heads CANNOT share a side; higher goes right of the stem, lower goes left — this is `[L19]`, already registered, but it is the load-bearing exception for §2 below and is restated here for completeness | Wikipedia *Stem (music)*; Bravura `splitStemUpSE`/`splitStemDownNW` | offset ≈ 1 notehead width (1.18 sp, Bravura) |
| **A cluster of three or more adjacent notes** | the OUTER two straddle as with a second; interior members switch sides again, alternating, rather than all piling on the stem's far side | Gould (cited via registry `[L19]` "known exceptions") | none numeric found |
| **A chord's interior member** (three-plus-note chord, middle note) | is genuinely mid-stroke by construction — the ONE case where "the head is not at the stroke's end" is correct and not a fault, and the only case `docs/ask-first-conventions.md`-style falsification for this convention names | this project, `benchmarks/omr-stem-attribution-2026-09/FINDINGS.md` §0 | 64%/95% of "off-end" heads on our two plates are exactly this |
| **Grace-note slashes** | the stem's slash must intersect a staff line or sit wholly inside a staff space, a POSITIONAL constraint on top of the ordinary attachment rule | LilyPond, *Special rhythmic concerns* | — |
| **Cross-staff beaming, notehead on the far staff's side of the beam** | the stem crosses the whole gap between two staves; attachment is still at the notehead's own edge, but "reaching" now traverses a much larger vertical distance than any single-staff case | LilyPond, *Cross-staff stems*; Dorico forum ("Extending note stem to other staff") | — |
| **Tremolo strokes** | ride the stem and therefore carry **no side of their own at all** — a tremolo mark is not attached left/right like an articulation, it straddles the stem | Wikipedia *Tremolo*; MuseScore handbook | — |

---

## 2. ⚠️⚠️ THE MISSING REGISTER — WHEN CAN TWO STEMS BE ADJACENT, TOUCHING, OR COLLINEAR?

**Nothing in the 18-entry registry addresses this, and it is the live
question this project has been measuring for a week.** What follows combines
the literature (which gives almost no numbers here — engravers are told how
to draw two voices apart, never told how close a mis-set pair may legally
come) with this project's own measurements, taken 2026-09-15 through
2026-09-19 on two publishers' plates of the same period, which is the closest
thing to a numeric register that exists anywhere for this question.

### 2.0 Why the literature is nearly silent

Every source consulted (Gould, Wikipedia's *Stem (music)*, LilyPond,
Dorico's documentation) states the RULE an engraver draws by — two voices
point opposite ways, a second's heads straddle the stem, notes are spaced
"in proportion to duration" — but **none states a minimum clear distance
between two stems that legally stand close together**, because a human
engraver adjusts the drawing until it reads unambiguously and the rule is
therefore about the RESULT (no visual confusion), not about a measurable
gap. This is a genuine gap in the sourced literature, not an oversight of
the search. Where LilyPond's own spacing engine has to make the decision
algorithmically, it reveals numbers no printed engraving guide states:

- **Odd-numbered (up-stem) voices shift RIGHT, even-numbered (down-stem)
  voices shift LEFT** when two voices at a second or closer would otherwise
  collide (`\shiftOn` / the default automatic layout). The shift amount is
  computed to clear the notehead, not fixed at a stated number of spaces.
- **A shared unison with same notehead shape and opposite stem direction is
  MERGED to one head with stems both ways** — this is the one case the
  literature explicitly puts two stems on ONE notehead by rule, not by
  accident, and it is the strongest documented case of two stems standing
  at literally zero horizontal separation.
- **Rests belonging to different voices are vertically displaced** to avoid
  landing on the same line as the opposing stem — evidence that stem/stem
  (and stem/rest) proximity is a recognised hazard the engraving system
  actively manages, even though no printed number for "how close is too
  close" survives into the documentation.

### 2.1 The five situations that bring two stems together — with numbers

**(a) Two voices stemming TOWARD each other, upper up / lower down, at
(near-)identical x.** This is the textbook case (`[L17]`) and the one Sean
named from a real Breitkopf plate. Measured on that plate
(`omr-stem-attribution-2026-09`, `benchmarks/omr-stem-pair-rule-2026-09`):

- The most extreme confirmed case (`glyph/1/0/3/4/0`) is a fused component
  spanning **5.7 staff spaces**, overshooting the top head by **2.5**
  notehead-heights and the bottom head by **2.8** — a single legitimate stem
  never overshoots at BOTH ends (a stem starts AT its notehead), so
  **overshoot at both ends is the asymmetry a single stem cannot produce.**
  Measured rate of both-ends overshoot on flagged (suspect) runs: **50%
  (7/14) Breitkopf, 18% (9/51) Litolff.**
- Flagged (fused) runs are **longer** than ordinary stems: median **5.72 sp
  (Litolff) / 4.43 sp (Breitkopf)** against ordinary medians of **4.12 / 3.46
  sp** — roughly 30–40% longer than a normal ~3.5 sp stem.
- Flagged runs are **~18% WIDER** than ordinary stems (0.38 vs 0.32 sp
  Litolff; 0.21 vs 0.18 sp Breitkopf) — two strokes at slightly different x
  merging into one wider connected component.
- Cutting a flagged run at the interior notehead leaves a **substantial
  piece on both sides** (medians 2.75/3.06 sp and 2.50/2.03 sp) — this is
  the discriminator against "one stem plus overrun": a genuine overrun
  leaves a short residual on one side, not two roughly-equal halves.
- **The x-offset between the two merging strokes, where measured directly on
  the "two stems eating each other" population inside the pair-rule work, is
  0.51–0.85 staff spaces** (centre-dx of paired strokes carrying two heads,
  both directions of stem, `omr-stem-pair-rule-2026-09` §2b table:
  0.56–0.73 sp across all sub-populations). **This is the working number to
  quote for "how close is close": on these two 19th-century plates, two
  independent stems fuse into one detected component when their centres are
  within roughly 0.5–0.9 staff spaces AND their vertical extents overlap.**

**(b) A second between voices, where head displacement puts stems roughly a
notehead apart.** This is `[L19]`'s straddle case read as a TWO-STEM
question rather than a one-chord question. Measured directly against
`Q.NOTEHEAD_STAFF_POSITION`, over 223 stemless/stemmed pairs standing at one
x on the Litolff plate:

- **Only 1 of 223 same-x pairs (0.4%) sits at an interval of one diatonic
  step (a second)** — the chordal-second shape is almost absent from the
  "two things at one x" population. 138 of 223 (62%) sit at an octave or
  wider.
- This is the discriminator: **a genuine chordal second at one x is RARE**
  on real orchestral writing (most simultaneous same-x events at a wide
  interval are two independent voices, not one chord), so "two stems at one
  x, a second apart" should be treated as the MINORITY reading, not the
  default one, when disambiguating a fused run.
- Bravura's stated offset for the straddle case is **1.18 staff spaces**
  (one notehead width) — this is the DESIGN number; the measured population
  above says how rarely a fused run actually has this shape on a real plate.

**(c) A chord's stem meeting another voice's stem.** Not separately
measured on this project (the pair-rule work's population is dominated by
(a) and by accidental/notehead confusions, not by chord-vs-voice
collisions), but the mechanism is the union of (a) and `[L19]`: a chord's
stem is already offset by the straddle rule, so where a second voice's stem
lands near that same x, the same 0.5–0.9 sp fusion hazard applies with one
side of the pair already displaced by ~1.18 sp from its own chord partner.
**Not established; flagged as untested.**

**(d) Cross-staff beaming bringing a stem in from the staff above or
below.** Not measured on this project at all — no cross-staff beaming
population has been isolated in any committed benchmark. The literature
gives no numeric collision distance (LilyPond computes it automatically
per-page). **Reach: zero. This is the least-covered of the five shapes and
is the most exposed on a conductor's score, where a cross-staff beam
crossing the inter-staff gap is common in reduced (piano/organ) writing but
rare in the purely orchestral plates this project reads.**

**(e) Stems of consecutive notes in a dense passage.** This is `[C14]`'s
domain, and it is where the biggest correction sits. `[C14]` as registered
says "two successive notes are set further apart than one accidental's own
two strokes" and prescribes dropping any pair of verticals within 0.9 sp
that overlap vertically by ≥0.6 as being one accidental glyph rather than
two stems. **This project has now measured that premise FALSE on a real
plate**: of 80 deleted stroke-pairs that land on a detected notehead, **62
(77.5%) were two genuine stems eating each other, not an accidental.**
Of the 36 pairs where BOTH strokes carry a notehead:

| shape | count | share | median centre-dx |
|---|--:|--:|--:|
| both stem DOWN (successive notes, same direction) | 23 | 63.9%(*) | 0.64 sp |
| opposite directions (two voices) | 10 | 27.8% | 0.59 sp |
| both stem UP | 3 | 8.3% | 0.70 sp |

(*of the 36 two-headed pairs; percentages above recompute the pair-rule
table's raw counts to a shared denominator.)

**So the dominant shape of "two adjacent stems" on a real 19th-century
orchestral plate is NOT the textbook two-voices-facing-each-other case — it
is two SUCCESSIVE notes in ONE voice, same stem direction, set close enough
in a dense passage to fuse.** The centre-dx for this shape (0.64 sp) is
statistically indistinguishable from the two-voice case (0.59 sp) and from
the accidental-pair case (0.56 sp) — **direction and centre-distance alone
cannot separate a fused pair of successive same-direction notes from a fused
stem-plus-accidental**, which is why this project's own attempt at a
geometry-only cut (best single feature: bottom-offset, separates at 0.823,
against a 0.723 majority baseline — ten points of lift, no empty interval)
was refused as "a constant fitted to this plate."

### 2.2 What DOES distinguish a fused pair — and what still does not

| signal | works? | number |
|---|---|---|
| **Overshoot at BOTH ends of the run past the outer noteheads** | ✅ decisive — a single stem starts AT its notehead, so it can only overshoot at one end | 50% Breitkopf / 18% Litolff of flagged runs |
| **Run length vs the ~3.5 sp norm** | partial — flagged runs run 30–40% longer, but this is a shift in a distribution, not an empty interval | 5.72/4.43 sp vs 4.12/3.46 sp |
| **Run width vs a single stem's ~0.10–0.16 sp (or this plate's own measured stem width)** | partial — ~18% wider, again a distribution shift | 0.38/0.21 vs 0.32/0.18 sp |
| **Whether the interior "orphan" notehead's box holds a companion on the SAME stroke** | ✅ the corrected discriminator for the (withdrawn) attribution-fault hypothesis — 64%/95% of off-end heads are genuine chord members with a same-x companion | — |
| **Direction of the two merging strokes (same vs opposite)** | ❌ does NOT separate — opposite-direction pairs are a MINORITY (27.8%) of genuine two-stem fusions; same-direction successive notes are the majority | — |
| **Centre-to-centre x offset alone** | ❌ does NOT separate two-stem pairs from stem+accidental pairs — all three shapes cluster at 0.56–0.70 sp with no empty interval | best single-feature separation 0.723–0.823, no gap |
| **Whether EITHER member of a fused pair carries a detected notehead at all** | ✅ the one geometry-cheap discriminator this project's own work recommends (not yet shipped): keep a stroke that meets a notehead, drop a pair only where NEITHER member does | recovers 53→20 summed error against a 15-error shipped baseline on an independent 10-cell hand count |
| **Column-level: do heads sharing one x SHARE their outcome (same duration/decision) more than chance?** | ✅ heads at one x are demonstrably MORE likely to share an outcome than a within-cell-shuffled null (118 observed mixed columns vs a null mean of 156.1, 0/400 draws at or below), the opposite of what "one stem serves only the outer head" would predict — supports "shared stems mostly work," which is a different question from "are two adjacent stems one stem or two" | 0/400 draws ≤ observed |

### 2.3 The register, stated as a decision table

Given a connected vertical run of ink on a scanned page, in roughly
descending order of how decisive the evidence is:

1. **Does the run overshoot BOTH its outermost noteheads?** If yes, it is
   two (or more) fused stems, not one — a single stem cannot do this.
2. **Is the run's length ≳ 1.3–1.4× the plate's own median single-stem
   length**, or its width ≳ 1.15–1.2× the plate's own median single-stem
   width? Weak evidence toward fusion; neither alone is decisive, and
   neither has an empty interval on this project's own two plates.
3. **Does an interior notehead sit alone at the junction** (no companion on
   the same stroke at the same x)? If the run is genuinely one stem, that
   interior head must be a MIDDLE MEMBER OF A CHORD (three-plus notes) —
   check for a companion above AND/OR below on the same x. If none exists at
   all, the run is two fused stems and the "orphan" head belongs to
   whichever visible segment its OWN y-position is closest to, not to the
   run as a single unit.
4. **Direction of the two candidate segments is NOT a reliable
   discriminator on its own** — same-direction successive notes fuse at
   least as often as opposite-direction two-voice writing, on the plates
   measured here (63.9% vs 27.8%).
5. **Presence of a detected notehead at EACH candidate segment's own end**
   is the cheapest and best-supported geometric proxy available today, but
   it is coupled to how good notehead detection already is on that segment
   — it fails toward "leave it as one fused run" exactly where detection is
   weakest, which is not a free win.

⚠️ **No source, internal or external, gives a clean minimum clear distance
in staff spaces below which two GENUINELY SEPARATE stems may never legally
stand.** The closest thing to one is the empirical centre-dx band
**0.5–0.9 staff spaces**, which is where this project's fused pairs
actually cluster on two publishers' plates — but that number describes
where fusion HAPPENS on a scan, not a rule an engraver was following; it is
a measurement of a detector's blind spot, not a fact about engraving.

---

## 3. EVERY RULE, GRADED AS A READING DISCRIMINATOR

**HARD** = an engraver cannot violate it; usable to rule a hypothesis OUT
outright. **STRONG TENDENCY** = usually true, named exceptions exist and are
common enough to matter. **PREFERENCE** = varies by publisher/era/house;
treat any single instance as weak evidence only.

| rule | id | grade | measurable on a scan? |
|---|---|---|---|
| Stem attaches right-up / left-down, never right-down | `[C9]` | **HARD** for the (side, direction) cell it fills — one of four cells is simply never music | Yes — the cheapest possible geometric test; already 95.9–98.2% agreement with existing readings on this project's plates |
| One voice, position → direction | `[C10]` | **STRONG TENDENCY** (suspended completely by 2-voice writing, chords) | Yes as a RULER not a reader — refuted here as a stand-alone direction READER (accuracy reverses past the 6th ledger step, traced to position error, not to the rule); useful as an AUDIT that flags a disagreement zone |
| Beam joins stem tips, one direction per beamed group | `[C11]` | **HARD** | Yes — 0.984 accuracy where a beam-mate exists (shipped) |
| Beam runs first-stem-to-last-stem; notehead attaches via stem, not centre | `[C12]` | **HARD** | Yes — measured overshoot band 0.35–0.47 nh-widths, no empty interval reported but a clean measured cluster |
| Stem ~3.5 sp by default, longer as needed | `[C13]` | **STRONG TENDENCY** as a default, **HARD** that it is AT LEAST the floor and AT MOST what the beam/ledger-reach demands | Partially — a length cap (8.0 sp measured here) separates read stems from junk, but the cap itself sits on a decaying population, not an empty interval |
| Successive notes set further apart than an accidental's own strokes | `[C14]` | ⚠️ **REFUTED as stated on this project's own plate** — no longer usable as a HARD rule; treat as a PREFERENCE at best, and an unreliable one (77.5% of its own deletions on this plate were wrong) | No — the geometry alone cannot separate the three populations it needs to (no empty interval; best cut 0.823 vs 0.723 baseline) |
| No stem → whole note | `[C15]` | **HARD** (font/engraving-level fact) | Yes in principle, but indistinguishable from "stem simply not detected" without an independent confirmation — this project has never separately confirmed it |
| Stacked beams at 0.75 sp centre-to-centre | `[C79]` | **HARD** (typographic constant, reproduces the font default exactly) | Yes — bimodal population with a genuine empty interval (0.26–0.65 sp) measured on this project's plate |
| Flag names a value, hangs on the stem | `[C80]` | **HARD** for attachment; the tail's exact design length is house style | Yes for attachment (stem-based rule beats proximity-based); a note under a beam carrying a flag on its stem is a HARD contradiction usable as a truth-free check (measured false-positive rate for THAT check itself: 2.7% engraved / 18.9–27.5% scanned) |
| Ledger stems reach the middle line | `[L12]` | **STRONG TENDENCY** (Gould states it as rigid; double-stemmed writing shortens instead per `[L12]`'s own "known exceptions") | Untested here, but it is a cheap, unused CROSS-CHECK on a ledger-note's pitch reading — if the far end of a long stem does not land near the middle line, either the stem is wrong or the pitch is |
| Floor of 2.5 sp | `[L13]` | **STATED AS ABSOLUTE** by Gould | Untested here — this project has a cap (8.0 sp) and no floor; a floor is a one-line addition to price |
| Stem thickness ~0.10–0.16 sp | `[L14]` | **PREFERENCE** (varies 0.10–0.16 across five named applications) | Barely — too close to barline thickness (0.16 sp) to separate on thickness alone; this project already separates barline from stem by EXTENT instead |
| Default-down when ambiguous | `[L15]` | **PREFERENCE** — Gould explicitly states some editions reverse it entirely (down-only, or up-only for vocal text clearance) | Only usable as a weak prior, and this project's own measured baseline (always-the-commoner-direction = 0.506, essentially a coin flip on the plate tested) shows the prior is worth very little on real orchestral material |
| Two voices: up/down regardless of position | `[L17]` | **HARD** where two voices genuinely share a staff | No direct test here, but it is the named mechanism behind two of this project's own open problems (`[C10]`'s reversal, `[C14]`'s deletions) |
| Direction held through a beat/half-bar | `[L18]` | **CONVENTIONAL** — "strength varies by edition" per Gould | Untested; proposed as a metrical signal readable from geometry with no duration arithmetic, never built |
| Chord containing a second straddles the stem | `[L19]` | **HARD** | Untested directly, but IS the missing-register's key exception (§2.1b) — and the measured population says this shape is RARE (0.4% of same-x pairs) compared to what intuition suggests |
| Beam angle follows outer interval; three named horizontal cases | `[L21]` | **HARD** as a principle; slope magnitude is house style | Untested; proposed as a pitch cross-check needing no notehead reading, never built |
| Beaming follows the metre, no mid-bar crossing | `[L22]` | **RIGID in modern practice; Gould explicitly states it is NOT historical practice for Classical/Romantic repertoire** — directly relevant to this project's 19th-century corpus | Untested; would need bar-position context this project already carries (`Q.ONSET_COLUMN`, meter machinery) but has never wired to beam boundaries |
| Grace note stems ≤ 2.5 sp (5 vu) | new (§1.2) | **STATED convention** (MEI/Verovio) | Untested — but notable that this equals Gould's absolute floor for an ORDINARY stem, so a short stem alone cannot distinguish a grace note from a minimum-length ordinary note; scale/size must arbitrate instead |
| Cue-note stems uniform direction, 65–75% notehead size | new (§1.1/§1.2) | **PREFERENCE** (house convention for legibility, not a physical constraint) | Untested |
| Unison shared notehead, stems both ways | new (§1.1) | **HARD** where it occurs (LilyPond's automatic merge, and orchestration practice for `a2`/divisi return) | This is the ONE case where "two stems, one notehead, zero horizontal separation" is CORRECT and expected — worth building as a named exception rather than a fusion fault |
| Two-stem fusion boundary (§2) | new | **NOT A RULE — a measured detector artefact.** Nothing here should be read as an engraving convention; it describes where THIS project's stroke detector currently confuses two stems for one | Yes, and it is the only entry in this table that is entirely about measurement rather than about engraving |

---

## 4. PERIOD AND PUBLISHER — 19th-century German plates vs modern engraving

Sean's plates are Litolff, Breitkopf & Härtel, Simrock, Peters — 19th-century
German engraved editions, not modern Finale/Sibelius/Dorico/LilyPond output.
Three concrete divergences surfaced in the sources above, and this project's
own `benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md`
already records analogous publisher-level divergences for brackets and
system grouping — the same caution applies to stems:

1. **Beaming-across-the-bar-middle is a MODERN rule, and Gould says so
   explicitly**: "Music from the Classical and Romantic periods frequently
   uses this beaming – the context makes it clear that cross rhythm is not
   intended." A beam that appears to violate `[L22]` on a Litolff or
   Breitkopf plate is very plausibly period-correct, not evidence of a
   segmentation error. **This directly bears on any rule that treats
   mid-bar beam crossings as an anomaly.**

2. **Breitkopf & Härtel's own history is a movable-TYPE tradition before it
   was an engraving one.** Johann Gottlob Immanuel Breitkopf's mid-18th-
   century system built up a note from separate pieces of type — a
   notehead-and-stem "mosaic" piece with stems of varying pre-cut lengths,
   usable right-side-up or inverted, with separate flag pieces attachable to
   the stem end. By the early 19th century the firm had moved to engraving
   and "abandoned Immanuel Breitkopf's complex hand-set movable type," but
   sources note "some features of the Breitkopf house style can still be
   seen" in the engraved output. **No specific stem-length or stem-thickness
   number survives from this transition in the sources searched — this is a
   real gap, not a confirmed measurement, and is flagged as such below.**

3. **The whole 3.5 sp / 2.5 sp / 8.0 sp length family (`[C13]`, `[L11]`,
   `[L13]`) is stated by Gould and LilyPond as MODERN typographic defaults.**
   This project's own measured cap (8.0 sp, an 11× cliff in a real
   population) was fit on **13 pages of 8 editions** spanning multiple
   publishers and periods, not isolated to one plate — so it is the
   strongest cross-publisher number in the whole stem family, but it has
   never been checked publisher-by-publisher for whether Litolff and
   Breitkopf cluster around the SAME nominal 3.5 sp default or around
   different house norms. **Not established.**

4. **The two-stem-fusion register in §2 is itself a period/publisher
   comparison, and the two plates DISAGREE about incidence**, though not
   about mechanism: on the same fusion test, Litolff shows both-end
   overshoot in 18% of flagged runs against Breitkopf's 50% — consistent
   with this project's general finding elsewhere in the registry that
   Litolff is the *"low-res bitonal"* end of the corpus and Breitkopf the
   denser, better-inked one. **A rate difference this large between two
   plates of the same nominal period is itself evidence that "19th-century
   German engraving" is not one population** — publisher, print run, and
   scan quality all move the numbers, and no single exception-space entry
   above should be treated as portable across the whole 19th-century German
   corpus without re-measurement per publisher.

---

## 5. WHAT IS NOT ESTABLISHED

- **No minimum legal clear distance between two genuinely separate stems is
  stated anywhere in the literature searched.** The 0.5–0.9 staff-space band
  in §2 is a measurement of where a specific detector on two specific plates
  currently confuses two stems for one — it describes the INSTRUMENT'S blind
  spot, not an engraving rule, and must never be quoted as if it were.
- **Cross-staff beaming stem collisions (§2.1d) have zero measured reach on
  this project.** No population has ever been isolated.
- **Chord-vs-voice stem collision (§2.1c) is inferred, not measured**, from
  the union of two separately-measured mechanisms.
- **The publisher/period comparison in §4 rests on general historical
  sources, not on a direct measurement of stem length, thickness, or
  fusion-distance BY PUBLISHER.** Only the fusion-rate difference (18% vs
  50%) is a direct, controlled, same-method comparison; everything else in
  §4 is qualitative.
- **`[C15]` (no stem → whole note) has never been tested here as a
  positive-evidence discriminator** — only asserted from the literature and
  from the fact that whole notes correctly appear in a `no_stem` population.
- **The grace-note stem-length coincidence with Gould's absolute floor (both
  ≈2.5 sp) has not been tested for confusability on any real plate** — it is
  a numeric observation from combining two independent sources, not a
  measurement.
- **The unison-shared-notehead exception (§1.1, §3) has never been checked
  against this project's own ownership-contest machinery**, which already
  resolves a related but different problem (one piece of ink read twice
  across two staves) — whether the SAME machinery would correctly leave a
  genuine `a2` unison alone is untested.
- **Beaming-follows-the-metre as a period-correct exception (§4.1) has never
  been checked against how often this project's own beam-boundary geometry
  actually crosses a bar's middle on a Litolff or Breitkopf plate** — the
  claim from the literature is qualitative; no incidence rate exists here.
- **Every "MEASURED HERE" number quoted from `omr-stem-attribution-2026-09`,
  `omr-stem-pair-rule-2026-09`, `omr-stem-direction-2026-09`,
  `omr-stem-stroke-2026-09`, and `omr-stem-attachment-2026-09` is n = 1–2
  documents, at most 2 publishers, and none of it has been checked against
  the printed page beyond a small hand-adjudicated sample** (those
  benchmarks' own FINDINGS.md files record this explicitly; nothing in this
  document upgrades that status).
- **This document does not propose shipping anything.** Several parallel
  branches (`claude/stem-run-split-2026-09-20`, `claude/stem-pair-rule`,
  `claude/stem-attachment-convention-2026-09`, `claude/stem-stroke-reader-2026-09`)
  are actively measuring and repairing pieces of the two-stem-fusion problem
  described in §2 as production code; this document is reference material
  for that work and for future exception-space questions, not a replacement
  for it.

---

## 6. SOURCES

**Primary literature (as cited throughout; none reproduced beyond short
quoted phrases under fair-use commentary):**
- Elaine Gould, *Behind Bars: The Definitive Guide to Music Notation* (Faber
  Music, 2011) — cited via the registry's existing page references (p.14,
  p.15, p.22, p.153) and via search-surfaced summaries where the registry
  had not already extracted a page.
- Wikipedia, *Stem (music)* — https://en.wikipedia.org/wiki/Stem_(music)
- Wikipedia, *Behind Bars (book)* — https://en.wikipedia.org/wiki/Behind_Bars_(book)
- Wikipedia, *A due* — https://en.wikipedia.org/wiki/A_due
- Wikipedia, *Tremolo* — https://en.wikipedia.org/wiki/Tremolo
- Wikipedia, *Breitkopf & Härtel* — https://en.wikipedia.org/wiki/Breitkopf_%26_H%C3%A4rtel
- Wikipedia, *Johann Gottlob Immanuel Breitkopf* — https://en.wikipedia.org/wiki/Johann_Gottlob_Immanuel_Breitkopf
- LilyPond Notation Reference v2.23–2.25, *Beams*, *Multiple voices*,
  *Special rhythmic concerns*, *Common notation for keyboards*, *Cross-staff
  stems* (snippets) — https://lilypond.org/doc/v2.24/Documentation/notation/
- LilyPond source, `scm/lily/define-grobs.scm` (stem-shorten, beamed-lengths,
  neutral-direction, beam-thickness) — cited via registry `[L11]`/`[L13]`/
  `[L15]`/`[L20]`, re-confirmed by search.
- Dorico notation reference (Steinberg), *Stem direction*, *Divisi* —
  https://www.steinberg.help/r/dorico-pro/6.1/en/dorico/topics/notation_reference/notation_reference_stems/
- SMuFL specification, *glyphsWithAnchors*, *Metrics and glyph registration*
  — https://w3c.github.io/smufl/latest/specification/glyphswithanchors.html
- MEI Guidelines / Verovio issue tracker on grace-note stem length —
  https://github.com/rism-digital/verovio/issues/419
- Hansen Media, *Conventions of Notation* (cue notes) —
  https://hansenmedia.net/courses/orchestration/lessons/conventions-of-notation/

**This project's own measurements (registry-adjacent, cited by benchmark
directory):**
- `docs/engraving-conventions.md` — the 125-entry registry, "Stems & beams"
  section (18 entries) and the ⚠️ correction notes attached to `[C9]`,
  `[C10]`, `[C13]`, `[C14]` in particular.
- `benchmarks/omr-stem-attachment-2026-09/FINDINGS.md`
- `benchmarks/omr-stem-direction-2026-09/FINDINGS.md`
- `benchmarks/omr-stem-attribution-2026-09/FINDINGS.md`
- `benchmarks/omr-stem-pair-rule-2026-09/FINDINGS.md`
- `benchmarks/omr-stem-stroke-2026-09/FINDINGS.md`
- `benchmarks/omr-stem-ink-2026-09/FINDINGS.md`
- `benchmarks/omr-staged-duration-beams-2026-09/FINDINGS.md`
- `benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md`
  (publisher-variation methodology, cited by analogy in §4)
- `docs/ask-first-conventions.md` (discipline this document follows for
  distinguishing MEASURED from ASSERTED)

---

## 7. ADDENDUM — MPA and MOLA, read directly (2026-09-20, second pass)

Two more primary sources were located and read as full text (via `pdftotext`,
not search snippets, so these are direct quotes rather than search
summaries):

**Music Publishers Association, *Standard Music Notation Practice*
(1966/1993)** — https://www.mpa.org/wp-content/uploads/2018/06/standard-practice-engraving.pdf

> "All single notes with single stems starting on the middle line of the
> staff and higher are stemmed down. A downstem is always attached to the
> left side of the note head. All single notes with single stems starting in
> the second space of the staff and lower are stemmed up. An upstem is
> always attached to the right side of the note head."

This restates `[C9]`+`[C10]` with one refinement worth adding to the
registry's own wording: **the pivot is stated as the MIDDLE LINE itself
being the boundary of the down-stem zone** (middle line and above → down),
which matches `[C10]`'s "at or above the middle line" phrasing exactly — no
new information, but a second independent primary source confirming the
same boundary rather than a derived one.

> "Single stems are exactly one octave in length. When there is more than
> one note head on a stem, as in chord, the stem length is calculated from
> the note closest to the end of the stem."

This is the **third independent primary source** (after Gould and the
registry's own measurement) for chord stem length being set by the OUTER
note, and it is worded as an absolute ("exactly one octave"), sharper than
Gould's "standard length" framing — another data point that a plate's
in-staff stems should cluster tightly around 3.5 sp rather than merely
tending toward it, which this project has never separately verified by
publisher (§4, "not established").

**Major Orchestra Librarians' Association, *Music Preparation Guidelines for
Orchestral Music*** — https://www.ericrichards.com/molaguidelinesbrochure2006.pdf

> "String parts should be created with one part per section. Complicated
> string divisions should be written on separate staves. Avoid dividing the
> music for the string section into multiple parts unless necessitated by
> multiple and continuous division of the voices."

This is the librarians'-side confirmation of the **divisi exception** named
in §1.1/§3: a divisi split is not merely "two voices on one staff" in the
ordinary `[L17]` sense — MOLA's own guidance is that a *sustained* divisi
should be given its OWN STAFF rather than resolved with opposing stems on
one staff, and opposing-stem divisi on a single staff is reserved for
brief, incidental splits. This sharpens §1.1's divisi/`a2` row: **the
two-stems-on-one-notehead and two-voices-opposing-stems shapes this project
measures on Litolff/Breitkopf are, by this convention, evidence of a BRIEF
split, not a sustained one** — a sustained divisi would more likely show up
as an added staff in the system, which is a structural (system-grouping)
fact rather than a stem fact, and is out of this document's scope.

> "In hand-copied parts it is recommended that all stems, beams, and bar
> lines be ruled with a straightedge, especially multiple-staff harp and
> keyboard parts."

Confirms that stem straightness is a DRAWING instruction (a straightedge
requirement), corroborating `[C56+L74]`'s registry framing of "a barline is
a straight line, not a vertical one" — the same discipline applies to a
stem, which is the geometric premise every fusion measurement in §2 already
assumes (a genuine stem is a straight run; a curved or angled run is a
compound object).

⚠️ Neither the MPA nor the MOLA document (both read in full) states a
numeric collision distance for two adjacent stems, a cross-staff beaming
number, or a tremolo-stroke number. This corroborates §2.0's finding that
the printed literature is genuinely silent on the adjacency question — it
is not a gap in this search, but a real absence in the sourced literature.

Ross's *Art of Music Engraving and Processing*, Gardner Read's *Music
Notation: A Manual of Modern Practice*, and Stone's *Music Notation in the
Twentieth Century* are catalogued (Internet Archive, Google Books, WorldCat)
but not full-text searchable or fetchable from this session — their content
could not be verified directly and nothing is attributed to them beyond
their existence and general subject matter. **This is a real source gap**,
not a claim about their content.
