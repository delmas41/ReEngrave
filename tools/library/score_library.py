#!/usr/bin/env python3
"""The central score library: where scores live, what they are called, what we know about them.

Scores arrived here from four directions — IMSLP downloads, the Gradus MusicXML
set, benchmark fixtures, and one-off files in ``~/Downloads`` — and each kept its
own naming.  This module is the single answer to "where is that score, and which
edition is it?"

Two halves, because they answer different questions:

``editions/``   printed editions as PDF.  What a *reader* sees: a particular
                publisher's engraving, with its scan quality and its errors.
                This is OMR input.
``reference/``  machine-readable MusicXML.  What the notes *are*.  This is ground
                truth — the dossier generator and every accuracy benchmark read
                from here.

A PDF and an MXL of the same work are two views of one thing, so they share a
``work_id`` and join on it.

Layout, under :func:`library_root` (machine-local, gitignored — the files are
large binaries)::

    library/
      editions/<composer>/<work>/<composer>--<work>--<edition>--<source>.pdf
                                 <same stem>.json          <- provenance sidecar
      reference/<composer>/<work>/<composer>--<work>--<movement>--<source>.mxl
                                 <same stem>.json

``--`` separates fields so a filename read on its own still says what it is;
single hyphens live inside a field.  The sidecar is written next to the file so a
score carries its provenance even if it is copied out of the tree.

The *catalog* (``data/score-library/catalog.json``) is the merge of every
sidecar, and unlike the store it is COMMITTED.  Provenance is hand-curated and
network-fetched; losing it to a gitignore would cost real work, and with the
catalog in git a lost store is re-fetchable from the IMSLP URLs it records.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

def _main_worktree(start: Path) -> Path:
    """The main checkout, even when this code is running from a git worktree.

    One machine holds ONE store; a worktree must not get its own empty copy.  In
    a worktree ``<root>/.git`` is a file reading ``gitdir: <main>/.git/worktrees/<name>``,
    so the main checkout is two levels above that ``.git``.  The same trap is
    documented for ``tools/omr/training/data/imslp`` — a worktree reached it only
    through a symlink somebody had to remember to create.
    """
    dotgit = start / ".git"
    if dotgit.is_file():
        m = re.search(r"gitdir:\s*(.+)", dotgit.read_text())
        if m:
            gitdir = Path(m.group(1).strip())
            for parent in gitdir.parents:
                if parent.name == ".git":
                    return parent.parent
    return start


REPO_ROOT = Path(__file__).resolve().parents[2]
#: Where shared, machine-local data lives — the same directory from every worktree.
MACHINE_ROOT = _main_worktree(REPO_ROOT)
CATALOG_PATH = REPO_ROOT / "data" / "score-library" / "catalog.json"
CATALOG_SCHEMA_VERSION = 1

#: Old per-work IMSLP layout that ~20 benchmark scripts still hard-code.
#: :func:`legacy_link_path` keeps those paths resolving after a file moves here.
LEGACY_IMSLP_ROOT = MACHINE_ROOT / "tools" / "omr" / "training" / "data" / "imslp"

EDITION_SUFFIXES = {".pdf"}
REFERENCE_SUFFIXES = {".mxl", ".musicxml", ".xml"}


def library_root() -> Path:
    """Physical store.  ``SCORE_LIBRARY_ROOT`` overrides, so a worktree or another
    machine can point at one shared copy instead of duplicating gigabytes."""
    env = os.environ.get("SCORE_LIBRARY_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return MACHINE_ROOT / "library"


def editions_root() -> Path:
    return library_root() / "editions"


def reference_root() -> Path:
    return library_root() / "reference"


# --------------------------------------------------------------------------
# naming
# --------------------------------------------------------------------------

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")

#: Applied before slugging so "Op.67" and "No. 5" survive as readable fields
#: rather than collapsing into "op-67"/"no-5" noise.
_SLUG_FIXUPS = (
    (re.compile(r"\bNo\.?\s*(\d+)", re.I), r"\1"),
    (re.compile(r"\bOp\.?\s*(\d+)", re.I), r"op\1"),
    (re.compile(r"\bK\.?\s*(\d+)", re.I), r"k\1"),
    (re.compile(r"\bBWV\.?\s*(\d+)", re.I), r"bwv\1"),
    (re.compile(r"\bmovement\s*(\d+)", re.I), r"mvt\1"),
    (re.compile(r"[‘’“”]"), ""),
)


def slug(text: str, *, maxlen: int = 60) -> str:
    """Lowercase, ASCII, hyphen-joined.  Empty input yields ``"unknown"``."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    for pattern, repl in _SLUG_FIXUPS:
        text = pattern.sub(repl, text)
    text = _SLUG_STRIP.sub("-", text.lower()).strip("-")
    if len(text) > maxlen:
        text = text[:maxlen].rstrip("-")
    return text or "unknown"


#: Encoders title the same work in their own language, so "Symphonie No. 5" and
#: "Symphony No.5" would otherwise become two works.  Only the genre noun is
#: translated — never the movement or the number.
_GENRE_SPELLINGS = (
    (re.compile(r"\bsinfoni[ae]\b", re.I), "Symphony"),
    (re.compile(r"\bsymphonie\b", re.I), "Symphony"),
    (re.compile(r"\bkonzert\b", re.I), "Concerto"),
    (re.compile(r"\bconcerto grosso\b", re.I), "Concerto Grosso"),
)

#: A movement-level file often titles itself "<work>, Part 4".  That fragment is
#: about the file, not the work, and splitting on it keeps movements together.
_WORK_TAIL = re.compile(
    r"[,\s]*\b(?:part|pt\.?|mvt\.?|movement|mov\.?)\s*\d{1,2}\b\s*$", re.I)


def normalize_work_title(title: str) -> str:
    """Fold spelling and per-movement tails so one work stays one work."""
    title = (title or "").strip()
    for pattern, repl in _GENRE_SPELLINGS:
        title = pattern.sub(repl, title)
    previous = None
    while previous != title:
        previous = title
        title = _WORK_TAIL.sub("", title).strip(" ,-")
    return title


#: Encoders append life dates to the composer name in every punctuation style
#: there is — "Bach(1685 - 1750)", "Mendelssohn (1809-1847)", "Satie(1866 – 1925)",
#: and one truncated "Schubert (1979 - 1828".  All of them made the *year* the
#: surname, which is how the store grew a composer called "1750".
_LIFE_DATES = re.compile(
    r"[\(\[]?\s*\b1?\d{3}\s*[-–—]\s*1?\d{3}\b\s*[\)\]]?"   # 1685 - 1750
    r"|[\(\[]\s*\b1?\d{3}\b\s*[-–—]?\s*[\)\]]?"              # (1685
)


def clean_composer(raw: str) -> str:
    """The person's name, with the biography taken back off."""
    text = (raw or "").strip()
    text = _LIFE_DATES.sub(" ", text)
    text = re.sub(r"\b(arr\.|arranged by|attr\.|attributed to|ed\.)\s*", " ", text, flags=re.I)
    text = re.sub(r"[\(\[]\s*[\)\]]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,;-–—()[]")
    return text


#: Genres whose number identifies the work.  A qualifier immediately before the
#: genre is kept, because "Piano Concerto No.1" and "Violin Concerto No.1" by one
#: composer are different works and must not share a key.
_WORK_KEY = re.compile(
    r"\b(?:(piano|violin|cello|viola|flute|oboe|clarinet|horn|trumpet|organ|"
    r"harpsichord|double)\s+)?"
    r"(symphony|concerto|sonata|quartet|quintet|sextet|trio|overture|suite|"
    r"mass|requiem|rhapsody|serenade|nocturne|prelude|fugue|etude|ballade|"
    r"impromptu|waltz|mazurka|polonaise|variations)"
    r"\s*(?:no\.?\s*)?(\d+)\b",
    re.I,
)


#: A trailing thematic-catalogue number is metadata about the work, not part of
#: its name, and only one side of the library tends to carry it — IMSLP titles
#: "The Planets, Op.32" where the MusicXML header says "The Planets".
_TRAILING_CATALOGUE = re.compile(
    r"[,\s]+(?:op|opus|k|kv|bwv|hwv|wab|hob|rv|d|m|cd|s|th|jb|woo|anh|h|l|b|sz)\.?\s*"
    r"[0-9ivx]+[a-z]?(?:\s*[-/]\s*[0-9]+[a-z]?)*\s*$",
    re.I,
)

#: Stripping the catalogue off a bare genre name would merge every one of a
#: composer's nocturnes into a single work, so those keep their number.
_BARE_GENRE = {
    "symphony", "concerto", "sonata", "quartet", "quintet", "sextet", "trio",
    "overture", "suite", "mass", "requiem", "rhapsody", "serenade", "nocturne",
    "prelude", "fugue", "etude", "ballade", "impromptu", "waltz", "mazurka",
    "polonaise", "variations", "scherzo", "fantasia", "fantasy", "romance",
    "intermezzo", "capriccio", "toccata", "march", "song", "lieder",
}


def work_key(title: str) -> str:
    """A title stripped to what identifies the WORK, for joining across sources.

    The two halves of the library title the same piece differently — an IMSLP
    page says "Symphony No.5, Op.67", a MusicXML header says "Symphony No.5" —
    and keying on the full title split Beethoven's fifth into two works with no
    edition and no ground truth respectively.  Key on genre + number, and let the
    key, opus and nickname stay in the folder name where a reader wants them.
    """
    title = normalize_work_title(title)
    m = _WORK_KEY.search(title)
    if not m:
        stripped = _TRAILING_CATALOGUE.sub("", title).strip(" ,-")
        if stripped and slug(stripped) not in _BARE_GENRE:
            return slug(stripped)
        return slug(title)
    qualifier, genre, number = m.groups()
    return slug(" ".join(p for p in (qualifier, genre, number) if p))


def composer_surname(raw: str) -> str:
    """Surname from either order — "Beethoven, Ludwig van" or "Gustav Mahler".

    Sources disagree: IMSLP writes "Last, First", MuseScore exports often write
    "First Last".  A comma is the reliable signal; without one, take the last
    word and let the nobiliary particles ("van", "de") stay where they are.
    """
    raw = clean_composer(raw)
    if not raw:
        return ""
    if "," in raw:
        return raw.split(",", 1)[0].strip()
    parts = [p for p in raw.split() if p]
    # "J.S. Bach" and "Mendelssohn-Bartholdy" both end in the surname; an initial
    # ("J.S.") never does, so skip trailing tokens that are only initials.
    while parts and re.fullmatch(r"(?:[A-Z]\.?){1,3}", parts[-1]):
        parts.pop()
    return parts[-1] if parts else ""


def to_surname_first(name: str) -> str:
    """"Johann Sebastian Bach" -> "Bach, Johann Sebastian"; a comma form is left alone."""
    name = clean_composer(name)
    if not name or "," in name:
        return name
    parts = [p for p in name.split() if p]
    surname = composer_surname(name)
    if not surname or surname not in parts:
        return name
    idx = len(parts) - 1 - parts[::-1].index(surname)
    # Nobiliary particles belong to the surname but trail the given names in the
    # library form IMSLP uses: "Beethoven, Ludwig van", not "van Beethoven, Ludwig".
    start = idx
    while start > 0 and parts[start - 1].lower() in {
        "van", "von", "de", "da", "del", "della", "di", "le", "la", "der", "den",
    }:
        start -= 1
    given = " ".join(parts[:start] + parts[idx + 1:] + parts[start:idx])
    return f"{surname}, {given}".strip(" ,") if given else surname


def canonical_stem(composer: str, work: str, variant: str, source: str) -> str:
    """``<composer>--<work>--<variant>--<source>``.

    ``variant`` is the edition for a PDF (publisher + year) and the movement for
    a reference file; ``source`` is where it came from (``imslp575951``,
    ``gradus``).  Every field is slugged, so the stem is safe as a filename on
    any filesystem and readable when it turns up on its own.
    """
    fields = [slug(composer, maxlen=30), slug(work), slug(variant), slug(source, maxlen=30)]
    return "--".join(f for f in fields if f and f != "unknown") or "unknown"


def edition_slug_from_publisher(publisher: str, year: str = "") -> str:
    """"Joseph Aibl, Munich, 1896, plate 2832" -> ``aibl-1896``.

    The publisher string is free text from IMSLP, so take the first component
    (the house) and the first 4-digit year anywhere in it.  A missing year is
    fine — ``aibl`` still identifies the edition within one work.
    """
    head = (publisher or "").split(",")[0].strip()
    # Drop a leading given name: "Joseph Aibl" -> "Aibl", "Breitkopf & Hartel" stays.
    words = [w for w in head.split() if w]
    if len(words) == 2 and words[0][:1].isupper() and "&" not in head:
        head = words[1]
    if not year:
        m = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", publisher or "")
        year = m.group(1) if m else ""
    head_slug = slug(head, maxlen=24)
    # Some entries record only a year; "2016-2016" says nothing twice.
    if head_slug == year or head_slug == "unknown":
        head_slug = ""
    return "-".join(p for p in (head_slug, year) if p) or "unknown-edition"


# --------------------------------------------------------------------------
# catalog records
# --------------------------------------------------------------------------


@dataclass
class ScoreEntry:
    """One file in the library.  ``path`` is relative to :func:`library_root`."""

    kind: str  # "edition" | "reference"
    path: str
    work_id: str
    composer: str
    composer_slug: str
    title: str
    source: str  # "imslp" | "gradus" | "local"
    sha256: str
    bytes: int
    composer_source: str = ""
    variant: str = ""
    movement: str = ""
    catalogue: str = ""  # Op.67, K.550, BWV 846
    genre: str = ""
    pages: int | None = None
    has_text_layer: bool | None = None
    imslp_id: str = ""
    imslp_url: str = ""
    publisher: str = ""
    publisher_year: str = ""
    plate: str = ""
    editor: str = ""
    reprint: str = ""
    image_type: str = ""
    copyright: str = ""
    uploader: str = ""
    date_submitted: str = ""
    original_filename: str = ""
    origin_path: str = ""  # where it was imported from, for traceability
    dossier_prefix: str = ""  # joins to data/dossiers/<prefix>-mvtN.json
    added: str = ""
    notes: str = ""
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v not in ("", None, {}, [])}


def clean_text(value):
    """Strip what cannot survive a round trip to a UTF-8 JSON file.

    PDF metadata is arbitrary bytes as far as the format is concerned: one Peters
    scan carries a NUL and an unpaired surrogate in its title, which ``json``
    will happily serialise and then ``write_text`` refuses to encode — the write
    fails after the file has already been copied into the store.
    """
    if isinstance(value, str):
        cleaned = value.encode("utf-8", "replace").decode("utf-8", "replace")
        return "".join(ch for ch in cleaned if ch == "\n" or ch >= " ").strip()
    if isinstance(value, dict):
        return {k: clean_text(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_text(v) for v in value]
    return value


def sha256_of(path: Path, *, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def sidecar_path(file_path: Path) -> Path:
    return file_path.with_suffix(".json")


def write_json_atomic(target: Path, data: dict) -> Path:
    """Write via a temp file and rename.

    Two ingest runs overlapping left a zero-byte sidecar, which then broke the
    whole catalog rebuild — one truncated file taking down the index is a bad
    trade for a write that can be made atomic in three lines.
    """
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(clean_text(data), indent=2, ensure_ascii=False) + "\n")
        tmp.replace(target)
    except Exception:
        tmp.unlink(missing_ok=True)   # never leave a half-written stub behind
        raise
    return target


def write_sidecar(file_path: Path, entry: ScoreEntry) -> Path:
    return write_json_atomic(sidecar_path(file_path), entry.to_dict())


# --------------------------------------------------------------------------
# reading what is already there
# --------------------------------------------------------------------------


def musicxml_metadata(path: Path) -> dict:
    """Title / movement / composer as recorded *inside* a MusicXML file.

    Read the file rather than parse the filename: the filename is somebody's
    shorthand, the embedded header is what the encoder actually declared.
    """
    try:
        if path.suffix.lower() == ".mxl":
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                root = None
                if "META-INF/container.xml" in names:
                    container = z.read("META-INF/container.xml").decode("utf-8", "replace")
                    m = re.search(r'full-path="([^"]+)"', container)
                    if m:
                        root = m.group(1)
                if root is None or root not in names:
                    root = next(
                        (n for n in names
                         if n.lower().endswith((".xml", ".musicxml")) and not n.startswith("META-INF")),
                        "",
                    )
                if not root:
                    return {}
                head = z.read(root)[:8192]
        else:
            head = path.read_bytes()[:8192]
    except (zipfile.BadZipFile, OSError, StopIteration):
        return {}

    text = head.decode("utf-8", "replace")

    def grab(pattern: str) -> str:
        m = re.search(pattern, text, re.S)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""

    return {
        "work_title": grab(r"<work-title>(.*?)</work-title>"),
        "work_number": grab(r"<work-number>(.*?)</work-number>"),
        "movement_title": grab(r"<movement-title>(.*?)</movement-title>"),
        "movement_number": grab(r"<movement-number>(.*?)</movement-number>"),
        "composer": grab(r'<creator type="composer">(.*?)</creator>'),
        "encoder": grab(r"<software>(.*?)</software>"),
    }


def pdf_facts(path: Path) -> dict:
    """Page count and whether a text layer exists.

    The text-layer flag is not trivia — it decides whether margin instrument
    labels are free to read or need Surya/Vision (28% of the IMSLP corpus has
    one).  Absent PyMuPDF, return nothing rather than a guess.
    """
    try:
        import fitz  # type: ignore
    except ImportError:
        return {}
    try:
        with fitz.open(path) as doc:
            pages = doc.page_count
            probe = min(6, pages)
            chars = sum(len(doc[i].get_text().strip()) for i in range(probe))
            meta = clean_text({k: v for k, v in (doc.metadata or {}).items() if v})
    except Exception:  # noqa: BLE001 - a corrupt PDF must not abort a whole import
        return {}
    return {
        "pages": pages,
        # A page number stamped on each page is ~30 chars and is not a text layer.
        "has_text_layer": chars > 40 * max(1, probe // 2),
        "pdf_metadata": meta,
    }


def iter_store_files(root: Path | None = None) -> Iterator[Path]:
    """Every score file in the store, sidecars excluded."""
    base = root or library_root()
    if not base.exists():
        return
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix.lower() in EDITION_SUFFIXES | REFERENCE_SUFFIXES:
            yield path


# --------------------------------------------------------------------------
# catalog I/O
# --------------------------------------------------------------------------


def load_catalog(path: Path | None = None) -> dict:
    target = path or CATALOG_PATH
    if not target.exists():
        return {"schema_version": CATALOG_SCHEMA_VERSION, "entries": []}
    return json.loads(target.read_text())


def save_catalog(catalog: dict, path: Path | None = None) -> Path:
    target = path or CATALOG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    catalog["schema_version"] = CATALOG_SCHEMA_VERSION
    catalog["entries"] = sorted(
        catalog.get("entries", []),
        key=lambda e: (e.get("kind", ""), e.get("composer_slug", ""), e.get("path", "")),
    )
    catalog["count"] = len(catalog["entries"])
    return write_json_atomic(target, catalog)


#: Absolute paths into somebody's home directory describe THIS machine, not the
#: work.  They stay in the local sidecars, where they are useful for tracing a
#: file back to its source, and out of the committed index, where they would be
#: 40% of the bytes and meaningless on any other machine.
_LOCAL_ONLY_FIELDS = ("origin_path", "duplicate_origins")


def _catalog_view(entry: dict) -> dict:
    """The committed form of a sidecar."""
    origins = 1 + len(entry.get("duplicate_origins") or [])
    view = {k: v for k, v in entry.items() if k not in _LOCAL_ONLY_FIELDS}
    if origins > 1:
        view["local_copies"] = origins
    return view


def rebuild_catalog(path: Path | None = None) -> dict:
    """Merge every sidecar in the store into the tracked catalog.

    Sidecar-driven rather than filename-driven, so a file with no sidecar is
    REPORTED as unregistered instead of being silently invented into the index.
    """
    entries: list[dict] = []
    orphans: list[str] = []
    unreadable: list[str] = []
    root = library_root()
    for file_path in iter_store_files(root):
        side = sidecar_path(file_path)
        if not side.exists():
            orphans.append(str(file_path.relative_to(root)))
            continue
        try:
            entry = json.loads(side.read_text())
        except json.JSONDecodeError:
            unreadable.append(str(file_path.relative_to(root)))
            continue
        entry["path"] = str(file_path.relative_to(root))
        entries.append(_catalog_view(entry))
    catalog = {"entries": entries}
    if orphans:
        catalog["unregistered"] = sorted(orphans)
    if unreadable:
        catalog["unreadable_sidecars"] = sorted(unreadable)
    return save_catalog(catalog, path) and load_catalog(path)


def verify(catalog: dict | None = None) -> dict:
    """Which catalog entries are actually present, and is the content unchanged?

    The store is gitignored and the catalog is not, so on a fresh clone every
    entry is missing — that is the expected state, not an error, and the report
    says so by listing them separately from checksum mismatches.
    """
    cat = catalog or load_catalog()
    root = library_root()
    present, missing, changed = [], [], []
    for entry in cat.get("entries", []):
        path = root / entry["path"]
        if not path.exists():
            missing.append(entry["path"])
            continue
        if entry.get("sha256") and sha256_of(path) != entry["sha256"]:
            changed.append(entry["path"])
        else:
            present.append(entry["path"])
    return {"present": present, "missing": missing, "changed": changed}


# --------------------------------------------------------------------------
# back-compat with the old training-data layout
# --------------------------------------------------------------------------


def legacy_link_path(work_slug: str, imslp_id: str) -> Path:
    """The path ~20 benchmark scripts already hard-code for an IMSLP edition."""
    return LEGACY_IMSLP_ROOT / work_slug / "pdfs" / f"imslp-{imslp_id}" / "score.pdf"


def ensure_legacy_link(work_slug: str, imslp_id: str, target: Path) -> Path | None:
    """Point the old path at the new store with a symlink.

    Moving the three existing PDFs without this would break measured benchmarks
    whose numbers are quoted in NOTES.md — the link costs nothing and keeps
    every recorded result reproducible.
    """
    link = legacy_link_path(work_slug, imslp_id)
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        if link.is_symlink() and link.resolve() == target.resolve():
            return link
        link.unlink()
    link.symlink_to(target)
    return link


def summarize(entries: Iterable[dict]) -> str:
    rows = list(entries)
    by_kind: dict[str, int] = {}
    by_composer: dict[str, int] = {}
    for e in rows:
        by_kind[e.get("kind", "?")] = by_kind.get(e.get("kind", "?"), 0) + 1
        key = e.get("composer") or e.get("composer_slug") or "?"
        by_composer[key] = by_composer.get(key, 0) + 1
    lines = [f"{len(rows)} files  " + "  ".join(f"{k}={v}" for k, v in sorted(by_kind.items()))]
    for composer, n in sorted(by_composer.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"  {n:4d}  {composer}")
    return "\n".join(lines)
