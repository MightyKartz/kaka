from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
from typing import Mapping

from .cli import BridgeConfig
from .host_private_adapter_package import (
    default_private_adapter_command_name,
    private_adapter_environment_variable,
    private_adapter_well_known_paths,
)


SCHEMA_VERSION = "kaka.host_shell_pilot_preflight.v1"
SURFACE = "hermes_openclaw_host_shell_pilot_preflight"


def build_host_shell_pilot_preflight(
    config: BridgeConfig,
    *,
    private_adapter_command: str,
    applications_root: Path | str = "/Applications",
    home: Path | str | None = None,
    path_env: str | None = None,
) -> Mapping[str, object]:
    runtime = config.runtime
    default_command = default_private_adapter_command_name(runtime)
    env_name = private_adapter_environment_variable(runtime)
    applications = Path(applications_root)
    home_path = Path(home).expanduser() if home is not None else Path.home()
    path_value = os.environ.get("PATH", "") if path_env is None else path_env
    host_shell = _host_shell_status(runtime, applications, path_value)
    command_sources = _private_adapter_command_sources(
        config,
        private_adapter_command=private_adapter_command,
        env_name=env_name,
        default_command=default_command,
        home=home_path,
        path_env=path_value,
    )
    selected = _select_command(command_sources, config.repo_root)
    blocking_reasons: list[str] = []
    if host_shell["detected"] is not True:
        blocking_reasons.append("missing_host_shell")
    if selected["provided"] is not True:
        blocking_reasons.append("missing_private_adapter_command")
    elif selected["outside_kaka_repo"] is not True:
        blocking_reasons.append("private_adapter_command_inside_kaka_repo")
    elif selected["exists"] is not True:
        blocking_reasons.append("private_adapter_command_missing")
    elif selected["executable"] is not True:
        blocking_reasons.append("private_adapter_command_not_executable")
    ready_for_conformance = not blocking_reasons
    next_actions = _next_actions(
        host_shell=host_shell,
        selected=selected,
        path_command=command_sources["path_command"],
        blocking_reasons=blocking_reasons,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "surface": SURFACE,
        "runtime": runtime,
        "ok": ready_for_conformance,
        "status": "ready_for_conformance" if ready_for_conformance else "blocked",
        "runtime_side_only": True,
        "phone_api_path": "/mobile/v1",
        "phone_api_unchanged": True,
        "p3_4_complete": False,
        "host_shell": host_shell,
        "private_adapter_command": {
            "default_command_name": default_command,
            "selected": selected,
            "environment_variable": command_sources["environment_variable"],
            "manifest_entrypoint": command_sources["manifest_entrypoint"],
            "well_known_paths": command_sources["well_known_paths"],
            "path_command": command_sources["path_command"],
        },
        "handoff_command": [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-shell-pilot-handoff",
            "--runtime",
            runtime,
        ],
        "release_preflight": {
            "can_run_conformance": ready_for_conformance,
            "can_mark_p3_4_complete": False,
            "blocking_reasons": blocking_reasons,
        },
        "next_actions": next_actions,
        "safety": {
            "runtime_side_only": True,
            "phone_api_unchanged": True,
            "phone_settings_owner": False,
            "no_proprietary_binary_bundled_by_kaka": True,
            "does_not_invoke_private_adapter_command": True,
            "does_not_run_conformance": True,
            "does_not_fetch_audit_refs": True,
        },
    }


def _host_shell_status(
    runtime: str,
    applications_root: Path,
    path_env: str,
) -> Mapping[str, object]:
    app_names = {
        "hermes": ("Hermes.app", "Hermes Setup.app"),
        "openclaw": ("OpenClaw.app",),
    }[runtime]
    cli_name = {"hermes": "hermes", "openclaw": "openclaw"}[runtime]
    candidates = [
        {
            "path": str(applications_root / app_name),
            "exists": (applications_root / app_name).exists(),
        }
        for app_name in app_names
    ]
    cli_path = shutil.which(cli_name, path=path_env) or ""
    return {
        "detected": any(candidate["exists"] for candidate in candidates) or bool(cli_path),
        "candidates": candidates,
        "cli": {
            "command": cli_name,
            "found": bool(cli_path),
            "path": cli_path,
        },
    }


def _private_adapter_command_sources(
    config: BridgeConfig,
    *,
    private_adapter_command: str,
    env_name: str,
    default_command: str,
    home: Path,
    path_env: str,
) -> Mapping[str, object]:
    manifest = _manifest_command(config)
    well_known_paths = _well_known_path_statuses(config.runtime, default_command, home)
    path_command = shutil.which(default_command, path=path_env) or ""
    raw_env = os.environ.get(env_name, "").strip()
    return {
        "argument": _command_status(private_adapter_command, config.repo_root, "argument"),
        "environment_variable": {
            "name": env_name,
            "configured": bool(raw_env),
            **_command_status(raw_env, config.repo_root, "environment_variable", include_source=False),
        },
        "manifest_entrypoint": {
            "configured": bool(manifest["command"]),
            "manifest_path": manifest["manifest_path"],
            **_command_status(
                str(manifest["command"]),
                config.repo_root,
                "manifest_entrypoint",
                include_source=False,
            ),
        },
        "well_known_paths": well_known_paths,
        "path_command": {
            "command": default_command,
            "found": bool(path_command),
            "path": path_command,
            "informational_only": True,
        },
    }


def _select_command(
    sources: Mapping[str, object],
    repo_root: Path,
) -> Mapping[str, object]:
    argument = sources["argument"]
    if argument["provided"]:
        return argument
    environment = sources["environment_variable"]
    if environment["configured"]:
        return {
            "provided": True,
            "source": "environment_variable",
            "path": environment["path"],
            "exists": environment["exists"],
            "executable": environment["executable"],
            "outside_kaka_repo": environment["outside_kaka_repo"],
        }
    manifest = sources["manifest_entrypoint"]
    if manifest["configured"]:
        return {
            "provided": True,
            "source": "manifest_entrypoint",
            "path": manifest["path"],
            "exists": manifest["exists"],
            "executable": manifest["executable"],
            "outside_kaka_repo": manifest["outside_kaka_repo"],
        }
    for candidate in sources["well_known_paths"]:
        if candidate["exists"] and candidate["executable"]:
            return {
                "provided": True,
                "source": "well_known_path",
                "path": candidate["path"],
                "exists": True,
                "executable": True,
                "outside_kaka_repo": _outside_repo(repo_root, Path(candidate["path"])),
            }
    return {
        "provided": False,
        "source": "missing",
        "path": "",
        "exists": False,
        "executable": False,
        "outside_kaka_repo": False,
    }


def _manifest_command(config: BridgeConfig) -> Mapping[str, object]:
    manifest_path = _runtime_manifest_path(config)
    if manifest_path is None:
        return {"manifest_path": "", "command": ""}
    if not manifest_path.exists():
        return {"manifest_path": str(manifest_path), "command": ""}
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"manifest_path": str(manifest_path), "command": ""}
    host_private_adapter = manifest.get("host_private_adapter", {})
    if not isinstance(host_private_adapter, Mapping):
        return {"manifest_path": str(manifest_path), "command": ""}
    command = host_private_adapter.get("command", "")
    return {
        "manifest_path": str(manifest_path),
        "command": command if isinstance(command, str) else "",
    }


def _runtime_manifest_path(config: BridgeConfig) -> Path | None:
    repo_root = config.repo_root.resolve(strict=False)
    if config.runtime == "hermes":
        return repo_root / "runtime-kit" / "hermes-plugin" / "kaka-mobile-bridge.package.json"
    if config.runtime == "openclaw":
        return repo_root / "runtime-kit" / "openclaw-skill" / "kaka-mobile-bridge.sidecar.json"
    return None


def _well_known_path_statuses(
    runtime: str,
    default_command: str,
    home: Path,
) -> list[Mapping[str, object]]:
    statuses = []
    for candidate in private_adapter_well_known_paths(runtime, default_command):
        expanded = Path(str(candidate).replace("~", str(home), 1))
        statuses.append({
            "path": str(expanded),
            "exists": expanded.is_file(),
            "executable": expanded.is_file() and os.access(expanded, os.X_OK),
        })
    return statuses


def _command_status(
    command: str,
    repo_root: Path,
    source: str,
    *,
    include_source: bool = True,
) -> Mapping[str, object]:
    cleaned = command.strip()
    if not cleaned:
        status = {
            "provided": False,
            "path": "",
            "exists": False,
            "executable": False,
            "outside_kaka_repo": False,
        }
        if include_source:
            status["source"] = source
        return status
    path = _command_path(cleaned, repo_root)
    status = {
        "provided": True,
        "path": str(path),
        "exists": path.is_file(),
        "executable": path.is_file() and os.access(path, os.X_OK),
        "outside_kaka_repo": _outside_repo(repo_root, path),
    }
    if include_source:
        status["source"] = source
    return status


def _command_path(command: str, repo_root: Path) -> Path:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    executable = tokens[0] if tokens else command
    path = Path(executable).expanduser()
    if path.is_absolute():
        return path.resolve(strict=False)
    if _looks_like_path(executable):
        return (repo_root / path).resolve(strict=False)
    return path


def _outside_repo(repo_root: Path, path: Path) -> bool:
    if not path.is_absolute():
        return False
    repo = repo_root.resolve(strict=False)
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(repo)
        return False
    except ValueError:
        return True


def _looks_like_path(value: str) -> bool:
    return value.startswith(("/", "~", ".")) or "/" in value


def _next_actions(
    *,
    host_shell: Mapping[str, object],
    selected: Mapping[str, object],
    path_command: Mapping[str, object],
    blocking_reasons: list[str],
) -> list[str]:
    actions: list[str] = []
    if "missing_host_shell" in blocking_reasons:
        actions.append("install_or_open_host_shell")
    if "missing_private_adapter_command" in blocking_reasons:
        actions.append("provide_private_adapter_command")
    if path_command["found"] and selected["provided"] is not True:
        actions.append("path_command_not_used_for_pilot_discovery")
        actions.append("configure_env_manifest_or_well_known_path")
    if selected["provided"] is True and "private_adapter_command_inside_kaka_repo" in blocking_reasons:
        actions.append("move_private_adapter_command_outside_kaka_repo")
    if selected["provided"] is True and (
        "private_adapter_command_missing" in blocking_reasons
        or "private_adapter_command_not_executable" in blocking_reasons
    ):
        actions.append("fix_private_adapter_command_path_or_permissions")
    if not actions:
        actions.append("run_host_private_adapter_conformance")
    return actions
