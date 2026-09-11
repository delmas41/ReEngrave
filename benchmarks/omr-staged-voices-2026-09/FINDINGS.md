# Stem direction and voices — three rules that were present and could not fire

2026-09-10. No flag. `Q.STEM` has carried a stem's BOX since the CV rung was
wired — **1,189 rows on Litolff `984073` p1-3** — and `gather_coverage` listed
`stem_direction` in `NO_VOCABULARY`. The direction was derivable from a row
already on the record and undeclared, and **three rules depended on it**:

| rule | where | what it said |
|---|---|---|
| the divisi guard | `adjudicate_event` | `divisi_guard: "not_implemented"` |
| `_directions_conflict` | `export._events` | never saw a direction |
| the one-voice test | `export._paired_spans` | handed an **EMPTY** `voice_of` |

⚠️ **An inert rule is indistinguishable from one that ran and found nothing.**
That is why `adjudicate_event`'s field was written as `not_implemented` in the
first place: an earlier draft wrote `"ran"` wherever stem ROWS merely existed.

```bash
python3 benchmarks/omr-staged-voices-2026-09/voices_arm.py <staged.json>
```

---

## 1. MEASURED — Litolff `984073` p1-3, clean tree `87b5e929`, `dirty: false`

### Reach

| | |
|---|--:|
| CV stem rows | **1,189** |
| noteheads read | 1,339 |

### `stem_direction`

| outcome | reason | value | n |
|---|---|---|--:|
| decided | `stem_projection` | up | **466** |
| decided | `stem_projection` | down | **371** |
| abstained | `no_stem` | — | 436 |
| abstained | `stems_disagree` | — | 66 |

**837 of 1,339 noteheads (62.5%) get a direction.** ⚠️ The two silences are
reported apart and must stay so: `no_stem` is ORDINARY (a whole note has none,
and on a scan a stem is often simply missed) while `stems_disagree` is ink we
cannot read — two stems meeting one head and pointing opposite ways, which is
precisely the divisi/double-stop ambiguity this quantity exists to keep
straight.

### The divisi guard, which used to say `not_implemented`

| | |
|---|--:|
| bars it RAN on | **375** |
| bars with no direction decided | 419 |
| **chords SEPARATED that x alone would have merged** | **4** |

⚠️ **Four, not four hundred**, and that is the honest headline. The guard is a
refusal, it fires rarely, and on this page it changed four groupings. What it
is worth on the printed page is unmeasured.

### `voices`

| | |
|---|--:|
| bars decided `one_voice` | 775 |
| bars decided `two_voices` | **19** |
| bars abstained `nothing_to_split` | 59 |

---

## 2. THE FILE — and the partition is EXACT

Of the **19** bars the record reads as two streams:

| | n |
|---|--:|
| written with a `<backup>` | **11** |
| refused: an event **straddles two streams** | 5 |
| refused: a stream has **no written note** | 1 |
| the exporter wrote the bar as an **empty measure** | 2 |

**11 + 5 + 1 + 2 = 19.** ⚠️ The reasons are counted apart because their
repairs differ, and the fourth was added only after the other three summed to
17: a filter that does not partition reads as a complete account.

Also in the file: **11 rests duplicated across voices** (the declared cover),
and `<backup>` × 11.

---

## 3. ⚠️⚠️ THE ACCOUNTING CONTROL RAISED, ON A REAL PAGE, AND IT WAS RIGHT

The first run of this change died:

```
Unbalanced: 1863 noteheads+rests in the log, 1616 written and
            264 accounted as dropped — the difference went nowhere.
```

1616 + 264 = 1880, **17 more than 1863**. Opened:

> `Q.VOICES` partitions `Q.EVENT`'s groups — every notehead the record **READ**
> — while `export._events` groups only the ones it can **WRITE**. The two
> groupings are not forced to agree, so a chord the exporter formed can span
> two of the record's streams, and every one of its notes is written TWICE.

Measured: **7 chord events straddle two streams** — three of three notes and
four of two — which is `3×3 + 4×2 = 17`, matching the control **to the unit**.

⚠️ **THE REPAIR IS A REFUSAL, NOT A MAJORITY VOTE.** Assigning such a chord to
the stream holding most of its notes would be the EXPORTER deciding a question
the record did not answer — the same overreach as collapsing a narrowed
duration by argmax, which this module refuses one screen up and says so.

⚠️ **This is the third instance of *two grouping rules nothing forces to
agree*** in this file's history, and the first that a control caught rather
than a human. It is also an argument for keeping the balance an EQUALITY: the
rests-in-both-voices convention had already forced a subtraction into it, and
the temptation at that moment was to relax it to `<=`. Relaxing it would have
shipped this bug.

---

## 4. WHAT CHANGED IN THE FILE, AND THE ONE THING THAT NEEDS A HUMAN

One record, exported twice, with and without the `Q.VOICES` verdicts:

| counter | with | without |
|---|--:|--:|
| `two_voice_bars` | 11 | — |
| `rests` | 443 | 432 |
| `rests_duplicated_across_voices` | 11 | — |
| **`tie_spans_marked`** | **59** | **60** |
| **`ties`** | **48** | **49** |

⚠️⚠️ **ONE TIE SPAN IS NOW REFUSED, and that is `_paired_spans`'s one-voice
rule firing for the first time on this path.** Whether that tie is real needs a
human against the print: the rule exists because a span whose ends land in
different voices is UNPAIRED at both and makes the file INVALID, and it prefers
the longest run within one voice over dropping — so a net −1 is either a
correct refusal or a wrong voice split. **n = 1, and no claim is made either
way.**

---

## 5. WHAT IS NOT CLAIMED

* **No accuracy claim.** Nothing here compares a voice split against the print.
* **The 4 separated chords are a COUNT, not a win.** x-only grouping would have
  merged them; whether the page prints divisi there is unmeasured.
* **One document, one publisher**, and 62.5% of noteheads get a direction at
  all — so on this scan the whole mechanism is silent on more than a third of
  the notes, by design (`no_stem` never blocks a merge).
* **`stems_disagree` at 66 is unexplained.** It may be real divisi, or two CV
  strokes on one stem. Nothing here separates them.

---

## 6. THE MUTATION BATTERY

`benchmarks/omr-staged-fermata-2026-09/probe/battery.sh` covers both wirings:
**20 arms, all RED**, positive control SURVIVED, harness control NOT APPLIED.

⚠️ **Its first run reported FOUR survivors and three were the BATTERY'S OWN
faults**, which is the standing lesson arriving again:

1. Two GATHER arms SURVIVED because `test_staged_glyph_families.py` was not in
   the test list — **a battery whose tests do not reach the file it mutates
   measures its own scope, not the code.**
2. One arm SURVIVED because `for h in heads` occurs **three times** in
   `rhythm.py` and the first is in `adjudicate_tuplet` — it mutated a different
   function. Re-anchored on the whole expression.
3. ⚠️ **One was a genuine test gap and is now closed**: *hoist reads only the
   chord's FIRST head*. `group_chords_in_measure` sorts a chord LOWEST NOTE
   FIRST and the adjudicator names whichever member its x test picked, so
   reading the hoist off the first head alone loses every fermata owned by
   another member — and every existing test happened to own the first.
