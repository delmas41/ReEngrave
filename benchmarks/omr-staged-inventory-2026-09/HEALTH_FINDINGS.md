# Per-stage "is this working" — read off the tests that already exist

`python3 -m tools.omr.staged.health` — the table is [HEALTH.md](HEALTH.md),
the machine copy `out/health.json`. `--check` exits non-zero on an empty cell;
`--run` also runs each staged test file and reports it.

Sean's bar, 2026-09-08: *"The tests currently may help us with if our tools and
stages are working but I am not worried about it looking better or worse."* So
it asks one question per decision — **is there a test saying it DECIDES what
it can, one saying it ABSTAINS when it cannot, and one saying it RECORDS
both?** Those three are `adjudicate.Ruling`'s own contract, and a decision
missing one is untested in a way a green suite cannot show.

---

## 1. The count in the handoff is stale: **226, not 153**

`for f in tools/omr/tests/test_staged_*.py; do pytest "$f"; done` at
`b2494cbc` totals 226 test functions across 16 files, not 153. One more
hand-counted figure that rotted — which is the argument for this being a
script.

## 2. ⚠️ WHAT THE EMPTY CELLS WERE, ALL CONFIRMED BY GREP BEFORE BEING BELIEVED

| decision | what was missing | confirmed by |
|---|---|---|
| `system_membership` | **decision #0 and NO staged test named it at all** | `grep -rn SYSTEM_MEMBERSHIP tools/omr/tests/test_staged_*.py` → 2 hits, both a docstring |
| `part_partition` | named ONLY by `test_staged_export.py`, which **supplies the join as a fixture** | `grep -rn PART_PARTITION` → 4 hits, all in the exporter's tests |
| `measure_partition` | no test asserted it DECIDES | the two `Outcome.DECIDED` hits build it as a fixture for `groups` |
| `group_symbol`, `key_signature`, `tuplet_ratio` | nothing asserted what they RECORD | — |
| `arc_owner`, `articulation_owner`, `wedge_anchor`, `dynamic`, `direction` | **five declared stubs no test named at all** | — |

⚠️ **"Structure first — everything else is addressed in terms of it" is
`ORDER`'s opening comment, and the first decision in it had no test.** A
passing suite cannot show that; only asking the registry what SHOULD have a
test can.

⚠️ **Coverage from a DOWNSTREAM stage is not coverage.** `part_partition`'s
only tests hand its verdict in and assert about the exporter. The check
reports that case by name.

All closed in `tools/omr/tests/test_staged_stage_contract.py` (19 tests).

## 3. ⚠️ `stub=True` IS A PROMISE AND NOTHING CHECKED IT

A stub always abstains with `not_implemented`; a stub that quietly returned a
value, or abstained for a different reason, would read downstream as ordinary
evidence. `test_staged_discipline.py` asserted the declarations are
consistent — that every stub says it is one — and nothing asserted the
BEHAVIOUR.

And the half that matters is what it records: a stub abstains **before reading
anything**, so `considered`, `used`, `basis`, `missing`, `declined` and
`detail` must all be empty. **A stub with evidence in its basis would mean it
looked at the page and still said `not_implemented`** — a different and much
worse thing than "not written yet".

## 4. ⚠️ THE REPORT SAID "EMPTY CELLS: none" ONCE BY ACCIDENT

Resolving a test that iterates `adjudicate.REGISTRY` / `ORDER` as covering
every decision emptied the report in one line: the discipline tests iterate
the whole registry to assert declaration properties, so every decision looked
covered in every shape. **A check that cannot fail is worse than no check.**

The over-broad clause was removed and its absence is pinned by
`test_staged_health.py::test_iterating_the_REGISTRY_does_NOT_credit_every_decision`.
The narrow case IS resolved and is bounded: a test iterating `stubs()` names
six decisions and asserts one behaviour, so it genuinely covers them.

⚠️ The shape classifier is TEXTUAL and undercounts — a test asserting in a
style the marker list does not name is invisible. **Its job is to point at the
empty cells, not to grade the full ones**, and every zero should be checked
with one `grep`. Both zeros it found on 2026-09-09 were checked that way and
both were real.

## 5. A NEW DERIVED CHECK, found by a test that was wrong first

`test_it_RECORDS_...` asserted that `gap_bridging` — declared in
`system_membership`'s `wants` — would show up in `Verdict.missing`. It does
not: `Evidence._note` records a quantity as missing only where the decision
actually QUERIED it. That semantic is right (a decision cannot be charged for
evidence it did not want on this subject) and it has a consequence:

⚠️ **A `wants` entry the decision never reads is INERT.** It declares nothing,
records nothing, and cannot be told apart from one that is read and always
present. `inventory` now reports it, following the decision's own helpers to
depth 3 within its module so `adjudicate_clef` asking for `clef_glyph` through
`_detector_terms` is not a false alarm:

| decision | declared and never read |
|---|---|
| `system_membership` | `gap_bridging` |
| `instrument` | `roster_entry`, `staff_ordinal`, `staff_group` |
| `part_partition` | `staff_ordinal`, `instrument` |
| `group_symbol` | `system_staff_count` |
| `clef` | `notehead_staff_position` |
| `key_signature` | `keysig_marker`, `dossier_fact` |
| `glyph_owner` | **`glyph_conf`**, `notehead_staff_position` |
| `tuplet_ratio` | `beam_stroke` |
| `duration` | `stem` |
| `meter` | `meter_glyph`, `duration`, `dossier_fact` |

⚠️ **`glyph_owner` / `glyph_conf` is the standing observation, reproduced.**
CLAUDE.md records that `_dedupe_cross_staff_detections` *"has both detections'
confidences in hand at the moment it decides and uses neither"*. The staged
rewrite declares the confidence and still does not read it — better, because
the declaration is visible, and now loud. `duration` / `stem` is known and
explained in `rhythm.py`'s own prose; the check makes it mechanical.

⚠️ **The check reported ZERO when first written**, because
`inspect.getsource` includes the decorator and `wants` lives there — so every
declared quantity "appeared in the source" and nothing could ever be flagged.
A zero is a suspect, not a result.

## 6. Per stage — where the tests are, and where they are not

| stage | tests |
|---|--:|
| RECORD | 261 |
| ADJUDICATE | 215 |
| PIPELINE | 92 |
| EVALUATE | 91 |
| GROUPS | 44 |
| **GATHER** | **27** |
| EXPORT | 19 |

⚠️ **GATHER is the thinnest real stage and it is the one the next work is
in.** Five of six stubs are starved because no gather site observes their
input (`arc_box`, `articulation_mark`, `wedge_box`, `dynamic_letter`), and
rests have no quantity at all — every one of those is a GATHER change first
and an adjudicator change second.
