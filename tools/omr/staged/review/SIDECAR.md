# The review-actions sidecar — the contract between the two 3.4 lanes

Roadmap 3.4. Lane (B), the viewer, **writes** this file. Lane (A),
`tools/omr/staged/review/`, **consumes** it. Neither lane may change the
required shape; an addition is an **optional** field and is documented here.

## The shape

```json
{"record": "<path to the record this pass was driven from>",
 "staff":  "staff/3/0/9",
 "actions": [
  {"id": "act-0001", "t": "<iso8601>", "stage": "gather",
   "kind": "add_box", "bbox_page_px": [x0,y0,x1,y1],
   "category": "noteheadBlack", "note": "..."},
  {"id": "act-0002", "t": "...", "stage": "gather",
   "kind": "delete_box", "glyph": "glyph/3/0/9/12/4", "note": "..."},
  {"id": "act-0003", "t": "...", "stage": "gather",
   "kind": "redraw_box", "glyph": "glyph/3/0/9/12/4",
   "bbox_page_px": [x0,y0,x1,y1], "note": "..."},
  {"id": "act-0004", "t": "...", "stage": "adjudicate|evaluate|infer|export",
   "kind": "agree|disagree", "verdict": "vrd:012111", "note": "..."}
]}
```

`id` must be unique across the file: it is how a verdict's `basis` is traced
back to a click, and two clicks sharing one id are a silently merged pair of
findings. `actions: []` is legal and is the **control** — an empty sidecar
must reproduce the record's verdicts N/N and the identical MusicXML.

## Optional fields lane (A) reads, all additive

| field | on | why |
|---|---|---|
| `reader` | the file, or one action | Which person filed these rows. **Must be a member of `record.READERS`** — `"sean"`, or `"session-test"` for a session standing in for him. A sidecar naming an undeclared reviewer is REFUSED rather than widening the vocabulary at run time: two rows from one reader are one signal, and a vocabulary a JSON file can extend cannot carry that meaning. Default `"sean"`. |
| `cell` | an `add_box` | `cell/3/0/9/12` — which measure cell the box was drawn in. **Strongly preferred.** See below. |
| `glyph` | an `add_box` | An existing glyph in the same cell, used only to resolve the cell. |

### ⚠️ An `add_box` must name its cell, and lane (A) will not guess it

A box arrives in **page pixels**; every consumer of `Q.GLYPH_BOX` reads the
**cell's canonical frame**. Converting between them needs to know which cell
the box belongs to, and deciding that from geometry alone is exactly the
padded-cell contest CLAUDE.md §10 says is resolved by `glyph_owner` and never
by a bounding test — the measure cell is padded 4 staff spaces (6 where the
neighbour is far) and on a conductor's page that reaches the next staff's ink.
A review tool inventing an answer there would file the human's evidence on the
wrong staff, which is the one failure that makes a correction worse than no
correction.

So: an `add_box` (or `redraw_box`) whose cell cannot be resolved from `cell`
or `glyph` is **refused, named, and reported** in the diff and the feedback
file. It is never dropped silently.

## What lane (A) does with each kind

| kind | becomes |
|---|---|
| `add_box` | an Observation of `Q.GLYPH_BOX` on a NEW glyph subject at the **human offset ordinal** (`human_evidence.HUMAN_GLYPH_BASE`, 400 000 — the fifth reader base, past gather's four), in the cell's canonical frame recovered from that cell's own rows; plus `Q.NOTEHEAD_CLASS` when the category is a notehead class, plus `Q.NOTEHEAD_STAFF_POSITION` when the cell's staff grid can be recovered. **Not** `Q.GLYPH_CONF`, `Q.GLYPH_BAND_DISTANCE`, `Q.GLYPH_LADDER`, `Q.BEAM_STROKE`, `Q.FLAG`, `Q.AUG_DOT` — see `human_evidence.HUMAN_BOX_ABSENT` for the reason on each. |
| `delete_box` | an Observation of `Q.HUMAN_BOX_VERDICT` = `"not_a_symbol"` on the named glyph. The machine's own `Q.GLYPH_BOX` row **stays**. `adjudicate_notehead_is_not_a_notehead` reads it and refuses the head with reason `human_not_a_symbol`. |
| `redraw_box` | both: a new human box (as `add_box`) **and** `Q.HUMAN_BOX_VERDICT` = `"redrawn"` on the original glyph. ⚠️ `redrawn` reaches **no consumer today** — dropping the machine's box is a decision nobody has taken. The feedback file reports it as a human row that changed nothing. |
| `agree` / `disagree` | an Observation of `Q.HUMAN_VERDICT_STANCE` on the **verdict's own subject**, with `detail.verdict_id`. ⚠️ It is filed against the verdict and **never applied**: no stage reads this quantity, deliberately, and `reach.KNOWN_GAPS` carries the reason. |

## The LABELS — an ADDITION, 2026-09-23 (roadmap 3.4c)

Sean, after his first minutes on the page: *"it works now but the UI is
awkward — I need to be able to select a box and re-label it"*, and *"and to
label boxes as nothing or belongs to another staff etc."*

So the viewer's panel asks one question — **WHAT IS THIS?** — and every answer
is one of the kinds below. **Nothing above changes**: `add_box`,
`delete_box`, `redraw_box`, `agree` and `disagree` keep their exact shape and
their exact meaning, and a lane (A) that had never heard of a label still
reads every sidecar it could read yesterday.

⚠️ **The label set is ONE TABLE, `human_evidence.HUMAN_BOX_LABELS`**, and
everything else derives from it — `check_sidecar`'s required fields,
`server.KIND_REQUIRES`, `/api/labels`, the viewer's panel and this row of the
document. The *etc.* in Sean's ask is satisfied by adding a row there, not by
editing four files.

⚠️ **`nothing` is spelled `delete_box`, deliberately.** The panel presents it
as the label *"nothing — not a symbol"*, because that is what he is saying,
but the sidecar kind stays `delete_box` and the filed value stays
`not_a_symbol`. A second spelling for one claim would make every sidecar
written before today ambiguous about which of the two it meant.

| kind | required | becomes |
|---|---|---|
| `relabel_box` | `glyph`, `category` | **two** rows. (a) `Q.HUMAN_BOX_VERDICT` = `"is_a:<class>"` on the ORIGINAL glyph, with `detail.machine_called_it` and `detail.filed_as`. (b) a human box of the NEW class at the human offset ordinal — the same machinery `add_box` uses, over the **machine's own** `detail.bbox_page_px` — with `detail.relabel_of`. A relabel of a glyph carrying no page rectangle is REFUSED whole: half a relabel is worse than none. |
| `own_box` | `glyph`, `staff` | `Q.HUMAN_BOX_VERDICT` = `"owner:<staff subject>"` on the glyph, plus `detail.twin_on_the_named_staff` — the id of the `Q.GLYPH_BAND_DISTANCE` row that proves the named staff holds the same ink, or `null`. A `staff` that is not a staff subject is refused (a part NAME is not a subject). |
| `dup_box` | `glyph`, `of` | `Q.HUMAN_BOX_VERDICT` = `"duplicate_of:<glyph>"`. The `of` glyph must hold rows in this record or the action is refused. |
| `unsure_box` | `glyph` | an **Abstention** on `Q.HUMAN_BOX_VERDICT`, reason `ABSTAIN.HUMAN_UNSURE`. ⚠️ Not a value: a reader who declined and a reader who answered are what `State.DECLINED` and `State.READ` exist to keep apart, and this is the record's first chance to say that of a PERSON. |

### What each label REACHES — measured, not asserted

`human_evidence.visibility()` derives this from the registries and
`rerun.py` measures it per run; the table below is what that derivation
returns on this tree.

| label | the decision that reads it | reason |
|---|---|---|
| `is_a:<non-notehead>` | `adjudicate_notehead_is_not_a_notehead` | `human_not_a_symbol`, `detail.human_says = is_a:<class>` |
| `is_a:<notehead class>` | **not a refusal.** `adjudicate_duration` decides on the human BOX's own subject with the new class | black→half is a disagreement about WHICH head, not whether there is one |
| `not_a_symbol` | `adjudicate_notehead_is_not_a_notehead` | `human_not_a_symbol` |
| `duplicate_of:<glyph>` | `adjudicate_notehead_is_not_a_notehead` | `human_not_a_symbol`, `human_says` naming the twin |
| `owner:<staff>` | `adjudicate_glyph_owner` | `human_owner` — **only on a glyph already in that decision's domain**, which is `subjects_from=Q.GLYPH_BAND_DISTANCE`, the CONTESTED population. On an uncontested glyph the row is filed, is handed to the notehead refusal (which declines it), and DECIDES nothing. |
| `human_unsure` | **nothing**, by design | the print is ambiguous; that is a convention question, not evidence |

⚠️ **A clef-class box in CELL 0 also files `Q.CLEF_GLYPH` and
`Q.CLEF_POSITION` on the STAFF** — the same two rows `gather_clefs` files for
a detected clef, measured the same way (position from the cell's own
recovered grid, with the control that can fail). Cell 0 only, because that is
gather's own rule: *a clef is read at the head of the staff*, and a mid-staff
clef change is a reading GATHER does not make. ⚠️⚠️ The row carries
`score=None`, and `clef._detector_terms` weights by `row.score`, reading
`None` as 0.0 and therefore as `W_DETECTOR_LOW` — **a human who read the
plate enters the clef contest as the weakest witness there is.** That is
wrong; it is reported rather than repaired by inventing a confidence, and
repairing it is a change to `clef.py`'s weighting with its own measurement.

⚠️ **An in-family relabel costs a duplicate note.** black→half adds the
human's half and refuses nothing, so the bar carries the machine's quarter as
well. Closing it needs either a rule that `is_a:<other notehead>` supersedes
the head class (`rhythm._head_class` reads `max(rows, key=score)`, so a human
row with no score would lose while still landing in that verdict's `used` —
which would read as WEIGHED and change nothing) or a rule that refuses the
machine's box, which is `redrawn`'s open question. Neither is taken here.

## Frames

`bbox_page_px` is `[x0, y0, x1, y1]` in **page pixels at the gather's own
DPI** — the same frame `Q.GLYPH_BOX.detail.bbox_page_px` carries. Lane (A)
recovers `upscale_factor` and the cell origin from the cell's existing glyph
rows and **checks every anchor against every other**; a cell whose anchors
disagree is refused with the spread printed, because a box in the wrong frame
is a measurement that looks exactly like a right one.
