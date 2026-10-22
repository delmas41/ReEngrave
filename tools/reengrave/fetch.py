"""ROADMAP 4.1 -- get the chosen edition's PDF onto disk.

**Never defeats or automates IMSLP's JavaScript download gate** (CLAUDE.md
§8). Held -> the library file is used directly, no browser touched at all.
Not held -> this OPENS the edition's IMSLP page in the user's default
browser for the one click the gate requires, prints one line telling the
user to click Download, and WATCHES the download directory for a new PDF,
with a timeout. It never fetches the PDF itself, and beyond the metadata
lookup `tools.library.ingest.ingest_imslp` already makes (provenance off
the wiki API, not the gated download), it makes no HTTP request at all.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional, Set

from tools.library import score_library as lib


class DownloadTimeout(RuntimeError):
    """No new PDF appeared in the download directory within the timeout."""


def default_open_browser(url: str) -> None:
    """`open <url>` on macOS (CLAUDE.md §"Hard constraints"), `webbrowser.open`
    elsewhere -- never a request this process makes itself."""
    if sys.platform == "darwin":
        subprocess.run(["open", url], check=False)
    else:
        import webbrowser
        webbrowser.open(url)


def _snapshot(downloads_dir: Path) -> Set[Path]:
    downloads_dir = Path(downloads_dir)
    if not downloads_dir.exists():
        return set()
    return {p for p in downloads_dir.iterdir() if p.suffix.lower() == ".pdf"}


def watch_for_download(downloads_dir: Path, *, timeout_s: float,
                       existing: Optional[Set[Path]] = None,
                       poll_s: float = 1.0,
                       now: Callable[[], float] = time.monotonic,
                       sleep: Callable[[float], None] = time.sleep) -> Path:
    """Block until a PDF not in `existing` appears in `downloads_dir`.

    `existing` is a snapshot taken BEFORE the browser was opened, so a file
    already sitting in the downloads directory from an unrelated download
    is never mistaken for this one -- the positive control in this module's
    own tests proves exactly that: a directory that already holds a PDF
    still times out when nothing NEW arrives (CLAUDE.md rule 7).
    """
    downloads_dir = Path(downloads_dir)
    before = existing if existing is not None else _snapshot(downloads_dir)
    deadline = now() + timeout_s
    while True:
        new = sorted(_snapshot(downloads_dir) - before)
        if new:
            return new[0]
        if now() >= deadline:
            raise DownloadTimeout(
                f"no new PDF appeared in {downloads_dir} within "
                f"{timeout_s:.0f}s -- click Download on the IMSLP page that "
                f"was opened, or pass --downloads-dir if it saves somewhere "
                f"else")
        sleep(poll_s)


def held_pdf_path(candidate: dict) -> Optional[Path]:
    """The library path for an already-held candidate, or `None` -- read-
    only, safe to call from a `--dry-run` (it touches no browser and no
    network)."""
    if candidate.get("held") and candidate.get("path"):
        return lib.library_root() / candidate["path"]
    return None


def get_edition_pdf(candidate: dict, *, downloads_dir: Path, timeout_s: float,
                    delay: float = 5.0,
                    open_browser: Callable[[str], None] = default_open_browser,
                    watch: Callable[..., Path] = watch_for_download,
                    ingest_imslp: Optional[Callable] = None) -> Path:
    """The candidate's PDF, on disk.

    Held: return the library file directly -- ROADMAP 4.1's own hard
    constraint, "if the chosen edition is already HELD, skip the browser
    step entirely." Not held: open the IMSLP page, watch for the download,
    then hand the new file to `tools.library.ingest.ingest_imslp` (imported
    lazily so tests can inject a fake without importing the real one, which
    would reach the network for provenance) and read the resulting library
    path back off a freshly rebuilt catalog -- `ingest_imslp` itself never
    returns a path, only writes a sidecar.
    """
    held = held_pdf_path(candidate)
    if held is not None:
        return held

    url = candidate.get("page_url") or (
        f"https://imslp.org/wiki/Special:ReverseLookup/{candidate.get('imslp_id')}")
    print(f"OPEN: {url}")
    print(f"  click Download for IMSLP{candidate.get('imslp_id')} -- "
         f"watching {downloads_dir} for the new PDF (timeout {timeout_s:.0f}s)")
    before = _snapshot(Path(downloads_dir))
    open_browser(url)
    downloaded = watch(downloads_dir, timeout_s=timeout_s, existing=before)
    print(f"  found {downloaded}")

    if ingest_imslp is None:
        from tools.library.ingest import ingest_imslp as ingest_imslp  # noqa: PLC0414
    ingest_imslp([downloaded], dry_run=False, delay=delay, offline=False)

    digest = lib.sha256_of(downloaded)
    fresh = lib.rebuild_catalog()
    for e in fresh.get("entries", ()):
        if e.get("sha256") == digest:
            return lib.library_root() / e["path"]
    raise RuntimeError(
        f"ingest reported success for {downloaded} but the rebuilt catalog "
        f"has no entry with its checksum -- run "
        f"`python3 -m tools.library.ingest catalog` by hand and re-run")
