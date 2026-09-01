#!/usr/bin/env python3
"""Pick the best full score on IMSLP for a list of works, and write a download list.

    python3 -m tools.library.build_wishlist --out wishlist.json --delay 4

One page fetch per work, no file downloads, so this touches nothing the
JavaScript download gate protects.  For each work it reads every file in the
*Full Scores* section — publisher, editor, scan type, page count — and ranks
them for OMR use:

* a **Normal Scan** of a real engraving beats a modern typeset, because a
  typeset is not the problem this project has to solve;
* a named publisher (Breitkopf, Simrock, Eulenburg, Peters) beats an anonymous
  upload, since the edition is the thing being catalogued;
* a page count in the plausible band for a full score beats one that is half a
  movement or a whole complete-works volume.

Works already held in the library are skipped unless ``--include-held``.
"""

from __future__ import annotations

import argparse
import html as H
import json
import re
import sys
import time
import urllib.parse

from tools.library import score_library as lib
from tools.library.imslp_meta import page_files

# (composer surname, work label, IMSLP page title)
WORKS: list[tuple[str, str, str]] = [
    # --- Beethoven: the cycle, minus the three already held -------------------
    ("Beethoven", "Symphony No.1", "Symphony No.1, Op.21 (Beethoven, Ludwig van)"),
    ("Beethoven", "Symphony No.2", "Symphony No.2, Op.36 (Beethoven, Ludwig van)"),
    ("Beethoven", "Symphony No.3 'Eroica'", "Symphony No.3, Op.55 (Beethoven, Ludwig van)"),
    ("Beethoven", "Symphony No.4", "Symphony No.4, Op.60 (Beethoven, Ludwig van)"),
    ("Beethoven", "Symphony No.7", "Symphony No.7, Op.92 (Beethoven, Ludwig van)"),
    ("Beethoven", "Symphony No.8", "Symphony No.8, Op.93 (Beethoven, Ludwig van)"),
    ("Beethoven", "Egmont Overture", "Egmont, Op.84 (Beethoven, Ludwig van)"),
    ("Beethoven", "Coriolan Overture", "Coriolan Overture, Op.62 (Beethoven, Ludwig van)"),
    ("Beethoven", "Leonore Overture No.3", "Leonore Overture No.3, Op.72b (Beethoven, Ludwig van)"),
    # --- Brahms ---------------------------------------------------------------
    ("Brahms", "Symphony No.1", "Symphony No.1, Op.68 (Brahms, Johannes)"),
    ("Brahms", "Symphony No.2", "Symphony No.2, Op.73 (Brahms, Johannes)"),
    ("Brahms", "Symphony No.3", "Symphony No.3, Op.90 (Brahms, Johannes)"),
    ("Brahms", "Symphony No.4", "Symphony No.4, Op.98 (Brahms, Johannes)"),
    ("Brahms", "Variations on a Theme by Haydn", "Variations on a Theme by Haydn, Op.56 (Brahms, Johannes)"),
    ("Brahms", "Academic Festival Overture", "Academic Festival Overture, Op.80 (Brahms, Johannes)"),
    ("Brahms", "Violin Concerto", "Violin Concerto, Op.77 (Brahms, Johannes)"),
    # --- Mozart ---------------------------------------------------------------
    ("Mozart", "Symphony No.25", "Symphony No.25 in G minor, K.183/173dB (Mozart, Wolfgang Amadeus)"),
    ("Mozart", "Symphony No.29", "Symphony No.29 in A major, K.201/186a (Mozart, Wolfgang Amadeus)"),
    ("Mozart", "Symphony No.31 'Paris'", "Symphony No.31 in D major, K.297/300a (Mozart, Wolfgang Amadeus)"),
    ("Mozart", "Symphony No.35 'Haffner'", "Symphony No.35 in D major, K.385 (Mozart, Wolfgang Amadeus)"),
    ("Mozart", "Symphony No.36 'Linz'", "Symphony No.36 in C major, K.425 (Mozart, Wolfgang Amadeus)"),
    ("Mozart", "Symphony No.38 'Prague'", "Symphony No.38 in D major, K.504 (Mozart, Wolfgang Amadeus)"),
    ("Mozart", "Symphony No.39", "Symphony No.39 in E-flat major, K.543 (Mozart, Wolfgang Amadeus)"),
    ("Mozart", "Symphony No.40", "Symphony No.40 in G minor, K.550 (Mozart, Wolfgang Amadeus)"),
    ("Mozart", "Symphony No.41 'Jupiter'", "Symphony No.41 in C major, K.551 (Mozart, Wolfgang Amadeus)"),
    ("Mozart", "Overture to Le nozze di Figaro", "Le nozze di Figaro, K.492 (Mozart, Wolfgang Amadeus)"),
    ("Mozart", "Requiem", "Requiem in D minor, K.626 (Mozart, Wolfgang Amadeus)"),
    # --- Haydn ----------------------------------------------------------------
    ("Haydn", "Symphony No.94 'Surprise'", "Symphony No.94 in G major, Hob.I:94 (Haydn, Joseph)"),
    ("Haydn", "Symphony No.100 'Military'", "Symphony No.100 in G major, Hob.I:100 (Haydn, Joseph)"),
    ("Haydn", "Symphony No.101 'Clock'", "Symphony No.101 in D major, Hob.I:101 (Haydn, Joseph)"),
    ("Haydn", "Symphony No.103 'Drumroll'", "Symphony No.103 in E-flat major, Hob.I:103 (Haydn, Joseph)"),
    ("Haydn", "Symphony No.104 'London'", "Symphony No.104 in D major, Hob.I:104 (Haydn, Joseph)"),
    # --- Schubert / Mendelssohn / Schumann ------------------------------------
    ("Schubert", "Symphony No.5", "Symphony No.5, D.485 (Schubert, Franz)"),
    ("Schubert", "Symphony No.8 'Unfinished'", "Symphony No.8, D.759 (Schubert, Franz)"),
    ("Schubert", "Symphony No.9 'Great'", "Symphony No.9, D.944 (Schubert, Franz)"),
    ("Mendelssohn", "Symphony No.3 'Scottish'", "Symphony No.3, Op.56 (Mendelssohn, Felix)"),
    ("Mendelssohn", "Symphony No.4 'Italian'", "Symphony No.4, Op.90 (Mendelssohn, Felix)"),
    ("Mendelssohn", "A Midsummer Night's Dream Overture", "A Midsummer Night's Dream Overture, Op.21 (Mendelssohn, Felix)"),
    ("Mendelssohn", "Violin Concerto", "Violin Concerto, Op.64 (Mendelssohn, Felix)"),
    ("Schumann", "Symphony No.1 'Spring'", "Symphony No.1, Op.38 (Schumann, Robert)"),
    ("Schumann", "Symphony No.3 'Rhenish'", "Symphony No.3, Op.97 (Schumann, Robert)"),
    ("Schumann", "Symphony No.4", "Symphony No.4, Op.120 (Schumann, Robert)"),
    # --- Berlioz / Franck / Saint-Saens ---------------------------------------
    ("Berlioz", "Symphonie fantastique", "Symphonie fantastique, H 48 (Berlioz, Hector)"),
    ("Berlioz", "Harold en Italie", "Harold en Italie, H 68 (Berlioz, Hector)"),
    ("Berlioz", "Le Carnaval romain", "Le Carnaval romain, H 95 (Berlioz, Hector)"),
    ("Franck", "Symphony in D minor", "Symphony in D minor, M.48 (Franck, César)"),
    ("Saint-Saens", "Symphony No.3 'Organ'", "Symphony No.3, Op.78 (Saint-Saëns, Camille)"),
    ("Saint-Saens", "Danse macabre", "Danse macabre, Op.40 (Saint-Saëns, Camille)"),
    # --- Tchaikovsky ----------------------------------------------------------
    ("Tchaikovsky", "Symphony No.4", "Symphony No.4, Op.36 (Tchaikovsky, Pyotr)"),
    ("Tchaikovsky", "Symphony No.5", "Symphony No.5, Op.64 (Tchaikovsky, Pyotr)"),
    ("Tchaikovsky", "Symphony No.6 'Pathetique'", "Symphony No.6, Op.74 (Tchaikovsky, Pyotr)"),
    ("Tchaikovsky", "Romeo and Juliet", "Romeo and Juliet, TH 42 (Tchaikovsky, Pyotr)"),
    ("Tchaikovsky", "1812 Overture", "1812 Overture, Op.49 (Tchaikovsky, Pyotr)"),
    ("Tchaikovsky", "The Nutcracker Suite", "The Nutcracker Suite, Op.71a (Tchaikovsky, Pyotr)"),
    ("Tchaikovsky", "Serenade for Strings", "Serenade for Strings, Op.48 (Tchaikovsky, Pyotr)"),
    # --- Dvorak / Smetana / Borodin / Rimsky ----------------------------------
    ("Dvorak", "Symphony No.7", "Symphony No.7, Op.70 (Dvořák, Antonín)"),
    ("Dvorak", "Symphony No.8", "Symphony No.8, Op.88 (Dvořák, Antonín)"),
    ("Dvorak", "Symphony No.9 'New World'", "Symphony No.9, Op.95 (Dvořák, Antonín)"),
    ("Dvorak", "Cello Concerto", "Cello Concerto, Op.104 (Dvořák, Antonín)"),
    ("Smetana", "Vltava (The Moldau)", "Má vlast, JB 1:112 (Smetana, Bedřich)"),
    ("Borodin", "Symphony No.2", "Symphony No.2 (Borodin, Aleksandr)"),
    ("Rimsky-Korsakov", "Scheherazade", "Scheherazade, Op.35 (Rimsky-Korsakov, Nikolay)"),
    ("Rimsky-Korsakov", "Capriccio espagnol", "Capriccio espagnol, Op.34 (Rimsky-Korsakov, Nikolay)"),
    ("Mussorgsky", "Pictures at an Exhibition (orch. Ravel)", "Pictures at an Exhibition (Mussorgsky, Modest)"),
    # --- Bruckner / Mahler ----------------------------------------------------
    ("Bruckner", "Symphony No.4 'Romantic'", "Symphony No.4 in E-flat major, WAB 104 (Bruckner, Anton)"),
    ("Bruckner", "Symphony No.5", "Symphony No.5 in B-flat major, WAB 105 (Bruckner, Anton)"),
    ("Bruckner", "Symphony No.7", "Symphony No.7 in E major, WAB 107 (Bruckner, Anton)"),
    ("Bruckner", "Symphony No.8", "Symphony No.8 in C minor, WAB 108 (Bruckner, Anton)"),
    ("Bruckner", "Symphony No.9", "Symphony No.9 in D minor, WAB 109 (Bruckner, Anton)"),
    ("Mahler", "Symphony No.1", "Symphony No.1 (Mahler, Gustav)"),
    ("Mahler", "Symphony No.2 'Resurrection'", "Symphony No.2 (Mahler, Gustav)"),
    ("Mahler", "Symphony No.4", "Symphony No.4 (Mahler, Gustav)"),
    ("Mahler", "Symphony No.6", "Symphony No.6 (Mahler, Gustav)"),
    ("Mahler", "Symphony No.9", "Symphony No.9 (Mahler, Gustav)"),
    # --- Sibelius / Nielsen / Elgar / Vaughan Williams -------------------------
    ("Sibelius", "Symphony No.2", "Symphony No.2, Op.43 (Sibelius, Jean)"),
    ("Sibelius", "Symphony No.5", "Symphony No.5, Op.82 (Sibelius, Jean)"),
    ("Sibelius", "Finlandia", "Finlandia, Op.26 (Sibelius, Jean)"),
    ("Sibelius", "Violin Concerto", "Violin Concerto, Op.47 (Sibelius, Jean)"),
    ("Nielsen", "Symphony No.4 'Inextinguishable'", "Symphony No.4, Op.29 (Nielsen, Carl)"),
    ("Elgar", "Enigma Variations", "Variations on an Original Theme, Op.36 (Elgar, Edward)"),
    ("Elgar", "Symphony No.1", "Symphony No.1, Op.55 (Elgar, Edward)"),
    ("Elgar", "Cello Concerto", "Cello Concerto, Op.85 (Elgar, Edward)"),
    ("Vaughan Williams", "Fantasia on a Theme by Thomas Tallis", "Fantasia on a Theme by Thomas Tallis (Vaughan Williams, Ralph)"),
    # --- French / Russian moderns ---------------------------------------------
    ("Debussy", "Prelude a l'apres-midi d'un faune", "Prélude à l'après-midi d'un faune (Debussy, Claude)"),
    ("Debussy", "Nocturnes", "Nocturnes (Debussy, Claude)"),
    ("Ravel", "Daphnis et Chloe Suite No.2", "Daphnis et Chloé (Ravel, Maurice)"),
    ("Ravel", "Rapsodie espagnole", "Rapsodie espagnole (Ravel, Maurice)"),
    ("Ravel", "Ma mere l'Oye", "Ma mère l'Oye (Ravel, Maurice)"),
    ("Stravinsky", "The Firebird Suite", "The Firebird (Stravinsky, Igor)"),
    ("Stravinsky", "Petrushka", "Petrushka (Stravinsky, Igor)"),
    ("Prokofiev", "Symphony No.1 'Classical'", "Symphony No.1, Op.25 (Prokofiev, Sergey)"),
    # --- Richard Strauss ------------------------------------------------------
    ("R. Strauss", "Don Juan", "Don Juan, Op.20 (Strauss, Richard)"),
    ("R. Strauss", "Tod und Verklarung", "Tod und Verklärung, Op.24 (Strauss, Richard)"),
    ("R. Strauss", "Also sprach Zarathustra", "Also sprach Zarathustra, Op.30 (Strauss, Richard)"),
    ("R. Strauss", "Ein Heldenleben", "Ein Heldenleben, Op.40 (Strauss, Richard)"),
    ("R. Strauss", "Don Quixote", "Don Quixote, Op.35 (Strauss, Richard)"),
    # --- Overtures and lighter orchestral -------------------------------------
    ("Wagner", "Die Meistersinger Prelude", "Die Meistersinger von Nürnberg, WWV 96 (Wagner, Richard)"),
    ("Rossini", "William Tell Overture", "Guillaume Tell (Rossini, Gioacchino)"),
    ("Weber", "Der Freischutz Overture", "Der Freischütz, Op.77 (Weber, Carl Maria von)"),
    ("Bizet", "L'Arlesienne Suite No.1", "L'Arlésienne (Bizet, Georges)"),
    ("Grieg", "Peer Gynt Suite No.1", "Peer Gynt Suite No.1, Op.46 (Grieg, Edvard)"),
    ("Holst", "The Planets", "The Planets, Op.32 (Holst, Gustav)"),
    # --- Under-recorded composers already represented in the reference half ----
    ("Beach", "Gaelic Symphony", "Symphony in E minor, Op.32 (Beach, Amy Marcy)"),
    ("Boulanger", "D'un matin de printemps", "D'un matin de printemps (Boulanger, Lili)"),
    ("Coleridge-Taylor", "Ballade in A minor", "Ballade, Op.33 (Coleridge-Taylor, Samuel)"),
    ("Chaminade", "Concertino for Flute", "Concertino, Op.107 (Chaminade, Cécile)"),
]

#: Publishers whose engravings are the ones an OMR system will actually meet.
GOOD_PUBLISHER = re.compile(
    r"breitkopf|simrock|peters|eulenburg|universal|durand|schott|litolff|"
    r"b(ä|a)renreiter|novello|belaieff|jurgenson|bote|f(ü|u)rstner|artaria|"
    r"philharmonia|kalmus|augener|steingr(ä|a)ber|hofmeister|senff|rieter",
    re.I,
)


def candidates_for(title: str) -> list[dict]:
    """Full scores on a work page, with publisher and scan type attached."""
    out = []
    for f in page_files(title):
        if not f.get("full_score"):
            continue
        desc = f.get("listed_description") or f.get("file_description") or ""
        if not re.search(r"complete score|full score", desc, re.I):
            continue
        out.append({
            "imslp_id": f["imslp_id"],
            "description": desc,
            "pages": f.get("listed_pages"),
            "publisher": f.get("publisher_information", ""),
            "editor": f.get("editor", ""),
            "scan": f.get("image_type", ""),
            "copyright": f.get("copyright", ""),
        })
    return out


def score_candidate(c: dict, familiar: set[str]) -> float:
    """Higher is a better OMR target.

    The ranking is about what the pipeline has to READ, not what a player would
    rather own: a 19th-century engraving is the actual problem, a modern typeset
    is not, and a manuscript is a different project entirely.
    """
    points = 0.0
    scan = (c.get("scan") or "").lower()
    if "typeset" in scan:
        points -= 1.5
    elif "manuscript" in scan:
        points -= 3.0
    elif "scan" in scan:
        points += 3.0

    publisher = c.get("publisher") or ""
    if GOOD_PUBLISHER.search(publisher):
        points += 2.5
    elif publisher:
        points += 0.5
    # An edition series we already hold makes cross-work comparison cleaner:
    # same engraver, same conventions, so a difference is the music, not the print.
    if any(word and word in publisher.lower() for word in familiar):
        points += 2.0

    pages = c.get("pages") or 0
    if 40 <= pages <= 320:
        points += 1.5
    elif pages > 400:
        points -= 1.5
    elif pages and pages < 20:
        points -= 2.0

    if re.search(r"preview|incomplete|excerpt|fragment|color|colour", c["description"], re.I):
        points -= 2.0
    if not c.get("copyright", "").lower().startswith("public domain"):
        points -= 0.5
    return points


def familiar_publishers(catalog: dict) -> dict[str, set[str]]:
    """Publisher words already represented per composer, for the consistency bonus."""
    out: dict[str, set[str]] = {}
    for e in catalog.get("entries", []):
        if e.get("kind") != "edition" or not e.get("publisher"):
            continue
        words = {w for w in re.findall(r"[a-z]{5,}", e["publisher"].lower())
                 if w not in {"verlag", "edition", "werke", "complete", "publications"}}
        out.setdefault(e.get("composer_slug", ""), set()).update(words)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="wishlist.json")
    ap.add_argument("--delay", type=float, default=4.0)
    ap.add_argument("--include-held", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    catalog = lib.load_catalog()
    familiar_pub = familiar_publishers(catalog)
    held = {e.get("imslp_id") for e in catalog.get("entries", []) if e.get("imslp_id")}
    held_works = {e["work_id"] for e in catalog.get("entries", []) if e.get("kind") == "edition"}

    rows = []
    works = WORKS[: args.limit] if args.limit else WORKS
    for i, (composer, label, title) in enumerate(works):
        if i:
            time.sleep(args.delay)
        try:
            candidates = candidates_for(title)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {label}: {exc}", file=sys.stderr)
            rows.append({"composer": composer, "work": label, "page_title": title,
                         "error": str(exc)})
            continue

        familiar = familiar_pub.get(lib.slug(composer, maxlen=30), set())
        ranked = sorted(candidates, key=lambda c: score_candidate(c, familiar), reverse=True)
        best = ranked[0] if ranked else None
        work_id = f"{lib.slug(composer, maxlen=30)}--{lib.work_key(label)}"
        row = {
            "composer": composer,
            "work": label,
            "page_title": title,
            "page_url": "https://imslp.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
            "already_held": work_id in held_works,
            "n_full_scores": len(candidates),
        }
        if best:
            row.update({
                "imslp_id": best["imslp_id"],
                "download_url": f"https://imslp.org/wiki/Special:ReverseLookup/{best['imslp_id']}",
                "pages": best["pages"],
                "publisher": best["publisher"],
                "editor": best["editor"],
                "scan": best["scan"],
                "description": best["description"],
                "copyright": best.get("copyright", ""),
                "held": best["imslp_id"] in held,
                "runner_up": ranked[1]["imslp_id"] if len(ranked) > 1 else None,
                "alternatives": [c["imslp_id"] for c in ranked[1:4]],
            })
        rows.append(row)
        mark = "held" if row.get("held") else ""
        print(f"  {composer:16.16s} {label:38.38s} "
              f"IMSLP{row.get('imslp_id','?'):<9} {str(row.get('pages','?')):>4}pp  "
              f"{row.get('publisher','')[:44]:44.44s} {mark}", flush=True)

    with open(args.out, "w") as fh:
        json.dump({"works": rows}, fh, indent=2, ensure_ascii=False)
    ok = [r for r in rows if r.get("imslp_id")]
    print(f"\n{len(ok)}/{len(rows)} works resolved to a full score -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
