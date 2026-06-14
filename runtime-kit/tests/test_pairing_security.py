from __future__ import annotations

from datetime import datetime, timedelta, timezone

from kaka_mobile_runtime_kit.pairing import (
    InMemoryPairingStore,
    PairingManager,
    PairingSecurityConfig,
    StaticPairingClock,
)


def _clock() -> StaticPairingClock:
    return StaticPairingClock(datetime(2026, 6, 5, 8, 0, 0, tzinfo=timezone.utc))


def test_production_pairing_session_is_short_lived_and_single_use():
    clock = _clock()
    manager = PairingManager(
        store=InMemoryPairingStore(),
        clock=clock,
        config=PairingSecurityConfig(code_ttl_seconds=120),
    )

    session = manager.issue_pairing_session(
        endpoint="https://macbook-pro.local:8765",
        runtime="hermes",
        display_name="Kartz MacBook Runtime",
    )
    payload = manager.pairing_payload(session)
    first = manager.exchange_pairing_code(
        session.pairing_code,
        device_name="Kartz iPhone",
        device_public_id="device_abc",
    )
    replay = manager.exchange_pairing_code(
        session.pairing_code,
        device_name="Kartz iPhone",
        device_public_id="device_abc",
    )

    assert session.pairing_code.startswith("pair_")
    assert payload == {
        "version": 1,
        "endpoint": "https://macbook-pro.local:8765",
        "runtime": "hermes",
        "display_name": "Kartz MacBook Runtime",
        "pairing_code": session.pairing_code,
        "expires_at": "2026-06-05T08:02:00Z",
    }
    assert first.ok is True
    assert first.token_record is not None
    assert first.token_record.token.startswith("mobile_")
    assert manager.is_mobile_token_active(first.token_record.token) is True
    assert replay.ok is False
    assert replay.error_code == "pairing_already_used"


def test_expired_pairing_code_is_rejected_without_issuing_token():
    clock = _clock()
    manager = PairingManager(
        store=InMemoryPairingStore(),
        clock=clock,
        config=PairingSecurityConfig(code_ttl_seconds=60),
    )
    session = manager.issue_pairing_session(
        endpoint="https://macbook-pro.local:8765",
        runtime="hermes",
        display_name="Kartz MacBook Runtime",
    )

    clock.advance(timedelta(seconds=61))
    result = manager.exchange_pairing_code(
        session.pairing_code,
        device_name="Kartz iPhone",
        device_public_id="device_abc",
    )

    assert result.ok is False
    assert result.error_code == "pairing_expired"
    assert manager.list_mobile_devices() == []


def test_mobile_token_can_be_revoked_and_listed_without_raw_secret():
    manager = PairingManager(
        store=InMemoryPairingStore(),
        clock=_clock(),
        config=PairingSecurityConfig(code_ttl_seconds=120),
    )
    session = manager.issue_pairing_session(
        endpoint="https://macbook-pro.local:8765",
        runtime="openclaw",
        display_name="Kartz OpenClaw Runtime",
    )
    result = manager.exchange_pairing_code(
        session.pairing_code,
        device_name="Kartz iPhone",
        device_public_id="device_abc",
    )
    assert result.token_record is not None

    assert manager.revoke_mobile_token(result.token_record.token) is True
    assert manager.is_mobile_token_active(result.token_record.token) is False
    devices = manager.list_mobile_devices()

    assert devices == [
        {
            "device_public_id": "device_abc",
            "device_name": "Kartz iPhone",
            "runtime": "openclaw",
            "issued_at": "2026-06-05T08:00:00Z",
            "expires_at": None,
            "revoked": True,
            "token_suffix": result.token_record.token[-6:],
        }
    ]
    assert result.token_record.token not in str(devices)


def test_phone_safe_security_summary_excludes_tokens_and_tls_private_paths():
    manager = PairingManager(
        store=InMemoryPairingStore(),
        clock=_clock(),
        config=PairingSecurityConfig(
            code_ttl_seconds=180,
            token_ttl_seconds=3600,
            trusted_local_tls_required=True,
            tls_trust_state="configured",
            tls_certificate_label="Pocket Agent Local Runtime",
            tls_private_key_path="/Users/kartz/.kaka/private/key.pem",
        ),
    )

    summary = manager.phone_safe_security_summary()
    rendered = str(summary)

    assert summary == {
        "pairing_code_ttl_seconds": 180,
        "mobile_token_ttl_seconds": 3600,
        "mobile_token_revocation_supported": True,
        "trusted_local_tls_required": True,
        "tls_trust_state": "configured",
        "tls_certificate_label": "Pocket Agent Local Runtime",
    }
    assert "key.pem" not in rendered
    assert "tls_private_key_path" not in rendered
    assert not any(str(value).startswith("mobile_") for value in summary.values())


def test_pairing_payload_includes_non_secret_tls_pin_metadata_when_configured():
    manager = PairingManager(
        store=InMemoryPairingStore(),
        clock=_clock(),
        config=PairingSecurityConfig(
            code_ttl_seconds=120,
            trusted_local_tls_required=True,
            tls_trust_state="configured",
            tls_certificate_label="Pocket Agent Local Runtime",
            tls_public_key_sha256="a" * 64,
            tls_private_key_path="/Users/kartz/.kaka/private/key.pem",
        ),
    )
    session = manager.issue_pairing_session(
        endpoint="https://macbook-pro.local:8765",
        runtime="hermes",
        display_name="Kartz MacBook Runtime",
    )

    payload = manager.pairing_payload(session)
    rendered = str(payload)

    assert payload["trusted_local_tls_required"] is True
    assert payload["tls_certificate_label"] == "Pocket Agent Local Runtime"
    assert payload["tls_public_key_sha256"] == "a" * 64
    assert "key.pem" not in rendered
    assert "tls_private_key_path" not in rendered
