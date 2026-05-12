import hashlib
import hmac

from fastapi import HTTPException


def verify_bolna_signature(body: bytes, signature_header: str | None, secret: str) -> bool:
    """Constant-time HMAC-SHA256 verification of Bolna webhook signature."""
    if not secret or not signature_header:
        return False
    try:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    except Exception:
        return False
    return hmac.compare_digest(expected, signature_header.strip())


def require_admin_token(provided: str | None, expected: str) -> None:
    """Raises 401 if the X-Admin-Token header doesn't match."""
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid admin token")
