#!/bin/bash
# Roadmap 1.1: a whole-movement staged gather for one of the three
# acceptance documents (benchmarks/acceptance/manifest.json), in one
# command.
#
#   bash benchmarks/acceptance/gather_movement.sh beethoven5-litolff --pages 0-17
#   bash benchmarks/acceptance/gather_movement.sh brahms1-breitkopf --pages 0-15
#   bash benchmarks/acceptance/gather_movement.sh beethoven5-engraved
#
# ⚠️⚠️ `--pages` IS REQUIRED FOR THE TWO SCANS, AND THIS SCRIPT REFUSES TO
# GUESS THE MOVEMENT'S LAST PAGE -- CLAUDE.md rule 6, "connect, never guess".
# The hand-verified `works.json` windows for both scans stop well short of
# the movement's end:
#
#   beethoven5-litolff: verified to pdf_page_index 4 (ref measure 112 of
#     502, 22%). Edition is 88 pages total (whole symphony, 4 movements).
#   brahms1-breitkopf:  verified to pdf_page_index 3 (ref measure 58 of
#     513, 11%). Edition is 86 pages total.
#
# Neither dossier nor works.json says where movement 1 actually ends on
# these plates -- that needs a human opening the PDF and finding the double
# barline / new tempo heading where movement 2 begins. A wrong guess here
# would wire a whole-movement decision to ink from the WRONG movement, which
# is worse than an honest missing artefact. Determine the range by hand,
# then pass it with `--pages`.
#
# The engraved document (`beethoven5-engraved`) needs none of this: it is a
# committed, already-bounded 24-bar / 3-page render (DECISIONS.md 2026-09-22
# names the excerpt on purpose, not the whole movement), and this script
# defers entirely to the existing lane that builds and gathers it.
#
# Every run writes a NEW record beside the manifest's existing (short,
# hand-verified) one -- it does NOT overwrite `manifest.json`'s `record.path`
# or its committed `md5` receipt. Pointing the acceptance harness at
# tonight's whole-movement record instead of the 4-page one is a separate,
# deliberate edit to the manifest for whoever reviews the run; this script
# only produces the artefact.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

MANIFEST="benchmarks/acceptance/manifest.json"

usage() {
  echo "usage: $0 <doc-id> [--pages A-B] [--no-route-weights]" >&2
  echo "  doc-id: one of the ids in $MANIFEST" >&2
  exit 1
}

DOC_ID="${1:-}"
[ -n "$DOC_ID" ] || usage
shift

PAGES=""
ROUTE_WEIGHTS=1
while [ $# -gt 0 ]; do
  case "$1" in
    --pages) PAGES="$2"; shift 2 ;;
    --no-route-weights) ROUTE_WEIGHTS=0; shift ;;
    *) echo "ERROR: unrecognised argument $1" >&2; usage ;;
  esac
done

# ── 1. provenance: refuse a dirty tree ──────────────────────────────────────
# ⚠️ A gather's own provenance stamp names the tree that FINISHED, not the
# code that ran (CLAUDE.md 5b) -- refusing up front is cheaper than
# discovering the discrepancy after an hour-long run.
if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: working tree is not clean." >&2
  echo "  A whole-movement gather's provenance stamp should name a real" >&2
  echo "  commit. Commit or stash first, then re-run." >&2
  git status --short >&2
  exit 1
fi
COMMIT="$(git rev-parse --short HEAD)"

# ── 2. resolve the document from the manifest ───────────────────────────────
INFO="$(python3 - "$DOC_ID" "$MANIFEST" <<'PYEOF'
import json
import sys
from pathlib import Path

doc_id, manifest_path = sys.argv[1], sys.argv[2]
sys.path.insert(0, ".")
from tools.omr.acceptance import load_manifest, resolve_path  # noqa: E402

try:
    manifest = load_manifest(Path(manifest_path))
except Exception as exc:  # noqa: BLE001
    print(f"ERROR: could not load {manifest_path}: {exc}", file=sys.stderr)
    sys.exit(1)

docs = {d["id"]: d for d in manifest["documents"]}
if doc_id not in docs:
    print(f"ERROR: unknown document id {doc_id!r}. Choices: "
          f"{sorted(docs)}", file=sys.stderr)
    sys.exit(1)

d = docs[doc_id]
pdf = resolve_path(d["pdf"])
if pdf is None or not pdf.is_file():
    print(f"ERROR: no PDF at {d.get('pdf')} (resolved: {pdf}). The score "
          f"library ('library/') is machine-local -- is it symlinked into "
          f"this worktree?", file=sys.stderr)
    sys.exit(1)

import shlex


def sh(k, v):
    print(f"{k}={shlex.quote(str(v))}")


sh("PDF", pdf)
sh("DPI", d["dpi"])
sh("KIND", d["kind"])
sh("LABEL", d["label"])
cp = d.get("count_page") or {}
sh("COUNT_PAGE_INDEX", cp.get("pdf_page_index"))
PYEOF
)"
if [ $? -ne 0 ] || [ -z "$INFO" ]; then
  exit 1
fi
eval "$INFO"

OUT_DIR="benchmarks/acceptance/out/${DOC_ID}"
mkdir -p "$OUT_DIR"

echo "── ${DOC_ID}: ${LABEL}"
echo "   pdf:    ${PDF}"
echo "   kind:   ${KIND}"
echo "   commit: ${COMMIT}"

# ── 3. the engraved document defers entirely to its own lane ───────────────
if [ "$KIND" = "engraved" ]; then
  if [ -n "$PAGES" ]; then
    echo "   (⚠️ --pages ignored: ${DOC_ID} is a fixed, already-bounded" >&2
    echo "   render; see benchmarks/omr-staged-engraved-2026-09/run_all.sh)" >&2
  fi
  echo "   this document is not a whole-movement scan gather -- it is a"
  echo "   committed 24-bar / 3-page render, already built by the lane"
  echo "   below (idempotent: it skips any step whose output exists)."
  exec bash benchmarks/omr-staged-engraved-2026-09/run_all.sh
fi

# ── 4. the two scans need an explicit, human-determined page range ─────────
if [ -z "$PAGES" ]; then
  cat >&2 <<EOF
ERROR: --pages is required for ${DOC_ID}.

The hand-verified works.json window for this document does not reach the
end of the movement (see this script's own header for the exact figures:
${DOC_ID} is verified only to page index ${COUNT_PAGE_INDEX}). Open the PDF
at ${PDF}
and find the page where movement 1 ends (a double barline followed by a new
tempo heading / movement title), then re-run with e.g. --pages 0-17.
EOF
  exit 1
fi

# ── 5. the budget estimate, before starting anything expensive ─────────────
N_PAGES="$(python3 -c "
from tools.omr.staged.__main__ import parse_pages
print(len(parse_pages('$PAGES')))
")"
python3 - "$N_PAGES" "$KIND" <<'PYEOF'
import sys
n = int(sys.argv[1])
# CLAUDE.md Sec.5b: ~93 s/page with the margin-label rungs; ~267 s/page if
# the direction-word reader also runs. OMR_DIRECTION_TEXT_SCAN_GATE=1 (set
# below, per roadmap 1.2) skips that reader on a page PROVED to be a scan,
# so the lower figure is what applies here -- printed alongside the
# without-the-gate figure so a reviewer can see what the gate is buying.
with_gate = n * 93
without_gate = n * (93 + 267)
def fmt(s):
    return f"{s}s (~{s/60:.1f} min, ~{s/3600:.1f} h)"
print(f"── budget estimate over {n} pages, OMR_DIRECTION_TEXT_SCAN_GATE=1:")
print(f"   expected (gate skips the direction reader on scan pages): {fmt(with_gate)}")
print(f"   if the gate did not fire on any page (upper bound):        {fmt(without_gate)}")
print("   ⚠️ n=1 document at this scale (roadmap 1.1's own first run) --")
print("   these figures are the CLAUDE.md per-page constants times page")
print("   count, not a measurement of a whole movement.")
PYEOF

# ── 6. the gather itself ────────────────────────────────────────────────────
TS="$(date -u +%Y%m%dT%H%M%SZ)"
RECORD="${OUT_DIR}/${DOC_ID}-whole-movement-${TS}.record.json"
LOG="${OUT_DIR}/${DOC_ID}-whole-movement-${TS}.log"

WEIGHTS_ARGS=(--weights auto)
if [ "$ROUTE_WEIGHTS" -eq 1 ]; then
  WEIGHTS_ARGS+=(--route-weights)
  echo "   weight routing: ON (--route-weights; OMR_WEIGHT_ROUTING default)"
else
  WEIGHTS_ARGS=(--weights auto --no-weight-routing)
  echo "   weight routing: OFF (--no-weight-routing) -> default weights"
fi

echo "── gathering pages ${PAGES} (${N_PAGES} pages) -> ${RECORD}"
echo "   log: ${LOG}"

# ⚠️ NO --musicxml HERE (CLAUDE.md 5b): staged/__main__.py imports the
# exporter AFTER the gather, so an edit to export.py mid-run would reach it
# and can turn a finished multi-hour gather into a NameError. Export
# separately below, once the gather has actually finished.
env \
  OMR_SURYA_KEEP_ALIVE=0 \
  OMR_DIRECTION_TEXT_SCAN_GATE=1 \
  PYTHONUNBUFFERED=1 \
  python3 -u -m tools.omr.staged "$PDF" --pages "$PAGES" --dpi "$DPI" \
    "${WEIGHTS_ARGS[@]}" --progress \
    --out "$RECORD" 2>&1 | tee "$LOG"

if [ ! -s "$RECORD" ]; then
  echo "ERROR: gather produced no (or an empty) record at $RECORD" >&2
  exit 1
fi

# ── 7. md5 receipt ───────────────────────────────────────────────────────────
MD5="$(md5 -q "$RECORD" 2>/dev/null || md5sum "$RECORD" | cut -d' ' -f1)"
echo "$MD5  $(basename "$RECORD")" > "${RECORD}.md5"
echo "── wrote ${RECORD} (md5 ${MD5})"

# ── 8. export MusicXML + LilyPond separately, from the finished record ─────
XML="${RECORD%.record.json}.musicxml"
LY="${RECORD%.record.json}.ly"
COVERAGE="${RECORD%.record.json}.coverage.json"
python3 -m tools.omr.staged.export "$RECORD" \
  --out "$XML" --lilypond "$LY" --coverage "$COVERAGE"
echo "── wrote ${XML}, ${LY}, ${COVERAGE}"

echo "── done. Provenance: commit ${COMMIT}, tree was clean at gather start."
echo "   To use this as the acceptance record for ${DOC_ID}, edit"
echo "   ${MANIFEST}'s record.path/record.md5 for it deliberately -- this"
echo "   script does not do that for you."
