#!/bin/zsh
# A mutation battery for the direction-word wiring — gatherer, decision,
# emission, counter.
#
# ⚠️ RESTORES FROM git, never from a hand-named backup — the articulation
# battery's first run copied to one name and restored from another, so `sed`
# wrote empty files over both sources and all ten arms reported SURVIVED
# because pytest said "no tests ran" and the classifier grepped for "failed".
#
# ⚠️ A BATTERY CAN PASS BY REFUSING EVERYTHING **AND** BY ACCEPTING
# EVERYTHING. ARM 0 is the positive control on the unmutated tree; an arm that
# reports BROKEN is a harness failure and is NOT a survivor.
#
# ⚠️ ANCHOR ON A WHOLE EXPRESSION, NOT A FRAGMENT. One fermata arm survived
# because `for h in heads` occurs three times in `rhythm.py` and it mutated a
# different function. Every anchor below was checked unique with `grep -c`.
#
# ⚠️ DO NOT RUN THIS WHILE A STAGED GATHER IS IN FLIGHT. `staged/__main__.py`
# imports the exporter AFTER the gather, so a long run picks up whatever
# `export.py` says when it reaches EXPORT.
T="tools/omr/tests/test_staged_direction.py tools/omr/tests/test_staged_export.py tools/omr/tests/test_staged_gather_coverage.py tools/omr/tests/test_staged_stage_contract.py"
EXPECT=199

check() {  # -> RED | SURVIVED | BROKEN
  local out; out=$(python3 -m pytest ${=T} -q 2>&1 | tail -3)
  if   echo "$out" | grep -q "no tests ran";  then echo "BROKEN(no tests)"
  elif echo "$out" | grep -q "error";          then echo "BROKEN(collect error)"
  elif echo "$out" | grep -q "failed";         then echo "RED"
  elif echo "$out" | grep -q "$EXPECT passed"; then echo "SURVIVED"
  else echo "BROKEN(unrecognised: $out)"; fi
}

arm() {  # file, 'old||new', name
  python3 - "$1" "$2" <<'PY'
import subprocess, sys
path, expr = sys.argv[1], sys.argv[2]
src = subprocess.run(["git","show",f"HEAD:{path}"],capture_output=True,text=True).stdout
old, new = expr.split("||")
if old not in src:
    sys.stderr.write(f"MUTATION DID NOT APPLY: {old!r}\n"); sys.exit(3)
open(path,"w").write(src.replace(old,new,1))
PY
  if [ $? -ne 0 ]; then echo "NOT APPLIED: $3"; git checkout -- "$1"; return; fi
  echo "$(check): $3"
  git checkout -- "$1"
}

G=tools/omr/staged/gather.py
X=tools/omr/staged/adjudicators/text.py
E=tools/omr/staged/export.py
echo "ARM 0 positive control: $(check)  (expected SURVIVED)"

# ── GATHER: the four states ───────────────────────────────────────────────
arm $G 'reason=ABSTAIN.READER_UNAVAILABLE,
                    note="no OCR rung available: neither .venv-surya nor "
                         "tesseract",||reason=ABSTAIN.NO_INK,
                    note="no OCR rung available: neither .venv-surya nor "
                         "tesseract",' \
       "GATHER: a blind machine reads as a page with no words"
arm $G 'reason=ABSTAIN.NO_INK,
                    note="the CV proposed no word-shaped ink in any band",||reason=ABSTAIN.READER_UNAVAILABLE,
                    note="the CV proposed no word-shaped ink in any band",' \
       "GATHER: a page with no words reads as a blind machine"
arm $G 'reason=ABSTAIN.NO_READING,
                        page_n_read=n_read,||reason=ABSTAIN.NO_INK,
                        page_n_read=n_read,' \
       "GATHER: a refused candidate reads as no ink at all"
arm $G '        _direction_cells_abstain(log, cells, local,
                                 ABSTAIN.READER_UNAVAILABLE,
                                 note="no OCR rung available")
        return||        return' \
       "GATHER: the blind state never reaches a CELL, so the decision is never asked"
arm $G 'if os.environ.get("OMR_DIRECTION_TEXT", "1").strip().lower() in (
            "0", "", "false", "no", "off"):||if os.environ.get("OMR_DIRECTION_TEXT", "1").strip().lower() not in (
            "1", "true", "yes", "on"):' \
       "GATHER: the default-ON flag read as an allow-list (a typo blinds it)"

# ── GATHER: the shim, and the corner/width hazard ─────────────────────────
arm $G '"bbox_page": [int(x0), int(y0),
                              int(round(x1 - x0)), int(round(y1 - y0))],||"bbox_page": [int(x0), int(y0), int(x1), int(y1)],' \
       "GATHER: a CORNER box handed to a reader that reads WIDTHS"
arm $G '"bbox_page_px": [int(v) for v in box] if box else None,||"bbox_page_px": [int(box[0]), int(box[1]),
                              int(box[2] - box[0]),
                              int(box[3] - box[1])] if box else None,' \
       "GATHER: a WIDTH span handed to a reader that reads CORNERS"

# ── GATHER: the join ──────────────────────────────────────────────────────
arm $G 'hits = accepted.get(
            (int(cand.staff_index), int(cand.measure_index),
             int(cand.x_page)))||hits = list(accepted.values())[0] if accepted else None' \
       "GATHER: readings joined to candidates by position, not by identity"

# ── ADJUDICATE ────────────────────────────────────────────────────────────
arm $X 'rows = ev.rows(Q.DIRECTION_WORD, scope=Scope.SELF_AND_DESCENDANTS)||rows = ev.rows(Q.DIRECTION_WORD)' \
       "ADJUDICATE: the declared input can never answer (default scope)"
arm $X 'return Ruling.abstain(ABSTAIN.READER_UNAVAILABLE,
                              blocked_rows=len(blocked),||return Ruling(value=[], reason="no_words", detail={"x": len(blocked)}) or Ruling.abstain(ABSTAIN.READER_UNAVAILABLE,
                              blocked_rows=len(blocked),' \
       "ADJUDICATE: blindness decided as an empty bar"
arm $X 'words.sort(key=lambda w: (w["x_page"] if w["x_page"] is not None
                                  else 0.0, w["text"]))||pass' \
       "ADJUDICATE: words emitted in gather order, not in page-x order"
arm $X 'return Ruling(value=[], reason="no_words",||return Ruling.abstain(ABSTAIN.NO_INK) or Ruling(value=[], reason="no_words",' \
       "ADJUDICATE: a read-and-empty bar abstains instead of deciding"

# ── EXPORT: emission and counter ──────────────────────────────────────────
arm $E '    _place_direction_words(rec, runs)||    pass' \
       "EXPORT: the decision decides into no file"
arm $E '(float(x) if x is not None else 0.0, "words", str(text)))||(float(x) if x is not None else 0.0, "dynamics", str(text)))' \
       "EXPORT: a word rendered as a <dynamics>"
arm $E 'counters["dynamics" if kind == "dynamics" else "direction_words"] += 1||counters["dynamics"] += 1' \
       "EXPORT: one counter again — a word billed to the dynamic family"
arm $E '"direction": (Q.DIRECTION, (), ("direction_words",)),||"direction": (Q.DIRECTION, (), ()),' \
       "EXPORT: the family loses its counter and cannot say what reached the file"
arm $E '"balanced": (d_written + report["direction_words_not_written_total"]
                     == d_decided),||"balanced": (d_written + report["direction_words_not_written_total"]
                     <= d_decided),' \
       "EXPORT: the balance regresses to the <= that hid ten hairpins"
arm $E '"cell_not_in_any_part": d_decided - d_placed,||"cell_not_in_any_part": 0,' \
       "EXPORT: the residue bucket stops counting"
