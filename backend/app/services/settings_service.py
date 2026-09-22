from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Setting
from app.schemas.settings import SettingsRead, SettingsUpdate


MODEL_SETTING_KEYS = ("base_url", "model", "temperature", "max_tokens")


@dataclass(slots=True)
class RuntimeSecrets:
    api_key: str | None = None


_runtime_secrets = RuntimeSecrets()
_secrets_lock = Lock()


def mask_key(value: str) -> str | None:
    if not value:
        return None
    if len(value) <= 7:
        return "****"
    return f"{value[:3]}-****{value[-4:]}"


class SettingsService:
    def __init__(self, session: Session, environment: Settings) -> None:
        self.session = session
        self.environment = environment

    def values(self) -> dict[str, object]:
        stored = {
            key: self.session.get(Setting, key).value
            for key in MODEL_SETTING_KEYS
            if self.session.get(Setting, key) is not None
        }
        with _secrets_lock:
            runtime_key = _runtime_secrets.api_key
        api_key = runtime_key if runtime_key is not None else self.environment.api_key
        return {
            "base_url": stored.get("base_url", self.environment.api_base),
            "model": stored.get("model", self.environment.model),
            "temperature": float(stored.get("temperature", self.environment.temperature)),
            "max_tokens": int(stored.get("max_tokens", self.environment.max_tokens)),
            "api_key": api_key,
        }

    def read(self) -> SettingsRead:
        values = self.values()
        api_key = str(values.pop("api_key"))
        return SettingsRead(
            **values,
            api_key_configured=bool(api_key),
            api_key_masked=mask_key(api_key),
        )

    def update(self, payload: SettingsUpdate) -> SettingsRead:
        changes = payload.model_dump(exclude_unset=True)
        for key in MODEL_SETTING_KEYS:
            if key not in changes or changes[key] is None:
                continue
            record = self.session.get(Setting, key)
            if record is None:
                record = Setting(key=key, value=str(changes[key]))
                self.session.add(record)
            else:
                record.value = str(changes[key])
        with _secrets_lock:
            if payload.clear_api_key:
                _runtime_secrets.api_key = ""
            elif payload.api_key:
                _runtime_secrets.api_key = payload.api_key.strip()
        self.session.commit()
        return self.read()


def reset_runtime_secrets() -> None:
    with _secrets_lock:
        _runtime_secrets.api_key = None

