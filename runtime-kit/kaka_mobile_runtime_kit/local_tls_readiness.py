from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Mapping


SCHEMA_VERSION = "kaka.local_tls_readiness.v1"
SURFACE = "hermes_openclaw_local_tls_readiness"
RUNTIMES = ("hermes", "openclaw")
REQUIRED_INPUTS = (
    "tls_trust_state",
    "tls_certificate_label",
    "tls_certificate_ref",
    "tls_public_key_sha256",
    "tls_expires_at",
    "trust_store_ref",
    "renewal_procedure_ref",
)


def _clean(value: str) -> str:
    return value.strip()


def _is_secret_like_ref(value: str) -> bool:
    lowered = _clean(value).lower()
    if not lowered:
        return False
    secret_markers = (
        "-----begin",
        "private key",
        "private_key",
        "tls_private_key",
        "bearer ",
        "token=",
        "secret",
        "mobile_",
        "sk-",
    )
    if any(marker in lowered for marker in secret_markers):
        return True
    if lowered.startswith("/users/") or lowered.startswith("~/"):
        return True
    if lowered.endswith(".key") or lowered.endswith("key.pem"):
        return True
    return False


def _non_secret_ref(value: str) -> str:
    cleaned = _clean(value)
    return "" if _is_secret_like_ref(cleaned) else cleaned


def _valid_public_key_sha256(value: str) -> bool:
    return re.fullmatch(r"[A-Fa-f0-9]{64}", _clean(value)) is not None


def _valid_future_timestamp(value: str) -> bool:
    cleaned = _clean(value)
    if not cleaned:
        return False
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc) > datetime.now(timezone.utc)


def _missing_inputs(values: Mapping[str, str]) -> list[Mapping[str, str]]:
    labels = {
        "tls_trust_state": "Trusted local TLS trust state must be configured",
        "tls_certificate_label": "User-visible local TLS certificate label",
        "tls_certificate_ref": "Non-secret certificate reference",
        "tls_public_key_sha256": "Public key SHA-256 fingerprint",
        "tls_expires_at": "Certificate expiry timestamp",
        "trust_store_ref": "Host trust store reference",
        "renewal_procedure_ref": "Certificate renewal procedure reference",
    }
    missing: list[Mapping[str, str]] = []
    if _clean(values.get("tls_trust_state", "")) != "configured":
        missing.append({"id": "tls_trust_state", "label": labels["tls_trust_state"]})
    if not _clean(values.get("tls_certificate_label", "")):
        missing.append({"id": "tls_certificate_label", "label": labels["tls_certificate_label"]})
    if not _non_secret_ref(values.get("tls_certificate_ref", "")):
        missing.append({"id": "tls_certificate_ref", "label": labels["tls_certificate_ref"]})
    if not _valid_public_key_sha256(values.get("tls_public_key_sha256", "")):
        missing.append({"id": "tls_public_key_sha256", "label": labels["tls_public_key_sha256"]})
    if not _valid_future_timestamp(values.get("tls_expires_at", "")):
        missing.append({"id": "tls_expires_at", "label": labels["tls_expires_at"]})
    if not _non_secret_ref(values.get("trust_store_ref", "")):
        missing.append({"id": "trust_store_ref", "label": labels["trust_store_ref"]})
    if not _non_secret_ref(values.get("renewal_procedure_ref", "")):
        missing.append({"id": "renewal_procedure_ref", "label": labels["renewal_procedure_ref"]})
    return missing


def build_local_tls_readiness(
    *,
    runtime: str,
    tls_trust_state: str = "not_configured",
    tls_certificate_label: str = "",
    tls_certificate_ref: str = "",
    tls_public_key_sha256: str = "",
    tls_expires_at: str = "",
    trust_store_ref: str = "",
    renewal_procedure_ref: str = "",
) -> Mapping[str, object]:
    normalized_runtime = _clean(runtime)
    if normalized_runtime not in RUNTIMES:
        raise ValueError(f"Unsupported local TLS runtime: {runtime}")

    values = {
        "tls_trust_state": tls_trust_state,
        "tls_certificate_label": tls_certificate_label,
        "tls_certificate_ref": tls_certificate_ref,
        "tls_public_key_sha256": tls_public_key_sha256,
        "tls_expires_at": tls_expires_at,
        "trust_store_ref": trust_store_ref,
        "renewal_procedure_ref": renewal_procedure_ref,
    }
    missing = _missing_inputs(values)
    ready = not missing

    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": normalized_runtime,
        "status": "ready_for_production_pairing" if ready else "blocked",
        "ready_for_production_pairing": ready,
        "missing_inputs": missing,
        "certificate": {
            "label": _clean(tls_certificate_label),
            "certificate_ref": _non_secret_ref(tls_certificate_ref),
            "public_key_sha256": _clean(tls_public_key_sha256)
            if _valid_public_key_sha256(tls_public_key_sha256)
            else "",
            "expires_at": _clean(tls_expires_at) if _valid_future_timestamp(tls_expires_at) else "",
        },
        "trust": {
            "tls_trust_state": _clean(tls_trust_state) or "not_configured",
            "trust_store_ref": _non_secret_ref(trust_store_ref),
        },
        "renewal": {
            "renewal_procedure_ref": _non_secret_ref(renewal_procedure_ref),
        },
        "phone_api": {
            "base_path": "/mobile/v1",
            "private_host_api_exposed": False,
            "phone_api_unchanged": True,
        },
        "gates": {
            "requires_trusted_local_tls": True,
            "requires_non_secret_certificate_ref": True,
            "can_start_bridge": False,
            "can_bind_lan": False,
            "can_advertise_bonjour": False,
            "can_mint_mobile_token": False,
        },
        "safety": {
            "runtime_side_only": True,
            "does_not_generate_certificate": True,
            "does_not_install_certificate": True,
            "does_not_modify_keychain": True,
            "does_not_read_private_key": True,
            "does_not_start_bridge": True,
            "does_not_bind_lan": True,
            "does_not_advertise_bonjour": True,
            "does_not_mint_credentials": True,
            "does_not_fetch_refs": True,
            "private_key_path_redacted": True,
        },
    }
