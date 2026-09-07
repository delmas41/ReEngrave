"""Screen the census hits against an INDEPENDENT statement of what each work is
scored for.

The census reports geometry: a full-width rule standing alone between two
staves. Whether that is a percussion part or a piece of page furniture is a
question the geometry cannot answer. The score library carries an answer from a
different source entirely — the IMSLP work page's own instrumentation field,
stored with `source_kind: "catalog"`, which the library README makes the
load-bearing distinction precisely because it is independent of the MusicXML
anything is scored against.

⚠️ This is a SCREEN, not an adjudication, and it is wrong in both directions:

  * a work that IS scored for unpitched percussion does not prove THIS page
    prints it, or prints it on one line (a bass drum is often on a five-line
    staff, and a tacet page prints nothing);
  * a work that is NOT so scored does not prove the detection is junk — a
    printed rule can be a divider, a cue staff, or an ossia.

What it is good for is RANKING: it says which hits to put in front of a human
first, and it gives a base rate that geometry alone cannot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]

# `instruments.py` marks Percussion `unpitched=True`, but the lexicon collapses
# the whole family onto one name, so the roster's own words are what separate a
# one-line part from a timpani. Kept as substrings of the roster entry's `text`,
# which is the raw IMSLP fragment.
UNPITCHED_WORDS = (
    "percussion", "bass drum", "side drum", "snare", "tenor drum", "drum",
    "cymbal", "triangle", "tambourine", "tam-tam", "tamtam", "tam tam",
    "castanet", "gong", "whip", "ratchet", "wood block", "woodblock",
    "gran cassa", "tamburo", "piatti", "gran tamburo", "military drum",
    "gr. cassa", "gr.cassa", "rute", "gr. trommel", "kleine trommel",
    "gr trommel", "gr.tr", "kl.tr", "becken", "gr. tr.", "kl. tr.",
    "gong", "gongs", "gran tamburo", "sleigh bell", "gr. drum",
    "prc", "perc", "batterie", "schlagzeug", "field drum", "crotales",
    "castanets", "wind-machine", "wind machine",
)
# Deliberately EXCLUDED: timpani, glockenspiel, xylophone, celesta, harp,
# bells, chimes, tubular bells, marimba, vibraphone. Every one of those is
# pitched and is printed on five lines — counting them would tell us a work has
# "percussion" while saying nothing about a one-line rule.


def has_unpitched(work: dict) -> tuple[bool, list[str]]:
    """⚠️ Reads the RAW roster string as well as the parsed roster, because the
    parser drops percussion on this corpus in two distinct ways and both bit
    this screen:

      * `debussy--la-mer` -- ONE FIELD HOLDING BOTH DIALECTS. The numeric
        dialect parses (`tmp`, `3prc`) and the prose list after `{{More}}`,
        which names bass drum / cymbals / tam-tam / triangle, does not. Same
        shape CLAUDE.md records for Bach's B minor Mass.
      * `ravel--daphnis-et-chloe` -- an `{{OnStInst}}` / `{{OffStInst}}` split
        where only the OFF-stage band survives: the roster is
        `piccolo, E clarinet, horn, trumpet` and the entire on-stage lineup,
        percussion included, is dropped. Same family as the Tannhauser
        cast-list fault.

    Both are reported to the library workstream rather than fixed here
    (`tools/library/` is not this session's file). Reading the raw string is
    the right move for a SCREEN anyway: it cannot be blinded by a parse.
    """
    inst = (work or {}).get("instrumentation") or {}
    hits = []
    raw = " ".join(str(v) for v in (inst.get("raw") or {}).values()).lower()
    for w in UNPITCHED_WORDS:
        if w in raw:
            hits.append(f"(raw) {w}")
            break
    for e in inst.get("roster") or []:
        text = str(e.get("text") or "").lower()
        if any(w in text for w in UNPITCHED_WORDS):
            hits.append(e.get("text"))
    for frag in inst.get("unparsed") or []:
        text = str(frag if isinstance(frag, str) else frag.get("text", "")).lower()
        if any(w in text for w in UNPITCHED_WORDS):
            hits.append(f"(unparsed) {text}")
    return bool(hits), hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", default="census.json")
    args = ap.parse_args(argv)

    cat = json.loads((ROOT / "data/score-library/catalog.json").read_text())
    works = cat.get("works") or {}
    doc = json.loads((HERE / args.census).read_text())
    ok = [r for r in doc["rows"] if "n_one" in r]
    hits = [r for r in ok if r.get("n_one")]

    # base rate: of every work the census READ, how many are scored for it?
    read_ids = {r["work_id"] for r in ok}
    base = sum(1 for w in read_ids if has_unpitched(works.get(w))[0])

    rows, plaus, susp = [], 0, 0
    seen: dict[str, tuple[bool, list[str]]] = {}
    for r in sorted(hits, key=lambda r: (r["work_id"], r["page"])):
        wid = r["work_id"]
        if wid not in seen:
            seen[wid] = has_unpitched(works.get(wid))
        yes, evid = seen[wid]
        plaus += r["n_one"] if yes else 0
        susp += 0 if yes else r["n_one"]
        rows.append({"work_id": wid, "path": r["path"], "page": r["page"],
                     "n_one": r["n_one"], "n_five": r["n_five"],
                     "roster_has_unpitched": yes, "roster_evidence": evid[:4],
                     "has_roster": bool((works.get(wid) or {}).get(
                         "instrumentation"))})

    print(f"census works read                {len(read_ids)}")
    print(f"  ...of which scored for unpitched percussion   {base} "
          f"({100.0*base/max(1,len(read_ids)):.0f}%)  <- BASE RATE")
    print()
    hit_ids = sorted({r['work_id'] for r in hits})
    hit_yes = sum(1 for w in hit_ids if seen[w][0])
    print(f"works WITH a one-line detection  {len(hit_ids)}")
    print(f"  ...of which scored for unpitched percussion   {hit_yes} "
          f"({100.0*hit_yes/max(1,len(hit_ids)):.0f}%)  <- ENRICHED?")
    print()
    print(f"one-line staves on a work scored for it (PLAUSIBLE)  {plaus}")
    print(f"one-line staves on a work NOT scored for it (SUSPECT) {susp}")
    print()
    print("SUSPECT hits — put these in front of a human first:")
    for r in rows:
        if not r["roster_has_unpitched"]:
            tag = "" if r["has_roster"] else "  [NO ROSTER HELD]"
            print(f"  {r['work_id']:44} p{r['page']:<4} "
                  f"{r['n_one']} rule(s){tag}")
    print()
    print("PLAUSIBLE hits, with the roster words that carried them:")
    for w in hit_ids:
        if seen[w][0]:
            print(f"  {w:44} {seen[w][1][:3]}")

    (HERE / "roster-screen.json").write_text(json.dumps({
        "base_rate_works_scored_for_unpitched": base,
        "works_read": len(read_ids),
        "hit_works": len(hit_ids), "hit_works_scored_for_unpitched": hit_yes,
        "staves_plausible": plaus, "staves_suspect": susp,
        "rows": rows}, indent=1) + "\n")
    print("\nwrote", HERE / "roster-screen.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
