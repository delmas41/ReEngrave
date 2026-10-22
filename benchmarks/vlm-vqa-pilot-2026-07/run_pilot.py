#!/usr/bin/env python3
"""
VLM-as-verifier pilot: measure how accurately Claude (Haiku 4.5 and Sonnet 5)
answers narrow visual questions about REAL, degraded scanned orchestral score
cells, using the existing YOLO hand-label ground truth as the answer key.

This is a measurement pilot, not a product feature: it asks whether Claude
could serve as a cheap automated verifier for the local YOLO OMR pipeline
(flagging cells where the model's detections and Claude's read of the image
disagree), and whether Haiku is "good enough" or Sonnet is needed.

Ground truth: `data/user-labeled/v1-2026-05-18-orchestral` and
`v2-2026-06-08-beet5` (97 hand-labeled cells total). Each cell has a YOLO
label file (`labels/<cell_id>.txt`, lines of `class_id cx cy w h` normalized)
and a cropped cell PNG (`images/<cell_id>.png`, symlinked to the source
benchmark directory). Class-id -> name mapping is read from
`data/user-labeled/catalog.yaml` (`names:` list, index = class id) — this is
the same mapping `verdicts_to_yolo_labels.py` used to WRITE the label files,
so it is authoritative (more so than `deepscores_classes.py`, whose spellings
can differ from the trained/labeled vocabulary per project docs).

Six question types are derived programmatically from the labels:
  Q1 notehead_count          - count of all notehead* classes
  Q2 hollow_notehead_present - any noteheadHalf*/noteheadWhole*/noteheadDoubleWhole*
                                (unfilled) vs noteheadBlack* (filled)
  Q3 accidental_present      - any accidental* class
  Q4 rest_count               - count of all rest* classes
  Q5 dynamic_present          - any dynamic* class (letters, hairpins)
  Q6 augmentation_dot_present - augmentationDot class present

A question type is SKIPPED if the answer distribution is degenerate: for
count questions, fewer than 10 cells with a nonzero value; for boolean
questions, fewer than 10 cells in the minority class. (In practice all six
pass this gate on the 97-cell set — see report.md.)

API usage: one Anthropic Messages API call per (cell, model) — one image +
one text prompt asking all 6 questions at once, with a JSON-schema
`output_config.format` to force a single well-formed JSON object back
(supported on both Haiku 4.5 and Sonnet 5). No thinking (disabled on Sonnet 5
explicitly; omitted on Haiku 4.5, which doesn't support the thinking param)
so cost/latency stay minimal for this narrow classification task.

Usage:
    python3 run_pilot.py                  # full run: 97 cells x 2 models
    python3 run_pilot.py --limit 5         # smoke test on first 5 cells
    python3 run_pilot.py --models haiku    # just one model
    python3 run_pilot.py --dry-run         # ground truth + cost estimate only, no API calls

Reads ANTHROPIC_API_KEY from backend/.env in the main ReEngrave checkout
(never printed). Writes results.json (raw per-cell per-question answers vs
truth) next to this script.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import os
import re
import sys
import threading
import time
from collections import Counter
from pathlib import Path

import yaml

try:
    import anthropic
except ImportError:
    print("Run this with the scratchpad venv's python (pip install anthropic pyyaml pillow).", file=sys.stderr)
    raise

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]  # .../crazy-margulis-20faeb (this worktree)
MAIN_CHECKOUT = Path("/Users/seanjohnson/Desktop/ReEngrave")
ENV_FILE = MAIN_CHECKOUT / "backend" / ".env"

VERSION_DIRS = [
    REPO_ROOT / "data/user-labeled/v1-2026-05-18-orchestral",
    REPO_ROOT / "data/user-labeled/v2-2026-06-08-beet5",
]
CATALOG_YAML = REPO_ROOT / "data/user-labeled/catalog.yaml"

RESULTS_PATH = SCRIPT_DIR / "results.json"

# ---------------------------------------------------------------------------
# Models + pricing (see skill "claude-api" model table, cached 2026-06-24)
# ---------------------------------------------------------------------------

MODEL_IDS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-5",
}
# USD per 1M tokens. Sonnet 5 sticker is $3/$15; a $2/$10 intro rate applies
# through 2026-08-31, which covers this pilot's run date (2026-07-10), but we
# budget against the sticker price to stay conservative — actual billed cost
# may come in lower.
PRICE_PER_MTOK = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-sonnet-5": {"input": 3.00, "output": 15.00},
}

HARD_BUDGET_USD = 2.00
SAFETY_BUDGET_USD = 1.90  # stop issuing new calls once projected spend crosses this

# ---------------------------------------------------------------------------
# Ground truth extraction
# ---------------------------------------------------------------------------


def load_class_names() -> list[str]:
    catalog = yaml.safe_load(CATALOG_YAML.read_text())
    return catalog["names"]


def load_cells(names: list[str]) -> dict[str, dict]:
    """Returns {cell_id: {"image_path": Path, "classes": [str, ...]}}"""
    cells: dict[str, dict] = {}
    for version_dir in VERSION_DIRS:
        labels_dir = version_dir / "labels"
        images_dir = version_dir / "images"
        for label_file in sorted(labels_dir.glob("*.txt")):
            cell_id = label_file.stem
            image_path = images_dir / f"{cell_id}.png"
            if not image_path.exists():
                print(f"WARNING: no image for {cell_id}, skipping", file=sys.stderr)
                continue
            classes = []
            for line in label_file.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                cls_id = int(line.split()[0])
                classes.append(names[cls_id])
            cells[cell_id] = {
                "image_path": image_path,
                "version": version_dir.name,
                "classes": classes,
            }
    return cells


def ground_truth_for_cell(classes: list[str]) -> dict:
    notehead_count = sum(1 for c in classes if c.lower().startswith("notehead"))
    rest_count = sum(1 for c in classes if c.lower().startswith("rest"))
    hollow_present = any(re.match(r"notehead(Half|Whole|DoubleWhole)", c) for c in classes)
    accidental_present = any(c.lower().startswith("accidental") for c in classes)
    dynamic_present = any(c.lower().startswith("dynamic") for c in classes)
    augdot_present = "augmentationDot" in classes
    return {
        "notehead_count": notehead_count,
        "hollow_notehead_present": hollow_present,
        "accidental_present": accidental_present,
        "rest_count": rest_count,
        "dynamic_present": dynamic_present,
        "augmentation_dot_present": augdot_present,
    }


QUESTION_TYPES = {
    "notehead_count": {"kind": "count", "label": "Q1 notehead count"},
    "hollow_notehead_present": {"kind": "bool", "label": "Q2 hollow notehead present"},
    "accidental_present": {"kind": "bool", "label": "Q3 accidental present"},
    "rest_count": {"kind": "count", "label": "Q4 rest count"},
    "dynamic_present": {"kind": "bool", "label": "Q5 dynamic present"},
    "augmentation_dot_present": {"kind": "bool", "label": "Q6 augmentation dot present"},
}


def check_distribution_gate(truths: dict[str, dict]) -> dict[str, dict]:
    """Returns {question: {"keep": bool, "reason": str, ...stats}}"""
    gate = {}
    for q, meta in QUESTION_TYPES.items():
        values = [t[q] for t in truths.values()]
        if meta["kind"] == "count":
            nonzero = sum(1 for v in values if v > 0)
            keep = nonzero >= 10
            gate[q] = {
                "keep": keep,
                "kind": "count",
                "n_nonzero": nonzero,
                "n_total": len(values),
                "reason": f"{nonzero}/{len(values)} cells nonzero" + ("" if keep else " (<10, SKIPPED)"),
            }
        else:
            n_true = sum(1 for v in values if v)
            n_false = len(values) - n_true
            keep = min(n_true, n_false) >= 10
            gate[q] = {
                "keep": keep,
                "kind": "bool",
                "n_true": n_true,
                "n_false": n_false,
                "reason": f"True={n_true}, False={n_false}" + ("" if keep else " (minority <10, SKIPPED)"),
            }
    return gate


# ---------------------------------------------------------------------------
# Prompt + JSON schema
# ---------------------------------------------------------------------------

PROMPT_TEXT = """You are looking at one small cropped image ("cell") from a real, scanned orchestral music score. It may show a full measure, a partial measure, or just a staff fragment. Scans are often degraded: faint ink, bleed-through from the other side of the page, skew, or low contrast.

Answer these questions about symbols that are CLEARLY drawn/visible in THIS IMAGE. Do not guess based on musical context, key signature, or what "should" be there — only count what you can actually see. If a symbol is cut off at the edge of the image but more than half of it is visible, count it; if less than half is visible, do not count it.

1. notehead_count: total number of noteheads visible (filled/black or hollow/open, any size — quarter, half, whole notes; count each notehead once even if it's part of a chord or beamed group).
2. hollow_notehead_present: true if at least one hollow (unfilled/open, white/outline-only) notehead is visible — the kind used for half notes and whole notes. false if all noteheads visible are filled/black, or there are no noteheads at all.
3. accidental_present: true if at least one accidental symbol (sharp #, flat b, natural, double-sharp, double-flat) is visible anywhere in the image, attached to any notehead.
4. rest_count: total number of rest symbols visible (whole rest, half rest, quarter rest, eighth rest, sixteenth rest, or a multi-measure rest bar) — count each rest symbol once.
5. dynamic_present: true if at least one dynamic marking is visible: a dynamics letter (p, f, m, s, z, r or combinations like mf, sfz) or a crescendo/diminuendo hairpin (< or >). Do not count expressive text words like "dolce" or "cresc." unless there is also a hairpin or letter symbol.
6. augmentation_dot_present: true if at least one augmentation dot (a small dot placed immediately to the right of a notehead, lengthening its duration) is visible.

Respond with ONLY the JSON object matching the schema. No other text."""

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "notehead_count": {"type": "integer"},
        "hollow_notehead_present": {"type": "boolean"},
        "accidental_present": {"type": "boolean"},
        "rest_count": {"type": "integer"},
        "dynamic_present": {"type": "boolean"},
        "augmentation_dot_present": {"type": "boolean"},
    },
    "required": [
        "notehead_count",
        "hollow_notehead_present",
        "accidental_present",
        "rest_count",
        "dynamic_present",
        "augmentation_dot_present",
    ],
    "additionalProperties": False,
}

MAX_TOKENS = 500

# ---------------------------------------------------------------------------
# API key
# ---------------------------------------------------------------------------


def read_api_key() -> str:
    if not ENV_FILE.exists():
        print(f"ERROR: {ENV_FILE} not found", file=sys.stderr)
        sys.exit(1)
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("ANTHROPIC_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            if key:
                return key
    print(f"ERROR: ANTHROPIC_API_KEY not found in {ENV_FILE}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


def estimate_image_tokens(image_path: Path) -> int:
    """Anthropic's published estimate: tokens ~= (width_px * height_px) / 750."""
    try:
        from PIL import Image

        with Image.open(image_path) as im:
            w, h = im.size
        return max(1, (w * h) // 750)
    except Exception:
        return 1600  # fallback rough estimate


PROMPT_TEXT_TOKEN_ESTIMATE = int(len(PROMPT_TEXT.split()) * 1.4) + 150  # + schema/system overhead
OUTPUT_TOKEN_ESTIMATE = 120  # small structured JSON object


def estimate_total_cost(cells: dict[str, dict], model_ids: list[str]) -> tuple[float, dict]:
    total = 0.0
    per_model = {}
    for model_id in model_ids:
        price = PRICE_PER_MTOK[model_id]
        model_total = 0.0
        for cell in cells.values():
            img_tok = estimate_image_tokens(cell["image_path"])
            input_tok = img_tok + PROMPT_TEXT_TOKEN_ESTIMATE
            cost = (input_tok / 1e6) * price["input"] + (OUTPUT_TOKEN_ESTIMATE / 1e6) * price["output"]
            model_total += cost
        per_model[model_id] = model_total
        total += model_total
    return total, per_model


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------


class BudgetExceeded(Exception):
    pass


class CostTracker:
    def __init__(self, hard_budget: float, safety_budget: float):
        self.hard_budget = hard_budget
        self.safety_budget = safety_budget
        self.spent = 0.0
        self.lock = threading.Lock()

    def check_and_reserve(self):
        with self.lock:
            if self.spent >= self.safety_budget:
                raise BudgetExceeded(f"Spent ${self.spent:.4f} >= safety budget ${self.safety_budget:.2f}")

    def add(self, amount: float):
        with self.lock:
            self.spent += amount
            if self.spent >= self.hard_budget:
                print(
                    f"\n!!! HARD BUDGET (${self.hard_budget:.2f}) EXCEEDED: spent ${self.spent:.4f} !!!",
                    file=sys.stderr,
                )


def call_model(client: "anthropic.Anthropic", model_id: str, cell_id: str, image_path: Path) -> dict:
    """Returns {"raw_text": str, "parsed": dict|None, "error": str|None,
    "usage": {"input_tokens": int, "output_tokens": int}, "cost_usd": float}"""
    image_bytes = image_path.read_bytes()
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    kwargs = dict(
        model=model_id,
        max_tokens=MAX_TOKENS,
        output_config={"format": {"type": "json_schema", "schema": JSON_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64},
                    },
                    {"type": "text", "text": PROMPT_TEXT},
                ],
            }
        ],
    )
    # Sonnet 5 defaults to adaptive thinking when `thinking` is omitted; disable
    # it explicitly for this narrow, cheap classification task. Haiku 4.5
    # predates the thinking param entirely — don't send it.
    if model_id == MODEL_IDS["sonnet"]:
        kwargs["thinking"] = {"type": "disabled"}

    last_err = None
    for attempt in range(3):
        try:
            response = client.messages.create(**kwargs)
            break
        except anthropic.RateLimitError as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                last_err = e
                time.sleep(2 * (attempt + 1))
                continue
            return {
                "raw_text": None,
                "parsed": None,
                "error": f"APIStatusError {e.status_code}: {e.message}",
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "cost_usd": 0.0,
            }
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1)
    else:
        return {
            "raw_text": None,
            "parsed": None,
            "error": f"Failed after retries: {last_err}",
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "cost_usd": 0.0,
        }

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    price = PRICE_PER_MTOK[model_id]
    cost = (usage["input_tokens"] / 1e6) * price["input"] + (usage["output_tokens"] / 1e6) * price["output"]

    if response.stop_reason == "refusal":
        return {
            "raw_text": None,
            "parsed": None,
            "error": "refusal",
            "usage": usage,
            "cost_usd": cost,
        }

    text = None
    for block in response.content:
        if block.type == "text":
            text = block.text
            break

    parsed = None
    error = None
    if text is None:
        error = f"no text block; stop_reason={response.stop_reason}"
    else:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            error = f"JSON parse error: {e}"

    return {"raw_text": text, "parsed": parsed, "error": error, "usage": usage, "cost_usd": cost}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N cells (smoke test)")
    parser.add_argument(
        "--models", type=str, default="haiku,sonnet", help="Comma-separated: haiku,sonnet (default both)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Ground truth + cost estimate only, no API calls")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent API calls")
    args = parser.parse_args()

    model_keys = [m.strip() for m in args.models.split(",") if m.strip()]
    model_ids = [MODEL_IDS[m] for m in model_keys]

    print("Loading ground truth from YOLO labels...")
    names = load_class_names()
    cells = load_cells(names)
    print(f"Loaded {len(cells)} cells with resolvable images.")

    truths = {cid: ground_truth_for_cell(d["classes"]) for cid, d in cells.items()}
    gate = check_distribution_gate(truths)
    print("\nDistribution gate (>=10 cells needed in minority/nonzero class):")
    for q, info in gate.items():
        status = "KEEP" if info["keep"] else "SKIP"
        print(f"  [{status}] {QUESTION_TYPES[q]['label']}: {info['reason']}")

    kept_questions = [q for q, info in gate.items() if info["keep"]]
    skipped_questions = [q for q, info in gate.items() if not info["keep"]]

    cell_ids = sorted(cells.keys())
    if args.limit:
        cell_ids = cell_ids[: args.limit]
    subset_cells = {cid: cells[cid] for cid in cell_ids}

    est_total, est_per_model = estimate_total_cost(subset_cells, model_ids)
    print(f"\nCost estimate for {len(subset_cells)} cells x {len(model_ids)} model(s):")
    for model_id, cost in est_per_model.items():
        print(f"  {model_id}: ${cost:.4f}")
    print(f"  TOTAL estimated: ${est_total:.4f} (hard budget ${HARD_BUDGET_USD:.2f})")

    if est_total > HARD_BUDGET_USD:
        print("ERROR: estimated cost exceeds hard budget before any calls. Aborting.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("\n--dry-run: stopping before any API calls.")
        return

    api_key = read_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    tracker = CostTracker(HARD_BUDGET_USD, SAFETY_BUDGET_USD)

    # results[model_key][cell_id] = {"parsed":..., "error":..., "usage":..., "cost_usd":...}
    results: dict[str, dict[str, dict]] = {mk: {} for mk in model_keys}

    jobs = []
    for model_key, model_id in zip(model_keys, model_ids):
        for cell_id in cell_ids:
            jobs.append((model_key, model_id, cell_id))

    print(f"\nRunning {len(jobs)} API calls with {args.workers} workers...")
    completed = 0
    lock = threading.Lock()

    def run_job(job):
        model_key, model_id, cell_id = job
        try:
            tracker.check_and_reserve()
        except BudgetExceeded as e:
            return job, {"raw_text": None, "parsed": None, "error": f"budget stop: {e}", "usage": {}, "cost_usd": 0.0}
        image_path = cells[cell_id]["image_path"]
        result = call_model(client, model_id, cell_id, image_path)
        tracker.add(result["cost_usd"])
        return job, result

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run_job, job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            job, result = future.result()
            model_key, model_id, cell_id = job
            results[model_key][cell_id] = result
            with lock:
                completed += 1
                if completed % 20 == 0 or completed == len(jobs):
                    print(f"  {completed}/{len(jobs)} done, spent so far: ${tracker.spent:.4f}")

    print(f"\nTotal actual spend: ${tracker.spent:.4f}")

    # -----------------------------------------------------------------
    # Assemble results.json
    # -----------------------------------------------------------------
    output = {
        "meta": {
            "n_cells": len(cell_ids),
            "models": {mk: MODEL_IDS[mk] for mk in model_keys},
            "kept_questions": kept_questions,
            "skipped_questions": skipped_questions,
            "distribution_gate": gate,
            "cost_usd_actual": tracker.spent,
            "cost_usd_estimated": est_total,
            "hard_budget_usd": HARD_BUDGET_USD,
            "price_per_mtok": PRICE_PER_MTOK,
        },
        "cells": {},
    }
    for cell_id in cell_ids:
        entry = {
            "version": cells[cell_id]["version"],
            "classes": cells[cell_id]["classes"],
            "ground_truth": truths[cell_id],
            "answers": {},
        }
        for model_key in model_keys:
            r = results[model_key].get(cell_id, {})
            entry["answers"][model_key] = {
                "model_id": MODEL_IDS[model_key],
                "parsed": r.get("parsed"),
                "error": r.get("error"),
                "usage": r.get("usage"),
                "cost_usd": r.get("cost_usd"),
            }
        output["cells"][cell_id] = entry

    RESULTS_PATH.write_text(json.dumps(output, indent=2))
    print(f"\nWrote {RESULTS_PATH}")

    # -----------------------------------------------------------------
    # Quick accuracy summary to stdout
    # -----------------------------------------------------------------
    print("\n=== ACCURACY SUMMARY ===")
    for model_key in model_keys:
        print(f"\n--- {model_key} ({MODEL_IDS[model_key]}) ---")
        n_errors = sum(1 for cid in cell_ids if results[model_key].get(cid, {}).get("parsed") is None)
        print(f"  parse/API errors: {n_errors}/{len(cell_ids)}")
        for q in kept_questions:
            kind = QUESTION_TYPES[q]["kind"]
            correct = 0
            correct_tol1 = 0
            n_scored = 0
            for cid in cell_ids:
                parsed = results[model_key].get(cid, {}).get("parsed")
                if parsed is None or q not in parsed:
                    continue
                n_scored += 1
                truth_val = truths[cid][q]
                pred_val = parsed[q]
                if kind == "count":
                    if isinstance(pred_val, bool):
                        continue
                    if pred_val == truth_val:
                        correct += 1
                    if abs(pred_val - truth_val) <= 1:
                        correct_tol1 += 1
                else:
                    if bool(pred_val) == bool(truth_val):
                        correct += 1
            acc = correct / n_scored if n_scored else float("nan")
            line = f"  {QUESTION_TYPES[q]['label']}: exact={acc:.1%} (n={n_scored})"
            if kind == "count":
                acc_tol1 = correct_tol1 / n_scored if n_scored else float("nan")
                line += f", +/-1={acc_tol1:.1%}"
            print(line)


if __name__ == "__main__":
    main()
