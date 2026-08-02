"""Credential vault crypto for saved SIEM connections (Phase 13b, plan §2.1).

AES-256-GCM via the `cryptography` package (already a dependency through
python-jose). Ciphertext layout: 12-byte random nonce || GCM ct+tag. Every
secret is AAD-bound to its connection_id, so a ciphertext transplanted onto
another row (even same-org) fails authentication instead of decrypting.

Master key: the SIEM_CRED_KEY env var (32 bytes, base64). **Documented
limitation (plan §2.1):** the shared VPS has no KMS — an env-var key means
a host/root compromise exposes stored secrets. Accepted trade-off for v1,
mitigated by: key_version enabling rotation-by-re-encryption, secrets being
write-only through the API, decrypt happening only inside the connector
call, and customer guidance to grant least-privilege revocable credentials
(Sentinel: a service principal with ONLY 'Microsoft Sentinel Reader').

The plaintext secret must never be logged, stored, echoed, sent to an LLM,
or embedded in an error message — nothing in this module ever includes it
in an exception or log line.
"""

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_VERSION = 1          # bump on rotation; decrypt refuses unknown versions
_NONCE_BYTES = 12
_KEY_BYTES = 32
_ENV_VAR = "SIEM_CRED_KEY"


class VaultError(Exception):
    """Vault configuration/decryption failure — user-safe, secret-free."""


def _load_key() -> bytes:
    raw = os.environ.get(_ENV_VAR, "")
    if not raw:
        raise VaultError(
            "SIEM credential storage is not configured on this server "
            f"({_ENV_VAR} is unset) — saved connections are unavailable"
        )
    try:
        key = base64.b64decode(raw, validate=True)
    except (ValueError, TypeError):
        key = b""
    if len(key) != _KEY_BYTES:
        raise VaultError(
            f"{_ENV_VAR} is not a valid 32-byte base64 key — "
            "saved connections are unavailable"
        )
    return key


def is_configured() -> bool:
    try:
        _load_key()
        return True
    except VaultError:
        return False


def encrypt_secret(plaintext: str, *, aad: str) -> tuple:
    """-> (ciphertext bytes, key_version). aad = str(connection_id)."""
    key = _load_key()
    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = AESGCM(key).encrypt(
        nonce, plaintext.encode("utf-8"), aad.encode("utf-8")
    )
    return nonce + ciphertext, KEY_VERSION


def decrypt_secret(ciphertext: bytes, key_version: int, *, aad: str) -> str:
    """Decrypt for immediate in-process use inside a connector call ONLY.
    Callers must not persist, log, or return the result."""
    if key_version != KEY_VERSION:
        raise VaultError(
            "this connection's secret was stored under an old key version — "
            "re-enter the secret to re-encrypt it"
        )
    key = _load_key()
    if not isinstance(ciphertext, (bytes, bytearray)) or len(ciphertext) <= _NONCE_BYTES:
        raise VaultError("the stored credential is corrupt — re-enter the secret")
    nonce, ct = bytes(ciphertext[:_NONCE_BYTES]), bytes(ciphertext[_NONCE_BYTES:])
    try:
        plaintext = AESGCM(key).decrypt(nonce, ct, aad.encode("utf-8"))
    except InvalidTag:
        raise VaultError(
            "the stored credential could not be decrypted (wrong key or "
            "tampered data) — re-enter the secret"
        )
    return plaintext.decode("utf-8")
