"""ROADMAP 2.102: the blind-tile spec. python3 p102_spec.py OUT_SPEC.json"""
import json
import sys

L = "/Users/seanjohnson/Desktop/ReEngrave/library/"
docs = {
    "dvorak": {"pdf": L + "editions/dvorak/symphony-8-op88/dvorak--symphony-8-op88--novello-1892--imslp405841.pdf",
               "record": L + "_shared-records/held-out-2101/dvorak8-novello-arm2.record.json"},
    "schumann": {"pdf": L + "editions/schumann/symphony-2-op61/schumann--symphony-2-op61--peters-1887--imslp514290.pdf",
                 "record": L + "_shared-records/held-out-2101/schumann2-peters-arm2.record.json"},
    "tchaikovsky": {"pdf": L + "editions/tchaikovsky/symphony-4-op36/tchaikovsky--symphony-4-op36--jurgenson--imslp377460.pdf",
                    "record": L + "_shared-records/held-out-2101/tchaikovsky4-jurgenson-arm2.record.json"},
    "litolff": {"pdf": L + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
                "record": L + "_shared-records/beethoven5-litolff-mvt1-whole-20261011-night.record.json"},
}
T = [
    ("dvorak", "glyph/4/0/15/5/6", "2.102a: bar-sum no longer settles a tuplet group (Sean's tile 6)", "tuplet_group",
     "now narrowed (was: decided eighth)"),
    ("schumann", "glyph/3/0/3/4/9", "2.102a: bar-sum no longer settles over columns the grouping left apart (tile 10's bar)",
     "simultaneous_columns", "now narrowed (was: decided eighth)"),
    ("litolff", "glyph/11/0/0/8/2", "2.102a COST: the one acceptance-record settlement the column guard removes",
     "simultaneous_columns_cost", "now narrowed (was: decided eighth)"),
    ("dvorak", "glyph/4/0/2/1/2", "2.102b: the C meter sign (Sean's tile 11)", "meter_sign",
     "now abstained not_a_note_mark (was: decided half)"),
    ("dvorak", "glyph/4/0/5/2/10", "2.102b: another narrow box in a meter column", "meter_sign",
     "now abstained not_a_note_mark (was: decided quarter)"),
    ("dvorak", "glyph/6/0/4/5/2", "2.102b: narrow box in a meter column, narrowed before", "meter_sign",
     "now abstained not_a_note_mark"),
    ("tchaikovsky", "glyph/5/0/1/4/1", "2.102b: narrow box in a meter column, on the plate whose meter is not read",
     "meter_sign", "now abstained not_a_note_mark"),
    ("dvorak", "glyph/4/0/16/1/5", "2.102b: tremolo slash refused as a head", "tremolo",
     "now abstained not_a_note_mark (was: decided quarter)"),
    ("schumann", "glyph/4/0/10/3/12", "2.102b: tremolo slashes (Sean's tile 17)", "tremolo",
     "now abstained not_a_note_mark (was: decided half)"),
    ("dvorak", "glyph/5/0/4/7/5", "CONTROL: an unrefused hollow head the rule still reads as a half", "control_half",
     "unchanged: decided half"),
]
tiles = [{"doc": d, "subject": s, "purpose": p, "rule": r, "our_reading": o} for d, s, p, r, o in T]
json.dump({"docs": docs, "tiles": tiles}, open(sys.argv[1], "w"), indent=1)
