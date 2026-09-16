#!/usr/bin/env python3
"""REACH of the roster repair — what a supplied roster changes, and where.

    python3 benchmarks/omr-producer-consumer-2026-09/roster_reach.py

⚠️⚠️ **IT DRIVES THE STAGED DECISION, NOT `work_roster.decide`, AND THAT IS
THE WHOLE POINT.** The RULE was measured a week ago — 28 firings over 1,422
real margin labels, every one hand-adjudicated correct. What was never
measured, because it could not happen, is the rule ARRIVING: `roster` was
threaded `run_staged` -> `run_staged_on` -> `gather` -> `gather_external`,
forwarded at every link and supplied by nobody, and `Q.ROSTER_ENTRY` was
filed on the DOCUMENT while `adjudicate_instrument` runs at STAFF. A probe
that called `decide()` directly would re-measure the rule and say nothing
about either fault. This one builds a `Log`, runs GATHER's own
`gather_external`, runs `adjudicate.run`, and reads the VERDICTS.

⚠️ **REACH FIRST, AND A DEAD INSTRUMENT EXITS NON-ZERO.** *A change that
moves nothing because it is inert and one that moves nothing because the page
holds nothing to move are the same number.* So this prints how many labels it
read and how many rosters it resolved BEFORE any result, and refuses at zero.

⚠️ **WHAT IS NOT ESTABLISHED: ACCURACY.** Nothing here is checked against a
print. The labels are what the readers actually emitted (committed dumps, not
re-read), and every verdict change is adjudicated by the rule's own recorded
reasoning, not by looking at the page. A `vetoed` row is a claim that the
lexicon was wrong, and the ONE thing that would settle it is the crop.
"""

from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate                      # noqa: E402
from tools.omr.staged import adjudicators                    # noqa: E402,F401
from tools.omr.staged import gather, record as R             # noqa: E402
from tools.omr.staged.record import Log, Outcome, Q, READERS  # noqa: E402
from tools.omr.work_roster import work_roster                 # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]

#: ⚠️⚠️ **DERIVED FROM THE CATALOG, AND THE FIRST DRAFT HAND-TYPED IT AND WAS
#: WRONG.** The label dumps name a SOURCE (`beethoven5-984073-scan`), which is
#: an edition; the roster is keyed on the WORK. I wrote out the mapping —
#: `beethoven--symphony-5-op68`-style ids read off the library's DIRECTORY
#: names — and every one of the eight was wrong, because the catalog keys on
#: **genre + number** (`beethoven--symphony-5`), never on the opus. The arm
#: reported *"works the CATALOG holds a roster for: 0"* on the very document
#: the repair was built for. ⚠️ It reported that rather than reporting zero
#: MOVES, which is the reach-first rule paying for itself — but it is still a
#: hand list inside a probe for a tool whose whole thesis is *derive, never
#: hand-list*, and it took a `work_id_for_pdf` call to notice.
#:
#: What survives by hand is only the IMSLP id, which is IN the source string;
#: the join to a work is `work_roster`'s own, off the catalog's editions.
SOURCE_IMSLP = {
    "beethoven5-575951-textlayer": "imslp575951",
    "beethoven5-984073-scan": "imslp984073",
    "beethoven6-504082-textlayer": "imslp504082",
    "brahms1-breitkopf-scan": "imslp317803",
    "dvorak9-simrock-scan": "imslp51629",
}

#: For dumps whose source names no IMSLP id, the PDF the page came from. The
#: id is still derived — `work_id_for_pdf` walks the path against the catalog.
SOURCE_PDF_HINT = {
    "ravel-bolero-textlayer": "ravel--bolero",
    "debussy-lamer-scan": "debussy--la-mer",
    "mahler5-local-scan": "mahler--symphony-5",
    "bach-brandenburg3-peters": "bach--concerto-3",
}


def _work_for(source: str):
    """The catalogued work a label dump's SOURCE belongs to, or None."""
    from tools.omr.work_roster import work_id_for_pdf
    key = SOURCE_IMSLP.get(source)
    if key:
        return work_id_for_pdf(key)
    hint = SOURCE_PDF_HINT.get(source)
    # ⚠️ A hint is only accepted where the CATALOG holds that id. A name the
    # catalog does not know returns None rather than being matched to
    # something near it — `roster_for_pdf`'s own rule, inherited.
    if hint and work_roster(hint) is not None:
        return hint
    return None

REACH_LOG = (ROOT / "benchmarks/omr-part-join-phase2-2026-09/out/"
                    "margin-label-reach.log")
LEXICON = ROOT / "benchmarks/omr-lexicon-2026-09/labels.json"


#: ⚠️ A REAL SYSTEM IS NOT 427 STAVES. Ravel's dump is 427 labels over many
#: pages; putting them all in one `Q.SYSTEM_STAFF_COUNT` makes
#: `adjudicate_part_partition` and `adjudicate_slot_index` do work no printed
#: page ever asks for, and the first run of this probe spent 28 minutes of CPU
#: on it. Chunking is BOTH faster and more faithful — and it changes no
#: verdict here, because `Q.INSTRUMENT` depends on the staff's own label and
#: the DOCUMENT's roster, neither of which crosses a chunk.
SYSTEM_MAX = 24


def verdicts_for(texts, roster):
    """Run GATHER + ADJUDICATE over one system's labels, with/without roster.

    One staff per label, so every label gets its own verdict and the
    `Q.MARGIN_LABEL` row is the only evidence in play.
    """
    out = []
    for start in range(0, len(texts), SYSTEM_MAX):
        chunk = texts[start:start + SYSTEM_MAX]
        log = Log()
        if roster is not None:
            gather.gather_external(log, None, roster=roster)
        for i, text in enumerate(chunk):
            sub = R.staff(0, 0, i)
            log.observe(sub, Q.STAFF_ORDINAL, i, reader=READERS.GEOMETRY,
                        frame="system")
            log.observe(sub, Q.MARGIN_LABEL, text, reader=READERS.TEXT_LAYER,
                        frame="system_margin")
        log.observe(R.system(0, 0), Q.SYSTEM_STAFF_COUNT, len(chunk),
                    reader=READERS.GEOMETRY, frame="system")
        adjudicate.run(log)
        for i in range(len(chunk)):
            v = log.verdict(Q.INSTRUMENT, R.staff(0, 0, i))
            out.append((None if v is None or v.outcome is Outcome.ABSTAINED
                        else v.value["name"],
                        None if v is None else v.reason,
                        {} if v is None else (v.detail or {})))
    return out


def arm(name, groups):
    """`groups` is `{work_id: [label, ...]}`. Prints reach, then the delta."""
    print(f"\n── {name} " + "─" * (60 - len(name)))
    rosters = {w: work_roster(w) for w in groups}
    n_labels = sum(len(v) for v in groups.values())
    resolved = {w: r for w, r in rosters.items() if r is not None}
    print(f"   labels read from the committed dump : {n_labels}")
    print(f"   works in the group                  : {len(groups)}")
    print(f"   works the CATALOG holds a roster for: {len(resolved)}")
    for w, r in sorted(rosters.items()):
        say = ("—" if r is None
               else f"{len(r.instruments)} instruments, complete={r.complete}")
        print(f"      {w:<46} {say}")
    if not n_labels or not resolved:
        print("   ⚠️⚠️ DEAD: no labels, or no roster resolved. A zero here is "
              "the instrument, not a result.")
        return None

    kinds = collections.Counter()
    moved = []
    for work, texts in sorted(groups.items()):
        roster = rosters.get(work)
        if roster is None:
            continue
        off = verdicts_for(texts, None)
        on = verdicts_for(texts, roster)
        for text, (a, ra, _), (b, rb, db) in zip(texts, off, on):
            kinds[db.get("roster_decision") or ("vetoed" if rb ==
                  "vetoed_by_the_work_roster" else "unchanged")] += 1
            if (a, ra) != (b, rb):
                moved.append((work, text, a, b, rb))
    print(f"   verdicts compared                   : {sum(kinds.values())}")
    print(f"   roster outcome                      : {dict(kinds)}")
    print(f"   VERDICTS THAT MOVED                 : {len(moved)}")
    for work, text, a, b, rb in moved:
        print(f"      {work:<34} {text!r:<26} {a} -> {b or 'ABSTAIN'}  ({rb})")
    return len(moved)


def from_reach_log():
    """The 50 labels the cascade actually read on the CLEANUP-COUNT pages.

    ⚠️ THE DOCUMENT SEAN READ AGAINST THE PRINT, which is why this arm is
    first: Litolff `984073` p.1-4 is the artefact the whole Phase 2 count is
    taken on, and the one the slot-index session records reading slot 11 as a
    `Bass voice` — a singer on an orchestral score.
    """
    if not REACH_LOG.is_file():
        return {}
    texts = []
    for line in REACH_LOG.read_text().splitlines():
        m = re.search(r"staff\s+\d+\s+'([^']*)'", line)
        if m:
            texts.append(m.group(1))
    # ⚠️ THE WORK IS DERIVED FROM THE PDF PATH IN THE LOG'S OWN HEADER,
    # never typed: the log records which file it read, and `work_id_for_pdf`
    # joins that to the catalog. Typing the id is what got the first draft
    # wrong.
    from tools.omr.work_roster import work_id_for_pdf
    head = REACH_LOG.read_text().splitlines()[0]
    pdf = head.split(":", 1)[1].strip() if ":" in head else ""
    work = work_id_for_pdf(pdf) if pdf else None
    return {work: texts} if (texts and work) else {}


def from_lexicon():
    if not LEXICON.is_file():
        return {}, []
    rows = json.loads(LEXICON.read_text())
    groups, unmapped = collections.defaultdict(list), collections.Counter()
    for r in rows:
        work = _work_for(r.get("source") or "")
        text = (r.get("text") or "").strip()
        if not text:
            continue
        if work is None:
            unmapped[r.get("source")] += 1
            continue
        groups[work].append(text)
    return dict(groups), sorted(unmapped.items())


def main() -> int:
    print("ROSTER REACH — what a supplied roster changes, measured through "
          "the STAGED decision")
    a = arm("the cleanup-count pages (Litolff Beethoven 5 p.1-4)",
            from_reach_log())
    groups, unmapped = from_lexicon()
    if unmapped:
        # ⚠️ REPORTED, NEVER DROPPED. A source with no work id is a label this
        # arm could not ask about, and a denominator that quietly shrinks is
        # how a reach figure flatters itself.
        print(f"\n   ⚠️ sources with no work_id mapping (EXCLUDED, not "
              f"skipped): {unmapped}")
    b = arm("the 1,422-label lexicon corpus", groups)
    if a is None and b is None:
        print("\n⚠️⚠️ DEAD INSTRUMENT — neither arm ran.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
