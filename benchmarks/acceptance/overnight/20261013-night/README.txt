compare 20261013-night vs 20261011-night, tree ca46eae46c630707ae597b9db8a14c9cdb5fba75 start 2026-10-14T11:07:26Z
beethoven5-litolff: readout diff exit 1
beethoven5-litolff: export exit 1
brahms1-breitkopf: readout diff exit 1
brahms1-breitkopf: export exit 1
acceptance exit 2 (see /Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/overnight-20261013-night/compare/acceptance.log)
done 2026-10-14T11:27:05Z
force exit 0
NOTE (agent): the compare script's own README lines above are verbatim. Its `readout diff exit 1` matches 20261011-night (diff tool exits 1 when records differ). NEW this night: `export exit 1` for both movements = the LilyPond writer raised staged.export.Unbalanced (see SUMMARY.md); the MusicXML was written, no .ly/.pdf. `acceptance exit 2` = refused to write current.json on a dirty tree (acceptance's own output files), as on 20261011-night; re-run with --force (force exit 0, shown above) writing current.json. all-stages-vs-20261011-night.txt was produced from that current.json vs origin/main 20261011-night/current.json with the compare script's own walker; the script's all-stages-vs-20260930 output (no current.json at the time) is not kept.
