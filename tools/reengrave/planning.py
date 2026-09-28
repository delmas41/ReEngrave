"""ROADMAP 4.1 -- rank editions, resolve pages, build the staged command.

Pure functions only: no network, no subprocess, no writes.  The two
side-effecting seams `reengrave import` needs -- opening a browser and
watching a download directory -- live in `fetch.py`, injected rather than
called from here, so everything in this module can be tested with a plain
dict standing in for the catalog.

Reuses `tools.library.build_wishlist`'s own ranking (`score_candidate`,
`familiar_publishers`) rather than restating it (CLAUDE.md rule 9): the
scoring rule that a real 19th-century scan beats a modern typeset was
measured once and lives in exactly one place.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tools.library import build_wishlist as bw
from tools.library import ingest as library_ingest
from tools.library import score_library as lib
from tools.omr.staged import movements as movements_mod

#: The committed, precomputed survey (`build_wishlist --out`) -- editions
#: IMSLP is known to carry that are not (yet) downloaded into the library.
#: "Catalogued" in the brief's sense: known on paper, not necessarily held.
WISHLIST_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "score-library" / "wishlist.json")


class NoKnownEdition(RuntimeError):
    """No held edition, no catalogued (wishlist) row, and no live IMSLP
    candidate for this work_id.  CLAUDE.md rule 6: a missing answer is
    reported, never guessed past."""


def composer_slug_of(work_id: str) -> str:
    """`"beethoven--symphony-5"` -> `"beethoven"` -- the same slug the
    catalog stores as `composer_slug`, split off the `work_id` rather than
    re-slugging a name (there is no name here to slug)."""
    return work_id.split("--", 1)[0]


def load_wishlist(path: Optional[Path] = None) -> List[dict]:
    target = path or WISHLIST_PATH
    if not target.exists():
        return []
    return json.loads(target.read_text()).get("works", [])


def _as_candidate(*, imslp_id: str, description: str, pages: Any,
                  publisher: str, editor: str, scan: str, copyright: str,
                  held: bool, path: str, page_url: str, source: str) -> dict:
    return {
        "imslp_id": str(imslp_id or ""),
        "description": description or "",
        "pages": pages,
        "publisher": publisher or "",
        "editor": editor or "",
        "scan": scan or "",
        "copyright": copyright or "",
        "held": held,
        "path": path or "",
        "page_url": page_url or "",
        "source": source,
    }


def _catalog_candidates(catalog: dict, work_id: str) -> List[dict]:
    """Every HELD edition of `work_id` -- a file actually in the library."""
    out = []
    for e in catalog.get("entries", ()):
        if e.get("kind") != "edition" or e.get("work_id") != work_id:
            continue
        raw = e.get("raw") or {}
        out.append(_as_candidate(
            imslp_id=e.get("imslp_id", ""),
            description=raw.get("file_description", ""),
            pages=e.get("pages"),
            publisher=e.get("publisher", ""),
            editor=e.get("editor", ""),
            scan=e.get("image_type", ""),
            copyright=e.get("copyright", ""),
            held=True,
            path=e.get("path", ""),
            page_url=e.get("imslp_url") or raw.get("imslp_work_url", ""),
            source="held",
        ))
    return out


def _wishlist_candidates(rows: Sequence[dict], work_id: str,
                         exclude_ids: set) -> List[dict]:
    """Every CATALOGUED-but-not-held row for `work_id` -- known from a prior
    `build_wishlist` survey, keyed the same way `ingest.py` keys a download
    (`work_id_for`, reused rather than restated)."""
    out = []
    for row in rows:
        imslp_id = str(row.get("imslp_id") or "")
        if not imslp_id or imslp_id in exclude_ids:
            continue
        wid = library_ingest.work_id_for(row.get("composer", ""), row.get("work", ""))
        if wid != work_id:
            continue
        out.append(_as_candidate(
            imslp_id=imslp_id,
            description=row.get("description", ""),
            pages=row.get("pages"),
            publisher=row.get("publisher", ""),
            editor=row.get("editor", ""),
            scan=row.get("scan", ""),
            copyright=row.get("copyright", ""),
            held=False,
            path="",
            page_url=row.get("page_url", ""),
            source="catalogued",
        ))
    return out


def rank_editions(work_id: str, *, catalog: Optional[dict] = None,
                  wishlist_rows: Optional[List[dict]] = None,
                  network_candidates: Optional[List[dict]] = None
                  ) -> List[dict]:
    """Every known candidate for `work_id`, ranked by
    `build_wishlist.score_candidate` -- highest first.

    Held catalog editions and catalogued (wishlist) rows are always
    considered; `network_candidates` (a fresh `build_wishlist.candidates_for`
    page fetch, done by the caller so this stays network-free) is used ONLY
    when neither of the first two has anything, so a work this repo already
    knows about never triggers a live IMSLP hit just to be ranked again.
    """
    catalog = catalog if catalog is not None else lib.load_catalog()
    wishlist_rows = wishlist_rows if wishlist_rows is not None else load_wishlist()

    held = _catalog_candidates(catalog, work_id)
    held_ids = {c["imslp_id"] for c in held if c["imslp_id"]}
    catalogued = _wishlist_candidates(wishlist_rows, work_id, held_ids)

    candidates = held + catalogued
    if not candidates and network_candidates:
        candidates = [
            _as_candidate(
                imslp_id=c.get("imslp_id", ""), description=c.get("description", ""),
                pages=c.get("pages"), publisher=c.get("publisher", ""),
                editor=c.get("editor", ""), scan=c.get("scan", ""),
                copyright=c.get("copyright", ""), held=False, path="",
                page_url=c.get("page_url", ""), source="network")
            for c in network_candidates
        ]
    if not candidates:
        raise NoKnownEdition(
            f"no held edition, no catalogued (wishlist) row, and no live "
            f"candidate for {work_id!r} -- run "
            f"`python3 -m tools.library.build_wishlist`, or pass --edition "
            f"if you already know the IMSLP id")

    familiar = bw.familiar_publishers(catalog).get(composer_slug_of(work_id), set())
    scored = [dict(c, score=bw.score_candidate(c, familiar)) for c in candidates]
    # Stable sort: ties keep held-before-catalogued-before-network order,
    # and original order within each -- deterministic, never a guess about
    # which of two equally-scored editions is "really" better (CLAUDE.md
    # rule 6). `--edition` is the escape when a human wants a specific one.
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored


def resolve_pages_spec(total_pages: Optional[int], movements_arg: Optional[str]
                       ) -> Tuple[str, Tuple[dict, ...]]:
    """The staged CLI's `--pages` spec, and the parsed movement spans (empty
    when none were given).

    `--movements` is passed straight through unchanged by the caller; this
    only reads it (via `movements_mod.parse_movement_spec`, reused rather
    than restated) to compute the page RANGE that must be gathered for the
    movements named -- a bad spec raises `MalformedMovementSpec` here, loudly,
    before anything runs, exactly as the staged CLI itself does.

    With no `--movements` at all, the whole known page count is requested
    (ROADMAP 4.1's own instruction: "If none is given, run as ONE movement").
    A `total_pages` of `None` (an edition whose page count nobody has
    recorded yet) falls back to page 0 alone rather than guessing a range.
    """
    if not movements_arg:
        if not total_pages:
            return "0", ()
        return f"0-{total_pages - 1}", ()
    spans = movements_mod.parse_movement_spec(movements_arg)
    lo = min(s["first_page"] for s in spans)
    hi = max(s["last_page"] for s in spans)
    return f"{lo}-{hi}", spans


def build_staged_command(*, python: str, pdf_path: str, work_id: str,
                         pages_spec: str, movements_arg: Optional[str],
                         out_dir: Path) -> List[str]:
    """The exact `python3 -m tools.omr.staged ...` invocation ROADMAP 4.1
    step 5 calls -- the SAME subprocess `python3 -m tools.omr.staged` itself
    is, so nothing about the staged CLI's own flags is restated here."""
    out_dir = Path(out_dir)
    cmd = [
        python, "-m", "tools.omr.staged", str(pdf_path),
        "--pages", pages_spec,
        "--route-weights",
        "--work-id", work_id,
        "--out", str(out_dir / f"{work_id}.record.json"),
        "--musicxml", str(out_dir / f"{work_id}.musicxml"),
        "--lilypond", str(out_dir / f"{work_id}.ly"),
        "--pdf", str(out_dir / f"{work_id}.pdf"),
        "--progress",
    ]
    if movements_arg:
        cmd += ["--movements", movements_arg]
    return cmd


def budget_for(pages_spec: str) -> Dict[str, Any]:
    """`tools.omr.staged.budget`'s own estimate over the page COUNT implied
    by `pages_spec` -- imported, never restated (CLAUDE.md rule 9)."""
    from tools.omr.staged import budget as budget_mod

    if "-" in pages_spec:
        lo_s, hi_s = pages_spec.split("-", 1)
        lo, hi = int(lo_s), int(hi_s)
    else:
        lo = hi = int(pages_spec)
    n_pages = hi - lo + 1
    return budget_mod.estimate_job_budget_s(n_pages)
