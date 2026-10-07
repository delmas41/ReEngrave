"""
Signed URLs for files under settings.upload_dir.

`/uploads/{path}` is served only with `?t=<exp>.<sig>`, where `sig` is
HMAC-SHA256(secret_key, f"{path}|{exp}") in hex and `exp` a unix time.
The API hands these URLs out wherever it returns a file the browser loads
(diff snippets, a score's PDF, a Gradus file); nothing else can read
`/uploads`.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from core.config import settings

URL_PREFIX = "/uploads/"


def _sig(rel_path: str, exp: int) -> str:
    msg = f"{rel_path}|{exp}".encode("utf-8")
    return hmac.new(settings.secret_key.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def upload_root() -> Path:
    return Path(settings.upload_dir).resolve()


def relative_upload_path(stored_path: Optional[str]) -> Optional[str]:
    """Map a stored path to its path relative to upload_dir (posix form).

    Accepts either a path already relative to upload_dir (diff snippets are
    stored that way) or a full path (scores and Gradus files). Returns None
    for an empty path or one that does not resolve inside upload_dir.
    """
    if not stored_path:
        return None
    root = upload_root()
    p = Path(stored_path)
    candidates = [p] if p.is_absolute() else [root / p, Path(os.path.abspath(p))]
    for cand in candidates:
        resolved = cand.resolve()
        if resolved.is_relative_to(root) and resolved.is_file():
            return resolved.relative_to(root).as_posix()
    return None


def make_token(rel_path: str, now: Optional[float] = None, ttl: Optional[int] = None) -> str:
    exp = int((now if now is not None else time.time()) + (ttl if ttl is not None else settings.upload_url_ttl_s))
    return f"{exp}.{_sig(rel_path, exp)}"


def signed_url(stored_path: Optional[str], now: Optional[float] = None) -> Optional[str]:
    """`/uploads/<rel>?t=<exp>.<sig>` for a stored path, or None."""
    rel = relative_upload_path(stored_path)
    if rel is None:
        return None
    return f"{URL_PREFIX}{quote(rel)}?t={make_token(rel, now=now)}"


def verify_token(rel_path: str, token: Optional[str], now: Optional[float] = None) -> bool:
    if not token or "." not in token:
        return False
    exp_s, sig = token.split(".", 1)
    try:
        exp = int(exp_s)
    except ValueError:
        return False
    if exp < (now if now is not None else time.time()):
        return False
    return hmac.compare_digest(sig, _sig(rel_path, exp))


def resolve_inside_uploads(rel_path: str) -> Optional[Path]:
    """The file `rel_path` names, or None if it escapes upload_dir or is
    not a regular file."""
    root = upload_root()
    try:
        target = (root / rel_path).resolve()
    except (OSError, ValueError):
        return None
    if not target.is_relative_to(root) or not target.is_file():
        return None
    return target
