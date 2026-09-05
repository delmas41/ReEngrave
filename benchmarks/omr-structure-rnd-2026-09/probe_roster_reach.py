#!/usr/bin/env python3
"""H2 OPPORTUNITY COUNT — is class (a) a wall for a PAGE or for a DOCUMENT?

MEASUREMENT ONLY. Nothing in `tools/` or `backend/` is touched, and no
roster pre-pass is built. The single question:

    Of the staves that print NO margin label at all, how many sit in a
    document whose EARLIER pages DO print a label for the corresponding
    staff?

⚠️ THIS COUNTS AN OPPORTUNITY, NOT A GAIN. A name that arrives via an
earlier page's roster still has to survive everything downstream — in
particular `contextual.resolve_ambiguous_label`, which overturned a
correctly-read `Tp.` into Trumpet because a corrupted layout fit named a
trumpet at that slot (the class-6 circularity, `docs/discussion-detector-
right-output-wrong-2026-09-04.md`). Every number here is an UPPER BOUND.

── inputs ───────────────────────────────────────────────────────────────
* `benchmarks/omr-scan-e2e-2026-09/works.json` — used ONLY to identify each
  row's source PDF and page index. ⚠️ `row["staves"]` is the SCORING KEY and
  is never read as an input to any inference; it is loaded once, at the very
  end, for the `verification` block, which changes no verdict.
* `vendored-labels/classified.json`, `vendored-labels/margin-ink.json` —
  the labels workstream's COMMITTED data (`claude/staff-identity-labels-
  2026-09-05` @ 672607c9). Reused rather than recomputed. Sound because
  `git diff 672607c9 HEAD -- tools/omr/{instruments,staff_labels,
  staff_labels_surya,staff_labels_tesseract,staff_detector,contextual,
  staff_labels_vision}.py` is EMPTY: the readers and the lexicon that
  produced those files are the ones on this tree.
* donor pages that are NOT corpus rows are read fresh here, with the ladder
  block copied verbatim from that workstream's `probe_ladder.py`.

⚠️ Ink is trusted ONLY IN THE NEGATIVE, exactly as the labels workstream
did: class (a) is its `margin-ink.json` verdict `a_NO_INK` (0 px over a band
of 100k-260k). The 13 `INK_look` staves are NOT counted as class (a) — they
are reported as a separate abstention.

── the alignment, and why it is the hard part ───────────────────────────
"The corresponding staff" is itself a join, and it can be wrong. A printed
orchestral score SUPPRESSES tacet staves on continuation systems, so
position i on page 6 is not position i on page 1. This probe therefore
ANCHORS on the labels both pages DO resolve, and abstains between anchors
whose staff counts disagree:

    anchors  = longest common subsequence of resolved instrument names
    segment  = the run of staves between two consecutive anchors
    if len(target segment) == len(donor segment): 1:1, in order
    else:                                          ABSTAIN, and count it

A target system with no anchor at all is joined only when the two systems
have equal staff counts — the same rule `export._stitch_slots` uses.

    python3 benchmarks/omr-structure-rnd-2026-09/probe_roster_reach.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

WORKS = REPO / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"
VEND = HERE / "vendored-labels"
DPI = 600  # works.json protocol.dpi — same as the labels workstream


# ── the ladder, copied verbatim in behaviour from probe_ladder.py ────────
def page_labels(pdf: Path, page_index: int) -> dict:
    """Every rung on one page, then THE LADDER'S OWN ANSWER.

    Not "the best rung" — `contextual._labels_for_page` stops at the first
    rung that covers the page and merges Tesseract on RAW presence. The
    committed `classified.json` this probe joins against is the ladder
    answer, so a donor page must be read the same way or the two sides are
    not comparable.
    """
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr import staff_labels, staff_labels_surya, staff_labels_tesseract
    from tools.omr.instruments import lookup

    pws = detect_staves(render_page(pdf, page_index, dpi=DPI))
    by_sys: dict[int, list] = {}
    for s in sorted(pws.staves, key=lambda s: s.top_y):
        by_sys.setdefault(s.system_index, []).append(s)

    rungs: dict[str, dict[int, str]] = {}
    rungs["text_layer"] = {l.staff_index: l.text
                           for l in staff_labels.read_staff_labels(pws)}
    try:
        rungs["surya"] = {l.staff_index: l.text
                          for l in staff_labels_surya.read_staff_labels_surya(pws)} \
            if staff_labels_surya.available() else {}
    except Exception as exc:                                   # noqa: BLE001
        rungs["surya"] = {}
        print(f"  !! surya failed: {exc}", file=sys.stderr)
    try:
        rungs["tesseract"] = {
            l.staff_index: l.text
            for l in staff_labels_tesseract.read_staff_labels_tesseract(pws)} \
            if staff_labels_tesseract.available() else {}
    except Exception as exc:                                   # noqa: BLE001
        rungs["tesseract"] = {}
        print(f"  !! tesseract failed: {exc}", file=sys.stderr)

    tl = {i: t for i, t in rungs["text_layer"].items() if t}
    sy = {i: t for i, t in rungs["surya"].items() if t}
    ts = {i: t for i, t in rungs["tesseract"].items() if t}

    def _usable(d):
        return sum(1 for t in d.values() if (lambda h: h and h.instrument)(lookup(t)))

    def _covered(d):
        widest = max((len(v) for v in by_sys.values()), default=0)
        if not d or not widest:
            return bool(d) and not widest
        named = {i for i, t in d.items()
                 if (lambda h: h and h.instrument)(lookup(t))}
        best = max((sum(1 for s in v if s.staff_index in named)
                    for v in by_sys.values()), default=0)
        return best / widest >= 0.75

    chosen = dict(tl)
    src = {i: "text_layer" for i in tl}
    if not _covered(chosen):
        if _usable(sy) > _usable(chosen):
            chosen, src = dict(sy), {i: "surya" for i in sy}
        if not _covered(chosen):
            for i, t in ts.items():
                if i not in chosen:          # raw presence, as the pipeline does
                    chosen[i], src[i] = t, "tesseract"

    systems = {}
    for sysi, staves in sorted(by_sys.items()):
        row = []
        for pos, staff in enumerate(staves):
            si = staff.staff_index
            text = (chosen.get(si) or "").strip()
            h = lookup(text) if text else None
            row.append({
                "position": pos,
                "text": text,
                "resolved": h.instrument.name if (h and h.instrument) else None,
                "rung": src.get(si),
            })
        systems[sysi] = row
    return {"pdf": str(pdf), "page_index": page_index,
            "structure": [len(v) for _, v in sorted(by_sys.items())],
            "rung_counts": {k: len(v) for k, v in rungs.items()},
            "systems": systems}


# ── alignment ────────────────────────────────────────────────────────────
def _lcs_anchor_pairs(tnames: list, dnames: list) -> list:
    """Longest common subsequence over resolved names; None never matches."""
    n, m = len(tnames), len(dnames)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if tnames[i] is not None and tnames[i] == dnames[j]:
                dp[i][j] = 1 + dp[i + 1][j + 1]
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if tnames[i] is not None and tnames[i] == dnames[j]:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def align(target: list, donor: list) -> dict:
    """position in target -> position in donor, or None where we abstain."""
    tn = [s["resolved"] for s in target]
    dn = [s["resolved"] for s in donor]
    anchors = _lcs_anchor_pairs(tn, dn)
    mapping: dict[int, int | None] = {}
    reasons: dict[int, str] = {}

    bounds = [(-1, -1)] + anchors + [(len(tn), len(dn))]
    for (ta, da), (tb, db) in zip(bounds, bounds[1:]):
        if ta >= 0:
            mapping[ta] = da
            reasons[ta] = "anchor"
        tseg = list(range(ta + 1, tb))
        dseg = list(range(da + 1, db))
        if len(tseg) == len(dseg):
            for t, d in zip(tseg, dseg):
                mapping[t] = d
                reasons[t] = "segment_1to1" if anchors else "equal_staff_counts"
        else:
            for t in tseg:
                mapping[t] = None
                reasons[t] = (f"segment_size_mismatch target={len(tseg)} "
                              f"donor={len(dseg)}")
    return {"anchors": anchors, "map": mapping, "reason": reasons,
            "n_anchors": len(anchors)}


RANK = {"REACHABLE": 0, "REACHABLE_TEXT_ONLY": 1,
        "UNREACHABLE_DONOR_BLANK": 2, "ABSTAIN_ALIGNMENT": 3}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "roster-reach.json"))
    a = ap.parse_args(argv)

    from tools.library.score_library import library_root
    lib = Path(library_root())

    works = json.loads(WORKS.read_text())
    rows = works["rows"]
    assert len(rows) == 20, f"expected 20 works.json rows, got {len(rows)}"

    classified = json.loads((VEND / "classified.json").read_text())
    ink = json.loads((VEND / "margin-ink.json").read_text())
    staves = classified["staves"]
    assert len(staves) == 407, f"expected 407 classified staves, got {len(staves)}"

    class_a = {(x["row_id"], x["system"], x["position"])
               for x in ink if x["verdict"] == "a_NO_INK"}
    ink_look = {(x["row_id"], x["system"], x["position"])
                for x in ink if x["verdict"] != "a_NO_INK"}
    assert class_a, "class (a) population is EMPTY — the join found nothing"
    print(f"class (a) staves (margin ink == 0): {len(class_a)}", file=sys.stderr)
    print(f"INK_look staves (abstained, not class a): {len(ink_look)}",
          file=sys.stderr)

    # ── target pages: the corpus rows, with the labels workstream's answers ──
    row_meta = {}
    for r in rows:
        cp = r["edition"]["catalog_path"]
        pdf = lib / cp
        assert pdf.exists(), f"PDF not found in the score library: {pdf}"
        row_meta[r["row_id"]] = {
            "catalog_path": cp,
            "pdf": pdf,
            "page_index": r["page"]["pdf_page_index"],
            "printed_page": r["page"].get("printed_page"),
            "publisher": r["edition"].get("publisher_as_catalogued", ""),
        }
    assert len({m["pdf"] for m in row_meta.values()}) == 6, "expected 6 editions"

    target_pages: dict[str, dict] = {}
    for rid, meta in row_meta.items():
        systems: dict[int, list] = {}
        for s in staves:
            if s["row_id"] != rid:
                continue
            systems.setdefault(s["system"], []).append(
                {"position": s["position"], "text": s["reads"].get("ladder", ""),
                 "resolved": s["resolved"], "rung": s["resolved_by"]})
        for k in systems:
            systems[k].sort(key=lambda x: x["position"])
        assert systems, f"no classified staves for row {rid}"
        target_pages[rid] = {"systems": systems,
                             "structure": [len(systems[k]) for k in sorted(systems)]}

    n_target_staves = sum(len(v) for p in target_pages.values()
                          for v in p["systems"].values())
    assert n_target_staves == 407, n_target_staves

    # ── donor pages ──────────────────────────────────────────────────────────
    # every EARLIER page of the same edition that we have an answer for:
    #   * corpus rows of the same edition with a smaller pdf page index
    #   * plus, read fresh here, the non-row pages before the earliest row
    by_edition: dict[str, list] = {}
    for rid, m in row_meta.items():
        by_edition.setdefault(m["catalog_path"], []).append((m["page_index"], rid))
    for v in by_edition.values():
        v.sort()

    fresh_needed = []
    for cp, lst in by_edition.items():
        first_idx = lst[0][0]
        for idx in range(0, first_idx):
            fresh_needed.append((cp, idx))
    print(f"non-row earlier pages to read fresh: {len(fresh_needed)} "
          f"{fresh_needed}", file=sys.stderr)

    fresh: dict[tuple, dict] = {}
    for cp, idx in fresh_needed:
        pdf = lib / cp
        print(f"== fresh donor read {cp} page {idx}", file=sys.stderr)
        pl = page_labels(pdf, idx)
        print(f"   structure={pl['structure']} rungs={pl['rung_counts']} "
              f"resolved={sum(1 for v in pl['systems'].values() for s in v if s['resolved'])}",
              file=sys.stderr)
        fresh[(cp, idx)] = pl

    n_fresh_staves = sum(len(v) for pl in fresh.values()
                         for v in pl["systems"].values())
    if fresh_needed:
        assert n_fresh_staves > 0, "fresh donor reads detected ZERO staves"
    print(f"fresh donor staves detected: {n_fresh_staves}", file=sys.stderr)

    def donors_for(rid: str):
        """(sort_key, donor_id, page_index, systems) for every earlier page."""
        m = row_meta[rid]
        out = []
        for idx, other in by_edition[m["catalog_path"]]:
            if idx < m["page_index"]:
                out.append((idx, other, idx, target_pages[other]["systems"]))
        for (cp, idx), pl in fresh.items():
            if cp == m["catalog_path"] and idx < m["page_index"]:
                out.append((idx, f"{m['catalog_path']}#p{idx}", idx, pl["systems"]))
        out.sort()
        return out

    # ── the count ────────────────────────────────────────────────────────────
    results = []
    for rid in sorted(target_pages):
        tsys = target_pages[rid]["systems"]
        donors = donors_for(rid)
        for sysi in sorted(tsys):
            target = tsys[sysi]
            a_here = [s for s in target
                      if (rid, sysi, s["position"]) in class_a]
            if not a_here:
                continue

            # one donor SYSTEM per target system — a real roster pass would
            # choose a donor, not a donor per staff. Best = most REACHABLE,
            # tie-broken by the NEAREST earlier page.
            best = None
            for pidx, did, _, dsystems in donors:
                for dsysi in sorted(dsystems):
                    donor = dsystems[dsysi]
                    al = align(target, donor)
                    n_reach = 0
                    for s in a_here:
                        q = al["map"].get(s["position"])
                        if q is not None and donor[q]["resolved"]:
                            n_reach += 1
                    key = (-n_reach, -al["n_anchors"], -pidx)
                    if best is None or key < best[0]:
                        best = (key, did, pidx, dsysi, donor, al)
            if best is None:
                for s in a_here:
                    results.append({
                        "row_id": rid, "system": sysi, "position": s["position"],
                        "publisher": row_meta[rid]["publisher"],
                        "verdict": "UNREACHABLE_NO_EARLIER_PAGE",
                        "why": "the document has no page before this one",
                    })
                continue

            _, did, pidx, dsysi, donor, al = best
            for s in a_here:
                p = s["position"]
                q = al["map"].get(p)
                if q is None:
                    v, why, name = ("ABSTAIN_ALIGNMENT", al["reason"].get(p, "?"),
                                    None)
                elif donor[q]["resolved"]:
                    v, why, name = ("REACHABLE", al["reason"].get(p, "?"),
                                    donor[q]["resolved"])
                elif donor[q]["text"]:
                    v, why, name = ("REACHABLE_TEXT_ONLY",
                                    f'donor text {donor[q]["text"]!r} unresolved',
                                    None)
                else:
                    v, why, name = ("UNREACHABLE_DONOR_BLANK",
                                    "donor staff prints nothing either", None)
                results.append({
                    "row_id": rid, "system": sysi, "position": p,
                    "publisher": row_meta[rid]["publisher"],
                    "verdict": v, "why": why,
                    "donor": did, "donor_page_index": pidx,
                    "donor_system": dsysi, "donor_position": q,
                    "donor_text": donor[q]["text"] if q is not None else None,
                    "donor_rung": donor[q]["rung"] if q is not None else None,
                    "imputed_name": name,
                    "n_anchors": al["n_anchors"],
                })

    assert len(results) == len(class_a), (
        f"counted {len(results)} verdicts for {len(class_a)} class-(a) staves")

    # ── verification, AFTER every verdict is fixed ───────────────────────────
    # ⚠️ works.json["staves"] is the SCORING KEY. Nothing above reads it. This
    # block only checks imputed names against the hand-read truth; it changes
    # no verdict and no count.
    def truth_names(rid):
        r = next(r for r in rows if r["row_id"] == rid)
        st = r.get("staves")
        while isinstance(st, str) and st.startswith("same-as:"):
            r = next(x for x in rows if x["row_id"] == st.split(":", 1)[1])
            st = r.get("staves")
        if isinstance(st, list):
            return [x.get("name") for x in st]
        return None

    from tools.omr.instruments import lookup
    ver = {"checked": 0, "agree": 0, "disagree": 0, "no_truth": 0, "cases": []}
    for r in results:
        if r["verdict"] != "REACHABLE":
            continue
        tn = truth_names(r["row_id"])
        if not tn or r["position"] >= len(tn):
            ver["no_truth"] += 1
            continue
        h = lookup(tn[r["position"]] or "")
        want = h.instrument.name if (h and h.instrument) else None
        ver["checked"] += 1
        if want == r["imputed_name"]:
            ver["agree"] += 1
        else:
            ver["disagree"] += 1
            ver["cases"].append({**{k: r[k] for k in
                                    ("row_id", "system", "position",
                                     "imputed_name", "donor_text")},
                                 "truth_name": tn[r["position"]],
                                 "truth_instrument": want})

    payload = {
        "meta": {
            "question": ("of the staves printing NO label, how many sit in a "
                         "document whose EARLIER page labels the corresponding "
                         "staff?"),
            "upper_bound": ("YES. A roster name still has to survive "
                            "contextual.resolve_ambiguous_label — the class-6 "
                            "circularity. This is coverage, not gain."),
            "class_a_source": "vendored-labels/margin-ink.json verdict a_NO_INK",
            "class_a_n": len(class_a),
            "ink_look_abstained_n": len(ink_look),
            "dpi": DPI,
            "donor_rungs_available": {
                "surya": __import__("tools.omr.staff_labels_surya",
                                    fromlist=["x"]).available(),
                "tesseract": __import__("tools.omr.staff_labels_tesseract",
                                        fromlist=["x"]).available(),
            },
            "fresh_donor_pages": [{"catalog_path": cp, "page_index": i,
                                   "structure": fresh[(cp, i)]["structure"],
                                   "rung_counts": fresh[(cp, i)]["rung_counts"]}
                                  for cp, i in fresh_needed],
        },
        "verdicts": results,
        "verification_against_scoring_key": ver,
    }
    Path(a.out).write_text(json.dumps(payload, indent=1))
    print(f"wrote {a.out}", file=sys.stderr)

    # ── report ───────────────────────────────────────────────────────────────
    import collections
    tot = collections.Counter(r["verdict"] for r in results)
    print("\nPOOLED", file=sys.stderr)
    for k, v in tot.most_common():
        print(f"  {k:32s} {v:4d}", file=sys.stderr)
    print("\nBY PUBLISHER", file=sys.stderr)
    pub = collections.defaultdict(collections.Counter)
    for r in results:
        pub[r["publisher"].split(",")[0]][r["verdict"]] += 1
    for p in sorted(pub):
        print(f"  {p}", file=sys.stderr)
        for k, v in pub[p].most_common():
            print(f"      {k:30s} {v:4d}", file=sys.stderr)
    print(f"\nverification vs scoring key: {ver['agree']}/{ver['checked']} agree, "
          f"{ver['disagree']} disagree, {ver['no_truth']} no truth",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
