#!/bin/bash
# Part B of the staged-Surya experiment: the FRACTION OF A REAL GATHER.
#
# docs/scope-surya-staged-optin-2026-09-16.md §9. Four ABAB arms (L = both OCR
# rungs on, C = the current default) plus LD, which asks whether the two Surya
# consumers share a model load.
#
#     bash benchmarks/omr-surya-staged-cost-2026-09/run_arms.sh
#     ARMS="L1" bash .../run_arms.sh          # one arm
#
# ⚠️⚠️ FOUR CORRECTIONS TO THE SCRIPT AS THE SCOPE SKETCHES IT, each against a
# trap this repo has already paid for:
#
#  1. IT RUNS FROM THE REPO ROOT. The sketch `cd`s into the benchmark dir and
#     then calls `python3 -m tools.omr.staged`, which cannot resolve.
#
#  2. NO `| tee` ON A COMMAND WHOSE EXIT CODE MATTERS. CLAUDE.md records a
#     `| tail` swallowing a real failure's status, and the 2026-09-15 pass
#     records a background suite exiting 0 having run nothing. Output goes to
#     a file and the status is read from the command itself.
#
#  3. THE CENSUS COUNTS OBSERVATIONS, NOT `grep -c '"margin_label"'`. Step 1
#     of this session made `gather_margin_labels` write an ABSTENTION per
#     staff, so that grep now reports ~75 for a C arm that must census ZERO --
#     the control inverts. See census.py.
#
#  4. `--check` IS A GATE, NOT A NOTE. A resident server means the arm
#     measures queueing (CLAUDE.md, 2026-09-11), so the run aborts. NEVER
#     `pkill`; `python3 -m tools.omr.staff_labels_surya --stop`.
#
# ⚠️ AND IT REFUSES A DIRTY TREE AND A RE-RUN OVER AN EXISTING RECORD. An
# unprovenanced A/B is the documented failure where "nothing moved" cannot be
# told from "you compared a file with itself"; a silently reused arm is the
# `scan_eval` caching trap, whose signature is an A/B that looks perfectly
# clean and ran once.

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BENCH="$ROOT/benchmarks/omr-surya-staged-cost-2026-09"
OUT="$BENCH/out"
cd "$ROOT" || exit 2
mkdir -p "$OUT"

PDF="${PDF:-$ROOT/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf}"
W="${W:-$ROOT/tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt}"
PAGES="${PAGES:-1-4}"
ARMS="${ARMS:-L1 C1 L2 C2 LD}"
export OMR_SURYA_KEEP_ALIVE=0

[ -f "$PDF" ] || { echo "ABORT: no PDF at $PDF"; exit 2; }
[ -f "$W" ]   || { echo "ABORT: no weights at $W"; exit 2; }

DIRTY="$(git status --porcelain | grep -v '^?? benchmarks/omr-surya-staged-cost-2026-09/out/' | wc -l | tr -d ' ')"
if [ "$DIRTY" != "0" ]; then
  echo "ABORT: the tree is dirty; every arm must share ONE commit with"
  echo "       dirty=false or the records name no tree."
  git status --porcelain | grep -v '^?? benchmarks/omr-surya-staged-cost-2026-09/out/'
  exit 2
fi
COMMIT="$(git rev-parse HEAD)"
echo "tree: $COMMIT (clean)"
echo "pdf : $PDF"
echo "arms: $ARMS   pages: $PAGES"
echo

for arm in $ARMS; do
  REC="$OUT/record-$arm.json"
  if [ -f "$REC" ]; then
    echo "ABORT: $REC already exists. A silently reused arm reports"
    echo "       'identical on every row' whatever the change did. Move it"
    echo "       aside deliberately."
    exit 2
  fi

  # GATE 1 -- nothing else may be reading the machine.
  python3 -m tools.omr.staff_labels_surya --check > "$OUT/$arm.precheck" 2>&1
  if grep -q '^persistent server: yes' "$OUT/$arm.precheck"; then
    echo "ABORT at $arm: a keep-alive server is resident -- this arm would"
    echo "       measure QUEUEING. Stop it with"
    echo "       python3 -m tools.omr.staff_labels_surya --stop"
    echo "       (never pkill), once nothing else is reading."
    cat "$OUT/$arm.precheck"
    exit 2
  fi
  # ⚠️ THE EXECUTABLE MUST BE PYTHON, NOT MERELY A COMMAND LINE MENTIONING
  # THE MODULE. `pgrep -f 'tools\.omr\.staged'` matches every shell whose
  # command line happens to contain the string -- including this session's
  # own tool-call wrappers and any commit message quoting it. Measured: it
  # reported EIGHT in-flight OMR runs when there were none, and aborted the
  # first arm. It failed CLOSED, which is the safe direction, but a gate
  # that can never pass is not a gate. Matching `comm` (the executable)
  # excludes a shell by construction.
  OTHER="$(ps -axo comm=,args= 2>/dev/null \
           | awk '$1 ~ /[Pp]ython/ && $0 ~ /-m tools\.omr\.(staged|transcribe)/' \
           | wc -l | tr -d ' ')"
  if [ "$OTHER" != "0" ]; then
    echo "ABORT at $arm: another OMR run is in flight ($OTHER python process(es))."
    ps -axo comm=,args= | awk '$1 ~ /[Pp]ython/ && $0 ~ /-m tools\.omr\.(staged|transcribe)/' | cut -c1-140
    exit 2
  fi

  # ⚠️ `LD` MUST COME BEFORE `L*`, AND IT DID NOT. `case` takes the FIRST
  # match, so `L*` swallowed `LD` and the arm built to answer "is the model
  # load shared between the two Surya consumers" ran with
  # OMR_DIRECTION_TEXT=1 -- an exact duplicate of an L arm. It cost 39
  # minutes and was caught only because the run's own echo prints DIRTEXT
  # beside the arm name. A `case` whose patterns overlap is ordered, not
  # matched, and the specific one has to be first.
  case "$arm" in
    LD) FLAGS="--surya --ocr"; DIRTEXT=0 ;;
    L*) FLAGS="--surya --ocr"; DIRTEXT=1 ;;
    C*) FLAGS="";              DIRTEXT=1 ;;
    *)  echo "ABORT: unknown arm '$arm'"; exit 2 ;;
  esac

  {
    echo "arm=$arm"
    echo "commit=$COMMIT"
    echo "dirty=0"
    echo "flags=$FLAGS"
    echo "OMR_DIRECTION_TEXT=$DIRTEXT"
    echo "OMR_SURYA_KEEP_ALIVE=$OMR_SURYA_KEEP_ALIVE"
    echo "start_epoch=$(date -u +%s)"
    echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    # ⚠️ WHAT THE ARM WAS COMPETING WITH. This machine idles near load 7 on
    # unrelated desktop processes, and CLAUDE.md records a suite stalling at
    # load 7 in a way that reads exactly like a hang. A wall-clock figure
    # with no load beside it cannot be compared to one taken on a quiet
    # machine -- which is half of why the 2026-09-11 pair's residue is
    # unexplained.
    echo "load_before=$(uptime | sed 's/.*averages*: //')"
  } > "$OUT/$arm.timing"

  echo "── $arm  flags='$FLAGS' OMR_DIRECTION_TEXT=$DIRTEXT  $(date -u +%H:%M:%SZ)"
  OMR_DIRECTION_TEXT=$DIRTEXT python3 -u -m tools.omr.staged "$PDF" \
      --pages "$PAGES" --weights "$W" $FLAGS \
      --out "$REC" --progress > "$OUT/$arm.log" 2>&1
  RC=$?
  {
    echo "end_epoch=$(date -u +%s)"
    echo "end_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "load_after=$(uptime | sed 's/.*averages*: //')"
    echo "exit=$RC"
  } >> "$OUT/$arm.timing"

  if [ "$RC" != "0" ]; then
    echo "   arm $arm FAILED (exit $RC); tail of its log:"
    tail -20 "$OUT/$arm.log"
    exit 1
  fi

  # The rung header -- §9 control 3. An arm cannot assert it was measuring
  # Surya unless the run said Surya was up.
  grep -m1 '^  rungs:' "$OUT/$arm.log" >> "$OUT/$arm.timing" \
      || echo "rungs=MISSING" >> "$OUT/$arm.timing"

  case "$arm" in
    C*) EXPECT="--expect-observations-exactly 0" ;;
    *)  EXPECT="--expect-observations-at-least 45" ;;
  esac
  python3 "$BENCH/census.py" "$REC" $EXPECT \
      --json-out "$OUT/$arm.census.json" > "$OUT/$arm.census.txt" 2>&1
  CRC=$?
  echo "census_exit=$CRC" >> "$OUT/$arm.timing"
  S=$(grep start_epoch "$OUT/$arm.timing" | cut -d= -f2)
  E=$(grep end_epoch "$OUT/$arm.timing" | cut -d= -f2)
  echo "   $arm: $((E - S)) s, census exit $CRC"
  tail -2 "$OUT/$arm.census.txt"
  if [ "$CRC" != "0" ]; then
    echo "   ⚠️ arm $arm is VOID by its own census."
  fi
done

echo
echo "── wall clock ────────────────────────────────────────────"
for arm in $ARMS; do
  S=$(grep start_epoch "$OUT/$arm.timing" | cut -d= -f2)
  E=$(grep end_epoch "$OUT/$arm.timing" | cut -d= -f2)
  N=$(python3 -c "import json;print(json.load(open('$OUT/$arm.census.json'))['margin_label_observations'])" 2>/dev/null || echo "?")
  printf "  %-3s %6s s   %s labels\n" "$arm" "$((E - S))" "$N"
done
