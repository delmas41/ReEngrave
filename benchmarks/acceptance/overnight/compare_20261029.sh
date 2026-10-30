#!/bin/bash
# Compare two overnight re-gathers: WHAT WE GET (the output) and HOW WE GET IT (the process).
# Sean 2026-10-29: "I want comparison of output as well as test process. What we get and how we get it."
#
#   TAG=20261029-night BASE=20261022-night bash benchmarks/acceptance/overnight/compare_20261029.sh
#   DOCS=beethoven5-litolff ...   one plate while the other is still gathering (NEVER load the 8.8 GB Brahms
#                                 record while its gather runs: the box crashed twice that way). Small CPU: one
#                                 process at a time. OMR_SURYA_KEEP_ALIVE=0.
#
# Reuses compare_20261009.sh for: readout diff per movement (first two stages), the coloured count page, MusicXML +
# LilyPond + PDF per movement, text counts, acceptance on the new record, regather_report. Adds what that did not do:
#   * the BASE record re-exported/re-scored by THIS tree (like with like -- the acceptance code and the scorer move),
#   * Sean's judged tiles on both records with one scorer and one index, right->wrong / right->gone / wrong->right,
#   * "what changed in the exported file" by kind, place-matched, on the whole movement and on the frozen sample,
#   * the abstention-reason diff and the wall/warning/record facts from the logs (logs_diff.py, prov_peek.py),
#   * the 2.229 product ranking on both records next to the 10-29 ranking,
#   * the process diff between the two commits (process_diff.py) and the apples-to-oranges list (apples.py).
# Large files stay under $R/overnight-$TAG/compare; the small text goes to $SUM and README.txt is assembled by
# readme_20261029.py from those files (no number is typed by hand).
#
# `readout diff` exits 1 when the records DIFFER (0 only when identical): that is its "differences found", not a
# failure -- the 20261022-night run logged it as a failure. compare_20261009.sh now treats only >1 as one.
set -uo pipefail
TAG=${TAG:-20261029-night}
BASE=${BASE:-20261022-night}
DOCS=${DOCS:-"beethoven5-litolff brahms1-breitkopf"}
M=/Users/seanjohnson/Desktop/ReEngrave
R=$M/library/_shared-records
HERE=$(cd "$(dirname "$0")" && pwd)
WT=${WT:-$M/.claude/worktrees/overnight-$TAG}     # the checkout the compare runs in (the tree under test)
OUT=${OUT:-$R/overnight-$TAG/compare}      # a test run sets OUT elsewhere so it cannot overwrite a night's compare dir
export COMPARE_OUT=$OUT
SUM=${SUM:-$HERE/$TAG}
mkdir -p "$OUT/rank" "$SUM"
export OMR_SURYA_KEEP_ALIVE=0 OMRNED_PYTHON=$M/.venv-omrned/bin/python
LOGF=$SUM/run-log.txt
echo "compare_20261029 $TAG vs $BASE docs [$DOCS] tree $(cd "$WT" && git rev-parse HEAD) start $(date -u +%FT%TZ)" > "$LOGF"

# 0. refuse a record a gather is still writing (a control that can fail)
READY=""
for doc in $DOCS; do
  if grep -q "^$doc pages .* exit " "$R/overnight-$TAG/summary.txt" 2>/dev/null && [ -s "$R/$doc-mvt1-whole-$TAG.record.json" ]; then
    READY="$READY $doc"
  else
    echo "$doc: gather for $TAG not finished (no exit line in summary.txt) -- SKIPPED" | tee -a "$LOGF"
  fi
  [ -s "$R/$doc-mvt1-whole-$BASE.record.json" ] || { echo "$doc: no BASE record $BASE -- SKIPPED" | tee -a "$LOGF"; READY=${READY% $doc}; }
done
READY=${READY# }
[ -n "$READY" ] || { echo "nothing to compare" | tee -a "$LOGF"; exit 3; }
echo "comparing: $READY" >> "$LOGF"
cd "$WT" || exit 2
# the checkout needs the machine-local assets (docs/running.md section 1)
for l in library omr-weights .venv-surya .venv-omrned; do [ -e "$l" ] || ln -sfn "$M/$l" "$l"; done
mkdir -p tools/omr/training/data && { [ -e tools/omr/training/data/weights ] || ln -sfn "$M/tools/omr/training/data/weights" tools/omr/training/data/weights; }
short() { case $1 in beethoven5-litolff) echo litolff ;; *) echo brahms ;; esac; }

# snapshot the environment of a gather that is still alive (the record keeps only explicit overrides)
ps eww -p "$(pgrep -f 'tools.omr.staged.*--through' | head -1)" 2>/dev/null | tr ' ' '\n' | grep -E '^(OMR_|OMRNED|PYTHONPATH)' | sort > "$SUM/env-snapshot.txt" 2>/dev/null

# 1. the reused parts (readout diff, count page, exports, text counts, acceptance on TAG, regather_report)
TAG=$TAG BASE=$BASE DOCS="$READY" WT=$WT SUM=$SUM OUT=$OUT LOGF=$SUM/run-log-1009.txt REPORT_OUT=${REPORT_OUT:-$OUT/regather-report} \
  bash "$HERE/compare_20261009.sh" > "$OUT/compare_20261009.out" 2>&1 || echo "compare_20261009.sh exit $?" >> "$LOGF"
cat "$SUM/run-log-1009.txt" >> "$LOGF" 2>/dev/null; rm -f "$SUM/run-log-1009.txt"

# 2. the BASE record re-exported by THIS tree (like with like)
MAN=$WT/benchmarks/acceptance/manifest-$BASE-rescore.json
python3 - "$TAG" "$BASE" "$MAN" "$READY" <<'EOF'
import json, sys
tag, base, out, docs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split()
m = json.load(open("benchmarks/acceptance/manifest.json"))
m["documents"] = [d for d in m["documents"] if d["id"] in docs]
for d in m["documents"]:
    d["record"] = {"root": "library", "path": f"_shared-records/{d['id']}-mvt1-whole-{base}.record.json", "md5": None,
                   "note": f"temporary: compare_20261029.sh re-export of {base} by the {tag} tree"}
json.dump(m, open(out, "w"), indent=1)
EOF
# --force: the TAG acceptance above has just rewritten tracked files under benchmarks/acceptance/out, so the tree is
# dirty by our own doing; the re-export is recorded dirty=true on purpose (it is a comparison column, not a record of the tree)
python3 -m tools.omr.acceptance --manifest "$MAN" --force --out "$OUT/base-rescored.current.json" --step-timeout 3600 \
    > "$OUT/base-rescored.acceptance.log" 2>&1 || echo "BASE re-export acceptance exit $?" >> "$LOGF"

rm -f "$MAN" "$WT/benchmarks/acceptance/manifest-$TAG.json"     # temporary manifests: untracked files would dirty the next run
# 3. Sean's judged tiles, one scorer, both records
for doc in $READY; do
  python3 "$HERE/judged_compare.py" "$R/$doc-mvt1-whole-$BASE.record.json" "$R/$doc-mvt1-whole-$TAG.record.json" "$(short $doc)" \
      --json "$OUT/judged-$(short $doc).json" > "$SUM/judged-$(short $doc).txt" 2>&1 || echo "$doc: judged_compare exit $?" >> "$LOGF"
done

# 4. what changed in the exported file + the product ranking (saved verdicts, exported by THIS tree)
for doc in $READY; do
  s=$(short $doc)
  ALL=$(python3 -c "import json;print(','.join(map(str,json.load(open('benchmarks/lane-report/sample.json'))['plates']['$s']['candidates'])))")
  LOADED=$(python3 -c "import json;p=json.load(open('benchmarks/lane-report/sample.json'))['plates']['$s'];print(','.join(map(str,sorted(set(p['pages'])|set(p['context_pages'])))))")
  NLOADED=$(echo "$LOADED" | tr ',' '\n' | wc -l | tr -d ' ')
  K=$HERE/ranking
  for arm in base tag; do
    if [ $arm = base ]; then REC=$R/$doc-mvt1-whole-$BASE.record.json; else REC=$R/$doc-mvt1-whole-$TAG.record.json; fi
    python3 "$K/export_saved.py" "$REC" "$OUT/rank" "$s" "$ALL" "$arm-all" >> "$OUT/rank/export.log" 2>&1 || echo "$doc: export_saved all/$arm failed" >> "$LOGF"
    python3 "$K/export_saved.py" "$REC" "$OUT/rank" "$s" "$LOADED" "$arm" >> "$OUT/rank/export.log" 2>&1 || echo "$doc: export_saved sample/$arm failed" >> "$LOGF"
    python3 "$K/rank_counts.py" "$OUT/rank" "$s" "$arm" "$LOADED" > "$OUT/rank/$s.$arm.rank.json" 2>> "$OUT/rank/export.log" || echo "$doc: rank_counts $arm failed" >> "$LOGF"
  done
  python3 "$K/compare.py" "$s" "$OUT/rank/$s.base-all.symbols.json" "$OUT/rank/$s.tag-all.symbols.json" > "$OUT/rank/compare-all-$s.txt" 2>&1
  python3 "$K/compare.py" "$s" "$OUT/rank/$s.base.symbols.json" "$OUT/rank/$s.tag.symbols.json" > "$OUT/rank/compare-sample-$s.txt" 2>&1
  python3 "$K/rank_table.py" "$OUT/rank" "$s" base tag "$NLOADED" > "$OUT/rank/rank-table-$s.txt" 2>&1
  cp "$OUT/rank/rank-table-$s.txt" "$SUM/ranking-$s.txt"
done

# 5. the process: logs, records' provenance, the code between the commits
python3 "$HERE/logs_diff.py" "$R" "$BASE" "$TAG" $READY > "$SUM/logs-diff.txt" 2>&1
sed -n '1,2p' "$SUM/logs-diff.txt" > "$SUM/logs-wall.txt"
RECS=""
for doc in $READY; do
  { echo "== $doc"; python3 "$HERE/prov_peek.py" "$R/$doc-mvt1-whole-$BASE.record.json" "$R/$doc-mvt1-whole-$TAG.record.json"; } >> "$SUM/prov.txt" 2>&1
done
BC=$(sed -n 's/.*commit \([0-9a-f]\{40\}\).*/\1/p' "$R/overnight-$BASE/summary.txt" | head -1)
TC=$(sed -n 's/.*commit \([0-9a-f]\{40\}\).*/\1/p' "$R/overnight-$TAG/summary.txt" | head -1)
python3 "$HERE/process_diff.py" "$BC" "$TC" > "$SUM/process.txt" 2>&1 || echo "process_diff exit $?" >> "$LOGF"
python3 "$HERE/apples.py" "$TAG" "$BASE" "$R" "$SUM" "$READY" > "$SUM/apples.txt" 2>&1 || echo "apples exit $?" >> "$LOGF"

# 6. the README
python3 "$HERE/readme_20261029.py" "$TAG" "$BASE" "$R" "$SUM" "$READY" >> "$LOGF" 2>&1 || echo "readme exit $?" >> "$LOGF"
echo "done $(date -u +%FT%TZ)" >> "$LOGF"
cat "$LOGF" | tail -8
