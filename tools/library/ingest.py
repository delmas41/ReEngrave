#!/usr/bin/env python3
"""Bring scores into the central library — copy, name, describe, index.

    # IMSLP PDFs sitting in ~/Downloads (provenance fetched from the wiki API)
    python3 -m tools.library.ingest imslp ~/Downloads/IMSLP*.pdf

    # a tree of MusicXML (Gradus, or any collection)
    python3 -m tools.library.ingest musicxml ~/Desktop/gradus-vercel/public/scores

    # a score PDF with no IMSLP identity
    python3 -m tools.library.ingest pdf score.pdf --composer "Mahler, Gustav" --work "Symphony No.5"

    python3 -m tools.library.ingest catalog     # rebuild the tracked index
    python3 -m tools.library.ingest verify      # what is present / missing / changed
    python3 -m tools.library.ingest relink      # old benchmark paths -> new store

Everything is COPIED, never moved: the sources are someone's working folders and
an import must not empty them.  Content is deduplicated by SHA-256, so importing
the same collection from two trees yields one file that records both origins,
and re-running an import changes nothing.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import sys
import time
from pathlib import Path

from tools.library import score_library as lib
from tools.library.score_library import ScoreEntry

# IMSLP download names: IMSLP<id>-PMLP<pmlp>-<descriptor>.pdf  (PMLP part optional
# on the oldest uploads, e.g. IMSLP00033-Mozart_-_Symphony_No_01...).
IMSLP_NAME = re.compile(r"^IMSLP(\d+)-(?:PMLP(\d+)-)?(.*)\.pdf$", re.I)

MUSICXML_MARKER = re.compile(rb"<score-(?:partwise|timewise)")

#: work_id -> dossier file prefix, for the works where both halves exist.
#: Only exact, known joins: a wrong dossier is worse than no dossier, because
#: the dossier layer SEEDS clefs and keys rather than only checking them.
DOSSIER_PREFIXES = {
    "beethoven--symphony-5": "beethoven-sym5",
    "beethoven--symphony-6": "beethoven-sym6",
    "beethoven--symphony-9": "beethoven-sym9",
    "mahler--symphony-5": "mahler-sym5",
    "mozart--symphony-40": "mozart-sym40",
    "mozart--symphony-41": "mozart-sym41",
}


def today() -> str:
    return _dt.date.today().isoformat()


def work_id_for(composer: str, work: str) -> str:
    return f"{lib.slug(lib.composer_surname(composer), maxlen=30)}--{lib.work_key(work)}"


def is_musicxml(path: Path) -> bool:
    """Content check, because ``.xml`` is also iZotope presets and build files."""
    suffix = path.suffix.lower()
    if suffix == ".mxl":
        return True
    try:
        return bool(MUSICXML_MARKER.search(path.read_bytes()[:65536]))
    except OSError:
        return False


def _index_by_hash() -> dict[str, Path]:
    """sha256 -> file already in the store, so imports are idempotent."""
    index: dict[str, Path] = {}
    for path in lib.iter_store_files():
        side = lib.sidecar_path(path)
        if side.exists():
            try:
                digest = json.loads(side.read_text()).get("sha256")
            except json.JSONDecodeError:
                digest = None
            index[digest or lib.sha256_of(path)] = path
        else:
            index[lib.sha256_of(path)] = path
    return index


def _unique_dest(dest: Path, taken: set[Path] | None = None) -> Path:
    """Never let one import silently overwrite another.

    Two distinct files can slug identically — two scans of Mahler 5 both land on
    "unknown-edition" — and dedup does not catch it because the CONTENT differs.
    Numbered suffixes are ugly; that is the point, they mark a name that needs a
    real ``--edition``.
    """
    taken = taken or set()
    if not dest.exists() and dest not in taken:
        return dest
    stem, suffix = dest.stem, dest.suffix
    n = 2
    while True:
        candidate = dest.with_name(f"{stem}-{n}{suffix}")
        if not candidate.exists() and candidate not in taken:
            return candidate
        n += 1


def _settled(path: Path, dest: Path) -> bool:
    """Is ``path`` already an acceptable home for a file that wants ``dest``?

    Two distinct files that slug alike get "-2", "-3" suffixes.  On the next
    reorganise the suffixed one recomputes the *base* stem, finds it taken, and
    takes the next number — climbing by one on every pass, forever.  A file
    already sitting at a numbered variant of its own target is where it belongs.
    """
    if path == dest:
        return True
    return (
        path.parent == dest.parent
        and path.suffix == dest.suffix
        and re.fullmatch(rf"{re.escape(dest.stem)}-\d+", path.stem) is not None
    )


def _place(src: Path, dest: Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def _note_duplicate(existing: Path, src: Path, *, dry_run: bool) -> None:
    """Record an additional origin on a file we already hold."""
    side = lib.sidecar_path(existing)
    if dry_run or not side.exists():
        return
    data = json.loads(side.read_text())
    origins = data.setdefault("duplicate_origins", [])
    if str(src) not in origins and str(src) != data.get("origin_path"):
        origins.append(str(src))
        side.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------
# IMSLP PDFs
# --------------------------------------------------------------------------


def ingest_imslp(paths: list[Path], *, dry_run: bool, delay: float, offline: bool) -> int:
    from tools.library import imslp_meta

    seen = _index_by_hash()
    added = skipped = 0
    work_pages: dict[str, str] = {}   # work_id -> IMSLP page, for the roster pass

    for i, src in enumerate(paths):
        match = IMSLP_NAME.match(src.name)
        if match:
            imslp_id, pmlp_id, descriptor = match.groups()
        else:
            # The legacy training layout renamed every file to "score.pdf" and
            # kept the id in the folder: .../pdfs/imslp-575951/score.pdf
            folder = re.match(r"^imslp-(\d+)$", src.parent.name, re.I)
            if not folder:
                print(f"  ! no IMSLP id in name or path, skipping: {src}", file=sys.stderr)
                continue
            imslp_id, pmlp_id, descriptor = folder.group(1), None, ""
        imslp_id = imslp_id.lstrip("0") or "0"

        digest = lib.sha256_of(src)
        if digest in seen:
            _note_duplicate(seen[digest], src, dry_run=dry_run)
            print(f"  = already held: {src.name}")
            skipped += 1
            continue

        meta: dict = {}
        file_meta: dict = {}
        if not offline:
            if i:
                import time

                time.sleep(delay)
            try:
                meta = imslp_meta.file_metadata(imslp_id)
                # file_metadata resolves the id to its own file via the rendered
                # page, so no filename guessing happens here.  If it could not,
                # leave the provenance blank rather than attach another file's.
                file_meta = meta.get("file", {})
                if not file_meta:
                    print(f"  ? no provenance block matched for IMSLP{imslp_id}", file=sys.stderr)
            except Exception as exc:  # noqa: BLE001 - network trouble must not lose the file
                print(f"  ! provenance lookup failed for {imslp_id}: {exc}", file=sys.stderr)

        composer = meta.get("composer") or _composer_from_descriptor(descriptor)
        title = meta.get("work_title") or _title_from_descriptor(descriptor)
        publisher = file_meta.get("publisher_information", "")
        year = _year_from(publisher)
        edition = lib.edition_slug_from_publisher(publisher) if publisher else "unknown-edition"

        work_id = work_id_for(composer, title)
        surname = lib.composer_surname(composer)
        stem = lib.canonical_stem(surname, title, edition, f"imslp{imslp_id}")
        dest = _unique_dest(
            lib.editions_root() / lib.slug(surname, maxlen=30) / lib.slug(title) / f"{stem}.pdf")

        facts = lib.pdf_facts(src)
        listed_pages = meta.get("listed_pages")
        if listed_pages and facts.get("pages") and listed_pages != facts["pages"]:
            print(f"  ! IMSLP{imslp_id} lists {listed_pages}pp but the file has "
                  f"{facts['pages']}pp — provenance may not match", file=sys.stderr)
        entry = ScoreEntry(
            kind="edition",
            path=str(dest.relative_to(lib.library_root())),
            work_id=work_id,
            composer=composer,
            composer_slug=lib.slug(surname, maxlen=30),
            title=title,
            source="imslp",
            sha256=digest,
            bytes=src.stat().st_size,
            variant=edition,
            catalogue=_catalogue_from(title, descriptor),
            pages=facts.get("pages"),
            has_text_layer=facts.get("has_text_layer"),
            imslp_id=imslp_id,
            imslp_url=meta.get("permalink", f"https://imslp.org/wiki/Special:ReverseLookup/{imslp_id}"),
            publisher=publisher,
            publisher_year=year,
            plate=_plate_from(publisher),
            editor=file_meta.get("editor", ""),
            reprint=file_meta.get("reprint", ""),
            image_type=file_meta.get("image_type", ""),
            copyright=file_meta.get("copyright", ""),
            uploader=file_meta.get("uploader", ""),
            date_submitted=file_meta.get("date_submitted", ""),
            original_filename=src.name,
            origin_path=str(src),
            dossier_prefix=DOSSIER_PREFIXES.get(work_id, ""),
            added=today(),
            raw={
                "imslp_page": meta.get("imslp_page", ""),
                "imslp_work_url": meta.get("imslp_url", ""),
                "file_description": file_meta.get("file_description", ""),
                "misc_notes": file_meta.get("misc_notes", ""),
                "pdf_metadata": facts.get("pdf_metadata", {}),
            },
        )

        _place(src, dest, dry_run=dry_run)
        if not dry_run:
            lib.write_sidecar(dest, entry)
        if meta.get("imslp_page"):
            work_pages[work_id] = meta["imslp_page"]
        seen[digest] = dest
        added += 1
        pages = facts.get("pages", "?")
        print(f"  + {dest.relative_to(lib.library_root())}  ({pages}pp, {publisher or 'publisher unknown'})")

    if work_pages and not offline:
        _capture_instrumentation(work_pages, delay=delay, dry_run=dry_run)

    print(f"\nIMSLP: {added} added, {skipped} already held")
    return 0


def _capture_instrumentation(work_pages: dict[str, str], *, delay: float,
                             dry_run: bool) -> None:
    """What each newly-ingested work is SCORED FOR, from the page we just read.

    Work-level, so it is one query per WORK rather than per file, and it is the
    same open MediaWiki API the provenance above comes from — never the download
    gate.  A failure here must not cost a file that is already in the store, so
    everything is caught and reported.
    """
    from tools.library import instrumentation as instr

    catalog = lib.load_catalog()
    for i, (work_id, page) in enumerate(sorted(work_pages.items())):
        if catalog.get("works", {}).get(work_id, {}).get("instrumentation"):
            continue
        if i:
            time.sleep(delay)
        try:
            fact = instr.build_fact(instr.fetch_work_instrumentation(page))
        except Exception as exc:  # noqa: BLE001
            print(f"  ! instrumentation lookup failed for {work_id}: {exc}", file=sys.stderr)
            continue
        what = instr.record(catalog, work_id, fact)
        print(f"  ~ instrumentation {what}: {work_id} "
              f"({fact['dialect']}, {len(fact['roster'])} parsed, "
              f"{len(fact['unparsed'])} unparsed)")
    if not dry_run:
        lib.save_catalog(catalog)


def _composer_from_descriptor(descriptor: str) -> str:
    """"Strauss_-_Till_Eulenspiegels..." -> "Strauss" (last resort, offline only)."""
    head = descriptor.replace("_", " ").split(" - ")[0].strip()
    return head if head and len(head.split()) <= 3 else ""


def _title_from_descriptor(descriptor: str) -> str:
    parts = descriptor.replace("_", " ").split(" - ", 1)
    title = parts[1] if len(parts) > 1 else parts[0]
    return re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()


def _year_from(text: str) -> str:
    m = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", text or "")
    return m.group(1) if m else ""


def _plate_from(text: str) -> str:
    m = re.search(r"plate\s+(\S+)", text or "", re.I)
    return m.group(1) if m else ""


def _catalogue_from(*texts: str) -> str:
    for text in texts:
        m = re.search(r"\b(Op\.?\s*\d+[a-z]?|K\.?\s*\d+|BWV\s*\d+|Hob\.[^\s,]+)", text or "", re.I)
        if m:
            return re.sub(r"\s+", "", m.group(1))
    return ""


# --------------------------------------------------------------------------
# MusicXML collections
# --------------------------------------------------------------------------


def ingest_musicxml(roots: list[Path], *, dry_run: bool, source: str, limit: int | None) -> int:
    seen = _index_by_hash()
    known = known_surnames()
    claimed: set[Path] = set()
    added = skipped = rejected = 0
    candidates: list[Path] = []

    for root in roots:
        if root.is_file():
            candidates.append(root)
            continue
        for suffix in ("*.mxl", "*.musicxml", "*.xml"):
            candidates.extend(sorted(root.rglob(suffix)))

    for src in candidates:
        if limit is not None and added >= limit:
            break
        if not is_musicxml(src):
            rejected += 1
            continue
        digest = lib.sha256_of(src)
        if digest in seen:
            _note_duplicate(seen[digest], src, dry_run=dry_run)
            skipped += 1
            continue

        meta = lib.musicxml_metadata(src)
        composer = lib.clean_composer(meta.get("composer") or "")
        title = meta.get("work_title") or ""
        movement = meta.get("movement_title") or ""

        # Mahler's export writes "Symphonie No. 5I.1. Trauermarsch." — one string
        # holding work and movement.  Split on the roman-numeral movement marker
        # rather than trusting the field boundary.
        if not movement:
            m = re.match(r"^(.*?)((?:[IVX]+[.\s]).*)$", title)
            if m and len(m.group(1).strip()) > 3:
                title, movement = m.group(1).strip(), m.group(2).strip()

        if not title:
            title = re.sub(r"[-_]+", " ", src.stem).strip()
        title = lib.normalize_work_title(title)
        if not composer:
            composer = _composer_from_path(src, known)

        surname = lib.composer_surname(composer)
        work_id = work_id_for(composer, title)
        variant = _variant_for_reference(src, movement, surname, title)
        stem = lib.canonical_stem(surname, title, variant, source)
        dest = (
            lib.reference_root()
            / lib.slug(surname, maxlen=30)
            / lib.slug(title)
            / f"{stem}{src.suffix.lower()}"
        )
        dest = _unique_dest(dest, claimed)

        entry = ScoreEntry(
            kind="reference",
            path=str(dest.relative_to(lib.library_root())),
            work_id=work_id,
            composer=composer,
            composer_slug=lib.slug(surname, maxlen=30),
            title=title,
            source=source,
            sha256=digest,
            bytes=src.stat().st_size,
            variant=variant,
            movement=movement,
            catalogue=_catalogue_from(meta.get("work_number", ""), title, src.stem),
            original_filename=src.name,
            origin_path=str(src),
            dossier_prefix=DOSSIER_PREFIXES.get(work_id, ""),
            added=today(),
            composer_source="embedded" if meta.get("composer") else "path",
            raw={k: v for k, v in meta.items() if v},
        )

        _place(src, dest, dry_run=dry_run)
        if not dry_run:
            lib.write_sidecar(dest, entry)
        claimed.add(dest)
        seen[digest] = dest
        added += 1

    print(f"MusicXML: {added} added, {skipped} duplicates of files already held, "
          f"{rejected} non-MusicXML files ignored")
    return 0


MOVEMENT_IN_NAME = re.compile(
    r"(?:^|[-_])(?:mvt|mov|movement|mvmt|pt|part|no)[-_]?(\d{1,2})(?:[-_]|$)", re.I)
CATALOGUE_IN_NAME = re.compile(r"(?:^|[-_])(bwv|kv?|op|hob|d|rv)[-_]?(\d{1,4})(?:[-_]|$)", re.I)


def _variant_for_reference(src: Path, movement_title: str, composer: str, work: str) -> str:
    """A short field that makes this file unique within its work, and ORDERS it.

    Embedded movement titles are not dependable here — the Mahler 5 export
    repeats "I. Trauermarsch" in every movement's header — while the collection's
    own filenames carry a correct ordinal.  So the filename ordinal wins, and the
    embedded title is kept in the ``movement`` field rather than the name.
    """
    m = MOVEMENT_IN_NAME.search(src.stem)
    if m:
        return f"mvt{int(m.group(1))}"
    m = CATALOGUE_IN_NAME.search(src.stem)
    if m:
        return f"{m.group(1).lower()}{m.group(2)}"
    if movement_title:
        return movement_title
    # Fall back to the filename, minus the words the folder path already says.
    known = set(lib.slug(composer).split("-")) | set(lib.slug(work).split("-"))
    rest = [t for t in lib.slug(src.stem).split("-") if t and t not in known]
    return "-".join(rest) or src.stem


#: A thematic-catalogue prefix names its composer unambiguously — that is what a
#: thematic catalogue IS.  Cheaper and safer than guessing from a folder.
CATALOGUE_COMPOSER = {
    "bwv": "Bach, Johann Sebastian",
    "hob": "Haydn, Joseph",
    "kv": "Mozart, Wolfgang Amadeus",
    "rv": "Vivaldi, Antonio",
    "hwv": "Handel, George Frideric",
    "wab": "Bruckner, Anton",
}


def _composer_from_filename(path: Path, known: set[str]) -> str:
    """"Tchaikovsky_Symphony6_Mvt3.musicxml" — the surname leads the filename."""
    tokens = re.split(r"[-_\s.]+", path.stem)
    for token in tokens[:2]:
        if token and lib.slug(token, maxlen=30) in known:
            return token
    return ""


def _composer_from_catalogue(path: Path) -> str:
    m = re.search(r"\b(bwv|hob|kv|rv|hwv|wab)\.?\s*\d", path.stem, re.I)
    return CATALOGUE_COMPOSER.get(m.group(1).lower(), "") if m else ""


def _composer_from_path(path: Path, known: set[str] | None = None) -> str:
    """Collections are usually foldered by composer; use that when the file is silent.

    Only names we have INDEPENDENTLY seen in some file's own metadata are
    accepted.  Shape alone is not enough evidence — "Piano Sonatas", "Desktop"
    and "Misc" are all well-formed folder names, and each became a composer in
    the store before this check existed.  With no known-name set, walk from the
    file outwards and take the first plausible folder, as before.
    """
    for part in reversed(path.parts[:-1]):
        cleaned = re.sub(r"[_-]+", " ", part).strip()
        if known is not None:
            surname = lib.composer_surname(cleaned)
            candidate = lib.slug(surname, maxlen=30) if surname else ""
            if candidate and candidate != "unknown" and candidate in known:
                return cleaned
            continue
        if re.fullmatch(r"[A-Z][A-Za-z.'\- ]{2,30}", cleaned) and cleaned.lower() not in {
            "scores", "songs", "lieder", "chorales", "music", "musicxml",
        }:
            return cleaned
    return ""


def composer_evidence(data: dict) -> str:
    """How we know this file's composer, strongest first.

    ``path`` is the weak one — it is a folder name, and a folder can be called
    "Misc".  Everything else was stated by the file, by IMSLP, or by a person,
    and must not be second-guessed by a folder-name check.
    """
    if data.get("composer_source"):
        return data["composer_source"]
    if (data.get("raw") or {}).get("composer"):
        return "embedded"
    if data.get("source") == "imslp":
        return "imslp"
    if data.get("kind") == "edition":
        return "manual"
    return "path"


def known_surnames() -> set[str]:
    """Composer slugs vouched for by something better than a folder name."""
    known: set[str] = set()
    for path in lib.iter_store_files():
        side = lib.sidecar_path(path)
        if not side.exists():
            continue
        data = json.loads(side.read_text())
        if composer_evidence(data) == "path":
            continue
        surname = lib.composer_surname(data.get("composer", ""))
        candidate = lib.slug(surname, maxlen=30) if surname else ""
        # "unknown" is the slug of every unnameable string, including "/".  Left
        # in the vouched set it matches the filesystem root and every path walk
        # short-circuits on it.
        if candidate and candidate != "unknown":
            known.add(candidate)
    return known


def canonical_display_names() -> dict[str, str]:
    """One spelling of each composer's name, chosen from the ones on hand.

    The same person arrives as "J.S. Bach", "Bach", and "Bach, Johann Sebastian"
    depending on who encoded the file.  The folder already unifies them; this
    unifies what the catalog SAYS, preferring a surname-first form with the most
    given names, so the index reads like a library index.
    """
    forms: dict[str, set[str]] = {}
    for path in lib.iter_store_files():
        side = lib.sidecar_path(path)
        if not side.exists():
            continue
        data = json.loads(side.read_text())
        name = lib.clean_composer(data.get("composer", ""))
        surname = lib.composer_surname(name)
        if name and surname:
            forms.setdefault(lib.slug(surname, maxlen=30), set()).add(name)

    best: dict[str, str] = {}
    for key, names in forms.items():
        # Rank: a comma form first, then the one naming the most words.
        ranked = sorted(names, key=lambda n: ("," in n, len(n.split()), len(n)), reverse=True)
        best[key] = lib.to_surname_first(ranked[0])
    return best


def cmd_reorganize(dry_run: bool) -> int:
    """Re-derive every held file's identity and move it to where it now belongs.

    Normalisation improves — life dates stripped from composer names, folder
    fallbacks restricted to vouched-for surnames — and the store has to be able
    to catch up without re-importing 1700 files from sources that may be gone.
    Sidecars are the input and the output, so nothing is re-fetched.
    """
    known = known_surnames()
    display = canonical_display_names()
    print(f"{len(known)} composer names vouched for by embedded metadata\n")

    moved = unchanged = renamed_only = 0
    claimed: set[Path] = set()
    for path in sorted(lib.iter_store_files()):
        side = lib.sidecar_path(path)
        if not side.exists():
            continue
        data = json.loads(side.read_text())

        evidence = composer_evidence(data)
        if evidence == "manual":
            # A person corrected this on purpose, usually BECAUSE the embedded
            # name was junk ("cmoposer", "作曲 / 编排").  Never re-read it.
            composer = lib.clean_composer(data.get("composer", ""))
        else:
            composer = lib.clean_composer(
                (data.get("raw") or {}).get("composer") or data.get("composer", ""))
        surname = lib.composer_surname(composer)
        # Re-derive only where the name came from a folder, or where cleaning
        # the stated name left nothing usable.
        if evidence != "manual" and (evidence == "path" or not surname):
            origin = Path(data.get("origin_path", "") or path.name)
            guess = (_composer_from_path(origin, known)
                     or _composer_from_filename(origin, known)
                     or _composer_from_catalogue(origin))
            if guess:
                composer, surname = lib.clean_composer(guess), lib.composer_surname(guess)
                evidence = "path"
            elif evidence == "path":
                # A folder name nothing else vouches for is not a composer.
                # "unknown" is the honest answer and keeps the junk out of the tree.
                composer, surname = "", ""

        slug_key = lib.slug(surname, maxlen=30) if surname else ""
        composer = display.get(slug_key, composer) or composer
        title = lib.normalize_work_title(data.get("title", ""))
        if not title:
            title = re.sub(r"[-_]+", " ", path.stem.split("--")[1] if "--" in path.stem else path.stem)

        variant = data.get("variant", "") or data.get("movement", "")
        source = data.get("source", "local")
        source_tag = f"imslp{data['imslp_id']}" if data.get("imslp_id") else source
        stem = lib.canonical_stem(surname, title, variant, source_tag)
        root = lib.editions_root() if data.get("kind") == "edition" else lib.reference_root()
        dest = root / lib.slug(surname, maxlen=30) / lib.slug(title) / f"{stem}{path.suffix.lower()}"

        # Derived metadata is refreshed whether or not the file moves: a change
        # to the work KEY (which joins editions to their ground truth) leaves
        # every path settled, so a move-only update would never apply it.
        updates = {
            "composer": composer or data.get("composer", ""),
            "composer_source": evidence,
            "composer_slug": slug_key,
            "title": title,
            "work_id": work_id_for(surname, title),
        }
        updates["dossier_prefix"] = DOSSIER_PREFIXES.get(
            updates["work_id"], data.get("dossier_prefix", ""))
        changed = any(data.get(k) != v for k, v in updates.items() if v)

        if _settled(path, dest):
            if changed:
                data.update(updates)
                if not dry_run:
                    side.write_text(json.dumps(
                        {k: v for k, v in data.items() if v not in ("", None, {}, [])},
                        indent=2, ensure_ascii=False) + "\n")
                renamed_only += 1
            unchanged += 1
            continue

        dest = _unique_dest(dest, claimed)
        claimed.add(dest)

        data.update(updates)
        data["path"] = str(dest.relative_to(lib.library_root()))
        data = {k: v for k, v in data.items() if v not in ("", None, {}, [])}

        if moved < 25:
            print(f"  {path.relative_to(lib.library_root())}\n    -> {data['path']}")
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            path.rename(dest)
            side.unlink(missing_ok=True)
            lib.write_json_atomic(lib.sidecar_path(dest), data)
        moved += 1

    # Empty composer folders left behind by the moves.
    if not dry_run:
        for d in sorted(lib.library_root().rglob("*"), reverse=True):
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
    if moved > 25:
        print(f"  ... and {moved - 25} more")
    print(f"\n{moved} moved, {unchanged} already correct"
          + (f", {renamed_only} metadata refreshed" if renamed_only else ""))
    return 0



def ingest_pdf(paths: list[Path], *, composer: str, work: str, edition: str,
               source: str, dry_run: bool) -> int:
    seen = _index_by_hash()
    added = skipped = 0
    for src in paths:
        digest = lib.sha256_of(src)
        if digest in seen:
            _note_duplicate(seen[digest], src, dry_run=dry_run)
            skipped += 1
            continue
        title = work or re.sub(r"[-_]+", " ", src.stem).strip()
        surname = lib.composer_surname(composer) or _composer_from_path(src, known_surnames())
        facts = lib.pdf_facts(src)
        work_id = work_id_for(surname, title)
        stem = lib.canonical_stem(surname, title, edition or "unknown-edition", source)
        dest = _unique_dest(
            lib.editions_root() / lib.slug(surname, maxlen=30) / lib.slug(title) / f"{stem}.pdf")

        entry = ScoreEntry(
            kind="edition",
            path=str(dest.relative_to(lib.library_root())),
            work_id=work_id,
            composer=composer or surname,
            composer_slug=lib.slug(surname, maxlen=30),
            title=title,
            source=source,
            sha256=digest,
            bytes=src.stat().st_size,
            variant=edition or "unknown-edition",
            pages=facts.get("pages"),
            has_text_layer=facts.get("has_text_layer"),
            original_filename=src.name,
            origin_path=str(src),
            dossier_prefix=DOSSIER_PREFIXES.get(work_id, ""),
            added=today(),
            raw={"pdf_metadata": facts.get("pdf_metadata", {})},
        )
        _place(src, dest, dry_run=dry_run)
        if not dry_run:
            lib.write_sidecar(dest, entry)
        seen[digest] = dest
        added += 1
        print(f"  + {dest.relative_to(lib.library_root())}  ({facts.get('pages','?')}pp)")
    print(f"PDF: {added} added, {skipped} already held")
    return 0


# --------------------------------------------------------------------------
# maintenance
# --------------------------------------------------------------------------


def cmd_refresh(dry_run: bool, delay: float) -> int:
    """Re-fetch IMSLP provenance for everything already held.

    The wiki is the source of truth and this parser keeps learning its templates,
    so a sidecar written by an older parser can be improved without re-importing
    the file.  Only provenance fields are rewritten; identity and checksum stay.
    """
    from tools.library import imslp_meta

    updated = 0
    files = [p for p in lib.iter_store_files() if lib.sidecar_path(p).exists()]
    imslp_files = []
    for path in files:
        data = json.loads(lib.sidecar_path(path).read_text())
        if data.get("source") == "imslp" and data.get("imslp_id"):
            imslp_files.append((path, data))

    for i, (path, data) in enumerate(imslp_files):
        if i:
            import time

            time.sleep(delay)
        try:
            meta = imslp_meta.file_metadata(data["imslp_id"])
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {data['imslp_id']}: {exc}", file=sys.stderr)
            continue
        fm = meta.get("file", {})
        if not fm:
            print(f"  ? IMSLP{data['imslp_id']}: no matching file block", file=sys.stderr)
            continue
        publisher = fm.get("publisher_information", "")
        before = data.get("publisher", "")
        # The edition slug is DERIVED from the publisher, so a provenance fix that
        # leaves it alone ships a file still named "unknown-edition". reorganize
        # renames from this field, so update it here and let that pass move it.
        if publisher:
            data["variant"] = lib.edition_slug_from_publisher(publisher)
        data.update({
            "publisher": publisher,
            "publisher_year": _year_from(publisher),
            "plate": _plate_from(publisher),
            "editor": fm.get("editor", ""),
            "reprint": fm.get("reprint", ""),
            "image_type": fm.get("image_type", ""),
            "copyright": fm.get("copyright", ""),
            "uploader": fm.get("uploader", ""),
            "date_submitted": fm.get("date_submitted", ""),
        })
        data = {k: v for k, v in data.items() if v not in ("", None, {}, [])}
        if not dry_run:
            lib.sidecar_path(path).write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        if before != publisher:
            print(f"  ~ {path.name}\n      was: {before}\n      now: {publisher}")
        updated += 1
    print(f"\nrefreshed {updated} IMSLP entries")
    return 0


def cmd_set(paths: list[Path], *, composer: str, work: str, edition: str, dry_run: bool) -> int:
    """Correct a held file's identity by hand.

    Some files name no composer anywhere — not in their metadata, not in their
    path, not in a catalogue number — and a person simply has to say.  Marking
    the correction ``manual`` stops :func:`cmd_reorganize` from overwriting it
    with another guess.  Run ``reorganize`` afterwards to move the file.
    """
    for path in paths:
        # Accept a path as typed (relative to the shell's cwd) or as the catalog
        # records it (relative to the library root); both are natural to paste.
        for candidate in (path, lib.library_root() / path, Path.cwd() / path):
            if candidate.exists():
                path = candidate.resolve()
                break
        side = lib.sidecar_path(path)
        if not side.exists():
            print(f"  ! not in the library: {path}", file=sys.stderr)
            continue
        data = json.loads(side.read_text())
        if composer:
            data["composer"] = composer
            data["composer_source"] = "manual"
            data["composer_slug"] = lib.slug(lib.composer_surname(composer), maxlen=30)
        if work:
            data["title"] = lib.normalize_work_title(work)
        if edition:
            data["variant"] = edition
        data["work_id"] = work_id_for(
            lib.composer_surname(data.get("composer", "")), data.get("title", ""))
        data["dossier_prefix"] = DOSSIER_PREFIXES.get(data["work_id"], data.get("dossier_prefix", ""))
        print(f"  {path.name}\n      composer={data.get('composer','')!r} title={data.get('title','')!r}")
        if not dry_run:
            side.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_relink(dry_run: bool) -> int:
    """Recreate the legacy training-data paths as symlinks into the store."""
    catalog = lib.load_catalog()
    made = 0
    for entry in catalog.get("entries", []):
        if entry.get("source") != "imslp" or not entry.get("imslp_id"):
            continue
        target = lib.library_root() / entry["path"]
        if not target.exists():
            continue
        # Use the path the file actually came from rather than re-deriving a
        # slug: the legacy folder names ("beethoven-symphony-5") predate the
        # work_id scheme and a derived guess would miss them.
        origin = entry.get("origin_path", "")
        if not origin:
            continue
        link = Path(origin)
        if not link.is_absolute():
            link = lib.REPO_ROOT / link
        try:
            link.relative_to(lib.LEGACY_IMSLP_ROOT)
        except ValueError:
            continue
        if link.is_symlink() and link.resolve() == target.resolve():
            continue
        print(f"  {link.relative_to(lib.REPO_ROOT)} -> {entry['path']}")
        if not dry_run:
            if link.exists() or link.is_symlink():
                # The store copy is byte-identical (same sha256 that dedup keyed
                # on), so replacing the original with a link loses nothing.
                if link.exists() and not link.is_symlink() and lib.sha256_of(link) != entry["sha256"]:
                    print(f"  ! checksum differs, leaving in place: {link}", file=sys.stderr)
                    continue
                link.unlink()
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target)
        made += 1
    print(f"\n{made} legacy links")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="say what would happen, copy nothing")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("imslp", help="ingest IMSLP-named PDFs")
    p.add_argument("paths", nargs="+", type=Path)
    p.add_argument("--delay", type=float, default=5.0, help="seconds between wiki lookups")
    p.add_argument("--offline", action="store_true", help="skip provenance lookup")

    p = sub.add_parser("musicxml", help="ingest a MusicXML file or tree")
    p.add_argument("paths", nargs="+", type=Path)
    p.add_argument("--source", default="local", help="provenance tag, e.g. gradus")
    p.add_argument("--limit", type=int, default=None)

    p = sub.add_parser("pdf", help="ingest a score PDF with no IMSLP identity")
    p.add_argument("paths", nargs="+", type=Path)
    p.add_argument("--composer", default="")
    p.add_argument("--work", default="")
    p.add_argument("--edition", default="")
    p.add_argument("--source", default="local")

    p = sub.add_parser("refresh", help="re-fetch IMSLP provenance for held files")
    p.add_argument("--delay", type=float, default=5.0)

    p = sub.add_parser("set", help="correct a held file's composer / work by hand")
    p.add_argument("paths", nargs="+", type=Path, help="paths relative to the library root")
    p.add_argument("--composer", default="")
    p.add_argument("--work", default="")
    p.add_argument("--edition", default="")

    p = sub.add_parser("instrumentation",
                       help="backfill each held work's IMSLP instrumentation")
    p.add_argument("--delay", type=float, default=6.0)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--refetch", action="store_true", help="re-read recorded works")

    # ⚠️ Deliberately NOT hooked into the ingest path the way `instrumentation`
    # is.  A work-level lookup is one HTTP call; an edition-level one renders a
    # page, detects staves and runs Surya (~11 s) and needs `.venv-surya`, so it
    # is a sweep somebody asks for, never a side effect of adding a file.
    p = sub.add_parser("edition-instrumentation",
                       help="read each held edition's roster off its own pages")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--availability", type=Path, default=None,
                   help="roster-availability.json, to hint the page to read first")
    p.add_argument("--only-hinted", action="store_true")
    p.add_argument("--refetch", action="store_true", help="re-read recorded editions")

    sub.add_parser("reorganize", help="re-derive names and repair the layout in place")

    sub.add_parser("catalog", help="rebuild data/score-library/catalog.json from sidecars")
    sub.add_parser("verify", help="check the catalog against the store")
    sub.add_parser("relink", help="recreate legacy benchmark paths as symlinks")

    args = ap.parse_args()

    if args.cmd == "imslp":
        return ingest_imslp(args.paths, dry_run=args.dry_run, delay=args.delay, offline=args.offline)
    if args.cmd == "musicxml":
        return ingest_musicxml(args.paths, dry_run=args.dry_run, source=args.source, limit=args.limit)
    if args.cmd == "pdf":
        return ingest_pdf(args.paths, composer=args.composer, work=args.work,
                          edition=args.edition, source=args.source, dry_run=args.dry_run)
    if args.cmd == "set":
        return cmd_set(args.paths, composer=args.composer, work=args.work,
                       edition=args.edition, dry_run=args.dry_run)
    if args.cmd == "instrumentation":
        from tools.library import instrumentation as instr

        report = instr.backfill(delay=args.delay, dry_run=args.dry_run,
                                limit=args.limit, refetch=args.refetch)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1 if report["errors"] else 0
    if args.cmd == "edition-instrumentation":
        from tools.library import edition_instrumentation as ed

        report = ed.acquire_all(dry_run=args.dry_run, limit=args.limit,
                                dpi=args.dpi, availability=args.availability,
                                refetch=args.refetch, only_hinted=args.only_hinted)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1 if report["errors"] else 0
    if args.cmd == "reorganize":
        return cmd_reorganize(args.dry_run)
    if args.cmd == "refresh":
        return cmd_refresh(args.dry_run, args.delay)
    if args.cmd == "catalog":
        catalog = lib.rebuild_catalog()
        print(lib.summarize(catalog.get("entries", [])))
        if catalog.get("unregistered"):
            print(f"\n{len(catalog['unregistered'])} files in the store with no sidecar")
        print(f"\nwrote {lib.CATALOG_PATH.relative_to(lib.REPO_ROOT)}")
        return 0
    if args.cmd == "verify":
        report = lib.verify()
        print(f"present {len(report['present'])}  missing {len(report['missing'])}  "
              f"changed {len(report['changed'])}")
        for path in report["missing"][:20]:
            print(f"  missing: {path}")
        for path in report["changed"]:
            print(f"  CHANGED: {path}")
        return 1 if report["changed"] else 0
    if args.cmd == "relink":
        return cmd_relink(args.dry_run)
    return 1


if __name__ == "__main__":
    sys.exit(main())
