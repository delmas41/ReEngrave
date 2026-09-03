# Grace-notehead batch 1 — the calibration sitting (2026-09-03)

**Survey Row 2's first cells.** 104 draw-from-scratch cells from two
grace-rich works chosen by their REFERENCES (the join that mattered: a
reference proving the work prints grace notes AND a scanned edition on
disk):

| tag | edition | pages (1-based) | cells | reference grace count |
|---|---|---|--:|--:|
| `mahler5` | Peters 3087b local scan | 4–14, 30–38 | 72 | mvt1 273 / mvt2 291 |
| `mozart40` | Breitkopf & Härtel 1880, IMSLP 984555 | 3–9 | 32 | mvt1 27 / mvt2 30 |

**What this sitting is, honestly.** `grace_score.py` cannot yet put
grace-rich cells in front of you: on this very pool it flags 10/104 cells
and the audited top hits are dots and smudge fragments, not graces — the
selector's bands are PROVISIONAL until the first real labels exist
(`../omr-labeling-survey-2026-09/GRACE_SELECTOR_2026-09-03.md`). So this is
a **sweep**: most cells hold no grace note, Tab records the inspection
(`inspected_passes` — that emptiness is coverage, not waste), and **every
real grace head you click is the first ground truth the selector and the
pre-fill size-veto calibrate against.**

Single-symbol pass (`batch_config.json`): one slot, small black notehead,
on-line/in-space decided by the snap, click places a 0.62-space box. The
cell opens **already in draw mode** — just click the heads; Esc steps out.
⚠️ The ledger-zone snap parity bug Sean reported is being fixed in a
parallel session — if a ledger-line grace snaps to the wrong variant, fix
it with `c` rather than fighting the click.

**Box / skip:** box grace-note HEADS only (the small ones, ~2/3 size);
never the slash, stem, flag, or any full-size head; a cell too bled to
read → skip the cell.

**After the sitting:** the verdicts calibrate `grace_score.py`'s bands
(then a targeted, reference-measure-guided cut makes sitting 2 dense), and
conversion waits for the campaign rule — this cell set exports only when
its passes are complete.

Cut with `select_cells_orchestral` (600 dpi default); cell PNGs are
gitignored and live in the worktree that cut them
(`weight-generalization-publishers-548504`); `recut_cells.py` can
re-materialize them from `cells.json` if frames still agree.
