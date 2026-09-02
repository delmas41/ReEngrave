# Audiveris GRID — the mature engine's system grouping (Phase 1C, part 3)

2026-09-01. Audiveris deep-dive (sub-agent). Official repo only
(audiveris.github.io/audiveris, AGPL-3.0). Tags: (doc)/(src)/(not found).

## The algorithm — a peak graph, not a barline test

GRID is step 4 of 20, before any note/symbol recognition — systems committed
from binarized ink alone (same architectural bet as ReEngrave). (src:
`OmrStep.java` — `GRID("Retrieve staff lines, barlines, systems & parts")`.)

1. Project each staff's interior onto x; peaks = barline/brace/bracket/stem
   candidates (`StaffProjector`).
2. Every peak is a vertex in a sheet-level graph; a vertical alignment between a
   peak in one staff and one in the next staff becomes an edge.
3. Each alignment is tested for **actual ink in the gap** — `PeakGraph.checkConnection`
   builds a corridor and measures `gap` and `whiteRatio`, defaults
   `maxConnectionGap=1.0` interline, `maxConnectionWhiteRatio=0.25`,
   `minConnectionGrade=0.5`. **Functionally ReEngrave's gap_bridging_counts.**
4. Systems = **transitive closure over adjacent-staff connections**
   (`PeakGraph.getSystemTops`). **There is no vertical-gap-distance heuristic
   anywhere** — confirms our finding that gap distance cannot separate systems,
   in the design of the most mature open-source OMR engine.

## The left systemic barline is the primary cue and must be fully connected

(src, `BarColumn` javadoc) The **start column** "indicates the left side of a
system, just before the staff lines begin"; is **full** when it has a peak for
every staff; **fully-connected** when full and all peaks linked by concrete
connections; "The system start column must be a fully-connected column."

Interior barlines are handled by THREE distinct rules:

| rule | requirement |
|---|---|
| start (systemic) column | full AND fully-connected |
| columns right of start | **full only** — ink continuity across gaps NOT required (`purgePartialColumns`) |
| any peak in a multi-staff system | ≥1 graph edge (alignment suffices) |

So Audiveris **tolerates interior barlines broken between families** (alignment
is enough), but system grouping still needs a connected chain — a damaged left
barline splits the system. First connection for a pair must be within
`maxFirstConnectionXOffset=2.0` interlines of the left edge, unless a connection
exists at the two staves' LAST peaks (the closing barline) — a fallback we lack.

## Brackets/braces do NOT determine system extent — they refine PARTS

Execution order proves it: `peakGraph.buildSystems()` runs FIRST ("until systems
are known"); every brace/bracket routine afterward iterates known systems.
Brackets searched "on the left of the starting column"; "braces in left margin
drive the gathering of staves into **parts**." Maintainer's own comment: "Code
in this method is rather fragile."

## Failure handling

- No automatic over-split recovery — `SystemMergeTask` is a manual UI op; doc
  offers merge only, no split.
- Orchestral accommodation: `largeSystemStaffCount=4`; `purgeExtendingPeaks`
  skips systems at/above it ("We cannot ruin a whole column of large system").
- `SystemManager` javadoc: for stacked systems "there is no way to always find
  out a precise border" → dispatches shareable entities to both.
- **No cross-system staff-count consistency check** (only indentation, for
  movement boundaries).
- No GRID regression tests; no published system-detection accuracy.
- System dividers not used (not in the grid package or OmrShape vocabulary).
- Cross-system part identity via **logical parts** collation on staff-count +
  staff-line-count + part names — directly analogous to ReEngrave slot identity.

**Decisive negative for us** (src): `PeakGraph.createSystems()` consumes only the
connection-derived `systemTops`; no gap-distance stage exists.

**Cost of failure** (INFERENCE grounded in src): `PeakGraph.buildSystems` throws
`StepException("No system found")` and calls `invalidate()` — a grouping failure
costs the ENTIRE sheet. (External: Torras et al. IJDAR 2024 measured Audiveris
76.9% measure coverage over COMREF, misses attributed to whole-page no-output.)

## LEGATO 2 — current SOTA, directly relevant

(arXiv:2607.05769) First large OMR model to work **system-by-system**: YOLOv8m
segments systems per page, finetuned on **1,024 manually annotated pages** from
single-staff to "complex orchestral arrangements". System detection
mAP50:95 **0.804**, mAP50 0.990. **No per-layout breakdown → still no published
number for 18+ staff pages.** Recogniser degrades gracefully under injected
merge/delete errors (Appendix C.2). **Weights not released** (HF has only v1
`guangyangmusic/legato-small`, no layout stage). We already cross-check against
LEGATO v1 (`benchmarks/.../legato_crosscheck.py`, AGPL, quarantined).

## Our detector's blind spot (local observation)

`tools/omr/training/deepscores_classes.py`: the DSv2 snapshot has `brace` and
`staff`, but the only bracket classes are `tupletBracket` / `ottavaBracket` —
**no system-bracket class, no barline class.** The symbol SmartScore and
capella-scan rely on most for grouping is one our detector has no label for.
(Grouping runs before YOLO anyway — repo-state §1.4 — so a bracket detector
would be classical-CV in the left margin, à la Audiveris.)
