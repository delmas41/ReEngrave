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

## Frames

`bbox_page_px` is `[x0, y0, x1, y1]` in **page pixels at the gather's own
DPI** — the same frame `Q.GLYPH_BOX.detail.bbox_page_px` carries. Lane (A)
recovers `upscale_factor` and the cell origin from the cell's existing glyph
rows and **checks every anchor against every other**; a cell whose anchors
disagree is refused with the spread printed, because a box in the wrong frame
is a measurement that looks exactly like a right one.
