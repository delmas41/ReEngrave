# Phase 2 — the vote fixes

> **Both fixes are landed and measured end to end.** `2fd787c` (the vote) and
> `0bfe60d` (the weight). The full ground-truth corpus, the canonical benchmark
> and the beet5 scan page are in **§ Measured end to end** below, which
> supersedes the *Still owed* section this document opened with. Item #8 was
> re-measured against the fixed reference and is **refused, with numbers.**

**2026-09-01.** Successor to `PHASE1.md`, which established that inferring a
key signature from the music is a measured NO-GO and that both pages cited as
evidence for it were failing for a different reason: the cross-page vote.

Two defects were named there, and **both are now fixed and landed**.

| | before | after | landed |
|---|---|---|---|
| **bolero-p10** — lone template flats on empty headers | 6 correct / **5 wrong** | 6 correct / **0 wrong** | ✅ `2fd787c` |
| **beet5-p15** — three correct readings rejected | **0 correct / 6 wrong** | **3 correct / 1 wrong** | ✅ `0bfe60d` |

⚠️ **Everything from here to "Measured end to end" was written BEFORE fix 1 was
authorised, and its numbers are vote-level replays rather than end-to-end
scores.** It is kept because the diagnosis is the useful part — in particular
*why* the second defect could not be repaired inside `key_signature_vote.py`,
which is the reasoning that earned the authorisation. Where the two disagree,
the end-to-end section is the one that describes what ships. Two specific
corrections it makes: p.15's before is 6 wrong end-to-end (5 at vote level, the
sixth arriving from the measure pass), and pastoral-p2 is 9 correct end-to-end
rather than the 8 the vote replay shows.

---

## How these numbers were taken, and why not end-to-end

⚠️ **The tree was not pristine, and that decided the method.** While this phase
was running, another workstream held uncommitted edits in `tools/omr/rhythm.py`,
`tools/omr/transcribe.py`, `tools/omr/export.py`, `tools/omr/voicing.py` and
`tools/omr/time_signature_locator.py`, and landed `6cd4802` mid-session. A page
transcribed under that tree would have carried their changes as well as mine,
so an end-to-end number could not have been attributed to this fix — and one of
the files in flight is the very file bug 1 lives in.

`reconcile` is a **pure function of its candidate list**, so the vote's own
contribution can be measured exactly without re-running the model.
`probe_vote_inputs.py` captured the real candidate lists for both pages on
`8c6452e`; `replay_vote.py` replays them through the vote and scores against
ground truth with the same `_tally` used by
`benchmarks/omr-key-signature/eval_key_signatures.py`.

```bash
python3 benchmarks/omr-keysig-from-music-2026-09/replay_vote.py --verbose
```

Tree state at measurement (`git status --porcelain`, HEAD `8c6452e`, then
`6cd4802`):

```
 M benchmarks/omr-corpus-widening-2026-09/FINDINGS.md
 M benchmarks/omr-key-signature/ground_truth.json      <- mine
 M tools/omr/export.py                                 <- another workstream
 M tools/omr/key_signature_vote.py                     <- mine
 M tools/omr/rhythm.py                                 <- another workstream
 M tools/omr/tests/test_key_signature_vote.py          <- mine
 M tools/omr/tests/test_rhythm.py                      <- another workstream
 M tools/omr/tests/test_time_signature_locator.py      <- another workstream
 M tools/omr/tests/test_transcribe_helpers.py          <- another workstream
 M tools/omr/time_signature_locator.py                 <- another workstream
 M tools/omr/transcribe.py                             <- another workstream
 M tools/omr/voicing.py                                <- another workstream
```

**The end-to-end runs were owed at this point and have since been taken** —
see *Measured end to end*. `pytest tools/omr/tests -q` was green (**1494
passed**) before this commit; 1546 after both fixes.

---

## Fix 2 — landed. `2fd787c`

### The mechanism

Boléro p.10 is not a page whose signature was missed. It is Ravel's
parallel-harmony passage at bar 153, and it **genuinely prints five different
key signatures**: the two piccolos notated in E (4♯) and G (1♯) and the
clarinet in D (2♯), over a C major orchestra. The detector reads all three
correctly, at a weight equal to the number of accidentals printed.

Because five signatures are in play, no value holds a majority — the modal
tally is `{1♭: 5.0, 1♯: 2.0, 2♯: 4.0, 4♯: 8.0}` and the mode holds 8/19 = 42%,
under `min_majority = 0.5`. The vote therefore took its `no majority to check
against` branch, **which kept every reading unconditionally**, including five
template-reader assertions of a single flat on headers that print nothing —
one of them a percussion staff.

`StaffCandidate.can_carry` already marks a source that can OVER-count, which is
the one thing the module's whole safety argument assumes no reader does. Such a
reading was blocked from *travelling* to another system and not from *asserting*
where nothing could check it. It now has to clear `strong_weight` on its own
there — the same bar a departure clears when there IS a reference, and the bar
whose docstring already says *"a lone accidental is never enough on its own"*.

### The choice inside the fix, and what the alternative cost

**The guard is on the SOURCE, not the count.** A uniform
`weight >= strong_weight` rule in the no-majority branch would also have removed
the five bad readings — and would have cost the **second piccolo's 1♯**, which
is one accidental from the detector and is correctly printed on the page. Two
correct readings for five wrong ones is not the trade; keying on `can_carry`
costs nothing and is what the module already means by the distinction.

Pinned by `test_a_detector_reading_of_one_accidental_is_not_touched`.

### What it does not change

An empty signature stays a wildcard (`fifths == 0` is exempt — a staff read as
printing nothing must never be overwritten, and that is pinned). A template
reading of 3 flats off 3 matched accidentals still asserts. No detector or
locator reading can reach the guard at all, so every page whose readers are
`detector` / `cv_locator` is byte-identical. All 19 previously pinned vote
behaviours pass unchanged; 5 tests added.

---

## Fix 1 — the diagnosis (landed as `0bfe60d`; this section is why)

### Why the reference was wrong

On beet5 p.15 the vote sees 7 readings. **Three read the correct three flats.**
The reference comes out as **one flat**, set by exactly two readings, and the
three correct ones are then rejected for departing from it.

The reason is not that weightless readings are barred from the reference — that
rule is deliberate and defensible (a signature fitted against a guessed clef is
a guess squared). The reason is one line in `transcribe._page_key_signatures`:

```python
weight=(
    DEFAULTED_CLEF_WEIGHT if source == "template_default_clef"   # ← a CONSTANT
    else float(len(read.matched_slots))
) if read else 0.0,
```

**A defaulted clef REPLACES the accidental count instead of discounting it.** A
template reading of three flats and a template reading of one flat both arrive
as `0.5`. The module's own measure of evidence — how many accidentals were
actually matched — is thrown away for exactly the readings that need it, and
`_modal_reference`'s `weight < 1.0` exclusion then drops all of them together.

That is why the defect cannot be repaired inside `key_signature_vote.py`: **the
vote cannot distinguish a 3-flat reading from a 1-flat reading on a defaulted
clef, because both reach it as the same number.** Every variant tried inside the
vote either changes nothing on p.15 or reaches the right answer only by
target-chasing two independent behaviours at once (counting sub-1.0 readings at
`max(w, 1.0)` *and* flipping `_modal_reference`'s tie-break away from
`-abs(f)`), which is two changes made to hit one page.

### The change, and what it is worth

```python
weight=(
    abs(read.fifths) * DEFAULTED_CLEF_WEIGHT if source == "template_default_clef"
    else float(len(read.matched_slots))
) if read else 0.0,
```

Discount the evidence for the guessed clef; do not discard it. A guessed clef
halves what a reading is worth, three matched accidentals still outweigh one,
and `DEFAULTED_CLEF_WEIGHT` keeps its meaning and its value.

Replayed on p.15's recorded candidates:

| | correct | wrong | missed | correct-abstentions | reference |
|---|--:|--:|--:|--:|--:|
| today | **0** | **5** | 11 | 6 | **1♭** |
| with the weight fix | **3** | **0** | 13 | 6 | **3♭** |

Per staff:

| | read | weight | source | today | with the fix |
|---|--:|--:|---|---|---|
| sys1 ord1 Oboi | −3 | 0.50 | template_default_clef | rejected | **kept ✓** |
| sys1 ord7 Violino I | −3 | 0.50 | template_default_clef | rejected | **kept ✓** |
| sys1 ord8 Violino II | −3 | 0.50 | template_default_clef | rejected | **kept ✓** |
| sys0 ord7 Violino I | −2 | 0.50 | template_default_clef | rejected | rejected |
| sys0 ord8 Violino II | −1 | 0.50 | template_default_clef | kept ✗ | **rejected ✓** |
| sys1 ord9 Viola | −1 | 1.00 | detector | kept ✗ | **rejected ✓** |
| sys1 ord10 Vc/Cb | −1 | 1.00 | cv_locator | kept ✗ | **rejected ✓** |

It removes the wrong assertions as well as recovering the right ones, and it
does so through the machinery that already existed: with the reference at 3♭,
a 1♭ reading is a *departure* and `strong_weight` refuses it on one accidental.
**Boléro is untouched** — every clef there is detector-read, so no candidate
takes the `template_default_clef` path.

### Two things this does NOT do

* It does not resurrect inference or cross-system carry. The three recovered
  readings are readings — the template reader fitted three flats to the slot
  table on those staves. Nothing is synthesised from the reference, and
  `can_carry=False` still keeps template readings on their own staff.
* It does not fix the **sixth** wrong staff on p.15. `sys0 ord0` reads one flat
  from the MEASURE pass (`_detect_key_sig_from_cell`, off a single `keyFlat` at
  confidence 0.49), never reaching the vote at all. p.15 ends at 3 correct / 1
  wrong end-to-end, not 3/0.

### The other two sub-items of fix 1 are also in `transcribe.py`

The brief asked to reconsider two more things; both were traced and both live
in the caller, not the vote:

* **"rejection falls back rather than zeroing"** — `reconcile` already returns
  `fifths=None` with `action="rejected"`. The zeroing is
  `fifths[staff_index] = verdict.fifths or 0` in `transcribe`, and it is
  deliberate: the comment there says the judgement "has to reach the measure
  pass or the same reading simply reappears there". Changing it is a decision
  about the measure pass, not about the vote.
* **`min_majority` computed over voters** — real, and on p.15 it lets a
  reference standing on 2.0 of the page's weight report a **100% majority**.
  Measured rather than argued (an earlier draft of this section asserted it was
  worth nothing and that was wrong):

  | p.15, weight fix OFF | correct | wrong |
  |---|--:|--:|
  | as shipped | 0 | **5** |
  | denominator over ALL readings | 0 | **4** |

  It is worth one wrong reading, not zero. The mechanism is that it moves the
  page into the no-majority branch, where **fix 2's new guard** then refuses
  the one template 1♭ — the two changes compose. With the weight fix on, it
  changes nothing (3 correct / 0 wrong either way), because the reference is
  correct and the majority is real.

  ⚠️ **Not landed, deliberately.** It makes the no-majority branch fire on more
  pages, and that branch now REJECTS over-counting sources — so it can lose a
  correct template reading on a page whose reference is right but weakly held.
  One wrong reading on one page is not worth taking that risk unmeasured, and
  the corpus run that would measure it is in *Still owed*. Reproduce with the
  `honest_denominator` variant against `replay_vote.py`.

---

## Ground truth — `beet5-p15` added

`benchmarks/omr-key-signature/ground_truth.json` now carries a fourth page: the
printed key signature of all 11 parts of Beethoven 5 p.15, hand-read off a 500
dpi render, with the crop kept at `crops/beet5_p15_sys1_headers.png` so the
reading can be re-checked without re-rendering.

It is the first ground-truth page that is **mid-movement**, and the first
carrying three distinct written signatures for one concert key **including
natural brass and timpani printing none** — 3♭ on the flutes, oboes, bassoons
and every string part, 1♭ on the B♭ clarinets, 0 on the horns, trumpets and
timpani. beet5-p2 has that shape at the head of the movement; p.15 proves it
recurs where a system merely restates the signature, which is where the
cross-page vote does its work.

Two things recorded with it:

* It is the page roadmap #4b cited, and it had **no** per-staff ground truth
  until now — which is why `omr-keysig-blindspot-2026-08`'s +4 staves there
  were called unverifiable in that report.
* **The dossier disagrees with this print on 3 of the 11 parts.** The modern
  MusicXML edition `data/dossiers/beethoven-sym5-mvt1.json` is generated from
  gives C Trumpet and Timpani `written_fifths -3`; the 1870s print gives them
  none. That is an EDITION difference, not an error in either, and it is a
  caveat on using a dossier as external truth for a scan's key signatures.

⚠️ **A correction to PHASE1.md.** Its "WTC I p.17" control is PDF page **index
17**; the ground-truth page named `wtc-p17` is index **16**. Both are E major
with four sharps and both are read 4♯ on every staff, so the ladder finding
stands as stated — but the two are adjacent pages, not the same page, and
PHASE1's control was not the ground-truth page.

---

## Item #8 — the ordering argument (it was re-measured; see the end)

PHASE1 recommended: *fix R1 first, then re-run #8.* R1 is not landed, so #8's
re-measurement is not available — and this is not a scheduling excuse, it is
the same mechanism:

#8 routes the detector's `accidental*` classes into the key readers. Its
recorded cost was **beet5-p2 10 correct → 9**, and the blindspot report already
identified the mechanism: the one staff that moved read 5 flats where there are
3, the vote **rejected it for departing from the system's reference, and the
rejection zeroed the staff rather than reverting it to the correct reading it
already had.** Both halves of that sentence are still true today. Routing more
readings — from the noisiest source in the stack — into a vote whose reference
can be set by two under-counts, and whose rejection is lossy, measures the vote
and not the routing.

p.15 is the page #8 would help most: 19 of its 21 signature-region flats carry
the `accidentalFlat` role and are discarded (9.5% carry `keyFlat`). Re-measure
#8 once the weight fix has landed and the reference on that page is 3♭.

---

## wtc-p17 — verified, and by mechanism rather than by score

The page that must stay 10/10. Run through `probe_vote_inputs.py` on the
ground-truth page (index **16**, 5 systems, 10 staves):

```
  10 candidates, every one:  4#   weight 4.00   source detector   can_carry y
  reference per system: {0..4: '4#'}      modal tally: {'4#': 40.0}
```

Fix 2 **cannot fire here, twice over**: no candidate has `can_carry=False`, so
none can reach the guard, and the reference holds 100% of the weight so the
no-majority branch is never entered at all. 10 correct / 0 wrong, unchanged.

That is a stronger statement than a matching score would be — it says the page
is outside the change's reach by construction, not that it happened to come out
the same.

## Still owed — CLEARED

⚠️ Superseded by *Measured end to end*. Kept as written so the sequence is
legible; every item below has since been run.

* **The full ground-truth corpus end-to-end**, pipeline mode, all four pages
  (`eval_key_signatures.py --mode pipeline`, `--weights
  tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`
  — the default `omr-weights/` path does not exist in a worktree). Expected:
  wtc-p17 10/10 and beet5-p2 / pastoral-p2 unchanged, since fix 2 cannot fire
  on a detector or locator reading.
* **`orchestral_eval --omr-ned`** — the three engraved works read their
  signatures from the dossier, so fix 2 should be invisible there; if it is
  not, that is the finding.
* **beet5 p.1** (7/12 correct, 0 wrong): does fix 2 move it? Its readers would
  have to include a lone template accidental on a page with no majority.
* Both were deferred because the tree was carrying another workstream's
  in-flight edits to `transcribe.py`, `export.py` and `voicing.py`, and because
  `orchestral_eval` was running for that workstream throughout — the brief's
  own compute rule.

## Commits

| | |
|---|---|
| `2fd787c` | fix 2 — the no-majority branch, + 5 tests |
| *(this doc)* | ground truth `beet5-p15`, `replay_vote.py`, PHASE2.md |

---

# Measured end to end

Taken on a clean pipeline tree after workstream A released `transcribe.py`,
`export.py` and `voicing.py`. Every row is `eval_key_signatures.py --mode
pipeline` — the honest end-to-end number, not the vote replay — run twice, once
with the change and once with `git checkout tools/omr/transcribe.py` under it.

```bash
python3 benchmarks/omr-key-signature/eval_key_signatures.py --mode pipeline \
    --weights tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt
```

## The ground-truth corpus, before and after

| page | before | after | |
|---|---|---|---|
| **beet5-p15** | **0 correct / 6 wrong** / 10 missed / 6 ac | **3 correct / 1 wrong** / 12 missed / 6 ac | **+3 correct, −5 wrong** |
| beet5-p2 | 10 correct / 1 wrong / 6 missed / 5 ac | 10 / 1 / 6 / 5 | identical |
| pastoral-p2 | 9 correct / 0 wrong / 9 missed / 2 ac | 9 / 0 / 9 / 2 | identical |
| wtc-p17 | 10 correct / 0 wrong / 0 missed | 10 / 0 / 0 | identical |
| bolero-p10 *(control, not GT)* | 6 correct / **5 wrong** | 6 correct / **0 wrong** | fix 2, −5 wrong |
| beet5 scan p.1 | 9/12, 0 wrong | 9/12, 0 wrong | identical |

**No page loses a correct reading. No page gains a wrong one.**

Two things in that table that would be easy to misread:

* **beet5-p2's one wrong reading is PRE-EXISTING.** It is there before the
  change and after it, byte for byte. It is not something this work introduced,
  and the vote-level replay does not show it at all because it comes from the
  measure pass rather than the vote.
* **beet5 scan p.1 is 9/12, not the 7/12 the brief quoted**, and that is
  workstream A's gain arriving tonight, not mine — my own before/after on that
  page is identical. The same applies to pastoral-p2, where an earlier
  vote-level replay in this document read 8 rather than 9: the replay scores
  the VOTE, and the end-to-end number includes the measure pass. Two different
  quantities, and the earlier draft's guess that the difference was "tree
  drift" was wrong.

## The canonical engraved benchmark

```
OMR-NED (pooled over 3 scores): 0.1328     942 edits
  mahler 0.0331 / beethoven 0.1649 / brahms 0.1707
```

**Byte-identical to the record before and after both fixes** — same pooled
figure, same edit count, same per-work rows, same error histogram. No
`--record` run and no CLAUDE.md edit was needed. That is the expected result
and worth stating as a *positive*: the three engraved works take their
signatures from the dossier, so a change to how a READ signature is weighted
must not reach them, and it does not.

## The single wrong staff that remains on p.15

`sys0 ord0` still reads one flat where the page prints three. It never reaches
the vote: the MEASURE pass (`_detect_key_sig_from_cell`) reads it off a lone
`keyFlat` at confidence 0.49. Out of scope for both fixes, and named here so
nobody re-derives it.

---

# Item #8 — re-measured against the fixed reference, and REFUSED

PHASE1 predicted #8's `-1` was an artefact of the broken reference and asked
for it to be re-run once R1 landed. It was. **The answer is still no, and it is
now emphatically worse.**

The implementation is not in the repo (it was written, measured and discarded
in August), so it was rebuilt to the blindspot report's own specification: fall
back to `accidentalSharp` / `accidentalFlat` where no key-ROLE marker is found,
with an x-cut at the first notehead, `max_outliers=0`, and permission to assert
only a POSITIVE signature.

| page | fix 1 only | **+ item #8** |
|---|---|---|
| **beet5-p15** | **3 correct / 1 wrong** | **0 correct / 6 wrong** |
| beet5-p2 | 10 correct / 1 wrong | **9 correct** / 1 wrong |
| pastoral-p2 | 9 / 0 | 9 / 0 |
| wtc-p17 | 10 / 0 | 10 / 0 |

It reproduces its old `-1` on beet5-p2 and **undoes the entire p.15 gain**.

**Why, and this is the part worth keeping.** `_key_sig_read_from_dets` runs
FIRST, before the CV locator and before the template reader. Routing
accidentals into it means the noisy source now PRE-EMPTS the reader that was
getting the right answer: the p.15 staves acquire an accidental-derived reading
from a header cell that also contains inline accidentals, and the correct
three-flat template fit never happens. The blindspot report saw half of this —
"the accidental path read 5 flats where there are 3" — and the other half is
precedence, which only became visible once something downstream was succeeding.

So the sequencing recommended in PHASE1 was right and the conclusion it was
expected to overturn stands. **Do not re-open #8 as a change to
`_key_sig_read_from_dets`.** If the class-role gap is ever worth closing, it
has to enter LAST — behind the template reader, into gaps only — and be marked
as a source that can over-count so `can_carry=False` and fix 2's guard apply to
it. That is a different change from the one that has now been measured twice.

Reverted; `tools/omr/transcribe.py` is at `0bfe60d`. Suite green, 1546 passed.

---

# Commits

| | |
|---|---|
| `2fd787c` | fix 2 — the no-majority branch may not licence an over-counting source (+5 tests) |
| `664cc71` | ground truth: `beet5-p15`, and `replay_vote.py` |
| `339e04c` | correction: the `min_majority` denominator is worth 1 wrong reading, not 0 |
| `f3a5d7f` | `wtc-p17` is outside fix 2's reach by construction |
| `0bfe60d` | fix 1 — a guessed clef DISCOUNTS a reading (+6 tests) |

Nothing pushed.
