"""passlib was replaced by direct bcrypt calls (ROADMAP 3.6b)."""

import bcrypt

from core.security import hash_password, verify_password


# Produced by the OLD stack (passlib==1.7.4 + bcrypt==3.2.2,
# CryptContext(schemes=["bcrypt"]).hash("pw-from-passlib")).
PASSLIB_HASH = "$2b$12$FkzAeX.3/5Eiau1xWO9GLeh7XjKME.CuWogQ0pmzDQt07xGb8xynq"


def test_real_passlib_hash_verifies():
    assert verify_password("pw-from-passlib", PASSLIB_HASH)
    assert not verify_password("pw-from-passlibX", PASSLIB_HASH)


def test_hash_made_by_the_old_scheme_still_verifies():
    # passlib's bcrypt handler wrote a plain "$2b$12$..." string; build one
    # with the same cost directly so the test needs no passlib.
    legacy = bcrypt.hashpw(b"correct horse", bcrypt.gensalt(rounds=12)).decode()
    assert legacy.startswith("$2b$12$")
    assert verify_password("correct horse", legacy)
    assert not verify_password("battery staple", legacy)


def test_hash_made_by_passlib_format_with_2a_prefix_verifies():
    # Very old passlib/bcrypt builds emitted $2a$; bcrypt.checkpw accepts it.
    h = bcrypt.hashpw(b"pw", bcrypt.gensalt(rounds=4)).decode().replace("$2b$", "$2a$", 1)
    assert verify_password("pw", h)


def test_new_hash_verifies_and_wrong_password_does_not():
    h = hash_password("s3cret-passphrase")
    assert h.startswith("$2b$12$")
    assert verify_password("s3cret-passphrase", h)
    assert not verify_password("s3cret-passphras", h)
    assert hash_password("s3cret-passphrase") != h  # salted


def test_long_password_is_truncated_not_rejected():
    long_pw = "a" * 100
    h = hash_password(long_pw)
    assert verify_password(long_pw, h)
    assert verify_password("a" * 72, h)  # bcrypt's own 72-byte limit


def test_malformed_hash_fails_closed():
    assert verify_password("x", "not-a-bcrypt-hash") is False
    assert verify_password("x", "") is False
