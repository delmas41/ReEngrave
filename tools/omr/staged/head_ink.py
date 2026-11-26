"""ONE head under a notehead box, and its fill read on that head -- ROADMAP 2.220 milestone 1 (STAGED GATHER measurement; decides nothing).

Flag `OMR_FILL_FROM_STROKES` (default ON since 2026-10-29): `gather.gather_head_ink` files one `Q.HEAD_INK` row per notehead-classed detector box;
nothing reads it yet, so flag on writes a byte-identical exported file.

CAUSE (benchmarks/ink-map-fill-2026-10/FINDINGS.md): fill is read inside the DETECTOR's box. Outside 1.1-1.9 x 0.9-1.8 sp, 2.148 files
`fill null, not_head_sized` and the detector's black class is written unread; inside it, a box holding an ff, a flag or a sharp reads
"hollow" on the slit (Sean's 2.220 tiles 2, 3, 6: 0.50 / 0.52 / 0.70). So the question is first "is this box ONE head?" and only then
"is that head hollow?" (fix A, DECISIONS 2026-10-28).

CONVENTION ASSUMED: a notehead is an oval about one staff space tall and 1.3-1.4 spaces wide (benchmarks/omr-notehead-width-2026-09); a
hollow head is one whose own ink holds white inside (2.148). A staff line is a row of ink across most of a window 3 sp either side
(2.164's `head_oval._line_rows`); a ledger, a row a horizontal run longer than any head (`LEDGER_MIN_SPACES`) crosses. WHAT WOULD FALSIFY IT: a real head Sean
values whose ink is wider than `MAX_WIDTH_SPACES` (a cluster drawn as one), or a half whose slit closes on the page raster.
NOT CONFIRMED beyond the two acceptance plates.

THE PAGE RASTER, NOTHING ERASED (Sean 2026-10-28, "rebuild this way"; 2.159: the cell raster merges a part-boxed head with its stem and
the next line). In a window around the box:
  1. bare line pixels out, read LOCALLY at this x: a run of ink lying wholly on a line's rows is a line; a line THICKENED by a head's
     outline is kept whole (2.164's `_kept_rows`, lesson 10: a line through a half's hole no longer fills the slit);
  2. stems are left in (a vertical opening also takes the solid column through a merged stacked chord); a stem only adds its hair
     width to the head's run of columns, and the head's rows come from the run's middle columns;
  3. the head = the run of HEAD-TALL columns (2.164's span measure on the cleaned ink: a slur or tie touching the head is thin and is not)
     over the box's core; the TRIMMED box is those columns and the rows their spans cover (fix D: an extent, never a centroid;
     window-stable on 2.115's tile 13, `test_head_ink_2_220`);
  4. not ONE head (`not_one_head`) where the trimmed ink is wider / taller / smaller than a head, or where an accidental / key / flag /
     dynamic box of the same cell holds `FOREIGN_SHARE` of it; a column two heads tall over a head-sized box is clipped to the box's rows
     first (fix C, `stack_clipped`);
  5. fill: 2.148's slit (`gather.head_interior_white`, unchanged, cut 0.18 / 0.06) on the TRIMMED box of the cleaned raster, and 2.23's
     centre/ring window (`notehead_ink_under`) beside it, and 2.164's oval width -- all three filed, the slit decides the producer's value.

PURE: numpy + cv2; the slit and window functions are passed in by the caller (they live in `gather.py`).
"""
import os
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

ENV = "OMR_FILL_FROM_STROKES"

#: How far past the detector's box the head's ink is looked for (a box drawn off its own head, 2.115's part-boxed heads).
SLACK_SPACES = 0.5
#: A ledger: a horizontal run at least this long (a head is <= ~1.5 sp wide on its ink; a ledger ~1.8-2.5 sp).
LEDGER_MIN_SPACES = 1.7
#: How far above / below the box the crop reaches (the staff-line window and the slack rows fit inside it).
ROW_REACH_SPACES = 2.0
#: The head's columns are the run of head-tall columns that overlaps the box's own core (its middle `CORE_SHARE` across) ...
CORE_SHARE = 0.4
#: ... read in the box's rows widened by this each way (2.115's tile 13: a box on the upper rim alone, the head 0.3 sp lower; a stack's next head is then clipped, fix C).
ROW_SLACK_SPACES = 0.45
#: A head row: its ink, first to last, spans at least this share of the head's run of columns.
ROW_WIDE_SHARE = 0.5
#: Fix A: ONE head's ink is at most this wide / tall, and at least `MIN_SPACES` both ways (filed with its margin; the consumer cuts).
#: A CUT-OFF MEASURED ON OUR TWO PLATES (CLAUDE §4: it may only narrow until another publisher confirms it): trimmed Litolff halves on
#: pp 4, 6 read 1.62 sp wide / 1.31 tall at the median (slanted ovals, page raster at 16 px a space); Sean's halves 5 and 7 trim to
#: 1.44 tall, his ff to 2.8 wide (FINDINGS ink-map-fill-2026-10, milestone 1).
MAX_WIDTH_SPACES = 1.75
MAX_HEIGHT_SPACES = 1.5
MIN_SPACES = 0.6
#: Fix C: the clip around a head-sized box's own rows when its column is two heads tall.
STACK_CLIP_SPACES = 0.15
#: Fix A: the head's ink lying inside a foreign box (accidental / key / flag / dynamic) whose own centre stands inside the trimmed head,
#: at this share or more, is that mark's.
FOREIGN_SHARE = 0.25
FOREIGN_PREFIXES = ("accidental", "key", "flag", "dynamic")
FOREIGN_EXCLUDE = ("dynamiccrescendohairpin", "dynamicdiminuendohairpin", "keyboard")
#: 2.148's cuts on the slit (`rhythm.HEAD_INTERIOR_WHITE_HOLLOW_MIN` / `_FILLED_MAX`), restated only for the producer's own margin.
SLIT_HOLLOW_MIN = 0.18
SLIT_FILLED_MAX = 0.06


TRIM_ENV = "OMR_HEAD_TRIM_LINE_ONLY"


def trim_line_only() -> bool:
    """Head-trim fix (2026-10-29, default ON): the END trim strips only a line's own UNDILATED rows, at most one locally measured
    line thickness per end (the 1 px dilations of `_line_rows` and of the ledger opening shaved ~a quarter off a head in a space
    on Litolff, 15.75 px/sp)."""
    return os.environ.get(TRIM_ENV, "1").strip().lower() not in ("0", "false", "no", "off", "")


TRIM_V2_ENV = "OMR_HEAD_TRIM_LINE_ONLY_V2"
#: Head-trim fix 2 (2026-10-29, default ON, Sean "Let's go with 1.6 for now"; explicit 0/false/no/off disables; needs `OMR_HEAD_TRIM_LINE_ONLY` too): the height cap of a head under the line-only trim.
#: 1.5 sp was set against heads the dilated trim shaved by 1-2 px a side; unshaved, a tilted hollow head on Litolff (15.75 px/sp)
#: measures 1.52-1.59 sp (Litolff p4+p6: 46 heads moved one_head -> too_tall), the heights have their valley at ~1.6-1.7 and
#: Brahms never reaches 1.55. Measured in benchmarks/shared-ink-map-2026-10/FINDINGS.md "head trim fix 2".
MAX_HEIGHT_SPACES_V2 = 1.6


def trim_line_only_v2() -> bool:
    return os.environ.get(TRIM_V2_ENV, "1").strip().lower() not in ("0", "false", "no", "off", "") and trim_line_only()


def enabled() -> bool:
    return os.environ.get(ENV, "1").strip().lower() not in ("0", "false", "no", "off", "")


OWN_ROWS_ENV = "OMR_HEAD_OWN_ROWS"


def own_rows() -> bool:
    """ROADMAP 2.327 (c), default OFF (built OFF: the shared lane report compares OFF and ON on one tree): the trimmed head's rows end
    at its own rim -- end rows holding no ink across the head's middle are paper beside or below it, never the head's."""
    return os.environ.get(OWN_ROWS_ENV, "0").strip().lower() in ("1", "true", "yes", "on")


OWN_INK_ENV = "OMR_HEAD_OWN_INK"


def own_ink() -> bool:
    """ROADMAP 2.355, default OFF (built OFF, Sean asleep; explicit 1/true/yes/on enables): the head's own ink is read from the head, not from
    its stem or a stroke beside it that does not touch it.

    As a musician says it: a black head is black whatever touches its edge; the stem is not the head; the head is the ink that crosses its
    own middle. NEVER fill read off the paper between a head and its stem; never a stroke that does not touch the head counted in its width.

    CAUSE (trace 2026-11-26, `/private/tmp/claude-501/trace-head-ink/`): of 625 heads Sean vouched for, 51 black Brahms heads abstained
    "readers split" because the slit counted the 2-3 px paper wedge between the head and its stem (the stem stands inside the slit's middle
    columns once the trimmed box takes the stem's hair width); 8 real heads read "too wide" with a slur end or stem stub counted in their
    columns. The stem is found the way the stroke map defines one (`stroke_map.V_MIN_SPACES` tall, at most `STEM_THIN_SPACES` wide) --
    measured here at the head's own x on the page raster, because the page stem reader (`page_stems`) files AFTER this GATHER reader."""
    return os.environ.get(OWN_INK_ENV, "0").strip().lower() in ("1", "true", "yes", "on")


def _stem_columns(clean: Any, ex0: int, ex1: int, ey0: int, ey1: int, sp: float) -> List[Tuple[int, int]]:
    """PURE. The column bands of the head's box [ex0, ex1) x [ey0, ey1) (crop frame) that are a STEM: a column whose ink runs on unbroken out of
    the head's top or bottom row, in all at least `stroke_map.V_MIN_SPACES` tall, whose run outside the head is thin (at most
    `stroke_map.STEM_THIN_SPACES` across) for at least `stroke_map.STEM_PART_MIN_SPACES` -- the stroke map's own words for a stem."""
    import numpy as np
    from .stroke_map import STEM_PART_MIN_SPACES, STEM_THIN_SPACES, V_MIN_SPACES
    H = clean.shape[0]
    vmin, thin = V_MIN_SPACES * sp, STEM_THIN_SPACES * sp
    bands: List[Tuple[int, int]] = []
    for side in ("up", "down"):
        cand = np.zeros(ex1 - ex0, bool)
        for c in range(ex0, ex1):
            col = clean[:, c]
            if side == "up":
                if ey0 - 1 < 0 or not col[ey0 - 1]:
                    continue
                y, n_out = ey0 - 1, 0
                while y >= 0 and col[y]:
                    n_out += 1
                    y -= 1
                y, n_in = ey0, 0
                while y < ey1 and col[y]:
                    n_in += 1
                    y += 1
            else:
                if ey1 >= H or not col[ey1]:
                    continue
                y, n_out = ey1, 0
                while y < H and col[y]:
                    n_out += 1
                    y += 1
                y, n_in = ey1 - 1, 0
                while y >= ey0 and col[y]:
                    n_in += 1
                    y -= 1
            cand[c - ex0] = n_out + n_in >= vmin
        c = 0
        while c < len(cand):
            if not cand[c]:
                c += 1
                continue
            s = c
            while c < len(cand) and cand[c]:
                c += 1
            b0, b1 = ex0 + s, ex0 + c
            # walking out of the head row by row through the band: the stem is the part of the run that is THIN (at most
            # `STEM_THIN_SPACES` across) for at least `STEM_PART_MIN_SPACES` -- "a thin part shorter than this is an oval's tip or a stem's
            # stub" (stroke_map) -- so a second head stacked on this one (as wide as a head) is passed through, and the stem beyond it found
            thin_rows, l_min, r_max = 0, None, None
            for k in range(1, H + 1):
                yy = ey0 - k if side == "up" else ey1 - 1 + k
                if yy < 0 or yy >= H:
                    break
                row = clean[yy]
                xs = np.nonzero(row[b0:b1])[0]
                if not len(xs):
                    break
                segs = []
                j = b0 + int(xs[0])
                while j < b1:
                    if not row[j]:
                        j += 1
                        continue
                    l = j
                    while l - 1 >= 0 and row[l - 1]:
                        l -= 1
                    r = j
                    while r + 1 < len(row) and row[r + 1]:
                        r += 1
                    segs.append((l, r))
                    j = r + 1
                narrow = [(l, r) for l, r in segs if r - l + 1 <= thin]
                if narrow:
                    thin_rows += 1
                    l_min = min([l_min] + [l for l, _ in narrow] if l_min is not None else [l for l, _ in narrow])
                    r_max = max([r_max] + [r for _, r in narrow] if r_max is not None else [r for _, r in narrow])
            if thin_rows >= STEM_PART_MIN_SPACES * sp and l_min is not None and r_max + 1 - l_min <= thin:
                bands.append((max(ex0, l_min), min(ex1, r_max + 1)))
    return sorted(set(b for b in bands if b[1] > b[0]))


def slit_rows_share(ink: Any, stem: Any) -> Tuple[float, int]:
    """PURE. 2.148's slit (`gather.head_interior_white` `rows_share`, the same rows 20-80%, columns 12-88%, white run >= 5% of the width) on the
    head's crop `ink` (bool, True = ink), where a white run counts only with HEAD ink, not stem ink (`stem`, bool, same shape), on both its
    ends: the paper between a head and its stem is not the head's inside. With no stem pixels it equals `rows_share` exactly."""
    import numpy as np
    hh, ww = ink.shape
    a, b = int(0.12 * ww), max(int(0.12 * ww) + 1, int(0.88 * ww))
    minrun = max(1, int(round(0.05 * ww)))
    n = hit = 0
    for yy in range(int(0.2 * hh), max(int(0.2 * hh) + 1, int(0.8 * hh))):
        r = ink[yy, a:b]
        st = stem[yy, a:b]
        xs = np.nonzero(r)[0]
        if len(xs) == 0:
            continue
        n += 1
        # the row's ink as segments; a segment that holds any stem pixel is the stem (with whatever of the head is fused to it)
        segs: List[Tuple[int, int, bool]] = []
        j = int(xs[0])
        while j <= xs[-1]:
            if not r[j]:
                j += 1
                continue
            s = j
            while j <= xs[-1] and r[j]:
                j += 1
            segs.append((s, j, bool(st[s:j].any())))
        ok = any(segs[q + 1][0] - segs[q][1] >= minrun and not segs[q][2] and not segs[q + 1][2] for q in range(len(segs) - 1))
        hit += ok
    return (hit / n if n else 0.0), n


def _own_ink(clean: Any, ex0: int, ex1: int, ey0: int, ey1: int, sp: float,
             core: Optional[Tuple[int, int]] = None) -> Tuple[Any, int, int, Any, Dict[str, Any]]:
    """ROADMAP 2.355 (`OMR_HEAD_OWN_INK`). The head's own ink inside its trimmed box [ex0, ex1) x [ey0, ey1) (crop frame):
      1. the head is the ink under the box's core that crosses its own middle: a stroke inside the box that does not reach the head's
         middle third of rows (a slur's end, a stub above it) or never comes under the box's core columns `core` (a mark beside the head
         that touches it only through a staff line we took out) is not the head and leaves the box -- joining goes by ink, never by box. A
         hollow head broken in two arcs keeps both: each arc runs over the core (its rim) and down the middle (its wall);
      2. the stem is not the head: the stem bands (`_stem_columns`) are returned as `stem` (the slit reads a white run that ends on the stem
         as the paper between the head and its stem, `slit_rows_share`), and `note["width_px"]` is the head's width without a stem band at
         its edge. The stem never leaves the slit's box: a Litolff half's stem is the wall of its hole (trace item 97).
    Returns (clean with the strokes of 1 taken out of the box, ex0, ex1, stem mask or None, note)."""
    import numpy as np
    from scipy import ndimage as nd
    note: Dict[str, Any] = {}
    h = ey1 - ey0
    sub = clean[ey0:ey1, ex0:ex1]
    lab, k = nd.label(sub, structure=np.ones((3, 3), bool))
    if k > 1:
        m0, m1 = int(h / 3.0), max(int(h / 3.0) + 1, int(round(2.0 * h / 3.0)))
        keep = set(int(v) for v in np.unique(lab[m0:m1]) if v)
        if core is not None:
            c0, c1 = max(0, core[0] - ex0), min(sub.shape[1], core[1] - ex0)
            if c1 > c0:
                under = set(int(v) for v in np.unique(lab[:, c0:c1]) if v)
                if keep & under:
                    keep &= under
        if keep:
            drop = np.isin(lab, [i for i in range(1, k + 1) if i not in keep])
            if drop.any():
                clean = clean.copy()
                clean[ey0:ey1, ex0:ex1] &= ~drop
                note["apart_px"] = int(drop.sum())
                cols = np.nonzero(clean[ey0:ey1, ex0:ex1].any(axis=0))[0]
                ex0, ex1 = ex0 + int(cols[0]), ex0 + int(cols[-1]) + 1
    bands = _stem_columns(clean, ex0, ex1, ey0, ey1, sp)
    note["_bands"] = bands
    stem = None
    if bands:
        stem = np.zeros_like(clean)
        for b0, b1 in bands:
            stem[ey0:ey1, b0:b1] = clean[ey0:ey1, b0:b1]
        note["stems"] = len(bands)
    return clean, ex0, ex1, stem, note


def width_without_stem(head: Any, ex0: int, ex1: int, bands: Sequence[Tuple[int, int]]) -> int:
    """PURE. The width in px of the head's ink `head` (bool crop) between columns [ex0, ex1), a stem band standing at either edge left out
    (the stem is not the head). The full width where nothing but stem is left."""
    import numpy as np
    w0, w1 = ex0, ex1
    for b0, b1 in bands:
        if b0 <= w0 + 1 and b1 < w1:
            w0 = b1
        elif b1 >= w1 - 1 and b0 > w0:
            w1 = b0
    cols = np.nonzero(head[:, w0:w1].any(axis=0))[0] if w1 > w0 else []
    return (int(cols[-1]) - int(cols[0]) + 1) if len(cols) else ex1 - ex0


def is_foreign_class(name: Optional[str]) -> bool:
    n = str(name or "").lower()
    return n.startswith(FOREIGN_PREFIXES) and not n.startswith(FOREIGN_EXCLUDE)


def _bare_line_pixels(ink: Any, line_rows: Any) -> Any:
    """Per column, the runs of ink lying WHOLLY on line rows (2.164's `_kept_rows`, vectorised): a bare line, not a head's edge."""
    import numpy as np
    H, W = ink.shape
    out = np.zeros_like(ink)
    if not line_rows.any():
        return out
    for c in range(W):
        col = ink[:, c]
        if not col.any():
            continue
        y = 0
        while y < H:
            if not col[y]:
                y += 1
                continue
            s = y
            while y < H and col[y]:
                y += 1
            if line_rows[s:y].all():
                out[s:y, c] = True
    return out


def trim_head(page_binary: Any, box: Sequence[float], space_px: float,
              foreign_boxes: Sequence[Sequence[float]] = ()) -> Optional[Dict[str, Any]]:
    """The head under the page box `box` = (x0, y0, x1, y1) on `page_binary` (0 = ink, staff lines in). Returns `clean` (bool crop, the
    head's neighbourhood with bare line pixels out), `origin` (crop x0, y0 on the page), `trimmed` [x0, y0, x1, y1] (page px),
    `extent_sp`, `stack_clipped`, `not_one_head` (None or why), `size_margin_sp`, `foreign_share`, `line_px_out`,
    `n_runs`; None off the raster or on a degenerate box."""
    import cv2
    import numpy as np
    from . import head_oval as HO
    if page_binary is None or getattr(page_binary, "ndim", 0) != 2 or not space_px or space_px <= 0:
        return None
    H, W = page_binary.shape
    sp = float(space_px)
    bx0, by0, bx1, by1 = (float(v) for v in box)
    if bx1 <= bx0 or by1 <= by0:
        return None
    x0, x1 = max(0, int(round(bx0 - SLACK_SPACES * sp))), min(W, int(round(bx1 + SLACK_SPACES * sp)))
    y0, y1 = max(0, int(round(by0 - ROW_REACH_SPACES * sp))), min(H, int(round(by1 + ROW_REACH_SPACES * sp)))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    lx0, lx1 = max(0, int(round(bx0 - HO.LINE_WINDOW_SPACES * sp))), min(W, int(round(bx1 + HO.LINE_WINDOW_SPACES * sp)))
    line_rows = HO._line_rows(np.asarray(page_binary[y0:y1, lx0:lx1]) == 0)
    ink = np.asarray(page_binary[y0:y1, x0:x1]) == 0
    # A LEDGER line is too short for the staff-line window: its rows are the rows a horizontal opening longer than any head keeps
    # (Litolff p2 tile 1: a half between two ledgers read 2.4 sp wide with them)
    kw = max(3, int(round(LEDGER_MIN_SPACES * sp)))
    hl = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, np.ones((1, kw), np.uint8)).any(axis=1)
    led = hl.copy()
    led[1:] |= hl[:-1]
    led[:-1] |= hl[1:]
    line_rows = line_rows | led
    line_core = None
    if trim_line_only():
        core = HO._line_rows(np.asarray(page_binary[y0:y1, lx0:lx1]) == 0, dilate=False) | hl
        runs_t = []
        k = 0
        while k < len(core):
            if core[k]:
                q = k
                while k < len(core) and core[k]:
                    k += 1
                runs_t.append(k - q)
            else:
                k += 1
        line_core = (core, max(1, int(np.median(runs_t))) if runs_t else 1)
    bare = _bare_line_pixels(ink, line_rows)
    a = ink & ~bare
    # Stems are NOT cut out: on a merged plate a vertical opening also takes the solid column through a stacked chord (Litolff p2 tile 1,
    # two halves and their ledgers), and a stem beside a head only adds its own hair width to the run of head-tall columns; the rows come
    # from the run's middle columns, so it never stretches the head.
    clean = a
    # The head's own columns (2.164's measure, read on the cleaned ink): a column is HEAD-TALL where its ink spans at least
    # `head_oval.HEAD_TALL_SPACES` within `head_oval.SPAN_WINDOW_SPACES`; a slur or tie touching the head is one thin stroke and is not.
    # The trimmed box is the run of head-tall columns over the box's core, and the rows those columns' spans cover.
    rb0, rb1 = max(0, int(round(by0 - ROW_SLACK_SPACES * sp)) - y0), min(clean.shape[0], int(round(by1 + ROW_SLACK_SPACES * sp)) - y0)
    sub = clean[rb0:rb1]
    win = HO.SPAN_WINDOW_SPACES * sp
    spans: List[Optional[Tuple[int, int]]] = []
    for c in range(sub.shape[1]):
        ys = np.nonzero(sub[:, c])[0]
        best, j = (None, 0.0), 0
        for i in range(len(ys)):
            while ys[i] - ys[j] > win:
                j += 1
            if ys[i] - ys[j] > best[1]:
                best = ((int(ys[j]), int(ys[i]) + 1), float(ys[i] - ys[j]))
        spans.append(best[0] if best[0] is not None and best[1] >= HO.HEAD_TALL_SPACES * sp else None)
    runs: List[Tuple[int, int]] = []
    c = 0
    while c < len(spans):
        if spans[c] is None:
            c += 1
            continue
        s0 = c
        while c < len(spans) and spans[c] is not None:
            c += 1
        runs.append((s0, c))
    cw = (bx1 - bx0) * (1 - CORE_SHARE) / 2.0
    kx0, kx1 = int(round(bx0 + cw)) - x0, max(int(round(bx0 + cw)) - x0 + 1, int(round(bx1 - cw)) - x0)
    over = [(min(r1, kx1) - max(r0, kx0), r0, r1) for r0, r1 in runs if min(r1, kx1) > max(r0, kx0)]
    out: Dict[str, Any] = {"origin": [x0, y0], "line_px_out": int(bare.sum()),
                           "n_runs": len(runs), "not_one_head": None, "stack_clipped": False}
    if not over:
        out.update(clean=clean, trimmed=None, extent_sp=None, not_one_head="no_head_ink", size_margin_sp=None, foreign_share=0.0)
        return out
    _o, ex0, ex1 = max(over)
    # The head's ROWS: rows whose ink, across the run's columns, reaches from one side of it to the other (`ROW_WIDE_SHARE` of the
    # run's width, first ink to last -- a hollow row's two walls count). A slur's end or a stem standing on the head is narrow in every
    # row it crosses, so it does not stretch the head (Litolff p10 tile 5: slur in from the top right, stem out at the bottom left).
    # The block of such rows over the box's middle row (or overlapping the box most), then the columns that block's ink reaches.
    rw = ex1 - ex0
    wide = np.zeros(clean.shape[0], bool)
    for r in range(rb0, rb1):
        xs_r = np.nonzero(clean[r, ex0:ex1])[0]
        wide[r] = len(xs_r) > 0 and (xs_r[-1] - xs_r[0] + 1) >= ROW_WIDE_SHARE * rw
    blocks: List[Tuple[int, int]] = []
    r = rb0
    while r < rb1:
        if not wide[r]:
            r += 1
            continue
        q = r
        while r < rb1 and wide[r]:
            r += 1
        blocks.append((q, r))
    if not blocks:
        out.update(clean=clean, trimmed=None, extent_sp=None, not_one_head="no_head_ink", size_margin_sp=None, foreign_share=0.0)
        return out
    by0r, by1r = int(round(by0)) - y0, int(round(by1)) - y0
    ey0, ey1 = max(blocks, key=lambda bl: (min(bl[1], by1r) - max(bl[0], by0r), bl[1] - bl[0]))
    rim_y0, rim_y1 = ey0, ey1                 # the head's rows WITH its rim on the lines (lane-stem-end-head r3: the head as a box draws it)
    # a staff/ledger line fused with the head's rim (lesson 10) is the line's, not the head's height: line rows at the block's ends go
    if line_core is None:
        while ey1 - ey0 > 1 and line_rows[ey0]:
            ey0 += 1
        while ey1 - ey0 > 1 and line_rows[ey1 - 1]:
            ey1 -= 1
    else:
        core, cap = line_core
        n = 0
        while ey1 - ey0 > 1 and n < cap and core[ey0]:
            ey0 += 1
            n += 1
        n = 0
        while ey1 - ey0 > 1 and n < cap and core[ey1 - 1]:
            ey1 -= 1
            n += 1
    # ROADMAP 2.327 (c): the head's own rows end where its rim does. A head's rim crosses its middle at its top and its bottom, so an
    # END row of the block whose ink does not reach the head's middle columns (the run's core, `CORE_SHARE` across) is paper beside or
    # below the head held between two other strokes -- its stem and the next mark -- never the inside of the head. NEVER read a hollow from
    # it (Brahms p0, 11 heads Sean judged solid read "hollow" on the paper between the stem and the next mark below them).
    if own_rows():
        m0 = ex0 + int(round((ex1 - ex0) * (1 - CORE_SHARE) / 2.0))
        m1 = max(m0 + 1, ex1 - int(round((ex1 - ex0) * (1 - CORE_SHARE) / 2.0)))
        while ey1 - ey0 > 1 and not clean[ey1 - 1, m0:m1].any():
            ey1 -= 1
        while ey1 - ey0 > 1 and not clean[ey0, m0:m1].any():
            ey0 += 1
    cols = np.nonzero(clean[ey0:ey1, ex0:ex1].any(axis=0))[0]
    ex0, ex1 = ex0 + int(cols[0]), ex0 + int(cols[-1]) + 1
    stem_mask = None
    if own_ink():
        clean, ex0, ex1, stem_mask, own_note = _own_ink(clean, ex0, ex1, ey0, ey1, sp, (kx0, kx1))
        out["own_ink"] = own_note
    head = np.zeros_like(clean)
    head[ey0:ey1, ex0:ex1] = clean[ey0:ey1, ex0:ex1]
    max_h = MAX_HEIGHT_SPACES_V2 if trim_line_only_v2() else MAX_HEIGHT_SPACES
    if (ey1 - ey0) / sp > max_h and (by1 - by0) / sp <= max_h:
        c = int(round(STACK_CLIP_SPACES * sp))
        r0, r1 = max(0, int(round(by0)) - y0 - c), min(head.shape[0], int(round(by1)) - y0 + c)
        h2 = np.zeros_like(head)
        h2[r0:r1] = head[r0:r1]
        if h2.any():
            head = h2
            out["stack_clipped"] = True
            ys, xs = np.nonzero(head)
            ex0, ey0, ex1, ey1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    w_sp, h_sp = (ex1 - ex0) / sp, (ey1 - ey0) / sp
    fs = 0.0
    if foreign_boxes:
        fm = np.zeros_like(head)
        for fb in foreign_boxes:
            fx0, fy0, fx1, fy1 = (int(round(float(v))) for v in fb)
            fcx, fcy = (fx0 + fx1) / 2.0 - x0, (fy0 + fy1) / 2.0 - y0
            if not (ex0 <= fcx < ex1 and ey0 <= fcy < ey1):
                continue            # a box passing over the head (Brahms p5: flag8thDown boxes from a head's top to its flag) is not AT it
            fm[max(0, fy0 - y0):max(0, fy1 - y0), max(0, fx0 - x0):max(0, fx1 - x0)] = True
        tot = int(head.sum())
        fs = round(float((head & fm).sum()) / tot, 3) if tot else 0.0
    noh = None
    # ROADMAP 2.355: the stem is not the head, so the head's width is read without a stem standing at its edge (the filed extent stays the box's)
    hw_sp = w_sp
    if "own_ink" in out:
        hw_sp = width_without_stem(head, ex0, ex1, out["own_ink"].pop("_bands", ())) / sp
        out["own_ink"]["width_sp"] = round(hw_sp, 3)
    if fs >= FOREIGN_SHARE:
        noh = "holds_another_marks_ink"
    elif hw_sp > MAX_WIDTH_SPACES:
        noh = "too_wide"
    elif h_sp > max_h:
        noh = "too_tall"
    elif hw_sp < MIN_SPACES or h_sp < MIN_SPACES:
        noh = "too_small"
    # lane-stem-end-head r3 (read by `stem_end_heads` only; no filed row carries it): the trimmed head with the rows the line-only trim
    # took back at its ends -- a black head in a space trims to ~0.63 sp on Litolff (10 of 15.75 px), the rim on its two lines included
    # it is the head a detector box would draw (Sean 2026-10-29, r2 tile 7: "too rectangular to capture the full bite")
    ry0, ry1 = (ey0, ey1) if out["stack_clipped"] else (min(ey0, rim_y0), max(ey1, rim_y1))
    out.update(rim_trimmed=[x0 + ex0, y0 + ry0, x0 + ex1, y0 + ry1], rim_extent_sp=[round(w_sp, 3), round((ry1 - ry0) / sp, 3)])
    if stem_mask is not None:
        out["stem_mask"] = stem_mask
    out.update(clean=clean, trimmed=[x0 + ex0, y0 + ey0, x0 + ex1, y0 + ey1], extent_sp=[round(w_sp, 3), round(h_sp, 3)],
               not_one_head=noh, foreign_share=fs,
               size_margin_sp=round(min(MAX_WIDTH_SPACES - hw_sp, max_h - h_sp, hw_sp - MIN_SPACES, h_sp - MIN_SPACES), 3))
    return out


def read_head_ink(page_binary: Any, box: Sequence[float], space_px: float, foreign_boxes: Sequence[Sequence[float]],
                  slit_fn: Callable[[Any, Tuple[float, float, float, float]], Optional[Dict[str, Any]]],
                  window_fn: Optional[Callable[[Any, Tuple[float, float, float, float]], Optional[Dict[str, Any]]]] = None
                  ) -> Optional[Dict[str, Any]]:
    """`trim_head`, then the fill on the TRIMMED box: `slit` (2.148's `rows_share` via `slit_fn` = `gather.head_interior_white`),
    `window` (2.23's centre/ring via `window_fn`), `oval_width_sp` (2.164), and `value` 'hollow' / 'filled' / None with `why` and
    `margin` (the slit's signed distance past the cut it passed). None off the raster."""
    import numpy as np
    from . import head_oval as HO
    t = trim_head(page_binary, box, space_px, foreign_boxes)
    if t is None:
        return None
    clean = t.pop("clean")
    stem_mask = t.pop("stem_mask", None)
    out = dict(t, slit=None, window=None, oval_width_sp=None, value=None, why=None, margin=None)
    if t["trimmed"] is None:
        out["why"] = "no_head_ink"
        return out
    ox, oy = t["origin"]
    tx0, ty0, tx1, ty1 = t["trimmed"]
    img = np.where(clean, 0, 255).astype(np.uint8)
    rel = (float(tx0 - ox), float(ty0 - oy), float(tx1 - tx0), float(ty1 - ty0))
    iw = slit_fn(img, rel)
    if iw and iw.get("rows_read"):
        out["slit"] = float(iw["rows_share"])
        out["slit_hole_share"] = iw.get("hole_share")
        if stem_mask is not None and SLIT_FILLED_MAX < out["slit"] < SLIT_HOLLOW_MIN:
            # ROADMAP 2.355: the paper between a head and its stem never makes the head hollow. Read only where the slit fell between its two
            # cuts: a white run ending on the stem does not count. It never overturns a slit that already decided (a Litolff half's stem
            # is the wall of its hole, so its slit reads hollow on the full measure).
            share, _n = slit_rows_share(clean[ty0 - oy:ty1 - oy, tx0 - ox:tx1 - ox], stem_mask[ty0 - oy:ty1 - oy, tx0 - ox:tx1 - ox])
            out["slit_off_stem"] = round(share, 4)
            if share <= SLIT_FILLED_MAX:
                out["slit"] = out["slit_off_stem"]
    if window_fn is not None:
        win = window_fn(img, rel)
        out["window"] = (win or {}).get("windows")
    ov = HO.oval_width(page_binary, t["trimmed"], space_px)
    out["oval_width_sp"] = (ov or {}).get("oval_width_sp")
    if t["not_one_head"]:
        out["why"] = "not_one_head"
        return out
    out["value"], out["margin"], out["why"] = fill_from_slit(out["slit"])
    if out["why"] == "readers_split" and own_ink():
        out["why"] = "slit_between_cuts" if out["slit"] is not None else "slit_unread"
    return out


def fill_from_slit(sl: Optional[float]) -> Tuple[Optional[str], Optional[float], Optional[str]]:
    """2.148's slit cut on one head: `(value, margin, why)` -- 'hollow' / 'filled' with the signed distance past the cut, else
    `(None, None, 'readers_split')`."""
    if sl is None:
        return None, None, "readers_split"
    if sl >= SLIT_HOLLOW_MIN:
        return "hollow", round(sl - SLIT_HOLLOW_MIN, 4), None
    if sl <= SLIT_FILLED_MAX:
        return "filled", round(SLIT_FILLED_MAX - sl, 4), None
    return None, None, "readers_split"
