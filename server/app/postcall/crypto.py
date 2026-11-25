"""Encryption at rest for transcripts and audio references. One cipher, one key per deployment."""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.errors import ConfigError, StateConflictError


class DataCipher:
    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.encode())
        except ValueError as exc:
            raise ConfigError("AV_DATA_KEY is not a valid Fernet key") from exc

    def encrypt_json(self, value: Any) -> bytes:
        return self._fernet.encrypt(json.dumps(value, ensure_ascii=False).encode())

    def decrypt_json(self, token: bytes) -> Any:
        try:
            return json.loads(self._fernet.decrypt(token))
        except InvalidToken as exc:
            raise StateConflictError("ciphertext does not match the configured data key") from exc
