"""ROADMAP 2.296: name a page-wide DYNAMIC claim a dynamic, in memory, for the readout tools (`claim_readout`, `judged_claims`).

The register files a printed dynamic as owner `word`, source `dynamic_letters`, category `dynamic` (`claims.OWNER_WORD`); `claim_readout.FINE_OF_FAMILY` names a claim by
its owner, so every readout calls a dynamic's ink a word's. NOT the category alone: the lexicon files the WORDS `cresc.` / `dim.` / `p dim.` under category `dynamic` too
(Litolff p2 'cr' of cresc., 2.288 r1 tile 10: a keyed-on-category rename made a word a dynamic). `apply()` wraps `claim_readout.owner_verdicts` so that a stroke-owner
candidate whose claim row is owner `word` + source `dynamic_letters` reads as family `dynamic` -- exactly what the tool would print once it reads the row's category (the one-line fix named in the FINDINGS).
No tool file is edited; no record is changed; nothing is written.
"""


def apply():
    from tools.omr.staged import claim_readout as CR
    if getattr(CR.owner_verdicts, "_kind_patched", False):
        return
    orig = CR.owner_verdicts

    def renamed(rows, env=None):
        out = orig(rows, env)
        dyn = {o["id"] for o in rows["observations"] if o.get("quantity") == "claimed_area"
               and (o.get("detail") or {}).get("owner") == "word" and (o.get("detail") or {}).get("source") == "dynamic_letters"}
        for det in out.values():
            for ent in (det.get("strokes") or {}).values():
                for c in ent[4]:
                    if c[1] == "word" and c[0] in dyn:
                        c[1] = "dynamic"
                if ent[1] == "word" and any(k in dyn for k in (ent[2] or ())):
                    ent[1] = "dynamic"
        return out
    renamed._kind_patched = True
    CR.owner_verdicts = renamed
