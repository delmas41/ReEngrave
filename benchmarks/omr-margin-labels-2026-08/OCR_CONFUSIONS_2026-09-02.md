# OCR letter-confusions in the margin-label lexicon — what is safe to fold

**2026-09-02.** A labelling batch surfaced `Yiolino II.` — a printed
`Violino II.` whose leading **V was OCR'd as Y** — dropped unmatched by
`instruments.lookup`. This asks whether the margin-label matcher should tolerate
common OCR letter-confusions (V/Y, l/I/1, rn/m, O/0), without loosening it
enough to create false instrument resolutions. The lexicon's precision is
load-bearing: a wrong high-confidence read pins a staff to the wrong part
(`dossier.join_parts_to_slots`), the failure the `Tr. Alt.`->Alto history warns
of.

## What already existed

The fold mechanism was already there (`instruments._OCR_FOLD`, since 2026-08-28)
and already covered **two** of the four families the request names: the **i/l/1**
stroke group and **O/0**. It is applied to both the alias and the candidate, as
a **fallback after exact matching fails**, and any match it produces is marked
`ocr_folded` -> **`confidence == "low"`**. So the real question is only **V/Y**
(add it) and **rn/m** (a two-character confusion a 1:1 fold cannot express).

## The decision: add V/Y as a fold, refuse the rest

`y -> v`, one line. Measured safe and sufficient for the reported case.

| input | before | after |
|---|---|---|
| `Yiolino II.` | — | Violin (low) |
| `Yiola` | — | Viola (low) |
| `Yioloncello` | — | Cello (low) |
| `Yni` | — | Violin (low) |
| `Tympani` | Timpani (high) | Timpani (high) — unchanged |
| `Xylophone` | Percussion (high) | Percussion (high) — unchanged |

**Why V/Y is safe.** `y` is rare in the vocabulary: only `tympani` and
`xylophone` carry one, and both resolve on the **exact pass, before the fold is
ever reached**, so folding `y->v` collides with nothing. Measured:

- **0** collisions over all **260 aliases** and every margin-label corpus truth
  string (`probe_ocr_fold.py`);
- **0** net-new cross-instrument alias collisions the fold introduces
  (`test_instruments.test_the_ocr_fold_is_only_the_reviewed_rare_confusions`);
- **0** change to any reader string in the corpora, so the benchmark is
  **unchanged**: text-layer vs Surya stays 25/24 agree, **0 disagree**, 30/23
  recovered, 0/1 missed.

The corpora contain **no V/Y case**, so this is a real-world fix, not a
benchmark one — its corpus effect is provably *nil in both directions*.

## What was refused, and why it costs two real reads

The corpora's own unrecovered reads are mostly **clipping** (`arinetti in C`,
`ani in C.G`, `bombe in C` — first letters cut off, a crop problem, not a
matching one). The two that are single-substitutions are **not** in the
request's V/Y set:

| unread | is | confusion |
|---|---|---|
| `Fug.` | `Fag.` (Bassoon) | **a/u** |
| `Oh.` | `Ob.` (Oboe) | **b/h** |

Taking these needs **common-letter** folds. Those are refused:

- **As a global fold**, folding a/u or b/h merges names and widens the wild
  match surface — `b/h` folds `horn->born`, `harp->barp`; `a` is in a large
  fraction of aliases. `b/h` already shows a flagged collision in the probe.
- **`ob` is 2 chars and `fag` is 3** — the danger zone. The vocabulary has 42
  aliases of <=3 chars (`cb`/`db`/`kb`/`tb`, `tp`/`tr`/`tb`, `vc`/`vl`, ...),
  dense in edit-distance-1 space. A general edit-distance-1 matcher over them is
  catastrophic.

A **gated single-substitution matcher** (whole token == an alias after one
*confusable* substitution, min length 3, pairs {v/y, a/u}) was prototyped and
measured (`probe_gated_matcher.py`): it is collision-free on the vocabulary
(0 clean-input fires, 0 perturbation collisions) and would additionally recover
`Fug.`->Bassoon. It was **not adopted**: its *only* gain over the one-line fold
is that single corpus read, bought with a new matching mechanism **and** the
common-letter `a/u` pair whose safety rests on this small corpus. `Oh.` needs
the 2-char `ob` and stays out regardless. For a low-priority precision-sensitive
path, the fold is the right size. The prototype is kept as the documented next
lever if the unread tail ever grows.

**rn/m** is multi-char (no 1:1 fold), has no corpus evidence, and would ride on
the rejected matcher. Left out.

## Files

| file | what |
|---|---|
| `probe_ocr_fold.py` | global-fold collision + recall probe, per candidate pair |
| `probe_single_sub.py` | intrinsic alias<->alias collision test for a gated matcher |
| `probe_gated_matcher.py` | the gated single-sub prototype, recall + perturbation stress |

Ship: `instruments._OCR_FOLD` gains `"y": "v"`; three tests in
`test_instruments.py` (the V/Y family, the two y-instruments, and the pinned
fold set).
