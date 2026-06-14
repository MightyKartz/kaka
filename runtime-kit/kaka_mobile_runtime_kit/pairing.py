from __future__ import annotations

import secrets
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Protocol


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso8601_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalized_public_key_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64:
        return ""
    if any(char not in "0123456789abcdef" for char in normalized):
        return ""
    return normalized


class PairingClock(Protocol):
    def now(self) -> datetime:
        ...


class SystemPairingClock:
    def now(self) -> datetime:
        return _utc_now()


class StaticPairingClock:
    def __init__(self, current: datetime) -> None:
        self.current = current.astimezone(timezone.utc).replace(microsecond=0)

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current = (self.current + delta).astimezone(timezone.utc).replace(microsecond=0)


@dataclass(frozen=True)
class PairingSecurityConfig:
    code_ttl_seconds: int = 120
    token_ttl_seconds: int | None = None
    trusted_local_tls_required: bool = False
    tls_trust_state: str = "not_configured"
    tls_certificate_label: str = ""
    tls_public_key_sha256: str = ""
    tls_private_key_path: str = ""
    runtime_version: str = "2026.5.16"

    def normalized_code_ttl_seconds(self) -> int:
        return min(max(int(self.code_ttl_seconds), 60), 300)

    def normalized_token_ttl_seconds(self) -> int | None:
        if self.token_ttl_seconds is None:
            return None
        value = int(self.token_ttl_seconds)
        if value <= 0:
            return None
        return max(value, 300)


@dataclass(frozen=True)
class PairingSession:
    session_id: str
    pairing_code: str
    endpoint: str
    runtime: str
    display_name: str
    issued_at: datetime
    expires_at: datetime
    used_at: datetime | None = None

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now.astimezone(timezone.utc)


@dataclass(frozen=True)
class MobileTokenRecord:
    token: str
    device_name: str
    device_public_id: str
    runtime: str
    issued_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and self.expires_at <= now.astimezone(timezone.utc)


@dataclass(frozen=True)
class PairingExchangeResult:
    ok: bool
    endpoint_id: str = ""
    display_name: str = ""
    runtime: str = ""
    runtime_version: str = ""
    token_record: MobileTokenRecord | None = None
    error_code: str = ""
    error_message: str = ""

    def to_mobile_bridge(self) -> dict[str, object]:
        if not self.ok or self.token_record is None:
            return {
                "error": {
                    "code": self.error_code,
                    "message": self.error_message,
                }
            }
        return {
            "endpoint_id": self.endpoint_id,
            "display_name": self.display_name,
            "runtime": self.runtime,
            "runtime_version": self.runtime_version,
            "mobile_token": self.token_record.token,
            "token_expires_at": _iso8601_z(self.token_record.expires_at),
        }


class PairingStore(Protocol):
    def save_pairing_session(self, session: PairingSession) -> None:
        ...

    def load_pairing_session(self, pairing_code: str) -> PairingSession | None:
        ...

    def mark_pairing_session_used(self, pairing_code: str, used_at: datetime) -> PairingSession | None:
        ...

    def save_mobile_token(self, record: MobileTokenRecord) -> None:
        ...

    def load_mobile_token(self, token: str) -> MobileTokenRecord | None:
        ...

    def revoke_mobile_token(self, token: str, revoked_at: datetime) -> bool:
        ...

    def list_mobile_tokens(self) -> list[MobileTokenRecord]:
        ...


class InMemoryPairingStore:
    def __init__(self) -> None:
        self.sessions: dict[str, PairingSession] = {}
        self.tokens: dict[str, MobileTokenRecord] = {}

    def save_pairing_session(self, session: PairingSession) -> None:
        self.sessions[session.pairing_code] = session

    def load_pairing_session(self, pairing_code: str) -> PairingSession | None:
        return self.sessions.get(pairing_code)

    def mark_pairing_session_used(self, pairing_code: str, used_at: datetime) -> PairingSession | None:
        session = self.sessions.get(pairing_code)
        if session is None:
            return None
        if session.is_used:
            return None
        updated = replace(session, used_at=used_at.astimezone(timezone.utc).replace(microsecond=0))
        self.sessions[pairing_code] = updated
        return updated

    def save_mobile_token(self, record: MobileTokenRecord) -> None:
        self.tokens[record.token] = record

    def load_mobile_token(self, token: str) -> MobileTokenRecord | None:
        return self.tokens.get(token)

    def revoke_mobile_token(self, token: str, revoked_at: datetime) -> bool:
        record = self.tokens.get(token)
        if record is None:
            return False
        self.tokens[token] = replace(record, revoked_at=revoked_at.astimezone(timezone.utc).replace(microsecond=0))
        return True

    def list_mobile_tokens(self) -> list[MobileTokenRecord]:
        return sorted(self.tokens.values(), key=lambda record: (record.issued_at, record.device_public_id))


class PairingManager:
    def __init__(
        self,
        store: PairingStore,
        clock: PairingClock | None = None,
        config: PairingSecurityConfig | None = None,
    ) -> None:
        self.store = store
        self.clock = clock or SystemPairingClock()
        self.config = config or PairingSecurityConfig()

    def issue_pairing_session(self, endpoint: str, runtime: str, display_name: str) -> PairingSession:
        issued_at = self.clock.now()
        expires_at = issued_at + timedelta(seconds=self.config.normalized_code_ttl_seconds())
        session = PairingSession(
            session_id=f"pairing_session_{secrets.token_urlsafe(12)}",
            pairing_code=f"pair_{secrets.token_urlsafe(18)}",
            endpoint=endpoint,
            runtime=runtime,
            display_name=display_name,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        self.store.save_pairing_session(session)
        return session

    def pairing_payload(self, session: PairingSession) -> dict[str, object]:
        payload: dict[str, object] = {
            "version": 1,
            "endpoint": session.endpoint,
            "runtime": session.runtime,
            "display_name": session.display_name,
            "pairing_code": session.pairing_code,
            "expires_at": _iso8601_z(session.expires_at),
        }
        payload.update(self._pairing_tls_metadata())
        return payload

    def exchange_pairing_code(self, pairing_code: str, device_name: str, device_public_id: str) -> PairingExchangeResult:
        now = self.clock.now()
        session = self.store.load_pairing_session(pairing_code)
        if session is None or session.is_expired(now):
            return self._error("pairing_expired", "The pairing code is missing or expired.")
        if session.is_used:
            return self._error("pairing_already_used", "The pairing code has already been used.")

        used = self.store.mark_pairing_session_used(pairing_code, now)
        if used is None:
            refreshed = self.store.load_pairing_session(pairing_code)
            if refreshed is not None and refreshed.is_used:
                return self._error("pairing_already_used", "The pairing code has already been used.")
            return self._error("pairing_expired", "The pairing code is missing or expired.")
        token_ttl = self.config.normalized_token_ttl_seconds()
        token = MobileTokenRecord(
            token=f"mobile_{secrets.token_urlsafe(32)}",
            device_name=device_name.strip() or "Pocket Agent iPhone",
            device_public_id=device_public_id.strip() or "device_unknown",
            runtime=used.runtime,
            issued_at=now,
            expires_at=(now + timedelta(seconds=token_ttl)) if token_ttl is not None else None,
        )
        self.store.save_mobile_token(token)
        return PairingExchangeResult(
            ok=True,
            endpoint_id=f"endpoint_{used.runtime}",
            display_name=used.display_name,
            runtime=used.runtime,
            runtime_version=self.config.runtime_version,
            token_record=token,
        )

    def is_mobile_token_active(self, token: str) -> bool:
        record = self.store.load_mobile_token(token)
        if record is None:
            return False
        now = self.clock.now()
        return not record.is_revoked and not record.is_expired(now)

    def revoke_mobile_token(self, token: str) -> bool:
        return self.store.revoke_mobile_token(token, self.clock.now())

    def list_mobile_devices(self) -> list[dict[str, object]]:
        return [
            {
                "device_public_id": record.device_public_id,
                "device_name": record.device_name,
                "runtime": record.runtime,
                "issued_at": _iso8601_z(record.issued_at),
                "expires_at": _iso8601_z(record.expires_at),
                "revoked": record.is_revoked,
                "token_suffix": record.token[-6:],
            }
            for record in self.store.list_mobile_tokens()
        ]

    def phone_safe_security_summary(self) -> dict[str, object]:
        summary: dict[str, object] = {
            "pairing_code_ttl_seconds": self.config.normalized_code_ttl_seconds(),
            "mobile_token_ttl_seconds": self.config.normalized_token_ttl_seconds(),
            "mobile_token_revocation_supported": True,
            "trusted_local_tls_required": bool(self.config.trusted_local_tls_required),
            "tls_trust_state": self.config.tls_trust_state,
            "tls_certificate_label": self.config.tls_certificate_label,
        }
        fingerprint = _normalized_public_key_sha256(self.config.tls_public_key_sha256)
        if fingerprint:
            summary["tls_public_key_sha256"] = fingerprint
        return summary

    def _pairing_tls_metadata(self) -> dict[str, object]:
        metadata: dict[str, object] = {}
        if self.config.trusted_local_tls_required:
            metadata["trusted_local_tls_required"] = True
        if self.config.tls_certificate_label.strip():
            metadata["tls_certificate_label"] = self.config.tls_certificate_label.strip()
        fingerprint = _normalized_public_key_sha256(self.config.tls_public_key_sha256)
        if fingerprint:
            metadata["tls_public_key_sha256"] = fingerprint
        return metadata

    def _error(self, code: str, message: str) -> PairingExchangeResult:
        return PairingExchangeResult(ok=False, error_code=code, error_message=message)
