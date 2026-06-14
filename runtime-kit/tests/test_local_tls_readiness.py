import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.cli import main
from kaka_mobile_runtime_kit.local_tls_readiness import build_local_tls_readiness


READY_INPUTS = {
    "tls_certificate_label": "Pocket Agent Local Runtime",
    "tls_certificate_ref": "keychain://login/kaka-local-runtime",
    "tls_public_key_sha256": "a" * 64,
    "tls_expires_at": "2036-12-31T23:59:59Z",
    "trust_store_ref": "macos-keychain://login",
    "renewal_procedure_ref": "docs/kaka-local-tls-renewal.md",
}


def test_local_tls_readiness_blocks_missing_tls_materials() -> None:
    report = build_local_tls_readiness(runtime="hermes")

    assert report["schema_version"] == "kaka.local_tls_readiness.v1"
    assert report["surface"] == "hermes_openclaw_local_tls_readiness"
    assert report["runtime"] == "hermes"
    assert report["status"] == "blocked"
    assert report["ready_for_production_pairing"] is False
    assert [item["id"] for item in report["missing_inputs"]] == [
        "tls_trust_state",
        "tls_certificate_label",
        "tls_certificate_ref",
        "tls_public_key_sha256",
        "tls_expires_at",
        "trust_store_ref",
        "renewal_procedure_ref",
    ]
    assert report["phone_api"]["base_path"] == "/mobile/v1"
    assert report["phone_api"]["private_host_api_exposed"] is False
    assert report["safety"]["does_not_read_private_key"] is True
    assert report["safety"]["does_not_install_certificate"] is True


def test_local_tls_readiness_accepts_configured_openclaw_tls_materials() -> None:
    report = build_local_tls_readiness(
        runtime="openclaw",
        tls_trust_state="configured",
        **READY_INPUTS,
    )

    assert report["status"] == "ready_for_production_pairing"
    assert report["ready_for_production_pairing"] is True
    assert report["missing_inputs"] == []
    assert report["certificate"]["label"] == "Pocket Agent Local Runtime"
    assert report["certificate"]["public_key_sha256"] == "a" * 64
    assert report["certificate"]["expires_at"] == "2036-12-31T23:59:59Z"
    assert report["trust"]["tls_trust_state"] == "configured"
    assert report["gates"]["can_start_bridge"] is False
    assert report["gates"]["can_mint_mobile_token"] is False


def test_local_tls_readiness_rejects_unknown_runtime() -> None:
    with pytest.raises(ValueError, match="Unsupported local TLS runtime"):
        build_local_tls_readiness(runtime="sidecar")


def test_local_tls_readiness_validates_against_schema() -> None:
    schema = json.loads(
        Path("runtime-kit/packaging/local-tls-readiness.schema.json").read_text()
    )

    Draft202012Validator(schema).validate(build_local_tls_readiness(runtime="hermes"))
    Draft202012Validator(schema).validate(
        build_local_tls_readiness(
            runtime="openclaw",
            tls_trust_state="configured",
            **READY_INPUTS,
        )
    )


def test_local_tls_readiness_schema_rejects_false_ready_or_secret_leak() -> None:
    schema = json.loads(
        Path("runtime-kit/packaging/local-tls-readiness.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)
    ready = json.loads(json.dumps(
        build_local_tls_readiness(
            runtime="hermes",
            tls_trust_state="configured",
            **READY_INPUTS,
        )
    ))

    ready_without_fingerprint = json.loads(json.dumps(ready))
    ready_without_fingerprint["certificate"]["public_key_sha256"] = ""
    assert not validator.is_valid(ready_without_fingerprint)

    blocked_but_ready = json.loads(json.dumps(build_local_tls_readiness(runtime="hermes")))
    blocked_but_ready["ready_for_production_pairing"] = True
    assert not validator.is_valid(blocked_but_ready)

    leaked_private_key = json.loads(json.dumps(ready))
    leaked_private_key["certificate"]["tls_private_key_path"] = "/Users/kartz/.kaka/private/key.pem"
    assert not validator.is_valid(leaked_private_key)

    mutating_report = json.loads(json.dumps(ready))
    mutating_report["safety"]["does_not_install_certificate"] = False
    assert not validator.is_valid(mutating_report)

    bridge_start_drift = json.loads(json.dumps(ready))
    bridge_start_drift["gates"]["can_start_bridge"] = True
    assert not validator.is_valid(bridge_start_drift)

    phone_api_drift = json.loads(json.dumps(ready))
    phone_api_drift["phone_api"]["private_host_api_exposed"] = True
    assert not validator.is_valid(phone_api_drift)


def test_local_tls_readiness_blocks_secret_like_refs_and_invalid_metadata() -> None:
    secret_ref = build_local_tls_readiness(
        runtime="hermes",
        tls_trust_state="configured",
        tls_certificate_label="Pocket Agent Local Runtime",
        tls_certificate_ref="/Users/kartz/.kaka/private/key.pem",
        tls_public_key_sha256="a" * 64,
        tls_expires_at="2036-12-31T23:59:59Z",
        trust_store_ref="macos-keychain://login",
        renewal_procedure_ref="Bearer secret-token",
    )
    invalid_fingerprint = build_local_tls_readiness(
        runtime="hermes",
        tls_trust_state="configured",
        **{**READY_INPUTS, "tls_public_key_sha256": "not-a-fingerprint"},
    )
    expired = build_local_tls_readiness(
        runtime="hermes",
        tls_trust_state="configured",
        **{**READY_INPUTS, "tls_expires_at": "2020-01-01T00:00:00Z"},
    )

    assert secret_ref["status"] == "blocked"
    assert [item["id"] for item in secret_ref["missing_inputs"]] == [
        "tls_certificate_ref",
        "renewal_procedure_ref",
    ]
    assert secret_ref["certificate"]["certificate_ref"] == ""
    assert secret_ref["renewal"]["renewal_procedure_ref"] == ""

    assert invalid_fingerprint["status"] == "blocked"
    assert [item["id"] for item in invalid_fingerprint["missing_inputs"]] == [
        "tls_public_key_sha256"
    ]

    assert expired["status"] == "blocked"
    assert [item["id"] for item in expired["missing_inputs"]] == ["tls_expires_at"]


def test_local_tls_readiness_cli_outputs_ready_report_without_private_key(capsys) -> None:
    exit_code = main(
        [
            "local-tls-readiness",
            "--runtime",
            "hermes",
            "--tls-trust-state",
            "configured",
            "--tls-certificate-label",
            "Pocket Agent Local Runtime",
            "--tls-certificate-ref",
            "keychain://login/kaka-local-runtime",
            "--tls-public-key-sha256",
            "b" * 64,
            "--tls-expires-at",
            "2036-12-31T23:59:59Z",
            "--trust-store-ref",
            "macos-keychain://login",
            "--renewal-procedure-ref",
            "docs/kaka-local-tls-renewal.md",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    rendered = json.dumps(report)
    assert exit_code == 0
    assert report["status"] == "ready_for_production_pairing"
    assert report["certificate"]["public_key_sha256"] == "b" * 64
    assert "tls_private_key_path" not in rendered
    assert "/Users/" not in rendered
