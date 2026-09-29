# Graft training-set audit — what actually reached production

**ANSWER:** The shipped graft (`hollow-graft-shift09-2026-09-04.pt`, commit
`0e9f005b`) trained its 7 kept notehead rows on a corpus that DOES include
hollow, hollow2, and 3 of 4 hollow3 publishers (via their round-3 "complete"
versions) — but keeps **only those 7 rows**; every other class the round-3/4
labeling added (rests, accidentals, slurs, ties, clefs — **≥1,772 boxes** across
v13–v21) is **discarded**, restored instead from the pre-completion 09-03
checkpoint. **Jurgenson/Tchaikovsky (v12, 18 cells / 48 boxes) never reached
the graft at all** — never admitted to `catalog-versions.txt`, used once in an
abandoned, unshipped cloud ablation that measured it harmful. Current Litolff
p1 half-notehead figure for the production weights: **31** of 68 printed
(`hollow_eval_shift09.json` / `gate_all_summary.json`, 2026-09-04, unchanged
since — no run has re-measured it).

## The graft mechanics (`merge_class_head.py`, per `docs/handoff-2026-09-04-round5-class-collapse.md:69-75`)

```
--ft omr-weights/round5-sweep/distill25/epoch0.pt          (donor: 7 rows)
--base omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt  (donor: 201 rows)
--keep noteheadHalfOnLine noteheadHalfInSpace noteheadWholeOnLine
       noteheadWholeInSpace noteheadHalfOnLineSmall noteheadHalfInSpaceSmall
       noteheadWhole
--bias-shift 0.9
```
`--keep` is explicit by name (`merge_class_head.py:118-129`) — the 201
restored rows come from `--base` unconditionally, **never** from anything
`distill25` learned, regardless of what `--labels-root` (informational only
here) contains.

## 1–2. Version → graft table

| campaign | version(s) | admitted 09-04? | in graft's 7 kept rows | in graft's 201 restored rows |
|---|---|---|---|---|
| hollow-2026-08 (Beet5/Bolero) | v7 → superseded by **v13** (25c/34b) | yes | **yes** — v13 is in `catalog-versions.txt`, feeds `distill25`'s images | no (comes from 09-03 base, pre-dates v13) |
| hollow2 litolff-hires | v8(part) → **v14** (54c/320b) | yes | **yes** | no |
| hollow2 peters-mahler5 | v8(part) → **v15** (54c/250b) | yes | **yes** | no |
| hollow2 eulenburg-scheherazade | v8(part) → **v16** (55c/296b) | yes | **yes** | no |
| hollow2 simrock-dvorak9 | v8(part) → **v17** (13c/47b) + **v22** (110c/759b, round 4) | yes | **yes** | no |
| hollow2 breitkopf-brahms1 | v8(part) → **v18** (56c/605b) | yes | **yes** | no |
| hollow3 universal-mahler1 | v9 (37c/69b) → **v19** (37c/126b) | yes | **yes** | no |
| hollow3 novello-elgar1 | v10 (15c/23b) → **v20** (15c/39b) | yes | **yes** | no |
| hollow3 durand-lamer | v11 (11c/28b) → **v21** (11c/55b) | yes | **yes** | no |
| hollow3 jurgenson-tchaikovsky1 | **v12** (18c/48b) | **NO** | **no** | no |
| dense base | v1–v4 | yes (always) | contributes, discarded like all non-notehead | **yes** — 09-03 base was itself trained on v1–v4(2×)+v7+v8 |
| clef | v5/v6 (15c/134b + 47c/572b) | no (parked, unrelated) | no | no |

"Yes" for the 7-row donor means: the version's *images* were in the corpus
`build_rehearsal_versions.py`/round-3/4 fine-tunes trained on, and `distill25`
(the specific epoch-0 checkpoint grafted) is one of those fine-tunes — but its
surviving contribution to the shipped file is bounded to notehead detections;
`distill25` itself collapsed to 12 classes (`ROUND5_METHOD_2026-09-04.md:77`),
so v19/v20/v21's rest/accidental/slur/tie boxes taught it nothing that
transfers. **v12 is the only hollow-campaign version with zero causal path
into the shipped checkpoint** — `catalog-versions.txt` comment (2026-09-03/04
block) states it "stays out on the cloud ablation that measured it HALVING the
half-note gain"; that ablation ran once, in the now-destroyed cloud box
(`CLOUD_HANDOFF.md`, commit `99696a25`), and was never shipped or re-admitted.

## 3. Classes grafted

Exactly the 7 named in `--keep` above: **`noteheadHalfOnLine`,
`noteheadHalfInSpace`, `noteheadWholeOnLine`, `noteheadWholeInSpace`,
`noteheadHalfOnLineSmall`, `noteheadHalfInSpaceSmall`, `noteheadWhole`** — both
`noteheadHalf*` and `noteheadWhole*` families are among them, confirmed by
`class_inventory_round5_graft.json`. All other 201 of 208 classes (including
`noteheadWholeOnLineSmall`, `noteheadWholeInSpaceSmall`, and every
`noteheadDoubleWhole*`) are restored from the 09-03 base, untouched by the
hollow campaigns.

## 4. Labeled but never trained on

- **v12 (Jurgenson Tchaikovsky 1, lowres): 18 cells / 48 boxes** — never in
  `catalog-versions.txt`; the one training run that touched it (`cloud-2048`
  ablation, `CLOUD_HANDOFF.md`) was destroyed and never shipped.
- **v5/v6 (clef): 15c/134b + 47c/572b** — parked by `catalog-versions.txt`'s
  own header (density-narrowing risk), unrelated to the hollow question but
  the same pattern: labeled, never fed a shipped checkpoint.
- **The round-3/4 completion delta on v13–v21: 320 cells / 1,772 boxes total**
  (rests, accidentals, slurs, ties, clefs, dynamics added on top of the
  original hollow/hollow2/hollow3 notehead-only boxes) — these boxes *were*
  read by `distill25`'s training step, but every class they teach besides the
  7 kept ones is thrown away by the graft's `--base` restore. Functionally
  equivalent to unused: no shipped weight reflects them.

## 5. The open gate

`hollow_eval_shift09.json` / `gate_all_summary.json` (2026-09-04, commit
`c20928c5`, unchanged since — `906f4b05` same day retried real DSv2 rehearsal
and closed that lever without touching these files): production graft reads
**31 half-noteheads** on Litolff p.1 (`noteheadHalfOnLine` 5 +
`noteheadHalfInSpace` 26) against **68 printed** — up from the pre-graft
09-03 production's 27, still well short of the plan's target. `ROADMAP.md`
2.4b cites this same 31 figure as current.
