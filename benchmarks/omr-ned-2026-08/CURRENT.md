# The current engraved figure — GENERATED

The one place the engraved 11-work OMR-NED figure is written. The block
below is rendered from `current-accuracy.json` by
`python3 -m tools.omr.accuracy_record --update` and checked by `--check`;
do not hand-edit it, and do not restate a current figure anywhere else.
It is the ENGRAVED CONTROL of the acceptance set (CLAUDE.md §6a), never the
objective: the metric is symmetric and rewards emitting fewer symbols.

<!-- accuracy:begin name=headline -->
Current on the engraved orchestral benchmark, measured on `6b230bd7`: **pooled 0.1122 / 2362 edits** over 11 works (Mahler 5 0.0209 at best, Dvorak 9 0.3380 at worst), across 10665 truth + 10381 predicted symbols. The direction reader is ON by default and needs `.venv-surya` or Tesseract; with neither — `--no-direction-text`, and what a machine with no OCR rung gets — **0.1214 / 2532**, measured on `6b230bd7`.

| work | OMR-NED | edits | note recall | precision | duration rate |
|---|--:|--:|--:|--:|--:|
| Mahler 5 | 0.0209 | 40 | 0.917 | 0.917 | 1.000 |
| Beethoven 5 | 0.0293 | 38 | 1.000 | 1.000 | 1.000 |
| Tchaikovsky 4 | 0.0444 | 69 | 0.925 | 0.925 | 1.000 |
| Bruckner 5 | 0.0931 | 185 | 0.962 | 0.962 | 1.000 |
| Brahms 1 | 0.0943 | 390 | 0.956 | 0.955 | 0.992 |
| Mozart 41 | 0.1025 | 301 | 0.991 | 0.991 | 0.947 |
| Beethoven 3 | 0.1294 | 215 | 0.975 | 0.975 | 1.000 |
| Mozart 40 | 0.1415 | 218 | 0.762 | 0.762 | 0.952 |
| Tchaikovsky 6 | 0.1855 | 266 | 0.756 | 0.747 | 0.985 |
| Brahms 4 | 0.2136 | 401 | 0.959 | 0.943 | 0.933 |
| Dvorak 9 | 0.3380 | 239 | 0.975 | 0.975 | 1.000 |
<!-- accuracy:end -->
