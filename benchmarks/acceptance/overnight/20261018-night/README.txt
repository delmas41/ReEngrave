compare 20261018-night vs 20261016-night, tree 2bb43b85a2070a5e163172109c3bb4973497c7b4 start 2026-10-19T12:48:41Z
beethoven5-litolff: readout diff exit 1
brahms1-breitkopf: readout diff exit 1
acceptance exit 2 (see /Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/overnight-20261018-night/compare/acceptance.log)
done 2026-10-19T13:08:09Z

== Manager summary 2026-10-19 (main 2bb43b85: first whole-movement run with 2.158/2.159/2.161/2.164/2.166/2.162/2.169/2.168 ON)
Acceptance (vs 20261016-night):
  Litolff notes reaching file 6731 -> 6626 / 11399; bars held out 584 -> 624; unread bars 699 -> 664
  Brahms  notes reaching file 12152 -> 11991 / 24260; bars held out 844 -> 915; unread bars 393 -> 393
Sean's judged tiles (judged score, right/wrong/narrowed):
  Litolff 130/30/33 -> 156/30/7   (narrowed->right 26, right->wrong 2, wrong->right 2)
  Brahms  120/20/16 -> 126/22/8   (narrowed->right 9, right->wrong 3, wrong->right 1, right->narrowed 1)
  All 5 right->wrong are `bar_disagrees_with_decided` (2.162 block: the bar no longer fixes a misread decided note).
EXPORT GAP: 2.168 marked 60 Litolff / 114 Brahms notes blue in the RECORD, but only 2 / 8 reach the file
  (coverage guessed.by_rule.bar_disagrees_with_decided). The rest sit in bars HELD OUT because the bar no longer
  adds up -- also the held-out rise (+40 / +71 bars) and the reach drop. 2.168's lane measured the record, not the file.
(The compare was run twice: the first run's summary files were deleted by a manager command error and regenerated.)
