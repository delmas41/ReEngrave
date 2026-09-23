# How to count — the three acceptance pages, 2026-09-23

Nothing here needs building. Open each HTML file in a browser and fill the
matching CSV.

## 1. Open these three

- `../out/count-beethoven5-litolff-p3-2026-09-23.html` (Litolff 984073,
  pdf page index 3, bars 49–82)
- `../out/count-brahms1-breitkopf-p2-2026-09-23.html` (Breitkopf 317803,
  pdf page index 1, bars 8–22)
- `../out/count-beethoven5-engraved-p0-2026-09-23.html` (Verovio page-truth
  render, bars 1–7, 18 parts)

Self-contained: the print and our render are embedded, one printed system per
row, at the resolution the record was read at (600 dpi for the scans, native
for the page-truth render). Click a crop to open it full size.

## 2. What you are counting

CATEGORIES.md §0: **"One unit = one FIX-ACTION: one edit a human would make
in a score editor, counted at the largest scope that a single editorial
gesture repairs."**

The four categories (CATEGORIES.md §1):

- **`missing`** — "the print has it, the file does not. The human must ADD
  something."
- **`wrong`** — "the file has something there, and it says the wrong thing.
  The human must EDIT in place."
- **`spurious`** — "the file has something the print does not. The human
  must DELETE."
- **`would-not-notice`** — "a real difference that costs zero work... the
  human would ship the file without touching it." This one is **your** eye
  (§2c) — nobody else's judgement can stand in for it.

## 3. Filling the sheet

One CSV per page, in this folder, named `<doc>-<page>-SEAN-2026-09-23.csv`.
Each row is one printed staff on one system; `page`, `system`, staff order,
`part_name` and the printed bar range are already filled in. Put a count in
`missing`, `wrong`, `spurious`, or `would_not_notice` (blank = zero), the
`scope` beside it (§0's list, now also `part-range` — §4c), `missable` =
`yes` for a `wrong` you could plausibly miss on a real pass (§2c), and a
short `notes`.

## 4. What NOT to count

If the print has nothing there, don't count it `missing`. If our file failed
to read something the print DOES show, count it `missing` regardless of why
— no detection, or a decision that abstained — your work is the same either
way (CATEGORIES.md §3). A misdetection that never reaches the file (nothing
there to delete) isn't `spurious` — there's nothing to act on.

## 5. When you're done

Save the CSV. That's it — a session will commit it and read it back.
