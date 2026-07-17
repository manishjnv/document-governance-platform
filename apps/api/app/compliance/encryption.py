"""Encryption-at-rest utility (T-2050).

encrypt_value/decrypt_value wrap cryptography.fernet.Fernet (symmetric,
authenticated, random IV per call -- same plaintext produces different
ciphertext each time). Key comes from settings.encryption_key; if unset,
an ephemeral key is generated once at import time so the utility never
crashes, at the cost of ciphertext not surviving a process restart.

This module only builds the utility -- no existing column/table is wired to
it in this pass. Picking a real target field (e.g. encrypting a specific PII
column) is a follow-up decision, not made speculatively here.
"""

import logging

from cryptography.fernet import Fernet

from app.config import settings

logger = logging.getLogger(__name__)


def _load_fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        logger.warning(
            "settings.encryption_key is unset -- generating an ephemeral "
            "Fernet key for this process. Values encrypted now will NOT "
            "decrypt after a restart; set encryption_key for anything "
            "persisted across deploys."
        )
        key = Fernet.generate_key()
    elif isinstance(key, str):
        key = key.encode()
    return Fernet(key)


_fernet = _load_fernet()


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string, returning a URL-safe base64 Fernet token."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet token produced by encrypt_value."""
    return _fernet.decrypt(ciphertext.encode()).decode()


if __name__ == "__main__":
    # ponytail: smallest runnable check -- round-trip + non-determinism.
    pt = "sensitive-value"
    c1, c2 = encrypt_value(pt), encrypt_value(pt)
    assert c1 != c2, "same plaintext should produce different ciphertext"
    assert decrypt_value(c1) == pt == decrypt_value(c2)
    print("encryption self-check OK")
