from __future__ import annotations

from datetime import datetime, timezone

from kaka_mobile_runtime_kit.pairing import MobileTokenRecord, PairingSession
from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore


def _session() -> PairingSession:
    issued_at = datetime(2026, 6, 5, 8, 0, 0, tzinfo=timezone.utc)
    return PairingSession(
        session_id="session_123",
        pairing_code="pair_sqlite_123",
        endpoint="https://macbook-pro.local:8765",
        runtime="hermes",
        display_name="Kartz MacBook Runtime",
        issued_at=issued_at,
        expires_at=datetime(2026, 6, 5, 8, 2, 0, tzinfo=timezone.utc),
    )


def _token() -> MobileTokenRecord:
    return MobileTokenRecord(
        token="mobile_secret_123456",
        device_name="Kartz iPhone",
        device_public_id="device_abc",
        runtime="hermes",
        issued_at=datetime(2026, 6, 5, 8, 0, 30, tzinfo=timezone.utc),
        expires_at=None,
    )


def test_sqlite_store_persists_pairing_session_and_used_state(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    store = SQLiteRuntimeStore(path)
    store.initialize()
    store.save_pairing_session(_session())

    reopened = SQLiteRuntimeStore(path)
    reopened.initialize()
    loaded = reopened.load_pairing_session("pair_sqlite_123")
    used = reopened.mark_pairing_session_used(
        "pair_sqlite_123",
        datetime(2026, 6, 5, 8, 0, 45, tzinfo=timezone.utc),
    )

    assert loaded == _session()
    assert used is not None
    assert used.used_at is not None
    assert used.used_at.isoformat() == "2026-06-05T08:00:45+00:00"


def test_sqlite_store_does_not_reuse_already_used_pairing_session(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    store = SQLiteRuntimeStore(path)
    store.initialize()
    store.save_pairing_session(_session())

    first = store.mark_pairing_session_used(
        "pair_sqlite_123",
        datetime(2026, 6, 5, 8, 0, 45, tzinfo=timezone.utc),
    )
    second = store.mark_pairing_session_used(
        "pair_sqlite_123",
        datetime(2026, 6, 5, 8, 1, 0, tzinfo=timezone.utc),
    )
    loaded = store.load_pairing_session("pair_sqlite_123")

    assert first is not None
    assert second is None
    assert loaded is not None
    assert loaded.used_at is not None
    assert loaded.used_at.isoformat() == "2026-06-05T08:00:45+00:00"


def test_sqlite_store_persists_mobile_token_revocation(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    store = SQLiteRuntimeStore(path)
    store.initialize()
    store.save_mobile_token(_token())

    reopened = SQLiteRuntimeStore(path)
    reopened.initialize()
    assert reopened.load_mobile_token("mobile_secret_123456") == _token()

    revoked = reopened.revoke_mobile_token(
        "mobile_secret_123456",
        datetime(2026, 6, 5, 8, 1, 0, tzinfo=timezone.utc),
    )
    loaded = SQLiteRuntimeStore(path)
    loaded.initialize()
    token = loaded.load_mobile_token("mobile_secret_123456")

    assert revoked is True
    assert token is not None
    assert token.revoked_at is not None
    assert token.revoked_at.isoformat() == "2026-06-05T08:01:00+00:00"
    assert [record.token for record in loaded.list_mobile_tokens()] == ["mobile_secret_123456"]
