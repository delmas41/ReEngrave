"""Assemble FINDINGS.md from the head/tail drafts and the measured JSON.

    python3 benchmarks/omr-family-refusals-2026-09/probe/write_findings.py

⚠️ THE TABLES ARE READ OUT OF THE PROBE OUTPUTS, not typed beside them. A
number in a report that was typed rather than read is the ledger this repo
keeps having to check against the tree (CLAUDE.md §2 rule 10).
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "out"

NAMES = [
    ("beethoven5-p1-p4", "beethoven5-p1-p4"),
    ("litolff whole", "beethoven5-litolff-mvt1-whole-20260923"),
    ("breitkopf whole", "brahms1-breitkopf-mvt1-whole-20260923"),
]


def arm_table() -> str:
    rows = ["| record | boxes | `on_a_staff_line` | `tall_not_a_rung` | kept |"
            " abstained | base refused |",
            "|---|---|---|---|---|---|---|"]
    for label, stem in NAMES:
        f = OUT / f"ledger-arm-{stem}.json"
        if not f.exists():
            rows.append(f"| `{label}` | _not run_ | | | | | |")
            continue
        d = json.loads(f.read_text())
        a, b = d["arm"], d["base"]
        base_ref = sum(v for k, v in b.items() if k.startswith("refused:"))
        rows.append(
            f"| `{label}` | {d['ledger_boxes_on_the_record']:,} "
            f"| **{a.get('refused:on_a_staff_line', 0):,}** "
            f"| **{a.get('refused:tall_not_a_rung', 0)}** "
            f"| {a.get('kept', 0):,} "
            f"| {sum(v for k, v in a.items() if k.startswith('ABSTAINED'))} "
            f"| {base_ref} |")
    return "\n".join(rows)


def owner_table() -> str:
    rows = ["| record | `glyph_owner` verdicts (base / arm) | **moved** |",
            "|---|---|---|"]
    for label, stem in NAMES:
        f = OUT / f"ledger-arm-{stem}.json"
        if not f.exists():
            rows.append(f"| `{label}` | _not run_ | |")
            continue
        d = json.loads(f.read_text())
        g = d["glyph_owner_verdicts"]
        rows.append(f"| `{label}` | {g['base']:,} / {g['arm']:,} "
                    f"| **{d['glyph_owner_moved']}** |")
    return "\n".join(rows)


def ladder_table() -> str:
    rows = ["| record | signals | `ledger_found == 0` base -> arm "
            "| `== 1` | `== 2` | `would_fire` base -> arm |",
            "|---|---|---|---|---|---|"]
    for label, stem in NAMES:
        f = OUT / f"ledger-arm-{stem}.json"
        if not f.exists():
            rows.append(f"| `{label}` | _not run_ | | | | |")
            continue
        d = json.loads(f.read_text())
        b = d["unladdered_signal_base"]
        a = d["unladdered_signal_arm"]
        hb, ha = b["ledger_found_hist"], a["ledger_found_hist"]
        rows.append(
            f"| `{label}` | {b['signals']:,} "
            f"| {hb.get('0', 0):,} -> **{ha.get('0', 0):,}** "
            f"| {hb.get('1', 0):,} -> {ha.get('1', 0):,} "
            f"| {hb.get('2', 0):,} -> {ha.get('2', 0):,} "
            f"| {b['would_fire']:,} -> **{a['would_fire']:,}** |")
    return "\n".join(rows)


def notes_table() -> str:
    rows = ["| record | `<note>` base | `<note>` arm | "
            "`notes_not_written` identical | census `unaccounted` | "
            "`family_refusals` all balanced |",
            "|---|---|---|---|---|---|"]
    for label, stem in NAMES:
        f = OUT / f"ledger-arm-{stem}.json"
        if not f.exists():
            rows.append(f"| `{label}` | _not run_ | | | | |")
            continue
        d = json.loads(f.read_text())
        same = d["notes_not_written_base"] == d["notes_not_written_arm"]
        bal = all(r["balanced"]
                  for r in (d["family_refusals_arm"] or {}).values())
        rows.append(
            f"| `{label}` | {d['notes_base']:,} | {d['notes_arm']:,} "
            f"| {'yes' if same else '**NO**'} "
            f"| `{d['status_census_arm_unaccounted']}` "
            f"| {'yes' if bal else '**NO**'} |")
    return "\n".join(rows)


def sean_section() -> str:
    before = json.loads((HERE.parent / "omr-stage-review-2026-09" / "out"
                         / "sean-viola-p3" / "feedback-summary.json")
                        .read_text())
    f = OUT / "sean-viola-p3-after" / "feedback-summary.json"
    note = ""
    if not f.exists():
        # ⚠️ THE FIRST RE-RUN, NAMED AS SUCH. It carries the `owner:other`
        # half of the lane and NOT the named-owner rule that the first
        # re-run's own result forced (see the commit that added it), so the
        # section says which run it is reading rather than presenting the two
        # as one number.
        f = (OUT / "sean-viola-p3-after-owner-other-only"
             / "feedback-summary.json")
        note = ("\n⚠️ **READ FROM `out/sean-viola-p3-after-owner-other-only/`** "
                "— the FIRST re-run, before the named-owner rule the first "
                "re-run's own result forced. The second re-run was still "
                "going when this file was assembled; re-run the command in "
                "§7 and then `write_findings.py` to replace this section.\n")
    if not f.exists():
        return ("_No re-run on disk; run the command in §7 and re-run "
                "`write_findings.py`._\n")
    after = json.loads(f.read_text())

    def kinds(summary):
        out = {}
        for aid in summary["reached_nothing"]:
            k = summary["per_action"][aid]["kind"]
            out[k] = out.get(k, 0) + 1
        return out

    kb, ka = kinds(before), kinds(after)
    lines = [
        f"`reached_nothing` **{len(before['reached_nothing'])} -> "
        f"{len(after['reached_nothing'])}**, by kind:", "",
        "| action kind | before | after |", "|---|---|---|"]
    for k in sorted(set(kb) | set(ka)):
        lines.append(f"| `{k}` | {kb.get(k, 0)} | {ka.get(k, 0)} |")
    lines += ["",
              f"Actions {after['counts']['actions']}, human rows "
              f"{after['counts']['human_rows']}, verdicts naming a human row "
              f"{after['counts']['verdicts_naming_a_human_row']:,} "
              f"(was {before['counts']['verdicts_naming_a_human_row']:,}), "
              f"verdicts changed {after['counts']['verdicts_changed']:,} "
              f"(was {before['counts']['verdicts_changed']:,}), notes "
              f"{after['counts']['notes_before']:,} -> "
              f"{after['counts']['notes_after']:,}.", "",
              "Staff census on `staff/3/0/9` after:", "",
              "```json",
              json.dumps(after["export"]["staff_census_after"], indent=1),
              "```", "",
              "**The two accidentals he owned to Violin II** "
              "(`glyph/3/0/9/1/0`, `glyph/3/0/9/7/2`) — both "
              "`accidentalNatural`, both carrying `owner:staff/3/0/8` and "
              "**NEITHER carrying a `Q.GLYPH_BAND_DISTANCE` row**, which is "
              "read straight off the amended record and is exactly why they "
              "reached nothing before: `adjudicate_glyph_owner`'s domain is "
              "that quantity, so the contest never saw either of them:", ""]
    for aid, row in sorted(after["per_action"].items()):
        if row["subject"] in ("glyph/3/0/9/1/0", "glyph/3/0/9/7/2"):
            lines.append(
                f"* `{aid}` `{row['kind']}` on `{row['subject']}` — "
                f"weighed by {row['weighed_by'] or 'nothing'}, "
                f"`reached_nothing` = {row['reached_nothing']}")
    lines.append(note)
    by_dec_b = before["per_stage"]["ADJUDICATE"]["by_decider"]
    by_dec_a = after["per_stage"]["ADJUDICATE"]["by_decider"]
    new = {k: v for k, v in by_dec_a.items() if k not in by_dec_b}
    if new:
        lines += ["Deciders that NAMED a human row for the first time "
                  "(`per_stage.ADJUDICATE.by_decider`, which sits under "
                  "`verdicts_naming_a_human_row` -- NAMED, not weighed):", ""]
        for k, v in sorted(new.items()):
            lines.append(f"* `{k}` — {v}")
        lines.append("")
    return "\n".join(lines)


def main():
    head = (Path("/tmp/claude-501/findings-head.md")).read_text()
    tail = (Path("/tmp/claude-501/findings-tail.md")).read_text()
    body = f"""
---

## 2. Base vs arm, on ONE tree

`probe/readjudicate_ledger.py` rebuilds one saved record and adjudicates it
TWICE in one process: the BASE with the ledger geometry returned to nothing
(an unmeetable tolerance and an unreachable height floor — what the decision
did before it existed; the human rules stay and are inert on records holding
no human row), the ARM as shipped. The record's own committed verdicts are an
INPUT, never a baseline (CLAUDE.md §6b). It prints its population first and
exits 2 declaring itself DEAD AT ZERO if the record holds no ledger box.

⚠️ Blind to GATHER, like every tool of its shape — which is fine here,
because this lane files no new GATHER row.

### 2a. Ledger verdicts per record

{arm_table()}

The BASE refuses nothing on any record: the arm is the only thing moving,
which is what says the numbers are the rule's and not the rebuild's.

### 2b. `glyph_owner` — **0 verdicts changed, and that is the finding**

{owner_table()}

This is not a null result. It is the answer to item 3 of the brief, and it is
structural:

> **`glyph_owner`'s ladder tier cannot see a refused rung, because the
> rung -> glyph join does not exist on the record.** `Q.GLYPH_LADDER` is built
> in GATHER by `gather._observe_ladder` from an anonymous list of rung
> rectangles (`_ledger_index` yields bare `(x0, x1, y)` tuples), and the row
> it files records `expected` and `found` as **COUNTS**, naming none of the
> ledger glyphs it matched. No ADJUDICATE refusal can reach it without a
> GATHER change — and a GATHER change is invisible to `readjudicate` and needs
> two full re-gathers to price. **Reported, not faked.**

Pinned behaviourally rather than asserted in prose:
`test_gather_s_own_ladder_row_NAMES_NO_RUNG_GLYPH` calls `_observe_ladder`
for real, asserts it found its rung (the positive control) and asserts the
row's detail names no glyph subject. The day that row names its rungs, the
test goes red and the discount can move to `glyph_owner` too.

### 2c. The ladder the refusal DOES reach

ADJUDICATE has its own ledger search — `notehead_precision.
_ledger_rungs_in_cell`, where the rungs ARE glyph subjects — so the join
exists there and the discount is applied there.
`adjudicate_ledger_is_not_a_ledger` runs before
`adjudicate_notehead_is_not_a_notehead` in `ORDER` for exactly that reason.
Over the noteheads that produce an `unladdered_signal`:

{ladder_table()}

Noteheads lose the only rung that joined them to their staff, and it was a
staff-line fragment. **Nothing changes in the file**, because
`notehead_precision.UNLADDERED_SHIPS = False` — the signal is recorded, not
acted on. That is the whole of what the discount buys today, and it is stated
rather than inflated.

### 2d. `<note>` and the census

{notes_table()}

The ledger rule moves the ACCOUNTING and not the music, which is the honest
outcome for a rule whose only live consumer today is a signal that does not
ship. The new `family_refusals` block is a partition
(`refused + kept + abstained == verdicts`, where `verdicts` is counted from
the rows themselves rather than restated) and it balances on every family.

---

## 3. Sean's sidecar, re-run

`python3 -m tools.omr.staged.review.rerun <litolff whole> <sean.sidecar.json>
--staff staff/3/0/9 --out out/sean-viola-p3-after`

{sean_section()}
"""
    (HERE / "FINDINGS.md").write_text(head + body + tail)
    print("wrote", HERE / "FINDINGS.md")


if __name__ == "__main__":
    main()
