#!/bin/bash
# Compare the all-stages re-gather of 2026-10-09 (TAG, through INFER, main 00473387)
# two ways (Sean 2026-10-08 night: "compare the output of the first 2 stages with
# last night as well as a full/all stages output"):
#
# ⚠️ `--arm env` too: BASE was gathered with OMR_DIRECTION_TEXT_SCAN_GATE=1 (no
# direction words on scans) and TAG without it -- a declared part of the change.
#   A. FIRST TWO STAGES vs last night's re-gather (BASE, through ADJUDICATE):
#      `readout diff` per movement (GATHER + ADJUDICATE only, by construction),
#      the coloured print of each count page (`readout html --against`), and a
#      direction-word / marking count straight off both records.
#   B. ALL STAGES: `tools.omr.acceptance` on the new records (a temporary
#      manifest -- the committed manifest is NOT adopted), its numbers side by
#      side with the last recorded all-stages numbers (benchmarks/acceptance/
#      current.json, 2026-09-30), plus MusicXML / LilyPond / PDF per movement.
#
# Run AFTER regather_20260930.sh (TAG=20261009-all THROUGH=infer) has written
# both records. Small text results go to $SUM (committed); the large ones
# (html pages, exports) stay machine-local under $OUT.
set -uo pipefail
TAG=${TAG:-20261009-all}
BASE=${BASE:-20261008-night}
M=/Users/seanjohnson/Desktop/ReEngrave
R=$M/library/_shared-records
WT=${WT:-$M/.claude/worktrees/overnight-$TAG}    # the clean checkout the gather ran in (2026-10-29: overridable)
DOCS=${DOCS:-"beethoven5-litolff brahms1-breitkopf"}   # 2026-10-29: Litolff alone while Brahms is still gathering (8.8 GB record)
LOGF=${LOGF:-$SUM/README.txt}                     # the script's own log; a caller that writes its own README sets this elsewhere
OUT=${OUT:-$R/overnight-$TAG/compare}   # 2026-10-29: overridable (a test run must not overwrite a night's compare dir)
HERE=$(cd "$(dirname "$0")" && pwd)
SUM=${SUM:-$HERE/$TAG}
mkdir -p "$OUT" "$SUM"
cd "$WT" || exit 2
export OMR_SURYA_KEEP_ALIVE=0 OMRNED_PYTHON=$M/.venv-omrned/bin/python
echo "compare $TAG vs $BASE, tree $(git rev-parse HEAD) start $(date -u +%FT%TZ)" > "$LOGF"

for doc in $DOCS; do
  case $doc in beethoven5-litolff) page=3 ;; *) page=1 ;; esac   # the count pages
  A=$R/$doc-mvt1-whole-$BASE.record.json
  B=$R/$doc-mvt1-whole-$TAG.record.json
  [ -s "$B" ] || { echo "$doc: no record $B" >> "$LOGF"; continue; }
  # A. first two stages
  python3 -m tools.omr.staged.readout diff "$A" "$B" --arm code --arm settings --arm env \
      --label-a "$BASE" --label-b "$TAG" \
      --json "$OUT/$doc-first-two-stages.json" --out "$SUM/$doc-first-two-stages.txt" \
      > "$OUT/$doc-diff.log" 2>&1
  rc=$?   # 2026-10-29: `readout diff` exits 1 WHEN THE RECORDS DIFFER (_cmd_diff: 0 if n_differences == 0 else 1) -- not a failure;
          # only 2 (provenance refused / nothing gathered) is one. The 10-23 README read the 1 as a failure.
  [ $rc -gt 1 ] && echo "$doc: readout diff FAILED exit $rc" >> "$LOGF"
  [ $rc -eq 1 ] && echo "$doc: readout diff exit 1 = the records differ (expected)" >> "$LOGF"
  python3 -m tools.omr.staged.readout html "$B" --against "$A" --arm code --arm settings --arm env \
      --page "$page" --label-a "$BASE" --label-b "$TAG" \
      --out "$OUT/$doc-count-page.html" > "$OUT/$doc-html.log" 2>&1 \
      || echo "$doc: readout html exit $?" >> "$LOGF"
  # B. all stages, as files
  python3 -m tools.omr.staged.export "$B" --out "$OUT/$doc.musicxml" --lilypond "$OUT/$doc.ly" \
      --coverage "$OUT/$doc.coverage.json" > "$OUT/$doc-export.log" 2>&1 \
      || echo "$doc: export exit $?" >> "$LOGF"
  if command -v lilypond >/dev/null && [ -s "$OUT/$doc.ly" ]; then
    (cd "$OUT" && lilypond -o "$doc" "$doc.ly" > "$OUT/$doc-lilypond.log" 2>&1) \
      || echo "$doc: lilypond exit $? (see $doc-lilypond.log)" >> "$LOGF"
  fi
done

# A. direction words and markings, both records (the families readout diff does not list)
python3 "$HERE/text_counts.py" "$R" "$BASE" "$TAG" $DOCS > "$SUM/text-words-and-markings.txt" 2>&1

# B. all-stages acceptance on the new records, through a temporary manifest
MAN=$WT/benchmarks/acceptance/manifest-$TAG.json   # inside the checkout: acceptance prints it relative to the repo
python3 - "$R" "$TAG" "$MAN" "$DOCS" <<'EOF'
import json, sys
R, tag, out, docs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split()
m = json.load(open("benchmarks/acceptance/manifest.json"))
m["documents"] = [d for d in m["documents"] if d["id"] in docs]
for d in m["documents"]:
    d["record"] = {"root": "library", "path": f"_shared-records/{d['id']}-mvt1-whole-{tag}.record.json",
                   "md5": None, "note": f"temporary: compare_20261009.sh, re-gather {tag}"}
json.dump(m, open(out, "w"), indent=1)
EOF
python3 -m tools.omr.acceptance --manifest "$MAN" --out "$OUT/current.json" \
    --step-timeout 3600 > "$OUT/acceptance.log" 2>&1 \
    || echo "acceptance exit $? (see $OUT/acceptance.log)" >> "$LOGF"
cp "$OUT/current.json" "$SUM/current.json" 2>/dev/null
python3 - "$SUM/current.json" "$M/benchmarks/acceptance/current.json" > "$SUM/all-stages-vs-20260930.txt" <<'EOF'
import json, sys
try:
    new = json.load(open(sys.argv[1]))
except Exception as e:                     # noqa: BLE001
    print("no new current.json:", e); sys.exit(0)
old = json.load(open(sys.argv[2]))
print(f"all stages: NEW tree {new.get('tree')} ({new.get('date')})  vs  OLD tree {old.get('tree')} ({old.get('date')})")
def walk(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k in ("names",):
                continue
            if k in b:
                walk(a[k], b[k], f"{path}.{k}" if path else k)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if a != b:
            print(f"  {path:70s} {b!s:>12} -> {a!s:>12}")
for doc in ("beethoven5-litolff", "brahms1-breitkopf"):
    print(f"\n== {doc}  (old -> new; only the numbers that moved)")
    walk(new.get("summary", {}).get(doc, {}), old.get("summary", {}).get(doc, {}))
EOF

# 2026-10-29: only with BOTH plates (regather_report walks both and would load the other plate's 8.8 GB record) and not when SKIP_REPORT is set.
if [ "$(echo $DOCS | wc -w)" -ge 2 ] && [ -z "${SKIP_REPORT:-}" ]; then
# C. ROADMAP 2.118: the DETAILED stage-by-stage report, per movement, beside the previous night.
# A separate, last step: it reads what the steps above wrote and cannot change them. A failure
# here only adds a line to the README.
REPORT_OUT=${REPORT_OUT:-$HERE/../../omr-regather-report-2026-10/$TAG}
mkdir -p "$REPORT_OUT"
python3 -m tools.omr.staged.check > "$REPORT_OUT/check.txt" 2>&1
python3 -m tools.omr.staged.regather_report night --tag "$TAG" --base "$BASE" \
    --compare-dir "$OUT" --out "$REPORT_OUT" > "$OUT/regather-report.log" 2>&1 \
    || echo "regather_report exit $? (see $OUT/regather-report.log)" >> "$LOGF"
fi
echo "done $(date -u +%FT%TZ)" >> "$LOGF"
