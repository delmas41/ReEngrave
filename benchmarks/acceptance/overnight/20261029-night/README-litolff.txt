compare_20261029 20261029-night vs 20261022-night docs [beethoven5-litolff] tree 08f3a831b31809c650e7d7c4b437ce2ef191eaa3 start 2026-10-30T07:29:22Z

== Manager summary (machine-assembled from the files named; rule-derived flags are CANDIDATES for a human reading)
Acceptance (20261022-night as run | 20261022-night re-exported by THIS tree | 20261029-night):
  Litolff notes reaching file 8887/11797 -> 8898/11868 (0.753 -> 0.750); held-out bars 0 -> 0; red bars 507 -> 412; bars add up 4946 -> 5170; unread bars 418 -> 280; parts named 12/12 -> 12/12
      (like with like = the middle column; the BASE as it was run on its own night differs from its re-export by: addup 4835->4946, unread 529->418)
      noteheads logged changed 11797 -> 11868 (GATHER saw a different number of heads)
Sean's judged tiles, SAME current index, today's scorer on BOTH records (right/wrong/narrowed):
  Litolff 164/42/6 -> 167/34/6 ; right->wrong 3, right->gone 6, wrong->right 12, unwritten->wrong 2, unwritten->right 0
What changed in the exported file (gained/lost by kind; place-matched, lane_report.diff_arms; BASE and TAG both exported by THIS tree from SAVED verdicts):
  Litolff whole movement:
     notes +451 -440 | rests +323 -181 | accidentals +28 -13 ~44 | flags +39 -44 | beams +62 -50 ~42 | ties +32 -17 ~1 | slurs +1 -33 | articulations +12 -2 | fermatas +6 -1 | tuplet notes -2 | note values ~68 | pitches ~203 | blue marks +417 -2
     paired 10681 hosts (10848, 10986) red 507 412 blue 2369 2563 not written 4539 4503
  Litolff frozen sample pages:
     notes +211 -175 | rests +167 -96 | accidentals +13 -7 ~23 | flags +18 -17 | beams +33 -23 ~25 | ties +17 -2 | slurs +1 -3 | articulations +1 -1 | fermatas +4 | note values ~48 | pitches ~87 | blue marks +247 -86 | dynamics +178 -184 | wedge
     paired 5614 hosts (5684, 5781) red 265 202 blue 1201 1383 not written 2249 2199
First two stages (GATHER + ADJUDICATE), readout diff per family (a diff exits 1 when the records differ -- that is its normal 'differences found', not a failure):
  Litolff: 44529 differences in all; provenance differences: [["code", "commit", "a2eae688030feebf177a40e2b0f2404dafd61f28", "12325ce2991f7bc1f930fb4b569a754e0cf1ca0c"]]
     (other classes)    gathered 15223 -> 15168, matched 15073, only-BASE 150, only-TAG 102, pairs with a changed answer 0
     accidental         gathered 1508 -> 1511, matched 1503, only-BASE 5, only-TAG 9, pairs with a changed answer 1503
     articulation       gathered 18 -> 21, matched 18, only-BASE 0, only-TAG 2, pairs with a changed answer 18
     clef               gathered 513 -> 505, matched 508, only-BASE 5, only-TAG 0, pairs with a changed answer 508
     dot                gathered 618 -> 619, matched 613, only-BASE 5, only-TAG 5, pairs with a changed answer 613
     dynamic            gathered 1590 -> 1602, matched 1572, only-BASE 18, only-TAG 28, pairs with a changed answer 1572
     fermata            gathered 178 -> 178, matched 178, only-BASE 0, only-TAG 0, pairs with a changed answer 178
     key                gathered 542 -> 540, matched 540, only-BASE 2, only-TAG 0, pairs with a changed answer 540
     note               gathered 11797 -> 11868, matched 11756, only-BASE 41, only-TAG 114, pairs with a changed answer 11756
     ornament           gathered 3 -> 3, matched 3, only-BASE 0, only-TAG 0, pairs with a changed answer 3
     rest               gathered 2969 -> 2980, matched 2957, only-BASE 12, only-TAG 16, pairs with a changed answer 2957
     slur               gathered 1225 -> 1225, matched 1225, only-BASE 0, only-TAG 0, pairs with a changed answer 1225
     tie                gathered 1419 -> 1416, matched 1412, only-BASE 7, only-TAG 3, pairs with a changed answer 1412
     time               gathered 82 -> 84, matched 80, only-BASE 2, only-TAG 4, pairs with a changed answer 80
     tuplet             gathered 13 -> 12, matched 12, only-BASE 1, only-TAG 0, pairs with a changed answer 12
     wedge              gathered 0 -> 1, matched 0, only-BASE 0, only-TAG 0, pairs with a changed answer 0
     matched 1:1, nothing changed: 
Abstention reasons that moved (old -> new; logs_diff.txt has all; decided verdicts that moved are listed there too):
  beethoven5-litolff
   accidental_owner                 is_a_key_signature_marker                   123      506     +383
   accidental_owner                 no_candidate                                372      503     +131
   rest_is_not_a_rest               whole_rest_hangs                              0       97      +97
   duration                         beams_ambiguous                              98      175      +77
   stem_value                       not_a_member                               1213     1288      +75
   unison_voices                    not_a_unison                              11251    11321      +70
   stem_value                       no_stem                                    2307     2259      -48
   head_stem                        no_stem                                    2307     2259      -48
   notehead_is_not_a_notehead       stem_end_ink_only                             0       46      +46
   stem_direction                   no_stem                                    1843     1802      -41
   duration                         beam_discounted_uncertain                   423      382      -41
   voices                           nothing_to_split                            174      140      -34
   unread_mark                      no_ink_component_rows                      5377     5343      -34
   stem_value                       stem_levels_unread                          109      143      +34
   DECIDED verdicts that moved (quantity: base -> tag): accidental_is_not_an_accidental 1508 -> 1511; accidental_owner 570 -> 578; arc_is_not_an_arc 2644 -> 2641; arc_kind 2637 -> 2634; arc_owner 2644 -> 2641; arpeggiato_is_not_an_arpeggiato 1897 -> 1900; articulation_is_not_an_articulation 18 -> 21; a
   ABSTENTIONS 44059 -> 44655; 86 reasons moved, 29 unchanged
The 2.229 product ranking on the new records (fix-actions per page, biggest first; the '10-29 rank' column is FINDINGS.md quoted, not recomputed):
  litolff ranking, fix-actions per page over 9 loaded pages, biggest first by TAG (BASE=base TAG=tag)
  kind                             BASE/pg    TAG/pg    delta   10-29 rank   (totals BASE -> TAG)
  ties and slurs not written          84.1      82.8     -1.3         83.0   757 -> 745
  pitched heads not written           34.0      34.4     +0.4         34.3   306 -> 310
  red bars                            29.4      22.4     -7.0         27.3   265 -> 202
  unread empty bars                   24.8      14.3    -10.4         31.0   223 -> 129
  dots decided, never placed           8.2       8.2     +0.0          8.1   74 -> 74
  blue notes (check load)            124.1     140.9    +16.8        138.4   1117 -> 1268
  blue rests (check load)              3.3       4.4     +1.1          3.8   30 -> 40
Files (machine-local, /Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/overnight-20261029-night/compare):
  beethoven5-litolff musicxml  4.2 MB
  beethoven5-litolff ly  0.7 MB
  beethoven5-litolff pdf  5.0 MB

Surprising / worse (rule-derived candidates; a human reads each against the print):
  - Litolff: 3 judged answers went RIGHT -> WRONG (must be 0): 2.162-review tile 5; 2.73-review tile 5; 2.83-fix-review tile tile_05
  - Litolff: 6 judged answers went RIGHT -> gone (narrowed/abstained/not found)
  - Litolff: 2 judged answers went unwritten -> WRONG
  - Litolff (other classes): GATHER boxes only-BASE 150 / only-TAG 102
  - Litolff accidental: GATHER boxes only-BASE 5 / only-TAG 9
  - Litolff articulation: GATHER boxes only-BASE 0 / only-TAG 2
  - Litolff clef: GATHER boxes only-BASE 5 / only-TAG 0
  - Litolff dot: GATHER boxes only-BASE 5 / only-TAG 5
  - Litolff dynamic: GATHER boxes only-BASE 18 / only-TAG 28
  - Litolff key: GATHER boxes only-BASE 2 / only-TAG 0
  - Litolff note: GATHER boxes only-BASE 41 / only-TAG 114
  - Litolff rest: GATHER boxes only-BASE 12 / only-TAG 16
  - Litolff tie: GATHER boxes only-BASE 7 / only-TAG 3
  - Litolff time: GATHER boxes only-BASE 2 / only-TAG 4
  - Litolff tuplet: GATHER boxes only-BASE 1 / only-TAG 0
  - abstention reason grew by +383: accidental_owner is_a_key_signature_marker 123 506 +383

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
                     TAG  ref origin/main commit 12325ce2991f7bc1f930fb4b569a754e0cf1ca0c through infer start 2026-10-30T06:10:24Z  | NOT DONE
== beethoven5-litolff
  wall min  BASE 67  TAG 68   (exit codes 0 / 0)
  ── EVALUATE: 18627 fired, 224181 skipped
  -> ── EVALUATE: 18735 fired, 224378 skipped
  ── INFER: 276 inferred, 62 skipped  ⚠️ every one is LABELLED and supersedes a recorded narrowing
  -> ── INFER: 271 inferred, 64 skipped  ⚠️ every one is LABELLED and supersedes a recorded narrowing
  LOG warnings/errors (lines matching warn|error|traceback|exception|failed|warning sign): BASE 3, TAG 3
  TAG: ⚠️ checked_nothing (never two independent signals -- corroborated NOTHING, however busy it looks): ['instrument_across_systems', 'key_signature_across_systems', 'measure_count_across_staves']
  TAG: ⚠️ DISAGREEMENTS: 3 (each implicates its WHOLE group, not its dissenter)
  TAG: ── INFER: 271 inferred, 64 skipped  ⚠️ every one is LABELLED and supersedes a recorded narrowing
== beethoven5-litolff
beethoven5-litolff-mvt1-whole-20261022-night.record.json
  1269 MB  commit a2eae688030feebf177a40e2b0f2404dafd61f28 dirty=False  weight routing routed/scanned
  rows {'observations': 296663, 'abstentions': 68443, 'verdicts': 189929}
  settings {"args": {"against": null, "conf": 0.25, "dpi": 600, "imgsz": null, "ink_rows": false, "movements": null, "no_roster": false, "no_weight_routing": false, "ocr": true, "pages": "1-16", "pdf": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", "route_weights": false, "sheet": null, "surya": true, "through": "infer", "weights": "auto", "work_id": null}, "env_overrides": {"OMR_SURYA_KEEP_ALIVE": "0"}}
beethoven5-litolff-mvt1-whole-20261029-night.record.json
  2937 MB  commit 12325ce2991f7bc1f930fb4b569a754e0cf1ca0c dirty=False  weight routing routed/scanned
  rows {'observations': 451499, 'abstentions': 69544, 'verdicts': 196346}
  settings {"args": {"against": null, "conf": 0.25, "dpi": 600, "imgsz": null, "ink_rows": false, "movements": null, "no_roster": false, "no_weight_routing": false, "ocr": true, "pages": "1-16", "pdf": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", "route_weights": false, "sheet": null, "surya": true, "through": "infer", "weights": "auto", "work_id": null}, "env_overrides": {"OMR_SURYA_KEEP_ALIVE": "0"}}
SETTINGS/ENV difference first -> last record (IDENTICAL):

-- record size and what grew (record_growth.py; rows by array and quantity, ~bytes = len(json) of each row)
== beethoven5-litolff
file size MB: BASE 1269  TAG 2937   (x2.31)
  observations  rows   296663 ->   451499   ~MB    102 ->    181
  abstentions   rows    68443 ->    69544   ~MB     22 ->     22
  verdicts      rows   189929 ->   196346   ~MB   1205 ->   2924
biggest growth by ~bytes (array / quantity: rows, ~MB):
  verdicts      duration                           rows    16342 ->    16569   ~MB  184.9 ->  556.3
  verdicts      voices                             rows     5377 ->     5343   ~MB  444.0 ->  722.6
  verdicts      stem_value                         rows    11797 ->    11868   ~MB  123.6 ->  370.0
  verdicts      arc_kind                           rows     2644 ->     2641   ~MB    9.8 ->  183.3
  verdicts      tie_pair                           rows     2644 ->     2641   ~MB    5.3 ->  171.4
  verdicts      notehead_is_not_a_notehead         rows    11797 ->    11868   ~MB   28.3 ->  176.4
  verdicts      dynamic_anchor                     rows      331 ->      331   ~MB   10.1 ->   89.6
  verdicts      rest_is_not_a_rest                 rows     2969 ->     2980   ~MB    4.1 ->   66.7
  observations  stroke                             rows        0 ->    90418   ~MB    0.0 ->   53.1
  verdicts      stroke_owner                       rows        0 ->     5343   ~MB    0.0 ->   40.0
  verdicts      meter                              rows       31 ->       31   ~MB   66.0 ->   98.1
  verdicts      dot_role                           rows      618 ->      619   ~MB    2.9 ->   31.7
  verdicts      accidental_owner                   rows     1508 ->     2039   ~MB    4.1 ->   30.7
  verdicts      unison_voices                      rows    11797 ->    11868   ~MB   11.3 ->   31.6

What the logs and records do NOT carry, so it is not estimated here: per-stage wall time (the run prints none), detector or OCR call counts, 
peak memory. Proxies that ARE recorded: pages, record size, row counts (above), EVALUATE fired/skipped and INFER inferred/skipped (logs_diff).

== Apples to oranges (read before believing any delta above)
1. The TAG tree is NOT the BASE tree plus one change: git log --oneline a2eae6880..12325ce29: 395 commits (76 merges, 319 non-merge). That is the point of the night, but it means no delta below has ONE cause; causes come from `readout diff` per family and the lanes' own reports.
2. Flags that act in GATHER and did not exist (or were off) at BASE -- the records differ in what was SEEN, not only decided: OMR_ACCIDENTAL_FAMILY, OMR_CLAIM_BRACKETS_FIRST, OMR_CLAIM_WORDS_FIRST, OMR_CLEF_SLOT_CLAIM, OMR_FILL_FROM_STROKES, OMR_KEY_PER_SYSTEM, OMR_KEY_SIGNATURE_CLAIM, OMR_METER_SLOT, OMR_STEMS_FROM_STROKES, OMR_STEM_END_HEAD_INK, OMR_STEM_TIP_TRUE_EDGE, OMR_STROKE_MAP; read-but-unscanned: OMR_ARC_CLAIM, OMR_BARLINE_SYSTEM_COLUMNS
3. Flags absent at BASE (the baseline lacked the mechanism entirely): 23 (OMR_ACCIDENTAL_FAMILY, OMR_BEAMS_FROM_STROKES, OMR_BEAM_OWN_EXTENT, OMR_CLAIM_BRACKETS_FIRST, OMR_CLAIM_WORDS_FIRST, OMR_CLEF_SLOT_CLAIM, OMR_ERASER_FIX, OMR_FILL_FROM_STROKES, OMR_FOUND_WHOLE_REST, OMR_HEAD_TRIM_LINE_ONLY, OMR_HEAD_TRIM_LINE_ONLY_V2, OMR_KEY_PER_SYSTEM, OMR_KEY_SIGNATURE_CLAIM, OMR_METER_SLOT, OMR_OWNER_LEDGER_WINS, OMR_REST_OWN_STROKE, OMR_STEMS_FROM_STROKES, OMR_STEM_BEAM_END, OMR_STEM_END_HEAD_INK, OMR_STEM_TIP_TRUE_EDGE, OMR_STROKE_MAP, OMR_WHOLE_REST_HANGS, OMR_WHOLE_REST_PLAIN)
4. BASE as run (tree a2eae6880) vs the same BASE record re-exported by this tree (08f3a831b): they DIFFER in beethoven5.bars_held_out_sum, beethoven5.bars_add_up_control, beethoven5.unread_bars -- exporter/acceptance changes move the headline with NO new gather; the middle column in the headline is the fair BASE
5. Judged tiles: BASE and TAG both scored NOW by the same scorer on the same index (judged_compare.py), so the d51e3967c scorer change (written values incl. blue) cannot show up as a move. The numbers in the 20261022-night README (159/32/6 Litolff, 142/21/5 Brahms) were the old scorer and are NOT comparable with the ones above.
6. Ranking and 'what changed in the file': both arms exported by THIS tree's exporter from the records' SAVED verdicts (no re-adjudication), so an exporter change between the commits is in neither delta. The ranking's page sample is the frozen one (benchmarks/lane-report/sample.json); 'whole movement' lines use every page holding staves. The '10-29 rank' column came from a DIFFERENT gather (main 1b47854a4, sample pages only) and is quoted, not recomputed.
7. Settings/env: the provenance settings/env difference first -> last record (IDENTICAL): Provenance records only explicit env overrides (OMR_SURYA_KEEP_ALIVE) and CLI args, NOT the whole shell environment: an inherited OMR_* variable at BASE cannot be ruled out. The TAG process's environment snapshot: OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
OMR_SURYA_KEEP_ALIVE=0
8. Detector weights: 20261022-night -> deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt; 20261029-night -> deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt; same file name. that file's mtime is 2026-09-04 (before both nights) -> unchanged on disk
9. Walls are single runs on a shared box: the overnight box load (other lanes, the web app, other agents) is not recorded, so a wall-minute delta of a few minutes is noise.
10. Machine-local inputs not versioned here: the PDFs under library/ and omr-weights/ (same paths both nights); page range comes from each record's provenance args.pages (SETTINGS diff above).

== Lane notes (hand-written after reading the above; Litolff only, Brahms pending)
- Headline (like with like, BASE re-exported by this tree): red bars 507 -> 412, bars add up 4946 -> 5170, unread bars 418 -> 280, notes reaching file 8887 -> 8898 of 11797 -> 11868 (fraction 0.753 -> 0.750: GATHER saw 71 more heads, 114 only-TAG vs 41 only-BASE note boxes). As run on its own night the BASE said 4835 / 529; the exporter moved those two without any new gather (4835 -> 4946, 529 -> 418).
- Judged (today's scorer, both records): 164/42/6 -> 167/34/6; wrong->right 12, but RIGHT->WRONG 3 (must be 0), all three the same new refusal `stacked_head_duplicate` (notehead_is_not_a_notehead stem_end_ink_only / stacked head): 2.162-review tile 5 (glyph/3/1/2/15/0), 2.73-review tile 5 (glyph/3/0/4/3/12), 2.83-fix-review tile_05 (glyph/4/0/7/7/10). Also right->gone 6 and unwritten->wrong 2. These need a crop look before the stem-end / stacked-head work is called safe.
- readout diff "pairs with a changed answer" equals "matched" in nearly every family: that is NOT 44k real changes. Each pair gained NEW GATHER rows (glyph_strokes 37450, mark_group 10805, head_ink 10253...). Real answer changes are the ADJUDICATE lines (accidental_owner 596, duration 265, rest_is_not_a_rest 192).
- Record growth x2.31 (1269 -> 2937 MB): rows barely moved (verdicts 189929 -> 196346); the weight is per-row payload on verdicts (duration ~185 -> 556 MB, voices 444 -> 723, stem_value 124 -> 370, arc_kind 10 -> 183, tie_pair 5 -> 171, notehead_is_not_a_notehead 28 -> 176) plus 90418 new `stroke` observations and 5343 `stroke_owner` verdicts (the shared stroke map, 2.195/2.205). Whole-movement record load time and memory scale with it (Brahms will be ~2x the 8.8 GB).
- Abstentions: is_a_key_signature_marker 123 -> 506 (+383) is the biggest mover (key-signature area claim 2.183 claims accidental-looking ink before owners); new whole_rest_hangs 97, stem_end_ink_only 46. Not checked against the print.
- Ranking: ties/slurs, pitched heads and dots flat; red bars and unread empty bars fell (-7.0 and -10.4 per page); blue notes rose 124 -> 141 per page (check load up, +16.8).
- Wall 67 -> 68 min. Acceptance for TAG was written with --force on a tree the compare itself had dirtied (recorded dirty=true); BASE re-export likewise.
