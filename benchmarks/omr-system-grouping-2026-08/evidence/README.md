# Evidence — what was actually looked at

Kept because two of this benchmark's conclusions were **wrong until a page was
rendered and examined**, and the images are the record of that.

| image | what it settled |
|---|---|
| `ground-truth-brackets.png` | **The method that works.** Left-margin strips of 12 Beethoven 9 pages. One bracket, one system — count these, not visual blocks. This is what produced the ground truth the 43% → 86% result is scored against. |
| `wrong-ground-truth-thumbnails.png` | **The method that fails, kept deliberately.** The same pages as whole-page thumbnails. At this scale the brass-to-strings bracket gap is indistinguishable from a system break, and five single-system pages (30, 35, 40, 45, 50) were labelled as two. That mislabelling briefly made the connectivity change look like no gain at all. |
| `beethoven9-p70-systems-and-groups.png` | Two systems found correctly, each grouped **4 woodwinds \| 2 horns \| 5 strings** — the bracket-group recovery, verified by eye. |
| `nottebohm-p90-staves.png` | The page holds ~13 music staves, not the 6 that `test_pipeline.py` asserted for months. All 11 the detector finds are real music. |
