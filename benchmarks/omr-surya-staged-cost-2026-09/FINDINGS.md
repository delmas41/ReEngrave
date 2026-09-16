# Surya in the staged pipeline: what it costs, what it buys, and the verdict

2026-09-15/16. The experiment pre-registered in
[`docs/scope-surya-staged-optin-2026-09-16.md`](../../docs/scope-surya-staged-optin-2026-09-16.md)
§9, run on Sean's machine with the machine taken exclusively.

**VERDICT: the pre-registered rule says FLIP BOTH ON, and the experiment
found something bigger than the question it was asked.** The flag under
discussion costs **93 s/page** and buys **50 instrument identities on 75
staves, 50 of 50 correct against hand-read print truth**. The reader nobody
was asking about — `OMR_DIRECTION_TEXT`, **on by default since 2026-09-02** —
costs **267 s/page on the same document and yields SIX words.**

---

## 1. The verdict against the rule, which was written before the run

| §9 clause | required | measured | |
|---|---|---|---|
| Part A median attributable | ≤ 30 s/page | **17.8 / 17.9 s** | ✓ |
| Part A max over 12 page-runs | ≤ 60 s | **18.8 s** | ✓ |
| Part B L − C | ≤ 25 % of C | **20.5 %** | ✓ |
| "keep opt-in" trigger | L−C > 50 % of C **and** > 2× noise | 20.5 % | not triggered |

**The flip is Sean's call and nothing in `pipeline.py` / `__main__.py` has
been changed.**

## 2. Part A — the attributable numerator, measured twice

Litolff Beethoven 5 p1-4, dpi 600, `OMR_SURYA_KEEP_ALIVE=0`, no resident
server, no detector. Two independent runs of 12 page-runs each.

| | run 1 | run 2 |
|---|--:|--:|
| **median attributable** (Surya spawn + Tesseract) | **17.8 s/page** | **17.9 s/page** |
| max | 18.8 s | 18.3 s |
| Surya first spawn | 16.7 s | 16.8 s |
| Surya **second** spawn, same process | 16.6 s | 16.9 s |
| Tesseract | 1.1 s | 1.1 s |
| prepare (render + detect — *not* attributable) | 0.8 s | 0.7 s |

⚠️ **THE MODEL LOAD IS NOT SHARED BETWEEN SPAWNS.** Over 24 paired calls the
second costs **+0.12 s mean MORE** than the first — not a fraction, not a
warm-cache discount. So the cost is per SPAWN, and scope §7's
single-subprocess merge is worth ~17 s/page **more than the flag itself**.

⚠️ **THE COST DOES NOT SCALE WITH THE PAGE.** 12 staves / 1 system and 22
staves / 2 systems both cost ~17 s. The documented "1.5 s per system" term is
real and is noise beside a fixed ~16 s spawn+load.

**Yield, over 75 staves** — because a cost with no yield beside it is half a
decision:

| rung | raw | consumable |
|---|--:|--:|
| text layer | **0** | **0** |
| Surya | **50** | **49** |
| Tesseract | 49 | 42 |

The 50 reproduces the scope's own "50 labels over 75 staves" exactly and
independently. Surya and Tesseract are within ONE label raw and SEVEN apart
consumable — the quality gap the cascade order already encodes, measured
here rather than inherited (page 3: Surya 11/11/11, Tesseract 10/8/8).

## 3. Accuracy — 50 of 50, against truth that is not an OCR output

Reach is not accuracy, and this repo's scar is that `Tr. Teq.` → Trumpet
resolves at MEDIUM on a trombone staff while nothing in the staged path
outranks a matched label. Sean asked whether his hand labels could answer it.

**50 labels scored, 50 correct, 0 wrong** (`probe_label_accuracy.py`).

⚠️ **THE OBVIOUS TRUTH FILE IS CIRCULAR AND IS NOT USED.**
`printed-lineups.json`'s own `_provenance` says its `full` lineup's NAMES
come from the OCR's read of page 1. Scoring the reader against names the
reader supplied is the reader agreeing with itself. What is used instead:
**structure** from the hand-read per-system suppression lists, and **names**
from `works.json`'s hand-confirmed `staves[i].name`, which are RICHER than
anything the reader produced — `Clarinetti in B`, `Corni in Es`,
`Timpani in C.G.`. A truth carrying a transposition the reader never read is
not a copy of the reader.

It scores the RESOLVED INSTRUMENT, not the string, because that is the unit
that reaches a consumer. **And it ties Part A's two counts together**: the
single label below `high` is `'Obol.'` at `low` — correct instrument, dropped
by every consumer. So the one non-consumable label is a correct reading held
back by caution, which is the right direction for the failure to run.

## 4. Part B — six arms, and an arm-order drift that L3 revealed

```
by start order:  L1 1980   C1 1753   L2 2203   C2 1872   L3 2352   LD 1378
```

⚠️ **EVERY SUCCESSIVE ARM IS SLOWER, IN BOTH CONDITIONS, WHILE MACHINE LOAD
FELL 7.07 → 3.82.** L slope **+93 s per position**, C slope **+59.5**. The
223 s first taken for a noise floor is DRIFT. Once the within-condition drift
line is removed the residual scatter is **L −12 / +25 / −12** and **C +0 /
+0** — a real floor of about **±25 s**. ⚠️ **The cause is UNKNOWN**: no
thermal warning is recorded and load fell throughout.

| estimator | L − C | as % of C |
|---|--:|--:|
| naive means (L at 1,3,5 and C at 2,4 — both centred at position 3.0) | 365.8 s | 20.2 % |
| drift-corrected (each C against the mean of its FLANKING L arms) | **372.0 s** | **20.5 %** |

The two agree because the ABAB design is balanced, which is what it is for.
An earlier figure of 279 s was L centred at position 2 against C at 3,
deflated by exactly one drift step.

## 5. ⚠️⚠️ THE FINDING THE EXPERIMENT WAS NOT ASKED FOR: the direction reader

**LD — labels ON, directions OFF — is 1378 s, FASTER THAN EVERY OTHER ARM,
including both C arms that carry no label reader at all.**

| | over 4 pages | per page | what it yields |
|---|--:|--:|---|
| the flag under discussion (labels) | **372 s** | **93 s** | **50 labels → 50 instruments, 50/50 correct** |
| `OMR_DIRECTION_TEXT` (directions) | **~1067 s** | **~267 s** | **6 accepted words** (`direction_word` read 6, declined 1180) |

Ratio **2.9 : 1**, and per unit of output it is 7.4 s per instrument against
~178 s per word. The scope guessed at this in §3 — *"the 'time it adds'
memory most plausibly attaches to the direction-text flag"* — and it is now
measured. **Sean opted out of the cheap reader; the expensive one has been on
by default since 2026-09-02.**

⚠️ This is a figure for THIS document. CLAUDE.md records direction text as
worth **144 edits on the ENGRAVED orchestral benchmark, 18.8 % of the pooled
figure**. Its value there is not in question and nothing here touches it. On
a low-res bitonal scan it returns six words for eighteen minutes.

## 6. ⚠️ The pre-registered residue hypothesis is REFUTED

Part A attributes 71 s of the 372 s. The hypothesis, written in
`decompose.py`'s docstring before the numbers were read, was that the ~300 s
residue is everything the pipeline does once identity is DECIDED.

**The records say the arms do essentially the same work.** `arc_kind` 779,
`duration` 2636, `dynamic` 1175, `event` 1117, `notehead_is_a_whole_rest`
2347, `stem_direction` 1443 and `direction` 1183 are identical in both. The
entire difference is `instrument` 50 vs 0, `slot_index` 50 vs 12,
`group_symbol` 7 vs 0, `clef` 70 vs 69, `key_signature` 49 vs 48 — about a
hundred extra decisions out of eighteen thousand. That cannot be 300 seconds.

**The surviving candidate, and the ranked next test: a Surya SPAWN costs more
from inside a gather than from a tiny probe process.** The staged process
holds four 600-dpi rasters, ten thousand detections and a 137 MB log; forking
from a multi-GB parent is not free. It would also explain the drift if system
memory pressure accumulates across arms. **Unmeasured.**

## 7. What the record now says, and could not before

Step 1 of this session, validated on real production runs:

| arm | what the 75 staves record |
|---|---|
| C (today's default) | `out_of_scope: 75` — *no OCR rung was asked* |
| L / LD | `no_ink: 25`, and **`OBS:surya: 50`** |

Before the fix every one of those said `no_ink` with `reader: text_layer` —
"this page prints no instrument name" on 75 staves where no rung that can
read a scan was ever asked, and 50 labels attributed to the one rung that
certainly did not find them. The sibling session's committed Brahms record
shows the same fault in the wild: **97 labels, all filed under `text_layer`,
on a PDF with no text layer on any of its four pages.**

## 8. What is NOT established

- **n = 1 document, 1 publisher, 4 pages**, on the low-res bitonal Litolff
  `984073` this repo already calls the pessimistic end of the corpus.
- **The drift's cause.** It is comparable in size to the effect and the
  design only cancels it because it is balanced.
- **The 300 s residue.**
- **Accuracy of the 25 unread staves' absence** — reach and accuracy are
  separate and only accuracy-on-what-was-read is measured.
- **Nothing about the engraved family**, which is where direction text is
  measured to be worth 144 edits.

## 9. Ranked next

1. **Sean's call on the flip.** The rule says flip; §8 says it is his.
2. ⚠️ **Re-price `OMR_DIRECTION_TEXT` on scans.** 267 s/page for six words on
   this document, and it is a DEFAULT. This is now the biggest lever in the
   file and it was not the question.
3. **Merge the two Surya subprocesses per page** (§7) — worth ~17 s/page from
   Part A alone, and more if the spawn-from-a-big-process hypothesis holds.
4. **Test that hypothesis**: measure RSS at spawn time, or re-run Part A from
   a process that has allocated several GB.
5. **A second publisher.** Breitkopf Brahms 1's staged record now exists
   (`library/_shared-records/brahms1-breitkopf-p0-p3.record.json`, written by
   a sibling session while this ran) and closes the 09-15 handoff's §11 gap.

## 10. Instrument defects found, all of one family

Every one failed by computing the wrong thing while looking fine:

- the scope's census `grep` **inverts** after Step 1 — a C arm that must
  census zero greps as ~75;
- `census.py`'s first draft used a bare-`Log` indent against a CLI record
  nested one level deeper: found the summary, found zero rows, printed
  `census OK: 0`. Caught by disagreeing with the record's own summary, which
  is now a VOID check in both directions;
- the in-flight gate, v1 `pgrep -f` matched 8 shells that merely MENTION the
  module → failed **closed**, aborted L1; v2 used `comm`, which macOS
  truncates to 15 chars → failed **open**, protecting nothing; v3 (`args=`,
  `$1 ~ python`) is right, verified against a live arm;
- `case` matched `L*` before `LD`, so the decomposition arm ran as a
  duplicate L arm. **Caught only because the arm prints its own
  configuration** — and kept as L3, where it revealed the drift;
- §9 control 2's `dirty=false` is **unsatisfiable as written**: arms stamp an
  unfiltered `git status` and each arm dirties the tree with its own output.
  The substantive check — no TRACKED modification, one commit — holds.

⚠️ **And one leak that is a real operational hazard**: C2 left an orphaned
`llama-server` and a LIVE SENTINEL behind despite `OMR_SURYA_KEEP_ALIVE=0`,
which would have made LD attach instead of spawn. The precheck gate caught
it and refused the arm. **A run can be contaminated by the previous run's
leak, and `--check` between arms is what stands between that and a silently
wrong number.**
