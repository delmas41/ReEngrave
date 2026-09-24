---
name: engrave
description: Run the full OMR pipeline on a music score PDF — extract notation via Claude Vision, review, and export corrected MusicXML + PDF.
---

# /engrave — Music Score OMR Pipeline

You are running the ReEngrave OMR pipeline. This takes a scanned PDF of a music score and produces corrected MusicXML and an engraved PDF.

## Input

The user provides a PDF path as an argument: `/engrave path/to/score.pdf`
If no argument is given, ask the user for the PDF path.

Also ask for (or infer from the score):
- **Title** (can be extracted from page 1)
- **Composer** (can be extracted from page 1)
- **Era** (baroque/classical/romantic/modern — helps with pattern matching)

## Tools Directory

All Python tools are in `tools/engrave/`. Run them from the project root:
```bash
cd /Users/seanjohnson/Desktop/ReEngrave && python tools/engrave/omr_pipeline.py <command> <args>
```

## Pipeline Steps

### Step 0: Prerequisites Check

Run this first:
```bash
python -c "from pdf2image import convert_from_path; print('pdf2image: OK')"
which lilypond && echo "lilypond: OK"
which musicxml2ly && echo "musicxml2ly: OK"
```

Report any missing dependencies and offer to help install them.

### Step 1: Check Learning History

Before starting, load any learned patterns:
```bash
python -c "
import sys; sys.path.insert(0, 'tools/engrave')
from learning import get_session_summary, get_prompt_context
print(get_session_summary())
print('---')
print(get_prompt_context())
"
```

Tell the user how many past corrections inform this session and if any auto-accept rules will apply.

### Step 2: Extract PDF Pages

```bash
python tools/engrave/omr_pipeline.py extract "<pdf_path>" output/pages
```

This converts each PDF page to a 300 DPI PNG. Report the page count to the user.

**LARGE SCORE HANDLING:** If the score has more than 15 pages, process in chunks of 10 pages. This prevents context overflow. Track which chunk you're on and save intermediate results. Between chunks, write the accumulated JSON fragments to disk so progress is not lost.

### Step 3: Claude Vision OMR

This is the core step. For each page image, YOU (Claude) read the image and extract music notation.

**Processing strategy:**
- For scores ≤ 15 pages: process all pages in this session
- For scores 16-50 pages: process in chunks of 10 pages, saving JSON after each chunk
- For scores 50+ pages: process in chunks of 10, and tell the user you'll need multiple sessions

**For page 1**, read the image using the Read tool, then output this JSON structure:

```json
{
  "page": 1,
  "header": {
    "title": "Symphony No. 5",
    "composer": "Beethoven",
    "tempo": "Allegro con brio",
    "key": "C minor",
    "time": "2/4"
  },
  "parts": [
    {
      "part_id": "P1",
      "part_name": "Flute",
      "clef": "treble",
      "measures": [
        {
          "number": 1,
          "xml": "<measure number=\"1\"><attributes><divisions>1</divisions><key><fifths>-3</fifths><mode>minor</mode></key><time><beats>2</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><note><rest/><duration>2</duration><type>half</type></note></measure>"
        }
      ]
    }
  ]
}
```

**For pages 2+**, include context from page 1:
- The established part list (part IDs and names)
- The last measure number from the previous page
- Key and time signature in effect

Read each page image, then output the same JSON structure (without the header).

**MusicXML rules for your output:**
- Use MusicXML 4.0 elements: `<note>`, `<pitch>`, `<step>`, `<octave>`, `<alter>`, `<duration>`, `<type>`, `<rest>`, `<chord>`, `<dot>`, `<beam>`, `<tied>`, `<slur>`, `<dynamics>`, `<articulations>`, `<staccato>`, `<accent>`, `<fermata>`, `<grace>`, `<forward>`, `<backup>`
- Duration values: 1=quarter (when divisions=1), 2=half, 4=whole, etc.
- Type values: "whole", "half", "quarter", "eighth", "16th", "32nd", "64th"
- For chords, add `<chord/>` to the second and subsequent notes
- For ties, use both `<tied type="start"/>` and `<tie type="start"/>` on the starting note
- For accidentals, use both `<alter>` in `<pitch>` AND `<accidental>` element
- `<divisions>` should be consistent within a part (use 4 for 16th-note resolution, or 1 for simple pieces)

**IMPORTANT:** If any learned patterns exist (from Step 1), incorporate them. For example, if patterns indicate common misreadings for certain instruments, pay extra attention to those areas.

Save each page's JSON:
```bash
# Write the JSON to a file (use the Write tool)
# Path: output/claude_vision/page_001.json, page_002.json, etc.
```

### Step 4: Assemble MusicXML

Assemble Claude Vision's results:
```bash
python tools/engrave/omr_pipeline.py assemble output/claude_vision output/claude_vision/assembled.xml
```

### Step 5: Interactive Review

Present results to the user conversationally:

> "Processed 12 pages, 42 measures across 4 parts.
> Would you like me to walk through any measures, or export as-is?"

The user may ask to review specific measures or parts. If they request changes, build a corrections list:
```json
[
  {
    "part_id": "P1",
    "measure": 5,
    "action": "replace",
    "replacement_xml": "<measure number=\"5\">...</measure>"
  }
]
```

For each correction the user requests, record the decision for the learning system:
```python
python -c "
import sys; sys.path.insert(0, 'tools/engrave')
from learning import record_correction
record_correction(
    score_title='...',
    measure_number=5,
    part_id='P1',
    part_name='Violin I',
    instrument='violin',
    era='classical',
    engine_a='claude_vision',
    engine_b='user_correction',
    engine_a_xml='<measure>...</measure>',
    engine_b_xml='<measure>...</measure>',
    winner='user_correction',
    difference_type='accidental',
)
"
```

### Step 6: Patch & Export

Build the corrections list from the review decisions, then:

```bash
# Write corrections JSON
# Then patch:
python tools/engrave/omr_pipeline.py patch output/claude_vision/assembled.xml output/corrections.json output

# Engrave PDF:
python tools/engrave/omr_pipeline.py engrave output/corrected.xml output
```

If no corrections were needed (everything accepted as-is), just copy the assembled XML:
```bash
cp output/claude_vision/assembled.xml output/corrected.xml
python tools/engrave/omr_pipeline.py engrave output/corrected.xml output
```

### Step 7: Update Learning System

After the session, update patterns:
```bash
python -c "
import sys; sys.path.insert(0, 'tools/engrave')
from learning import update_patterns
result = update_patterns()
print(f'Updated: {result[\"total_corrections\"]} corrections, {len(result[\"patterns\"])} patterns')
"
```

### Step 8: Present Results

Tell the user where the output files are:
> **Done! Output files:**
> - MusicXML: `output/corrected.xml`
> - LilyPond source: `output/corrected.ly`
> - Engraved PDF: `output/corrected.pdf`
>
> Learning system updated with N new corrections.

## Error Handling

- If a page fails Claude Vision extraction, log it and continue with other pages. Mark the failed page in the output so the user can re-process it later.
- If LilyPond engraving fails, still deliver the corrected MusicXML. The user can try engraving manually or with different LilyPond settings.
- If the PDF has non-music pages (title pages, blank pages, text pages), skip them during OMR but note them.

## Re-processing

The user can ask to re-process specific pages or parts:
- "re-check page 3" → re-read page 3 image, re-extract, update the assembled XML
- "the viola part looks wrong throughout" → re-extract just the viola measures
- "just export what we have" → skip to Step 6

## Large Score Chunking Protocol

For scores over 15 pages:

1. Process pages 1-10 first (chunk 1)
2. Save all page JSONs to disk after chunk 1
3. Tell the user: "Chunk 1 complete (pages 1-10). Processing pages 11-20..."
4. Process pages 11-20 (chunk 2), carrying forward the part list and last measure number
5. Continue until all pages are done
6. Then proceed with assembly, review, export

Between chunks, always save state. If the session ends mid-chunk, the user can resume with:
`/engrave --resume output/` (detect existing page JSONs and continue from where we left off)

## Resume Protocol

If `output/claude_vision/` already has page JSON files:
1. List existing files: `ls output/claude_vision/page_*.json`
2. Determine which pages are done and which remain
3. Ask user: "Found existing results for pages 1-10. Resume from page 11? Or start fresh?"
4. If resuming, load the part list from page 1's JSON and continue
