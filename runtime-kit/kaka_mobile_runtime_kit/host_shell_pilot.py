from __future__ import annotations

import json
import os
import shlex
from pathlib import Path
from typing import Mapping

from .cli import BridgeConfig
from .host_private_adapter_package import (
    default_private_adapter_command_name,
    private_adapter_environment_variable,
    private_adapter_well_known_paths,
)
from .host_private_adapter_conformance import build_host_private_adapter_conformance_report


SCHEMA_VERSION = "kaka.host_shell_pilot_receipt.v1"
SURFACE = "hermes_openclaw_external_host_shell_pilot"
SYNTHETIC_FIXTURE_MARKERS = (
    "runtime-kit/tests/fixtures/fake_private_host_api.py",
    "fake_private_host_api.py",
)


def build_host_shell_pilot_receipt(
    config: BridgeConfig,
    *,
    private_adapter_command: str,
    distribution_source: str,
    distribution_channel: str,
    package_version: str,
    host_api_level: str,
    private_adapter_timeout_seconds: float = 10,
    native_channel_verified: bool = False,
    signature_verified: bool = False,
    update_feed_verified: bool = False,
    install_verified: bool = False,
    update_verified: bool = False,
    failure_recovery_verified: bool = False,
    release_notes_verified: bool = False,
    native_channel_ref: str = "",
    signature_subject: str = "",
    notarization_team_id: str = "",
    update_feed_ref: str = "",
    install_receipt_ref: str = "",
    update_receipt_ref: str = "",
    failure_recovery_receipt_ref: str = "",
    release_notes_ref: str = "",
    conformance_report: Mapping[str, object] | None = None,
) -> Mapping[str, object]:
    command, command_source = _discover_private_adapter_command(
        config,
        private_adapter_command,
    )
    command_info = _command_info(config.repo_root, command, source=command_source)
    synthetic_only = _is_synthetic_command(command)
    report = conformance_report
    if command and report is None:
        report = build_host_private_adapter_conformance_report(
            config,
            private_adapter_command=command,
            private_adapter_timeout_seconds=private_adapter_timeout_seconds,
        )
    conformance = _conformance_summary(report, synthetic_only=synthetic_only)
    distribution = {
        "source": distribution_source,
        "channel": distribution_channel,
        "package_version": package_version,
        "host_api_level": host_api_level,
        "native_channel_verified": bool(native_channel_verified),
        "signature_verified": bool(signature_verified),
        "update_feed_verified": bool(update_feed_verified),
    }
    distribution_evidence = _evidence_refs(
        native_channel_ref=native_channel_ref,
        signature_subject=signature_subject,
        notarization_team_id=notarization_team_id,
        update_feed_ref=update_feed_ref,
    )
    if distribution_evidence:
        distribution["evidence"] = distribution_evidence
    drills = {
        "install_verified": bool(install_verified),
        "update_verified": bool(update_verified),
        "failure_recovery_verified": bool(failure_recovery_verified),
        "release_notes_verified": bool(release_notes_verified),
    }
    drill_evidence = _evidence_refs(
        install_receipt_ref=install_receipt_ref,
        update_receipt_ref=update_receipt_ref,
        failure_recovery_receipt_ref=failure_recovery_receipt_ref,
        release_notes_ref=release_notes_ref,
    )
    if drill_evidence:
        drills["evidence"] = drill_evidence
    blocking_reasons = _blocking_reasons(
        command_info=command_info,
        distribution=distribution,
        conformance=conformance,
        drills=drills,
    )
    synthetic_conformance_passed = (
        synthetic_only
        and conformance["ran"] is True
        and conformance["ok"] is True
    )
    if synthetic_conformance_passed and "synthetic_conformance_only" not in blocking_reasons:
        blocking_reasons.append("synthetic_conformance_only")
    can_complete = not blocking_reasons
    status = "ready" if can_complete else "synthetic_only" if synthetic_conformance_passed else "not_ready"
    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": config.runtime,
        "ok": can_complete,
        "status": status,
        "runtime_side_only": True,
        "phone_api_path": "/mobile/v1",
        "phone_api_unchanged": True,
        "external_binary_required": True,
        "binary_owner": "host_shell",
        "distribution_owner": config.runtime,
        "private_adapter_command": command_info,
        "distribution": distribution,
        "conformance": conformance,
        "drills": drills,
        "release_readiness": {
            "can_start_external_pilot": can_complete,
            "can_mark_p3_4_complete": can_complete,
            "blocking_reasons": blocking_reasons,
        },
        "safety": {
            "runtime_side_only": True,
            "phone_api_unchanged": True,
            "phone_settings_owner": False,
            "no_proprietary_binary_bundled_by_kaka": True,
        },
    }


def _discover_private_adapter_command(
    config: BridgeConfig,
    private_adapter_command: str,
) -> tuple[str, str]:
    explicit_command = private_adapter_command.strip()
    if explicit_command:
        return explicit_command, "argument"

    environment_command = _environment_private_adapter_command(config.runtime)
    if environment_command:
        return environment_command, "environment_variable"

    manifest_command = _manifest_private_adapter_command(config)
    if manifest_command:
        return manifest_command, "manifest_entrypoint"

    well_known_command = _well_known_private_adapter_command(config.runtime)
    if well_known_command:
        return well_known_command, "well_known_path"

    return "", "missing"


def _evidence_refs(**values: str) -> Mapping[str, object]:
    return {
        key: value.strip()
        for key, value in values.items()
        if isinstance(value, str) and value.strip()
    }


def _environment_private_adapter_command(runtime: str) -> str:
    try:
        env_name = private_adapter_environment_variable(runtime)
    except ValueError:
        return ""
    raw_command = os.environ.get(env_name, "").strip()
    if not raw_command:
        return ""
    return _command_string_from_configured_value(raw_command)


def _manifest_private_adapter_command(config: BridgeConfig) -> str:
    manifest_path = _runtime_manifest_path(config)
    if manifest_path is None or not manifest_path.exists():
        return ""
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return ""
    host_private_adapter = manifest.get("host_private_adapter", {})
    if not isinstance(host_private_adapter, Mapping):
        return ""
    raw_command = host_private_adapter.get("command", "")
    if not isinstance(raw_command, str) or not raw_command.strip():
        return ""
    return _command_string_from_configured_value(raw_command.strip())


def _runtime_manifest_path(config: BridgeConfig) -> Path | None:
    repo_root = config.repo_root.resolve(strict=False)
    if config.runtime == "hermes":
        return repo_root / "runtime-kit" / "hermes-plugin" / "kaka-mobile-bridge.package.json"
    if config.runtime == "openclaw":
        return repo_root / "runtime-kit" / "openclaw-skill" / "kaka-mobile-bridge.sidecar.json"
    return None


def _well_known_private_adapter_command(runtime: str) -> str:
    try:
        command_name = default_private_adapter_command_name(runtime)
        candidates = private_adapter_well_known_paths(runtime, command_name)
    except ValueError:
        return ""
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return shlex.quote(str(path))
    return ""


def _command_string_from_configured_value(value: str) -> str:
    path = Path(value).expanduser()
    if path.is_file() and os.access(path, os.X_OK):
        return shlex.quote(str(path))
    return value


def _command_info(repo_root: Path, command: str, *, source: str) -> Mapping[str, object]:
    if not command:
        return {
            "provided": False,
            "path": "",
            "source": source,
            "outside_kaka_repo": False,
        }

    tokens = _command_tokens(command)
    executable = tokens[0] if tokens else command
    command_path = _resolve_path(repo_root, executable)
    return {
        "provided": True,
        "path": str(command_path),
        "source": source,
        "outside_kaka_repo": _command_is_external(repo_root, tokens),
    }


def _command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _command_is_external(repo_root: Path, tokens: list[str]) -> bool:
    repo = repo_root.resolve(strict=False)
    path_tokens = [_resolve_path(repo, token) for token in tokens if _looks_like_path(token)]
    if not path_tokens:
        return False
    return all(path.is_absolute() and not _is_relative_to(path, repo) for path in path_tokens)


def _resolve_path(repo_root: Path, token: str) -> Path:
    path = Path(token).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve(strict=False)


def _looks_like_path(token: str) -> bool:
    return (
        token.startswith("/")
        or token.startswith("~/")
        or token.startswith("./")
        or token.startswith("../")
        or "/" in token
    )


def _conformance_summary(
    report: Mapping[str, object] | None,
    *,
    synthetic_only: bool,
) -> Mapping[str, object]:
    if report is None:
        return {
            "required": True,
            "ran": False,
            "ok": False,
            "synthetic_only": synthetic_only,
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
            },
        }
    summary = report.get("summary", {})
    return {
        "required": True,
        "ran": True,
        "ok": bool(report.get("ok", False)),
        "synthetic_only": synthetic_only,
        "summary": {
            "total": _summary_int(summary, "total"),
            "passed": _summary_int(summary, "passed"),
            "failed": _summary_int(summary, "failed"),
        },
    }


def _summary_int(summary: object, key: str) -> int:
    if not isinstance(summary, Mapping):
        return 0
    try:
        return int(summary.get(key, 0))
    except (TypeError, ValueError):
        return 0


def _blocking_reasons(
    *,
    command_info: Mapping[str, object],
    distribution: Mapping[str, object],
    conformance: Mapping[str, object],
    drills: Mapping[str, object],
) -> list[str]:
    reasons: list[str] = []
    if command_info["provided"] is not True:
        reasons.append("missing_private_adapter_command")
    elif command_info["outside_kaka_repo"] is not True:
        reasons.append("private_adapter_command_not_external")
    if distribution["native_channel_verified"] is not True:
        reasons.append("native_distribution_not_verified")
    if distribution["signature_verified"] is not True:
        reasons.append("signature_not_verified")
    if distribution["update_feed_verified"] is not True:
        reasons.append("update_feed_not_verified")
    if command_info["provided"] is True and conformance["ran"] is not True:
        reasons.append("conformance_not_run")
    if command_info["provided"] is True and conformance["ok"] is not True:
        reasons.append("conformance_not_passed")
    if drills["install_verified"] is not True:
        reasons.append("install_drill_not_verified")
    if drills["update_verified"] is not True:
        reasons.append("update_drill_not_verified")
    if drills["failure_recovery_verified"] is not True:
        reasons.append("failure_recovery_not_verified")
    if drills["release_notes_verified"] is not True:
        reasons.append("release_notes_not_verified")
    return reasons


def _is_synthetic_command(command: str) -> bool:
    return any(marker in command for marker in SYNTHETIC_FIXTURE_MARKERS)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
