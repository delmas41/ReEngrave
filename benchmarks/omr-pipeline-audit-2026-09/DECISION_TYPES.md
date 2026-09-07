# The decision-TYPE axis — round 1

**Agent II, 2026-09-07 overnight audit.** Sean's question: *"analyze each decision
point … to determine effectiveness as well as explore what other information could
be helpful … Ask again if the type of decision — gating / probability etc — is the
best way to decide, and what are the downstream implications of the decision
type."*

⚠️ **This is a SCOPING round.** The schema (§1) plus two slices worked completely
(§3 the clef precedence ladder, §4 glyph ownership). The rest of the pipeline is
not covered and is not guessed at — §7 says what was left out, and §7.1 names the
round-2 candidate the coordinator's verify pass surfaced.

⚠️ **No pipeline behaviour changed.** Everything is a read-only probe over
committed artefacts plus source read against the tree. Probes and captured output
are under `probe/` and `out/`; each runs in seconds and writes nothing.

⚠️ **Tree stamp, and one correction to my own working copy.** All source reads and
all line numbers below were re-derived from the main checkout at **`350f0532`**
(after the coordinator's rebase: `docs/architecture-decision-map.md` at 1,629
lines, `tools/omr/transcribe.py` at 5,314). **Several line numbers in my brief had
drifted and are corrected here** — `_drop_clipped_notehead_fragments` is `:539`
not `:558`, `_drop_unladdered_noteheads` is `:3070` not `:3098`, the ownership
call sites are `:4715`/`:4722` not `:4682`/`:4689`. The clef-ladder numbers
(`:1594/:1604/:1656/:1708/:1769/:1789`) are correct as given.

⚠️ **Artefact stamp.** The committed transcriptions I measure were built by an
earlier tree. That is the normal substrate for this kind of probe (the
additive-vs-gated survey used the same files) and it is load-bearing exactly once
— in §3.2, where a guard landed after the fixtures were stamped. That case is
reconciled against the current code, not assumed.

⚠️ **What this round does NOT do.** It does not rebuild the decision map, and it
re-recommends no conversion
[`benchmarks/omr-additive-vs-gated-2026-09/FINDINGS.md`](../omr-additive-vs-gated-2026-09/FINDINGS.md)
measured and refused. I disagree with that survey nowhere. It also does not
re-report anything corrected by the map's own verification pass (`fbbd09c1`) — I
read that commit in full before writing.

---

## 0. The one-line answer

> **The pipeline's house style is the PRECEDENCE LADDER writing into a SCALAR
> SLOT, and its cost is not the ranking — it is the container. Both slices are
> dominated by one property no existing document classifies: IRREVERSIBILITY.
> Measured, `_dedupe_cross_staff_detections` parks 12.2% of its 4,521 verdicts
> for possible reversal and 0% in the shipped default; and the clef argmax
> overturns a staff's clef mid-page on 11 of 193 scan staves from a single
> detection at confidence as low as 0.32, of which the existing guard reaches
> 3 — and 0 with the shipped defaults.**
>
> **The type question has an answer the additive/gated framing cannot reach.**
> At neither of this round's worst sites is the right change gate → additive or
> gate → probability. A cell needs one clef and a glyph needs one owner, so the
> *commitment* is right. Two other things are wrong, and they are different
> repairs:
>
> 1. **SCALAR → RECORD.** The commitment overwrites its own evidence instead of
>    standing beside it. (`clef_final` is the counter-example that proves the
>    point: the one place a record IS kept, it is kept badly — 9 of its 20
>    occurrences are stale — and its only reader is its own keeper.)
> 2. **ALLOWLIST → SELF-CONTRADICTION TEST.** Where a guard exists, it is a
>    hand-listed set of two `(instrument, from-clef, to-clef)` triples. The
>    signal it is standing in for — *this staff contradicted its own header
>    reading, at confidence 0.32* — needs no instrument, and therefore is not
>    subject to the identity gate that (correctly) blocks the instrument route.

---

## 1. The schema, and the three changes I argue for

The brief's eleven fields are the right axes. Three changes, each forced by
something measured in §3 or §4 rather than by taste.

### 1.1 The schema as used here

| # | field | notes |
|---|---|---|
| 1 | **DECISION** + `file:line`, one sentence | |
| 2 | **TYPE** | hard gate · veto · threshold · raw argmax · precedence ladder · unweighted vote · additive score · abstention · deferral · **allowlist** |
| 3 | **CONSTRAINT or OPINION** | the additive-vs-gated §1 test — what licenses or condemns a gate |
| 4 | **EFFECTIVENESS** = reach × precision | reach MEASURED wherever an artefact can answer it, else `UNMEASURED` + the probe that would |
| **4b** | ⚠️ **MEASURED-ON vs FIRES-ON** | **NEW.** Which family the rule's evidence came from, and which family it fires on |
| 5 | **WHAT THE TYPE DESTROYS** | one of four named quantities (§1.4), never "information" |
| **6** | ⚠️ **REVERSIBILITY** | REVERSIBLE · IRREVERSIBLE-BY-DELETION · IRREVERSIBLE-BY-QUANTISATION |
| **6b** | ⚠️ **RECOVERY PATH, and is it ON** | **NEW.** A distinct state: reversible in principle, irreversible as shipped |
| 7 | **RECORDS ITS REFUSAL?** | yes / no / **yes-but-unreliable** (§3.3 forced the third value) |
| 8 | **DOWNSTREAM IMPLICATIONS OF THE TYPE** | who would have used what was destroyed; does a later stage re-derive it; does it make a later decision *look* unambiguous |
| 9 | **BETTER TYPE, and what must be TRUE for it to pay** | a specific condition, not a preference |
| 10 | **BLAST RADIUS + an A/B that can FAIL** | flag-off byte-identity is the project standard |
| 11 | **PRIORITY** = reach × per-firing cost × cheapness | |

### 1.2 Change 1 — REVERSIBILITY needs a companion field, because "reversible" has two states

`_dedupe_cross_staff_detections` parks rank-0 notehead verdicts in `deferred`
(`transcribe.py:2770-2790`) so `_apply_roster_range_veto` can reverse them once
identity exists. That path is real code and is measured — and it is
`OMR_ROSTER_RANGE_VETO`, **default `off`** (`transcribe.py:2619`), shipped off at
52 swaps for +24 edits. The honest classification of those 550 verdicts is
neither "reversible" nor "irreversible": it is *reversible in principle,
irreversible as shipped*. One field would have to pick one and would mislead
either way.

The same shape appears twice more in this round — the mid-staff clef veto behind
`OMR_INSTRUMENT_CLEF_DEFAULT` (§3.2) and `OMR_CONTEST_DUMP` (§4.3c). Three
independent instances is enough to make it a field.

### 1.3 Change 2 — MEASURED-ON vs FIRES-ON, because I found a live case where they are opposite

`_UNLADDERED_NOTEHEAD_MAX_CONF = 0.65` (`transcribe.py:2963`) is justified by an
empty gap: *"fakes 0.45-0.53 against 0.76+ for every real one"*. That gap was
measured on **three ENGRAVED works** —
[`benchmarks/omr-ned-2026-08/LADDER_EVIDENCE_2026-09-01.md:72-85`](../omr-ned-2026-08/LADDER_EVIDENCE_2026-09-01.md)
names them. Measured here, the rule fires **351 times on scans and 28 on
engravings**: 12.5× more often on the family it was *not* measured on, where the
surviving population is continuous through the constant (§4.4). A schema
recording only "sits on a measured gap" marks this green. It is not green.

The field generalises: this project's recurring trap is a rule priced on one
family or publisher and shipped for all — *"document roster transfer scored
Simrock 45/45 and Litolff 2/50, same rule"*
(`docs/handoff-probability-gates-2026-09-05.md` §2).

### 1.4 Change 3 — field 5 must name the quantity, and there are exactly four kinds

Making this closed rather than free-text is what let §3 and §4 be compared at all:

| destroyed | what it was |
|---|---|
| **the margin** | how far the winner beat the runner-up |
| **the runner-up** | the second candidate itself |
| **the disagreement** | that two readers said different things at all |
| **the object** | the detection / reading, deleted |

The first three are recoverable by writing them down — byte-identical to output.
The fourth is not, and that is why §6 ranks deletion sites above quantisation
sites at equal reach.

### 1.5 One thing I deliberately do NOT add

A "should this be a probability" column. The standard is settled and I apply it
rather than re-litigate it: **P(name) ECE 0.1277, P(set) 0.1301, top bin
promising 0.989 and delivering 0.692.** Every recommendation below is either
*record the number* or *accumulate signed evidence in arbitrary units with a
threshold*, which is what `slots._pair_score` already does. Neither is a
probability and neither is called one.

---

## 2. Method and substrate

| substrate | what it is | size |
|---|---|--:|
| `benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json` | committed scan transcriptions | 11 files, **193 staves**, 2,235 cells, 16,706 kept detections |
| `benchmarks/omr-orchestral-e2e/fixtures/*.omr.json` | committed engraved transcriptions | 11 files, **224 staves**, 1,517 cells, 8,523 kept detections |
| `benchmarks/omr-additive-vs-gated-2026-09/out/contests/*.contests.json` | the 20-row scan gate under `OMR_CONTEST_DUMP=1` | 20 rows, **4,521 contested pairs** |
| `benchmarks/omr-scan-e2e-2026-09/fixtures/*.truth.musicxml` | hand-verified truth windows | used only in §3.2 |

⚠️ **Two denominators, not mixed.** "of 193 staves" is the 11-file scan set; "of
4,521 pairs" is the 20-row set — the same convention as the additive-vs-gated
survey, for the same reason.

⚠️ **A survivor sample is biased and I say so at each use.** A committed
transcription holds what the pipeline KEPT. It can prove a population is
continuous across a threshold (§4.4); it cannot show what was deleted, because
those objects are gone. That asymmetry is itself a finding about the type (§5.3).

⚠️ **A00 applied.** Nothing here concludes a mechanism is wrong from a score.
§3.2 is the only place a decision is called wrong, and it is called wrong against
hand-verified truth MusicXML — not against a metric.

---

## 3. SLICE A — the clef precedence ladder

### 3.1 Reach of every rung, measured

`out/probe_clef_ladder_reach.txt`. Rung order in code: argmax over clef
detections (`transcribe.py:1594-1617`) → CV locator (`:1656`) → detector-on-header
(`:1708`) → specialist (`:1769`) → dossier (`:1789`).

| rung | scan (193 staves) | engraved (224) |
|---|--:|--:|
| **detector argmax** | **144 (74.6%)** | **212 (94.6%)** |
| CV locator | 5 (2.6%) | 0 |
| detector-on-header | 14 (7.3%) | 0 |
| specialist | 0 (not configured) | 0 |
| dossier | 0 (gate runs dossier-free) | 10 (4.5%) |
| **nothing read → positional default** | **30 (15.5%)** | 2 (0.9%) |

The 30 defaulted scan staves come out `treble` 20, `bass` 8, `alto` 2.

**Reading:** five rungs, and rung 1 answers three quarters of scan staves and
nineteen twentieths of engraved ones; everything below it is a 9.8% / 4.5% tail.
So the ladder's *ordering* is nearly irrelevant to the outcome. **The
consequential decision is rung 1's own internal one — a raw argmax at `:1604`.**

### 3.2 ⚠️⚠️ THE FINDING — a single mid-staff detection overturns a staff's clef, and the guard that exists reaches 3 of 11 (0 as shipped)

`transcribe.py:1594` initialises `best_clef_conf = -1.0`; `:1604` takes the
maximum with no floor. That function runs **once per measure cell**, and its own
comment (`:1610-1614`) says the per-cell tracking is deliberate: *"it tracks THIS
cell's reading, not the inherited `active_clef`"*. Consequence: a clef detection
in a **non-first** cell overwrites `active_clef` for the rest of the staff, at
any confidence, with no comparison against what that staff's own header already
read.

Every occurrence in the 11 committed scan transcriptions
(`out/probe_clef_midstaff_flips.txt`) — each triggered by exactly ONE detection,
the only clef detection in its cell:

```
row                    staff  instrument   change            at   class       conf   identity src
beethoven-575951-p2     s8    Violin       treble -> bass    m7   clefF       0.68   score_order
beethoven-575951-p2     s20   Violin       alto   -> treble  m1   clefG       0.58   score_order
beethoven-984073-p1     s9    Viola        alto   -> bass    m4   clefF       0.59   label
beethoven-984073-p1     s11   Contrabass   bass   -> treble  m3   clefG       0.66   score_order_ambiguity
beethoven-984073-p2     s8    Violin       treble -> bass    m6   clefF       0.73   score_order
brahms-317803-p1        s9    Violin       treble -> bass    m3   clefF       0.32   label
brahms-317803-p1        s12   Cello        tenor  -> bass    m5   clefF       0.82   label
brahms-317803-p2        s2    Clarinet     treble -> bass    m3   clefF       0.35   label
brahms-317803-p2        s11   Viola        alto   -> bass    m5   clefF       0.41   label
mahler-p3               s6    Trombone     bass   -> tenor   m3   clefCTenor  0.60   label
mahler-p3               s10   Violin       treble -> tenor   m3   clefCTenor  0.55   label
```

**11 of 193 scan staves (5.7%). 0 of 224 engraved staves.**

**Adjudicated against the truth MusicXML** — the same hand-verified windows the
scan gate scores against:

| row | mid-part clef changes in TRUTH | verdict |
|---|---|---|
| `beethoven-984073-p1` | **none, across 18 parts × 16 measures** | both flips **WRONG** |
| `brahms-317803-p1` | exactly one: measure index **5**, sign **F** (bass) | s12 Cello tenor→bass at **m5** — **CORRECT** on index and target. s9 Violin treble→bass at m3 matches nothing — **WRONG** |
| `mahler-p3` | one: measure index 4, C clef line 4 (tenor) | one of the two m3 tenor flips is plausibly it, the other is not — **not adjudicated**, the part↔staff join is not established |
| `beethoven-575951-p2`, `-984073-p2`, `brahms-317803-p2` | changes exist, at measure indices past the window's usable range | **not adjudicated** |

**At least one flip is right, at least three are demonstrably wrong, and nine of
eleven are musically implausible on their face** (Violin → bass ×3, Violin →
tenor, Viola → bass ×2, Contrabass → treble, Clarinet → bass).

#### ⚠️ A guard EXISTS, and its reach is the finding

`git log --all -S "MID_STAFF_CHANGE_VETOES" -- tools/omr/` → one commit
(`9051487b`). `clef_correction.veto_implausible_clef_changes` (`:460`) walks each
staff's measures and undoes a mid-staff change whose
`(instrument, from, to)` triple is listed. The table is
`clef_correction.py:444-447` and it has **two entries**:

```python
MID_STAFF_CHANGE_VETOES = {
    ("Violin", "treble", "bass"),
    ("Viola",  "alto",   "bass"),
}
```

Two further conditions: the staff's `instrument_source` must be `"label"`, and
the whole tier is behind `OMR_INSTRUMENT_CLEF_DEFAULT`, **default off**
(`contextual.py:1003`, call site `:1517-1521`).

Applied to the eleven measured flips:

| gate | flips it reaches |
|---|--:|
| triple is in the table | 5 of 11 |
| … **and** `instrument_source == "label"` | **3 of 11** (beet984073-p1 s9, brahms-p1 s9, brahms-p2 s11) |
| … **and** `OMR_INSTRUMENT_CLEF_DEFAULT` on | **0 of 11 as shipped** |

Of the eight it does not reach, **two are correct** and the table is right to
omit them (Cello tenor→bass, Trombone bass→tenor). The remaining **six are
implausible and escape**: three because the triple is not listed (Violin
alto→treble, Clarinet treble→bass, Violin treble→tenor), two because the
identity source is `score_order` although the triple IS listed, one for both
reasons.

⚠️ **The identity gate is CORRECT and I am not proposing to widen it.** It is
defended by held-out evidence reproduced twice independently — *Viola read as
Violin ×3* — and by a measured regression when a `score_order` identity was
admitted next door. `clef_correction.py:476-497` states this at length and the
statement holds.

**That is precisely why the repair is a different decision.** The evidence that
covers all six escapees names no instrument at all: *this cell's clef reading
contradicts the reading this same staff's own header produced, and it does so at
confidence 0.32*. It needs no identity, so the identity gate does not apply to
it — and the shape is one the codebase already uses:
`contextual._fill_defaulted_clefs` takes a staff's clef from the same part's
reading on another system (measured 48/52 → 49/52), i.e. two independent looks at
one fact, which the map's §4.1 provenance rule expressly permits.

**What a confidence floor would do on this sample:** 0.40 blocks 2, 0.60 blocks
6, 0.70 blocks 9, 0.80 blocks 10. The one flip corroborated correct against truth
is the **highest-confidence of the eleven** (0.82). ⚠️ **n=1 correct. That is the
observation that ranks the item; it is NOT a proposal for a constant**, and the
corpus is the prerequisite.

⚠️ **A00 discipline, explicitly.** (1) The comparison is valid — the shipped
fixtures, read against their own committed truth. (2) No metric is charging: the
claim is that a Violin staff is pitched in bass clef for four measures, a fact
about the output. (3) A downstream consumer can use the right answer —
`pitch_resolver` uses whatever `active_clef` holds. (4) Only then, the mechanism —
and the mechanism is *not* "the detector is wrong". The detector is allowed to be
wrong. **The mechanism is that an unfloored scalar overwrite is the wrong TYPE
for a decision this consequential, and that its existing guard is an allowlist
where the available evidence is a contradiction.**

### 3.3 ⚠️ `clef_final` is the record — and 9 of its 20 occurrences are stale

The map's newly-added stage-8a row is right that a mid-staff change is recorded:
`transcribe.py:4674-4679` writes `clef_final` when the staff's end clef differs
from its first-cell clef. Measured, **20 of 193 scan staves carry it**, and it
covers all 11 flips. So "the flip goes unrecorded" would be false and I do not
claim it.

What is true is worse in a more specific way:

- **9 of the 20 are stale.** On those staves `clef_final == staff["clef"]` and
  *every* measure carries the same clef — the field announces a change that no
  surviving measure shows (Dvořák p5 ×7, Mahler p3 ×2). Both of those systems
  report `n_measures_dropped_as_furniture = 1`, and
  `_drop_furniture_measures` reassigns `staff[field] = kept[0][field]` for
  `clef`/`key_signature`/`time_signature` when a LEADING measure is dropped
  (`transcribe.py:3062-3065`) — which makes `staff["clef"]` agree with the
  post-change measures while `clef_final` keeps its earlier value.
  ⚠️ **Strongly indicated, not proven by a controlled run**: the correlation is
  2 of 2 systems and the mechanism is in the code, but I did not A/B it.
- **Its only reader is its own keeper.** The map's new CONSUMED BY column states
  it and I verified it: `grep -rn clef_final tools/omr/ backend/ frontend/src`
  outside tests returns `clef_correction.py:550-552`, which reads it *solely to
  keep it consistent* after a veto, plus the two write sites. Not `export.py`,
  not the backend, not the frontend.
- **It records the fact and not the evidence.** No measure index, no confidence,
  no runner-up. So the record cannot distinguish the Brahms Cello's correct
  0.82 change from the Brahms Violin's spurious 0.32 one — which is exactly the
  discrimination a consumer would need.

This is why field 7 needed a third value. *"Records its refusal"* is not binary:
a record that is stale 45% of the time, carries no evidence, and is read only by
its own maintainer is closer to no record than to one.

### 3.4 The argmax's contest population — the margin, the runner-up and the disagreement

`out/probe_clef_argmax_contests.txt`, per cell:

| | scan | engraved |
|---|--:|--:|
| cells with ≥1 clef detection | 197 | 230 |
| cells with **≥2** — a genuine contest | **39** | **90** |
| … margin < 0.05 | 9 | 14 |
| … margin < 0.10 | 17 | 25 |
| … **runner-up a DIFFERENT class** | **12 of 39** | **19 of 90** |

Different-class contests include `clefG 0.90 / clefF 0.90` — a dead heat between
treble and bass — plus `clefCAlto 0.40 / clefG 0.34` and `clefF 0.92 /
clefCTenor 0.88`. **Nothing is recorded.** There is no `clef_candidates` list,
unlike `pitch_candidates` at the sibling site, and
`git log --all -S "clef_candidates" -- tools/omr/` returns **zero commits on any
branch** — never built, never removed. `git log --all -S "min_clef_conf"` is
likewise empty: no confidence floor for a clef has ever existed here.
`best_clef_conf` appears in exactly one commit (`14087860`, Phase 4a) and has
never been revisited.

### 3.5 The locator gate is a PRESENCE gate, and ≥22 scan cells silence it on sub-0.60 evidence

`transcribe.py:1656` — `if read_clef and locate_c_clefs and clef_source is None`.
The gate is the *existence* of a detector clef, not its strength
(`out/probe_clef_winner_confidence.txt`):

| winning clef detection confidence | scan (n=197) | engraved (n=230) |
|---|--:|--:|
| median | 0.904 | 0.969 |
| **under 0.60** | **22** | 5 |
| under 0.40 | 10 | 3 |

So on at least 22 scan cells a detector clef under 0.60 silences three downstream
readers at once — the CV locator (which reads C clefs by *geometry*, not by a
training distribution), the header-detector rung and the specialist. On ten of
them the silencing evidence is under 0.40.

⚠️ **Reach, not accuracy**, per this project's own reach-before-accuracy rule. It
says how many staves a floor could reach. It does **not** say the locator would
have been right on them; the locator's own recorded trade is *"8 false positives
removed for 20 declined C clefs"*, and its five firings are its entire production
reach.

### 3.6 `clef_geometry.resolve_clef` — a measurement and a guess return the same shape

`clef_geometry.py:239`. The good path returns
`ClefRead(source="geometry", residual=…)` (`:292`); where the family is unknown,
the anchor is missing, the snap fails, or `residual > max_residual`, it returns
`ClefRead(name=fallback, source="class", line=None)` (`:275`, `:279`, `:288`).
The argmax at `:1604` inspects **neither `source` nor `residual`** — a geometry
read that measured the named line and a class-label fallback that measured
nothing are the same object to the caller, ranked purely by the detector's
confidence in the *box*.

**UNMEASURED, and measurable:** record `source` and `residual` at `:1607`; the
question is what share of the 144 scan / 212 engraved detector-supplied clefs are
fallbacks rather than measurements. The map's new CONSUMED BY column already
states the consumer side (`ClefRead.residual` and `.line` → `probe`; `.family` →
`NOBODY`).

### 3.7 Slice A rows

| # | 1 DECISION | 2 TYPE | 3 C/O | 4 REACH (measured) | 4b measured-on / fires-on | 5 DESTROYS | 6 REVERSIBILITY | 6b RECOVERY | 7 RECORDS REFUSAL |
|--:|---|---|---|---|---|---|---|---|---|
| **A1** | `transcribe.py:1604` — the cell's clef, argmax with no floor, re-run per cell | **raw argmax** | OPINION | supplies 144/193 scan, 212/224 engraved; contested in 39 / 90 cells; **overturns a staff mid-page 11×** | n/a / flips are 11 scan : 0 engraved | **the margin, the runner-up, the disagreement**, and by overwriting `active_clef`, **the object** | **IRREVERSIBLE-BY-DELETION** for the pitches already resolved; the staff-scope clef pair survives | `clef_final` (§3.3) — no consumer | **yes-but-unreliable**: 9 of 20 stale, no evidence carried |
| **A1b** | `clef_correction.py:460` — undo an implausible mid-staff change | **allowlist** of 2 `(instrument, from, to)` triples + identity gate + a default-off flag | OPINION (the triples), CONSTRAINT (the identity gate — measured, keep) | **3 of 11** flips by triple+source; **0 as shipped** | Beethoven/Brahms string staves / both | the change it undoes is restated; the *unlisted* changes leave no trace | REVERSIBLE (it is itself the reversal) | `OMR_INSTRUMENT_CLEF_DEFAULT`, **off** | yes — `clef_change_veto` on the staff |
| **A2** | `transcribe.py:1656` — may the CV locator speak | **hard gate on presence** | OPINION dressed as structure | locator supplies 5/193; **≥22** scan cells silence it on conf < 0.60, 10 under 0.40 | n/a | the losing reader's entire opinion | IRREVERSIBLE-BY-DELETION (the locator never runs) | none | **no** |
| **A3** | `:1708` header rung, `:1769` specialist rung | precedence ladder, gap-fill | OPINION | header rung 14/193 scan, 0 engraved; specialist 0/0 | n/a | **agreement** — two rungs saying the same thing is worth nothing | REVERSIBLE (nothing deleted; a rung simply never runs) | none | **no** |
| **A4** | `:1789` dossier override — overwrites even a read clef | **veto / override** | **CONSTRAINT** (external truth about the work) | 10/224 engraved, 0 scan | n/a | nothing | n/a | n/a | **YES — `clef_overridden_by_dossier`, the only real record in the slice** |
| **A5** | `clef_geometry.py:239` — geometry read or class fallback | abstention **collapsed into the same return type** | OPINION | UNMEASURED (§3.6) | n/a | the reading's **provenance** and its residual | IRREVERSIBLE-BY-QUANTISATION | none | partially — `residual` is on the object and no caller reads it |
| **A6** | `clef_locator` veto chain — `header_ink.py:314`; `clef_locator.py:480`, `:771`, `:795`, `:804`, `:821`, `:843`, `:850` (`_has_f_clef_dots`, def `:547`), `:865` | **chain of hard vetoes**, each destroying its own measurement in the expression that forms it | OPINION | 5 located staves; the *rejections* are unmeasured in production | n/a | **the margin at seven continuous quantities** (`bw`,`bh`,`aspect`,`cx/w`,`dx`,`dy`,`dw`), plus `symmetry` computed at `:840` and dropped at the `:843`/`:850` refusals | IRREVERSIBLE-BY-DELETION | none | **the recorder EXISTS and no pipeline call site switches it on** — `grep -rn "trace=" tools/omr/*.py` returns nothing; sites are `transcribe.py:1677`, `:4286` |

**Fields 8–11 for the two that matter.**

**A1 / A1b — downstream implications of the type.** Every note after the flip is
pitched against the new clef. `staff_dict["clef"]` is the *first* cell's
(`transcribe.py:4551`), so the staff record and the measures disagree, and
`export._staff_measures_xml` takes `measure.get("clef") or clef` — the measure
wins, and the exported part changes clef with nothing distinguishing a real
change from an overwrite. Further downstream, `clef_correction.propose_clef` is
later asked whether this staff's clef is wrong and has access to none of it: not
the runner-up, not the margin, not that the staff contradicted itself. It
re-derives an answer from register instead — the map's "forces a later stage to
re-derive the same fact" pattern — and the additive survey measured that path
producing **5 proposals on 193 scan staves and applying 0**.
**9 — better type.** *Not additive, not a probability.* A cell needs one clef. The
type that fits is **argmax + an ASYMMETRIC floor + a record**: establishing a
clef where none is in effect is the cheap case; **overturning one already in
effect on this staff is the expensive case** and should carry a higher bar,
because the staff has already spoken. **What must be TRUE for it to pay:** that
correct mid-staff flips carry systematically higher confidence than spurious
ones. On this sample they do (the one corroborated flip is the maximum of
eleven) — **n=1, so this is a hypothesis and the corpus is the prerequisite.**
An equally cheap variant needs no confidence at all and is worth pricing beside
it: *require a mid-staff change to be corroborated by more than one cell.* Nine
of the eleven flips rest on a single detection in a single cell.
**10 — blast radius + an A/B that can fail.** `OMR_CLEF_MIDSTAFF_MIN_CONF`,
default `0.0` ⇒ byte-identical (assert on both families' MusicXML). An arm at
0.75 changes the measure-level clef on 9 of 193 scan staves and nothing else.
**The control that can fail: the Brahms p1 s12 flip is CORRECT against truth and
must survive.** A floor that loses it is disqualified whatever the pooled number
does. Price on per-row **note recall**, not OMR-NED — a clef restates pitches and
the gate's noise floor is ±6 edits.
**11 — priority: HIGHEST in the slice.** 5.7% of scan staves × the pipeline's
highest per-error cost (a whole staff of wrong pitches) × one comparison and one
dict key. And ⚠️ it is **coupled to the held `OMR_INSTRUMENT_CLEF_DEFAULT`
decision** — a floor would reduce what A1b has to catch, so the two should be
priced together, not unilaterally.

**A6 — downstream implications of the type.** Seven vetoes collapse real numbers
to bools, and the one that survives to the end (`LocatedClef.symmetry`, rounded
to 4dp) is `probe`-only. The vetoes are not thereby wrong —
`dot_single_clear_is_enough` is a *recorded, deliberate* trade. The cost is that
the trade cannot be re-priced without re-running the pipeline, which is why the
additive survey had to reimplement `propose_clef` next door.
**9:** unchanged type, plus the trace. **10:** passing `trace={}` at `:1677` and
`:4286` and stashing it is byte-identical by construction (the trace is
write-only). **11 — the cheapest item in the whole audit**: the recorder is
written and tested and two call sites do not pass it.

---

## 4. SLICE B — glyph ownership

Three decisions delete detections: `_drop_clipped_notehead_fragments:539` (at
detection time, inside the cell pass), `_drop_unladdered_noteheads:3070` (called
at `:4715`) and `_dedupe_cross_staff_detections:2645` (called at `:4722`).

### 4.1 Reach, measured (`out/probe_ownership_reach.txt`)

| | scan (11 files) | engraved (11 files) |
|---|--:|--:|
| detections KEPT | 16,706 | 8,523 |
| noteheads KEPT | 4,339 | 1,557 |
| cross-staff duplicates removed | **1,446** = 8.0% of all detections made | **2,592** = **23.3% of all detections made** |
| clipped notehead fragments dropped | 101 (2.3% of kept noteheads) | 46 (3.0%) |
| unladdered noteheads dropped | **351** (8.1% of kept noteheads) | 28 (1.8%) |

⚠️ **The engraved figure is the surprise, and it is in no existing document.**
Nearly a quarter of every detection made on a conductor's engraving is deleted by
one rule whose bottom tier is distance to a staff band. The scan figure is a third
of that. (Denominators are *made* = kept + removed.)

### 4.2 ⚠️ Reversibility — 87.8% by construction, 100% as shipped

`out/probe_ownership_reversibility.txt`, over the 20-row contest dump (4,521
pairs, reproducing the recorded figure exactly). `transcribe.py:2770` parks a
pair only when `deferred is not None and is_note and rank == 0`, so the only
verdicts that can ever be revisited are noteheads decided by distance:

| category | contests | ladder | distance | **reversible** |
|---|--:|--:|--:|--:|
| structural (beam/tie/slur/staff/ledger) | 2,197 | 0 | 2,197 | **0** |
| dynamic | 869 | 0 | 869 | **0** |
| notehead | 816 | 266 | 550 | **550** |
| ornament | 215 | 0 | 215 | **0** |
| accidental | 198 | 0 | 198 | **0** |
| flag | 102 | 0 | 102 | **0** |
| rest | 91 | 0 | 91 | **0** |
| clef | 24 | 0 | 24 | **0** |
| time-sig digit | 7 | 0 | 7 | **0** |
| stem | 2 | 0 | 2 | **0** |
| **total** | **4,521** | 266 | 4,255 | **550 = 12.2%** |

**IRREVERSIBLE-BY-DELETION by construction: 3,971 = 87.8%.** And the recovery
path for the other 12.2% is `OMR_ROSTER_RANGE_VETO` (`transcribe.py:2619`),
default `off`, shipped off at 52 swaps for +24 edits. **So in the configuration
that actually runs, 0 of 4,521 ownership verdicts are ever revisited.**

That is the round's cleanest type-level statement: the pipeline's largest
overlapping population is resolved by its weakest evidence, and its one reversal
mechanism was built for 18% of that population and is off.

### 4.3 What the type destroys, quantified three ways

**(a) The higher-confidence copy, 44.8% of the time.**
⚠️ **CORRECTED IN ROUND 2 — read §R0.1 before using this figure.** It is the
complement of a number the additive survey already published, and ~50% is what
NO relationship looks like. Original text follows, with the inference it invited
withdrawn there. — Both confidences are in
hand at the moment of decision — fetched at `transcribe.py:2801-2802` *only* for
the instrumentation blob. Over all 4,521 pairs the **deleted** copy scored higher
than the survivor **2,026 times (44.8%)**, 24 exact ties, |Δconf| median 0.064,
p95 0.343. This is **not** an argument that confidence should decide — the
additive survey measured it agreeing with the trusted ladder only **0.617
[0.558, 0.674]** and I do not dispute that. It is the *size of the quantity
thrown away*: on nearly half of four and a half thousand deletions, the surviving
record is the one the detector believed less.

**(b) The class disagreement — 436 pairs, and it is not what the framing
assumes.** The deduper requires the same *category*, not the same *class*. 436 of
4,521 contests (9.6%) carry different classes, and only **17** are the expected
`…OnLine`/`…InSpace` artefact of one glyph at two staff positions. The rest are
genuine reading disagreements:

```
beam / tie                118      dynamicF / dynamicP                 22
slur / tie                 74      flag16thUp / flag8thUp              18
beam / slur                71      accidentalFlat / accidentalNatural  15
staff / tie                18      flag16thDown / flag32ndDown         12
```

**An ownership rule is silently settling a classification dispute.**
`flag16thUp` vs `flag8thUp` decides a duration; `accidentalFlat` vs
`accidentalNatural` decides a pitch; `dynamicF` vs `dynamicP` decides an exported
dynamic. The deciding criterion is distance to a staff band, which has no opinion
about any of them, and the disagreement is recorded nowhere outside
`OMR_CONTEST_DUMP`.

⚠️ I make **no claim** that the disagreement predicts which side is right. It is
untested and testable — against the ladder as an internal gold standard, exactly
as confidence was tested (that survey's §1.3, n=266). That probe does not exist.

**(c) The band distances.** `OMR_CONTEST_DUMP` (`transcribe.py:2789-2812`)
records both confidences, both classes, both pitches and the deciding tier — and
**not the distances**, the single quantity that decided 94.1% of the verdicts and
that this project has already caught being a coin flip (5-62 px). Confirmed by
reading the write block: there is no distance field.

### 4.4 ⚠️ `_drop_unladdered_noteheads` — the constant's gap is real on the family it barely fires on

`transcribe.py:2963`, `_UNLADDERED_NOTEHEAD_MAX_CONF = 0.65` — the pipeline's one
confidence threshold outside `OMR_CONF_THRESHOLD`. Justified by an empty gap
measured on three ENGRAVED works
(`LADDER_EVIDENCE_2026-09-01.md:72-85`: fakes 0.45-0.53, lowest real 0.76).

Fires **351×** on scans, **28×** on engravings.

Confidence histogram of the **surviving** outside-staff noteheads
(`out/probe_unladdered_threshold_neighbourhood.txt`, 0.05 buckets):

```
scan (n=756 kept outside the band)
  0.50: 12   0.55: 19   0.60: 27   0.65: 35   0.70: 62   0.75: 132   0.80: 261
engraved (n=357)
  0.60:  1   0.65:  2   0.70:  0   0.75:   8   0.80:  27   0.85: 184
```

**On engravings the population is essentially empty across the constant; on scans
it rises monotonically straight through it.** A hard threshold on a continuum, in
the family where it does 92.6% of its work.

⚠️ **Survivor bias, stated.** Sub-0.65 survivors are those that found a ladder
rung, so this cannot show what was deleted. It is sufficient for the T1 claim —
the populations *overlap* at the constant on scans — and insufficient for any
claim about whether the deletions were right. What would settle that is an
`OMR_UNLADDERED_DUMP` recording every refused notehead with its confidence, rung
count and band distance: byte-identical, and the same *record the refusal* item
as everywhere else.

⚠️ **A00, deliberately: I am NOT proposing the constant move.** It may be exactly
right. The finding is that its stated justification — an empty gap — does not hold
on the family it fires on, so its *type* is currently unlicensed there and nobody
can tell, because the refusals are not recorded.

### 4.5 `_drop_clipped_notehead_fragments` — the one gate in the slice I would leave alone

`transcribe.py:539`, constant at `:532`. Height < 0.6 staff spaces AND touching
the crop edge. Interior noteheads 0.61-1.12, edge-grazed real notes 0.77-0.99,
fragments 0.29-0.56 — **T1 fails by construction**, exactly as the
probability-gates handoff requires. It is a CONSTRAINT in the useful sense: a
notehead is one staff space tall because that is what a notehead is.

One note on its type. It is blind to `confidence` — a 0.95 detection dies on
geometry alone — while its sibling `_drop_unladdered_noteheads` is built entirely
on confidence. The map flags that asymmetry; measured, the asymmetry is
**correct**, because the two rules answer different questions (*is this shape a
notehead* vs *is this thing on this staff*). Recording the dropped fragment's
confidence is still free and would let anyone re-check that.

### 4.6 Slice B rows

| # | 1 DECISION | 2 TYPE | 3 C/O | 4 REACH | 4b measured-on / fires-on | 5 DESTROYS | 6 REVERSIBILITY | 6b RECOVERY | 7 RECORDS REFUSAL |
|--:|---|---|---|---|---|---|---|---|---|
| B1 | `_dedupe:2645` **rank 2 — ledger ladder** | veto, completeness only | **CONSTRAINT** (an unbroken rung run physically joins glyph to staff) | 266/4,521 = 5.9% | both / both | the rung counts (only completeness survives) | IRREVERSIBLE-BY-DELETION | **none — ladder pairs are deliberately not parked** (`:2779-2784`, correctly) | no |
| B2 | `_dedupe:2645` **rank 1 — written range / hairpin-has-notes** | veto on the impossible | **CONSTRAINT** | **0 of 4,521 on scans** — `_staff_written_ranges` returns `{}` dossier-free | dossier runs / never on the gate | nothing (never fires) | n/a | `OMR_ROSTER_RANGE_VETO`, **off** | n/a |
| **B3** | `_dedupe:2645` **rank 0 — distance to band** | **tie-break promoted to the whole rule** | OPINION, a documented coin flip (5-62 px) | **4,255/4,521 = 94.1%**; 82% in categories no higher tier can reach | n/a / both | **the object**; plus the margin, both confidences, the class disagreement (436), and the band distances themselves | **IRREVERSIBLE-BY-DELETION** | 550 parked (12.2%) behind a default-off flag ⇒ **0 as shipped** | **no** — `OMR_CONTEST_DUMP` is off, and omits the distances even when on |
| **B4** | `_drop_unladdered_noteheads:3070` | **hard confidence threshold** 0.65 | OPINION (a detector score) | **351 scan / 28 engraved noteheads deleted** | **engraved / overwhelmingly scan** | the object, its confidence, its rung count, its band distance | IRREVERSIBLE-BY-DELETION | none | **no** — an integer counter only, and `n_unladdered_noteheads_dropped` is SERIALISED-ONLY |
| B5 | `_drop_clipped_notehead_fragments:539` | hard gate on an empty gap | **CONSTRAINT** | 101 scan / 46 engraved | engraved 3-work / both | the object; its confidence | IRREVERSIBLE-BY-DELETION | none | **no** |
| B6 | the doomed-set application loop `:2810-2814` | greedy, strongest-first | CONSTRAINT (avoids the non-transitive-IoU cluster fault, measured 0.2275 vs 0.2263) | every verdict | n/a | which verdicts were *skipped* because a side was already doomed | REVERSIBLE in principle (nothing new is decided) | n/a | no |

**Fields 8–11 for B3 and B4.**

**B3 — downstream implications of the type.** A deleted detection never existed
for `pitch_resolver`, `rhythm`, `voicing`, the consistency checks, the contextual
pass or the exporter. Every later stage sees a page that looks unambiguous: one
glyph, one staff, no record that two staves claimed it. **That mechanism was
already found from the other end** — CLAUDE.md records that 83% of re-attributed
dynamic letters are the target staff's *sole* evidence *because* distance had
already removed the twin. The 869 dynamic contests here are that population, and
their reversibility is zero.
**9 — better type.** The pairwise structure and the tier order are both
CONSTRAINTS and should not move (the cluster-winner refactor measured worse; the
ladder is a physical join). What is wrong is that the *bottom* tier is a deletion
at all: a coin flip that commits. The fitting type is **deletion + a record of
the contest on the SURVIVOR** — a `contested_with` field carrying the loser's
staff, class, confidence and band distance. Not additive, not a probability: it
is the P(set) half of the project's own standard, and *"an abstention is not a
dead end"* applied to a deletion.
**What must be TRUE for it to pay:** that a later stage can use the loser. Two
already exist — the roster range veto (needs identity, which runs later) and
`export._arbitrate_arcs_in_system`, which re-decides arc ownership at export time
and would benefit from knowing an arc was contested. ⚠️ Note **263 of the 436
different-class contests are arc classes** (beam/tie/slur), and
`OMR_ARC_ATTRIBUTION` is already default-**on** — so a consumer for exactly that
subset is already shipping.
**10 — A/B.** `OMR_CONTEST_RECORD=1` writing `contested_with` onto survivors:
byte-identical MusicXML by construction, asserted on both families. Nothing is
priced until a consumer exists.
**11 — priority: HIGHEST in the slice**, on reach alone.

**B4 — downstream implications of the type.** 351 scan noteheads are deleted at
page scope *after* pitch resolution, so the resolved `pitch` goes with them;
`n_unladdered_noteheads_dropped` reaches the JSON and nothing reads it. It is
also the only place a per-class or per-family confidence floor could be
prototyped cheaply, which matters because `OMR_CONF_THRESHOLD` — one global number
for 208 classes — is the probability-gates handoff's strongest candidate.
**9 — better type.** ⚠️ **Not additive.** The rule already combines two signals
(confidence AND rung count) and CLAUDE.md records that *"neither signal is
sufficient alone"* — a conjunction of two weak opinions. The honest upgrade is a
**two-dimensional record before any change to the rule**, because the current
form cannot tell "0.64 with zero rungs" from "0.30 with zero rungs".
**10 — A/B.** Record first (byte-identical). Any later threshold arm must be
priced on scan-gate **note recall**, and ⚠️ the metric will mislead: OMR-NED is
symmetric and rewards emitting fewer symbols, so deleting *more* noteheads can
improve it. The worked precedent is `OMR_ARC_ATTRIBUTION`'s `drop` arm, which
scored better by emitting 20 fewer slurs — 12 of them real — and was REFUSED.
**11 — priority: high, and cheap** — the record is one dict append.

---

## 5. TYPE as a systemic property

### 5.1 The house style is a precedence ladder over a scalar slot — the wrong *container*, not the wrong *ranking*

The shape recurs: an ordered list of readers, each gated on `X is None`, writing
into one variable. Clef (`:1604/:1656/:1708/:1769/:1789`); ownership (`_dedupe`'s
rank 2 → 1 → 0); meter (`backfill_page_time_signatures`); identity
(`_read_labels_for_page`'s rungs).

Measured, the ranking is nearly always right and nearly always irrelevant: rung 1
answers 74.6% / 94.6% of clef staves and rank 0 answers 94.1% of ownership
contests. **The real cost is structural rather than ordinal:**

- **A ladder cannot express agreement.** Two rungs agreeing is worth exactly
  nothing — the second never runs. On the clef ladder this is not hypothetical:
  25 scan cells carry a clef detection in a non-first cell; **14 agree with the
  staff's established clef and are worth zero, and 11 disagree and are executed
  with no floor.** Agreement is discarded; disagreement is acted on. That is
  backwards for a page where one fact is printed once and read many times.
- **A ladder writes into a slot, so the loser is not merely unused — it is
  unaddressable.** `pitch_candidates` exists at the sibling site; clefs have no
  equivalent and never have (`git log --all -S "clef_candidates"` → nothing,
  ever). A later stage that wants to reconsider has nothing to reconsider *from*,
  which is why `clef_correction` re-derives from register and reaches 5 proposals
  on 193 staves.
- **A ladder makes the output look unanimous.** After `_dedupe`, every surviving
  detection looks uncontested; after the clef argmax, every staff looks like it
  read one clef. Nine of the map's export gaps are the same shape one layer down.

**So the systemic recommendation is not "make the ladders additive".** It is:
*a ladder may keep its ordering and must stop overwriting.* Write the winner AND
the field it beat. That is the additive-vs-gated survey's shortlist item 1 stated
as an architectural property instead of a list of sites — and both of this round's
slices land on it independently.

### 5.2 Three costumes, not two

The map names `SCORE_LABEL_CONFLICT = −8.0` dominating a scorer whose maximum
non-label positive is +2.5 — a gate in additive clothing. This round adds two
more, and I think both are more dangerous:

**A gate wearing a TIERED-EVIDENCE coat.** `_dedupe`'s rank ladder reads like a
hierarchy of evidence strengths (ladder > range > distance), which is sound. But
the tiers are **mutually exclusive**: rank 2 firing means distance is never even
computed for comparison, and rank 0 firing means the ladder said nothing rather
than said "unbroken on neither side". A pair where a ladder and a distance point
the *same* way scores identically to one where the ladder alone spoke. That costs
nothing today (rank 1 never fires, rank 2 fires 5.9%), and it is why the
confidence-vs-ladder agreement test had n=266 rather than n=4,521.

**An evidence-free rule wearing an EXPERTISE coat.** `MID_STAFF_CHANGE_VETOES` is
two hand-listed `(instrument, from, to)` triples; `TREBLE_OVERRIDE_INSTRUMENTS`
is a four-name allowlist the additive survey already recommends replacing with an
additive margin term. Both read like domain knowledge and both are enumerations
standing in for a measurement that is available: in A1b's case, *the staff
contradicting its own header at 0.32*. **An allowlist's failure mode is
invisible by construction** — it does not decline, it simply never fires, so the
six escaping flips produce no signal of any kind.

**And a fourth, adjacent: a gate wearing a REPORT's coat.** `OMR_CONTEST_DUMP` is
documented as verdict-neutral reach instrumentation. It is also the *only* place
the pipeline records that two staves claimed one glyph — and it is off by default
and omits the deciding quantity. `clef_locator`'s `trace` is the same shape: a
complete recorder, written and tested, that no call site passes. **An instrument
that is off is not a record.**

### 5.3 Reversibility is orthogonal to the A–E taxonomy, which is why it is worth adding

A–E classifies what happens to the *number*. It does not classify what happens to
the *object*, and the two come apart in both directions:

| | number survives | number destroyed |
|---|---|---|
| **object survives** | (healthy) | Class B — `Match.coverage` → high/medium/low. Recoverable by re-reading the string |
| **object deleted** | not observed | Class A/E — `_dedupe` rank 0, `_drop_unladdered`, the clef overwrite. **Not recoverable at any cost short of re-running the pipeline** |

The bottom-right cell is where this audit's leverage is and it is invisible to
A–E. It is also what makes *record the refusal* more than tidiness: at a
quantisation site the number can be re-derived later; at a deletion site it
cannot, because the input is gone. **At equal reach, record deletion sites
first.**

### 5.4 Two properties the type analysis kept surfacing that no column captures

**(a) Scope mismatch.** A per-cell decision writing a per-staff fact (the clef
argmax); a per-pair decision writing a per-page fact (`_dedupe`); the map's own
§4.3 hazard, a per-system refusal guarding a document-wide write. In each case
the decision's evidence is narrower than its blast radius, and in each case the
error is invisible at the scope where it was made. On this round's evidence that
predicts where a bad decision hurts better than the A–E class does.

**(b) The evidence's family provenance** (§1.3). Two of this round's four
worst-behaved constants are engraved-measured and scan-fired.

---

## 6. Ranked conclusions

Priority = reach × per-firing cost × cheapness. Each names the measurement that
would settle it and whether an existing harness can SEE it.

⚠️ **Part names do not reach musicdiff at all**, so nothing scored on identity is
visible to OMR-NED, the 20-row scan gate or `orchestral_eval`. None of the seven
below is an identity item — deliberately, which is why they are measurable today.

| # | conclusion | evidence | what would settle it | harness can see it? |
|--:|---|---|---|---|
| **1** | **The clef argmax overturns a staff's clef mid-page from ONE detection at conf 0.32-0.82 — 11 of 193 scan staves, 0 of 224 engraved. ≥1 right, ≥3 demonstrably wrong against truth. The existing veto reaches 3 of 11, and 0 with shipped defaults.** | §3.2; `out/probe_clef_midstaff_flips.txt`; truth adjudication vs `*.truth.musicxml`; `clef_correction.py:444-447`, `contextual.py:1003` | `OMR_CLEF_MIDSTAFF_MIN_CONF` (and/or a two-cell corroboration rule) A/B on per-row **note recall**. ⚠️ Control that must not fail: the Brahms p1 s12 flip is CORRECT and must survive | **YES** — a clef restates pitches, so `scan_eval` note recall moves. ⚠️ give each arm its own `--tag=`; a cached A/B reports "identical" and the tell is wall time |
| **2** | **87.8% of ownership deletions are irreversible by construction; 100% as shipped.** The one recovery path covers noteheads only and is default-off | §4.2, 4,521 pairs | structural — nothing to settle. The action is `contested_with` on survivors, byte-identical | n/a until a consumer exists; ⚠️ one exists in outline (`OMR_ARC_ATTRIBUTION`, already on, and 263 of the 436 class-disagreements are arcs) |
| **3** | **`clef_final` is the pipeline's only mid-staff-change record and it is unreliable: 9 of 20 occurrences are stale, it carries no evidence, and its only reader is its own keeper** | §3.3; `transcribe.py:3062-3065`, `:4674-4679`; `clef_correction.py:548-552` | write the measure index and the triggering confidence alongside it; and A/B `_drop_furniture_measures`' clef reassignment against `clef_final` | n/a — it is a record |
| **4** | **`_UNLADDERED_NOTEHEAD_MAX_CONF = 0.65` was measured on engravings and fires 12.5× more on scans, where the surviving population is continuous through it** | §4.4; `LADDER_EVIDENCE_2026-09-01.md:72-85` | a refusal dump (confidence × rung count × band distance) for the 351 scan deletions, then hand-adjudicate a sample | ⚠️ **not safely** — OMR-NED is symmetric and rewards deleting noteheads. Price on note recall, and treat a pooled *improvement* as suspect (the `OMR_ARC_ATTRIBUTION` `drop` arm is the precedent) |
| **5** | **436 of 4,521 ownership contests are two DIFFERENT readings, not one glyph seen twice** — 263 arc-class, 47 flag (a duration), 38 dynamic, 31 accidental (a pitch) — and an ownership rule settles the classification silently | §4.3(b) | test the class disagreement against the ladder gold standard, exactly as confidence was tested (n=266) | partly — the probe needs no harness; acting on it would |
| **6** | **`clef_locator`'s trace recorder is complete and no pipeline call site passes it.** `grep -rn "trace=" tools/omr/*.py` → nothing | §3.7 A6 | pass `trace={}` at `transcribe.py:1677` and `:4286`. Byte-identical by construction | n/a |
| **7** | **The clef argmax cannot tell a geometry measurement from a class-label fallback** — `ClefRead.source` and `.residual` are on the object and no caller reads them | §3.6 | one-line probe recording `source`/`residual` at `:1607` | n/a — UNMEASURED, and the probe is free |

**And one conclusion about the audit itself.** Every item above is *record the
refusal*, except #1, which is *record the refusal plus one comparison*. The
additive-vs-gated survey reached that from the additive side; this round reaches
it from the reversibility side, on different sites and different data. **Two
roads, one destination — and it is not corroboration**, because the substrates
differ: §3 and §4.4 share nothing with that survey, and only §4.2-4.3 share its
contest dump.

---

## 7. What round 1 does NOT cover

- **Most of the pipeline.** Stages 1, 2, 3, 5, 7, 8b, 8c, 9, 10 and 11 are
  untouched. The map's §5 rows for them stand.
- **Precision, everywhere except §3.2.** Reach is measured throughout; only the
  eleven clef flips were adjudicated.
- **Whether the CV locator would be RIGHT on the ≥22 staves it is silenced on.**
  Reach only, per the reach-before-accuracy rule.
- **How often the two independent clef readings (`:4286` header vs `:1604`
  measure) disagree** — the map's own §10.1 UNMEASURED item. It needs a run, not
  an artefact: the header read is not written to the output.
- **The deleted objects' distributions** at all three ownership sites. §4.4's
  histogram is survivor-biased and says so.
- **A controlled A/B of the `_drop_furniture_measures` → `clef_final` mechanism**
  (§3.3). Correlation 2 of 2 systems plus the code path; not proven by a run.
- **Anything requiring `scan_eval` or `orchestral_eval`.** Not run — coordinator
  permission required, and not needed for a scoping round.

### 7.1 Round-2 candidates, in the order I would take them

1. ⚠️ **`direction_text`'s `accepted[0]` argmax (`direction_text.py:801`) over a
   `Reader` interface that carries no confidence at all.** Surfaced by the map's
   verification pass (72 uncatalogued decision points in that module) and it is a
   decision-TYPE finding of exactly this round's kind: a raw argmax whose ranking
   quantity *does not exist in the type it ranks*. Not diverted into here, at the
   coordinator's instruction. It also sits on ~75% of whole-work wall clock, so
   its blast radius is cost as well as correctness.
2. **Tie pairing (25 decision points) and slur pairing (46)** — in the spine with
   zero §5 rows, and §4.3(b) shows 263 of the ownership class-disagreements are
   arc classes, so the two slices meet there.
3. **`export.py`'s decision surface**, which the map calls the longest dead-signal
   list in the pipeline and where the reversibility question is trivial (nothing
   downstream at all) but the *quantisation* question is not.
4. **The meter chain** (`backfill_page_time_signatures` and the asymmetric
   specialist override at `:1777`) — the one precedence ladder in the pipeline
   whose later rung overwrites *unconditionally*, the opposite convention from the
   clef ladder in the same function.

---

## 8. Reproducing

```bash
cd /Users/seanjohnson/Desktop/ReEngrave
P=.claude/worktrees/nice-nash-085307/benchmarks/omr-pipeline-audit-2026-09/probe

python3 $P/probe_clef_ladder_reach.py                    # 3.1  rung reach, both families
python3 $P/probe_clef_argmax_contests.py                 # 3.4  contests + different-class pairs
python3 $P/probe_clef_midstaff_flips.py                  # 3.2  every mid-staff clef overwrite
python3 $P/probe_clef_winner_confidence.py               # 3.5  what silences the lower rungs
python3 $P/probe_ownership_reach.py                      # 4.1  the three deletion rules' reach
python3 $P/probe_ownership_reversibility.py              # 4.2  tier x category x reversibility
python3 $P/probe_unladdered_threshold_neighbourhood.py   # 4.4  the 0.65 constant's neighbourhood
```

Read-only; seconds each; committed artefacts only. Outputs captured under `out/`.
Fixtures are gitignored build products, so in a worktree the probes point at the
main checkout.

The two adjudications in §3.2 and §3.3 were done inline rather than in a script
and are reproduced by these:

```python
# §3.2 — mid-part clef changes in the truth
import xml.etree.ElementTree as ET, glob, os
for f in sorted(glob.glob("benchmarks/omr-scan-e2e-2026-09/fixtures/*.truth.musicxml")):
    r = ET.parse(f).getroot()
    late = [(p.get("id"), mi, c.findtext("sign"), c.findtext("line"))
            for p in r.iter("part")
            for mi, m in enumerate(p.findall("measure"))
            for c in m.iter("clef") if mi > 0]
    print(os.path.basename(f), late or "NONE")

# §3.3 — stale clef_final
import json
for f in sorted(glob.glob("benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json")):
    for pg in json.load(open(f))["pages"]:
        for sy in pg["systems"]:
            for st in sy["staves"]:
                seq = {m.get("clef") for m in st.get("measures", [])}
                if st.get("clef_final") and len(seq) == 1:
                    print(f, st["staff_index"], st.get("clef"), st["clef_final"],
                          sy.get("n_measures_dropped_as_furniture"))
```

---
---

# ROUND 2

**Appended 2026-09-07.** Coordinator brief: take the four round-1 candidates in
my own order. Round 1 is unchanged except for one erratum pointer at §4.3(a),
which §R0.1 discharges.

Same disciplines as round 1: read-only probes over committed artefacts, line
numbers re-derived from the main checkout, `scan_eval`/`orchestral_eval`
embargo respected, UNMEASURED said out loud. Seven new probes under `probe/`,
outputs under `out/`.

---

## R0. Errata and one demotion of my own round-1 nomination

### R0.1 ⚠️ ERRATUM — the 44.8% figure is not new, and ~50% is what NO relationship looks like

Round 1 §4.3(a) reported that at `_dedupe_cross_staff_detections` the deleted
copy scored higher than the survivor **2,026 of 4,521 times (44.8%)**. Two
corrections, both mine:

1. **It is not an independent measurement.** It is the arithmetic complement of
   a figure the additive-vs-gated survey already published: that survey reports
   `P(winner conf > loser conf) = 0.545` on the 4,233 distance-decided pairs.
   Winner-higher 55.2% ⇔ loser-higher 44.8%. **One measurement, two framings** —
   and by this audit's own rule, *two signals sharing an ancestor are ONE
   signal*. I should have recognised my own number in theirs. Credit belongs to
   that survey.
2. **The right reading is "confidence is not informative here", not "the site
   chooses wrongly 44.8% of the time".** If confidence carried no ownership
   information at all you would expect ~50%, so a 44.8/55.2 split is the *null*
   with a small excess on top — the same weak positive signal the survey states
   as 0.545 [0.530, 0.560], and consistent with its 0.617 [0.558, 0.674] against
   the ladder gold standard. My phrase *"the surviving record is the one the
   detector believed less"* invites a defect-rate reading and is **withdrawn**.

**What survives, and it is the part the type analysis needs:** both confidences
are in hand at `transcribe.py:2801-2802` and neither is read; whether or not
they are informative is a question the site is not in a position to ask, because
it records nothing. The reversibility finding (§4.2 — 87.8% by construction,
100% as shipped) is untouched by this and rests on the tier/category
cross-tabulation, not on confidence.

### R0.2 A second correction I owe: `_stitch_slots` reach is smaller than "canonical" suggests

Round 1's table called `_stitch_slots` the canonical all-or-nothing refusal
without measuring it. Measured (`out/probe_stitch_refusal_reach.txt`): it
**refuses on 2 of 11 scan rows and 0 of 11 engraved rows.** On the two refused
rows it emits **51 per-system fragments**. ⚠️ And one of the two refuses on a
**one-staff difference** — `brahms-317803-p2` prints `[14, 13]`, the 13 being one
suppressed tacet staff. Bach prints `[12, 3, 3, 3, 1, 2]`, which is a
segmentation failure rather than a printing convention.

⚠️ **No proposal.** The additive survey classifies this refusal as a CONSTRAINT
to keep (joining by ordinal across suppressed staves grafts one instrument's
music onto another), `OMR_SLOT_STITCH` is the measured alternative, and backlog
§A0b has it **queued for re-pricing against the page-normalised truth**. I am
adding the reach and the granularity — *one staff of disagreement costs the whole
document's part continuity* — and nothing else.

---

## R1. `direction_text` — 72 uncatalogued points, and the argmax that has never fired

### R1.1 ⚠️ THE NOMINATION IS DEMOTED BY ITS OWN REACH: `accepted[0]` has arbitrated ZERO times

`direction_text.py:801` is `winner_name, hit = accepted[0]` and the coordinator
is right that its shape is the purest instance of this commission's question:
`Reader = Callable[[list[np.ndarray]], list[str]]` (`:614`) — **the ranking
quantity does not exist in the type being ranked.** There is no confidence
anywhere in the reader interface, so `accepted[0]` is not an argmax at all; it is
**reader-list order**, and `default_readers` appends Surya first and Tesseract
second, unconditionally.

Measured over the 11 committed scan transcriptions, which carry the full
per-page report (`out/probe_direction_funnel.txt`):

```
candidates proposed by the CV : 139
at least one rung read something : 134
lexicon ACCEPTED                 :  20
attached to a measure            :  20
CONFLICTS between the two rungs  :   0        <-- accepted[0]'s entire reach
winning rung: surya 19, tesseract 1
```

**Zero conflicts. The decision has never had to choose.** Both rungs ran on all
11 pages (`readers: [surya, tesseract]` on every one) and both contribute
accepted readings — verified not to be a short-circuit artefact, since
`read_directions` reads every crop with every rung by design (`:777-786`).
⚠️ **But this is NOT evidence that the rungs AGREED.** A conflict is recorded
only when *both* rungs produce an ACCEPTED reading and the two differ. Where one
rung is accepted and the other's reading is refused, the refusal is not counted
and — by the `:798` asymmetry below — not even recorded. So the honest statement
is that **the two rungs never both spoke**, not that they concurred. The
demotion stands either way: a decision that has never fired cannot be ranked on
accuracy.

⚠️ **This is my own round-1 nomination failing this project's reach-before-accuracy
rule, and I am reporting it that way.** A decision with zero measured firings is
not a defect worth fixing; it is a hazard worth *recording*, because the reach
could change the day a third rung is added or a page defeats one reader.
Priority: **demoted to the record-the-refusal sweep.**

⚠️ **What is genuinely wrong at that site is adjacent to the argmax, not in
it.** `info["rejected"]` is extended **only when `not accepted`** (`:798`). So on
a crop where one rung is accepted and the other's reading is refused, **the
refused string is discarded unrecorded.** The asymmetry is exactly backwards for
learning anything about the rungs: you see a rung's failures only on the crops
where *every* rung failed. Up to 20 second-rung readings on this corpus are
invisible for that reason. Free to fix, byte-identical, and it is the record that
would let anyone re-price the reader order the argmax stands in for.

⚠️ Also inert: `default_readers` drops Tesseract on a page that `page_is_engraved`
proves born-digital. All 11 scan pages report `page_is_engraved: False`, and the
11 engraved fixtures were built with `--no-direction-text` so they carry **no
report at all**. **The classifier's reach is unmeasurable on the standing
corpora** — its own docstring already flags that the born-digital claim rests on
three LilyPond fixtures.

### R1.2 The lexicon gate — established before proposing anything, and it is well earned

`direction_lexicon.lookup:139-181`. The gate is **exact per-token membership**:
every token must be in `TERMS` (140 entries) or `CONNECTIVE` (25), at least one
must be a real term, plus a charset `fullmatch` (`:149`), a 6-token cap and an
adjacent-repeat veto (`:166`).

Classifying all **135 refused strings** by *which clause refused them*
(`out/probe_direction_refusals.txt`):

| refusing clause | n | share | examples |
|---|--:|--:|---|
| **no term at all** | **71** | 52.6% | `ae`, `fa i a`, `epee oom`, `sy .`, `f FT jt` |
| **charset veto** (digit/bracket/symbol) | **50** | 37.0% | `a & =`, `%`, `—> eT`, `1 o>` |
| PARTIAL — ≥1 real term matched, then discarded | **10** | 7.4% | below |
| adjacent-repeat veto | 2 | 1.5% | `CRESC. CRESC. CRESC. CRESC. CRESC. CRESC.` |
| >6 tokens | 2 | 1.5% | `Cresc.` ×8 |

**121 of 135 (89.6%) carry no legal term at all.** The gate is doing exactly what
its docstring says it is for, and this is *evidence for the standing refusal to
loosen it*, not against. I propose no widening of `TERMS`, no OCR fold, and no
relaxation of the charset rule — all three are refused on the record, and this
measurement supports all three refusals.

⚠️ Note the two repetition families exit through **different clauses** — the
6-token cap catches the ×7 and ×8 cases before the adjacent-repeat veto ever
looks at them. Same fault, two exits, and only one of them is described in the
docstring that exists to explain it.

### R1.3 ⚠️ The 10 PARTIAL refusals are NOT a lexicon question — they are two of the module's own rules colliding

```
x3  'F legato'         matched=[legato]  unknown=[f]
x2  'f legato'         matched=[legato]  unknown=[f]
x2  'f  legato'        matched=[legato]  unknown=[f]
x1  'F espr.e legato'  matched=[legato]  unknown=[f, espr.e]
x1  "' espr. e legato" matched=[espr, legato]  unknown=[']
x1  'Basson Cresc.'    matched=[cresc]   unknown=[basson]
```

`lookup` computes `matched` and **discards it at `return None`** (`:174`) — the
canonical *the-margin-and-the-runner-up-destroyed* shape, here destroying a
complete legal direction.

**Seven of the ten fail on one token: `f`** (an eighth has `f` among two unknowns). And `f` is unmatched *by design*, from
this module's own docstring: *"It does not touch the letter dynamics … The
lexicon deliberately omits them so the two readers cannot both claim one mark."*
Meanwhile `_is_inside_a_word` (`:282`) **deliberately does not blank** a dynamic
glyph with ink hard against it on both sides — because on the Brahms page the `p`
of `espr.` is detected as `dynamicP`, and blanking it cost 56 edits. So:

> **Rule A keeps the dynamic letter in the crop. Rule B refuses any phrase
> containing it. Both are correct in isolation and their intersection costs
> `legato` six times on the scan corpus.**

That is a decision-TYPE fault, not a lexicon gap: `TERMS` needs no new member,
because the offending token is drawn from a set the exporter already enumerates
(`export._DYNAMIC_LETTER`) and which this module already declares out of scope.

⚠️ **Stated as a candidate, with the standing refusal flagged, and NOT as a
recommendation to loosen.** The additive survey's §7.5 refuses loosening the
lexicon and says explicitly of this shape: *"The recommendation here is to RECORD
the near-miss and its coverage (Class C), not to accept it."* I am consistent
with that: **record first.** `info["rejected"]` already exists; adding the
`matched` / `unknown` split to it is byte-identical and turns "135 strings" into
the table above on every run.
**What would have to be TRUE for the trim itself to pay:** that the trimmed token
is always claimed by `measure_dynamics` on the same measure, so the two readers
still cannot double-claim it. That is checkable from a single run and has not
been checked. ⚠️ And OMR-NED charges an invented direction its own character
count, so six recovered `legato`s is a ±36-character bet inside a ±6-edit noise
floor — it must be priced on words-correct-per-staff
(`benchmarks/omr-dynamics-band-2026-09/probe_dynamic_band.py`), not on the
pooled figure.

### R1.4 `staff_labels_surya` — the free DEFAULT rung the map omits, now catalogued

Measured reach of the whole label ladder over the 11 scan transcriptions
(`out/probe_label_reader_tiers.txt`, from each run's own `contextual.label_tiers`):

| rung | labels supplied |
|---|--:|
| text layer | 12 |
| **surya** | **134 (87.6%)** |
| tesseract | 7 |
| vision | 0 |
| human | 0 |

132 of 193 staves labelled; 15 labels read and unresolved; 32 instruments from
score order. **Surya supplies seven of every eight margin labels on the scan
family** — and the decision map catalogues the *unreachable* human rung in full
while giving this module no row at all.

Its decision surface, catalogued:

| decision (file:line) | type | C/O | reach / what it destroys | reversible? | records refusal? |
|---|---|---|---|---|---|
| `_lines_with_boxes:48` → `_lines:74` | projection | — | ⚠️ **`x_left` is computed at `:69` and thrown away one line later** — `_lines` returns `(text, y, h)`. The margin path is therefore x-blind, the same fault the map records for the *text-layer* reader (`staff_labels.py:189`) and does not record here | IRREVERSIBLE-BY-DELETION | no |
| `_assign:89` runaway-height cap | hard gate on a **measured 22× empty gap** (`_RUNAWAY_HEIGHT_FRACTION = 0.5`; the two known runaways at 1.04× the span, Boléro's 17 correct blocks at 0.015–0.047×) | **CONSTRAINT-shaped** — a block cannot be one staff's label and the whole crop | **the dropped block is not counted** | IRREVERSIBLE-BY-DELETION | **no** |
| `_assign:107-113` nearest-tick | **raw argmax + tolerance gate** | OPINION | the distance to the winning tick is computed, used for the gate and the join order, then discarded; the runner-up tick is never formed | IRREVERSIBLE-BY-DELETION | **no** |
| `read_staff_labels_surya:344`, the `confidence=` assignment at `:384` | projection | — | `confidence=hit.confidence if hit else "none"` — the only "confidence" a Surya label ever carries is the **lexicon's** high/medium/low. The OCR contributes none, exactly as `direction_text`'s `Reader` does not | IRREVERSIBLE-BY-QUANTISATION | no |
| `available():121` | abstention | CONSTRAINT | correct, and the documented degradation | n/a | yes (via the ladder's counts) |

⚠️ **The consequence for `_assign` is a shared failure signature.** A page where
Surya read every label and `_assign` dropped them all — by the height cap or the
tolerance — is **byte-identical in the output to a page Surya could not read**,
because only survivors are returned. That is the same "an abstention and a
failure look alike" fault the direction reader's own report was built to fix
(`read_directions` returns `info` for exactly this reason), applied to the rung
that supplies 87.6% of the labels. The fix is the same and equally free: return
the counts.

---

## R2. Tie and slur pairing — anchors, measured, with the grammar left alone

⚠️ **Prior art honoured.** `benchmarks/omr-export-gaps-2026-09/FINDINGS.md` §2/§5/§6
built the export-time tie/slur grammar veto (`OMR_ARC_RECLASS`), measured it on
both families and shipped it **default off** — engraved +2 edits, scan **+130,
refused**, the whole +130 in the tie→slur half. **I re-propose none of it.** That
document also names what is open: *"grammar needs anchors — anchor recall is the
foundation the grammar multiplies; it cannot replace it"* (R4). This section is
the anchor half, measured.

### R2.1 ⚠️ THE FINDING — 79.6% of scan tie detections never find two anchors, and nothing counts them

`transcribe._pair_ties_in_staff:2038` pairs a tie glyph with the nearest notehead
on each side. **Replayed faithfully over the committed transcriptions** — every
input it reads (`bbox_page`, `category`, `class`) is in the JSON, so the replay
is exact (`out/probe_tie_pairing_replay.txt`):

| | scan (11 pages) | engraved (11 works) |
|---|--:|--:|
| tie detections | **1,459** | 155 |
| paired on **both** sides | **298 (20.4%)** | 70 (45.2%) |
| found **one** side only | **422 (28.9%)** | 30 (19.4%) |
| found **no** side | **739 (50.7%)** | 55 (35.5%) |

**`_pair_ties_in_staff` returns `n_new_pairs` and nothing else.** The 1,161 scan
ties that failed to anchor are not counted, not flagged, and not distinguishable
downstream from a page with no ties. That is precisely the population
`OMR_ARC_RECLASS`'s `unpaired_*` sub-rules key on — the rules the export-gaps
document found *"turn junk tie detections into junk slurs"* — and its size has
never been stated.

⚠️ **What the number is NOT.** It is not a false-positive rate for the detector.
A tie with no anchor may be a spurious detection, a real tie whose notehead was
missed, or a real tie whose anchor was deleted by the ownership rules in §4 (263
of my 436 class-disagreements are arc classes, and 118 of those are `beam`/`tie`).
**Those three are not separable from an artefact**, and separating them is the
measurement the anchor half needs.

### R2.2 The two argmaxes, and the quantity the tie's own definition asks for

`:2088-2105` runs two independent nearest-neighbour argmaxes — nearest head at or
left of the arc's left edge, nearest at or right of its right edge — each inside a
3-notehead-width window, and **`best_left_dx` / `best_right_dx` are computed and
discarded**. There is no joint test: the two winners are accepted whenever they
are not the same detection.

Measured on the pairs that *did* form:

| |y| between the two paired heads, in notehead heights | scan (n=298) | engraved (n=70) |
|---|--:|--:|
| median | 0.42 | 0.01 |
| p90 | 1.79 | 0.47 |
| max | **4.66** | 1.47 |
| pairs more than 0.5 nh apart | **122 (40.9%)** | 4 (5.7%) |

**A tie joins two notes at the same staff position** — that is a rule of
engraving, not a reading — and the scan distribution has a long tail the engraved
one does not.

⚠️⚠️ **AND THE OBVIOUS INFERENCE IS THE ONE THE PRIOR ART FORBIDS.** Of the 298
scan pairs, **199 (66.8%) join two heads whose resolved pitches differ** (engraved:
23 of 70). It is tempting to read that as 199 wrong pairings. **The export-gaps
document measured exactly this and says otherwise**: on a scan the resolved pitch
at an arc's ends is downstream of what scans get wrong (`wrong note` is 26% of
that pool), so a step disagreement between two tie endpoints is *usually a
resolution error, not a wrong arc* — which is why the `flagged_diff_pitch` rule
cost +130 edits and broke a nearly perfect tie inventory (Brahms p2: 192 tie
elements against a truth of 194, slashed to 87). **So the artefacts cannot
separate "wrongly paired" from "correctly paired, wrongly pitched", and I do not
claim they can.**

What is unambiguous and type-shaped: **the pairing never forms the quantity at
all.** `y_tol` is a single scalar, `max(avg_nh_h * 3, 30)`, applied to the arc's
CENTRE against each head — so two heads up to ~6 notehead heights apart can pair,
and the vertical relationship *between the two chosen heads* is never computed,
never compared, never recorded. Recording it is free and is what would let anyone
re-price the anchor question when scan pitch resolution improves — which is the
export-gaps document's own stated trigger (*"the same probe re-prices it in
minutes"*).

⚠️ **A null worth stating:** the bare `30` pixel floor in `max(avg_nh_h * 3, 30)`
looks like the unit fault the map flags elsewhere (`measure_extractor.py:1107`'s 10 px —
the decision map cites it as `_build_measure_cell:1060`, which has drifted) and **never binds** — median `avg_nh_h` is 30.5 px on scans and 43.5 on
engravings, so `3×` is 91 / 130. It is inert on both corpora, and that is a
measurement rather than an assumption.

### R2.3 Slur pairing — the constants are plateaus and stay; the reach is elsewhere

`export.annotate_slurs_in_staff:2356` and `annotate_slurs_in_slot:2363`, with
`_merge_arcs_across_barlines:2209`, `_noteheads_under:2301`,
`_voice_of_notehead:2338`. Its three constants (`_SLUR_BOUNDARY_SPACES 0.5`,
`_SLUR_CONTINUATION_DY_SPACES 2.0`, `_SLUR_ARC_PAD_NOTEHEADS 0.25`) each sit on a
documented gap with a documented plateau — T1 fails by construction and they
should not be touched.

The type observations that remain:

- `_merge_arcs_across_barlines` decides continuation on **edge proximity AND a dy
  tolerance**, and the CLAUDE.md record notes the continuation cluster's top
  moved 0.53 → 1.14 spaces when system grouping changed — inside the gap, but it
  *moved*. **The margin to the gap edge is exactly what is not recorded**, so the
  next such shift will again be discovered by re-measuring rather than announced
  by the run.
- ⚠️ `export._arbitrate_arcs_in_system:1770` (`OMR_ARC_ATTRIBUTION`, **default
  `move`, ON**) is the one place in the pipeline that *re-decides* arc ownership
  after the fact, on evidence the ownership pass never had (which staff's
  noteheads the arc hugs). **It is therefore the existing consumer for round 1's
  `contested_with` proposal**, and the two workstreams meet exactly here: 263 of
  the 436 different-class ownership contests are arc classes, and this function
  is already shipping, already comparative (`_ARC_RIVAL_MARGIN_SPACES = 0.5`),
  and already refuses `drop` in favour of `move` on the measured grounds that
  deleting flatters the metric. It computes `own - best[0]` — a real margin — at
  `:1804` and **discards it**.

---

## R3. `export.py` — reversibility trivial, quantisation not

Round 1's framing holds and I add one measured reach, chosen because it is the
sharpest instance and because `measure_dynamics` is already priced by the
additive survey (45/45 and 8/8 at edit distance 1) and must not be re-measured.

**`<duration>` is written while the pipeline's own statement that the bar does
not sum is on the same dict, unread.** The map names the blindness; the reach
(`out/probe_meter_guard_reach.txt`):

| | scan | engraved |
|---|--:|--:|
| measures | 2,235 | 1,517 |
| carrying `rhythm_sum_warning` | **111 (5.0%)** | 12 (0.8%) |
| severity high / low | 88 / 23 | 11 / 1 |

**111 scan measures are serialised with an integer `<duration>` at the exact
moment the pipeline has computed, and recorded, that their contents do not sum to
the bar.** (The 111 / 12 split reproduces the additive survey's figure exactly —
a control that my probe reads the same field they did, not a second measurement.)

⚠️ **No proposal to act on it in the exporter.** `rhythm_sum_warning` is
Class C with a real signed magnitude and no confidence field, and the honest
first step is the one round 1 already ranks: give it a consumer only after a
corpus prices one. What is worth stating is the *type* fact — the exporter's
decisions are the only ones in the pipeline whose reversibility is trivially
"nothing downstream", which means **every quantisation there is terminal**, and
it is also the one stage where recording costs literally nothing because no
later stage can be confused by an extra field.

---

## R4. The meter chain — where the ladder's direction contradicts itself, and what it is worth

The coordinator's framing was `:1774` (clef specialist, gap-fill) against `:1777`
(meter specialist, unconditional). Both are real and the asymmetry is exactly as
described — the code is:

```python
if spec_clef is not None and clef_source is None:      # :1769  GAP-FILL
    active_clef = spec_clef
if spec_time_sig is not None:                          # :1772  UNCONDITIONAL
    active_time_sig = spec_time_sig
```

⚠️ **But it is INERT on everything measurable, and I have to say so.** The
specialist runs only when `clef_reader is not None`, and every fixture in both
standing corpora records `clef_weights: null`
(`out/probe_meter_changes.txt` and a direct read of the run headers). **Reach: 0
of 193 scan staves and 0 of 224 engraved.** It is a latent hazard, correctly
identified, with no measured firing — the same verdict R1.1 gives my own
nomination, and I apply it evenhandedly.

### R4.1 ⚠️ THE LIVE ASYMMETRY IS ONE LAYER UP, AND IT IS THE SHARPEST RESULT OF BOTH ROUNDS

The clef and the meter are overwritten **per cell, unconditionally, with no
floor** — the clef at `:1604`, the meter at `:1634-1636`. Both then carry
forward onto every later measure of the staff. ⚠️ **And there is a THIRD, the
key signature at `:1628-1631`, sitting physically between them — see §R8.1.**
All three overwrite sites fall inside one thirty-line span of one function.

They differ in what runs afterwards:

| | the page-scope guard | default | measured on 11 scan pages |
|---|---|---|--:|
| **METER** | `rhythm.drop_uncorroborated_meter_changes:597`, called from `backfill_page_time_signatures` at `rhythm.py:689` — a mid-staff change survives only if `max(2, 0.5 × n_staves)` staves see the same change at the same measure index | **ON** | ⚠️ **CORRECTED IN ROUND 3 (§R8.1): 21 is MEASURES reverted, not changes.** The comparable number is **0 surviving mid-staff meter changes on 193 staves** |
| **CLEF** | `clef_correction.veto_implausible_clef_changes:460` — a 2-triple `(instrument, from, to)` allowlist, identity-gated to `label` | **OFF** (`OMR_INSTRUMENT_CLEF_DEFAULT`) | **11 surviving mid-staff clef changes on 193 staves** (round 1 §3.2) |

`drop_uncorroborated_meter_changes`'s docstring describes the *identical*
failure this audit found for the clef — *"a single false reading rewrites the
rest of the staff and then votes for itself as many times as there are bars
left"* — diagnosed on Beethoven 5 page 1, where five `timeSig4` boxes fired on
barline fragments and shipped a 2/4 page as common time.

**So: the pipeline has already met this bug, already built the repair, and
applied it to one of the two facts that behave identically.** Engraved: 0
reverted, 0 surviving — the fault is scan-only in both channels, which is the
control.

### R4.2 ⚠️ The meter's guard CANNOT be transplanted, and the disanalogy is the useful part

The meter guard's evidence is that **a meter change is a system-wide event,
printed on every staff at the same bar** — a CONSTRAINT of engraving, which is
why corroboration across staves is exact and needs no threshold beyond a quorum.
**A clef change is printed on ONE staff.** Corroboration across staves is
therefore not available, and proposing it would be the mistake this audit exists
to catch.

What transplants is the **shape**, not the witness: *a mid-staff overwrite must
be corroborated by something independent before it is believed.* For the clef the
independent witnesses that exist are the three round 1 already named, and this
section changes none of them — it only shows the shape is already house practice:

1. the same staff's own header reading (a contradiction — round 1 §3.2);
2. more than one cell agreeing (round 1's second variant — 9 of the 11 flips rest
   on a single detection in a single cell);
3. the same part's reading on another system, which
   `contextual._fill_defaulted_clefs` already implements for a different purpose.

### R4.3 A third instance of the stale-`*_final` fault, larger than the first

Round 1 §3.3 found `clef_final` stale on 9 of 20 scan occurrences. The same shape
on the meter, and worse: **32 of 193 scan staves carry `time_signature_final`
while 0 staves show a per-measure meter change** (`out/probe_meter_changes.txt`).
Every one of the 32 announces a change no surviving measure supports.

The mechanism is different from `clef_final`'s and is *more* structural:
`time_signature_final` is written inside the staff loop (`transcribe.py:4683`),
and `backfill_page_time_signatures` **and**
`drop_uncorroborated_meter_changes` (which `backfill` itself calls,
`rhythm.py:689`) both run afterwards at PAGE scope — `transcribe.py:4757`, with
`_reconcile_page_to_meter` at `:4785` — and rewrite the measures the field
describes. So the
field is stale **by construction**, not by accident — and its staleness is the
shadow of the guard working correctly.

> **Generalised: `*_final` is written before the page-scope passes that rewrite
> the thing it describes, so it records the pre-repair state and reads as the
> post-repair one.** Three instances now: `clef_final` (9 of 20 stale),
> `time_signature_final` (32 of 32 stale on scans), and `key_signature_final`,
> which the map already lists under `NOBODY`. **None has a consumer**, which is
> the only reason none has caused a fault — and it makes them a trap for exactly
> the next person who gives one a consumer, which is what round 1's conclusion 3
> and the additive survey's shortlist item 1 both invite.

---

## R5. Ranked conclusions, round 2

| # | conclusion | evidence | what would settle it | harness can see it? |
|--:|---|---|---|---|
| **R1** | ⚠️ **SUPERSEDED BY §R8.1 — there are THREE instances, not two, and the 21 was a unit error.** The corrected form: clef 11 surviving flips, key signature 7, meter 0, on the same 193 scan staves | §R4.1; `rhythm.py:597`; `clef_correction.py:460`; round 1 §3.2 | this *is* round-1 conclusion 1's A/B, now with a precedent and a control. ⚠️ The meter's cross-staff witness does NOT transplant (§R4.2) | **YES** — a clef restates pitches; note recall moves |
| **R2** | **79.6% of scan tie detections never find two anchors (1,161 of 1,459) and nothing counts them** — the anchor half the arc-reclass work names as the open one | §R2.1, faithful replay | count them and split the three causes (spurious / missed head / head deleted by the ownership rules). ⚠️ Not separable from artefacts | partly — the count is free; the causes need a run |
| **R3** | **`*_final` fields are stale by construction — 32 of 32 on the meter, 9 of 20 on the clef — and none has a consumer** | §R4.3, §3.3 | write them after the page-scope passes, or delete them. Byte-identical either way to the MusicXML | n/a — they reach no consumer |
| **R4** | **`accepted[0]` — the purest instance of the type fault — has arbitrated ZERO times.** What is wrong beside it is that `rejected` is recorded only when EVERY rung failed | §R1.1, 11 pages | nothing to price. Record the second rung's refused reading: free | n/a |
| **R5** | **The direction lexicon refuses well (89.6% of refusals carry no legal term) and the 10 PARTIAL refusals are two of the module's own rules colliding — 7 of them on the letter `f` alone** | §R1.2-R1.3 | record `matched`/`unknown` on the refusal (free), then check whether `measure_dynamics` claims the same `f` on the same measure | ⚠️ **not** pooled OMR-NED — words-correct-per-staff |
| **R6** | **Surya supplies 87.6% of scan margin labels and has no row in the map; `_assign` drops blocks silently, so "read and discarded" is byte-identical to "could not read"** | §R1.4 | return the drop counts. Free | n/a |
| **R7** | **`_stitch_slots` refuses on 2 of 11 scan rows, one of them on a ONE-staff difference, emitting 51 fragments** | §R0.2 | ⚠️ already queued — backlog §A0b, against the page-normalised truth. **No proposal from me** | queued |

**Couplings, restated because they are what makes this usable:**
- Round-1 conclusion 1 / R1 above stays **coupled to `OMR_INSTRUMENT_CLEF_DEFAULT`** and moves only with Sean.
- R2 is **downstream of scan pitch resolution**, per the arc-reclass document's R4 ordering — the anchor count is worth having now, acting on it is not.
- R7 is **owned by the queued `OMR_SLOT_STITCH` re-pricing**, not by this audit.

## R6. What round 2 does NOT cover

- **`direction_text`'s other ~60 decision points.** I catalogued the reader
  ladder, the lexicon gate and the funnel; the CV candidate-finding half
  (`find_candidates`, `_blank_detections`, the nine `BandConfig` constants) is
  measured in its own benchmark and I did not re-derive it.
- **Slur pairing reach.** §R2.3 gives the type reading; I replayed ties, not
  slurs — slur pairing runs at export scope over stitched slots and a faithful
  replay needs the stitcher, which is contended (backlog §A0b).
- **`export.py` beyond one site.** Its decision surface is the largest in the
  pipeline and round 2 measured one reach in it.
- **Any engraved direction-text figure.** The 11 engraved fixtures were built
  `--no-direction-text` and carry no report; every direction number here is
  scan-only and says so.
- **Anything requiring a run.** Embargo respected; all seven probes read
  committed artefacts.

## R7. Reproducing round 2

```bash
cd /Users/seanjohnson/Desktop/ReEngrave
P=.claude/worktrees/nice-nash-085307/benchmarks/omr-pipeline-audit-2026-09/probe

python3 $P/probe_direction_funnel.py         # R1.1  candidates -> read -> accepted -> placed, conflicts
python3 $P/probe_direction_refusals.py       # R1.2  which lexicon clause refused each string
python3 $P/probe_label_reader_tiers.py       # R1.4  which rung supplied each margin label
python3 $P/probe_tie_pairing_replay.py       # R2.1  faithful replay of _pair_ties_in_staff
python3 $P/probe_meter_changes.py            # R4.3  meter sources, changes, stale *_final
python3 $P/probe_meter_guard_reach.py        # R4.1  uncorroborated meter changes reverted
python3 $P/probe_stitch_refusal_reach.py     # R0.2  where _stitch_slots refuses
```

Read-only, seconds each, committed artefacts only. Outputs captured under `out/`.
`probe_direction_refusals.py` imports `tools.omr.direction_lexicon` to classify
by the live clause set — ⚠️ if that module's clause order changes, the probe goes
silently stale, which is the same hazard the additive survey records for its
`propose_clef` reimplementation and the same argument for recording the refusal
at the site.

---
---

# ROUND 3

**Appended 2026-09-07.** Coordinator verdict on round 2: sound, 28 of 31
quantities exact, 19 of 19 line numbers correct, with one unit error inside the
headline and one missing third instance. Both are addressed below, and a third
problem — **mine, and worse than the one they caught** — is disclosed in §R8.0.

Round-2 text is corrected in place where a number was wrong, each correction
marked and pointing here. Two new probes; all sixteen re-run from an unrelated
CWD under the new fail-loud fixture helper (§R8.4).

---

## R8.0 ⚠️ THREE CORRECTIONS, AND THE SECOND ONE IS A PROBE THAT LIED

### (a) The unit error, as reported

`rhythm.py:666` increments `reverted` **inside the per-measure loop**, and the
docstring says so: *"Returns how many measures were reverted"*. So round 2's
*"21 changes reverted"* is **21 MEASURES**. The number of *changes* is not
recoverable from the artefact, because the guard stores its consequence and not
its decision — which is this report's own thesis arriving in this report's own
evidence.

**A bound is derivable and I give it rather than the number.** The 21 reverted
measures fall on exactly **3 pages** (Beethoven 984073-p1: 12, Brahms 317803-p1:
6, Mahler p2: 3 — `out/probe_meter_guard_reach.txt` plus a per-page split), and
each page contributes at least one change, so **3 ≤ changes ≤ 21**. It cannot be
tightened: one change reverts every measure from its index to the end of *its
staff*, so 12 reverted measures on a 12-staff page is consistent with 1 change
and with 12.

**The comparison is retired, not repaired.** §R8.1 replaces it with three counts
that are all the same quantity — *staves carrying a surviving mid-staff change* —
so nothing has to be converted. The 11 clef flips were always that quantity.

### (b) ⚠️⚠️ MY OWN PROBE PRODUCED A CLEAN ALL-ZERO TABLE AT EXIT 0 — TWICE

Round 2 §R4.3 reported *"0 staves whose per-measure meter changes"* and, in the
material behind it, the same for key signatures. **Both came from a probe that
keyed on fields the dicts do not carry.** `sig()` read `ts.get('beats')` and
`ts.get('beat_type')`; the real keys are `numerator` / `denominator`. Every meter
stringified to `"None/None"`, every staff looked constant, and the probe printed
a tidy table and exited 0.

This is **exactly the failure mode the verifier flagged in Agent I's probes**,
in my own evidence, and it is worse than a CWD problem because no environment
change would ever surface it.

Re-derived with an `assert` on the key set, from a clean CWD:

| | round-2 claim | corrected |
|---|---|---|
| mid-staff **meter** changes surviving | 0 | **0 — the verdict HOLDS** |
| mid-staff **key-signature** changes surviving | 0 | **7 — the verdict was WRONG** |
| stale `time_signature_final` | 32 of 32 | 32 of 32 — holds |
| stale `key_signature_final` | 26 of 26 | **19 of 26** (the other 7 are the real flips) |

**The meter conclusion survived by luck** — the bug made everything constant and
the truth was also constant — and the key-signature conclusion did not. Both
probes now assert on their key set before reading it, and both assertions are
kept in the committed source with the reason.

⚠️ **The general lesson, which is this audit's own subject:** a probe that reads
a field by name and gets `None` cannot distinguish *"the field is absent"* from
*"the value is null"* — the identical fault this report attributes to
`key_signature_warning` (an unread staff and a staff printing no key signature
are indistinguishable) and to `staff_labels_surya._assign` (read-and-discarded
looks like could-not-read). **Assert on the schema, not on the value.**

### (c) The minor corrections

Applied in place in round 2, each marked: *"ten lines apart"* → the three sites
span thirty lines and are named individually; *"six of the ten PARTIAL
refusals"* → **seven** fail on `f` alone and an eighth has `f` among two
unknowns; the doomed-set loop is `:2810-2814`; `read_staff_labels_surya` is
`def` at `:344` with the cited line at `:384`; and `_build_measure_cell:1060`
is quoted from the decision map, whose line has drifted — the 10 px test is at
`measure_extractor.py:1107`.

### (d) The `accepted[0]` restatement (coordinator's D12)

Round 2's *"zero conflicts"* is corrected in place. It is true **as the pipeline
defines a conflict** — both rungs producing an *accepted* reading that differs —
and it is **not** a short-circuit artefact: `read_directions:777-786` reads every
crop with every rung on purpose. But a conflict where one rung is accepted and
the other refused is neither counted nor, by the `:798` asymmetry, recorded. So
the finding is **"the two rungs never both spoke"**, not "the rungs agreed". The
demotion stands: a decision that has never fired cannot be ranked on accuracy.

---

## R8.1 ⚠️⚠️ THREE ADJACENT SITES, ONE FAULT, THREE LEVELS OF PROTECTION — AND THE FLIP COUNTS RANK INVERSELY

The coordinator's third instance is real, and it is the strongest result of the
audit. Three facts are established per cell, carried forward onto every later
measure of the staff, and overwritten by any later cell — **inside one thirty-line
span of one function**:

```
transcribe.py:1594-1617   CLEF           argmax over clef detections, best_clef_conf = -1.0, no floor
transcribe.py:1628-1631   KEY SIGNATURE  _detect_key_sig_from_cell -> slot fit, else COUNT the markers
transcribe.py:1634-1636   METER          parse_time_signature, applied unconditionally
```

What runs afterwards differs, and so does the outcome
(`out/probe_clef_midstaff_flips.txt`, `out/probe_key_signature_flips.txt`,
`out/probe_meter_changes.txt` — all three counting the same thing, *staves
carrying a surviving mid-staff change*):

| fact | page-scope guard | default | **scan (193 staves)** | engraved (224) |
|---|---|---|--:|--:|
| **CLEF** | `clef_correction.veto_implausible_clef_changes:460` — a **2-entry** `(instrument, from, to)` allowlist, gated on `instrument_source == "label"` | **OFF** | **11** | 0 |
| **KEY SIGNATURE** | *(none)* | — | **7** | 0 |
| **METER** | `rhythm.drop_uncorroborated_meter_changes:597` — a change survives only if `max(2, 0.5 × n_staves)` staves see the same change at the same measure index | **ON** | **0** | 0 |

**Full corroboration → none surviving. A two-entry allowlist that is off → eleven.
Nothing at all → seven.** Eighteen surviving flips on the scan family, zero on
the engraved one, which is the control: the fault is print-quality-driven in all
three channels.

### The seven key-signature flips, in full

Every one is triggered by a **single** marker at confidence **0.26–0.57**:

```
row                          staff  instrument  measure  change              marker
beethoven-575951-p1          s2     Clarinet    m11      0 flats -> 1 flat   keyFlat 0.32
beethoven-575951-p2          s0     Flute       m15      2 flats -> 1 flat   keyFlat 0.26
beethoven-575951-p2          s3     Bassoon     m2       2 flats -> 1 flat   keyFlat 0.42
beethoven-575951-p2          s20    Violin      m3       3 flats -> 1 flat   keyFlat 0.50
beethoven-984073-p2          s3     Bassoon     m2       2 flats -> 1 flat   keyFlat 0.57
dvorak-405834-p5             s4     Horn        m3       0 flats -> 1 flat   keyFlat 0.49
mahler-p2                    s15    Violin      m6       4 sharps -> 1 sharp keySharp 0.33
```

⚠️ **Every flip lands on exactly one accidental, and that is the mechanism, not a
coincidence.** `_detect_key_sig_from_cell:839-858` tries the slot fit first and,
when the fit abstains, **falls back to COUNTING the markers** (`n = len(markers)`).
One stray marker therefore reads as one accidental, whatever the staff was in.

⚠️ **AND ITS DOCSTRING SAYS THE OPPOSITE.** `:836-837`: *"Falls back to the count
when geometry can't run or the fit abstains, **so a reading is never lost — only
improved on**."* That is true of the first cell, where the alternative is nothing.
It is **false mid-staff**, where the fallback does not preserve a reading — it
replaces a four-sharp staff with a count of one. A new code-vs-prose
disagreement, in the §8 idiom of the decision map, not among its D1–D28.

### ⚠️ Five of the seven overturn a reading the cross-page VOTE had already confirmed

`key_signature_source` on the flipped staves, with the vote's own recorded reason:

```
mahler-p2 s15        header_vote   "kept: agrees with the system's 4 sharps"     -> overturned to 1 sharp by a 0.33 marker
beethoven-984073-p2 s3  header_vote "kept: 2 flats is a standard transposition"  -> overturned to 1 flat by a 0.57 marker
beethoven-575951-p2 s0  header_vote "kept: no majority to check against"         -> 1 flat
beethoven-575951-p2 s3  header_vote "kept: no majority to check against"         -> 1 flat
beethoven-575951-p1 s2  header_vote "rejected: 1 flat differs from the system"   -> 1 flat
```

The Mahler row is the sharpest single instance in this audit: **a reading the
system-wide vote explicitly confirmed against four sharps is destroyed by one
detection at confidence 0.33**, and every note after measure 6 on that staff is
spelled against one sharp.

⚠️ **And the protection that exists is applied to the wrong cell.**
`skip_key_sig_detection` (`:1628`) suppresses the cell reader on the staff's
**FIRST** cell precisely because the vote has already ruled — the code comment
says *"re-reading them here in isolation can only discard that context"* — and
then adds *"Later cells still run"*. **The argument for suppression is strictly
stronger on the later cells**: on cell 0 the reader is looking at the printed key
signature, and on cell 11 it is looking at ink that resembles one. The suppression
is applied where the reader is most likely right and withheld where it is most
likely wrong. Measured: **104 first-cell key markers and 15 later-cell markers on
scans, the later ones at confidence 0.26–0.70 (median 0.42), and 7 of the 15
change the staff's key.** Engraved: 176 first-cell, **0 later-cell** — hence 0
flips there.

### R8.2 What this changes about the recommendation

Round 2 said *port the meter guard's shape to the clef*. The three-instance form
says something different and more useful:

> **The neighbourhood needs one rule, not three retrofits.** Three facts with
> identical lifetimes (established per cell, carried forward, overwritten by any
> later cell) have three unrelated protections, and the differences are
> historical rather than principled: the meter was guarded because a specific
> Beethoven page shipped as common time, the clef because two string families
> were misread on one edition, and the key signature never because nobody looked.

⚠️ **The witnesses genuinely differ and must not be unified** — this is the
discipline that survives from round 2 and it now has three cases rather than two:

| fact | scope | available independent witness |
|---|---|---|
| METER | **system** — printed on every staff at the same bar | other staves at the same measure index (what the guard uses; exact) |
| KEY SIGNATURE | **staff**, but ALSO system-scope in practice — a key change is printed on every staff | ⚠️ **both**: the staff's own header vote (already computed, already consulted for cell 0) **and** cross-staff corroboration |
| CLEF | **staff** — printed on one staff alone | the staff's own header reading; more than one cell; the same part on another system |

**The key signature is the cheapest of the three to guard and the only one that
is currently unguarded**, because the evidence it needs is not merely available —
it has already been computed, has already been used on the adjacent cell, and is
already recorded on the staff dict with its reason string.

⚠️ **Not a proposal to ship.** Every one of the three is a behaviour change and
this audit changes nothing. What I claim is measured: the reach (11 / 7 / 0), the
mechanism (count fallback; no floor; unconditional), the confidences (0.26–0.82
across all eighteen), and that the guard's own evidence for the key signature
already exists. ⚠️ The clef item stays **coupled to `OMR_INSTRUMENT_CLEF_DEFAULT`**
and moves only with Sean; a key-signature guard is **not** so coupled — it touches
no identity and no allowlist — which makes it the cheaper first arm of the two.
The A/B that can fail: flag default-off ⇒ byte-identical, and the arm must not
suppress a *real* key change, of which this corpus contains **zero** on either
family — so a corpus that contains one is a prerequisite before any default flips.

---

## R9. `export.py` beyond one site

### R9.1 ⚠️ The record the whole audit has been asking for already exists — on 5,896 noteheads, read by nobody

`pitch_candidates` is on **every notehead in both corpora**, always three
entries, always with a distinct runner-up and a numeric weight
(`out/probe_pitch_candidates_payload.txt`):

| | scan | engraved |
|---|--:|--:|
| noteheads | 4,339 | 1,557 |
| carrying `pitch_candidates` | **4,339 (100%)** | **1,557 (100%)** |
| list size | 3, always | 3, always |
| with a distinct runner-up | 4,339 | 1,557 |
| winner − runner-up weight margin, p10 / median / p90 | **0.213** / 0.523 / 0.640 | 0.541 / 0.623 / 0.667 |

A real example, verbatim: `pitch C6 (0.982) · D6 (0.351) · Bb5 (0.315)`.

**This is exactly the form every decision in both rounds was found to be missing
— a winner, a runner-up and a margin — and it exists at one site, for the one
fact that needed it least** (notehead reading F1 is 0.999 on engravings), and it
reaches no production consumer: `grep -c pitch_candidates export.py` is 0, and
`clef_correction.py:312` *pops* it unread.

The margin is not decorative: the scan p10 of 0.213 against the engraved 0.541
says the record already separates confident pitch reads from marginal ones, and
separates the two families in the right direction, with no work.

⚠️ **No proposal to consume it.** The standing rule holds — record first, give it
a consumer only when a corpus prices one — and its one existing reader
(`maestro_bridge/re-rank.ts`) is off by default. What is worth stating is the
**architectural** fact: the pipeline knows how to build this record and does so
5,896 times per benchmark run; it is not a capability that has to be invented for
the clef, the key signature or glyph ownership, only extended.

### R9.2 Two export nulls, stated because they look like hazards and are not

- **`_parse_pitch:217` → `<rest/>`.** The map flags that an unparsable primary
  pitch becomes a rest rather than falling to candidate #2. **Reach on both
  corpora: 0 noteheads of 5,896 have no parsable pitch.** The hazard is latent,
  not live, and the fall-to-candidate-2 repair would currently fire never.
- **Piano grouping by `len(staves) == 2` (`:3428`, `:3505`).** Every system in
  both corpora carries 3+ staves (scan `[12,13,14,17,…]`, engraved 11–25), so
  the *"a 2-staff orchestral extract becomes a piano"* hazard has **reach 0**
  here. It is real and this corpus cannot see it — which is the honest statement,
  and the same shape as the eleven-work benchmark's blindness to the eventless
  measure.

### R9.3 The type reading for the stage, unchanged and now with a reason

Export decisions are the only ones in the pipeline whose reversibility is
trivially *nothing downstream*, so **every quantisation there is terminal** — and
it is also the one stage where recording is free of consequence, because no later
stage exists to be confused by an extra field. That asymmetry is why §R9.1's
observation is worth more here than anywhere else: the stage that can least
afford to destroy a margin is the stage that already receives one, on every note,
and drops it.

---

## R10. `direction_text`'s CV half — catalogued, with the reach that is and is not measurable

The ~60 points round 2 left. ⚠️ **Almost none of them has a measurable reach from
committed artefacts**, because the CV half runs on page rasters and the result
JSON records only its output count. I say that rather than producing numbers the
substrate cannot support. What the funnel *does* pin down is the aggregate:
**139 candidates proposed across 11 scan pages** (`out/probe_direction_funnel.txt`),
i.e. everything below produced 139 survivors.

| decision (`direction_text.py`) | type | C/O | constant standing | destroys | records? |
|---|---|---|---|---|---|
| `_page_ink:273`, threshold at `:278` — a fixed grey 180 | hard threshold | OPINION | ⚠️ **a bare literal**, and the one place the module bypasses `page.binary` on the stated grounds that Sauvola is tuned for staff lines. No sweep cited | the grey value; every sub-threshold letter | no |
| band reach above / below (`above_spaces 8.0`, `below_spaces 3.0`, `clearance 0.25`) | geometric window | OPINION | **measured and documented as OVERLAPPING** — the docstring states plainly that Mahler's title sits closer than Beethoven's direction, so no vertical reach separates them | the distance itself | no |
| `above_first_measure_only` | hard gate on x | **CONSTRAINT-shaped** — a heading is centred on the page, a direction is left-aligned to its music | keeps both real directions, refuses all four heading blocks on the three probe pages | which of the two rules refused | no |
| letter filters (`min/max_glyph_height 0.18/2.00`, `max_width 2.00`) | hard gates | OPINION | measured against a specific pair (bold `U` 1.79×1.65 vs italic `l` 0.4×1.1) and **tuned upward once**, from 1.60, to admit the `U` | the component | no |
| `min_fill_ratio 0.16` | hard gate | **CONSTRAINT-shaped** (a letter fills ⅕ of its box, a slur arc a ¹⁄₄₀) and a RATIO, so scale-free | the ratio | no |
| word clustering (`word_gap 2.20`, `min_components 3`, `min_word_width 0.9`, `min_word_height 0.55`) | hard gates | OPINION | `min_word_height` sits on a **real measured gap** (true directions 1.1–1.8, both false runs 0.2); the others are set past observed values on one page | the cluster | no |
| `_is_inside_a_word:282` — do not blank a dynamic with ink both sides | **exception to a blanking rule** | OPINION | measured as a GAP (a dynamic stands ~1.7 spaces clear; letters inside a word touch), and deliberately restricted to dynamics | ⚠️ **it is one half of §R1.3's collision** — this rule keeps the `f`, and the lexicon then refuses the phrase containing it | no |
| `max_blank_width_spaces 4.0` — a span's box is not blanked | hard gate | **CONSTRAINT-shaped**, on a **measured empty gap** in the class space (glyphs ≤ 3.2 spaces, spans ≥ 7.7) | which class made it a span | no |
| `page_is_engraved` → drop the Tesseract rung | classifier gate | OPINION | ⚠️ **the born-digital claim rests on three LilyPond fixtures**, which its own docstring flags. **Reach unmeasurable here**: all 11 scan pages report `False`, and the engraved fixtures were built `--no-direction-text` and carry no report | the second rung entirely | yes — `page_is_engraved` is in the report |
| `attach_to_page:825` — drop a direction whose measure is not found | abstention | CONSTRAINT | **reach 0**: 20 accepted, 20 placed | the direction | only via the count difference |

**The type pattern of the whole CV half is uniform and, unusually for this
report, largely defensible**: it is a cascade of hard gates on quantities
expressed in staff spaces, four of which sit on measured empty gaps or are
scale-free ratios, and the module is the only one in the audit that **returns a
structured report of its own funnel** rather than a bare count. That report is
why §R1 could be written at all, and it is the shape §R8.2 and §R9.1 are asking
every other stage to adopt.

⚠️ **The one thing the report does not carry is the CV half's own refusals** —
`find_candidates:505` returns survivors, so *"how many clusters were proposed and
rejected, and by which filter"* is exactly as invisible as
`staff_labels_surya._assign`'s dropped blocks (§R1.4). `n_candidates` is the
count *after* every filter. That is the single gap in an otherwise
well-instrumented module, and it is the same gap in the same shape as everywhere
else.

---

## R11. Probe hygiene — the endorsed fix, applied, and one it would not have caught

All sixteen probes now share `probe/_fixtures.py`:

- **`OMR_FIXTURE_ROOT`** selects the checkout (default: the main checkout), so a
  probe works from a worktree and from any CWD;
- **`fixtures(pattern, expect_at_least=N)` RAISES `SystemExit(2)`** on a short
  glob, and every family call names its expected row count (11 / 11 / 20), so a
  partially-populated fixtures directory fails as loudly as an empty one;
- **`chdir_root()`** exits 2 rather than tracebacking when the root is wrong.

Verified: every probe exits 0 from `/tmp`, and `OMR_FIXTURE_ROOT=/nonexistent`
gives **exit 2** with a one-line diagnosis rather than a clean empty table.

⚠️ **And the fix would NOT have caught §R8.0(b).** The globs were correct, the
files were read, the counts were real — the probe asked for a field that does not
exist and got `None`. Fixture hygiene protects against *no data*; it does not
protect against *the wrong field*. The complementary guard, now in both affected
probes, is an **assertion on the schema** at the point of read. Both are needed
and they are different.

---

## R12. Ranked conclusions, round 3

| # | conclusion | evidence | what would settle it | harness can see it? |
|--:|---|---|---|---|
| **1** | **Three adjacent per-cell overwrites — clef, key signature, meter — one fault, three levels of protection, and the surviving-flip counts rank inversely: 11 / 7 / 0 on 193 scan staves, 0 / 0 / 0 engraved** | §R8.1, three probes counting one quantity | separate A/Bs, each flag default-off ⇒ byte-identical. ⚠️ Clef stays coupled to `OMR_INSTRUMENT_CLEF_DEFAULT`; the key signature is **not** coupled and is the cheaper first arm | **YES** — clef and key both restate/re-spell pitches, so scan-gate note recall moves |
| **2** | **The key signature is unguarded, its flips all land on exactly one accidental via the COUNT fallback (`:857-858`), and 5 of 7 overturn a reading the cross-page vote had confirmed — one of them "agrees with the system's 4 sharps", destroyed by a 0.33 marker** | §R8.1 | as above. ⚠️ Prerequisite: this corpus contains **zero** real mid-staff key changes, so a corpus containing one is needed before any default flips | YES |
| **3** | **The suppression that exists is applied to the wrong cell** — `skip_key_sig_detection` silences the reader on cell 0, where it is most likely right, and lets it run on later cells, where 7 of 15 markers change the key | §R8.1 | a flag extending the existing suppression to later cells is a strictly smaller change than a new guard | YES |
| **4** | **`pitch_candidates` — winner, runner-up and margin — is present on 100% of noteheads (5,896) and read by no production consumer.** The record this audit keeps asking for exists, for the fact that needed it least | §R9.1 | nothing to settle; it is a capability statement. Consumers stay blocked on a corpus | n/a |
| **5** | **A new code-vs-prose disagreement:** `_detect_key_sig_from_cell:836-837` claims the count fallback means *"a reading is never lost — only improved on"*; mid-staff it replaces a 4-sharp staff with a count of 1 | §R8.1 | docstring | n/a |
| **6** | **My own probes lied twice, in the failure mode the verifier flagged elsewhere.** Fixture hygiene does not catch it; a schema assertion does | §R8.0(b), §R11 | done — both guards in the committed source | n/a |
| **7** | **`direction_text`'s CV half is the best-instrumented decision surface in the pipeline and still does not record its own refusals** — `n_candidates` is the count after every filter | §R10 | add per-filter rejection counts to the existing report. Byte-identical | n/a |

## R13. What round 3 does NOT cover

- **Precision of the 7 key-signature flips against print truth.** The truth
  MusicXML would answer it (a `<key>` after measure 1) and I did not run it; the
  mechanism (count-of-one from a single 0.26–0.57 marker) and the vote's own
  "agrees with the system" reason are the evidence offered instead.
- **Whether a key-signature guard would cost anything.** Zero real mid-staff key
  changes exist in either corpus, so this substrate can measure the benefit and
  **cannot** measure the cost.
- **The CV half's reach**, per §R10 — unmeasurable from artefacts, said rather
  than estimated.
- **`export.py`'s remaining sites.** Four measured across rounds 2–3; the map
  lists many more.
- **Anything requiring a run.** Embargo respected throughout all three rounds.

## R14. Reproducing round 3

```bash
export OMR_FIXTURE_ROOT=/Users/seanjohnson/Desktop/ReEngrave     # or any checkout
P=.claude/worktrees/nice-nash-085307/benchmarks/omr-pipeline-audit-2026-09/probe

python3 $P/probe_key_signature_flips.py        # R8.1  the third instance, with a schema assert
python3 $P/probe_meter_changes.py              # R8.0b re-derived under the corrected key
python3 $P/probe_clef_midstaff_flips.py        # R8.1  the eleven clef flips
python3 $P/probe_pitch_candidates_payload.py   # R9.1  the record nobody reads
python3 $P/probe_direction_funnel.py           # R10   the 139 -> 134 -> 20 funnel
```

Every probe now runs from any CWD, honours `OMR_FIXTURE_ROOT`, and **exits 2**
rather than printing an empty table when the fixtures are not where it looked.
