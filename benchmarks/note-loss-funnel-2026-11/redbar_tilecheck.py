"""ROADMAP 2.311 -- put the ranking classifier's row beside Sean's reading of the 12 red-bar tiles (answers-2.311-redbars.json).

    python3 benchmarks/note-loss-funnel-2026-11/redbar_tilecheck.py

The agree / partial / disagree word is OUR judgment of whether the classifier's row says what Sean read in the boxed bar (Sean's words are quoted
in the file under `answers`; the verdict words below are ours and labelled so). Run after `redbar_ranking.py`.
"""
from __future__ import annotations

import json

HERE = "benchmarks/note-loss-funnel-2026-11/"
VERDICT = {
    "1": ("agree", "Sean: a chord and three beamed UNISON eighths (stems both ways). Row: a note's beam could not be told (joined or not). The two "
                   "refusals that used to head this bar are a neighbour staff's head tips at the cell's bottom edge, set aside."),
    "2": ("partial", "Sean: two half notes on a chord with a tremolo slash. Row: short with head-sized ink in no box -- that ink is the slash, so the "
                     "ink is real, but the classifier does not know what it is; the bar is red because half notes were written as a quarter. The refused "
                     "fragment that used to head this bar is a neighbour's tip at the bottom edge."),
    "3": ("agree", "Sean: a quarter and a quarter rest, one voice; the SF belongs to the system above. Row: the second voice is a copy of marks already "
                   "counted in the first (the rest box is written in both voices)."),
    "4": ("agree", "Sean: one unison half note, tied both sides. Row: a narrow mark refused as 'not a note' alone inside the cell, nothing written -- the half "
                   "note itself was refused."),
    "5": ("agree", "Sean: top voice a half note (natural before it), bottom voice a whole rest. Row: a note on a stem with beam ink judged uncertain, value "
                   "held. (The head class in the record is black; Sean reads a half.)"),
    "6": ("agree", "Sean: a two-note chord then a quarter rest, a fermata over the rest. Row: a rest counted here is the exact surplus (a 16th rest at the "
                   "start of the bar that Sean does not read)."),
    "7": ("agree", "Sean: two dotted quarters. Row: short by half a note, a dot printed beside a plain written quarter and the detector drew no box on it."),
    "8": ("agree", "Sean: a chord of quarters, an eighth rest, a chord of dotted quarters. Row: chord on one stem whose members' values the marks do not "
                   "settle (head_and_marks)."),
    "9": ("agree", "Sean: top voice quarter rest, eighth rest, quarter slurred to an eighth; bottom two dotted quarters. Row: flag ink beside a stem seen, "
                   "flag not read (the eighth)."),
    "10": ("agree", "Sean: two dotted quarters. Row: short by dots printed and never boxed (two plain quarters, shortfall one beat)."),
    "11": ("agree", "Sean: two dotted quarters, both under a slur. Row: a dot beside a plain note, augmentation or staccato not decided: value held."),
    "12": ("agree", "Sean: two dotted quarters. Row: short by half a note, a dot printed beside a plain written quarter and never boxed."),
}


def main() -> None:
    key = json.load(open("out/print/2.311-redbars-key.json"))
    rk = json.load(open(HERE + "redbar-ranking.json"))
    idx = {(b["plate"], b["page"], b["system"], b["staff"], b["cell"]): b for b in rk["bars"]}
    ans = json.load(open(HERE + "answers-2.311-redbars.json"))
    out = {}
    for t in key:
        b = idx[(t["plate"], t["page"], t["system"], t["staff"], t["cell"])]
        v, why = VERDICT[str(t["tile"])]
        out[str(t["tile"])] = dict(old_first_cause=t["first_cause"] + ": " + str(t["first_cause_reason"]), classifier_row=b["row"], classifier_reason=b["reason"],
                                   verdict_ours=v, why_ours=why)
    ans["classifier_check_2026-11-16"] = dict(
        note="Verdict words are OURS (the classifier's row against Sean's reading of the boxed bar), not Sean's. Sean's own words are in `answers`.",
        agree=sum(1 for x in out.values() if x["verdict_ours"] == "agree"), partial=sum(1 for x in out.values() if x["verdict_ours"] == "partial"),
        disagree=sum(1 for x in out.values() if x["verdict_ours"] == "disagree"), tiles=out)
    json.dump(ans, open(HERE + "answers-2.311-redbars.json", "w"), indent=1)
    for k, x in out.items():
        print(k, x["verdict_ours"], "|", x["classifier_row"])


if __name__ == "__main__":
    main()
