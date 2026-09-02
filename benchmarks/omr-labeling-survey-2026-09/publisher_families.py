#!/usr/bin/env python3
"""Normalise the score-library catalog's ~213 raw publisher strings into
engraving-HOUSE families, and report per family whether it has scanned PDFs on
disk, its engraving era, and its orchestral works.

This is the reproducible evidence behind the "publisher axis" of
SURVEY_DESIGN.md. Engraving STYLE is what matters — a hollow notehead closes
differently across houses and decades — so the mapping groups by press +
national tradition + era, not by exact catalogue string.

    python3 benchmarks/omr-labeling-survey-2026-09/publisher_families.py
    python3 benchmarks/omr-labeling-survey-2026-09/publisher_families.py --orchestral

Reads data/score-library/catalog.json (committed) and checks library/editions/
(machine-local, gitignored) for on-disk presence. Run from the MAIN checkout;
library_root does not resolve from a worktree here (this script is deliberately
dependency-free and does not import tools.*).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CATALOG = os.path.join(REPO, "data", "score-library", "catalog.json")
LIB = os.path.join(REPO, "library")

# Orchestral repertoire filter (feedback_orchestral_only: survey orchestral scores).
ORCH = re.compile(
    r"symphon|concerto|overture|suite|poem|scheherazade|bolero|planets|1812|"
    r"serenade|romeo|francesca|espa|pictures|fountains|pines|daphnis|petrushka|"
    r"firebird|rite|nocturne|la.mer|iberia|rhapsod|variation|capriccio|marche|"
    r"fantas|slavonic|holberg|peer.gynt|academic|tragic",
    re.I,
)


def family(pub: str | None) -> str:
    """Map a raw publisher string to an engraving-house family."""
    p = (pub or "").lower()
    # IMSLP shorthand for 19th-c German collected critical editions (mostly
    # Breitkopf-engraved: Bach-Gesellschaft, the *Werke* series, *Sämtliche
    # Werke*). One broad house tradition; kept separate from the plain
    # Breitkopf Partitur-Bibliothek run because the decade and format differ.
    if re.search(r"complete|gesellschaft|gesamtausgabe|\baga\b|werke\)|linkwork", p):
        if "bärenreiter" in p or "neue mozart" in p:
            return "Barenreiter (modern Urtext)"
        return "German Collected-Works (Breitkopf tradition)"
    table = [
        ("breitkopf", "Breitkopf & Hartel (Leipzig)"),
        ("peters", "C.F. Peters / Edition Peters (Leipzig)"),
        ("eulenburg", "Eulenburg (miniature scores)"),
        ("litolff", "Litolff (Braunschweig 1870)"),
        ("simrock", "Simrock (Berlin/Bonn)"),
        ("durand", "Durand (Paris)"),
        ("novello", "Novello (London)"),
        ("jurgenson", "Jurgenson (Moscow)"),
        ("universal", "Universal Edition (Vienna)"),
        ("philharmonia", "Universal Edition (Vienna)"),
        ("schott", "Schott (Mainz)"),
        ("belaieff", "Belaieff (Leipzig)"),
        ("belaïeff", "Belaieff (Leipzig)"),
        ("gutheil", "Gutheil (Moscow)"),
        ("bessel", "Bessel (St. Petersburg)"),
        ("aibl", "Aibl (Munich)"),
        ("hansen", "Wilhelm Hansen (Copenhagen)"),
        ("hamelle", "Hamelle (Paris)"),
        ("enoch", "Enoch (Paris)"),
        ("goodwin", "Goodwin & Tabb (London)"),
        ("schirmer", "Schirmer (New York)"),
        ("leuckart", "Leuckart (Leipzig)"),
        ("fürstner", "Furstner (Berlin)"),
        ("furstner", "Furstner (Berlin)"),
        ("rahter", "Rahter (Hamburg)"),
        ("ricordi", "Ricordi (Milan)"),
        ("bote", "Bote & Bock (Berlin)"),
        ("wiener philh", "Wiener Philharmonischer Verlag"),
        ("kahnt", "Kahnt (Leipzig)"),
        ("hofmeister", "Hofmeister (Leipzig)"),
        ("augener", "Augener (London)"),
        ("weinberger", "Weinberger (Vienna)"),
        ("oxford", "OUP (London)"),
        ("russes de musique", "Editions Russes de Musique (Paris)"),
        ("r.m.v", "Editions Russes de Musique (Paris)"),
        ("schlesinger", "Schlesinger/Lienau (Berlin)"),
        ("lienau", "Schlesinger/Lienau (Berlin)"),
        ("fromont", "Fromont (Paris)"),
        ("schmidt", "A.P. Schmidt (Boston)"),
    ]
    for key, name in table:
        if key in p:
            return name
    # Everything else: modern typesets, blanked provenance, one-off houses.
    if re.match(r"^\s*(20\d\d|\(#|\*|catalog|snkl|univerzitet|pierre|john s|"
                r"shu-yu|knute|2016)", p) or p in ("", "(none)"):
        return "Other / modern-typeset / unknown provenance"
    return "Other minor houses"


def engraving_year(pub: str | None) -> int | None:
    """The plate/publication year in the publisher string (NOT the IMSLP upload
    date, which lives in date_submitted and would otherwise contaminate the era)."""
    m = re.search(r"\b(1[6789]\d\d)\b", pub or "")
    return int(m.group(1)) if m else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orchestral", action="store_true",
                    help="list orchestral works per family")
    args = ap.parse_args()

    entries = json.load(open(CATALOG))["entries"]
    eds = [e for e in entries if e.get("kind") == "edition"]

    fam: dict[str, list] = collections.defaultdict(list)
    for e in eds:
        fam[family(e.get("publisher"))].append(e)

    def on_disk(e) -> bool:
        return bool(e.get("path")) and os.path.exists(os.path.join(LIB, e["path"]))

    print(f"catalog: {len(eds)} editions, {len(fam)} engraving-house families\n")
    hdr = f"{'FAMILY':<44} {'eds':>4} {'disk':>4} {'scan':>4} {'orch':>4} {'txt':>4}  eras"
    print(hdr)
    print("-" * len(hdr))
    for f, es in sorted(fam.items(), key=lambda x: -len(x[1])):
        disk = sum(on_disk(e) for e in es)
        scan = sum(e.get("image_type") == "Normal Scan" for e in es)
        orch = sum(bool(ORCH.search((e.get("work_id") or "") + " " + (e.get("title") or ""))) for e in es)
        txt = sum(bool(e.get("has_text_layer")) for e in es)
        yrs = sorted({y for y in (engraving_year(e.get("publisher")) for e in es) if y})
        era = f"{yrs[0]}-{yrs[-1]}" if len(yrs) > 1 else (str(yrs[0]) if yrs else "?")
        print(f"{f:<44} {len(es):>4} {disk:>4} {scan:>4} {orch:>4} {txt:>4}  {era}")
        if args.orchestral:
            for e in es:
                if ORCH.search((e.get("work_id") or "") + " " + (e.get("title") or "")):
                    d = "on-disk" if on_disk(e) else "MISSING"
                    print(f"      - {e.get('composer','?')[:18]:18s} {(e.get('title') or '')[:34]:34s} "
                          f"imslp={e.get('imslp_id')} txt={int(bool(e.get('has_text_layer')))} {d}")


if __name__ == "__main__":
    main()
