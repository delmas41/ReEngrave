"""Pytest configuration for ReEngrave backend tests."""

import os
import sys
import tempfile

# Add the backend directory to sys.path so modules can be imported directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Point every module-level setting at a throwaway directory BEFORE any test
# module imports `core.config` / `database.connection` / `main` (both read
# the environment once, at import). Without this the first module to import
# `main` decides the DB file, and a stale ./reengrave.db from an older
# schema (e.g. before Score.user_id) breaks every route test.
_tmp_root = tempfile.mkdtemp(prefix="reengrave-tests-")
os.environ.setdefault("UPLOAD_DIR", os.path.join(_tmp_root, "uploads"))
os.environ.setdefault("EXPORT_DIR", os.path.join(_tmp_root, "exports"))
os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///" + os.path.join(_tmp_root, "test.db"))
os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)
os.makedirs(os.environ["EXPORT_DIR"], exist_ok=True)

# The app refuses to start with the shipped default SECRET_KEY unless this
# is set (core.config.check_startup_secret); tests run with the default.
os.environ.setdefault("ALLOW_DEFAULT_SECRET", "true")
