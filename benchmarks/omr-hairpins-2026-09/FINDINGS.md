# Hairpins — the ninth export gap, and the two things it is not

*2026-09-03. `<wedge>` reaches both exporters. Measured on the eleven-work
engraved benchmark and on the five verified rows of the scan benchmark.
§2 named a staff-attribution gap and left it open; §6, same day, closes it.*

---

## The headline, both directions

| | pooled OMR-NED | edits | `wrong crescendo` | `wrong diminuendo` |
|---|--:|--:|--:|--:|
| engraved 11-work, before | 0.1306 | 2745 | 3 | 5 |
| engraved 11-work, **after** | **0.1304** | **2742** | **1** | **4** |
| engraved 11-work, **+ §6's attribution fix** | **0.1299** | **2733** | **1** | **3** |
| scanned 5-row, before | 0.7517 | 7894 | — | — |
| scanned 5-row, **after** | **0.7525** | **7904** | — | — |

The §6 row is the controlled A/B (§6 explains why, and why a from-scratch
rebuild lands on a different pooled number for reasons that are not this fix).

Two changes are in that "after", and they are separable — the scan column moves
for one of them and the engraved column for the other:

* **hairpins**, worth −3 edits on the engraved side and **exactly zero on the
  scan side**, because the detector fires on no hairpin at all on any of the
  five scanned pages (§3);
* **[the eighth gap, still open until today](#4-the-eighth-fix-was-never-committed)**
  — a bar with no notes dropping its dynamics and words — worth +10 edits on
  the scan side and zero on the engraved side, in the direction the metric
  charges for being right about a bar that is wrong around it (§4).

Both arms re-export the SAME stored transcriptions
(`score_export_arm.py`), so nothing in either figure is detector noise. The
before arm reproduces CLAUDE.md's recorded per-work table to four places —
Mahler 0.0272, Tchaikovsky 6 0.1916, Brahms 4 0.2238, pooled 0.1306 / 2745 —
which is the control that says these fixtures are the canonical configuration.

⚠️ **The recorded headline block in CLAUDE.md is NOT updated by this.** It is
written by `orchestral_eval --omr-ned --record` and belongs to the merged tree;
run it there.

---

## 1. A slur is drawn OVER its notes; a hairpin is drawn BETWEEN them

This is the whole finding, and the first version of the change got it wrong.

Hairpins and slurs look like the same problem. Both are curves over a run of
notes; both are cut in two by the per-measure cell crop and have to be rejoined
in page pixels; both need a start note, a stop note, a `number=` level and a
single voice. So `annotate_wedges_in_slot` reuses `_merge_arcs_across_barlines`,
`_voice_of_notehead` and the numbering wholesale — and reused
`_noteheads_under` too, which is where it stopped working.

`_noteheads_under` asks which noteheads the ink COVERS. **It returns nothing on
a real hairpin.** On the Mahler 5 fixture — the only page in the benchmark whose
hairpins the detector reads at all — the Trumpet staff prints a diminuendo at
page x 5922-6068 in a bar whose only notehead spans 5817-5897. The hairpin does
not overlap the note it applies to by one pixel, because the engraver drew it in
the space the note leaves. All four detections behave that way: **0 of 4**.

So the edges are read as POINTERS instead:

* **start** — the note whose centre is NEAREST the left edge, either side of it;
* **stop** — the note still sounding at the right edge, unless the next attack
  is within reach of it.

### The start rule was measured, and the obvious one is wrong

"The last note at or before the left edge" is the reading that follows from
"the hairpin begins after its note". It is wrong: the ink begins slightly
BEFORE the note it starts on. On the Tchaikovsky 6 fixture the crescendo's ink
begins **26 px left** of the note it starts on and **105 px right** of the
previous one — so a before-the-edge rule reaches back past the answer every
time.

Scored against the truth's own spans over all eleven works
(`probe_stop_rule.py`, pairing on part + measure + offset and asking whether the
KIND and the DURATION agree — which is what musicdiff compares, a wedge being a
music21 spanner):

| start rule | truth hairpins | we export | paired | **exactly right** |
|---|--:|--:|--:|--:|
| last at or before the edge | 8 | 6 | 1 | 1 |
| **nearest, either side** | 8 | **5** | **4** | **4** |

### The stop rule has a plateau nothing exercises, and says so

The right edge admits two readings and the ink cannot be asked which. A hairpin
can END ON a note — a crescendo drawn up to the downbeat it arrives at — or END
UNDER one, drawn in the space a long note leaves, in which case the note it
started on is also the note it stops on. **Both are in the Mahler truth**: two
of its three hairpins span one note, and the third runs `m5 -> m6`.

`_WEDGE_STOP_REACH_NOTEHEADS` is how close the next attack must stand to be
taken as the stop. Every value from 0.0 to 1.5 scores 4 exact and 2.0 scores 0.

⚠️ **That plateau is vacuous and the constant is weaker than the ones around
it.** It scores identically across the range because the reaching branch never
FIRES: all five hairpins we export end under a note still sounding, so 0.0 would
do as well. The other shape is real and is unmeasurable here — the Mahler
crescendo that has it landed its detection on the empty staff below (§2). 1.0 is
the middle of a range known not to hurt, chosen to handle that shape when it
arrives. It is not read off a gap in a population, and it should be re-swept the
first time a corpus contains one.

---

## 2. Why only 5 of 8, and why that is not an export problem

The detector fires **9 hairpin boxes** over the eleven works against 8 truth
hairpins, and we export 5. The 4 that do not come out are not lost on the way to
the file:

* **3 of Mahler's 4 sit on a staff with ZERO detected noteheads** — staff 18,
  one below the Trumpet staff that actually prints them. A hairpin is drawn in
  the gap under its staff, and `transcribe._dedupe_cross_staff_detections`
  awards a contested glyph to the nearer five-line band. **This is the same
  failure CLAUDE.md already records for ledger noteheads**, in the same
  function, for the same geometric reason — and the ledger-ladder evidence that
  fixed it there has no analogue for a hairpin, which has no ladder. A hairpin
  needs a note at each end and there is none to have.
* **Brahms 4's one confident detection (0.91) is dropped** because the note the
  truth starts it on was never detected: our reading of that bar holds one
  notehead where the truth holds several, so the anchors come out in the wrong
  order and the pass abstains rather than guessing.

The one hairpin we export WRONG (Brahms 4, +1 edit) comes from the other
detection on that page — a 679×24 px box at confidence **0.28**, spanning a
whole cell, which is a line and not a hairpin.

**So the ninth gap is not the eight before it.** The first eight were export
fixes outright: the detector had the symbol and the file did not. Here, wiring
the exporter takes `<wedge>` from 0 elements to 10 and from 3 truth hairpins
matched to 4, and it cannot take it further, because the rest are not in the
transcription to export. Closing a categorical gap is not the same as reading
the symbol.

---

## 3. The scan benchmark cannot price this, and a zero there is not a null result

Its truth carries **20 hairpins** across the five verified rows. The detector
fires on **none** — zero `dynamicCrescendoHairpin` and zero
`dynamicDiminuendoHairpin` across all five pages, at the pipeline's own
defaults on production scan weights.

So the scan arm of the export change is byte-identical by construction, and
`0.7517 -> 0.7517` was verified rather than assumed (every one of the five
`.omr.musicxml` files diffs empty against the baseline export). The +10 edits in
the headline table belong entirely to §4.

⚠️ This is the shape CLAUDE.md warns about under `OMR_CELL_LINE_TRACE`: a
benchmark that cannot express a fault cannot price its repair. **On scans,
hairpins are a DETECTION problem and this change is not addressed to it.** The
lever is the labeling pipeline, and the classes are already in the DSv2 class
space.

---

## 4. The eighth fix was never committed

Found by looking for it, because a hairpin over a resting staff would hit the
same branch the direction reader hits.

A measure the detector found no events in takes the whole-measure-rest path,
which appends the rest directly and **never calls `_mxl_voice_events` — the only
thing that emits `<direction>`**. `_dyn` is computed one line above the branch
and silently discarded. Both export sites had it. It had been dropping DYNAMICS
since they shipped, a month before the direction reader existed.

Commit `a907e41` (2026-09-02), and its duplicate `46e42a4`, describe this fix in
detail — "Both export sites had it", "Both are covered by tests now", a measured
no-change on the engraved benchmark — and **contain one file each, a Surya
determinism probe.** The export hunk is in no commit on any branch: `git log
--all -S 'directions=_dyn' -- tools/omr/export.py` returns only `89277a2`, the
commit that introduced dynamics. `test_direction_text.py` has no test for the
case either. The branch was live on main on 2026-09-03.

**THE TREE OUTRANKS THE LEDGER**, including a ledger written as a commit
message in the tree's own history.

Fixed in `export._mxl_empty_measure`, with the four unit tests the message had
promised. Marks go BEFORE the rest, so they land at offset 0 of the bar: there
is no event to place them against — that is what makes the bar empty — so
`_direction_slots`' nearest-note rule has nothing to say.

Measured: **2 measures** across the five verified scan rows carry marks and no
events (Beethoven 5 / IMSLP 984073 and Mahler 5, one dynamic each), and **0**
across all eleven engraved works, which is exactly why sixteen benchmark rounds
never saw it — an engraved page puts an event in every bar.

⚠️ **It makes the scan figure WORSE by 10 edits and ships anyway.** The whole
delta is `entire measure insert/delete` 2731 → 2741, with `wrong dynamic`
unchanged: both recovered marks land in bars that do not pair, where the charge
is already delete-whole-bar plus insert-whole-bar, and a correct symbol added to
such a bar raises a charge already being levied whole. Same call as the
articulation ship (+97 pooled, still right) and `b8ccc89` (chords bottom-up, +2,
still right). The dynamic is printed on the page and belongs in the file.

---

## 5. LilyPond gets less than MusicXML, on purpose

`\<` … `\!` are post-events on notes, so the same anchors serve — but LilyPond
is stricter than MusicXML in two ways, and `_lily_wedge_plan` DROPS rather than
approximates, because an unterminated `\<` is a compile warning and a hairpin
drawn to the wrong place.

| | MusicXML | LilyPond |
|---|---|---|
| a hairpin under ONE long note | written (start, note, stop) | dropped — `c4\<\!` is not a hairpin |
| two overlapping hairpins | `number="1"` and `number="2"` | the second is dropped; there is no level |
| two hairpins TOUCHING on one note | both | both — `e'4\!\>` is ordinary |
| ends in different LilyPond voices | n/a | dropped (see below) |
| across a system break | written | never offered — one `\new Staff` per system |

The voice case is not the transcription's voices: `_lone_voice_is_the_second`
routes a measure's lone voice to `\voiceTwo` when its stems point down, PER
MEASURE, so a wedge spanning two measures can find its ends in different lanes.
`_lily_staff_block` therefore decides the lanes ONCE, before rendering, so the
planner sees the same lanes the renderer will use.

The one hairpin the engraved benchmark exports is the single-note case, so
**LilyPond emits none of it** and the path is covered by unit tests plus a
compile check rather than by the benchmark: a synthesised two-hairpin bar
renders `c'4\< d'4 e'4\!\> f'4\!` and compiles under `lilypond -s` with no
warnings.

---

## 6. §2's gap closes — a hairpin belongs to the staff whose notes it spans

*2026-09-03, same day.* §2 named the fault and left it open: three of Mahler's
four hairpin detections were landing on staff 18, empty of noteheads on the
whole page, because a hairpin sits in the GAP below its own staff and a
contested copy's centre falls roughly midway between the two staves
bracketing that gap — distance, which is what
`transcribe._dedupe_cross_staff_detections` used for every glyph with no
ledger ladder, is close to a coin flip there. Measured on the actual contested
pairs (page pixels, `mahler-sym5-mvt1`, staff 17 above / staff 18 below,
five-line bands 4729-4894 / 5080-5246): the three misattributed hairpins sit
at centre y 4975-5018, **5 to 62 px nearer staff 18's top** than staff 17's
bottom — the fourth, correctly kept, sits 25 px the other way. Nothing
separates the four cleanly by distance; what separates them is that staff 17
carries a notehead in every one of those bars and staff 18 carries none, on
the whole page.

**The fix is a veto, not a rule about which side a hairpin prints on.** Of the
two signals CLAUDE.md flagged as worth measuring — "the staff whose notes it
spans in x" and "the printed-side convention (prefer the staff above)" — only
the first is exercised by anything in this corpus, so only the first shipped.
`transcribe._WEDGE_HAIRPIN_CLASSES` names the two wedge classes, and a new
tier in `_dedupe_cross_staff_detections` fires only when both contested copies
are one of them: if exactly one side's bar holds a notehead, that side wins,
ahead of distance and at the same rank as the pitch-range veto (a hairpin
needs a note to attach to at both ends, `export.annotate_wedges_in_slot`, and
a staff with none in that bar can never export it). Where **both** sides have
a note — the case the "prefer above" idea was for — nothing in the eleven-work
corpus exercises it, so distance is still the whole rule there, same as before
today. `TestHairpinDedupePrefersTheStaffWithNotes`
(`tools/omr/tests/test_transcribe_helpers.py`) pins the veto and both
fall-through cases, including a plain `dynamicF` letter to confirm the veto
does not leak into the rest of the `dynamic` category.

**Effect, measured two ways.** `score_export_arm.py` re-exports the eleven
stored transcriptions with `mahler-sym5-mvt1` alone re-run through the fixed
`transcribe()` (the other ten are byte-identical inputs, and byte-identical
under re-export too, since none of their hairpin detections were ever
contested with an empty staff — confirmed by inspecting `brahms-sym4-mvt1` and
`tchaikovsky-sym6-mvt2`, whose hairpins already sat on staves that carry
notes):

| | pooled OMR-NED | edits | `wrong crescendo` | `wrong diminuendo` | Mahler 5 |
|---|--:|--:|--:|--:|--:|
| §1-§5 (this doc's "after") | 0.1304 | 2742 | 1 | 4 | 0.0267 / 51 |
| **+ staff-attribution fix** | **0.1299** | **2733** | **1** | **3** | **0.0219 / 42** |

All nine edits are Mahler's, matching its own delta exactly — the pool moves by
exactly what one work moves by, which is the isolation check
`score_export_arm.py` exists to make possible without re-running the detector
on ten unrelated pages. `probe_stop_rule.py` at the shipped configuration
(`nearest`, reach `1.0`) reads the same story from the truth-pairing side —
Mahler's exported hairpins go from 1 of 3 truth to **3 of 3**, paired 1 → 3,
exact 1 → 2 (the third pairs correctly but not on an exact duration, which is
a separate, already-documented plateau — §1 — not this fix). Brahms 4 and
Tchaikovsky 6 are unchanged: `truth 2 ours 1 paired 0` and `truth 3 ours 3
paired 3 exact 3` respectively, both before and after. **Eleven-work total:
5 of 8 truth hairpins exported → 7 of 8**, paired 4 → 6, exact 4 → 5.

**Confirmed with a full rebuild — and the confirmation itself surfaced a
second finding.** `orchestral_eval --omr-ned` re-detected all eleven works
fresh (not re-exported) rather than taking the fast arm's word alone, and the
CATEGORICAL result reproduces exactly: `wrong crescendo` still 1, `wrong
diminuendo` still 3, and all four of Mahler's hairpins land on staff 17 again
— same staff, same measures, independently re-detected. But the OVERALL
Mahler edit count did not land at 42 a second time: it came in at **50**
(OMR-NED 0.0261, truth 958 / pred 957), closer to the pre-fix 51 than to the
fast arm's 42. The same four hairpin boxes explain why once compared: their
confidences moved between the two runs — 0.84→0.85, 0.89→0.90, 0.90→0.93, and
**0.83→0.69** for the widest one — on byte-identical code and the same PDF.
That is CPU floating-point jitter in the detector itself (plausibly the same
family this project already suspected — see the Surya-nondeterminism lead in
project memory — though nothing here isolates which stage), and it moves
OTHER symbols on the page too, not just hairpins, which is what the extra ~8
edits are. **So there are now two honest numbers and they answer different
questions**: the fast arm's 0.1304 → 0.1299 (−9 edits, Mahler 51 → 42) is the
controlled, single-variable measurement — everything except this fix's own
effect held fixed, which is the entire reason `score_export_arm.py` re-exports
from stored transcriptions instead of re-detecting. The full rebuild's
0.1304 → 0.1303 (−1 pooled edit) is what a from-scratch run happens to land on
against unrelated detector noise of comparable size to the fix itself, and
reading it as "the fix barely helped" would be mistaking that noise for a
verdict — the hairpin-specific categories it actually measures (`wrong
crescendo`/`wrong diminuendo`) moved by exactly the amount the controlled arm
predicted. **Eleven-work total, either way: 5 of 8 truth hairpins exported →
7 of 8.**

**The scan benchmark still cannot price this, and still isn't asked to.** All
five verified scan rows detect zero hairpins of either class (re-confirmed
2026-09-03), so the veto's `is_hairpin` branch never fires there and the
scanned figure is unmoved by construction — the same non-result §3 already
recorded, now for a second fix in a row.

---

## Reproducing

```bash
python3 benchmarks/omr-hairpins-2026-09/probe_stop_rule.py     # the rule sweep
python3 benchmarks/omr-hairpins-2026-09/score_export_arm.py --label after
python3 -m tools.omr.export_coverage --all                    # wedge is gone
python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --score-only
python3 -m pytest tools/omr/tests/test_transcribe_helpers.py \
    -k Hairpin                                                 # §6's dedup veto
```

Both benchmark scripts read the fixtures `orchestral_eval` and `scan_eval` leave
behind and re-export from the stored `.omr.json`, so an A/B costs seconds rather
than the hour a full re-run does — and cannot move because the detector moved.
§6's `score_export_arm`/`probe_stop_rule` numbers above are the exception: they
follow re-running `transcribe()` on `mahler-sym5-mvt1.pdf` alone (the only work
with a contested hairpin), then re-exporting the pool as usual — cheaper than
`orchestral_eval --omr-ned`'s full eleven-work re-detection, and still a real
re-transcription rather than a re-export of stale detections.
