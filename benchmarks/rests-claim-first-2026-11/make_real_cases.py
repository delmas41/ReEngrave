"""ROADMAP 2.288 round 4 -- Sean's 36 answered rest tiles (rounds 1-3, `answers/answers-2.288-r*.json`) as REAL CASES: page, box, what Sean said, and what the rest reader must therefore do.
Writes `real_cases.json` (the form lane 2.295's replay tool reads: plate, page, cell, class, box in page px, `sean` verbatim, `is_rest`).

    python3 benchmarks/rests-claim-first-2026-11/make_real_cases.py

`is_rest` follows Sean's word: a rest of any kind (a "half of a quarter rest" is a rest whose box held half) is True; a flag, stem, note, natural, or a letter of a word is False.
`must`: a rest is claimed (READ with ink) or refused ONLY for a named merged-ink reason (`touches_a_head`: a rest touching a note's ink, ROADMAP 2.290 step 5);
a not-rest is never claimed as a rest."""
import json
import pathlib

HERE = pathlib.Path(__file__).parent


def main():
    out = []
    for r in (1, 2, 3):
        d = json.load(open(HERE / "answers" / ("answers-2.288-r%d.json" % r)))
        for k, v in sorted(d["answers"].items(), key=lambda kv: int(kv[0])):
            word = v["sean"]
            rest = ("rest" in word.lower()) and not word.lower().startswith("an eighth note")
            out.append(dict(id="r%d-%02d" % (r, int(k)), round=r, tile=int(k), plate=v["plate"], page=v["page"], cell=v.get("cell"), cls=v["cls"], box=v["box"], sean=word,
                            is_rest=rest, must=("claimed_or_refused_for_merged_ink" if rest else "refused")))
    (HERE / "real_cases.json").write_text(json.dumps(out, indent=1))
    print(len(out), "cases;", sum(c["is_rest"] for c in out), "rests;", sum(not c["is_rest"] for c in out), "not rests")


if __name__ == "__main__":
    main()
