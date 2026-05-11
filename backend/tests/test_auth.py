import hashlib
import hmac

import pytest
from fastapi import HTTPException

from app.auth import require_admin_token, verify_bolna_signature


def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_verify_bolna_signature_accepts_valid():
    body = b'{"x":1}'
    sig = sign("topsecret", body)
    assert verify_bolna_signature(body, sig, "topsecret") is True


def test_verify_bolna_signature_rejects_tampered_body():
    body = b'{"x":1}'
    sig = sign("topsecret", body)
    assert verify_bolna_signature(b'{"x":2}', sig, "topsecret") is False


def test_verify_bolna_signature_rejects_wrong_secret():
    body = b'{"x":1}'
    sig = sign("topsecret", body)
    assert verify_bolna_signature(body, sig, "different") is False


def test_verify_bolna_signature_rejects_malformed_header():
    body = b'{"x":1}'
    assert verify_bolna_signature(body, "not-hex", "topsecret") is False


def test_verify_bolna_signature_empty_secret_skips_verification():
    """If we don't have a secret configured, treat as unverified (caller decides)."""
    assert verify_bolna_signature(b"anything", "any", "") is False


def test_require_admin_token_accepts():
    require_admin_token("expected", "expected")  # should not raise


def test_require_admin_token_rejects_wrong():
    with pytest.raises(HTTPException) as exc:
        require_admin_token("wrong", "expected")
    assert exc.value.status_code == 401


def test_require_admin_token_rejects_empty():
    with pytest.raises(HTTPException):
        require_admin_token(None, "expected")
