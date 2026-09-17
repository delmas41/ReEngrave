# Handoff: re-run the gather with the identity flag on

**Everything from 2026-09-17 is on main** (`e38dbc25`, PR #52). This is one
unfinished measurement and one agent still running.

## 1. THE RE-RUN — one flag, ~40 minutes

The 2026-09-17 re-gather proved `Q.INK`'s reach on a real scan but left
`publisher` unset on all 15,579 store entries, because
**`OMR_DOCUMENT_IDENTITY` is default OFF and the run used defaults.** The
store's whole point is conditioning on the plate, so it has never been
exercised end to end.

```bash
cd /Users/seanjohnson/Desktop/ReEngrave        # or a worktree off main
W=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
PDF=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
O=benchmarks/omr-positional-store-2026-09/out

env OMR_DOCUMENT_IDENTITY=1 OMR_DIRECTION_TEXT_SCAN_GATE=1 \
  python3 -m tools.omr.staged "$PDF" --pages 1-4 --weights "$W" \
  --out $O/beet5-p1-p4-ink-identity.record.json --progress

python3 -m tools.omr.positional_store $O/beet5-p1-p4-ink-identity.record.json \
  --out $O/store.json
```

**What must change from the 2026-09-17 run:** `per publisher` must read
`Henry Litolff's Verlag, Braunschweig, 1870, plate 2769` and NOT `unknown`,
and the accumulator line must not say `identity from none`. The rung resolves
that plate correctly when called directly (`work_id beethoven--symphony-5`,
`image_type Normal Scan`, `source_kind catalog`), so this is a wiring
confirmation, not a discovery.

⚠️ **BEFORE LAUNCHING:** commit everything, including untracked benchmark
files — the record stamps `provenance.dirty` and a dirty stamp makes it
unattributable. Run WITHOUT `--musicxml`: `staged/__main__.py` imports the
exporter AFTER the gather, so a mid-run edit kills it at the last step.
⚠️ A worktree needs the four symlinks (weights, `.venv-surya`, `.venv-omrned`);
three of the four fail on the scan side only.

### What the 2026-09-17 run DID establish (do not re-measure)

7,093 `Q.INK` rows over 4 pages; **3,019 (42.6%) UNNAMED** — no detection
explains them; **1,607 explained by MORE THAN ONE class**. Both counters were
ZERO in every earlier record, so `A-INK-1`'s many-to-many half and the store's
unnamed-ink half are no longer untested. Record: `beet5-p1-p4-ink.record.json`,
provenance `374d1905`, clean.

## 2. THE AGENT STILL RUNNING

`claude/ink-position-facts`-ish — building a position fact for each of the 11
families that have none (`capture` names them). Producers only, no consumers.
Check for its branch; if it landed, expect the SAME collision the store had:

⚠️⚠️ **A NEW BRANCH WILL BREAK `capture --check`, AND THAT IS THE AUDIT
WORKING.** Merging the store produced six failures neither branch could see,
all RED ON SUCCESS — `capture` asserting gaps the store had CLOSED. Expect:
new quantities unclassified in `UNSCORED`, and `POSITION <family> has no
staff-grid position fact` entries going STALE as each is filled. A closed gap
must LEAVE `KNOWN_GAPS`; rewrite the tests to the new contract rather than
deleting them.

## 3. WHAT NOT TO DO WITH THE RESULTS

⚠️ `A-INK-4`: **a measurement retires a concept only within the factor set it
was taken in.** The new position facts are wired to no consumer, so when
anything asks "do they help?" the answer will be no — their partners do not
exist yet. That is the expected result, NOT a verdict. `Q.STEM` is the
near-miss: gathered and unread through THREE discoveries, worth 114 narrowed
durations the day something read it.

⚠️ And `A-INK-4` again: a factor CONTRIBUTES, it does not decide. Do not add a
rule, veto or threshold that uses a position to rule something out.
