"""Configuration for the engrave pipeline."""

import os

CLAUDE_MODEL = os.getenv("ENGRAVE_MODEL", "claude-opus-4-6")
PDF_DPI = int(os.getenv("ENGRAVE_DPI", "300"))
OUTPUT_DIR = os.getenv("ENGRAVE_OUTPUT", "./output")

# Learning system
CORRECTIONS_DB = os.path.join(OUTPUT_DIR, "corrections_db.json")
LEARNED_PATTERNS = os.path.join(OUTPUT_DIR, "learned_patterns.json")
ENGINE_ACCURACY = os.path.join(OUTPUT_DIR, "engine_accuracy.json")
FINETUNING_DATA = os.path.join(OUTPUT_DIR, "finetuning_data.jsonl")

# Auto-accept thresholds
AUTO_ACCEPT_MIN_SAMPLES = 10
AUTO_ACCEPT_MIN_ACCURACY = 0.90
PATTERN_MIN_SAMPLES = 5
PATTERN_MIN_ERROR_RATE = 0.60
