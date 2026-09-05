# A fixture anchored at the origin cannot tell a corner from an extent

**2026-09-05.** `hairpin_detection._measure_for` shipped to main in PR #16 with

```python
if box[0] <= page_x <= box[0] + box[2]:      # treats box[2] as a WIDTH
```

while `types.py:146` documents `bbox_page_px` as `(x0, y0, x1, y1)` — **corners**.
Real data settles it: on `dvorak-sym9-mvt1-405834-p5` measure 7 is
`x0=4259, x1=4796` on a 5084-wide page, so the buggy right edge is
`4259 + 4796 = 9055` — off the page, which is why every measure swallowed every
hairpin to its right and **41 of 59 hairpins (69%) landed in the wrong measure**
(dynamics session's measurement; the fix is theirs and in progress).

## Why nineteen tests missed it

The module's fixture puts the first measure at **`x0 = 0`**, and at the origin
`0 + x1 == x1` — **the two conventions return the identical answer**. Nineteen
tests passed, including one named
`test_a_hairpin_lands_on_the_measure_that_contains_it`. Moving that fixture's
first measure to `x0 = 100` makes four of them fail against the old code
(verified by restoring the bug and re-running, not by assuming).

**The general rule: a fixture whose coordinates start at zero cannot
distinguish `(x0, y0, x1, y1)` from `(x, y, w, h)`.** Any test built on one is
blind to the whole convention-confusion family, however many assertions it
carries and however well its name describes the thing it cannot see.

## Where else this blindness exists in the suite

Swept 2026-09-05 — **18 fixtures anchor a bbox at `x0 = 0`**:

```
test_clef_correction.py:25          test_line_detection_beams.py:37
test_clef_locator.py:165           test_line_detection_stems.py:36, 167
test_clef_reader_precedence.py:35  test_phase2.py:93, 125, 195, 238, 252
test_clipped_noteheads.py:30       test_staff_line_removal.py:44
test_header_ink.py:228             test_time_signature_locator.py:88
test_header_reader.py:45           test_key_signature_locator.py:74
test_key_signature_template.py:47
```

⚠️ **This is a list of blind spots, NOT a list of bugs.** Most of these pass a
whole-cell box to code that never re-derives an edge from it, so the convention
never matters and moving the anchor would prove nothing. The list is worth
having for one purpose: **when a defect in the corner/extent family is
suspected, these are the fixtures that cannot rule it out.**

The cheap general prophylactic, for new fixtures rather than a sweep of old
ones: **anchor test geometry away from the origin** (`x0 = 100`, not `0`).
It costs nothing and it makes the two conventions disagree, which is the whole
point of a fixture.

## The pattern this belongs to

Same family as the rest-regex that missed `<rest measure="yes" />` and the
`signed_fifths` that returns 0 for both "C major printed" and "nothing read":
**two distinct facts collapsing to one representation**, where the collapse is
invisible precisely where it is most convenient. See
[the detector-right/output-wrong taxonomy](discussion-detector-right-output-wrong-2026-09-04.md)
class 5 (right value, wrong unit or frame) and
`[[feedback_corroboration_is_not_evidence]]` in memory.
