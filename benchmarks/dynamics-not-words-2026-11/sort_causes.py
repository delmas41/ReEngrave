"""ROADMAP 2.296 step 2: every printed dynamic of the named pages, sorted by CAUSE (what the page ledger's claim register holds for it).

    python3 benchmarks/dynamics-not-words-2026-11/sort_causes.py RECORD.json PAGE[,PAGE...] [--json OUT]

RECORD = a gathered record (`python3 -m tools.omr.staged PDF --pages ... --out RECORD`) or a slice directory (`observations.jsonl`, `abstentions.jsonl`).
A PRINTED DYNAMIC here is what the pipeline's own readers name one: a `dynamic_letters` claim (detector letters, lone or spelled), or a direction
word whose text holds a dynamic token (`dynamics` on the row: `f legato`, `p dolce`, `p cresc. f`) or is all dynamic vocabulary. `cresc.` / `dim.` are WORDS.
Reads rows only; files nothing; decides nothing.

  claim_named_word   a `dynamic_letters` claim (category dynamic) stands on the dynamic's ink: claimed ONCE, for the dynamic; the register's OWNER NAME is
                     `word` (`claims.OWNER_WORD`), so any tool keyed on the owner reads it as a word            (accounting: kind name)
  compound_swallowed a direction word's area covers the dynamic token's letters; no dynamic claim stands on them     (the word owns the dynamic's ink)
  compound_split     (flag ON) the word's claim stops at the dynamic's ink and a dynamic claim of its own stands there (`compound_of` on the claim)
  letters_unclaimed  detector dynamic letters with no claim of any kind -- counted by the gather's own census (why: all_ink_on_a_mark = the letter box
                     is a note's ink; a false letter), listed apart: they are not printed dynamics until Sean says so
"""
import collections
import json
import pathlib
import re
import sys


def load(path):
    p = pathlib.Path(path)
    if p.is_dir():
        obs = [json.loads(l) for l in open(p / "observations.jsonl")]
        ab = [json.loads(l) for l in open(p / "abstentions.jsonl")] if (p / "abstentions.jsonl").exists() else []
        return obs, ab
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
    from tools.omr.staged.record_io import load_record
    res = load_record(str(p))
    rec = res.get("record", res)
    return rec["observations"], rec.get("abstentions", [])


def page_of(subject):
    m = re.match(r"^(?:glyph|cell|staff|system|page)/(\d+)", str(subject))
    if m:
        return int(m.group(1))
    m = re.match(r"^p(\d+)", str(subject))
    return int(m.group(1)) if m else None


def box(v):
    return v if isinstance(v, list) and len(v) == 4 and all(isinstance(t, (int, float)) for t in v) else None


def small_overlap(a, b):
    ix, iy = max(0.0, min(a[2], b[2]) - max(a[0], b[0])), max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    sm = max(1.0, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))
    return ix * iy / sm


def main():
    obs, ab = load(sys.argv[1])
    pages = [int(x) for x in sys.argv[2].split(",")]
    out_json = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    result = {}
    for pg in pages:
        claims = [o for o in obs if o.get("quantity") == "claimed_area" and page_of(o["subject"]) == pg and box(o.get("value"))
                  and (o.get("detail") or {}).get("owner") == "word"]
        read = [c for c in claims if c["detail"].get("standing", "READ") == "READ"]
        words = [o for o in obs if o.get("quantity") == "direction_word" and page_of(o["subject"]) == pg and isinstance(o.get("value"), str)]
        letters = [o for o in obs if o.get("quantity") == "dynamic_letter" and page_of(o["subject"]) == pg and box((o.get("detail") or {}).get("bbox_page_px"))]
        census = {}
        for a in ab:
            d = a.get("detail") or {}
            if a.get("quantity") == "claimed_area" and d.get("why") == "page_claim_census" and page_of(a["subject"]) == pg:
                census = d.get("census") or {}
        dyn_claims = [c for c in read if c["detail"].get("source") == "dynamic_letters"]
        split = [c for c in dyn_claims if c["detail"].get("compound_of")]
        plain = [c for c in dyn_claims if not c["detail"].get("compound_of")]
        named = [c for c in dyn_claims if c["detail"].get("category") == "dynamic"]
        cw = [w for w in words if (w.get("detail") or {}).get("dynamics")]
        swallowed, twin = [], []
        for w in cw:
            wb = (w["detail"] or {}).get("bbox_page_px")
            inc = set(w["detail"].get("includes_dynamic_glyphs") or ())
            ls = [L for L in letters if L["subject"] in inc]
            hit = [c for c in dyn_claims if any(small_overlap(L["detail"]["bbox_page_px"], c["value"]) >= 0.5 for L in ls)]
            has_split = any(c["detail"].get("compound_of") == w["id"] for c in split)
            row = dict(word=w["value"], row=w["id"], box=[round(t) for t in wb] if wb else None, dynamics=w["detail"].get("dynamics"),
                       letters=len(ls), own_claims=[(c["id"], c["detail"].get("text") or c["detail"].get("detector_letter"),
                                                      c["detail"].get("compound_of")) for c in hit], split=has_split)
            (swallowed if not hit else twin if not has_split else []).append(row)
        result[pg] = dict(
            dynamic_claims=len(dyn_claims), claim_named_word=len(named) - len(split), compound_split=len(split),
            compound_words=len(cw), compound_swallowed=len(swallowed), compound_with_other_dynamic_claim=len(twin),
            detector_letters=len(letters), census={k: v for k, v in census.items() if "dynamic" in k or "compound" in k},
            swallowed=swallowed, twin=twin)
        r = result[pg]
        print("page %d: dynamic claims %d (named `word` %d, compound split %d) | words holding a dynamic token %d: swallowed %d, other dynamic claim on the letters %d"
              % (pg, r["dynamic_claims"], r["claim_named_word"], r["compound_split"], r["compound_words"], r["compound_swallowed"], r["compound_with_other_dynamic_claim"]))
        print("   census:", r["census"])
        for w in swallowed + twin:
            print("   word", w)
    if out_json:
        pathlib.Path(out_json).write_text(json.dumps(result, indent=1, default=str))


main()
