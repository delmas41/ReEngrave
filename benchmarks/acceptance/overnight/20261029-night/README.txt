compare_20261029 20261029-night vs 20261022-night docs [brahms1-breitkopf] tree 05f0b9eb9c9556b0207ded6b4e23df4129f7038a start 2026-10-30T13:12:04Z

== Manager summary (machine-assembled from the files named; rule-derived flags are CANDIDATES for a human reading)
Acceptance (20261022-night as run | 20261022-night re-exported by THIS tree | 20261029-night):
  Brahms  notes reaching file 15174/24375 -> 15155/24408 (0.623 -> 0.621); held-out bars 0 -> 0; red bars 628 -> 588; bars add up 5884 -> 6051; unread bars 251 -> 177; parts named 14/14 -> 14/14
      (like with like = the middle column; the BASE as it was run on its own night differs from its re-export by: addup 5786->5884, unread 349->251)
      noteheads logged changed 24375 -> 24408 (GATHER saw a different number of heads)
Sean's judged tiles, SAME current index, today's scorer on BOTH records (right/wrong/narrowed):
  Brahms  149/22/5 -> 151/19/5 ; right->wrong 0, right->gone 1, wrong->right 2, unwritten->wrong 0, unwritten->right 1
What changed in the exported file (gained/lost by kind; place-matched, lane_report.diff_arms; BASE and TAG both exported by THIS tree from SAVED verdicts):
  Brahms  whole movement:
     notes +238 -257 | rests +236 -138 | accidentals +98 -61 ~206 | dots +119 -79 | flags +68 -66 ~3 | beams +90 -166 ~65 | ties +90 -37 ~1 | slurs +41 -100 | articulations +48 -29 | fermatas +1 | note values ~95 | pitches ~308 | blue marks +587
     paired 21968 hosts (22272, 22319) red 628 588 blue 3252 3370 not written 11295 11285
  Brahms  frozen sample pages:
     notes +61 -31 | rests +30 -6 | accidentals +34 -11 ~66 | dots +37 -8 | flags +12 -15 | beams +9 -18 ~5 | ties +30 -12 | slurs +8 -10 | articulations +3 -8 | note values ~15 | pitches ~104 | blue marks +185 -105 | dynamics +1 | wedges +3 -1 
     paired 6482 hosts (6519, 6573) red 166 166 blue 930 1010 not written 3202 3160
First two stages (GATHER + ADJUDICATE), readout diff per family (a diff exits 1 when the records differ -- that is its normal 'differences found', not a failure):
  Brahms : 107986 differences in all; provenance differences: [["code", "commit", "a2eae688030feebf177a40e2b0f2404dafd61f28", "12325ce2991f7bc1f930fb4b569a754e0cf1ca0c"]]
     (other classes)    gathered 27388 -> 27387, matched 27377, only-BASE 11, only-TAG 13, pairs with a changed answer 0
     accidental         gathered 6544 -> 6540, matched 6539, only-BASE 5, only-TAG 0, pairs with a changed answer 6539
     articulation       gathered 1474 -> 1474, matched 1474, only-BASE 0, only-TAG 0, pairs with a changed answer 1474
     clef               gathered 1102 -> 1101, matched 1101, only-BASE 1, only-TAG 0, pairs with a changed answer 1101
     dot                gathered 10113 -> 10115, matched 10112, only-BASE 1, only-TAG 3, pairs with a changed answer 10112
     dynamic            gathered 3941 -> 3942, matched 3941, only-BASE 0, only-TAG 1, pairs with a changed answer 3941
     fermata            gathered 12 -> 12, matched 12, only-BASE 0, only-TAG 0, pairs with a changed answer 12
     key                gathered 1354 -> 1354, matched 1354, only-BASE 0, only-TAG 0, pairs with a changed answer 1354
     note               gathered 24375 -> 24408, matched 24367, only-BASE 8, only-TAG 41, pairs with a changed answer 24367
     ornament           gathered 24 -> 24, matched 24, only-BASE 0, only-TAG 0, pairs with a changed answer 24
     rest               gathered 8870 -> 8870, matched 8869, only-BASE 1, only-TAG 1, pairs with a changed answer 8869
     slur               gathered 3148 -> 3147, matched 3146, only-BASE 2, only-TAG 0, pairs with a changed answer 3146
     tie                gathered 11666 -> 11674, matched 11665, only-BASE 1, only-TAG 8, pairs with a changed answer 11665
     time               gathered 518 -> 518, matched 518, only-BASE 0, only-TAG 0, pairs with a changed answer 518
     tuplet             gathered 4 -> 4, matched 4, only-BASE 0, only-TAG 0, pairs with a changed answer 4
     wedge              gathered 2 -> 2, matched 2, only-BASE 0, only-TAG 0, pairs with a changed answer 2
     matched 1:1, nothing changed: 
Abstention reasons that moved (old -> new; logs_diff.txt has all; decided verdicts that moved are listed there too):
  brahms1-breitkopf
   accidental_owner                 is_a_key_signature_marker                   283     1480    +1197
   duration                         beams_ambiguous                             144      386     +242
   duration                         beam_discounted_uncertain                  2072     1863     -209
   accidental_owner                 no_candidate                                677      760      +83
   head_ink_is_a_rest               no_head_refused_on_the_ink                 7091     7168      +77
   stem_value                       not_a_member                               1233     1300      +67
   rest_is_not_a_rest               whole_rest_hangs                              0       50      +50
   glyph_owner                      tied                                        422      378      -44
   glyph_owner                      stem_disagrees                               45        1      -44
   stem_value                       stem_levels_unread                          776      733      -43
   unison_voices                    not_a_unison                              24142    24175      +33
   key_signature                    mixed_marker_kinds                           39       13      -26
   notehead_position                ledger_not_read                            4713     4738      +25
   duration                         owned_by_another_staff                     3484     3506      +22
   DECIDED verdicts that moved (quantity: base -> tag): accidental_is_not_an_accidental 6544 -> 6540; accidental_owner 3504 -> 3540; arc_is_not_an_arc 14814 -> 14821; arc_kind 14761 -> 14771; arc_owner 14814 -> 14821; arpeggiato_is_not_an_arpeggiato 860 -> 856; articulation_is_not_an_articulation 1472 
   ABSTENTIONS 105456 -> 106973; 72 reasons moved, 40 unchanged
The 2.229 product ranking on the new records (fix-actions per page, biggest first; the '10-29 rank' column is FINDINGS.md quoted, not recomputed):
  brahms ranking, fix-actions per page over 8 loaded pages, biggest first by TAG (BASE=base TAG=tag)
  kind                             BASE/pg    TAG/pg    delta   10-29 rank   (totals BASE -> TAG)
  ties and slurs not written         161.4     160.2     -1.1        160.0   1291 -> 1282
  pitched heads not written           42.9      40.8     -2.1         46.3   343 -> 326
  red bars                            20.8      20.8     +0.0         20.5   166 -> 166
  dots decided, never placed          17.1      17.1     +0.0         17.1   137 -> 137
  unread empty bars                   10.5       6.1     -4.4         14.5   84 -> 49
  blue notes (check load)             98.1     107.6     +9.5        107.0   785 -> 861
  blue rests (check load)             14.5      15.0     +0.5         13.2   116 -> 120
Files (machine-local, /Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/overnight-20261029-night/compare):
  brahms1-breitkopf musicxml  7.5 MB
  brahms1-breitkopf ly  1.0 MB
  brahms1-breitkopf pdf  10.2 MB

Surprising / worse (rule-derived candidates; a human reads each against the print):
  - Brahms : notes reaching the file DOWN 15174 -> 15155
  - Brahms : 1 judged answers went RIGHT -> gone (narrowed/abstained/not found)
  - Brahms  (other classes): GATHER boxes only-BASE 11 / only-TAG 13
  - Brahms  accidental: GATHER boxes only-BASE 5 / only-TAG 0
  - Brahms  clef: GATHER boxes only-BASE 1 / only-TAG 0
  - Brahms  dot: GATHER boxes only-BASE 1 / only-TAG 3
  - Brahms  dynamic: GATHER boxes only-BASE 0 / only-TAG 1
  - Brahms  note: GATHER boxes only-BASE 8 / only-TAG 41
  - Brahms  rest: GATHER boxes only-BASE 1 / only-TAG 1
  - Brahms  slur: GATHER boxes only-BASE 2 / only-TAG 0
  - Brahms  tie: GATHER boxes only-BASE 1 / only-TAG 8
  - abstention reason grew by +1197: accidental_owner is_a_key_signature_marker 283 1480 +1197
  - abstention reason grew by +242: duration beams_ambiguous 144 386 +242

== Process: how we got it
== commits
BASE a2eae688030feebf177a40e2b0f2404dafd61f28  TAG 12325ce2991f7bc1f930fb4b569a754e0cf1ca0c
git log --oneline a2eae6880..12325ce29: 395 commits (76 merges, 319 non-merge)
changed under tools/omr: 88 files changed, 14863 insertions(+), 223 deletions(-)
files changed by area: tests 45, staged 34, tools/omr/direction_lexicon.py 1, tools/omr/direction_text.py 1, tools/omr/key_signature_template.py 1, tools/omr/line_detection.py 1, tools/omr/measure_extractor.py 1, tools/omr/page_wide.py 1, tools/omr/staff_line_removal.py 1, tools/omr/time_signature_locator.py 1, tools/omr/yolo_detector.py 1

== ROADMAP items named in commit subjects (52; one line each, with the commit, in /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a34f16b60d63e545a/benchmarks/acceptance/overnight/20261029-night/process.txt):
  0.25 2.143 2.150 2.150b 2.179 2.183 2.187 2.187b 2.188 2.189 2.192 2.194 2.195 2.198 2.201 2.201b 2.202 2.202b 2.202c 2.202d 2.202e 2.202f 2.204 2.205 2.206 2.206b 2.206c 2.206d 2.206e 2.206f 2.207 2.208 2.209 2.210 2.211 2.212 2.213 2.213b 2.214 2.215 2.216 2.217 2.218 2.219 2.220 2.220b 2.220c 2.221 2.222 2.223 2.224 2.230
== 'Land' commits (the ones that flip a default)
  c19bf2e5b Land ROADMAP 2.183 + 2.187 ON (Sean 2026-10-23): OMR_KEY_SIGNATURE_CLAIM, OMR_KEY_PER_SYSTEM
  b7b649b5b Land ROADMAP 2.201 + 2.195 + 2.198 ON (Sean 2026-10-26): OMR_ACCIDENTAL_FAMILY, OMR_STROKE_MAP
  2db9c2f31 Land ROADMAP 2.205 ON (Sean 2026-10-26 "1. Yes"): OMR_STROKE_OWNER
  2f7638d69 Land ROADMAP 2.208 ON (Sean 2026-10-26 "Yes"): OMR_CLEF_SLOT_CLAIM
  1e839f905 Land ROADMAP 2.209 ON (Sean 2026-10-27 "Yes"): OMR_STEM_BEAM_END
  85055e8cd Land ROADMAP 2.211 (Sean 2026-10-27 "Yes"): score by written place
  e83bd6fc9 Land eraser path: OMR_ERASER_FIX, OMR_METER_SLOT, OMR_REST_OWN_STROKE, OMR_STEM_TIP_TRUE_EDGE, OMR_BEAM_OWN_EXTENT default ON (Sean 2026-10-27)
  f5405e8a9 Land head trim fix: OMR_HEAD_TRIM_LINE_ONLY default ON
  d51e3967c Land the judged scorer (lane-scorer-blue): key.json galleries scored, written_moves; DECISIONS + version_memory
  53b27557c Land head height cap 1.6 sp (OMR_HEAD_TRIM_LINE_ONLY_V2 default ON); DECISIONS, ROADMAP 2.220b, flags, version_memory
  c4ba3b869 Land the GATHER arc claim ON (OMR_ARC_CLAIM, lane-arcs-claim-1029); kind-from-ends and slur-from-anchors stay OFF
  16165283f Land duplicate-pass cleanup: DECISIONS + version_memory
  cd6151616 Land whole-rest bars ON (OMR_FOUND_WHOLE_REST, OMR_WHOLE_REST_HANGS, OMR_WHOLE_REST_PLAIN; lane-whole-rest-1029)
  846efa623 Land page-wide barlines ON (OMR_BARLINE_SYSTEM_COLUMNS, lane-barlines-1029)
  d5f555e5e Land 2.221 m1/m1b: page-wide word and bracket claims default ON (OMR_CLAIM_WORDS_FIRST, OMR_CLAIM_BRACKETS_FIRST)
  fac9ccc79 Land stem-end head reader from ink: OMR_STEM_END_HEAD_INK default ON (ROADMAP 2.224)

== flag DEFAULTS that differ (same AST scanner on both trees; ON = the default state)
flag                               BASE     TAG      GATHER? read in (TAG tree)
OMR_ACCIDENTAL_FAMILY              absent   ON       YES     accidental_family.py, adjudicators/ownership.py, export.py
OMR_BEAMS_FROM_STROKES             absent   ON       no      adjudicators/rhythm.py, beam_strokes.py, stroke_owner.py
OMR_BEAM_OWN_EXTENT                absent   ON       no      line_detection.py
OMR_CLAIM_BRACKETS_FIRST           absent   ON       YES     adjudicators/claimed_by.py, claims.py, export.py
OMR_CLAIM_WORDS_FIRST              absent   ON       YES     direction_lexicon.py, adjudicators/claimed_by.py, claims.py
OMR_CLEF_SLOT_CLAIM                absent   ON       YES     claims.py, gather.py, record.py
OMR_ERASER_FIX                     absent   ON       no      staff_line_removal.py
OMR_FILL_FROM_STROKES              absent   ON       YES     adjudicators/rhythm.py, export.py, gather.py
OMR_FOUND_WHOLE_REST               absent   ON       no      export.py
OMR_HEAD_TRIM_LINE_ONLY            absent   ON       no      head_ink.py
OMR_HEAD_TRIM_LINE_ONLY_V2         absent   ON       no      head_ink.py
OMR_KEY_PER_SYSTEM                 absent   ON       YES     gather.py, key_object.py, record.py
OMR_KEY_SIGNATURE_CLAIM            absent   ON       YES     adjudicators/claimed_by.py, adjudicators/family_precision.py, adjudicators/notehead_precision.py
OMR_METER_SLOT                     absent   ON       YES     gather.py, time_signature_locator.py
OMR_OWNER_LEDGER_WINS              absent   ON       no      adjudicators/ownership.py
OMR_REST_OWN_STROKE                absent   ON       no      adjudicators/head_rest_shape.py
OMR_STEMS_FROM_STROKES             absent   OFF      YES     adjudicators/ownership.py, adjudicators/rhythm.py, gather.py
OMR_STEM_BEAM_END                  absent   ON       no      adjudicators/stem_value.py
OMR_STEM_END_HEAD_INK              absent   ON       YES     adjudicators/notehead_precision.py, adjudicators/rhythm.py, export.py
OMR_STEM_TIP_TRUE_EDGE             absent   ON       YES     gather.py, stroke_map.py
OMR_STROKE_MAP                     absent   ON       YES     accidental_family.py, adjudicators/rhythm.py, adjudicators/stroke_owner.py
OMR_WHOLE_REST_HANGS               absent   ON       no      adjudicators/family_precision.py, adjudicators/notehead_precision.py, adjudicators/stroke_owner.py
OMR_WHOLE_REST_PLAIN               absent   ON       no      export.py
(23 flags changed default; 89 flags seen by the scan at BASE, 112 at TAG)

== every OMR_* NAME in non-test source: added since BASE (28) / gone (0)  [catches value flags the scan misses]
  + OMR_ARC_CLAIM                      GATHER staged/adjudicators/stroke_owner.py
      not seen by the default scan; read as: (no environ line; named only)
      docs/flags-2026-09.md default column: **default ON, Sean 2026-10-29** ("Yes"; unset = ON, an explicit `0/false/no/off` disables; needs `OMR_SYSTEM_ARCS`, `OMR_STROKE_MAP`; tiles 10/10 arcs
  + OMR_ARC_KIND_FROM_ENDS             staged/adjudicators/ownership.py
      not seen by the default scan; read as: (no environ line; named only)
      docs/flags-2026-09.md default column: **default OFF** (allow-list; waits for ROADMAP 2.223)
  + OMR_BARLINE_SYSTEM_COLUMNS         GATHER measure_extractor.py
      not seen by the default scan; read as: raw = os.environ.get("OMR_BARLINE_SYSTEM_COLUMNS")
      docs/flags-2026-09.md default column: **default ON, Sean 2026-10-29** (roadmap 2.221 m2; unset = ON, an explicit `0/false/no/off` disables)
  + OMR_SLUR_FROM_ANCHORS              staged/arc_claim.py
      not seen by the default scan; read as: (no environ line; named only)
      docs/flags-2026-09.md default column: **default OFF** (allow-list; waits for ROADMAP 2.223)
  + OMR_STROKE_OWNER                   staged/adjudicate.py
      not seen by the default scan; read as: (no environ line; named only)
      docs/flags-2026-09.md default column: **`1` ON since 2026-10-26** (ROADMAP 2.205, step 5 of the shared ink map, Sean "1. Yes"; explicit `0`/`false`/`no`/`off` disables; meaningful only wit

blind spot: a flag read through a path the scan cannot parse and already present at BASE is NOT listed even if its default moved.


-- the two runs, from their logs and records
wall (summary.txt)   BASE ref origin/main commit a2eae688030feebf177a40e2b0f2404dafd61f28 through infer start 2026-10-23T05:21:17Z  | done 2026-10-23T10:13:12Z
                     TAG  ref origin/main commit 12325ce2991f7bc1f930fb4b569a754e0cf1ca0c through infer start 2026-10-30T06:10:24Z  | done 2026-10-30T13:11:26Z
== brahms1-breitkopf
  wall min  BASE 224  TAG 352   (exit codes 0 / 0)
  ── EVALUATE: 53051 fired, 606324 skipped
  -> ── EVALUATE: 53473 fired, 604703 skipped
  ── INFER: 291 inferred, 0 skipped  ⚠️ every one is LABELLED and supersedes a recorded narrowing
  -> ── INFER: 259 inferred, 0 skipped  ⚠️ every one is LABELLED and supersedes a recorded narrowing
  LOG warnings/errors (lines matching warn|error|traceback|exception|failed|warning sign): BASE 3, TAG 3
  TAG: ⚠️ checked_nothing (never two independent signals -- corroborated NOTHING, however busy it looks): ['clef_across_systems', 'instrument_across_systems', 'key_signature_across_systems', 'measure_count_a
  TAG: ⚠️ DISAGREEMENTS: 20 (each implicates its WHOLE group, not its dissenter)
  TAG: ── INFER: 259 inferred, 0 skipped  ⚠️ every one is LABELLED and supersedes a recorded narrowing
== brahms1-breitkopf
brahms1-breitkopf-mvt1-whole-20261022-night.record.json
  8833 MB  commit a2eae688030feebf177a40e2b0f2404dafd61f28 dirty=False  weight routing routed/scanned
  rows {'observations': 745802, 'abstentions': 123413, 'verdicts': 455512}
  settings {"args": {"against": null, "conf": 0.25, "dpi": 600, "imgsz": null, "ink_rows": false, "movements": null, "no_roster": false, "no_weight_routing": false, "ocr": true, "pages": "0-26", "pdf": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", "route_weights": false, "sheet": null, "surya": true, "through": "infer", "weights": "auto", "work_id": null}, "env_overrides": {"OMR_SURYA_KEEP_ALIVE": "0"}}
brahms1-breitkopf-mvt1-whole-20261029-night.record.json
  19647 MB  commit 12325ce2991f7bc1f930fb4b569a754e0cf1ca0c dirty=False  weight routing routed/scanned
  rows {'observations': 1106988, 'abstentions': 127836, 'verdicts': 464229}
  settings {"args": {"against": null, "conf": 0.25, "dpi": 600, "imgsz": null, "ink_rows": false, "movements": null, "no_roster": false, "no_weight_routing": false, "ocr": true, "pages": "0-26", "pdf": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", "route_weights": false, "sheet": null, "surya": true, "through": "infer", "weights": "auto", "work_id": null}, "env_overrides": {"OMR_SURYA_KEEP_ALIVE": "0"}}
SETTINGS/ENV difference first -> last record (IDENTICAL):

-- record size and what grew (record_growth.py; rows by array and quantity, ~bytes = len(json) of each row)
== brahms1-breitkopf
file size MB: BASE 8833  TAG 19647   (x2.22)
  observations  rows   745802 ->  1106988   ~MB    257 ->    455
  abstentions   rows   123413 ->   127836   ~MB     40 ->     42
  verdicts      rows   455512 ->   464229   ~MB   9103 ->  20532
biggest growth by ~bytes (array / quantity: rows, ~MB):
  verdicts      duration                           rows    35496 ->    35571   ~MB  970.0 -> 4031.1
  verdicts      voices                             rows     6685 ->     6699   ~MB 4847.8 -> 7304.8
  verdicts      stem_value                         rows    24375 ->    24408   ~MB  586.8 -> 2448.9
  verdicts      dot_role                           rows    10113 ->    10115   ~MB   79.8 -> 1075.9
  verdicts      tie_pair                           rows    14814 ->    14821   ~MB   31.4 ->  923.2
  verdicts      arc_kind                           rows    14814 ->    14821   ~MB  310.7 ->  970.5
  verdicts      notehead_is_not_a_notehead         rows    24375 ->    24408   ~MB   70.4 ->  474.5
  verdicts      dynamic_anchor                     rows      691 ->      691   ~MB   38.8 ->  260.3
  verdicts      accidental_owner                   rows     6544 ->     7867   ~MB   30.9 ->  244.7
  verdicts      wedge_anchor                       rows      278 ->      278   ~MB  466.7 ->  662.9
  verdicts      meter                              rows       53 ->       53   ~MB  289.5 ->  427.5
  observations  stroke                             rows        0 ->   216010   ~MB    0.0 ->  126.2
  verdicts      rest_is_not_a_rest                 rows     8870 ->     8870   ~MB   16.4 ->  108.9
  verdicts      stroke_owner                       rows        0 ->     6699   ~MB    0.0 ->   81.5

What the logs and records do NOT carry, so it is not estimated here: per-stage wall time (the run prints none), detector or OCR call counts, 
peak memory. Proxies that ARE recorded: pages, record size, row counts (above), EVALUATE fired/skipped and INFER inferred/skipped (logs_diff).

== Apples to oranges (read before believing any delta above)
1. The TAG tree is NOT the BASE tree plus one change: git log --oneline a2eae6880..12325ce29: 395 commits (76 merges, 319 non-merge). That is the point of the night, but it means no delta below has ONE cause; causes come from `readout diff` per family and the lanes' own reports.
2. Flags that act in GATHER and did not exist (or were off) at BASE -- the records differ in what was SEEN, not only decided: OMR_ACCIDENTAL_FAMILY, OMR_CLAIM_BRACKETS_FIRST, OMR_CLAIM_WORDS_FIRST, OMR_CLEF_SLOT_CLAIM, OMR_FILL_FROM_STROKES, OMR_KEY_PER_SYSTEM, OMR_KEY_SIGNATURE_CLAIM, OMR_METER_SLOT, OMR_STEMS_FROM_STROKES, OMR_STEM_END_HEAD_INK, OMR_STEM_TIP_TRUE_EDGE, OMR_STROKE_MAP; read-but-unscanned: OMR_ARC_CLAIM, OMR_BARLINE_SYSTEM_COLUMNS
3. Flags absent at BASE (the baseline lacked the mechanism entirely): 23 (OMR_ACCIDENTAL_FAMILY, OMR_BEAMS_FROM_STROKES, OMR_BEAM_OWN_EXTENT, OMR_CLAIM_BRACKETS_FIRST, OMR_CLAIM_WORDS_FIRST, OMR_CLEF_SLOT_CLAIM, OMR_ERASER_FIX, OMR_FILL_FROM_STROKES, OMR_FOUND_WHOLE_REST, OMR_HEAD_TRIM_LINE_ONLY, OMR_HEAD_TRIM_LINE_ONLY_V2, OMR_KEY_PER_SYSTEM, OMR_KEY_SIGNATURE_CLAIM, OMR_METER_SLOT, OMR_OWNER_LEDGER_WINS, OMR_REST_OWN_STROKE, OMR_STEMS_FROM_STROKES, OMR_STEM_BEAM_END, OMR_STEM_END_HEAD_INK, OMR_STEM_TIP_TRUE_EDGE, OMR_STROKE_MAP, OMR_WHOLE_REST_HANGS, OMR_WHOLE_REST_PLAIN)
4. BASE as run (tree a2eae6880) vs the same BASE record re-exported by this tree (05f0b9eb9): they DIFFER in brahms1.bars_held_out_sum, brahms1.bars_add_up_control, brahms1.unread_bars -- exporter/acceptance changes move the headline with NO new gather; the middle column in the headline is the fair BASE
5. Judged tiles: BASE and TAG both scored NOW by the same scorer on the same index (judged_compare.py), so the d51e3967c scorer change (written values incl. blue) cannot show up as a move. The numbers in the 20261022-night README (159/32/6 Litolff, 142/21/5 Brahms) were the old scorer and are NOT comparable with the ones above.
6. Ranking and 'what changed in the file': both arms exported by THIS tree's exporter from the records' SAVED verdicts (no re-adjudication), so an exporter change between the commits is in neither delta. The ranking's page sample is the frozen one (benchmarks/lane-report/sample.json); 'whole movement' lines use every page holding staves. The '10-29 rank' column came from a DIFFERENT gather (main 1b47854a4, sample pages only) and is quoted, not recomputed.
7. Settings/env: the provenance settings/env difference first -> last record (IDENTICAL): Provenance records only explicit env overrides (OMR_SURYA_KEEP_ALIVE) and CLI args, NOT the whole shell environment: an inherited OMR_* variable at BASE cannot be ruled out. The TAG process's environment snapshot: not captured (the gather had already exited)
8. Detector weights: 20261022-night -> deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt; 20261029-night -> deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt; same file name. that file's mtime is 2026-09-04 (before both nights) -> unchanged on disk
9. Walls are single runs on a shared box: the overnight box load (other lanes, the web app, other agents) is not recorded, so a wall-minute delta of a few minutes is noise.
10. Machine-local inputs not versioned here: the PDFs under library/ and omr-weights/ (same paths both nights); page range comes from each record's provenance args.pages (SETTINGS diff above).
