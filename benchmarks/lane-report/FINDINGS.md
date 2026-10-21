# 2.188 -- the shared lane report (tooling, no default)

Command: `python3 -m tools.omr.staged.lane_report --flag OMR_X --out DIR` (docs/running.md §2b). STAGED, ADJUDICATE..EXPORT replay of the
20261020-night records; a GATHER flag re-gathers (`--from gather`, built, NOT run end to end -- needs two detector gathers; first
user should smoke it on one page).

**Frozen sample** (`sample.json`, seed 2188, `random.Random(2188)` over every page of the record holding staves, nothing excluded):
Litolff pages 2 4 6 8 9 10 11 16 (of 1-16); Brahms pages 0 4 5 8 12 14 19 25 (of 0-26). Each plate also LOADS its opening page
(Litolff 1, Brahms 0 -- in the Brahms sample anyway) and never counts it: the first run, without it, could not size a whole rest
(606 `size_measure_rest` verdicts missing) because the meter is printed on page 1 -- a slice is only faithful with the page whose
meter/key every later bar inherits.

**What the controls showed (CLAUDE rule 7).**
- Identity (unknown flag, OFF==ON): first build reported "+185 -185 notes" on Litolff -- padding rests/notes written with no glyph box were
  paired by list; fixed (they are counted per bar, never paired); now `NOTHING CHANGED` on both plates.
- OFF reproduces the record: Litolff 8958/8958, Brahms 12324/12324 duration/rest verdicts (row ids blanked: a slice renumbers rows).
- Known effect, `OMR_DOT_POSITION_OVER_WEDGE` (landed ON 2.180; OFF=0 vs ON=1): Litolff nothing; Brahms notes +6, dots +16, ties +6,
  articulations +1, blue -7/+4, red bars 174 -> 166, judged wrong->right 4, right->wrong 0. The control line says ON reproduces the
  record (default-ON flag), OFF moves 20 verdicts -- as it must.
- Tiles: 12 (9 changes stratified by kind, 3 controls), orange box, key outside the folder; looked at the sheet, boxes sit on the symbol.

**Wall time** 11 min for both plates at `--workers 4` (Brahms ~10 min an arm), 16 min at the default 2. First run adds ~2 min of slicing.
That is "minutes", not seconds: the cost is the ADJUDICATE..INFER replay of ~9 dense pages per arm.

**Known limits.** Pairing is by page position (a symbol with no glyph box is counted per bar, no tile). Red-bar warning words show as
`words`. A flag read at import time is safe (one process per arm); a flag read only in the web path is not exercised. Context page
means a cross-page rule that needs a page other than the opening one is not reproduced (the control line would say so).
