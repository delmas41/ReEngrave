"""ROADMAP 2.296: name a page-wide DYNAMIC claim a dynamic, in memory, for the readout tools (`claim_readout`, `judged_claims`).

The register files a printed dynamic as owner `word`, source `dynamic_letters`, category `dynamic` (`claims.OWNER_WORD`); `claim_readout.FINE_OF_FAMILY` names a claim by
its owner, so every readout calls a dynamic's ink a word's. NOT the category alone: the lexicon files the WORDS `cresc.` / `dim.` / `p dim.` under category `dynamic` too
(Litolff p2 'cr' of cresc., 2.288 r1 tile 10: a keyed-on-category rename made a word a dynamic). `apply()` wraps `claim_readout.owner_verdicts` so that a stroke-owner
candidate whose claim row is owner `word` + source `dynamic_letters` reads as family `dynamic` -- exactly what the tool would print once it reads the claim row's `source`
(the one-line fix named in the FINDINGS). No tool file is edited; no record is changed; nothing is written.

THE ROW ID MUST BE THE REBUILT LOG'S. `owner_verdicts` re-runs the owner on `review.rerun.rebuild_gather`, which RENUMBERS the rows densely (a slice of one page of a
several-page record has other ids than the file's), so the claim key in a verdict is the rebuilt id, not the id in `observations.jsonl`. The first cut of this patch looked the file's
ids up and renamed nothing on any page but the first of a record (found on Litolff p4 / p9 / p10, where every `ff` stayed a word): `rebuild_gather`'s `old_id -> new_id` map is
kept here and the dynamic set is translated through it.
"""


def apply():
    from tools.omr.staged import claim_readout as CR
    from tools.omr.staged.review import rerun as RR
    if getattr(CR.owner_verdicts, "_kind_patched", False):
        return
    orig_rebuild = RR.rebuild_gather
    last = {"map": {}}

    def rebuild(rec):
        log, id_map = orig_rebuild(rec)
        last["map"] = dict(id_map)
        return log, id_map
    RR.rebuild_gather = rebuild
    orig = CR.owner_verdicts

    def renamed(rows, env=None):
        out = orig(rows, env)
        m = last["map"]
        dyn = {m.get(o["id"], o["id"]) for o in rows["observations"] if o.get("quantity") == "claimed_area"
               and (o.get("detail") or {}).get("owner") == "word" and (o.get("detail") or {}).get("source") == "dynamic_letters"}
        n = 0
        for det in out.values():
            for ent in (det.get("strokes") or {}).values():
                for c in ent[4]:
                    if c[1] == "word" and c[0] in dyn:
                        c[1] = "dynamic"
                        n += 1
                if ent[1] == "word" and any(k in dyn for k in (ent[2] or ())):
                    ent[1] = "dynamic"
        renamed.last_renamed = n
        return out
    renamed._kind_patched = True
    CR.owner_verdicts = renamed
