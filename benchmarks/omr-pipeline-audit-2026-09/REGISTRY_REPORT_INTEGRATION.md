# Wiring the registry into `docs/progress-dashboard.html` — the diff, UNAPPLIED

**Nothing in this file has been applied.** `tools/dashboard/generate.py`,
`docs/progress-dashboard.*` and `metric-registry.json` are untouched by the
branch that carries this document. The renderer it accompanies
(`tools/dashboard/registry_report.py`) is standalone and writes only
`registry-report.{html,md}` in this directory.

The README's §"Wiring it into `docs/progress-dashboard.html`" lists six steps.
This is what four of them look like as a patch, plus **one finding that changes
the shape of step 1** and should be decided before anybody applies it.

---

## ⚠️ The finding: a dashboard CELL cannot carry a `mandatory_caption`

`generate.py` renders the flow graph as small grid cells — `display` is a short
string (`"F1 0.919"`), `detail` is a subtitle. The registry's rule is that a
captioned row must show its caption **beside the number, in the same visual
block**, and that *a renderer which cannot place it must not show the row*.

Five rows carry a caption today, and each is 120–260 characters. Putting one in
`detail` is placing it beside the number and would satisfy the rule; putting it
in a tooltip, a `<details>`, or dropping it because the cell is small would
not — and "the cell is small" is exactly the pressure that produces the quiet
drop. So step 1 has three honest options and the middle one is a decision, not
an implementation detail:

| option | consequence |
|---|---|
| render the caption into `detail`, in full | correct; makes five cells 4–6 lines tall |
| render the row's number but not its caption | **forbidden by the schema.** Do not. |
| do not place captioned rows on the flow graph at all; link them to the report | correct, and the cells stay small |

`_registry_cell()` below implements the **first**, and `SKIP_CAPTIONED` switches
to the third. Neither can produce the second: a captioned row with no room for
its caption raises.

---

## 1 · `pipeline_metrics()` reads the registry

```diff
--- a/tools/dashboard/generate.py
+++ b/tools/dashboard/generate.py
@@
 RATE_GREEN = 0.90   # higher-is-better rates (F1, recall, "n of m correct")
 RATE_AMBER = 0.75
 NED_GREEN = 0.15    # OMR-NED — lower is better
 NED_AMBER = 0.30
+
+# ── % of achievable: ONE axis, ONE threshold pair ───────────────────────────
+# The two pairs above are two hand-set constants doing the work a ceiling
+# should do. Under the registry there is one number and one direction.
+PCT_GREEN = 90.0
+PCT_AMBER = 60.0
+
+REGISTRY = ROOT / "benchmarks" / "omr-pipeline-audit-2026-09" / "metric-registry.json"
+
+#: ⚠️ Set True to keep captioned rows OFF the flow graph entirely (option 3
+#: above). False places them with their caption in `detail`. There is no third
+#: setting, because dropping the caption is not an option the schema allows.
+SKIP_CAPTIONED = False
@@
 def pipeline_metrics() -> dict:
@@
-    m = {}
+    m = {}
+    m.update(registry_metrics())
```

```python
def registry_metrics() -> dict:
    """Every registry row as a dashboard cell, in % of achievable.

    The registry `id`s are already the names the content JSON uses
    (`reading:clef`, `scan:pitch`, `engraved:omr_ned`), so no content JSON
    changes. Rows are ADDED FIRST and the existing inline derivations still run
    after them, so an id present in both keeps its old value until the inline
    branch is deleted — deliberate, so the two can be diffed during a
    changeover rather than swapped blind.
    """
    from tools.dashboard import registry_report as rr

    reg = rr.load_registry(REGISTRY)
    rr.gate_schema_version(reg)          # R2 — refuses an unread schema, loudly

    out = {}
    for row in reg["rows"]:
        problem = rr.caption_problem(row)
        if problem:                       # R1 — cannot place it, do not show it
            print("registry: WITHHELD %s — %s" % (row["id"], problem), file=sys.stderr)
            continue
        cap = row.get("mandatory_caption")
        if cap and SKIP_CAPTIONED:
            continue

        pct, c = row.get("pct_of_achievable"), row.get("ceiling") or {}
        detail = "%s · n=%s %s · ceiling %s (%s)" % (
            rr.native_str(row), row.get("n"), row.get("n_unit") or "",
            c.get("kind"), c.get("status"))
        if cap:
            # R1: the caption goes in the cell, with the number. Not a tooltip.
            detail = ('<b class="mandatory-caption">MUST BE READ WITH THIS '
                      'NUMBER: %s</b> · %s' % (esc(rr.prose(cap)), detail))

        out[row["id"]] = {
            "display": ("%.1f%%" % pct) if row.get("scoreable") and pct is not None
                       else "unscoreable",
            "pct": pct if row.get("scoreable") else None,
            "ceiling_status": c.get("status"),
            "detail": detail if row.get("scoreable")
                      else rr.prose(row.get("why_not") or ""),
            "source": (c.get("evidence") or [row.get("source") or ""])[0],
        }
    return out
```

## 2 · `_status()` collapses from two axes to one

```diff
@@ def _status(cell: dict) -> tuple:
     """(css class, label). Derived from the number, never asserted."""
+    # % of achievable — one axis, higher is better, ceiling-relative.
+    if cell.get("pct") is not None:
+        v = cell["pct"]
+        if v >= PCT_GREEN:
+            return "good", "good"
+        if v >= PCT_AMBER:
+            return "warn", "partial"
+        return "crit", "weak"
     if cell.get("rate") is not None:
```

`rate` and `ned` stay until every cell has moved, so a half-migrated board still
colours. The native value is already in `detail`, so nothing is lost.

## 3 · Trust becomes visible

```diff
@@
-    return '<div class="cell %s">%s</div>' % (klass, body)
+    trust = "" if cell.get("ceiling_status") in rr.TRUSTED_CEILING_STATUS else " hatched"
+    return '<div class="cell %s%s">%s</div>' % (klass, trust, body)
```

```css
.cell.hatched{background-image:repeating-linear-gradient(45deg,
  rgba(128,128,128,.35) 0 3px,transparent 3px 7px)}
```

Twenty of the forty scoreable rows are `assumed`. A row scored against a guess
and one scored against a corroborated ceiling must not look identical, and today
they do.

## 4 · Unscoreable cells keep their grey and gain `why_not`

Handled by `registry_metrics()` above: no `pct` ⇒ `_status` returns
`("grey", "unmeasured")` unchanged, and `detail` becomes the registry's own
`why_not` instead of a hand-written string in the content JSON. Sixteen rows.

## 5 · The delta column — NOT drafted here, and it is the one to be careful with

The README gates it on four conditions (equal `era_key`; equal `ceiling.value`
**and** `ceiling.evidence`; magnitude over the row's own `noise_floor`; and
`companions.edits` moving with the ratio). The registry supports all four, and
`registry_report.py` already renders `companions` on every row that has them —
but **it has no second snapshot to difference against**, so a delta column would
be built with no data to test it on. It needs a stamped history file first
(`current-accuracy.json`'s shape), which is a change to the *builder*, not the
renderer.

⚠️ Note also that the registry's own comparability rule says most rows may not
be differenced at all: 5 of 56 rows declare a `time_series` key. A delta column
would print "—" on 51 of them.

## 6 · Two build-time refusals

```diff
@@ def main() -> int:
     ap.add_argument("--check", action="store_true",
@@
+    ap.add_argument("--strict", action="store_true",
+                    help="fail the build on any registry warning")
@@
+    from tools.dashboard import registry_report as rr
+    rc = rr.main(["--check"] + (["--strict"] if args.strict else []))
+    if rc:
+        print("the registry report is stale or warning — regenerate it first",
+              file=sys.stderr)
+        return rc
```

Same shape as `accuracy_record.check()`: a hand-edited figure, a missing
evidence file or a withheld row fails the suite rather than rendering.

---

## What this integration does NOT get you

- **A single top-line number.** There isn't one and there must not be
  (`pool_key`). The flow graph already renders per stage; the registry makes the
  refusal structural rather than conventional.
- **`render_with` pairs.** ⚠️ This is the second field a cell cannot hold, and
  it fails the same way `mandatory_caption` does. A flow graph places one cell
  per stage, so two rows bound by `render_with` land in different cells or in
  none — and the schema says a consumer that cannot place them together must
  render **neither**. So a bound pair either gets one merged cell showing both
  figures side by side, or stays off the graph and links here. `registry_metrics()`
  above does **not** yet implement this; wiring it in must call
  `rr.bind_groups()` and drop or merge every bound row, or the dashboard will
  print the flattering half alone.
- **Adjacency in general.** `registry-report.html` gets it from `render_with`
  (a schema binding) and contextualises families with `era_key` (same
  measurement conditions). Only the first is a rule; the second is a reading
  aid. The dashboard should link to the report rather than reproduce either.
- **Anything about scans that the harness cannot see.** Ten of the sixteen
  unscoreable rows are `visibility`. Wiring them in makes the blind spots
  *visible*; it does not make them measured.
