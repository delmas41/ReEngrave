# CLAUDE.md migration, 2026-10-13

Sean (2026-10-13): *"I would like to make Claude.md much more concise. I don't
want to lose specific knowledge that we need for context but it feels
bloated."* The 6,174-word `CLAUDE.md` (last at `31ddceb5`) became an
1,844-word one; every section below maps to where its content now lives.
`git show 31ddceb5:CLAUDE.md` is the old text.

Old section numbers are still cited in ROADMAP and DECISIONS lines written
before today (e.g. "CLAUDE.md §10", "§6b"); this table resolves them.

**Legend:** KEPT = still in CLAUDE.md (section given); MOVED = verbatim or
lightly trimmed into the named doc; DROPPED = removed, with the reason.

| old section / bullet | now |
|---|---|
| **Header** ("This is the SPEC ... under 6,000 words ... restates no measurement") | KEPT, rewritten (header). |
| Header: read order (CLAUDE.md, ROADMAP, DECISIONS, plan 2026-09-22) | KEPT (header); the plan moved to the §8 index. |
| Header: the chronicle, "read it by search, never front to back, never brief a lane from it" | KEPT, shortened to one row of the §8 index ("search it, never brief from it"). The reason (sentences corrected in place) DROPPED as duplicate of the chronicle's own header. |
| Header: `PROJECT_STATUS.md`/`NOTES.md` frozen; `PROJECT_BRIEF.md`/`version_memory.md` un-frozen 2026-10-07 and updated with every commit | KEPT (last line of §8 and §6 "Landing"); the un-freeze date DROPPED (history, in DECISIONS 2026-10-07 and `version_memory.md`'s own header). |
| **§1 What the product is** (product, definition of done, "Sean is the cheapest evidence") | KEPT verbatim (§1). |
| **§2 The ten rules** 1-10 | KEPT (§2), each tightened; substance unchanged. Rule 7's "who says it's right" line kept with its date dropped (DECISIONS 2026-09-29 holds it). |
| **§3 Two readers, one product path** (STAGED product path; LEGACY frozen; 39 legacy flags; the shared modules list) | KEPT in two sentences (§3); full text MOVED to `docs/staged-internals.md` §1. The 3.1/3.3 LilyPond/PDF/web-app status lines MOVED there too. |
| **§4a Stages** table + "does the answer FOLLOW, or is it merely BEST" | KEPT (§3). Also in `docs/staged-internals.md` §2. |
| **§4b The record** (subjects, rows, verdicts, quantities, scope, GATHER order / A-GATHER-1, provenance, correlated_groups) | MOVED to `docs/staged-internals.md` §3. |
| **§4c The decisions** (adjudicator files, the derive command, wants/implicates, stubs; EVALUATE rules; INFER switches and harness; EXPORT equality, refusals, `Unbalanced`, hold-out, measure-rest, `status_census`) | MOVED to `docs/staged-internals.md` §4 (file list left open-ended with "..." since the count is derived; GUESSED-blue note added from DECISIONS 2026-10-12/13). "Stubs: none" DROPPED -- the tool `adjudicate.stubs()` is the truth, as the line itself said. |
| **§4d The derived checks** (`check`, exit codes, N must go down, KNOWN_GAPS, the parts list, three blind spots) | MOVED to `docs/staged-internals.md` §5. "114-entry" registry count DROPPED (a count the `conventions` check derives). The one-line "check number must go down" KEPT (§6 Tests). |
| **§5a Setup** (docker, `.env`, admin bypass, hot-patch, weights files, never `phase-j-mix`) | MOVED to `docs/running.md` §1. "Never load `phase-j-mix`" also KEPT (§7). |
| §5a worktree symlinks (the four assets) | MOVED to `docs/running.md` §1; KEPT as a pointer (§6 "Where"). |
| §5a library machine-local; cloud container shallow clone (121 commits, `--unshallow`, 0.8's 41 rows) | MOVED to `docs/running.md` §1 "Cloud sessions". |
| **§5b Staged CLI** (commands, option list, `--movements`, `--pdf`, no `--dossier`) | MOVED to `docs/running.md` §2 (`--through` added to the option list; it was missing). |
| §5b operational facts (export separately; cost 93 s/page + 3-36 s direction words, 267 s before; `OMR_SURYA_KEEP_ALIVE`; never `pkill llama-server`; 115 MB/page) | MOVED to `docs/running.md` §2. "Never `pkill -f llama-server`" also KEPT (§6). The timings are measurements and ALSO live in `benchmarks/omr-direction-text-2026-09/FINDINGS.md` and `benchmarks/omr-decide-stage-cost-2026-09/FINDINGS.md`; kept in running.md as operating guidance, not as a result. |
| §5b other staged commands (`check`, `export`, `trace`, `readout show/diff/html`, `factsheet`, `acceptance_quick`) and the `readout` note | MOVED to `docs/running.md` §2. |
| §5b one command (`tools.reengrave import`, ROADMAP 4.1) | MOVED to `docs/running.md` §2. |
| **§5c Legacy pipeline** (commands; web app OMR/export/review route; `apply_corrections_to_musicxml` stub; `claude_vision` engine) | MOVED to `docs/running.md` §4. |
| **§6a Acceptance set** (table; engraved / proxies / the count) | MOVED to `docs/measuring.md` §1 (count-deferred note and hand-truth pointer added). Pointer KEPT (rule 4, §8). |
| **§6b How to A/B** (every test GATHER+ADJUDICATE; two re-gathers; small re-gather default; base vs arm one tree, 2,760/2,993; GATHER change needs two re-gathers; `--tag`; +/-6 noise floor; OMR-NED symmetric; print check = crop with a ruler; reach before accuracy; refusal test positive control; shared record is a snapshot) | MOVED to `docs/measuring.md` §2 (blind-tile conventions from memory/DECISIONS added). "Every test is GATHER+ADJUDICATE only" KEPT (§3). The 1.6/1.6b quotes shortened; the full quotes are in DECISIONS 2026-09-30 and ROADMAP 1.6b. Small/full re-gather commands MOVED to `docs/running.md` §3. |
| **§6c Tests** (fast tier, durations.json rule, measure_durations, no source-text asserts, mutation batteries archived, don't edit tools/ mid-run, starved run) | MOVED to `docs/measuring.md` §3 (worker cap added); two-line summary KEPT (§6 Tests). |
| **§7 Flags** (table doc, four verdicts, "at most 15", deny/allow-list convention, detector knobs) | MOVED to `docs/measuring.md` §4; pointer KEPT (§8). |
| **§8 Data not off the page** (library 289/29/1,745, source_kind, ingest, 54 unindexed; rosters; dossiers 97; fact sheet 29-44 of ~55; conventions registry 114/44) | MOVED to `docs/data-sources.md`. "114 entries, 44 read by nothing" DROPPED (the `conventions` check derives both). The other counts kept as orientation (catalog sizes, not measurements). |
| **§9 Detector** (class deletion last layer / 127 vs 0 beams / option A; never erase staff lines; routing 147 pages / `image_type` 7 of 289; 208 classes spelled twice / 157 canonical; unboxed = background; labeling UI, pre-fill 0.915, hand truth) | MOVED to `docs/detector.md` (round-5 surgery, augmentation and stem-finder facts from DECISIONS/memory added). One-paragraph summary KEPT (§7). |
| **§10 Page facts**: whole rest = bar; dot window; beam/stem geometry; arc over, hairpin between; tie interval 0.168/0.435; key/meter change on every staff; cautionary meter; carry holds until printed return / label the switch / weighed not gated; stems up-right down-left 96/96; middle-line convention | MOVED to `docs/page-facts.md` §1-2 with FINDINGS paths added for the figures. The five that cost lanes weekly KEPT in §5. |
| §10 page truth is not an encoding truth | MOVED to `docs/page-facts.md` §2. |
| §10 two witnesses off one raster fall silent together | MOVED to `docs/page-facts.md` §2; one line KEPT (§5). |
| §10 cell pad 4/6 spaces, `glyph_owner` contest drops the loser; ledger lines name the owner; no far note without a ledger; hairpin under its staff | MOVED to `docs/page-facts.md` §3 (ledgers) and §1 (hairpin); ledger rule KEPT (§5). |
| §10 measure LOCALLY (Litolff 7 px wander, ~5%, ROADMAP 2.48) | MOVED to `docs/page-facts.md` §3; KEPT one line (§5). |
| §10 cell index restarts per system; canonical frame can't answer cross-staff | MOVED to `docs/page-facts.md` §3; cell-index line KEPT (§5). |
| §10 Litolff MERGES / Breitkopf SHATTERS (46 of 180; a third of stemless heads are barlines; 1.3 sp width floor 0/103) | MOVED to `docs/page-facts.md` §3 with FINDINGS paths; KEPT one line (§5). |
| §10 label lexicon (global aliases, derived cross products, `Tp.`, `Basso.`, 29 of 29 unlabeled) | MOVED to `docs/page-facts.md` §4 (2.94 worn-label rule added). |
| §10 condensed count is an encoding property; identity loss is placement; `Violoncello e Basso` convention (Sean 2026-09-22) | MOVED to `docs/page-facts.md` §4 (2.93 confirmation and 2.95 brace rule added); KEPT one line (§5). |
| **§11 Web app internals** (auth, DB no migrations, storage, Verovio, payments/nginx, Maestro, frontend build, stubs, audiveris retired) | MOVED to `docs/running.md` §5 (the 5060 `ERR_UNSAFE_PORT` note from memory added). |
| **§12 Where things are** (tree listing + deployment) | KEPT, compressed (§8 block); deployment line MOVED to `docs/running.md` §6. |
| **§13 Sessions in parallel** (worktree off origin/main, no checkout of a dirty file, no bare stash, fence by function name, claim a ROADMAP number, cloud session role, lane report is a ledger, how a session ends) | KEPT (§6 "Where" and "Landing"), tightened. The cloud-session sentence MOVED to `docs/running.md` §1. |

## Added, from DECISIONS 2026-10-12/13 (not in the old file)

| rule | where |
|---|---|
| READ / GUESSED (blue `#1F6FEB`, with candidates) / UNREAD; nothing uncertain written unmarked | CLAUDE.md §4; `docs/staged-internals.md` §4 (INFER). |
| Eighth only on evidence; the bar sum confirms, never supplies | CLAUDE.md §4; `docs/page-facts.md` §1. |
| Written value from the shape; a tuplet only where its marking is seen | CLAUDE.md §4; `docs/page-facts.md` §1. |
| Only a clef before key accidentals; key accidentals in fixed order | CLAUDE.md §4; `docs/page-facts.md` §2. |
| 95% is not fixed; the bar is the cost of error | CLAUDE.md §4. |
| Lean lanes and machine-load caps (2-3 lanes, one gather at a time, 4 test workers, push at milestones, small agents for landings/recording) | CLAUDE.md §6. The numbers are as Sean gave them for this housekeeping (2026-10-13); the "two lanes, Sonnet, machine time is free" half is ROADMAP "How to work" (DECISIONS 2026-09-28/29, 2026-10-01). No single DECISIONS line holds the 2026-10-13 numbers; if Sean wants one, append it. |
| Brace names the whole group (2.95); cello+bass confirmed on the five Litolff staves (2.93); worn label from roster+gap+one neighbour (2.94); whole-bar rest sized to `<time>` (2.98) | `docs/page-facts.md`. |

## Dropped outright

| what | why |
|---|---|
| "It is kept under 6,000 words" | replaced by the new header. |
| "Stubs: none" | the line itself said `adjudicate.stubs()` is the truth. |
| Conventions registry "114 entries", "44 are read by nothing" | derived by the `conventions` check (rule 9: a tool's number is not restated). |
| INFER "25 of 25" print verification of `collapse_slot_index_to_family_block` | a measurement; lives in `benchmarks/omr-infer-default-2026-09/FINDINGS.md`. The rule's ALWAYS_ON status is kept in `docs/staged-internals.md`. |
| The direction-word reader timing history (267 s before the token cap) | kept once in `docs/running.md` as operating guidance; the measurement is in `benchmarks/omr-direction-text-2026-09/FINDINGS.md`. |
| §5b "There is no `--dossier` and there will not be one" (duplicate) | kept once, in `docs/running.md` §2 and `docs/data-sources.md`; removed from CLAUDE.md. |
| §6b full Sean quotes on the small re-gather (1.6/1.6b) | the quotes are in DECISIONS 2026-09-30 and ROADMAP 1.6b; `docs/measuring.md` keeps the first one. |
| §5a "(121 commits from 2026-10-01 on the 2026-10-07 audit)" | kept in `docs/running.md`; a dated measurement that will go stale, also in `docs/audit-2026-10-07-code-cleaning.md`. |
| The "Each of these has cost at least one lane and is still true" framing of §10 | kept as the header of `docs/page-facts.md`. |
