# Handoff — continuing the "Project progress dashboard" session

**Written 2026-09-06.** The session titled *Project progress dashboard*
(`local_1fe01edd-849e-4cfd-a3e3-8790a0c42729`, branch
`claude/project-progress-dashboard-3fb8e2`, model Fable 5) was **archived** after
its PR merged, which is why it disappeared from the session list. Its transcript
is intact but its process is stopped, so **the subagents it spawned are gone** —
they were in-process children, not peer sessions, and no handle to them survives.

Nothing is in flight. This file carries what that session knew.

---

## 1. Its work is all on main

Head of main is `7ea27a4b`. Four agent branches landed:

| branch | what it did |
|---|---|
| `claude/movement-reference-2026-09` | a page belongs to its MOVEMENT's orchestra, not the volume's |
| `claude/absent-instrument-veto-2026-09` | refuse a name the movement's lineup cannot contain |
| `claude/spans-veto-composition-2026-09` | the 2×2 that priced the two together |
| `claude/label-ladder-2026-09` | the free label rungs run as documented |

All four verified `IN MAIN`. `docs/progress-dashboard.html` regenerates clean —
`python3 -m tools.dashboard.generate --check` reports **OK: dashboard is current**.

**Three flags were flipped default-ON**, on Sean's explicit delegation of the call:

- `OMR_MOVEMENT_REFERENCE` + `OMR_ABSENT_INSTRUMENT_VETO` (`e3422c71`) — **together;
  the pairing is the decision, neither is right alone**
- `OMR_LABEL_MERGE_QUALITY` (`7ea27a4b`)

### The headline number

Whole work, Beethoven 5 / Litolff, 88 pages, 1616 staff records, 807 judgeable:

| | impossible | correct | wrong | unnamed |
|---|--:|--:|--:|--:|
| spans off / veto off | **91** | 750 | 57 | 0 |
| spans off / veto on | 0 | 750 | 50 | 7 refused |
| **spans on / veto off** | **0** | **756** | 51 | **0** |
| spans on / veto on | 0 | 756 | 51 | 0 |

Spans remove all 91 **by naming**, not by refusing. The veto adds nothing on top
*on this work* — but on a **truncated page set** spans alone go 44 → 57 impossible
(nine correct string names become Trombone), because a span lacking its movement's
opening page has no fully-labelled system and its unlabelled string slots land on
the document's Trombone slots by position. The veto cleans that up. **Which fix
carries the load depends on whether the run contains its movement's opening page,
and the case where spans fail is created by spans.** That is why they ship together.

⚠️ **n = 1 work.** Neither standing benchmark can price either flag, provably: all
20 scan-gate rows and every `orchestral_eval` excerpt are single-page, so the veto
is inert (attestation distance always 0) and spans take no boundary. **A second
whole work disagreeing is the evidence that would reverse the call**, and it does
not exist yet.

---

## 2. Open threads, in the order they are worth picking up

1. **`Tp.` → Trumpet where it means Timpani.** The largest remaining fault on that
   page set: **one bug repeated 51 times**, and the whole residue under spans.
   `Tp.` is Timpani in German/Italian practice and Trumpet in English. Flagged
   independently by two agents.
   ⚠️ **A live session already owns this** — *"Fix `Tp.` resolving to Trumpet, not
   Timpani"* (`local_52073ef5`, running, branch `claude/agitated-bassi-e3a0ab`),
   working out of the dashboard session's old worktree. **Check with it before
   starting anything here.**
2. **`Basso.` → "Bass voice" at HIGH confidence** on an orchestral bottom staff.
   Reader-independent, so a lexicon fault of the `Tr. Alt.` → Alto family. Unfixed.
3. **Harvested lexicon gaps**, concrete and unclaimed: `'in Es 3 4'`,
   `'orni in F I II'`, `'larinetti in A'`, `'mpani in C-G'`.
4. **The veto's 18 refusals under spans are a pure unpriced cost** — unpriced, not
   disproven. Reduced systems carry no full-lineup truth to adjudicate them.
5. **A pre-existing test failure**, not caused by any of this work:
   `test_direction_text::test_the_env_var_restricts_the_rungs` — a cross-test env
   leak. Passes alone and alongside both branches' test files.
6. **25 orphaned `agent-*` git worktrees** under `.claude/worktrees/`. Inert
   checkouts, not processes. Pruning ones whose branches are already in main is
   safe; the rest need a look.

---

## 3. Traps this session paid for — read before running a benchmark

⚠️ **`scan_eval` CACHES, and a cached A/B fails SAFE-LOOKING.**
`run_pipeline` opens with `if pred.is_file() and raw.is_file() and not force:
return`, so two arms sharing a fixtures dir with an empty `--tag` reuse the first
arm's transcriptions and **the second arm never runs**. It reports *"identical on
every bucket and every row"* — exactly the clean no-regression result a
flag-guarded change hopes for. **The tell was wall time, minutes vs hours, not the
output.** Give every arm its own `--tag` (needs `=`, as `--tag=-myarm`) or its own
work-dir. Contrapositive: arms returning *different* numbers did both genuinely run.

⚠️ **A worktree needs FOUR symlinks, and three fail on the scan side only** — so a
worktree that runs `orchestral_eval` cleanly proves nothing about `scan_eval`.
`scan_eval` ignores `OMRNED_PYTHON` and resolves `.venv-omrned` worktree-relative.

⚠️ **The Surya keep-alive server is SHARED.** `pkill -f llama-server` destroyed
another agent's multi-hour run (`395e2193`, committed against itself). Use
`--stop`, or `OMR_SURYA_KEEP_ALIVE=0` for an unattended run.

⚠️ **Establish a null at three levels before believing it.** The label-ladder arms
came back flat on both pools and the agent proved the flag had *run* (transcriptions
differ 20/20 and 11/11), that exports differ on 5 files, and that the entire export
difference is `<part-name>` — which musicdiff does not score. **The pools are blind
to the channel, not to the change.** Measured on that channel directly: engraved
part names **67 → 71 correct, placeholders 2 → 0, 4 of 4 better, 0 worse**.

---

## 4. The correction worth carrying

A PDF text layer is **not** more reliable than OCR — on a scan it *is* OCR,
someone else's, run once, years ago, with no ability to reconsider. Beethoven 5 p.1
staff 8 prints `Violino II.`; the text layer encodes `Yiolino II.`; the lexicon
rescues it via the `Y`→`V` fold, which is tagged `low` **by construction**; and
`slots.MIN_LABEL_CONFIDENCE` and `roster.py:219` both drop `low`. **Read correctly,
carried correctly, discarded at the join** — while the reader that would have got it
right was never asked, because a cost control meant for the *paid* rung was gating a
*free* one, against that module's own documented promise.
