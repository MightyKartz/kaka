from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import re
import shlex
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence

from agent_pocket_mock_bridge.app import create_app
from agent_pocket_mock_bridge.fake_openai import create_fake_openai_server
from agent_pocket_mock_bridge.photo_providers import (
    build_openai_base_url_report,
    build_photo_provider,
    build_provider_preflight_report,
)
from agent_pocket_mock_bridge.server import BonjourAdvertisement, build_app_for_provider, create_http_server


DEFAULT_TOKEN = "dev-mobile-token"
DEFAULT_BUNDLE_ID = "com.kaka.AgentPocket"
DEFAULT_SIMULATOR_LIBRARY_FIXTURE = "/tmp/agent-pocket-simulator-library-fixture.png"
DEFAULT_SIMULATOR_PICKER_UI_SCREENSHOT = "/tmp/agent-pocket-simulator-picker-ui-smoke.png"
DEFAULT_SIMULATOR_DISCOVERY_REFRESH_RECEIPT = "docs/qa-receipts/simulator-discovery-refresh-latest.json"
DEFAULT_SIMULATOR_DISCOVERY_REFRESH_SCREENSHOT = "/tmp/agent-pocket-simulator-discovery-refresh.png"
DEFAULT_SIMULATOR_UI_TEST_PREFLIGHT_RECEIPT = "docs/qa-receipts/simulator-ui-test-preflight-latest.json"
DEFAULT_SIMULATOR_SUITE_RECEIPT = "docs/qa-receipts/simulator-suite-latest.json"
DEFAULT_SIMULATOR_CAPTURE_READY_RECEIPT = "docs/qa-receipts/simulator-capture-ready-latest.json"
DEFAULT_SIMULATOR_CAPTURE_COMPLETED_RECEIPT = "docs/qa-receipts/simulator-capture-completed-latest.json"
DEFAULT_SIMULATOR_CAPTURE_COMPLETED_SCREENSHOT = "/tmp/agent-pocket-simulator-capture-completed.png"
DEFAULT_SIMULATOR_RESULT_GALLERY_RECEIPT = "docs/qa-receipts/simulator-result-gallery-latest.json"
DEFAULT_SIMULATOR_RESULT_GALLERY_SCREENSHOT = "/tmp/agent-pocket-simulator-result-gallery.png"
DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_RECEIPT = "docs/qa-receipts/simulator-result-gallery-downloaded-latest.json"
DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_SCREENSHOT = "/tmp/agent-pocket-simulator-result-gallery-downloaded.png"
DEFAULT_SIMULATOR_SHARE_SHEET_RECEIPT = "docs/qa-receipts/share-sheet-flow-latest.json"
DEFAULT_SIMULATOR_SHARE_SHEET_SCREENSHOT = "/tmp/agent-pocket-simulator-share-sheet.png"
DEFAULT_SIMULATOR_ONLY_RESUME_RECEIPT = "docs/qa-receipts/simulator-only-resume-latest.json"
DEFAULT_REAL_PROVIDER_SMOKE_IMAGE = "/tmp/kaka-smoke-real-provider.png"
DEFAULT_GATE_F_PREFLIGHT_RECEIPT = "docs/qa-receipts/gate-f-preflight-latest.json"
DEFAULT_GATE_F_HANDOFF_RECEIPT = "docs/qa-receipts/gate-f-handoff-latest.json"
DEFAULT_PHYSICAL_DEVICE_PREFLIGHT_RECEIPT = "docs/qa-receipts/physical-device-preflight-latest.json"
DEFAULT_OPENAI_PROVIDER_PREFLIGHT_RECEIPT = "docs/qa-receipts/provider-openai-preflight-latest.json"
DEFAULT_PROVIDER_ENV_SOURCES_RECEIPT = "docs/qa-receipts/provider-env-sources-latest.json"
DEFAULT_PROVIDER_ENV_SOURCES_ALL_PROFILES_RECEIPT = "docs/qa-receipts/provider-env-sources-all-profiles-latest.json"
DEFAULT_HERMES_OPENAI_AUTH_IMPORT_RECEIPT = "docs/qa-receipts/hermes-openai-auth-import-latest.json"
DEFAULT_IPHONE_CREDENTIAL_BOUNDARY_RECEIPT = "docs/qa-receipts/iphone-credential-boundary-latest.json"
HERMES_PROVIDER_ENV_FORCE_PREFIX = "_HERMES_FORCE_"
OPENAI_PROVIDER_ENV_KEYS = ("OPENAI_API_KEY", "OPENAI_BASE_URL")
PHOTO_PROVIDER_CHOICES = ["fixture", "script", "recipe_local", "openai"]


@dataclass(frozen=True)
class EvaluationResult:
    ok: bool
    missing: list[str]


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def _parse_env_file(path: str) -> dict[str, str]:
    if not path:
        return {}
    values: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ["'", '"']:
                value = value[1:-1]
            values[key] = value
    return values


def _env_with_file(base_env: Optional[Mapping[str, str]] = None, env_file: str = "") -> dict[str, str]:
    values = _provider_visible_env(os.environ if base_env is None else base_env)
    values.update(_provider_visible_env(_parse_env_file(env_file)))
    return values


def _provider_visible_env(values: Mapping[str, str]) -> dict[str, str]:
    normalized = dict(values)
    for key in OPENAI_PROVIDER_ENV_KEYS:
        forced_key = f"{HERMES_PROVIDER_ENV_FORCE_PREFIX}{key}"
        forced_value = str(normalized.get(forced_key, "")).strip()
        if forced_value:
            normalized[key] = normalized[forced_key]
        normalized.pop(forced_key, None)
    return normalized


def _provider_force_env_state(values: Mapping[str, str], key: str = "OPENAI_API_KEY") -> str:
    forced_key = f"{HERMES_PROVIDER_ENV_FORCE_PREFIX}{key}"
    return "set" if str(values.get(forced_key, "")).strip() else "missing"


def _default_hermes_home() -> str:
    return os.path.join(os.path.expanduser("~"), ".hermes")


def _hermes_profile_root(hermes_home: str = "", hermes_profile: str = "") -> str:
    home = os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home()))
    profile = hermes_profile.strip()
    if profile:
        return os.path.join(home, "profiles", profile)
    return home


def _hermes_shared_auth_file(hermes_home: str = "") -> str:
    home = os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home()))
    return os.path.join(home, "shared-auth", "auth.json")


def _summarize_hermes_auth_file(auth_file: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": auth_file,
        "exists": False,
        "openai": {
            "credential_pool": "missing",
            "compatible_with_photo_provider": False,
        },
        "openai_codex": {
            "credential_pool": "missing",
            "compatible_with_photo_provider": False,
        },
    }
    if not auth_file or not os.path.exists(auth_file):
        return base

    try:
        with open(auth_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "error": f"readable Hermes auth JSON: {error}",
        }

    pool = data.get("credential_pool", {})
    if not isinstance(pool, Mapping):
        pool = {}

    def summarize_pool(provider: str, compatible: bool) -> dict[str, Any]:
        entries = pool.get(provider, [])
        if not isinstance(entries, list):
            entries = []
        labels: list[str] = []
        auth_types: list[str] = []
        has_credential = False
        for raw_entry in entries:
            if not isinstance(raw_entry, Mapping):
                continue
            label = str(raw_entry.get("label", "")).strip()
            if label:
                labels.append(label)
            auth_type = str(raw_entry.get("auth_type", "")).strip()
            if auth_type:
                auth_types.append(auth_type)
            if str(raw_entry.get("access_token", "")).strip():
                has_credential = True
        return {
            "credential_pool": "set" if entries and has_credential else "missing",
            "entries": len(entries),
            "labels": labels,
            "auth_types": sorted(set(auth_types)),
            "compatible_with_photo_provider": compatible,
        }

    return {
        **base,
        "exists": True,
        "openai": summarize_pool("openai", compatible=True),
        "openai_codex": {
            **summarize_pool("openai-codex", compatible=False),
            "note": "OpenAI Codex OAuth is not an OpenAI Images API key.",
        },
    }


def _hermes_openai_auth_env(auth_file: str) -> dict[str, str]:
    if not auth_file or not os.path.exists(auth_file):
        return {}
    try:
        with open(auth_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, Mapping):
        return {}
    pool = data.get("credential_pool", {})
    if not isinstance(pool, Mapping):
        return {}
    entries = pool.get("openai", [])
    if not isinstance(entries, list):
        return {}
    for raw_entry in entries:
        if not isinstance(raw_entry, Mapping):
            continue
        auth_type = str(raw_entry.get("auth_type", "")).strip()
        access_token = str(raw_entry.get("access_token", "")).strip()
        if auth_type != "api_key" or not access_token:
            continue
        values = {"OPENAI_API_KEY": access_token}
        base_url = str(raw_entry.get("base_url", "")).strip()
        if base_url:
            values["OPENAI_BASE_URL"] = base_url
        return values
    return {}


def _build_hermes_provider_context(
    hermes_home: str = "",
    hermes_profile: str = "",
) -> tuple[dict[str, Any], dict[str, str], str]:
    if not hermes_home and not hermes_profile:
        return {}, {}, ""

    home = os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home()))
    home_env_file = os.path.join(home, ".env")
    home_env_exists = os.path.exists(home_env_file)
    env_values = _provider_visible_env(_parse_env_file(home_env_file)) if home_env_exists else {}
    profile_root = _hermes_profile_root(hermes_home=hermes_home, hermes_profile=hermes_profile)
    env_file = os.path.join(profile_root, ".env")
    auth_file = os.path.join(profile_root, "auth.json")
    shared_auth_file = _hermes_shared_auth_file(hermes_home)
    env_exists = os.path.exists(env_file)
    if env_exists and env_file != home_env_file:
        env_values.update(_provider_visible_env(_parse_env_file(env_file)))
    auth = _summarize_hermes_auth_file(auth_file)
    shared_auth = _summarize_hermes_auth_file(shared_auth_file)
    auth_env = _hermes_openai_auth_env(auth_file)
    shared_auth_env = _hermes_openai_auth_env(shared_auth_file)
    auth_source_used = ""

    def apply_auth_env(source: str, source_env: Mapping[str, str]) -> bool:
        nonlocal auth_source_used
        used = False
        if source_env.get("OPENAI_API_KEY") and not env_values.get("OPENAI_API_KEY"):
            env_values["OPENAI_API_KEY"] = source_env["OPENAI_API_KEY"]
            used = True
        if source_env.get("OPENAI_BASE_URL") and not env_values.get("OPENAI_BASE_URL"):
            env_values["OPENAI_BASE_URL"] = source_env["OPENAI_BASE_URL"]
            used = True
        if used and not auth_source_used:
            auth_source_used = source
        return used

    profile_auth_used = apply_auth_env("profile_auth", auth_env)
    shared_auth_used = apply_auth_env("shared_auth", shared_auth_env)
    openai_key_state = "set" if env_values.get("OPENAI_API_KEY") else "missing"
    missing: list[str] = []
    if openai_key_state == "missing":
        missing.append("Hermes server-side OPENAI_API_KEY")
    openai_auth_set = (
        auth.get("openai", {}).get("credential_pool") == "set"
        or shared_auth.get("openai", {}).get("credential_pool") == "set"
    )
    if (
        (
            auth.get("openai_codex", {}).get("credential_pool") == "set"
            or shared_auth.get("openai_codex", {}).get("credential_pool") == "set"
        )
        and openai_key_state == "missing"
        and not openai_auth_set
    ):
        missing.append("OpenAI Codex OAuth is not an Images API key")

    context = {
        "profile": hermes_profile.strip() or "default",
        "home": home,
        "profile_root": profile_root,
        "home_env_file": {
            "path": home_env_file,
            "exists": home_env_exists,
            "OPENAI_API_KEY": _env_key_state(env_values if home_env_exists else {}, "OPENAI_API_KEY")
            if not env_exists or env_file == home_env_file
            else _env_file_key_state(home_env_file).get("OPENAI_API_KEY", "missing"),
            "OPENAI_BASE_URL": _env_file_key_state(home_env_file, "OPENAI_BASE_URL").get(
                "OPENAI_BASE_URL",
                "missing",
            ),
        },
        "env_file": {
            "path": env_file,
            "exists": env_exists,
            "OPENAI_API_KEY": _env_file_key_state(env_file).get("OPENAI_API_KEY", "missing"),
            "OPENAI_BASE_URL": _env_file_key_state(env_file, "OPENAI_BASE_URL").get(
                "OPENAI_BASE_URL",
                "missing",
            ),
        },
        "effective_env": {
            "OPENAI_API_KEY": openai_key_state,
            "OPENAI_BASE_URL": _env_key_state(env_values, "OPENAI_BASE_URL"),
        },
        "auth_env": {
            "source": "hermes_auth_openai_api_key",
            "used": profile_auth_used,
            "OPENAI_API_KEY": _env_key_state(auth_env, "OPENAI_API_KEY"),
            "OPENAI_BASE_URL": _env_key_state(auth_env, "OPENAI_BASE_URL"),
        },
        "shared_auth_env": {
            "source": "hermes_shared_auth_openai_api_key",
            "used": shared_auth_used,
            "OPENAI_API_KEY": _env_key_state(shared_auth_env, "OPENAI_API_KEY"),
            "OPENAI_BASE_URL": _env_key_state(shared_auth_env, "OPENAI_BASE_URL"),
        },
        "config": {
            "OPENAI_BASE_URL": build_openai_base_url_report(env_values),
        },
        "auth_file": {
            "path": auth_file,
            "exists": bool(auth.get("exists")),
        },
        "auth": auth,
        "shared_auth_file": {
            "path": shared_auth_file,
            "exists": bool(shared_auth.get("exists")),
        },
        "shared_auth": shared_auth,
        "missing": missing,
    }
    if env_exists:
        effective_env_file = env_file
    elif home_env_exists:
        effective_env_file = home_env_file
    elif auth_source_used == "profile_auth":
        effective_env_file = auth_file
    elif auth_source_used == "shared_auth":
        effective_env_file = shared_auth_file
    else:
        effective_env_file = ""
    return context, env_values, effective_env_file


def _env_key_state(values: Mapping[str, str], key: str = "OPENAI_API_KEY") -> str:
    return "set" if str(values.get(key, "")).strip() else "missing"


def _env_file_key_state(path: str, key: str = "OPENAI_API_KEY") -> dict[str, Any]:
    expanded = os.path.abspath(os.path.expanduser(path)) if path else ""
    if not expanded:
        return {"path": "", "exists": False, key: "missing"}
    exists = os.path.exists(expanded)
    values = _provider_visible_env(_parse_env_file(expanded)) if exists else {}
    return {
        "path": expanded,
        "exists": exists,
        key: _env_key_state(values, key),
    }


def _shell_startup_candidate_files(home: str = "") -> list[str]:
    home_dir = os.path.abspath(os.path.expanduser(home or "~"))
    candidates = [
        os.path.join(home_dir, ".zshenv"),
        os.path.join(home_dir, ".zprofile"),
        os.path.join(home_dir, ".zshrc"),
        os.path.join(home_dir, ".profile"),
        os.path.join(home_dir, ".bash_profile"),
        os.path.join(home_dir, ".bashrc"),
    ]
    environment_dir = os.path.join(home_dir, ".config", "environment.d")
    if os.path.isdir(environment_dir):
        for name in sorted(os.listdir(environment_dir)):
            if name.endswith(".conf"):
                candidates.append(os.path.join(environment_dir, name))
    return list(dict.fromkeys(candidates))


def _shell_startup_key_sources(home: str = "", key: str = "OPENAI_API_KEY") -> dict[str, Any]:
    home_dir = os.path.abspath(os.path.expanduser(home or "~"))
    files: list[dict[str, Any]] = []
    for path in _shell_startup_candidate_files(home_dir):
        expanded = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(expanded):
            continue
        try:
            summary = _env_file_key_state(expanded, key=key)
        except OSError as error:
            files.append({
                "source": "shell_startup_file",
                "path": expanded,
                "exists": True,
                key: "unknown",
                "error": str(error),
                "counts_for_provider_readiness": False,
            })
            continue
        files.append({
            "source": "shell_startup_file",
            "path": str(summary.get("path", expanded)),
            "exists": bool(summary.get("exists")),
            key: str(summary.get(key, "missing")),
            "counts_for_provider_readiness": False,
        })
    set_files = [
        {
            "source": "shell_startup_file",
            "path": str(source.get("path", "")),
        }
        for source in files
        if source.get(key) == "set"
    ]
    if set_files:
        state = "declared_not_active"
    elif files:
        state = "checked_missing"
    else:
        state = "no_startup_files"
    return {
        "home": home_dir,
        "key": key,
        "state": state,
        "counts_for_provider_readiness": False,
        "files": files,
        "set_files": set_files,
    }


def _list_hermes_profile_env_sources(
    hermes_home: str = "",
    selected_profile: str = "",
    key: str = "OPENAI_API_KEY",
) -> list[dict[str, Any]]:
    home = os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home()))
    profiles_root = os.path.join(home, "profiles")
    if not os.path.isdir(profiles_root):
        return []
    selected = selected_profile.strip()
    profiles: list[dict[str, Any]] = []
    for name in sorted(os.listdir(profiles_root)):
        profile_root = os.path.join(profiles_root, name)
        if not os.path.isdir(profile_root):
            continue
        env_summary = _env_file_key_state(os.path.join(profile_root, ".env"), key=key)
        profiles.append({
            "profile": name,
            "selected": bool(selected and name == selected),
            "env_file": env_summary,
            key: env_summary.get(key, "missing"),
        })
    return profiles


def _auth_env_source(path: str, source: str, profile: str = "", selected: bool = False) -> dict[str, Any]:
    expanded = os.path.abspath(os.path.expanduser(path)) if path else ""
    auth_env = _hermes_openai_auth_env(expanded)
    return {
        "source": source,
        "profile": profile,
        "selected": selected,
        "path": expanded,
        "exists": bool(expanded and os.path.exists(expanded)),
        "OPENAI_API_KEY": _env_key_state(auth_env, "OPENAI_API_KEY"),
        "OPENAI_BASE_URL": _env_key_state(auth_env, "OPENAI_BASE_URL"),
    }


def _list_hermes_profile_auth_sources(
    hermes_home: str = "",
    selected_profile: str = "",
) -> list[dict[str, Any]]:
    home = os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home()))
    profiles_root = os.path.join(home, "profiles")
    if not os.path.isdir(profiles_root):
        return []
    selected = selected_profile.strip()
    profiles: list[dict[str, Any]] = []
    for name in sorted(os.listdir(profiles_root)):
        profile_root = os.path.join(profiles_root, name)
        if not os.path.isdir(profile_root):
            continue
        profiles.append(_auth_env_source(
            os.path.join(profile_root, "auth.json"),
            source="hermes_profile_auth",
            profile=name,
            selected=bool(selected and name == selected),
        ))
    return profiles


def _counts_for_selected_profile(source: Mapping[str, Any], selected_profile: str) -> bool:
    if not selected_profile.strip():
        return True
    source_name = str(source.get("source", ""))
    if source_name in {"hermes_profile", "hermes_profile_auth", "hermes_gateway_process", "hermes_cli_auth"}:
        return bool(source.get("selected"))
    return True


def _parse_hermes_gateway_processes(
    ps_output: str,
    selected_profile: str = "",
    key: str = "OPENAI_API_KEY",
) -> list[dict[str, Any]]:
    selected = selected_profile.strip()
    processes: list[dict[str, Any]] = []
    for raw_line in ps_output.splitlines():
        match = re.match(r"\s*(\d+)\s+(.*)", raw_line)
        if not match:
            continue
        pid, args = match.groups()
        if "hermes_cli.main" not in args or " gateway " not in f" {args} ":
            continue
        if " run " not in f" {args} ":
            continue
        profile_match = re.search(r"(?:^|\s)--profile\s+([^\s]+)", args)
        profile = profile_match.group(1) if profile_match else ""
        if selected and profile != selected:
            continue
        key_match = re.search(rf"(?:^|\s){re.escape(key)}=([^\s]+)", args)
        forced_key = f"{HERMES_PROVIDER_ENV_FORCE_PREFIX}{key}"
        forced_key_match = re.search(rf"(?:^|\s){re.escape(forced_key)}=([^\s]+)", args)
        processes.append({
            "source": "hermes_gateway_process",
            "pid": pid,
            "profile": profile,
            "selected": bool(selected and profile == selected),
            key: "set"
            if (
                (key_match and key_match.group(1).strip())
                or (forced_key_match and forced_key_match.group(1).strip())
            )
            else "missing",
            "force_env": "set"
            if forced_key_match and forced_key_match.group(1).strip()
            else "missing",
        })
    return processes


def _list_hermes_gateway_process_env_sources(
    selected_profile: str = "",
    key: str = "OPENAI_API_KEY",
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    runner = command_runner or _run_command
    result = runner(["ps", "eww", "-axo", "pid=,args="])
    if result.returncode != 0:
        return [], {
            "ok": False,
            "error": _clean_error(result),
        }
    processes = _parse_hermes_gateway_processes(
        result.stdout,
        selected_profile=selected_profile,
        key=key,
    )
    return processes, {
        "ok": True,
        "error": "",
    }


def _is_current_hermes_process(args: str) -> bool:
    lower = args.lower()
    return (
        "hermes_cli.main" in args
        or "/.hermes/" in lower
        or " ~/.hermes/" in lower
        or " hermes " in f" {lower} "
    )


def _parse_current_hermes_processes(
    ps_output: str,
    selected_profile: str = "",
) -> list[dict[str, Any]]:
    selected = selected_profile.strip()
    processes: list[dict[str, Any]] = []
    for raw_line in ps_output.splitlines():
        match = re.match(r"\s*(\d+)\s+(.*)", raw_line)
        if not match:
            continue
        pid, args = match.groups()
        if not _is_current_hermes_process(args):
            continue
        profile_match = re.search(r"(?:^|\s)--profile\s+([^\s]+)", args)
        profile = profile_match.group(1) if profile_match else ""
        gateway_run = " gateway " in f" {args} " and " run " in f" {args} "
        process_kind = "hermes_cli" if "hermes_cli.main" in args else "hermes_runtime"
        key_match = re.search(r"(?:^|\s)OPENAI_API_KEY=\S+", args)
        forced_key_match = re.search(
            rf"(?:^|\s){re.escape(HERMES_PROVIDER_ENV_FORCE_PREFIX)}OPENAI_API_KEY=\S+",
            args,
        )
        base_url_match = re.search(r"(?:^|\s)OPENAI_BASE_URL=\S+", args)
        forced_base_url_match = re.search(
            rf"(?:^|\s){re.escape(HERMES_PROVIDER_ENV_FORCE_PREFIX)}OPENAI_BASE_URL=\S+",
            args,
        )
        processes.append({
            "source": "hermes_process",
            "pid": pid,
            "kind": process_kind,
            "profile": profile,
            "selected": bool(selected and profile == selected),
            "gateway_run": gateway_run,
            "OPENAI_API_KEY": "set" if key_match or forced_key_match else "missing",
            "OPENAI_BASE_URL": "set" if base_url_match or forced_base_url_match else "missing",
            "force_env": "set" if forced_key_match else "missing",
        })
    return processes


def _list_current_hermes_process_env_diagnostics(
    selected_profile: str = "",
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    runner = command_runner or _run_command
    result = runner(["ps", "eww", "-axo", "pid=,args="])
    if result.returncode != 0:
        return [], {
            "ok": False,
            "error": _clean_error(result),
        }
    return _parse_current_hermes_processes(
        result.stdout,
        selected_profile=selected_profile,
    ), {
        "ok": True,
        "error": "",
    }


def _hermes_provider_reference_files(
    hermes_home: str = "",
    selected_profile: str = "",
) -> list[dict[str, Any]]:
    home = os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home()))
    candidates: list[tuple[str, str, str]] = [
        ("home", "", os.path.join(home, "config.yaml")),
        ("home", "", os.path.join(home, "auth.json")),
        ("home", "", os.path.join(home, "shared-auth", "auth.json")),
    ]
    profiles_root = os.path.join(home, "profiles")
    if os.path.isdir(profiles_root):
        for profile in sorted(os.listdir(profiles_root)):
            profile_root = os.path.join(profiles_root, profile)
            if not os.path.isdir(profile_root):
                continue
            candidates.extend([
                ("profile", profile, os.path.join(profile_root, "config.yaml")),
                ("profile", profile, os.path.join(profile_root, "auth.json")),
            ])

    selected = selected_profile.strip()
    references: list[dict[str, Any]] = []
    for source, profile, path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                text = handle.read()
        except OSError:
            continue
        references.append({
            "source": source,
            "profile": profile,
            "selected": bool(selected and profile == selected),
            "path": path,
            "openai_reference": "present" if "openai" in text.lower() else "absent",
            "OPENAI_API_KEY": "present" if "OPENAI_API_KEY" in text else "absent",
            "OPENAI_BASE_URL": "present" if "OPENAI_BASE_URL" in text else "absent",
        })
    return references


def _parse_hermes_auth_list(stdout: str) -> dict[str, Any]:
    providers: dict[str, dict[str, Any]] = {}
    current_provider = ""
    for raw_line in stdout.splitlines():
        line = raw_line.rstrip()
        header = re.match(r"^([A-Za-z0-9_.-]+)\s+\((\d+)\s+credentials?\):", line)
        if header:
            current_provider = header.group(1)
            providers[current_provider] = {
                "credential_count": int(header.group(2)),
                "auth_types": [],
                "source_types": [],
            }
            continue
        if not current_provider or not line.strip().startswith("#"):
            continue
        auth_types = providers[current_provider]["auth_types"]
        source_types = providers[current_provider]["source_types"]
        for auth_type in ["api_key", "oauth"]:
            if re.search(rf"\b{re.escape(auth_type)}\b", line) and auth_type not in auth_types:
                auth_types.append(auth_type)
        for source_type in ["env", "device_code", "gh_cli"]:
            if re.search(rf"\b{re.escape(source_type)}\b", line) and source_type not in source_types:
                source_types.append(source_type)
    for provider in providers.values():
        provider["auth_types"] = sorted(provider["auth_types"])
        provider["source_types"] = sorted(provider["source_types"])
    return {
        "providers": providers,
        "provider_names": sorted(providers.keys()),
    }


def _parse_hermes_auth_status(provider: str, stdout: str, returncode: int) -> dict[str, Any]:
    state = "unknown"
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        prefix = f"{provider}:"
        if line.lower().startswith(prefix):
            state = line[len(prefix):].strip().replace(" ", "_") or "unknown"
            break
    if state == "unknown" and returncode != 0:
        state = "unavailable"
    return {
        "provider": provider,
        "state": state,
    }


def _build_hermes_cli_auth_diagnostics(
    hermes_profile: str = "",
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
) -> dict[str, Any]:
    profile = hermes_profile.strip()
    if not profile:
        return {
            "profile": "",
            "skipped": "hermes_profile missing",
            "openai_images_api_key_auth": "unknown",
        }

    runner = command_runner or _run_command
    profile_args = ["--profile", profile]
    auth_list_command = ["hermes", *profile_args, "auth", "list"]
    openai_status_command = ["hermes", *profile_args, "auth", "status", "openai"]
    auth_list_result = runner(auth_list_command)
    openai_status_result = runner(openai_status_command)
    auth_list = _parse_hermes_auth_list(auth_list_result.stdout) if auth_list_result.returncode == 0 else {
        "providers": {},
        "provider_names": [],
    }
    providers = auth_list.get("providers", {})
    openai_provider = providers.get("openai", {}) if isinstance(providers, Mapping) else {}
    openai_auth_types = openai_provider.get("auth_types", []) if isinstance(openai_provider, Mapping) else []
    status = _parse_hermes_auth_status("openai", openai_status_result.stdout, openai_status_result.returncode)
    images_api_key_auth = "set" if "api_key" in openai_auth_types else "missing"

    return {
        "profile": profile,
        "commands": {
            "auth_list": " ".join(shlex.quote(part) for part in auth_list_command),
            "openai_status": " ".join(shlex.quote(part) for part in openai_status_command),
        },
        "auth_list": {
            "ok": auth_list_result.returncode == 0,
            **auth_list,
        },
        "openai_status": {
            "ok": openai_status_result.returncode == 0,
            **status,
        },
        "openai_images_api_key_auth": images_api_key_auth,
    }


def _hermes_cli_openai_auth_source(
    cli_auth: Mapping[str, Any],
    key: str = "OPENAI_API_KEY",
) -> dict[str, Any]:
    if not cli_auth or cli_auth.get("skipped"):
        return {}
    profile = str(cli_auth.get("profile", "")).strip()
    openai_status = cli_auth.get("openai_status", {})
    status_state = ""
    if isinstance(openai_status, Mapping):
        status_state = str(openai_status.get("state", "")).strip()
    key_state = (
        "set"
        if cli_auth.get("openai_images_api_key_auth") == "set" or status_state == "logged_in"
        else "missing"
    )
    return {
        "source": "hermes_cli_auth",
        "profile": profile,
        "selected": bool(profile),
        "provider": "openai",
        "openai_status": status_state,
        key: key_state,
    }


IPHONE_CREDENTIAL_BOUNDARY_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai_api_key_env", re.compile(r"\bOPENAI_API_KEY\b")),
    ("openai_base_url_env", re.compile(r"\bOPENAI_BASE_URL\b")),
    ("openai_image_env", re.compile(r"\bOPENAI_IMAGE_[A-Z0-9_]+\b")),
    ("openai_api_host", re.compile(r"\bapi\.openai\.com\b", re.IGNORECASE)),
    ("openai_images_edits_path", re.compile(r"(?:^|/)images/edits\b", re.IGNORECASE)),
    ("openai_image_model", re.compile(r"\bgpt-image[-A-Za-z0-9.]*\b", re.IGNORECASE)),
    ("openai_secret_key_literal", re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b")),
)

IPHONE_CREDENTIAL_BOUNDARY_DEFAULT_PATHS: tuple[str, ...] = (
    "Sources",
    "ios/AgentPocket",
    "ios/AgentPocketPickerUITests",
    "Tests",
)

IPHONE_CREDENTIAL_BOUNDARY_EXCLUDED_DIRS: set[str] = {
    ".build",
    ".git",
    "build",
    "build-device",
    "DerivedData",
    "SourcePackages",
}

IPHONE_CREDENTIAL_BOUNDARY_EXTENSIONS: set[str] = {
    ".swift",
    ".plist",
    ".entitlements",
    ".xcconfig",
}


def _iter_iphone_client_files(root: str, relative_paths: Sequence[str]) -> list[str]:
    root_abs = os.path.abspath(root)
    files: list[str] = []
    for relative_path in relative_paths:
        path = os.path.abspath(os.path.join(root_abs, relative_path))
        if not os.path.exists(path):
            continue
        if os.path.isfile(path):
            if os.path.splitext(path)[1] in IPHONE_CREDENTIAL_BOUNDARY_EXTENSIONS:
                files.append(path)
            continue
        for directory, dirnames, filenames in os.walk(path):
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if dirname not in IPHONE_CREDENTIAL_BOUNDARY_EXCLUDED_DIRS
            ]
            for filename in filenames:
                full_path = os.path.join(directory, filename)
                if os.path.splitext(full_path)[1] in IPHONE_CREDENTIAL_BOUNDARY_EXTENSIONS:
                    files.append(full_path)
    return sorted(set(files))


def build_iphone_credential_boundary_report(
    root: str = ".",
    client_paths: Optional[Sequence[str]] = None,
) -> Mapping[str, Any]:
    root_abs = os.path.abspath(root)
    scan_paths = list(client_paths or IPHONE_CREDENTIAL_BOUNDARY_DEFAULT_PATHS)
    files = _iter_iphone_client_files(root_abs, scan_paths)
    violations: list[dict[str, Any]] = []
    for path in files:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                for line_number, line in enumerate(handle, start=1):
                    for rule, pattern in IPHONE_CREDENTIAL_BOUNDARY_RULES:
                        if not pattern.search(line):
                            continue
                        violations.append({
                            "path": os.path.relpath(path, root_abs),
                            "line": line_number,
                            "rule": rule,
                            "match": "redacted",
                        })
        except OSError as error:
            violations.append({
                "path": os.path.relpath(path, root_abs),
                "line": 0,
                "rule": "readable_client_file",
                "error": str(error),
            })

    return {
        "ok": not violations,
        "phase": "iphone-credential-boundary",
        "iphone_credential_required": False,
        "boundary": "iPhone talks only to Hermes/mobile bridge; OpenAI provider credentials stay server-side.",
        "allowed_client_authorization": "Hermes/mobile bridge Bearer token only",
        "root": root_abs,
        "scan_paths": scan_paths,
        "scanned_files": len(files),
        "forbidden_rules": [rule for rule, _pattern in IPHONE_CREDENTIAL_BOUNDARY_RULES],
        "violations": violations,
        "missing": [] if not violations else ["iPhone OpenAI credential boundary"],
        "next_actions": [] if not violations else [
            "Remove OpenAI provider credentials, provider base URLs, and Images API request paths from iPhone client code.",
            "Keep OpenAI provider routing in Hermes/mock bridge and rerun this boundary check.",
        ],
    }


def build_provider_env_sources_report(
    env_file: str = "",
    hermes_home: str = "",
    hermes_profile: str = "",
    key: str = "OPENAI_API_KEY",
    env: Optional[Mapping[str, str]] = None,
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
    include_hermes_cli_auth: bool = False,
) -> Mapping[str, Any]:
    raw_env_values = os.environ if env is None else env
    env_values = _provider_visible_env(raw_env_values)
    runner = command_runner or _run_command
    source_args = _provider_source_command_args(
        env_file=env_file,
        hermes_home=hermes_home,
        hermes_profile=hermes_profile,
    )
    current_process = {
        "source": "current_process",
        key: _env_key_state(env_values, key),
    }
    forced_current_process = {
        "source": "hermes_force_current_process",
        "force_env": f"{HERMES_PROVIDER_ENV_FORCE_PREFIX}{key}",
        key: _provider_force_env_state(raw_env_values, key),
    }
    explicit_env_file = _env_file_key_state(env_file, key=key) if env_file else {}
    home = os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home()))
    hermes_profiles = _list_hermes_profile_env_sources(
        hermes_home=hermes_home,
        selected_profile=hermes_profile,
        key=key,
    )
    hermes_profile_auths = _list_hermes_profile_auth_sources(
        hermes_home=hermes_home,
        selected_profile=hermes_profile,
    )
    selected_profile = next(
        (profile for profile in hermes_profiles if profile.get("selected")),
        {},
    )
    launchd_result = runner(["launchctl", "getenv", key])
    launchd_value = launchd_result.stdout.strip()
    launchd = {
        "source": "launchd",
        key: "set" if launchd_result.returncode == 0 and bool(launchd_value) else "missing",
        "ok": launchd_result.returncode == 0,
        "error": "" if launchd_result.returncode == 0 else _clean_error(launchd_result),
    }
    sources: list[Mapping[str, Any]] = [current_process, forced_current_process, launchd]
    if explicit_env_file:
        sources.append({"source": "env_file", **explicit_env_file})
    hermes_home_env_file = _env_file_key_state(os.path.join(home, ".env"), key=key)
    shell_home = os.path.dirname(home) if hermes_home.strip() else ""
    shell_startup_files = _shell_startup_key_sources(home=shell_home, key=key)
    sources.append({
        "source": "hermes_home_env",
        "path": hermes_home_env_file.get("path", ""),
        "exists": bool(hermes_home_env_file.get("exists")),
        key: hermes_home_env_file.get(key, "missing"),
    })
    hermes_home_auth_file = _auth_env_source(
        os.path.join(home, "auth.json"),
        source="hermes_home_auth",
    )
    hermes_shared_auth_file = _auth_env_source(
        _hermes_shared_auth_file(hermes_home),
        source="hermes_shared_auth",
    )
    sources.append(hermes_home_auth_file)
    sources.append(hermes_shared_auth_file)
    for profile in hermes_profiles:
        sources.append({
            "source": "hermes_profile",
            "profile": profile.get("profile", ""),
            "selected": bool(profile.get("selected")),
            "path": profile.get("env_file", {}).get("path", ""),
            "exists": bool(profile.get("env_file", {}).get("exists")),
            key: profile.get(key, "missing"),
        })
    sources.extend(hermes_profile_auths)
    gateway_processes, gateway_process_probe = _list_hermes_gateway_process_env_sources(
        selected_profile=hermes_profile,
        key=key,
        command_runner=runner,
    )
    hermes_processes, hermes_process_probe = _list_current_hermes_process_env_diagnostics(
        selected_profile=hermes_profile,
        command_runner=runner,
    )
    sources.extend(gateway_processes)
    provider_references = _hermes_provider_reference_files(
        hermes_home=hermes_home,
        selected_profile=hermes_profile,
    )
    hermes_cli_auth = (
        _build_hermes_cli_auth_diagnostics(
            hermes_profile=hermes_profile,
            command_runner=runner,
        )
        if include_hermes_cli_auth
        else {}
    )
    hermes_cli_openai_source = _hermes_cli_openai_auth_source(hermes_cli_auth, key=key)
    if hermes_cli_openai_source:
        sources.append(hermes_cli_openai_source)
    set_sources = [
        source
        for source in sources
        if isinstance(source, Mapping) and source.get(key) == "set"
        and _counts_for_selected_profile(source, hermes_profile)
    ]
    selected_state = ""
    if selected_profile:
        selected_state = str(selected_profile.get(key, "missing"))
    selected_env_path = ""
    if selected_profile:
        env_file_value = selected_profile.get("env_file", {})
        if isinstance(env_file_value, Mapping):
            selected_env_path = str(env_file_value.get("path", ""))
    next_actions: list[str] = []
    if set_sources:
        next_actions.append("Run provider_preflight with the same server-side key source, then rerun gate_f_preflight.")
    else:
        if hermes_profile.strip():
            detail = f" ({selected_env_path})" if selected_env_path else ""
            next_actions.append(
                "Add the OpenAI Images API key to Hermes auth with "
                f"`{_hermes_auth_add_openai_command(hermes_home, hermes_profile)}` and paste the key at the secure prompt."
            )
            next_actions.append(
                "Run provider_preflight from the Hermes/mock bridge process that already has OPENAI_API_KEY, "
                f"or add OPENAI_API_KEY to the selected Hermes profile env file{detail} if that profile is "
                "the intended server-side key source."
            )
        elif env_file:
            next_actions.append(
                "Run provider_preflight from the Hermes/mock bridge process that already has OPENAI_API_KEY, "
                "or add OPENAI_API_KEY to the selected server-side env file if that file is the intended key source."
            )
        else:
            next_actions.append(
                "Expose OPENAI_API_KEY to the Hermes/mock bridge process through a server-side env file, "
                "Hermes profile .env, or user launchd environment."
            )
        next_actions.append(
            "Rerun provider_preflight after the key source reports set; the iPhone app never stores or calls this key."
        )

    return {
        "ok": bool(set_sources),
        "key": key,
        "env": {key: "set" if set_sources else "missing"},
        "current_process": current_process,
        "launchd": launchd,
        "env_file": explicit_env_file,
        "hermes": {
            "home": home,
            "home_env_file": hermes_home_env_file,
            "home_auth_file": hermes_home_auth_file,
            "shared_auth_file": hermes_shared_auth_file,
            "selected_profile": hermes_profile.strip(),
            "selected_profile_state": selected_state,
            "profiles": hermes_profiles,
            "profile_auths": hermes_profile_auths,
            "gateway_process_probe": gateway_process_probe,
            "gateway_processes": gateway_processes,
            "process_probe": hermes_process_probe,
            "processes": hermes_processes,
            "provider_references": provider_references,
            "cli_auth": hermes_cli_auth,
            "cli_openai_source": hermes_cli_openai_source,
        },
        "shell_startup_files": shell_startup_files,
        "sources": list(sources),
        "set_sources": [
            {
                "source": str(source.get("source", "")),
                "profile": str(source.get("profile", "")),
                "path": str(source.get("path", "")),
                "pid": str(source.get("pid", "")),
            }
            for source in set_sources
        ],
        "missing": [] if set_sources else [key],
        "next_actions": next_actions,
        "commands": {
            "hermes_auth_add_openai": _hermes_auth_add_openai_command(hermes_home, hermes_profile),
            "provider_env_sources": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa provider-env-sources "
                f"{(source_args + ' ') if source_args else ''}"
                f"--receipt-file {DEFAULT_PROVIDER_ENV_SOURCES_RECEIPT}"
            ),
            "hermes_openai_auth_import": (
                "OPENAI_API_KEY=<server-side-openai-api-key> "
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa hermes-openai-auth-import "
                f"{(source_args + ' ') if source_args else ''}"
                f"--receipt-file {DEFAULT_HERMES_OPENAI_AUTH_IMPORT_RECEIPT}"
            ),
            "provider_preflight": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa provider-preflight "
                "--photo-provider openai --photo-pack-root photo-pack "
                f"{(source_args + ' ') if source_args else ''}"
                f"--receipt-file {DEFAULT_OPENAI_PROVIDER_PREFLIGHT_RECEIPT}"
            ),
            "gate_f_preflight": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa gate-f-preflight "
                f"{(source_args + ' ') if source_args else ''}"
                f"--receipt-file {DEFAULT_GATE_F_PREFLIGHT_RECEIPT}"
            ),
            "launchd_setenv_template": f"launchctl setenv {key} <redacted-openai-api-key>",
        },
    }


def _provider_env_from_sources(
    env_file: str = "",
    hermes_home: str = "",
    hermes_profile: str = "",
) -> tuple[dict[str, str], str, dict[str, Any]]:
    env_values = _provider_visible_env(os.environ)
    env_overlay, effective_env_file, hermes_context = _provider_env_overlay_from_sources(
        env_file=env_file,
        hermes_home=hermes_home,
        hermes_profile=hermes_profile,
    )
    env_values.update(env_overlay)
    return env_values, effective_env_file, hermes_context


def _provider_env_overlay_from_sources(
    env_file: str = "",
    hermes_home: str = "",
    hermes_profile: str = "",
) -> tuple[dict[str, str], str, dict[str, Any]]:
    env_overlay = _provider_visible_env(_parse_env_file(env_file))
    effective_env_file = env_file
    hermes_context, hermes_env_values, hermes_env_file = _build_hermes_provider_context(
        hermes_home=hermes_home,
        hermes_profile=hermes_profile,
    )
    if hermes_context:
        env_overlay.update(hermes_env_values)
        if not effective_env_file:
            effective_env_file = hermes_env_file
    return env_overlay, effective_env_file, hermes_context


def _provider_source_command_args(
    env_file: str = "",
    hermes_home: str = "",
    hermes_profile: str = "",
) -> str:
    args: list[str] = []
    if hermes_home.strip() or hermes_profile.strip():
        if hermes_home.strip():
            args.extend(["--hermes-home", shlex.quote(hermes_home)])
        if hermes_profile.strip():
            args.extend(["--hermes-profile", shlex.quote(hermes_profile)])
    elif env_file:
        args.extend(["--env-file", shlex.quote(env_file)])
    return " ".join(args)


def _provider_source_arg_value(provider_source_args: str, option: str) -> str:
    try:
        parts = shlex.split(provider_source_args)
    except ValueError:
        return ""
    for index, part in enumerate(parts):
        if part == option and index + 1 < len(parts):
            return parts[index + 1]
        prefix = f"{option}="
        if part.startswith(prefix):
            return part[len(prefix):]
    return ""


def _hermes_auth_add_openai_command_from_source_args(provider_source_args: str) -> str:
    return _hermes_auth_add_openai_command(
        hermes_home=_provider_source_arg_value(provider_source_args, "--hermes-home"),
        hermes_profile=_provider_source_arg_value(provider_source_args, "--hermes-profile"),
    )


def _load_auth_json(path: str) -> dict[str, Any]:
    if not path or not os.path.exists(path):
        return {"version": 1, "credential_pool": {}}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "credential_pool": {}}
    if not isinstance(data, dict):
        return {"version": 1, "credential_pool": {}}
    if "version" not in data:
        data["version"] = 1
    if not isinstance(data.get("credential_pool"), dict):
        data["credential_pool"] = {}
    return data


def _hermes_openai_auth_import_path(
    hermes_home: str = "",
    hermes_profile: str = "",
    scope: str = "profile",
) -> str:
    if scope == "shared":
        return _hermes_shared_auth_file(hermes_home)
    home = os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home()))
    profile = hermes_profile.strip()
    if profile:
        return os.path.join(home, "profiles", profile, "auth.json")
    return os.path.join(home, "auth.json")


def build_hermes_openai_auth_import_report(
    hermes_home: str = "",
    hermes_profile: str = "",
    scope: str = "profile",
    label: str = "agent-pocket-openai-images",
    key_env: str = "OPENAI_API_KEY",
    base_url_env: str = "OPENAI_BASE_URL",
    env: Optional[Mapping[str, str]] = None,
    write: bool = True,
) -> Mapping[str, Any]:
    env_values = _provider_visible_env(os.environ if env is None else env)
    scope = scope.strip() or "profile"
    key = str(env_values.get(key_env, "")).strip()
    base_url = str(env_values.get(base_url_env, "")).strip()
    auth_file = _hermes_openai_auth_import_path(
        hermes_home=hermes_home,
        hermes_profile=hermes_profile,
        scope=scope,
    )
    exists_before = bool(auth_file and os.path.exists(auth_file))
    missing: list[str] = []
    if not key:
        missing.append(key_env)
    if scope == "profile" and not hermes_profile.strip() and not hermes_home.strip():
        missing.append("hermes_profile")

    written = False
    if write and not missing:
        data = _load_auth_json(auth_file)
        pool = data.get("credential_pool")
        if not isinstance(pool, dict):
            pool = {}
            data["credential_pool"] = pool
        entries = pool.get("openai", [])
        if not isinstance(entries, list):
            entries = []
        entry = {
            "label": label,
            "auth_type": "api_key",
            "access_token": key,
        }
        if base_url:
            entry["base_url"] = base_url
        retained = [
            existing
            for existing in entries
            if not (
                isinstance(existing, Mapping)
                and str(existing.get("label", "")) == label
                and str(existing.get("auth_type", "")) == "api_key"
            )
        ]
        pool["openai"] = [entry, *retained]
        parent = os.path.dirname(auth_file)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(auth_file, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        written = True

    base_url_report = build_openai_base_url_report({
        "OPENAI_BASE_URL": base_url,
    })
    next_actions: list[str] = []
    if missing:
        next_actions.append(
            f"Expose {key_env} only to the Hermes/mock bridge server process, then rerun this import command."
        )
    else:
        next_actions.append(
            "Rerun provider_preflight with the same Hermes source to write redacted server-side key proof."
        )
        next_actions.append(
            "Rerun gate_f_preflight before the real iPhone OpenAI flow; the iPhone still never stores this key."
        )

    return {
        "ok": not missing and written,
        "phase": "hermes-openai-auth-import",
        "scope": scope,
        "profile": hermes_profile.strip(),
        "auth_file": {
            "path": auth_file,
            "exists_before": exists_before,
            "written": written,
        },
        "env": {
            key_env: _env_key_state(env_values, key_env),
            base_url_env: _env_key_state(env_values, base_url_env),
        },
        "credential": {
            "provider": "openai",
            "auth_type": "api_key",
            "label": label,
            "base_url": base_url_report,
        },
        "missing": missing,
        "iphone_credential_required": False,
        "next_actions": next_actions,
    }


def _with_provider_command_env_file(report: Mapping[str, Any], env_file: str) -> dict[str, Any]:
    return _with_provider_command_source_args(
        report,
        _provider_source_command_args(env_file=env_file),
    )


def _with_provider_command_source_args(report: Mapping[str, Any], source_args: str) -> dict[str, Any]:
    updated = dict(report)
    commands = dict(updated.get("commands", {})) if isinstance(updated.get("commands"), Mapping) else {}
    source_args = source_args.strip()
    if source_args:
        server_command = str(commands.get("server", ""))
        if "--env-file /path/to/hermes-openai.env" in server_command:
            server_command = server_command.replace(
                "--env-file /path/to/hermes-openai.env",
                source_args,
            )
        elif "--env-file" not in server_command and "--hermes-profile" not in server_command:
            server_command = f"{server_command} {source_args}".strip()
        commands["server"] = server_command

        qa_command = str(commands.get("qa", ""))
        if qa_command and "--env-file" not in qa_command and "--hermes-profile" not in qa_command:
            commands["qa"] = f"{qa_command} {source_args}"
    updated["commands"] = commands
    return updated


@contextmanager
def _temporary_environ(values: Mapping[str, str]):
    previous: dict[str, Optional[str]] = {}
    for key, value in values.items():
        previous[key] = os.environ.get(key)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def fetch_qa_status(base_url: str, token: str = DEFAULT_TOKEN, timeout: float = 5.0) -> Mapping[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/mobile/v1/qa/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class SmokeRealProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def run_smoke_real_provider(
    *,
    mode: str = "fake",
    base_url: str = "",
    host: str = "127.0.0.1",
    port: int = 0,
    token: str = DEFAULT_TOKEN,
    timeout_seconds: float = 60.0,
    interval_seconds: float = 0.5,
    image_file: str = "",
    photo_pack_root: str = "photo-pack",
) -> Mapping[str, Any]:
    normalized_mode = mode.strip() or "fake"
    provider = _smoke_real_provider_name(normalized_mode)
    report: dict[str, Any] = {
        "schema_version": "kaka.smoke_real_provider.v1",
        "surface": "mock_bridge_server_smoke",
        "ok": False,
        "mode": normalized_mode,
        "provider": provider,
        "base_url": "",
        "steps": [],
        "artifacts": {},
        "tasks": {},
        "recall": {},
    }
    server = None
    thread = None
    owns_server = not str(base_url).strip()
    try:
        if owns_server:
            app = build_app_for_provider(
                "fixture",
                photo_pack_root=photo_pack_root,
                provider=provider,
            )
            server = create_http_server(host=host, port=port, app=app)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            actual_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
            actual_port = int(server.server_address[1])
            base_url = f"http://{actual_host}:{actual_port}"
        base = str(base_url).rstrip("/")
        report["base_url"] = base

        health = _smoke_step(
            report,
            "health",
            lambda: _smoke_json_request(base, "/mobile/v1/health", token=token, timeout=timeout_seconds),
        )
        if not health.get("ok"):
            raise SmokeRealProviderError("health_failed", "Bridge health did not report ok.")

        capabilities = _smoke_step(
            report,
            "capabilities",
            lambda: _smoke_json_request(base, "/mobile/v1/capabilities", token=token, timeout=timeout_seconds),
        )
        if "image_intake" not in capabilities.get("tasks", {}):
            raise SmokeRealProviderError("capability_missing", "Capabilities did not advertise image_intake.")
        if "intake" not in capabilities.get("tasks", {}):
            raise SmokeRealProviderError("capability_missing", "Capabilities did not advertise universal intake.")

        image_bytes, filename, mime_type, image_source, local_image_file = _smoke_image_payload(image_file)
        upload = _smoke_step(
            report,
            "asset_upload",
            lambda: _smoke_upload_asset(
                base,
                token=token,
                filename=filename,
                mime_type=mime_type,
                body=image_bytes,
                timeout=timeout_seconds,
            ),
        )
        asset_id = str(upload.get("asset_id", "")).strip()
        if not asset_id:
            raise SmokeRealProviderError("asset_upload_failed", "Asset upload did not return an asset_id.")
        report["artifacts"] = {
            "asset_id": asset_id,
            "image_file": local_image_file,
            "image_source": image_source,
            "filename": filename,
            "mime_type": mime_type,
        }

        image_task_create = _smoke_step(
            report,
            "image_intake_create",
            lambda: _smoke_json_request(
                base,
                "/mobile/v1/tasks/image-intake",
                method="POST",
                token=token,
                payload={
                    "profile_id": "photo-agent",
                    "asset_id": asset_id,
                    "locale": "en",
                },
                timeout=timeout_seconds,
            ),
        )
        image_task = _smoke_step(
            report,
            "image_intake_status",
            lambda: _smoke_poll_task(
                base,
                str(image_task_create.get("task_id", "")),
                token=token,
                timeout_seconds=timeout_seconds,
                interval_seconds=interval_seconds,
            ),
        )
        image_summary = _smoke_task_summary(image_task)
        report["tasks"]["image_intake"] = image_summary
        _smoke_step(report, "image_intake_result", lambda: _require_task_result(image_task, "image_intake"))

        intake_create = _smoke_step(
            report,
            "universal_intake_create",
            lambda: _smoke_json_request(
                base,
                "/mobile/v1/tasks/intake",
                method="POST",
                token=token,
                payload={
                    "type": "text",
                    "text": "M1 smoke test note: remember this only for QA and then forget it.",
                    "source_app": "Pocket Agent QA",
                    "locale": "en",
                },
                timeout=timeout_seconds,
            ),
        )
        intake_task = _smoke_step(
            report,
            "universal_intake_status",
            lambda: _smoke_poll_task(
                base,
                str(intake_create.get("task_id", "")),
                token=token,
                timeout_seconds=timeout_seconds,
                interval_seconds=interval_seconds,
            ),
        )
        intake_summary = _smoke_task_summary(intake_task)
        report["tasks"]["universal_intake"] = intake_summary
        _smoke_step(report, "universal_intake_result", lambda: _require_task_result(intake_task, "intake"))

        remember = _smoke_step(
            report,
            "recall_remember",
            lambda: _smoke_json_request(
                base,
                "/mobile/v1/recall/actions",
                method="POST",
                token=token,
                payload={
                    "action": "remember",
                    "source_task_id": intake_summary.get("task_id", ""),
                    "user_visible_summary": "M1 smoke test note should be remembered then forgotten.",
                },
                timeout=timeout_seconds,
            ),
        )
        report["recall"]["remember"] = _smoke_recall_summary(remember)
        forget = _smoke_step(
            report,
            "recall_forget",
            lambda: _smoke_json_request(
                base,
                "/mobile/v1/recall/actions",
                method="POST",
                token=token,
                payload={
                    "action": "forget",
                    "source_task_id": intake_summary.get("task_id", ""),
                    "user_visible_summary": "Forget the M1 smoke test note.",
                },
                timeout=timeout_seconds,
            ),
        )
        report["recall"]["forget"] = _smoke_recall_summary(forget)
        report["ok"] = True
    except SmokeRealProviderError as error:
        report["error"] = {"code": error.code, "message": error.message}
    except Exception as error:
        report["error"] = {"code": "smoke_failed", "message": str(error)}
    finally:
        if server is not None:
            server.shutdown()
        if thread is not None:
            thread.join(timeout=2)
        if server is not None:
            server.server_close()
    return report


def _smoke_real_provider_name(mode: str) -> str:
    normalized = mode.strip() or "fake"
    if normalized == "real":
        return "anthropic"
    if normalized in {"fake", "anthropic", "hermes"}:
        return normalized
    return "fake"


def _smoke_real_provider_mode(mode: str, provider: str = "") -> str:
    normalized_provider = provider.strip()
    if normalized_provider:
        return normalized_provider
    return mode.strip() or "fake"


def _smoke_real_provider_missing_key(provider: str) -> str:
    if provider == "anthropic" and not str(os.environ.get("ANTHROPIC_API_KEY", "")).strip():
        return "ANTHROPIC_API_KEY"
    if provider == "hermes" and not str(os.environ.get("KAKA_HERMES_API_KEY", "")).strip():
        return "KAKA_HERMES_API_KEY"
    return ""


def _smoke_step(report: dict[str, Any], name: str, action: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    started = time.monotonic()
    step: dict[str, Any] = {"name": name, "status": "failed", "duration_ms": 0}
    report["steps"].append(step)
    try:
        result = action()
    except SmokeRealProviderError as error:
        step["duration_ms"] = _elapsed_ms(started)
        step["error"] = {"code": error.code, "message": error.message}
        raise
    except Exception as error:
        step["duration_ms"] = _elapsed_ms(started)
        step["error"] = {"code": "step_failed", "message": str(error)}
        raise
    step["status"] = "passed"
    step["duration_ms"] = _elapsed_ms(started)
    return result


def _elapsed_ms(started: float) -> int:
    return int(round((time.monotonic() - started) * 1000))


def _smoke_json_request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    token: str = DEFAULT_TOKEN,
    payload: Optional[Mapping[str, Any]] = None,
    timeout: float = 60.0,
) -> Mapping[str, Any]:
    body = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    return _read_smoke_json_response(request, timeout=timeout)


def _smoke_upload_asset(
    base_url: str,
    *,
    token: str,
    filename: str,
    mime_type: str,
    body: bytes,
    timeout: float,
) -> Mapping[str, Any]:
    boundary = f"kaka-smoke-{time.time_ns()}"
    metadata = json.dumps({"width": 4, "height": 4}, separators=(",", ":"))
    multipart = b"".join([
        _multipart_field(boundary, "metadata", metadata.encode("utf-8")),
        _multipart_file(boundary, "file", filename, mime_type, body),
        f"--{boundary}--\r\n".encode("utf-8"),
    ])
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/mobile/v1/assets",
        data=multipart,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    return _read_smoke_json_response(request, timeout=timeout)


def _read_smoke_json_response(request: urllib.request.Request, *, timeout: float) -> Mapping[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
            return json.loads(raw_body) if raw_body else {}
    except urllib.error.HTTPError as error:
        raw_body = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            payload = {"body": raw_body}
        message = payload.get("error", {}).get("message") if isinstance(payload, Mapping) else ""
        raise SmokeRealProviderError(
            "http_error",
            f"HTTP {error.code} for {request.full_url}: {message or raw_body}",
        ) from error


def _multipart_field(boundary: str, name: str, value: bytes) -> bytes:
    return (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n"
    ).encode("utf-8") + value + b"\r\n"


def _multipart_file(boundary: str, name: str, filename: str, mime_type: str, value: bytes) -> bytes:
    return (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + value + b"\r\n"


def _smoke_image_payload(image_file: str) -> tuple[bytes, str, str, str, str]:
    if image_file:
        with open(image_file, "rb") as handle:
            return (
                handle.read(),
                os.path.basename(image_file),
                _mime_type_for_image_file(image_file),
                "provided_file",
                os.path.abspath(os.path.expanduser(image_file)),
            )
    generated_path = DEFAULT_REAL_PROVIDER_SMOKE_IMAGE
    with open(generated_path, "wb") as handle:
        handle.write(_simulator_library_fixture_png(width=4, height=4))
    with open(generated_path, "rb") as handle:
        return handle.read(), os.path.basename(generated_path), "image/png", "generated_file", generated_path


def _mime_type_for_image_file(path: str) -> str:
    lower = path.lower()
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".heic"):
        return "image/heic"
    return "image/png"


def _smoke_poll_task(
    base_url: str,
    task_id: str,
    *,
    token: str,
    timeout_seconds: float,
    interval_seconds: float,
) -> Mapping[str, Any]:
    if not task_id:
        raise SmokeRealProviderError("missing_task_id", "Task creation did not return a task_id.")
    deadline = time.monotonic() + timeout_seconds
    while True:
        task = _smoke_json_request(
            base_url,
            f"/mobile/v1/tasks/{task_id}",
            token=token,
            timeout=timeout_seconds,
        )
        status = str(task.get("status", ""))
        if status in {"completed", "failed", "cancelled"}:
            return task
        if time.monotonic() >= deadline:
            raise SmokeRealProviderError("task_timeout", f"Timed out waiting for task {task_id}.")
        time.sleep(max(float(interval_seconds), 0.0))


def _require_task_result(task: Mapping[str, Any], result_type: str) -> Mapping[str, Any]:
    if task.get("status") != "completed":
        raise SmokeRealProviderError("task_failed", f"{result_type} task did not complete.")
    if task.get("result_type") != result_type:
        raise SmokeRealProviderError("unexpected_result_type", f"Expected {result_type} result.")
    if result_type == "image_intake" and not isinstance(task.get("image_intake"), Mapping):
        raise SmokeRealProviderError("missing_result", "Image intake result is missing.")
    if result_type == "intake" and not isinstance(task.get("intake"), Mapping):
        raise SmokeRealProviderError("missing_result", "Universal intake result is missing.")
    return task


def _smoke_task_summary(task: Mapping[str, Any]) -> dict[str, Any]:
    summary = {
        "task_id": task.get("task_id", ""),
        "status": task.get("status", ""),
        "result_type": task.get("result_type", ""),
        "provider": task.get("provider", ""),
    }
    if isinstance(task.get("image_intake"), Mapping):
        suggestions = task["image_intake"].get("suggestions", [])
        summary["title"] = task["image_intake"].get("title", "")
        summary["suggestions_count"] = len(suggestions) if isinstance(suggestions, list) else 0
    if isinstance(task.get("intake"), Mapping):
        suggestions = task["intake"].get("suggestions", [])
        summary["title"] = task["intake"].get("title", "")
        summary["suggestions_count"] = len(suggestions) if isinstance(suggestions, list) else 0
    return summary


def _smoke_recall_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    item = payload.get("item")
    return {
        "action": payload.get("action", ""),
        "status": payload.get("status", ""),
        "item_id": item.get("item_id", "") if isinstance(item, Mapping) else "",
        "deleted_item_ids": payload.get("deleted_item_ids", []),
    }


def evaluate_connection_restore(status: Mapping[str, Any]) -> EvaluationResult:
    missing: list[str] = []
    if _count(status, "requests", "health") < 1:
        missing.append("health request")
    if _count(status, "requests", "capabilities") < 1:
        missing.append("capabilities request")
    return EvaluationResult(ok=not missing, missing=missing)


def evaluate_discovery_refresh(status: Mapping[str, Any]) -> EvaluationResult:
    missing = list(evaluate_connection_restore(status).missing)
    if _count(status, "requests", "pairing_dev") < 1:
        missing.append("pairing_dev request")
    if _count(status, "requests", "pairing_exchange") < 1:
        missing.append("pairing_exchange request")
    return EvaluationResult(ok=not missing, missing=missing)


def evaluate_photo_flow(status: Mapping[str, Any]) -> EvaluationResult:
    missing: list[str] = []
    if _count(status, "requests", "asset_upload") < 1:
        missing.append("asset_upload request")
    if _count(status, "requests", "photo_task_create") < 1:
        missing.append("photo_task_create request")
    if _count(status, "tasks", "completed") < 1:
        missing.append("completed task")
    if _count(status, "requests", "asset_download") < 1:
        missing.append("asset_download request")
    if _count(status, "assets", "download_request_count") < 1:
        missing.append("result download")
    return EvaluationResult(ok=not missing, missing=missing)


def evaluate_local_recipe_photo_flow(status: Mapping[str, Any]) -> EvaluationResult:
    missing = list(evaluate_photo_flow(status).missing)
    if _receipt_provider_name(status) != "recipe_local":
        missing.append("provider recipe_local")

    task = _last_task(status)
    variant_count = task.get("variant_count", 0)
    if not isinstance(variant_count, int) and isinstance(task.get("variants"), list):
        variant_count = len(task["variants"])
    if not isinstance(variant_count, int) or variant_count < 2:
        missing.append("local recipe two variants")

    if task.get("renderer") != "local_parametric":
        missing.append("local recipe renderer")

    composition = task.get("composition")
    if not _has_recipe_composition(composition):
        missing.append("local recipe composition")
    if not _has_recipe_crop(composition):
        missing.append("local recipe crop metadata")

    qa = task.get("qa")
    if not _has_recipe_difference_metrics(qa):
        missing.append("local recipe difference metrics")

    return EvaluationResult(ok=not missing, missing=missing)


def verify_receipt_payload(
    receipt: Mapping[str, Any],
    expected_phase: str,
    expected_provider: str = "",
) -> EvaluationResult:
    missing: list[str] = []
    if receipt.get("phase") != expected_phase:
        missing.append(f"phase {expected_phase}")
    if receipt.get("ok") is not True:
        missing.append("ok receipt flag")
    if expected_phase == "iphone-credential-boundary":
        if receipt.get("iphone_credential_required") is not False:
            missing.append("iPhone credential-free boundary")
        if not isinstance(receipt.get("violations"), list):
            missing.append("credential boundary violations")
        return EvaluationResult(ok=not missing, missing=missing)

    status = receipt.get("status")
    if not isinstance(status, Mapping):
        missing.append("status")
    else:
        if expected_phase == "connection":
            evaluator = evaluate_connection_restore
        elif expected_phase == "discovery-refresh":
            evaluator = evaluate_discovery_refresh
        elif expected_phase == "photo-flow" and expected_provider == "recipe_local":
            evaluator = evaluate_local_recipe_photo_flow
        else:
            evaluator = evaluate_photo_flow
        missing.extend(evaluator(status).missing)
        if expected_provider and expected_provider != "recipe_local":
            provider_name = _receipt_provider_name(status)
            if provider_name != expected_provider:
                missing.append(f"provider {expected_provider}")

    return EvaluationResult(ok=not missing, missing=missing)


def build_physical_qa_commands(
    host: str,
    port: int = 8765,
    device_id: str = "",
    bundle_id: str = DEFAULT_BUNDLE_ID,
) -> list[str]:
    base_url = f"http://{host}:{port}"
    return [
        "# 0. Preferred: run the whole LAN QA session in one terminal",
        build_run_lan_command(host=host, port=port, device_id=device_id, bundle_id=bundle_id),
        "",
        "# Or run the same evidence chain step by step:",
        "# 1. Start the LAN mock Hermes bridge",
        (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.server "
            f"--host 0.0.0.0 --port {port} --bonjour --bonjour-host {host}"
        ),
        "",
        "# 2. Relaunch Pocket Agent on the physical iPhone",
        (
            "xcrun devicectl device process launch "
            f"--device {device_id} --terminate-existing {bundle_id}"
        ),
        "",
        "# 3. Wait until saved Hermes restore reaches the bridge",
        (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa wait-connection "
            f"--base-url {base_url}"
        ),
        "",
        "# 4. On iPhone: choose/take a photo, Send to Pocket Agent, Review Results, Download Selected",
        (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa wait-photo-flow "
            f"--base-url {base_url} --timeout 180"
        ),
        "",
        "# 5. Inspect the final QA receipt if needed",
        (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa status "
            f"--base-url {base_url}"
        ),
    ]


def build_run_lan_command(
    host: str,
    port: int = 8765,
    device_id: str = "",
    bundle_id: str = DEFAULT_BUNDLE_ID,
    connection_timeout: float = 60,
    photo_timeout: float = 180,
    no_bonjour: bool = False,
    photo_provider: str = "fixture",
) -> str:
    parts = [
        "PYTHONPATH=mock_bridge",
        "python3",
        "-m",
        "agent_pocket_mock_bridge.qa",
        "run-lan",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if device_id:
        parts.extend(["--device-id", device_id])
    else:
        parts.append("--no-launch")
    parts.extend(
        [
            "--bundle-id",
            bundle_id,
            "--connection-timeout",
            _format_duration(connection_timeout),
            "--photo-timeout",
            _format_duration(photo_timeout),
        ]
    )
    if no_bonjour:
        parts.append("--no-bonjour")
    if photo_provider != "fixture":
        parts.extend(["--photo-provider", photo_provider])
    return " ".join(parts)


def build_run_tailscale_command(
    host: str,
    port: int = 8765,
    device_id: str = "",
    bundle_id: str = DEFAULT_BUNDLE_ID,
    connection_timeout: float = 60,
    photo_timeout: float = 180,
    photo_provider: str = "fixture",
) -> str:
    return build_run_lan_command(
        host=host,
        port=port,
        device_id=device_id,
        bundle_id=bundle_id,
        connection_timeout=connection_timeout,
        photo_timeout=photo_timeout,
        no_bonjour=True,
        photo_provider=photo_provider,
    )


def build_preflight_report(
    port: int = 8765,
    bundle_id: str = DEFAULT_BUNDLE_ID,
    env: Optional[Mapping[str, str]] = None,
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
) -> Mapping[str, Any]:
    runner = command_runner or _run_command
    env_values = _provider_visible_env(os.environ if env is None else env)
    lan = runner(["ipconfig", "getifaddr", "en0"])
    tailscale_report = _build_tailscale_report(runner, env=env_values)
    devices = runner(["xcrun", "devicectl", "list", "devices"])
    devicectl = runner(["xcrun", "--find", "devicectl"])
    dns_sd = runner(["which", "dns-sd"])

    lan_ip = _first_line(lan.stdout)
    tailscale_ip = str(tailscale_report.get("ip", ""))
    device_id = _first_connected_device_id(devices.stdout)

    commands: dict[str, str] = {}
    if lan_ip:
        commands["lan"] = build_run_lan_command(
            host=lan_ip,
            port=port,
            device_id=device_id,
            bundle_id=bundle_id,
        )
    if tailscale_ip:
        commands["tailscale"] = build_run_tailscale_command(
            host=tailscale_ip,
            port=port,
            device_id=device_id,
            bundle_id=bundle_id,
        )

    return {
        "lan": {
            "ok": lan.returncode == 0 and bool(lan_ip),
            "ip": lan_ip,
            "error": "" if lan.returncode == 0 else _clean_error(lan),
        },
        "tailscale": tailscale_report,
        "device": {
            "ok": devices.returncode == 0 and bool(device_id),
            "id": device_id,
            "error": "" if devices.returncode == 0 else _clean_error(devices),
        },
        "tools": {
            "devicectl": {
                "ok": devicectl.returncode == 0,
                "path": _first_line(devicectl.stdout),
                "error": "" if devicectl.returncode == 0 else _clean_error(devicectl),
            },
            "dns_sd": {
                "ok": dns_sd.returncode == 0,
                "path": _first_line(dns_sd.stdout),
                "error": "" if dns_sd.returncode == 0 else _clean_error(dns_sd),
            },
        },
        "simulator": build_simulator_preflight_report(
            port=port,
            bundle_id=bundle_id,
            gate_f_host=lan_ip,
            command_runner=runner,
        ),
        "commands": commands,
    }


def build_physical_device_preflight_report(
    project: str = "ios/AgentPocket.xcodeproj",
    scheme: str = "AgentPocket",
    target: str = "AgentPocket",
    configuration: str = "Debug",
    device_id: str = "",
    build_check: bool = False,
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
) -> Mapping[str, Any]:
    runner = command_runner or _run_command
    devices = runner(["xcrun", "devicectl", "list", "devices"])
    destinations = runner(["xcodebuild", "-project", project, "-scheme", scheme, "-showdestinations"])
    build_command = [
        "xcodebuild",
        "-project",
        project,
        "-target",
        target,
        "-configuration",
        configuration,
        "-sdk",
        "iphoneos",
        "-allowProvisioningUpdates",
        "build",
    ]

    resolved_device_id = device_id.strip() or _first_connected_device_id(devices.stdout)
    device = _physical_device_summary(devices.stdout, resolved_device_id)
    physical_destinations = _ios_physical_destinations(destinations.stdout)
    ineligible = _ineligible_destinations(destinations.stdout)
    matching_destination = next(
        (destination for destination in physical_destinations if destination.get("id") == resolved_device_id),
        {},
    )
    matching_ineligible = [
        note
        for note in ineligible
        if (resolved_device_id and resolved_device_id in note)
        or (device.get("name") and str(device.get("name")) in note)
    ]
    if not matching_ineligible:
        matching_ineligible = ineligible

    device_ok = devices.returncode == 0 and bool(resolved_device_id)
    destination_ok = destinations.returncode == 0 and bool(matching_destination)
    target_build: dict[str, Any] = {
        "checked": bool(build_check),
        "ok": False,
        "target": target,
        "configuration": configuration,
        "sdk": "iphoneos",
        "command": " ".join(build_command),
        "error": "",
    }
    if build_check:
        build = runner(build_command) if command_runner else _run_command(build_command, timeout_seconds=240)
        target_build = {
            **target_build,
            "ok": build.returncode == 0,
            "error": "" if build.returncode == 0 else _clean_error(build),
        }

    cli_build_ok = bool(target_build.get("checked")) and bool(target_build.get("ok"))
    ok = device_ok and (destination_ok or cli_build_ok)
    if ok:
        status = "ready" if destination_ok else "ready_via_cli_build"
        missing: list[str] = []
    elif not device_ok:
        status = "device_not_connected"
        missing = ["paired physical iPhone"]
    elif build_check and not cli_build_ok:
        status = "blocked_by_target_build"
        missing = ["iphoneos target build"]
    elif matching_ineligible and any("is not installed" in note for note in matching_ineligible):
        status = "blocked_by_xcode_device_support"
        missing = ["Xcode iOS device platform support"]
    else:
        status = "blocked_by_xcode_destination"
        missing = ["Xcode physical iPhone destination"]

    next_actions: list[str] = []
    if status == "blocked_by_xcode_device_support":
        next_actions.append(
            "Install the matching iOS platform from Xcode > Settings > Components, then rerun physical-device-preflight."
        )
    elif status == "ready_via_cli_build":
        next_actions.append(
            "Use the CLI run-lan or gate-f-resume path for real-device QA; install Xcode platform support only if you need the Xcode Run button."
        )
    elif status == "device_not_connected":
        next_actions.append("Connect and trust the physical iPhone, then rerun physical-device-preflight.")
    elif status == "blocked_by_target_build":
        next_actions.append("Fix the iphoneos target build, then rerun physical-device-preflight --build-check.")
    elif status == "blocked_by_xcode_destination":
        next_actions.append("Open Xcode Devices and make the iPhone eligible for the AgentPocket scheme.")

    return {
        "ok": ok,
        "status": status,
        "project": project,
        "scheme": scheme,
        "target": target,
        "configuration": configuration,
        "device": {
            "ok": device_ok,
            "id": resolved_device_id,
            "name": str(device.get("name", "")),
            "state": str(device.get("state", "")),
            "model": str(device.get("model", "")),
            "raw": str(device.get("raw", "")),
            "error": "" if devices.returncode == 0 else _clean_error(devices),
        },
        "xcode_destination": {
            "ok": destination_ok,
            "eligible": matching_destination,
            "ineligible": matching_ineligible,
            "error": "" if destinations.returncode == 0 else _clean_error(destinations),
        },
        "target_build": target_build,
        "missing": missing,
        "next_actions": next_actions,
        "commands": {
            "show_destinations": f"xcodebuild -project {project} -scheme {scheme} -showdestinations",
            "target_build": " ".join(build_command),
            "open_xcode_components": "open x-apple.systempreferences:com.apple.dt.Xcode",
        },
    }


def build_simulator_preflight_report(
    app_path: str = "ios/build/Debug-iphonesimulator/AgentPocket.app",
    port: int = 8766,
    bundle_id: str = DEFAULT_BUNDLE_ID,
    gate_f_host: str = "",
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
) -> Mapping[str, Any]:
    runner = command_runner or _run_command
    available = runner(["xcrun", "simctl", "list", "devices", "available"])
    booted = runner(["xcrun", "simctl", "list", "devices", "booted"])
    simctl = runner(["xcrun", "--find", "simctl"])

    available_devices = _simulator_devices(available.stdout)
    booted_devices = _simulator_devices(booted.stdout)
    selected_device = booted_devices[0] if booted_devices else (available_devices[0] if available_devices else {})
    booted_device = booted_devices[0] if booted_devices else {}
    app_exists = os.path.exists(app_path)
    selected_id = str(selected_device.get("id", ""))
    gate_f_host_arg = f"--gate-f-host {gate_f_host.strip()} " if gate_f_host.strip() else ""

    commands = {
        "build": (
            "xcodebuild -project ios/AgentPocket.xcodeproj -target AgentPocket "
            "-configuration Debug -sdk iphonesimulator build"
        ),
        "install": f"xcrun simctl install booted {app_path}",
        "launch": f"xcrun simctl launch --terminate-running-process booted {bundle_id}",
        "local_connection": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan "
            f"--host 127.0.0.1 --port {port} --no-launch --connection-only "
            f"--bundle-id {bundle_id} --connection-timeout 45 --photo-timeout 180"
        ),
        "connection_smoke_session": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-connection-smoke "
            f"--host 127.0.0.1 --port {port} --bundle-id {bundle_id} "
            "--receipt-file docs/qa-receipts/simulator-connection-latest.json"
        ),
        "discovery_refresh_smoke": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-discovery-refresh-smoke "
            f"--host 127.0.0.1 --port {port + 1} --bundle-id {bundle_id} "
            f"--receipt-file {DEFAULT_SIMULATOR_DISCOVERY_REFRESH_RECEIPT} "
            f"--screenshot-file {DEFAULT_SIMULATOR_DISCOVERY_REFRESH_SCREENSHOT}"
        ),
        "smoke_launch": (
            "xcrun simctl launch --terminate-running-process booted "
            f"{bundle_id} --agent-pocket-simulator-smoke "
            f"--agent-pocket-smoke-base-url http://127.0.0.1:{port}"
        ),
        "smoke_session": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan "
            f"--host 127.0.0.1 --port {port} --no-launch --bundle-id {bundle_id} "
            "--connection-timeout 45 --photo-timeout 60 "
            "--receipt-file docs/qa-receipts/simulator-photo-flow-smoke.json"
        ),
        "openai_smoke_session": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-openai-smoke "
            f"--host 127.0.0.1 --port {port + 3} --bundle-id {bundle_id} "
            "--fake-openai-port 8781 "
            "--receipt-file docs/qa-receipts/simulator-openai-compatible-photo-flow.json "
            "--fake-openai-status-file docs/qa-receipts/simulator-openai-compatible-fake-openai-status.json "
            "--screenshot-file /tmp/agent-pocket-simulator-openai-provider-smoke.png"
        ),
        "capture_ready_smoke": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-ready-smoke "
            f"--bundle-id {bundle_id} "
            "--screenshot-file /tmp/agent-pocket-simulator-capture-ready.png "
            f"--receipt-file {DEFAULT_SIMULATOR_CAPTURE_READY_RECEIPT}"
        ),
        "capture_completed_smoke": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-completed-smoke "
            f"--bundle-id {bundle_id} "
            f"--screenshot-file {DEFAULT_SIMULATOR_CAPTURE_COMPLETED_SCREENSHOT} "
            f"--receipt-file {DEFAULT_SIMULATOR_CAPTURE_COMPLETED_RECEIPT}"
        ),
        "result_gallery_smoke": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-result-gallery-smoke "
            f"--bundle-id {bundle_id} "
            f"--screenshot-file {DEFAULT_SIMULATOR_RESULT_GALLERY_SCREENSHOT} "
            f"--receipt-file {DEFAULT_SIMULATOR_RESULT_GALLERY_RECEIPT}"
        ),
        "result_gallery_downloaded_smoke": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-result-gallery-downloaded-smoke "
            f"--bundle-id {bundle_id} "
            f"--screenshot-file {DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_SCREENSHOT} "
            f"--receipt-file {DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_RECEIPT}"
        ),
        "share_sheet_smoke": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-share-sheet-smoke "
            f"--bundle-id {bundle_id} "
            f"--screenshot-file {DEFAULT_SIMULATOR_SHARE_SHEET_SCREENSHOT} "
            f"--receipt-file {DEFAULT_SIMULATOR_SHARE_SHEET_RECEIPT}"
        ),
        "picker_ui_smoke": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-picker-ui-smoke "
            f"--bundle-id {bundle_id} "
            f"--screenshot-file {DEFAULT_SIMULATOR_PICKER_UI_SCREENSHOT}"
        ),
        "ui_test_preflight": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-ui-test-preflight "
            f"--receipt-file {DEFAULT_SIMULATOR_UI_TEST_PREFLIGHT_RECEIPT}"
        ),
        "suite": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-suite "
            f"--suite-receipt-file {DEFAULT_SIMULATOR_SUITE_RECEIPT}"
        ),
        "simulator_only_resume": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-only-resume "
            f"--suite-receipt-file {DEFAULT_SIMULATOR_SUITE_RECEIPT} "
            f"--gate-f-preflight-receipt {DEFAULT_GATE_F_PREFLIGHT_RECEIPT} "
            f"{gate_f_host_arg}"
            f"--resume-receipt-file {DEFAULT_SIMULATOR_ONLY_RESUME_RECEIPT} "
            "--readiness-output-file docs/agent-pocket-readiness.md"
        ),
        "seed_photo_library": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-seed-photo-library "
            f"--image-file {DEFAULT_SIMULATOR_LIBRARY_FIXTURE}"
        ),
    }
    if selected_id:
        commands["boot"] = (
            f"xcrun simctl boot {selected_id} && "
            f"xcrun simctl bootstatus {selected_id} -b"
        )

    return {
        "ok": simctl.returncode == 0 and app_exists and bool(booted_device),
        "app": {
            "exists": app_exists,
            "path": app_path,
        },
        "simctl": {
            "ok": simctl.returncode == 0,
            "path": _first_line(simctl.stdout),
            "error": "" if simctl.returncode == 0 else _clean_error(simctl),
        },
        "available": {
            "ok": available.returncode == 0,
            "count": len(available_devices),
            "error": "" if available.returncode == 0 else _clean_error(available),
        },
        "booted": {
            "ok": bool(booted_device),
            "id": str(booted_device.get("id", "")),
            "name": str(booted_device.get("name", "")),
            "error": "" if booted.returncode == 0 else _clean_error(booted),
        },
        "selected": selected_device,
        "commands": commands,
    }


def build_simulator_ui_test_preflight_report(
    project: str = "ios/AgentPocket.xcodeproj",
    scheme: str = "AgentPocket",
    test_target: str = "AgentPocketPickerUITests",
    bundle_id: str = DEFAULT_BUNDLE_ID,
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
) -> Mapping[str, Any]:
    runner = command_runner or _run_command
    sdk = runner(["xcodebuild", "-showsdks"])
    runtimes = runner(["xcrun", "simctl", "list", "runtimes"])
    destinations = runner([
        "xcodebuild",
        "-showdestinations",
        "-project",
        project,
        "-scheme",
        scheme,
        "-sdk",
        "iphonesimulator",
    ])

    sdk_versions = _ios_simulator_sdk_versions(sdk.stdout)
    runtime_versions = _ios_runtime_versions(runtimes.stdout)
    latest_sdk = _latest_version(sdk_versions)
    latest_runtime = _latest_version(runtime_versions)
    available_destinations = _ios_simulator_destinations(destinations.stdout)
    ineligible_destinations = _ineligible_destinations(destinations.stdout)
    mismatch_ok = bool(latest_sdk and latest_runtime and latest_sdk == latest_runtime)

    if not latest_sdk:
        mismatch_reason = "No iOS Simulator SDK was reported by xcodebuild."
    elif not latest_runtime:
        mismatch_reason = "No iOS Simulator runtime was reported by simctl."
    elif latest_sdk != latest_runtime:
        mismatch_reason = "Installed iOS Simulator runtime does not match the active iOS Simulator SDK."
    else:
        mismatch_reason = ""

    destinations_ok = destinations.returncode == 0 and bool(available_destinations)
    return {
        "ok": sdk.returncode == 0 and runtimes.returncode == 0 and destinations_ok and mismatch_ok,
        "project": project,
        "scheme": scheme,
        "test_target": test_target,
        "sdk": {
            "ok": sdk.returncode == 0 and bool(sdk_versions),
            "versions": sdk_versions,
            "latest": latest_sdk,
            "error": "" if sdk.returncode == 0 else _clean_error(sdk),
        },
        "runtime": {
            "ok": runtimes.returncode == 0 and bool(runtime_versions),
            "versions": runtime_versions,
            "latest": latest_runtime,
            "error": "" if runtimes.returncode == 0 else _clean_error(runtimes),
        },
        "destinations": {
            "ok": destinations_ok,
            "available": available_destinations,
            "ineligible": ineligible_destinations,
            "error": "" if destinations.returncode == 0 else _clean_error(destinations),
        },
        "mismatch": {
            "ok": mismatch_ok,
            "sdk_latest": latest_sdk,
            "runtime_latest": latest_runtime,
            "reason": mismatch_reason,
        },
        "commands": {
            "build_ui_test_bundle": (
                f"xcodebuild build -project {project} -target {test_target} "
                "-configuration Debug -sdk iphonesimulator"
            ),
            "run_picker_ui_test": (
                f"xcodebuild test -project {project} -scheme {scheme} "
                "-destination 'platform=iOS Simulator,name=<matching-installed-simulator>' "
                f"-only-testing:{test_target}/{test_target}/testChoosingSeededPhotoShowsReadySendAction"
            ),
            "seed_photo_library": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-seed-photo-library "
                f"--image-file {DEFAULT_SIMULATOR_LIBRARY_FIXTURE}"
            ),
            "launch_picker_ui_smoke": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-picker-ui-smoke "
                f"--bundle-id {bundle_id} --screenshot-file {DEFAULT_SIMULATOR_PICKER_UI_SCREENSHOT}"
            ),
            "open_xcode_components": "open x-apple.systempreferences:com.apple.dt.Xcode",
        },
    }


def build_gate_audit_report(
    root: str = ".",
    simulator_connection_receipt: str = "docs/qa-receipts/simulator-connection-latest.json",
    fixture_receipt: str = "docs/qa-receipts/simulator-photo-flow-smoke.json",
    script_receipt: str = "docs/qa-receipts/simulator-script-provider-photo-flow.json",
    openai_receipt: str = "docs/qa-receipts/simulator-openai-compatible-photo-flow-screenshot.json",
    fake_openai_status_file: str = "docs/qa-receipts/simulator-openai-compatible-fake-openai-status-screenshot.json",
    python_test_receipt: str = "docs/qa-receipts/python-tests-latest.json",
    swift_test_receipt: str = "docs/qa-receipts/swift-test-latest.json",
    simulator_ui_test_preflight_receipt: str = DEFAULT_SIMULATOR_UI_TEST_PREFLIGHT_RECEIPT,
    simulator_suite_receipt: str = DEFAULT_SIMULATOR_SUITE_RECEIPT,
    simulator_only_resume_receipt: str = DEFAULT_SIMULATOR_ONLY_RESUME_RECEIPT,
    provider_preflight_receipt: str = DEFAULT_OPENAI_PROVIDER_PREFLIGHT_RECEIPT,
    provider_env_sources_receipt: str = DEFAULT_PROVIDER_ENV_SOURCES_RECEIPT,
    provider_env_sources_all_profiles_receipt: str = DEFAULT_PROVIDER_ENV_SOURCES_ALL_PROFILES_RECEIPT,
    iphone_credential_boundary_receipt: str = DEFAULT_IPHONE_CREDENTIAL_BOUNDARY_RECEIPT,
    gate_f_preflight_receipt: str = DEFAULT_GATE_F_PREFLIGHT_RECEIPT,
    gate_f_handoff_receipt: str = DEFAULT_GATE_F_HANDOFF_RECEIPT,
    physical_device_preflight_receipt: str = DEFAULT_PHYSICAL_DEVICE_PREFLIGHT_RECEIPT,
    screenshot_file: str = "/tmp/agent-pocket-simulator-openai-provider-smoke-autocapture.png",
    picker_ui_screenshot_file: str = DEFAULT_SIMULATOR_PICKER_UI_SCREENSHOT,
    discovery_refresh_receipt_file: str = DEFAULT_SIMULATOR_DISCOVERY_REFRESH_RECEIPT,
    discovery_refresh_screenshot_file: str = DEFAULT_SIMULATOR_DISCOVERY_REFRESH_SCREENSHOT,
    capture_ready_receipt_file: str = DEFAULT_SIMULATOR_CAPTURE_READY_RECEIPT,
    capture_ready_screenshot_file: str = "/tmp/agent-pocket-simulator-capture-ready.png",
    capture_completed_receipt_file: str = DEFAULT_SIMULATOR_CAPTURE_COMPLETED_RECEIPT,
    capture_completed_screenshot_file: str = DEFAULT_SIMULATOR_CAPTURE_COMPLETED_SCREENSHOT,
    result_gallery_receipt_file: str = DEFAULT_SIMULATOR_RESULT_GALLERY_RECEIPT,
    result_gallery_screenshot_file: str = DEFAULT_SIMULATOR_RESULT_GALLERY_SCREENSHOT,
    result_gallery_downloaded_receipt_file: str = DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_RECEIPT,
    result_gallery_downloaded_screenshot_file: str = DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_SCREENSHOT,
    physical_openai_receipt: str = "docs/qa-receipts/openai-photo-flow.json",
    env: Optional[Mapping[str, str]] = None,
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
    provider_source_args: str = "",
) -> Mapping[str, Any]:
    env_values = _provider_visible_env(os.environ if env is None else env)
    runner = command_runner or _run_command
    tailscale = _build_tailscale_report(runner, env=env_values)
    provider_preflight = _audit_provider_preflight(root, provider_preflight_receipt)
    provider_env_sources = _audit_provider_env_sources(root, provider_env_sources_receipt)
    provider_env_sources_all_profiles = _audit_provider_env_sources(root, provider_env_sources_all_profiles_receipt)
    iphone_credential_boundary = _audit_iphone_credential_boundary(root, iphone_credential_boundary_receipt)
    openai_api_key_state = (
        "set"
        if env_values.get("OPENAI_API_KEY") or provider_preflight.get("ok") or provider_env_sources.get("ok")
        else "missing"
    )

    docs = _audit_files(
        root,
        [
            "docs/mobile-bridge-api.md",
            "docs/superpowers/specs/2026-05-30-agent-pocket-photo-mvp-design.md",
        ],
    )
    simulator_connection = _audit_receipt(root, simulator_connection_receipt, expected_phase="connection")
    fixture = _audit_receipt(root, fixture_receipt, expected_phase="photo-flow")
    script = _audit_receipt(root, script_receipt, expected_phase="photo-flow", expected_provider="script")
    openai = _audit_receipt(root, openai_receipt, expected_phase="photo-flow", expected_provider="openai")
    fake_openai = _audit_fake_openai_status(root, fake_openai_status_file)
    python_tests = _audit_test_receipt(root, python_test_receipt, expected_name="python")
    swift_tests = _audit_test_receipt(root, swift_test_receipt, expected_name="swift")
    simulator_ui_test_preflight = _audit_simulator_ui_test_preflight(
        root,
        simulator_ui_test_preflight_receipt,
    )
    simulator_suite = _audit_simulator_suite(root, simulator_suite_receipt)
    simulator_only_resume = _audit_simulator_only_resume(root, simulator_only_resume_receipt)
    gate_f_preflight = _audit_gate_f_preflight(root, gate_f_preflight_receipt)
    gate_f_handoff = _audit_gate_f_handoff(root, gate_f_handoff_receipt)
    physical_device_preflight = _audit_physical_device_preflight(root, physical_device_preflight_receipt)
    screenshot = _audit_simulator_screenshot(root, screenshot_file)
    picker_ui_screenshot = _audit_simulator_screenshot(root, picker_ui_screenshot_file)
    discovery_refresh = _audit_receipt(root, discovery_refresh_receipt_file, expected_phase="discovery-refresh")
    discovery_refresh_screenshot = _audit_simulator_screenshot(root, discovery_refresh_screenshot_file)
    capture_ready_receipt = _audit_capture_ready_receipt(root, capture_ready_receipt_file)
    capture_ready_screenshot = _audit_simulator_screenshot(root, capture_ready_screenshot_file)
    capture_completed_receipt = _audit_capture_completed_receipt(root, capture_completed_receipt_file)
    capture_completed_screenshot = _audit_simulator_screenshot(root, capture_completed_screenshot_file)
    result_gallery_receipt = _audit_result_gallery_receipt(root, result_gallery_receipt_file)
    result_gallery_screenshot = _audit_simulator_screenshot(root, result_gallery_screenshot_file)
    result_gallery_downloaded_receipt = _audit_result_gallery_downloaded_receipt(root, result_gallery_downloaded_receipt_file)
    result_gallery_downloaded_screenshot = _audit_simulator_screenshot(root, result_gallery_downloaded_screenshot_file)
    physical_openai = _audit_receipt(
        root,
        physical_openai_receipt,
        expected_phase="photo-flow",
        expected_provider="openai",
    )

    gate_a_missing = [item["path"] for item in docs if not item["exists"]]
    gate_b_missing = _receipt_missing(fixture) + _status_missing(python_tests)
    gate_c_missing = _status_missing(swift_tests)
    gate_d_missing = (
        _receipt_missing(simulator_connection)
        + _receipt_missing(fixture)
        + _receipt_missing(discovery_refresh)
        + _file_missing(discovery_refresh_screenshot)
        + _file_missing(picker_ui_screenshot)
        + _receipt_missing(capture_ready_receipt)
        + _file_missing(capture_ready_screenshot)
        + _receipt_missing(capture_completed_receipt)
        + _file_missing(capture_completed_screenshot)
    )
    gate_e_missing = (
        _receipt_missing(script)
        + _receipt_missing(openai)
        + _status_missing(fake_openai)
        + _receipt_missing(result_gallery_receipt)
        + _file_missing(result_gallery_screenshot)
        + _receipt_missing(result_gallery_downloaded_receipt)
        + _file_missing(result_gallery_downloaded_screenshot)
    )

    gate_f_missing: list[str] = []
    if not physical_openai["ok"]:
        gate_f_missing.append("real iPhone OpenAI photo-flow receipt")
    if openai_api_key_state == "missing":
        gate_f_missing.append("OPENAI_API_KEY")
    gate_f_endpoint = gate_f_preflight.get("endpoint", {})
    if not isinstance(gate_f_endpoint, Mapping):
        gate_f_endpoint = {}
    endpoint_evidence_ok = bool(tailscale.get("ok")) or bool(gate_f_endpoint.get("ok"))
    if not endpoint_evidence_ok:
        gate_f_missing.append("Tailscale endpoint evidence")
    if physical_device_preflight.get("exists") and not physical_device_preflight.get("ok"):
        for item in physical_device_preflight.get("missing", []):
            item_text = str(item)
            if item_text and item_text not in gate_f_missing:
                gate_f_missing.append(item_text)
    gate_f_preflight_host = str(gate_f_endpoint.get("host", "")).strip()
    gate_f_preflight_host_arg = f"--host {gate_f_preflight_host} " if gate_f_preflight_host else ""
    provider_source_args = provider_source_args.strip()
    provider_source_arg = f"{provider_source_args} " if provider_source_args else ""

    gates: dict[str, Mapping[str, Any]] = {
        "A": {
            "title": "Bridge API and engineering spec",
            "status": "passed" if not gate_a_missing else "missing_evidence",
            "evidence": docs,
            "missing": gate_a_missing,
        },
        "B": {
            "title": "Mock bridge tests and simulator fake task",
            "status": "passed" if not gate_b_missing else "needs_fresh_verification",
            "evidence": [fixture, python_tests],
            "missing": gate_b_missing,
            "fresh_verification": "PYTHONPATH=mock_bridge python3 -m pytest mock_bridge/tests photo-pack/tests ios/tests -q",
        },
        "C": {
            "title": "Swift core tests and connection parsing",
            "status": "passed" if not gate_c_missing else "needs_fresh_verification",
            "evidence": [swift_tests],
            "missing": gate_c_missing,
            "fresh_verification": "swift test",
        },
        "D": {
            "title": "SwiftUI simulator app fixture, PhotosPicker entry, and capture-ready photo flow",
            "status": "passed" if not gate_d_missing else "missing_evidence",
            "evidence": [
                simulator_connection,
                fixture,
                discovery_refresh,
                discovery_refresh_screenshot,
                picker_ui_screenshot,
                capture_ready_receipt,
                capture_ready_screenshot,
                capture_completed_receipt,
                capture_completed_screenshot,
            ],
            "missing": gate_d_missing,
        },
        "E": {
            "title": "Photo Pack adapter chain, downloadable result, and result review UI",
            "status": "passed" if not gate_e_missing else "missing_evidence",
            "evidence": [
                script,
                openai,
                fake_openai,
                screenshot,
                result_gallery_receipt,
                result_gallery_screenshot,
                result_gallery_downloaded_receipt,
                result_gallery_downloaded_screenshot,
            ],
            "missing": gate_e_missing,
        },
        "F": {
            "title": "Real Photo Pack adapter returns variants to a real iPhone",
            "status": "passed" if not gate_f_missing else "missing_external_evidence",
            "evidence": [physical_openai],
            "missing": gate_f_missing,
        },
    }
    simulator_evidence_ok = all(gates[name]["status"] == "passed" for name in ["A", "B", "D", "E"])
    gate_f_ok = gates["F"]["status"] == "passed"
    all_gates_closed = simulator_evidence_ok and gate_f_ok and gates["C"]["status"] == "passed"

    return {
        "ok": all_gates_closed,
        "mode": "simulator-only-audit",
        "summary": {
            "simulator_evidence_ok": simulator_evidence_ok,
            "gate_f_ok": gate_f_ok,
            "all_gates_closed": all_gates_closed,
            "remaining_external": gates["F"]["missing"],
        },
        "external": {
            "openai_api_key": openai_api_key_state,
            "tailscale": {
                **tailscale,
            },
            "physical_iphone": {
                "status": "requires_real_device_receipt",
                "receipt": physical_openai,
            },
            "provider_preflight": provider_preflight,
            "provider_env_sources": provider_env_sources,
            "provider_env_sources_all_profiles": provider_env_sources_all_profiles,
            "gate_f_preflight": gate_f_preflight,
            "gate_f_handoff": gate_f_handoff,
            "physical_device_preflight": physical_device_preflight,
        },
        "local": {
            "iphone_credential_boundary": iphone_credential_boundary,
            "simulator_ui_test_preflight": simulator_ui_test_preflight,
            "simulator_suite": simulator_suite,
            "simulator_only_resume": simulator_only_resume,
            "simulator_artifacts": {
                "simulator_connection_receipt": simulator_connection,
                "fixture_photo_flow_receipt": fixture,
                "discovery_refresh_receipt": discovery_refresh,
                "discovery_refresh_screenshot": discovery_refresh_screenshot,
                "picker_ui_screenshot": picker_ui_screenshot,
                "capture_ready_receipt": capture_ready_receipt,
                "capture_ready_screenshot": capture_ready_screenshot,
                "capture_completed_receipt": capture_completed_receipt,
                "capture_completed_screenshot": capture_completed_screenshot,
                "result_gallery_receipt": result_gallery_receipt,
                "result_gallery_screenshot": result_gallery_screenshot,
                "result_gallery_downloaded_receipt": result_gallery_downloaded_receipt,
                "result_gallery_downloaded_screenshot": result_gallery_downloaded_screenshot,
                "openai_photo_flow_receipt": openai,
                "fake_openai_status": fake_openai,
                "openai_screenshot": screenshot,
            },
        },
        "gates": gates,
        "commands": {
            "gate_audit": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa gate-audit "
                f"{provider_source_arg}"
            ).strip(),
            "gate_f_provider_check": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa gate-f-provider-check "
                f"{gate_f_preflight_host_arg}{provider_source_arg}"
            ).strip(),
            "gate_f_preflight": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa gate-f-preflight "
                f"{gate_f_preflight_host_arg}{provider_source_arg}"
                f"--receipt-file {gate_f_preflight_receipt}"
            ),
            "provider_env_sources": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa provider-env-sources "
                f"{provider_source_arg}"
                f"--receipt-file {provider_env_sources_receipt}"
            ),
            "provider_env_sources_all_profiles": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa provider-env-sources "
                f"--receipt-file {provider_env_sources_all_profiles_receipt}"
            ),
            "iphone_credential_boundary": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa iphone-credential-boundary "
                f"--receipt-file {iphone_credential_boundary_receipt}"
            ),
            "hermes_auth_add_openai": _hermes_auth_add_openai_command_from_source_args(provider_source_args),
            "hermes_openai_auth_import": (
                "OPENAI_API_KEY=<server-side-openai-api-key> "
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa hermes-openai-auth-import "
                f"{provider_source_arg}"
                f"--receipt-file {DEFAULT_HERMES_OPENAI_AUTH_IMPORT_RECEIPT}"
            ),
            "gate_f_handoff": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa gate-f-handoff "
                f"--simulator-only-resume-receipt {simulator_only_resume_receipt} "
                f"--gate-f-preflight-receipt {gate_f_preflight_receipt} "
                f"--receipt-file {gate_f_handoff_receipt}"
            ),
            "physical_device_preflight": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa physical-device-preflight "
                f"--build-check --receipt-file {physical_device_preflight_receipt}"
            ),
            "simulator_openai_smoke": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-openai-smoke "
                "--host 127.0.0.1 --port 8769 --fake-openai-port 8781 "
                f"--receipt-file {openai_receipt} "
                f"--fake-openai-status-file {fake_openai_status_file} "
                f"--screenshot-file {screenshot_file}"
            ),
            "simulator_connection_smoke": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-connection-smoke "
                "--host 127.0.0.1 --port 8766 "
                f"--receipt-file {simulator_connection_receipt}"
            ),
            "simulator_capture_ready_smoke": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-ready-smoke "
                "--bundle-id com.kaka.AgentPocket "
                "--screenshot-file /tmp/agent-pocket-simulator-capture-ready.png "
                f"--receipt-file {capture_ready_receipt_file}"
            ),
            "simulator_discovery_refresh_smoke": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-discovery-refresh-smoke "
                "--bundle-id com.kaka.AgentPocket "
                f"--receipt-file {discovery_refresh_receipt_file} "
                f"--screenshot-file {discovery_refresh_screenshot_file}"
            ),
            "simulator_capture_completed_smoke": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-capture-completed-smoke "
                "--bundle-id com.kaka.AgentPocket "
                f"--screenshot-file {capture_completed_screenshot_file} "
                f"--receipt-file {capture_completed_receipt_file}"
            ),
            "simulator_result_gallery_smoke": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-result-gallery-smoke "
                "--bundle-id com.kaka.AgentPocket "
                f"--screenshot-file {result_gallery_screenshot_file} "
                f"--receipt-file {result_gallery_receipt_file}"
            ),
            "simulator_result_gallery_downloaded_smoke": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-result-gallery-downloaded-smoke "
                "--bundle-id com.kaka.AgentPocket "
                f"--screenshot-file {result_gallery_downloaded_screenshot_file} "
                f"--receipt-file {result_gallery_downloaded_receipt_file}"
            ),
            "simulator_picker_ui_smoke": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-picker-ui-smoke "
                "--bundle-id com.kaka.AgentPocket "
                f"--screenshot-file {DEFAULT_SIMULATOR_PICKER_UI_SCREENSHOT}"
            ),
            "simulator_ui_test_preflight": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-ui-test-preflight "
                f"--receipt-file {simulator_ui_test_preflight_receipt}"
            ),
            "simulator_suite": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-suite "
                f"--suite-receipt-file {simulator_suite_receipt}"
            ),
            "simulator_only_resume": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-only-resume "
                f"--suite-receipt-file {simulator_suite_receipt} "
                f"--gate-f-preflight-receipt {gate_f_preflight_receipt} "
                f"{('--gate-f-host ' + gate_f_preflight_host + ' ') if gate_f_preflight_host else ''}"
                f"{provider_source_arg}"
                f"--resume-receipt-file {DEFAULT_SIMULATOR_ONLY_RESUME_RECEIPT} "
                "--readiness-output-file docs/agent-pocket-readiness.md"
            ),
            "simulator_seed_photo_library": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-seed-photo-library "
                f"--image-file {DEFAULT_SIMULATOR_LIBRARY_FIXTURE}"
            ),
            "python_tests": "PYTHONPATH=mock_bridge python3 -m pytest mock_bridge/tests photo-pack/tests ios/tests -q",
            "python_test_receipt": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa test-receipt "
                f"--name python --receipt-file {python_test_receipt} -- "
                "python3 -m pytest mock_bridge/tests photo-pack/tests ios/tests -q"
            ),
            "swift_tests": "swift test",
            "swift_test_receipt": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa test-receipt "
                f"--name swift --receipt-file {swift_test_receipt} -- "
                "swift test"
            ),
            "gate_f_real_iphone": (
                "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan "
                "--host <mac-ip-or-tailscale-ip> --device-id <coredevice-id> "
                f"--photo-provider openai {provider_source_arg}"
                "--receipt-file "
                f"{physical_openai_receipt}"
            ),
        },
    }


def build_gate_f_preflight_report(
    root: str = ".",
    port: int = 8765,
    bundle_id: str = DEFAULT_BUNDLE_ID,
    photo_pack_root: str = "photo-pack",
    physical_openai_receipt: str = "docs/qa-receipts/openai-photo-flow.json",
    provider_preflight_receipt: str = DEFAULT_OPENAI_PROVIDER_PREFLIGHT_RECEIPT,
    provider_env_sources_receipt: str = DEFAULT_PROVIDER_ENV_SOURCES_RECEIPT,
    physical_device_preflight_receipt: str = DEFAULT_PHYSICAL_DEVICE_PREFLIGHT_RECEIPT,
    env: Optional[Mapping[str, str]] = None,
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
    host: str = "",
    env_file: str = "",
    provider_source_args: str = "",
) -> Mapping[str, Any]:
    env_values = _provider_visible_env(os.environ if env is None else env)
    runner = command_runner or _run_command
    tailscale = _build_tailscale_report(runner, env=env_values)
    tailscale_ip = str(tailscale.get("ip", ""))
    tailscale_ready = bool(tailscale.get("ok"))
    explicit_host = host.strip()
    endpoint_host = explicit_host or tailscale_ip
    endpoint_source = "explicit_host" if explicit_host else ("tailscale" if tailscale_ready else "")
    endpoint = {
        "ok": bool(endpoint_host),
        "source": endpoint_source,
        "host": endpoint_host,
        "missing": [] if endpoint_host else ["Tailscale endpoint evidence"],
    }
    provider_preflight = _audit_provider_preflight(root, provider_preflight_receipt)
    provider_env_sources = _audit_provider_env_sources(root, provider_env_sources_receipt)
    openai_key_from_env = bool(env_values.get("OPENAI_API_KEY"))
    openai_key_from_provider_receipt = bool(provider_preflight.get("ok"))
    openai_key_from_env_sources = bool(provider_env_sources.get("ok"))
    openai_key_state = (
        "set"
        if openai_key_from_env or openai_key_from_provider_receipt or openai_key_from_env_sources
        else "missing"
    )
    openai_key_evidence = ""
    if openai_key_from_env:
        openai_key_evidence = "environment"
    elif openai_key_from_provider_receipt:
        openai_key_evidence = "provider_preflight_receipt"
    elif openai_key_from_env_sources:
        openai_key_evidence = "provider_env_sources_receipt"
    provider_env = dict(env_values)
    if openai_key_from_provider_receipt and not openai_key_from_env:
        provider_env["OPENAI_API_KEY"] = "provider-preflight-receipt"
    provider = build_provider_preflight_report(
        "openai",
        photo_pack_root=_resolve_audit_path(root, photo_pack_root),
        env=provider_env,
    )
    receipt = _audit_receipt(
        root,
        physical_openai_receipt,
        expected_phase="photo-flow",
        expected_provider="openai",
    )
    physical_device_preflight = _audit_physical_device_preflight(root, physical_device_preflight_receipt)
    physical_device = physical_device_preflight.get("device", {})
    if not isinstance(physical_device, Mapping):
        physical_device = {}
    device_id = str(physical_device.get("id", "")).strip() or "<coredevice-id>"
    provider_source_args = provider_source_args.strip() or _provider_source_command_args(env_file=env_file)
    provider_source_arg = f"{provider_source_args} " if provider_source_args else ""
    provider = _with_provider_command_source_args(provider, provider_source_args)
    provider_env_prefix = "" if provider_source_args else "OPENAI_API_KEY=<set-in-hermes-process> "
    server_env = {
        "env_file": env_file,
        "openai_api_key": openai_key_state,
        "key_evidence": openai_key_evidence,
        "provider_source_args": provider_source_args,
    }

    missing_to_start: list[str] = []
    if openai_key_state == "missing":
        missing_to_start.append("OPENAI_API_KEY")
    if not provider.get("adapter", {}).get("exists"):
        missing_to_start.append("OpenAI Photo Pack adapter")
    if not endpoint.get("ok"):
        missing_to_start.append("Tailscale endpoint evidence")

    missing_to_close: list[str] = []
    if not receipt.get("ok"):
        missing_to_close.append("real iPhone OpenAI photo-flow receipt")

    run_host = endpoint_host or "<mac-tailscale-ip>"
    run_command = (
        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan "
        f"--host {run_host} --port {port} --device-id {device_id} "
        f"--bundle-id {bundle_id} --no-bonjour --photo-provider openai "
        f"{provider_source_arg}"
        f"--receipt-file {physical_openai_receipt}"
    )
    verify_command = (
        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa verify-receipt "
        f"--file {physical_openai_receipt} --phase photo-flow --photo-provider openai"
    )
    resume_host_arg = f"--host {explicit_host} " if explicit_host else ""
    resume_command = (
        "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa gate-f-resume "
        f"{resume_host_arg}--port {port} --device-id {device_id} --bundle-id {bundle_id} "
        f"{provider_source_arg}"
        f"--gate-f-preflight-receipt {DEFAULT_GATE_F_PREFLIGHT_RECEIPT} "
        f"--physical-openai-receipt {physical_openai_receipt}"
    )
    checks = {
        "openai_api_key": openai_key_state,
        "openai_provider": provider,
        "tailscale": {
            **tailscale,
        },
        "endpoint": endpoint,
        "server_env": server_env,
        "provider_preflight_receipt": provider_preflight,
        "provider_env_sources_receipt": provider_env_sources,
        "physical_openai_receipt": receipt,
        "physical_device_preflight": physical_device_preflight,
    }
    commands = {
        "provider_preflight": (
            f"{provider_env_prefix}PYTHONPATH=mock_bridge "
            "python3 -m agent_pocket_mock_bridge.qa provider-preflight "
            f"--photo-provider openai --photo-pack-root {photo_pack_root} "
            f"{provider_source_arg}"
            f"--receipt-file {DEFAULT_OPENAI_PROVIDER_PREFLIGHT_RECEIPT}"
        ),
        "provider_env_sources": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa provider-env-sources "
            f"{provider_source_arg}"
            f"--receipt-file {DEFAULT_PROVIDER_ENV_SOURCES_RECEIPT}"
        ),
        "hermes_auth_add_openai": _hermes_auth_add_openai_command_from_source_args(provider_source_args),
        "hermes_openai_auth_import": (
            "OPENAI_API_KEY=<server-side-openai-api-key> "
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa hermes-openai-auth-import "
            f"{provider_source_arg}"
            f"--receipt-file {DEFAULT_HERMES_OPENAI_AUTH_IMPORT_RECEIPT}"
        ),
        "run_real_iphone_openai": run_command,
        "verify_real_iphone_openai": verify_command,
        "gate_f_resume": resume_command,
        "readiness_report": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa readiness-report "
            f"{provider_source_arg}"
            "--output-file docs/agent-pocket-readiness.md"
        ),
    }
    diagnostic_preflight = {
        "checks": checks,
        "commands": commands,
    }

    return {
        "ok": not missing_to_start and not missing_to_close,
        "ready_to_run": not missing_to_start,
        "missing_to_start": missing_to_start,
        "missing_to_close": missing_to_close,
        "start_blockers": _gate_f_start_blockers(missing_to_start, diagnostic_preflight),
        "server_diagnostics": _gate_f_server_diagnostics(diagnostic_preflight),
        "checks": checks,
        "commands": commands,
    }


def _gate_f_start_blockers(
    missing_to_start: Sequence[str],
    preflight: Mapping[str, Any],
) -> list[dict[str, Any]]:
    commands = preflight.get("commands", {})
    if not isinstance(commands, Mapping):
        commands = {}
    blockers: list[dict[str, Any]] = []
    for item in missing_to_start:
        if item == "OPENAI_API_KEY":
            auth_command = str(commands.get("hermes_auth_add_openai", "")).strip()
            if auth_command:
                next_action = (
                    "Add the OpenAI Images API key with hermes_auth_add_openai, "
                    "then rerun provider_preflight."
                )
            else:
                next_action = (
                    "Run provider_preflight from the Hermes/mock bridge process that performs the edit, "
                    "or add OPENAI_API_KEY to the selected server-side Hermes/profile env source."
                )
            blockers.append({
                "missing": "OPENAI_API_KEY",
                "label": "server-side OpenAI key proof (Hermes/provider runtime)",
                "scope": "Hermes/mock bridge server process",
                "iphone_required": False,
                "message": (
                    "Pocket Agent on iPhone never stores or calls OPENAI_API_KEY; "
                    "the runtime that performs the photo edit must prove it can read the key."
                ),
                "next_action": next_action,
                "remediation_command": auth_command,
                "evidence_command": str(commands.get("provider_preflight", "")),
            })
        elif item == "OpenAI Photo Pack adapter":
            blockers.append({
                "missing": "OpenAI Photo Pack adapter",
                "label": "OpenAI Photo Pack adapter",
                "scope": "Mac workspace",
                "iphone_required": False,
                "message": "The server-side OpenAI adapter file must exist before a real provider run can start.",
                "next_action": "Restore the OpenAI Photo Pack adapter and rerun gate_f_preflight.",
                "evidence_command": "",
            })
        elif item == "Tailscale endpoint evidence":
            blockers.append({
                "missing": "Tailscale endpoint evidence",
                "label": "reachable Mac endpoint",
                "scope": "Mac network endpoint",
                "iphone_required": False,
                "message": "The iPhone needs a reachable Hermes/mock-bridge endpoint, but no provider key belongs on iPhone.",
                "next_action": "Provide a reachable Mac LAN host or Tailscale endpoint, then rerun gate_f_preflight.",
                "evidence_command": str(commands.get("gate_f_resume", "")),
            })
        else:
            blockers.append({
                "missing": str(item),
                "label": str(item),
                "scope": "external preflight",
                "iphone_required": False,
                "message": "Resolve this Gate F start condition before launching the real iPhone flow.",
                "next_action": "Rerun gate_f_preflight after addressing this start blocker.",
                "evidence_command": "",
            })
    return blockers


def _gate_f_server_diagnostics(preflight: Mapping[str, Any]) -> dict[str, Any]:
    checks = preflight.get("checks", {})
    if not isinstance(checks, Mapping):
        checks = {}
    provider_preflight = checks.get("provider_preflight_receipt", {})
    if not isinstance(provider_preflight, Mapping):
        provider_preflight = {}
    provider_env_sources = checks.get("provider_env_sources_receipt", {})
    if not isinstance(provider_env_sources, Mapping):
        provider_env_sources = {}
    hermes_sources = provider_env_sources.get("hermes", {})
    if not isinstance(hermes_sources, Mapping):
        hermes_sources = {}
    server_env = checks.get("server_env", {})
    if not isinstance(server_env, Mapping):
        server_env = {}
    openai_provider = checks.get("openai_provider", {})
    if not isinstance(openai_provider, Mapping):
        openai_provider = {}

    def selected_items(items: Any) -> list[dict[str, Any]]:
        if not isinstance(items, (list, tuple)):
            return []
        selected: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, Mapping) and item.get("selected"):
                selected.append(dict(item))
        return selected

    provider_config = openai_provider.get("config", {})
    if not isinstance(provider_config, Mapping):
        provider_config = {}
    return {
        "server_env": {
            "openai_api_key": str(server_env.get("openai_api_key", "")),
            "key_evidence": str(server_env.get("key_evidence", "")),
            "provider_source_args": str(server_env.get("provider_source_args", "")),
        },
        "openai_provider": {
            "ok": bool(openai_provider.get("ok")),
            "env": dict(openai_provider.get("env", {})) if isinstance(openai_provider.get("env"), Mapping) else {},
            "config": dict(provider_config),
        },
        "provider_preflight_receipt": {
            "exists": bool(provider_preflight.get("exists")),
            "ok": bool(provider_preflight.get("ok")),
            "status": str(provider_preflight.get("status", "")),
            "env": dict(provider_preflight.get("env", {})) if isinstance(provider_preflight.get("env"), Mapping) else {},
            "config": dict(provider_preflight.get("config", {})) if isinstance(provider_preflight.get("config"), Mapping) else {},
        },
        "provider_env_sources_receipt": {
            "exists": bool(provider_env_sources.get("exists")),
            "ok": bool(provider_env_sources.get("ok")),
            "status": str(provider_env_sources.get("status", "")),
            "selected_profile_state": str(hermes_sources.get("selected_profile_state", "")),
            "selected_gateway_processes": selected_items(hermes_sources.get("gateway_processes", [])),
            "selected_processes": selected_items(hermes_sources.get("processes", [])),
            "selected_provider_references": selected_items(hermes_sources.get("provider_references", [])),
        },
    }


def build_gate_f_handoff_report(
    root: str = ".",
    simulator_only_resume_receipt: str = DEFAULT_SIMULATOR_ONLY_RESUME_RECEIPT,
    gate_f_preflight_receipt: str = DEFAULT_GATE_F_PREFLIGHT_RECEIPT,
) -> Mapping[str, Any]:
    simulator_resume = _audit_simulator_only_resume(root, simulator_only_resume_receipt)
    gate_f_preflight = _audit_gate_f_preflight(root, gate_f_preflight_receipt)

    remaining_to_start = list(gate_f_preflight.get("missing_to_start", []))
    remaining_to_close = list(gate_f_preflight.get("missing_to_close", []))
    commands = gate_f_preflight.get("commands", {})
    if not isinstance(commands, Mapping):
        commands = {}
    endpoint = gate_f_preflight.get("endpoint", {})
    if not isinstance(endpoint, Mapping):
        endpoint = {}
    stored_start_blockers = gate_f_preflight.get("start_blockers", [])
    if not isinstance(stored_start_blockers, list):
        stored_start_blockers = []
    handoff_start_blockers = [
        dict(item) for item in stored_start_blockers if isinstance(item, Mapping)
    ] or _gate_f_start_blockers(remaining_to_start, gate_f_preflight)
    hermes_openai_auth_command = str(commands.get("hermes_auth_add_openai", "")).strip()
    if hermes_openai_auth_command:
        for blocker in handoff_start_blockers:
            if (
                blocker.get("missing") == "OPENAI_API_KEY"
                and not str(blocker.get("remediation_command", "")).strip()
            ):
                blocker["remediation_command"] = hermes_openai_auth_command
    stored_server_diagnostics = gate_f_preflight.get("server_diagnostics", {})
    if not isinstance(stored_server_diagnostics, Mapping):
        stored_server_diagnostics = {}
    handoff_server_diagnostics = (
        dict(stored_server_diagnostics)
        if stored_server_diagnostics
        else _gate_f_server_diagnostics(gate_f_preflight)
    )

    local_handoff_ready = bool(simulator_resume.get("ok")) and bool(gate_f_preflight.get("exists"))
    gate_f_closed = bool(gate_f_preflight.get("ok"))
    gate_f_ready_to_run = bool(gate_f_preflight.get("ready_to_run"))
    if gate_f_closed:
        status = "gate_f_closed"
    elif local_handoff_ready and gate_f_ready_to_run:
        status = "handoff_ready_for_real_iphone"
    elif local_handoff_ready:
        status = "handoff_ready_with_external_blockers"
    else:
        status = "missing_local_evidence"

    next_actions: list[str] = []
    if not simulator_resume.get("ok"):
        next_actions.append("Refresh local Simulator evidence with simulator_only_resume.")
    if not gate_f_preflight.get("exists"):
        next_actions.append("Refresh Gate F preflight with gate_f_preflight.")
    if "OPENAI_API_KEY" in remaining_to_start:
        if commands.get("hermes_auth_add_openai"):
            next_actions.append("Add the OpenAI Images API key with hermes_auth_add_openai, then rerun provider_preflight.")
        else:
            next_actions.append(
                "Confirm OPENAI_API_KEY is available to the Hermes/mock bridge process and rerun provider_preflight."
            )
    if "OpenAI Photo Pack adapter" in remaining_to_start:
        next_actions.append("Restore the OpenAI Photo Pack adapter and rerun gate_f_preflight.")
    if "Tailscale endpoint evidence" in remaining_to_start:
        next_actions.append("Provide a reachable Mac host or Tailscale endpoint, then rerun gate_f_preflight.")
    if "real iPhone OpenAI photo-flow receipt" in remaining_to_close:
        next_actions.append("When the physical iPhone is available again, run gate_f_resume.")
    if not next_actions and gate_f_closed:
        next_actions.append("Gate F is already closed by the real iPhone OpenAI receipt.")

    return {
        "phase": "gate-f-handoff",
        "ok": local_handoff_ready,
        "status": status,
        "gate_f_closed": gate_f_closed,
        "gate_f_ready_to_run": gate_f_ready_to_run,
        "execution_mode": "local-mac-simulator-only",
        "safe_without_physical_iphone": True,
        "physical_iphone_used": False,
        "physical_device_launch_attempted": False,
        "real_device_commands_executed": [],
        "remaining_to_start": [str(item) for item in remaining_to_start],
        "remaining_to_close": [str(item) for item in remaining_to_close],
        "start_blockers": handoff_start_blockers,
        "server_diagnostics": handoff_server_diagnostics,
        "endpoint": {
            "ok": bool(endpoint.get("ok")),
            "source": str(endpoint.get("source", "")),
            "host": str(endpoint.get("host", "")),
            "missing": [str(item) for item in endpoint.get("missing", [])]
            if isinstance(endpoint.get("missing", []), list)
            else [],
        } if endpoint else {},
        "local_simulator_resume": simulator_resume,
        "gate_f_preflight": gate_f_preflight,
        "commands": {
            str(key): str(value)
            for key, value in commands.items()
            if key in [
                "provider_preflight",
                "hermes_auth_add_openai",
                "hermes_openai_auth_import",
                "run_real_iphone_openai",
                "verify_real_iphone_openai",
                "gate_f_resume",
            ]
        },
        "next_actions": next_actions,
    }


def run_gate_f_provider_check(
    root: str = ".",
    host: str = "",
    port: int = 8765,
    bundle_id: str = DEFAULT_BUNDLE_ID,
    photo_pack_root: str = "photo-pack",
    physical_openai_receipt: str = "docs/qa-receipts/openai-photo-flow.json",
    provider_preflight_receipt: str = DEFAULT_OPENAI_PROVIDER_PREFLIGHT_RECEIPT,
    provider_env_sources_receipt: str = DEFAULT_PROVIDER_ENV_SOURCES_RECEIPT,
    provider_env_sources_all_profiles_receipt: str = DEFAULT_PROVIDER_ENV_SOURCES_ALL_PROFILES_RECEIPT,
    gate_f_preflight_receipt: str = DEFAULT_GATE_F_PREFLIGHT_RECEIPT,
    readiness_output_file: str = "docs/agent-pocket-readiness.md",
    env_file: str = "",
    hermes_home: str = "",
    hermes_profile: str = "",
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
) -> Mapping[str, Any]:
    provider_source_args = _provider_source_command_args(
        env_file=env_file,
        hermes_home=hermes_home,
        hermes_profile=hermes_profile,
    )
    env_values, effective_env_file, hermes_context = _provider_env_from_sources(
        env_file=env_file,
        hermes_home=hermes_home,
        hermes_profile=hermes_profile,
    )

    provider_env_sources = build_provider_env_sources_report(
        env_file=env_file,
        hermes_home=hermes_home,
        hermes_profile=hermes_profile,
        env=env_values,
        command_runner=command_runner,
        include_hermes_cli_auth=True,
    )
    _write_receipt(provider_env_sources_receipt, provider_env_sources)

    provider_env_sources_all_profiles = build_provider_env_sources_report(
        hermes_home=hermes_home,
        command_runner=command_runner,
        include_hermes_cli_auth=True,
    )
    _write_receipt(provider_env_sources_all_profiles_receipt, provider_env_sources_all_profiles)

    provider_preflight = build_provider_preflight_report(
        provider="openai",
        photo_pack_root=photo_pack_root,
        env=env_values,
    )
    provider_preflight = _with_provider_command_source_args(
        provider_preflight,
        provider_source_args or _provider_source_command_args(env_file=effective_env_file),
    )
    if hermes_context:
        provider_preflight = {**provider_preflight, "hermes": hermes_context}
    _write_receipt(provider_preflight_receipt, provider_preflight)

    gate_f_preflight = build_gate_f_preflight_report(
        root=root,
        port=port,
        bundle_id=bundle_id,
        photo_pack_root=photo_pack_root,
        physical_openai_receipt=physical_openai_receipt,
        provider_preflight_receipt=provider_preflight_receipt,
        provider_env_sources_receipt=provider_env_sources_receipt,
        host=host,
        env=env_values,
        env_file=effective_env_file,
        provider_source_args=provider_source_args,
        command_runner=command_runner,
    )
    _write_receipt(gate_f_preflight_receipt, gate_f_preflight)

    gate_audit = build_gate_audit_report(
        root=root,
        provider_preflight_receipt=provider_preflight_receipt,
        provider_env_sources_receipt=provider_env_sources_receipt,
        provider_env_sources_all_profiles_receipt=provider_env_sources_all_profiles_receipt,
        gate_f_preflight_receipt=gate_f_preflight_receipt,
        physical_openai_receipt=physical_openai_receipt,
        env=env_values,
        command_runner=command_runner,
        provider_source_args=provider_source_args,
    )
    readiness_markdown = build_readiness_markdown(gate_audit)
    if readiness_output_file:
        parent = os.path.dirname(readiness_output_file)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(readiness_output_file, "w", encoding="utf-8") as handle:
            handle.write(readiness_markdown)

    ready_to_run = bool(gate_f_preflight.get("ready_to_run"))
    provider_ready = bool(provider_preflight.get("ok"))
    start_blockers = _gate_f_start_blockers(
        list(gate_f_preflight.get("missing_to_start", [])),
        gate_f_preflight,
    )
    next_actions = [
        str(blocker.get("next_action", ""))
        for blocker in start_blockers
        if isinstance(blocker, Mapping) and str(blocker.get("next_action", "")).strip()
    ]
    if ready_to_run and gate_f_preflight.get("commands", {}).get("gate_f_resume"):
        next_actions.append("Run gate_f_resume to execute and verify the real iPhone OpenAI photo flow.")

    return {
        "ok": ready_to_run and provider_ready,
        "phase": "gate-f-provider-check",
        "status": "ready_to_run" if ready_to_run and provider_ready else "blocked_to_start",
        "ready_to_run": ready_to_run,
        "provider_ready": provider_ready,
        "provider_source": {
            "args": provider_source_args,
            "env_file": effective_env_file,
            "hermes": {
                "home": os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home())),
                "profile": hermes_profile.strip(),
            } if hermes_home.strip() or hermes_profile.strip() else {},
        },
        "receipts": {
            "provider_env_sources": provider_env_sources_receipt,
            "provider_env_sources_all_profiles": provider_env_sources_all_profiles_receipt,
            "provider_preflight": provider_preflight_receipt,
            "gate_f_preflight": gate_f_preflight_receipt,
            "readiness_report": readiness_output_file,
        },
        "provider_env_sources": {
            "ok": bool(provider_env_sources.get("ok")),
            "env": dict(provider_env_sources.get("env", {})) if isinstance(provider_env_sources.get("env"), Mapping) else {},
            "missing": [str(item) for item in provider_env_sources.get("missing", [])]
            if isinstance(provider_env_sources.get("missing", []), list)
            else [],
        },
        "provider_env_sources_all_profiles": {
            "ok": bool(provider_env_sources_all_profiles.get("ok")),
            "env": dict(provider_env_sources_all_profiles.get("env", {}))
            if isinstance(provider_env_sources_all_profiles.get("env"), Mapping)
            else {},
            "set_sources": [
                {
                    "source": str(source.get("source", "")),
                    "profile": str(source.get("profile", "")),
                    "path": str(source.get("path", "")),
                    "pid": str(source.get("pid", "")),
                }
                for source in provider_env_sources_all_profiles.get("set_sources", [])
                if isinstance(source, Mapping)
            ],
        },
        "provider_preflight": {
            "ok": provider_ready,
            "env": dict(provider_preflight.get("env", {})) if isinstance(provider_preflight.get("env"), Mapping) else {},
            "missing": [str(item) for item in provider_preflight.get("missing", [])]
            if isinstance(provider_preflight.get("missing", []), list)
            else [],
        },
        "gate_f_preflight": {
            "ok": bool(gate_f_preflight.get("ok")),
            "ready_to_run": ready_to_run,
            "missing_to_start": [str(item) for item in gate_f_preflight.get("missing_to_start", [])]
            if isinstance(gate_f_preflight.get("missing_to_start", []), list)
            else [],
            "missing_to_close": [str(item) for item in gate_f_preflight.get("missing_to_close", [])]
            if isinstance(gate_f_preflight.get("missing_to_close", []), list)
            else [],
            "endpoint": dict(gate_f_preflight.get("checks", {}).get("endpoint", {}))
            if isinstance(gate_f_preflight.get("checks"), Mapping)
            and isinstance(gate_f_preflight.get("checks", {}).get("endpoint"), Mapping)
            else {},
        },
        "commands": {
            str(key): str(value)
            for key, value in (gate_f_preflight.get("commands", {}) if isinstance(gate_f_preflight.get("commands"), Mapping) else {}).items()
            if key in {
                "provider_preflight",
                "provider_env_sources",
                "hermes_auth_add_openai",
                "hermes_openai_auth_import",
                "run_real_iphone_openai",
                "verify_real_iphone_openai",
                "gate_f_resume",
            }
        },
        "next_actions": next_actions,
    }


def run_gate_f_resume(
    root: str = ".",
    port: int = 8765,
    device_id: str = "",
    bundle_id: str = DEFAULT_BUNDLE_ID,
    token: str = DEFAULT_TOKEN,
    connection_timeout: float = 45,
    photo_timeout: float = 180,
    interval: float = 1.0,
    photo_pack_root: str = "photo-pack",
    gate_f_preflight_receipt: str = DEFAULT_GATE_F_PREFLIGHT_RECEIPT,
    physical_openai_receipt: str = "docs/qa-receipts/openai-photo-flow.json",
    host: str = "",
    env: Optional[Mapping[str, str]] = None,
    env_file: str = "",
    provider_source_args: str = "",
) -> Mapping[str, Any]:
    env_values = _env_with_file(env, env_file)
    env_overlay = _provider_visible_env(_parse_env_file(env_file))
    if env is not None:
        env_overlay.update(_provider_visible_env(dict(env)))
    effective_provider_source_args = provider_source_args.strip() or _provider_source_command_args(env_file=env_file)
    provider_source: dict[str, Any] = {
        "args": effective_provider_source_args,
        "env_file": os.path.abspath(os.path.expanduser(env_file)) if env_file else "",
    }
    source_hermes_home = _provider_source_arg_value(effective_provider_source_args, "--hermes-home")
    source_hermes_profile = _provider_source_arg_value(effective_provider_source_args, "--hermes-profile")
    if source_hermes_home or source_hermes_profile:
        provider_source["hermes"] = {
            "home": os.path.abspath(os.path.expanduser(source_hermes_home or _default_hermes_home())),
            "profile": source_hermes_profile,
        }
    preflight = build_gate_f_preflight_report(
        root=root,
        port=port,
        bundle_id=bundle_id,
        photo_pack_root=photo_pack_root,
        physical_openai_receipt=physical_openai_receipt,
        host=host,
        env=env_values,
        env_file=env_file,
        provider_source_args=provider_source_args,
    )
    _write_receipt(gate_f_preflight_receipt, preflight)

    checks = preflight.get("checks")
    tailscale = checks.get("tailscale") if isinstance(checks, Mapping) else {}
    if not isinstance(tailscale, Mapping):
        tailscale = {}
    resolved_host = host or str(tailscale.get("ip", ""))
    missing_to_start = list(preflight.get("missing_to_start", []))
    missing_to_close = list(preflight.get("missing_to_close", []))
    endpoint_evidence = "explicit_host" if host else ("tailscale" if resolved_host else "")
    if host:
        missing_to_start = [
            item for item in missing_to_start
            if item != "Tailscale endpoint evidence"
        ]

    if missing_to_start or not resolved_host:
        if not resolved_host and "Tailscale endpoint evidence" not in missing_to_start:
            missing_to_start.append("Tailscale endpoint evidence")
        start_blockers = _gate_f_start_blockers(missing_to_start, preflight)
        commands = preflight.get("commands", {})
        if not isinstance(commands, Mapping):
            commands = {}
        next_actions = [
            str(blocker.get("next_action", ""))
            for blocker in start_blockers
            if isinstance(blocker, Mapping) and str(blocker.get("next_action", "")).strip()
        ]
        return {
            "ok": False,
            "phase": "gate-f-resume",
            "status": "blocked_to_start",
            "host": resolved_host,
            "endpoint_evidence": endpoint_evidence,
            "provider_source": provider_source,
            "launched": False,
            "verified": False,
            "missing_to_start": missing_to_start,
            "missing_to_close": missing_to_close,
            "start_blockers": start_blockers,
            "server_diagnostics": _gate_f_server_diagnostics(preflight),
            "commands": {
                str(key): str(value)
                for key, value in commands.items()
                if key in {
                    "provider_preflight",
                    "provider_env_sources",
                    "hermes_auth_add_openai",
                    "hermes_openai_auth_import",
                    "gate_f_resume",
                }
            },
            "next_actions": next_actions,
            "gate_f_preflight": {
                "path": gate_f_preflight_receipt,
                "ready_to_run": bool(preflight.get("ready_to_run")),
            },
            "physical_openai_receipt": physical_openai_receipt,
        }

    with _temporary_environ(env_overlay):
        run_code = run_lan_qa_session(
            host=resolved_host,
            port=port,
            device_id=device_id,
            bundle_id=bundle_id,
            token=token,
            connection_timeout=connection_timeout,
            photo_timeout=photo_timeout,
            interval=interval,
            launch_app=True,
            connection_only=False,
            advertise_bonjour=False,
            photo_provider="openai",
            photo_pack_root=photo_pack_root,
            receipt_file=physical_openai_receipt,
        )
    if run_code != 0:
        return {
            "ok": False,
            "phase": "gate-f-resume",
            "status": "run_failed",
            "host": resolved_host,
            "endpoint_evidence": endpoint_evidence,
            "provider_source": provider_source,
            "launched": True,
            "verified": False,
            "run_returncode": run_code,
            "missing_to_start": [],
            "missing_to_close": missing_to_close,
            "gate_f_preflight": {
                "path": gate_f_preflight_receipt,
                "ready_to_run": True,
            },
            "physical_openai_receipt": physical_openai_receipt,
        }

    try:
        with open(physical_openai_receipt, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        verification = {
            "ok": False,
            "phase": "photo-flow",
            "missing": [f"readable receipt JSON: {error}"],
        }
    else:
        result = verify_receipt_payload(
            receipt,
            expected_phase="photo-flow",
            expected_provider="openai",
        )
        verification = {
            "ok": result.ok,
            "phase": "photo-flow",
            "missing": result.missing,
        }

    return {
        "ok": bool(verification.get("ok")),
        "phase": "gate-f-resume",
        "status": "verified" if verification.get("ok") else "verification_failed",
        "host": resolved_host,
        "endpoint_evidence": endpoint_evidence,
        "provider_source": provider_source,
        "launched": True,
        "verified": bool(verification.get("ok")),
        "run_returncode": run_code,
        "missing_to_start": [],
        "missing_to_close": [] if verification.get("ok") else missing_to_close,
        "gate_f_preflight": {
            "path": gate_f_preflight_receipt,
            "ready_to_run": True,
        },
        "physical_openai_receipt": physical_openai_receipt,
        "verification": verification,
    }


def _human_evidence_label(item: str) -> str:
    if item == "OPENAI_API_KEY":
        return "server-side OpenAI key proof (Hermes/provider runtime)"
    return item


def _human_evidence_values(values: Sequence[Any]) -> list[str]:
    return [_human_evidence_label(str(item)) for item in values]


def _hermes_auth_add_openai_command(hermes_home: str = "", hermes_profile: str = "") -> str:
    prefix = f"HERMES_HOME={hermes_home.strip()} " if hermes_home.strip() else ""
    profile_arg = f"--profile {hermes_profile.strip()} " if hermes_profile.strip() else ""
    return (
        f"{prefix}hermes {profile_arg}auth add openai "
        "--type api-key --label agent-pocket-openai-images"
    )


def _readiness_probe_status(probe: Mapping[str, Any]) -> tuple[str, str]:
    path = str(probe.get("path", ""))
    if probe.get("ok"):
        return "ready", path
    if not probe.get("exists"):
        return "missing", path

    details: list[str] = []
    missing = probe.get("missing", [])
    if isinstance(missing, Sequence) and not isinstance(missing, (str, bytes)):
        missing_values = [str(item) for item in missing if str(item)]
        if missing_values:
            details.append(f"missing {', '.join(missing_values)}")
    status = str(probe.get("status", ""))
    if status and not details:
        details.append(status.replace("_", " "))
    if details:
        if path:
            return "failed", f"{path}; {'; '.join(details)}"
        return "failed", "; ".join(details)
    return "failed", path


def build_readiness_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary", {})
    gates = report.get("gates", {})
    external = report.get("external", {})
    local = report.get("local", {})
    commands = report.get("commands", {})
    remaining_external = list(summary.get("remaining_external", []))
    local_gate_names = ["A", "B", "C", "D", "E"]
    proven_local_gates = [
        gate_name
        for gate_name in local_gate_names
        if gates.get(gate_name, {}).get("status") == "passed"
    ]
    gate_f_preflight = external.get("gate_f_preflight")
    required_external_evidence = [str(item) for item in remaining_external]
    if isinstance(gate_f_preflight, Mapping):
        for key in ["missing_to_start", "missing_to_close"]:
            values = gate_f_preflight.get(key, [])
            if isinstance(values, (list, tuple)):
                for value in values:
                    item = str(value)
                    if item not in required_external_evidence:
                        required_external_evidence.append(item)

    def format_list(values: Sequence[str]) -> str:
        if not values:
            return "none"
        labels = _human_evidence_values(values)
        if len(labels) == 1:
            return labels[0]
        if len(labels) == 2:
            return f"{labels[0]} and {labels[1]}"
        return f"{', '.join(labels[:-1])}, and {labels[-1]}"

    overall_complete = bool(summary.get("simulator_evidence_ok")) and bool(summary.get("gate_f_ok"))
    current_test_lane = (
        "local Mac Simulator plus real iPhone"
        if summary.get("gate_f_ok")
        else "local Mac Simulator only"
    )
    openai_key_state = str(external.get("openai_api_key", "unknown"))
    server_key_status = (
        "ready"
        if openai_key_state == "set"
        else "not proven"
        if openai_key_state == "missing"
        else openai_key_state
    )
    iphone_boundary_report = local.get("iphone_credential_boundary")
    iphone_boundary_path = DEFAULT_IPHONE_CREDENTIAL_BOUNDARY_RECEIPT
    if isinstance(iphone_boundary_report, Mapping):
        iphone_boundary_path = str(
            iphone_boundary_report.get("path", DEFAULT_IPHONE_CREDENTIAL_BOUNDARY_RECEIPT)
        )
    iphone_boundary_status = (
        "passed"
        if isinstance(iphone_boundary_report, Mapping) and iphone_boundary_report.get("ok")
        else "not proven"
    )
    physical_preflight_report = external.get("physical_device_preflight")
    physical_launch_status = "not checked"
    if isinstance(physical_preflight_report, Mapping) and physical_preflight_report.get("exists"):
        physical_launch_status = str(physical_preflight_report.get("status", "unknown"))

    lines = [
        "# Pocket Agent MVP Readiness",
        "",
        "## Executive Status",
        f"- Simulator evidence: {'passed' if summary.get('simulator_evidence_ok') else 'not passed'}",
        f"- Gate F: {'passed' if summary.get('gate_f_ok') else 'missing external evidence'}",
    ]
    if summary.get("gate_f_ok"):
        lines.append("- Gate F is closed by a real-device provider receipt.")
    else:
        gate_f_needed = format_list(required_external_evidence)
        lines.append(f"- Gate F remains open until required external evidence is available: {gate_f_needed}.")

    lines.extend(
        [
            "",
            "## Completion Audit",
            f"- Overall objective: {'complete' if overall_complete else 'not complete'}",
            f"- Proven locally: Gates {format_list(proven_local_gates)}",
            f"- Current test lane: {current_test_lane}",
            f"- Not yet proven: {'none' if summary.get('gate_f_ok') else 'Gate F real iPhone OpenAI provider flow'}",
            f"- Required external evidence: {format_list(required_external_evidence)}",
            "",
            "## Completion Evidence Matrix",
            "| Requirement | Status | Evidence / Boundary |",
            "| --- | --- | --- |",
            f"| Local simulator MVP gates | {'passed' if summary.get('simulator_evidence_ok') else 'not passed'} | Gates {format_list(proven_local_gates)} |",
            f"| iPhone credential boundary | {iphone_boundary_status} | OpenAI key/API use absent from client; receipt {iphone_boundary_path} |",
            f"| Server-side OpenAI key proof | {server_key_status} | Hermes/provider runtime owns `OPENAI_API_KEY`; iPhone credential required: false |",
            f"| Physical iPhone launch path | {physical_launch_status} | CLI/CoreDevice route; Xcode GUI platform support is optional for this proof |",
            f"| Real iPhone OpenAI photo flow | {'passed' if summary.get('gate_f_ok') else 'not proven'} | Requires docs/qa-receipts/openai-photo-flow.json from a real iPhone run |",
            "",
            "## Skills And Tooling",
            "- @superpowers: TDD and verification-before-completion flow used for local implementation work.",
            "- @build-ios-apps: unavailable in this session; Xcode/SwiftPM fallback used.",
            "- ui-ux-pro-max and frontend-design: applied as mobile UX guardrails; no visual redesign was made in this report step.",
            "",
            "## Gate Ledger",
            "| Gate | Status | Scope | Missing Evidence |",
            "| --- | --- | --- | --- |",
        ]
    )
    for gate_name in ["A", "B", "C", "D", "E", "F"]:
        gate = gates.get(gate_name, {})
        missing = ", ".join(_human_evidence_values(gate.get("missing", [])))
        lines.append(
            f"| {gate_name} | {gate.get('status', 'unknown')} | {gate.get('title', '')} | {missing} |"
        )

    verification_lines: list[str] = []
    seen_test_receipts: set[str] = set()
    for gate in gates.values():
        if not isinstance(gate, Mapping):
            continue
        evidence_items = gate.get("evidence", [])
        if not isinstance(evidence_items, (list, tuple)):
            continue
        for evidence in evidence_items:
            if not isinstance(evidence, Mapping):
                continue
            name = str(evidence.get("name", ""))
            if name not in {"python", "swift"} or name in seen_test_receipts:
                continue
            seen_test_receipts.add(name)
            label = "Python tests" if name == "python" else "Swift tests"
            status = "passed" if evidence.get("ok") else "missing or failing"
            path = str(evidence.get("path", ""))
            summary_text = str(evidence.get("summary", ""))
            detail_parts = [part for part in [path, summary_text] if part]
            detail = f" ({'; '.join(detail_parts)})" if detail_parts else ""
            verification_lines.append(f"- {label}: {status}{detail}")
    if verification_lines:
        lines.extend(["", "## Fresh Verification"])
        lines.extend(verification_lines)

    iphone_boundary = local.get("iphone_credential_boundary")
    if isinstance(iphone_boundary, Mapping):
        boundary_status = "passed" if iphone_boundary.get("ok") else "missing"
        lines.extend(["", "## Client Credential Boundary"])
        lines.append(
            "- iPhone OpenAI credential boundary: "
            f"{boundary_status} ({iphone_boundary.get('path', DEFAULT_IPHONE_CREDENTIAL_BOUNDARY_RECEIPT)})"
        )
        scanned_files = iphone_boundary.get("scanned_files")
        if scanned_files not in [None, ""]:
            lines.append(f"- Scanned client files: {scanned_files}")
        lines.append(
            "- Boundary: iPhone stores Hermes/mobile bridge credentials only; OpenAI provider keys and provider URLs stay server-side."
        )
        violations = iphone_boundary.get("violations", [])
        if isinstance(violations, (list, tuple)) and violations:
            labels = []
            for violation in violations[:5]:
                if not isinstance(violation, Mapping):
                    continue
                labels.append(
                    f"{violation.get('path', '')}:{violation.get('line', '')} {violation.get('rule', '')}".strip()
                )
            if labels:
                lines.append(f"- Boundary violations: {'; '.join(labels)}")

    lines.extend(["", "## External Readiness"])
    lines.append(
        "- Server-side OpenAI key proof: "
        f"{server_key_status} (Hermes/provider runtime only; iPhone never stores or calls this key)"
    )
    provider_preflight = external.get("provider_preflight")
    if isinstance(provider_preflight, Mapping) and provider_preflight.get("exists"):
        provider_status, provider_detail = _readiness_probe_status(provider_preflight)
        lines.append(
            "- Provider preflight receipt: "
            f"{provider_status} ({provider_detail})"
        )
        provider_config = provider_preflight.get("config")
        if isinstance(provider_config, Mapping):
            base_url = provider_config.get("OPENAI_BASE_URL")
            if isinstance(base_url, Mapping):
                base_state = str(base_url.get("state", ""))
                base_value = str(base_url.get("value", ""))
                if base_state or base_value:
                    detail = " ".join(part for part in [base_state, base_value] if part)
                    if base_url.get("redacted"):
                        detail = f"{detail}, credentials redacted"
                    lines.append(f"- OpenAI base URL: {detail}")
        hermes = provider_preflight.get("hermes")
        if isinstance(hermes, Mapping) and hermes:
            profile = str(hermes.get("profile", ""))
            home_env_file = hermes.get("home_env_file", {})
            if isinstance(home_env_file, Mapping):
                home_env_state = str(home_env_file.get("OPENAI_API_KEY", ""))
                home_env_path = str(home_env_file.get("path", ""))
                if home_env_state:
                    detail = f"OPENAI_API_KEY {home_env_state}"
                    if home_env_path:
                        detail = f"{detail}, {home_env_path}"
                    lines.append(f"- Hermes home provider check: {detail}")
            env_file = hermes.get("env_file", {})
            env_key_state = ""
            env_file_path = ""
            if isinstance(env_file, Mapping):
                env_key_state = str(env_file.get("OPENAI_API_KEY", ""))
                env_file_path = str(env_file.get("path", ""))
            effective_env = hermes.get("effective_env", {})
            effective_key_state = ""
            effective_base_url_state = ""
            if isinstance(effective_env, Mapping):
                effective_key_state = str(effective_env.get("OPENAI_API_KEY", ""))
                effective_base_url_state = str(effective_env.get("OPENAI_BASE_URL", ""))
            if profile or env_key_state:
                detail = []
                if profile:
                    detail.append(profile)
                if effective_key_state:
                    detail.append(f"effective OPENAI_API_KEY {effective_key_state}")
                if effective_base_url_state:
                    detail.append(f"effective OPENAI_BASE_URL {effective_base_url_state}")
                if env_key_state:
                    detail.append(f"profile OPENAI_API_KEY {env_key_state}")
                if env_file_path:
                    detail.append(env_file_path)
                lines.append(f"- Hermes profile provider check: {', '.join(detail)}")
            auth_env = hermes.get("auth_env")
            if isinstance(auth_env, Mapping):
                auth_key_state = str(auth_env.get("OPENAI_API_KEY", ""))
                auth_base_state = str(auth_env.get("OPENAI_BASE_URL", ""))
                auth_used = auth_env.get("used")
                if auth_key_state or auth_base_state:
                    detail = []
                    if auth_key_state:
                        detail.append(f"OPENAI_API_KEY {auth_key_state}")
                    if auth_base_state:
                        detail.append(f"OPENAI_BASE_URL {auth_base_state}")
                    if auth_used:
                        detail.append("used")
                    lines.append(f"- Hermes auth OpenAI API-key source: {', '.join(detail)}")
            shared_auth_env = hermes.get("shared_auth_env")
            if isinstance(shared_auth_env, Mapping):
                shared_key_state = str(shared_auth_env.get("OPENAI_API_KEY", ""))
                shared_base_state = str(shared_auth_env.get("OPENAI_BASE_URL", ""))
                shared_used = shared_auth_env.get("used")
                if shared_key_state or shared_base_state:
                    detail = []
                    if shared_key_state:
                        detail.append(f"OPENAI_API_KEY {shared_key_state}")
                    if shared_base_state:
                        detail.append(f"OPENAI_BASE_URL {shared_base_state}")
                    if shared_used:
                        detail.append("used")
                    shared_auth_file = hermes.get("shared_auth_file", {})
                    if isinstance(shared_auth_file, Mapping):
                        shared_path = str(shared_auth_file.get("path", ""))
                        if shared_path:
                            detail.append(shared_path)
                    lines.append(f"- Hermes shared auth OpenAI API-key source: {', '.join(detail)}")
            auth = hermes.get("auth")
            if isinstance(auth, Mapping):
                openai_codex = auth.get("openai_codex")
                if (
                    isinstance(openai_codex, Mapping)
                    and openai_codex.get("credential_pool") == "set"
                    and openai_codex.get("compatible_with_photo_provider") is False
                ):
                    lines.append("- OpenAI Codex OAuth: present, but not an OpenAI Images API key")
    provider_env_sources = external.get("provider_env_sources")
    if isinstance(provider_env_sources, Mapping) and provider_env_sources.get("exists"):
        source_status, source_detail = _readiness_probe_status(provider_env_sources)
        lines.append(
            "- Provider env source probe: "
            f"{source_status} ({source_detail})"
        )
        source_entries = provider_env_sources.get("sources", [])
        if isinstance(source_entries, (list, tuple)):
            force_labels: list[str] = []
            for source in source_entries:
                if not isinstance(source, Mapping):
                    continue
                if source.get("source") != "hermes_force_current_process":
                    continue
                force_key = str(source.get("force_env", "")) or f"{HERMES_PROVIDER_ENV_FORCE_PREFIX}OPENAI_API_KEY"
                state = str(source.get("OPENAI_API_KEY", ""))
                detail = force_key
                if state:
                    detail = f"{detail} {state}"
                force_labels.append(detail)
            if force_labels:
                lines.append(f"- Hermes force env source: {'; '.join(force_labels)}")
        shell_startup = provider_env_sources.get("shell_startup_files", {})
        if isinstance(shell_startup, Mapping):
            shell_files = shell_startup.get("files", [])
            shell_set_files = shell_startup.get("set_files", [])
            if isinstance(shell_set_files, (list, tuple)) and shell_set_files:
                labels = [
                    str(source.get("path", ""))
                    for source in shell_set_files
                    if isinstance(source, Mapping) and str(source.get("path", "")).strip()
                ]
                detail = "; ".join(labels) if labels else "present"
                lines.append(
                    "- Shell startup key declaration: "
                    f"{detail} (diagnostic only; not active Hermes/provider evidence)"
                )
            elif isinstance(shell_files, (list, tuple)) and shell_files:
                lines.append(
                    "- Shell startup key declaration: checked existing startup files, "
                    "OPENAI_API_KEY missing"
                )
        hermes_sources = provider_env_sources.get("hermes", {})
        if isinstance(hermes_sources, Mapping):
            home_env_file = hermes_sources.get("home_env_file", {})
            if isinstance(home_env_file, Mapping):
                home_env_state = str(home_env_file.get("OPENAI_API_KEY", ""))
                home_env_path = str(home_env_file.get("path", ""))
                if home_env_state:
                    detail = f"OPENAI_API_KEY {home_env_state}"
                    if home_env_path:
                        detail = f"{detail}, {home_env_path}"
                    lines.append(f"- Hermes home env source: {detail}")
            shared_auth_file = hermes_sources.get("shared_auth_file", {})
            if isinstance(shared_auth_file, Mapping):
                shared_key_state = str(shared_auth_file.get("OPENAI_API_KEY", ""))
                shared_base_state = str(shared_auth_file.get("OPENAI_BASE_URL", ""))
                shared_path = str(shared_auth_file.get("path", ""))
                if shared_key_state or shared_base_state:
                    detail = []
                    if shared_key_state:
                        detail.append(f"OPENAI_API_KEY {shared_key_state}")
                    if shared_base_state:
                        detail.append(f"OPENAI_BASE_URL {shared_base_state}")
                    if shared_path:
                        detail.append(shared_path)
                    lines.append(f"- Hermes shared auth source: {', '.join(detail)}")
            selected_profile = str(hermes_sources.get("selected_profile", ""))
            selected_state = str(hermes_sources.get("selected_profile_state", ""))
            if selected_profile or selected_state:
                detail = []
                if selected_profile:
                    detail.append(selected_profile)
                if selected_state:
                    detail.append(f"OPENAI_API_KEY {selected_state}")
                lines.append(f"- Selected Hermes env source: {', '.join(detail)}")
            profile_auths = hermes_sources.get("profile_auths", [])
            if isinstance(profile_auths, (list, tuple)):
                labels = []
                for auth_source in profile_auths:
                    if not isinstance(auth_source, Mapping) or not auth_source.get("selected"):
                        continue
                    profile = str(auth_source.get("profile", "")) or "default"
                    key_state = str(auth_source.get("OPENAI_API_KEY", ""))
                    base_state = str(auth_source.get("OPENAI_BASE_URL", ""))
                    path = str(auth_source.get("path", ""))
                    detail = [profile]
                    if key_state:
                        detail.append(f"OPENAI_API_KEY {key_state}")
                    if base_state:
                        detail.append(f"OPENAI_BASE_URL {base_state}")
                    if path:
                        detail.append(path)
                    labels.append(", ".join(detail))
                if labels:
                    lines.append(f"- Selected Hermes auth source: {'; '.join(labels)}")
            gateway_processes = hermes_sources.get("gateway_processes", [])
            if isinstance(gateway_processes, (list, tuple)) and gateway_processes:
                labels: list[str] = []
                for process in gateway_processes:
                    if not isinstance(process, Mapping):
                        continue
                    profile = str(process.get("profile", "")) or "default"
                    pid = str(process.get("pid", ""))
                    state = str(process.get("OPENAI_API_KEY", ""))
                    label = f"{profile}"
                    if pid:
                        label = f"{label} pid {pid}"
                    if state:
                        label = f"{label} OPENAI_API_KEY {state}"
                    force_state = str(process.get("force_env", ""))
                    if force_state:
                        label = f"{label} force env {force_state}"
                    labels.append(label)
                if labels:
                    lines.append(f"- Hermes gateway process source: {'; '.join(labels)}")
            hermes_processes = hermes_sources.get("processes", [])
            if isinstance(hermes_processes, (list, tuple)) and hermes_processes:
                labels = []
                for process in hermes_processes:
                    if not isinstance(process, Mapping):
                        continue
                    if (
                        not process.get("selected")
                        and process.get("OPENAI_API_KEY") != "set"
                        and process.get("OPENAI_BASE_URL") != "set"
                    ):
                        continue
                    profile = str(process.get("profile", "")) or "default"
                    pid = str(process.get("pid", ""))
                    key_state = str(process.get("OPENAI_API_KEY", ""))
                    base_url_state = str(process.get("OPENAI_BASE_URL", ""))
                    parts = [profile]
                    if pid:
                        parts.append(f"pid {pid}")
                    if key_state:
                        parts.append(f"OPENAI_API_KEY {key_state}")
                    if base_url_state:
                        parts.append(f"OPENAI_BASE_URL {base_url_state}")
                    force_state = str(process.get("force_env", ""))
                    if force_state:
                        parts.append(f"force env {force_state}")
                    labels.append(" ".join(parts))
                if labels:
                    lines.append(f"- Hermes process diagnostics: {'; '.join(labels[:6])}")
            provider_references = hermes_sources.get("provider_references", [])
            if isinstance(provider_references, (list, tuple)) and provider_references:
                labels = []
                for reference in provider_references:
                    if not isinstance(reference, Mapping):
                        continue
                    if not reference.get("selected"):
                        continue
                    profile = str(reference.get("profile", "")) or "default"
                    path = str(reference.get("path", ""))
                    openai_state = str(reference.get("openai_reference", ""))
                    key_token = str(reference.get("OPENAI_API_KEY", ""))
                    base_token = str(reference.get("OPENAI_BASE_URL", ""))
                    label = (
                        f"{profile}, openai reference {openai_state}, "
                        f"OPENAI_API_KEY token {key_token}, OPENAI_BASE_URL token {base_token}"
                    )
                    if path:
                        label = f"{label}, {path}"
                    labels.append(label)
                if labels:
                    lines.append(f"- Hermes selected config references: {'; '.join(labels)}")
            cli_auth = hermes_sources.get("cli_auth")
            if isinstance(cli_auth, Mapping) and not cli_auth.get("skipped"):
                detail = []
                profile = str(cli_auth.get("profile", ""))
                if profile:
                    detail.append(profile)
                openai_status = cli_auth.get("openai_status", {})
                if isinstance(openai_status, Mapping):
                    state = str(openai_status.get("state", ""))
                    if state:
                        detail.append(f"openai {state}")
                images_state = str(cli_auth.get("openai_images_api_key_auth", ""))
                if images_state:
                    detail.append(f"Images API key {images_state}")
                auth_list = cli_auth.get("auth_list", {})
                providers = auth_list.get("providers", {}) if isinstance(auth_list, Mapping) else {}
                if isinstance(providers, Mapping):
                    openai_codex = providers.get("openai-codex", {})
                    if isinstance(openai_codex, Mapping):
                        auth_types = openai_codex.get("auth_types", [])
                        if isinstance(auth_types, (list, tuple)) and auth_types:
                            detail.append(f"openai-codex {'/'.join(str(item) for item in auth_types)} present")
                if detail:
                    lines.append(f"- Hermes CLI auth: {', '.join(detail)}")
        set_sources = provider_env_sources.get("set_sources", [])
        if isinstance(set_sources, (list, tuple)) and set_sources:
            labels: list[str] = []
            for source in set_sources:
                if not isinstance(source, Mapping):
                    continue
                label = str(source.get("source", ""))
                profile = str(source.get("profile", ""))
                if profile:
                    label = f"{label}:{profile}"
                if label:
                    labels.append(label)
            if labels:
                lines.append(f"- Provider env source with key: {', '.join(labels)}")
        source_actions = provider_env_sources.get("next_actions", [])
        if isinstance(source_actions, (list, tuple)) and source_actions:
            lines.append("- Provider env source next actions:")
            for index, item in enumerate(source_actions, start=1):
                lines.append(f"{index}. {item}")
    provider_env_sources_all_profiles = external.get("provider_env_sources_all_profiles")
    if isinstance(provider_env_sources_all_profiles, Mapping) and provider_env_sources_all_profiles.get("exists"):
        sweep_status, sweep_detail = _readiness_probe_status(provider_env_sources_all_profiles)
        sweep_sources = provider_env_sources_all_profiles.get("set_sources", [])
        sweep_labels: list[str] = []
        if isinstance(sweep_sources, (list, tuple)):
            for source in sweep_sources:
                if not isinstance(source, Mapping):
                    continue
                label = str(source.get("source", ""))
                profile = str(source.get("profile", ""))
                if profile:
                    label = f"{label}:{profile}"
                path = str(source.get("path", ""))
                pid = str(source.get("pid", ""))
                if pid:
                    label = f"{label} pid {pid}"
                if path:
                    label = f"{label} {path}"
                if label:
                    sweep_labels.append(label)
        if sweep_labels:
            lines.append(
                "- Hermes all-profile key sweep: found compatible OpenAI Images API-key source(s) "
                f"{', '.join(sweep_labels)} ({sweep_detail}; selected profile probe still governs Gate F)"
            )
        else:
            hermes_sweep = provider_env_sources_all_profiles.get("hermes", {})
            profile_count = 0
            if isinstance(hermes_sweep, Mapping):
                profiles = hermes_sweep.get("profiles", [])
                if isinstance(profiles, (list, tuple)):
                    profile_count = len(profiles)
            profile_detail = f"; scanned profiles {profile_count}" if profile_count else ""
            lines.append(
                "- Hermes all-profile key sweep: no compatible OpenAI Images API key found "
                f"({sweep_status}; {sweep_detail}{profile_detail})"
            )
    tailscale = external.get("tailscale", {})
    if isinstance(tailscale, Mapping):
        cli = tailscale.get("cli")
        ip_check = tailscale.get("ip_check")
        if isinstance(cli, Mapping) and isinstance(ip_check, Mapping):
            cli_status = "ready" if cli.get("ok") else "missing"
            cli_detail = cli.get("path") or cli.get("error") or ""
            lines.append(f"- Tailscale CLI: {cli_status}" + (f" ({cli_detail})" if cli_detail else ""))
            ip_status = "ready" if ip_check.get("ok") else "missing"
            ip_detail = ip_check.get("value") or ip_check.get("error") or ""
            lines.append(f"- Tailscale IP: {ip_status}" + (f" ({ip_detail})" if ip_detail else ""))
        else:
            tailnet_status = "ready" if tailscale.get("ok") else "missing"
            tailnet_detail = tailscale.get("ip") or tailscale.get("error") or ""
            lines.append(f"- Tailscale: {tailnet_status}" + (f" ({tailnet_detail})" if tailnet_detail else ""))
    if remaining_external:
        lines.append("- Remaining Gate F evidence:")
        for item in remaining_external:
            lines.append(f"  - {_human_evidence_label(str(item))}")
    else:
        lines.append("- Remaining Gate F evidence: none")

    physical_preflight = external.get("physical_device_preflight")
    if isinstance(physical_preflight, Mapping) and physical_preflight.get("exists"):
        lines.extend(["", "## Physical Device Preflight"])
        lines.append(f"- Receipt: {physical_preflight.get('path', '')}")
        device = physical_preflight.get("device", {})
        if isinstance(device, Mapping):
            device_name = str(device.get("name", ""))
            device_id = str(device.get("id", ""))
            device_state = str(device.get("state", ""))
            if device_name or device_id or device_state:
                detail = ", ".join(part for part in [device_id, device_state] if part)
                lines.append(f"- Device: {device_name} ({detail})" if detail else f"- Device: {device_name}")
        lines.append(f"- Xcode destination: {physical_preflight.get('status', 'unknown')}")
        target_build = physical_preflight.get("target_build", {})
        if isinstance(target_build, Mapping) and target_build.get("checked"):
            build_status = "ready" if target_build.get("ok") else "blocked"
            build_target = str(target_build.get("target", ""))
            build_config = str(target_build.get("configuration", ""))
            build_sdk = str(target_build.get("sdk", ""))
            build_detail = " ".join(part for part in [build_target, build_config, build_sdk] if part)
            lines.append(
                "- CLI target build: "
                f"{build_status}" + (f" ({build_detail})" if build_detail else "")
            )
        missing = physical_preflight.get("missing", [])
        if isinstance(missing, (list, tuple)) and missing:
            lines.append(f"- Missing: {', '.join(str(item) for item in missing)}")
        ineligible = physical_preflight.get("ineligible", [])
        if isinstance(ineligible, (list, tuple)) and ineligible:
            lines.append(f"- Xcode destination note: {_preferred_xcode_destination_note(ineligible)}")
        next_actions = physical_preflight.get("next_actions", [])
        if isinstance(next_actions, (list, tuple)) and next_actions:
            lines.append("- Physical device next actions:")
            for index, item in enumerate(next_actions, start=1):
                lines.append(f"{index}. {item}")

    if isinstance(gate_f_preflight, Mapping) and gate_f_preflight.get("exists"):
        lines.extend(["", "## Gate F External Preflight"])
        lines.append(f"- Receipt: {gate_f_preflight.get('path', '')}")
        lines.append(f"- Start readiness: {gate_f_preflight.get('status', 'unknown')}")
        missing_to_start = gate_f_preflight.get("missing_to_start", [])
        if isinstance(missing_to_start, (list, tuple)) and missing_to_start:
            lines.append(f"- Missing to start: {', '.join(_human_evidence_values(missing_to_start))}")
        else:
            lines.append("- Missing to start: none")
        start_blockers = gate_f_preflight.get("start_blockers", [])
        if isinstance(start_blockers, (list, tuple)) and start_blockers:
            lines.append("- Start blocker details:")
            for blocker in start_blockers:
                if not isinstance(blocker, Mapping):
                    continue
                label = str(blocker.get("label", "")) or str(blocker.get("missing", ""))
                scope = str(blocker.get("scope", ""))
                message = str(blocker.get("message", ""))
                iphone_required = blocker.get("iphone_required")
                detail = label
                if scope:
                    detail = f"{detail} ({scope})"
                if iphone_required is False:
                    detail = f"{detail}; iPhone credential required: false"
                lines.append(f"  - {detail}")
                if message:
                    lines.append(f"    {message}")
                remediation_command = str(blocker.get("remediation_command", "")).strip()
                if remediation_command:
                    lines.append(f"    Remediation command: `{remediation_command}`")
        missing_to_close = gate_f_preflight.get("missing_to_close", [])
        if isinstance(missing_to_close, (list, tuple)) and missing_to_close:
            lines.append(f"- Missing to close: {', '.join(_human_evidence_values(missing_to_close))}")
        else:
            lines.append("- Missing to close: none")
        endpoint = gate_f_preflight.get("endpoint")
        if isinstance(endpoint, Mapping):
            endpoint_status = "ready" if endpoint.get("ok") else "missing"
            endpoint_source = str(endpoint.get("source", ""))
            endpoint_host = str(endpoint.get("host", ""))
            endpoint_detail = (
                f"{endpoint_source}: {endpoint_host}"
                if endpoint_source and endpoint_host
                else endpoint_source or endpoint_host
            )
            lines.append(
                "- Endpoint evidence: "
                f"{endpoint_status}" + (f" ({endpoint_detail})" if endpoint_detail else "")
            )
        resume_commands = gate_f_preflight.get("commands")
        if isinstance(resume_commands, Mapping):
            for key in [
                "provider_preflight",
                "provider_env_sources",
                "hermes_auth_add_openai",
                "hermes_openai_auth_import",
                "run_real_iphone_openai",
                "verify_real_iphone_openai",
                "gate_f_resume",
            ]:
                command = resume_commands.get(key)
                if command:
                    lines.extend([f"### {key}", "```bash", str(command), "```"])
            checklist: list[str] = []
            missing_to_start_values = [str(item) for item in missing_to_start] if isinstance(missing_to_start, (list, tuple)) else []
            missing_to_close_values = [str(item) for item in missing_to_close] if isinstance(missing_to_close, (list, tuple)) else []
            if "OPENAI_API_KEY" in missing_to_start_values:
                if resume_commands.get("hermes_auth_add_openai"):
                    checklist.append(
                        "Add the OpenAI Images API key with `hermes_auth_add_openai`, "
                        "then rerun `provider_preflight`; the iPhone app never stores or calls this key."
                    )
                else:
                    checklist.append(
                        "Confirm `OPENAI_API_KEY` is available to the Hermes/mock bridge process, "
                        "then rerun `provider_preflight`; the iPhone app never stores or calls this key."
                    )
            if "Tailscale endpoint evidence" in missing_to_start_values:
                checklist.append(
                    "Install or start Tailscale, or set `TAILSCALE_CLI=/path/to/tailscale`, "
                    "until preflight reports a Mac tailnet endpoint."
                )
            if "real iPhone OpenAI photo-flow receipt" in missing_to_close_values:
                if resume_commands.get("gate_f_resume"):
                    checklist.append(
                        "When the iPhone and external start conditions are available, run `gate_f_resume`."
                    )
                else:
                    checklist.append("When the iPhone is available, run `run_real_iphone_openai`.")
                    checklist.append("Verify `docs/qa-receipts/openai-photo-flow.json` with `verify_real_iphone_openai`.")
            if checklist:
                lines.extend(["", "## Gate F Resume Checklist"])
                for index, item in enumerate(checklist, start=1):
                    lines.append(f"{index}. {item}")

    gate_f_handoff = external.get("gate_f_handoff")
    if isinstance(gate_f_handoff, Mapping) and gate_f_handoff.get("exists"):
        lines.extend(["", "## Gate F No-Device Handoff"])
        lines.append(f"- Receipt: {gate_f_handoff.get('path', '')}")
        lines.append(f"- Handoff status: {gate_f_handoff.get('status', 'unknown')}")
        lines.append(f"- Execution mode: {gate_f_handoff.get('execution_mode', '')}")
        lines.append(f"- Physical iPhone used: {str(gate_f_handoff.get('physical_iphone_used')).lower()}")
        lines.append(
            "- Physical device launch attempted: "
            f"{str(gate_f_handoff.get('physical_device_launch_attempted')).lower()}"
        )
        remaining_to_start = gate_f_handoff.get("remaining_to_start", [])
        if isinstance(remaining_to_start, (list, tuple)) and remaining_to_start:
            lines.append(f"- Remaining to start: {', '.join(_human_evidence_values(remaining_to_start))}")
        else:
            lines.append("- Remaining to start: none")
        remaining_to_close = gate_f_handoff.get("remaining_to_close", [])
        if isinstance(remaining_to_close, (list, tuple)) and remaining_to_close:
            lines.append(f"- Remaining to close: {', '.join(_human_evidence_values(remaining_to_close))}")
        else:
            lines.append("- Remaining to close: none")
        endpoint = gate_f_handoff.get("endpoint")
        if isinstance(endpoint, Mapping):
            endpoint_status = "ready" if endpoint.get("ok") else "missing"
            endpoint_source = str(endpoint.get("source", ""))
            endpoint_host = str(endpoint.get("host", ""))
            endpoint_detail = (
                f"{endpoint_source}: {endpoint_host}"
                if endpoint_source and endpoint_host
                else endpoint_source or endpoint_host
            )
            lines.append(
                "- Endpoint evidence: "
                f"{endpoint_status}" + (f" ({endpoint_detail})" if endpoint_detail else "")
            )
        next_actions = gate_f_handoff.get("next_actions", [])
        if isinstance(next_actions, (list, tuple)) and next_actions:
            lines.append("- Next handoff actions:")
            for index, item in enumerate(next_actions, start=1):
                lines.append(f"{index}. {item}")

    if isinstance(local, Mapping):
        resume = local.get("simulator_only_resume")
        if isinstance(resume, Mapping) and resume.get("exists"):
            lines.extend(["", "## Local Simulator Resume Evidence"])
            lines.append(f"- Resume receipt: {resume.get('path', '')}")
            lines.append(f"- Resume status: {resume.get('status', 'unknown')}")
            lines.append(f"- Execution mode: {resume.get('execution_mode', '')}")
            lines.append(f"- Physical iPhone used: {str(resume.get('physical_iphone_used')).lower()}")
            lines.append(
                "- Physical device launch attempted: "
                f"{str(resume.get('physical_device_launch_attempted')).lower()}"
            )
            commands_executed = resume.get("real_device_commands_executed", [])
            if isinstance(commands_executed, (list, tuple)) and commands_executed:
                lines.append(
                    "- Real-device commands executed: "
                    f"{', '.join(str(command) for command in commands_executed)}"
                )
            else:
                lines.append("- Real-device commands executed: none")
            missing = resume.get("missing", [])
            if isinstance(missing, (list, tuple)) and missing:
                lines.append(f"- Missing resume evidence: {', '.join(str(item) for item in missing)}")

        suite = local.get("simulator_suite")
        if isinstance(suite, Mapping) and suite.get("exists"):
            lines.extend(["", "## Local Simulator Suite"])
            lines.append(f"- Suite status: {suite.get('status', 'unknown')}")
            required_steps = suite.get("required_steps", [])
            if isinstance(required_steps, (list, tuple)) and required_steps:
                lines.append(f"- Required steps: {', '.join(str(step) for step in required_steps)}")
            failed_steps = suite.get("failed_required_steps", [])
            if isinstance(failed_steps, (list, tuple)) and failed_steps:
                lines.append(f"- Failed required steps: {', '.join(str(step) for step in failed_steps)}")

        artifacts = local.get("simulator_artifacts")
        if isinstance(artifacts, Mapping):
            artifact_labels = [
                ("discovery_refresh_receipt", "No-payload discovery refresh receipt"),
                ("discovery_refresh_screenshot", "No-payload discovery refresh screenshot"),
                ("picker_ui_screenshot", "PhotosPicker entry screenshot"),
                ("capture_ready_receipt", "Selected-photo ready receipt"),
                ("capture_ready_screenshot", "Selected-photo ready screenshot"),
                ("capture_completed_receipt", "Completed capture receipt"),
                ("capture_completed_screenshot", "Completed capture screenshot"),
                ("result_gallery_receipt", "Result gallery receipt"),
                ("result_gallery_screenshot", "Result gallery screenshot"),
                ("result_gallery_downloaded_receipt", "Result gallery downloaded receipt"),
                ("result_gallery_downloaded_screenshot", "Result gallery downloaded screenshot"),
                ("openai_photo_flow_receipt", "OpenAI-compatible photo-flow receipt"),
                ("fake_openai_status", "Fake OpenAI status receipt"),
                ("openai_screenshot", "OpenAI-compatible smoke screenshot"),
            ]
            artifact_lines: list[str] = []
            for key, label in artifact_labels:
                artifact = artifacts.get(key)
                if not isinstance(artifact, Mapping):
                    continue
                path = str(artifact.get("path", ""))
                if not path:
                    continue
                ready = bool(artifact.get("ok")) if "ok" in artifact else bool(artifact.get("exists"))
                suffix = "" if ready else " (missing)"
                artifact_lines.append(f"- {label}: {path}{suffix}")
            if artifact_lines:
                lines.extend(["", "## Local Simulator Artifacts"])
                lines.extend(artifact_lines)

        ui_test = local.get("simulator_ui_test_preflight")
        if isinstance(ui_test, Mapping) and ui_test.get("exists"):
            lines.extend(["", "## Local Simulator UI Test Readiness"])
            lines.append(f"- Xcode UI test destination: {ui_test.get('status', 'unknown')}")
            lines.append(f"- iOS Simulator SDK: {ui_test.get('sdk_latest', '')}")
            lines.append(f"- Installed iOS Simulator runtime: {ui_test.get('runtime_latest', '')}")
            reason = str(ui_test.get("reason", ""))
            if reason:
                lines.append(f"- Detail: {reason}")
            ineligible = ui_test.get("ineligible", [])
            if isinstance(ineligible, (list, tuple)) and ineligible:
                lines.append(f"- Xcode destination note: {_preferred_xcode_destination_note(ineligible)}")

    lines.extend(["", "## Next Commands"])
    for key in [
        "gate_audit",
        "physical_device_preflight",
        "gate_f_provider_check",
        "gate_f_preflight",
        "provider_env_sources",
        "provider_env_sources_all_profiles",
        "iphone_credential_boundary",
        "hermes_auth_add_openai",
        "hermes_openai_auth_import",
        "gate_f_handoff",
        "python_test_receipt",
        "swift_test_receipt",
        "simulator_connection_smoke",
        "simulator_discovery_refresh_smoke",
        "simulator_suite",
        "simulator_only_resume",
        "simulator_seed_photo_library",
        "simulator_picker_ui_smoke",
        "simulator_ui_test_preflight",
        "simulator_capture_ready_smoke",
        "simulator_capture_completed_smoke",
        "simulator_result_gallery_smoke",
        "simulator_result_gallery_downloaded_smoke",
        "simulator_openai_smoke",
        "gate_f_real_iphone",
    ]:
        command = commands.get(key)
        if command:
            lines.extend([f"### {key}", "```bash", str(command), "```"])

    return "\n".join(lines) + "\n"


def run_lan_qa_session(
    host: str,
    port: int = 8765,
    device_id: str = "",
    bundle_id: str = DEFAULT_BUNDLE_ID,
    token: str = DEFAULT_TOKEN,
    connection_timeout: float = 60,
    photo_timeout: float = 180,
    interval: float = 2.0,
    launch_app: bool = True,
    connection_only: bool = False,
    advertise_bonjour: bool = True,
    photo_provider: str = "fixture",
    photo_pack_root: str = "photo-pack",
    app_launcher: Optional[Callable[[str, str], None]] = None,
    bonjour_launcher=None,
    status_fetcher: Callable[..., Mapping[str, Any]] = fetch_qa_status,
    receipt_file: str = "",
    out=None,
    err=None,
) -> int:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr

    if launch_app and not device_id:
        print("--device-id is required unless --no-launch is used.", file=err_stream)
        return 2

    if connection_only and not launch_app:
        base_url = f"http://{host}:{port}"
        print("Using an already running Pocket Agent Mobile Bridge.", file=out_stream, flush=True)
        print(f"iPhone endpoint: {base_url}", file=out_stream, flush=True)
        return _wait_for_status(
            base_url=base_url,
            token=token,
            timeout_seconds=connection_timeout,
            interval_seconds=interval,
            evaluator=evaluate_connection_restore,
            status_fetcher=status_fetcher,
            phase="connection",
            receipt_file=receipt_file,
            out=out_stream,
            err=err_stream,
        )

    app = None
    if photo_provider != "fixture":
        app = create_app(photo_provider=build_photo_provider(photo_provider, photo_pack_root=photo_pack_root))
    server = create_http_server(host="0.0.0.0", port=port, app=app)
    actual_port = int(server.server_address[1])
    base_url = f"http://{host}:{actual_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    bonjour = None
    launcher = app_launcher or _launch_ios_app

    try:
        thread.start()
        print(f"Pocket Agent mock bridge listening on http://0.0.0.0:{actual_port}", file=out_stream, flush=True)
        print(f"iPhone endpoint: {base_url}", file=out_stream, flush=True)

        if advertise_bonjour:
            bonjour = BonjourAdvertisement(
                name="Pocket Agent Mock Hermes",
                host=host,
                port=actual_port,
                pairing_code="pair_dev",
                launcher=bonjour_launcher,
            )
            try:
                bonjour.start()
                print(f"Bonjour advertising Pocket Agent Mock Hermes at {base_url}", file=out_stream, flush=True)
            except OSError as error:
                print(f"Bonjour advertisement did not start: {error}", file=err_stream, flush=True)

        if launch_app:
            print(f"Launching {bundle_id} on {device_id}", file=out_stream, flush=True)
            try:
                launcher(device_id, bundle_id)
            except Exception as error:
                print(f"Unable to launch iPhone app: {error}", file=err_stream, flush=True)
                return 1
        else:
            print("App launch skipped; open Pocket Agent on the iPhone manually.", file=out_stream, flush=True)

        print("Waiting for saved Hermes connection restore...", file=out_stream, flush=True)
        connection_result = _wait_for_status(
            base_url=base_url,
            token=token,
            timeout_seconds=connection_timeout,
            interval_seconds=interval,
            evaluator=evaluate_connection_restore,
            status_fetcher=status_fetcher,
            phase="connection",
            receipt_file=receipt_file,
            out=out_stream,
            err=err_stream,
        )
        if connection_result != 0 or connection_only:
            return connection_result

        print(
            "On iPhone: choose/take a photo, Send to Pocket Agent, Review Results, Download Selected.",
            file=out_stream,
            flush=True,
        )
        print("Waiting for photo upload/task/download receipt...", file=out_stream, flush=True)
        return _wait_for_status(
            base_url=base_url,
            token=token,
            timeout_seconds=photo_timeout,
            interval_seconds=interval,
            evaluator=evaluate_photo_flow,
            status_fetcher=status_fetcher,
            phase="photo-flow",
            receipt_file=receipt_file,
            out=out_stream,
            err=err_stream,
        )
    finally:
        if bonjour is not None:
            try:
                bonjour.stop()
            except Exception as error:
                print(f"Bonjour advertisement did not stop cleanly: {error}", file=err_stream, flush=True)
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def run_simulator_connection_session(
    host: str = "127.0.0.1",
    port: int = 8766,
    bundle_id: str = DEFAULT_BUNDLE_ID,
    token: str = DEFAULT_TOKEN,
    connection_timeout: float = 45,
    interval: float = 1.0,
    launch_app: bool = True,
    advertise_bonjour: bool = True,
    simulator_launcher: Optional[Callable[[str], None]] = None,
    bonjour_launcher=None,
    status_fetcher: Callable[..., Mapping[str, Any]] = fetch_qa_status,
    receipt_file: str = "docs/qa-receipts/simulator-connection-latest.json",
    out=None,
    err=None,
) -> int:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr
    server = create_http_server(host="0.0.0.0", port=port)
    actual_port = int(server.server_address[1])
    base_url = f"http://{host}:{actual_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    bonjour = None
    launcher = simulator_launcher or _launch_simulator_app

    try:
        thread.start()
        print(f"Pocket Agent mock bridge listening on http://0.0.0.0:{actual_port}", file=out_stream, flush=True)
        print(f"Simulator endpoint: {base_url}", file=out_stream, flush=True)

        if advertise_bonjour:
            bonjour = BonjourAdvertisement(
                name="Pocket Agent Mock Hermes",
                host=host,
                port=actual_port,
                pairing_code="pair_dev",
                launcher=bonjour_launcher,
            )
            try:
                bonjour.start()
                print(f"Bonjour advertising Pocket Agent Mock Hermes at {base_url}", file=out_stream, flush=True)
            except OSError as error:
                print(f"Bonjour advertisement did not start: {error}", file=err_stream, flush=True)

        if launch_app:
            print(f"Launching Simulator app {bundle_id}", file=out_stream, flush=True)
            try:
                launcher(bundle_id)
            except Exception as error:
                print(f"Unable to launch Simulator app: {error}", file=err_stream, flush=True)
                return 1
        else:
            print("Simulator launch skipped; launch Pocket Agent manually.", file=out_stream, flush=True)

        return _wait_for_status(
            base_url=base_url,
            token=token,
            timeout_seconds=connection_timeout,
            interval_seconds=interval,
            evaluator=evaluate_connection_restore,
            status_fetcher=status_fetcher,
            phase="connection",
            receipt_file=receipt_file,
            out=out_stream,
            err=err_stream,
        )
    finally:
        if bonjour is not None:
            try:
                bonjour.stop()
            except Exception as error:
                print(f"Bonjour advertisement did not stop cleanly: {error}", file=err_stream, flush=True)
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def run_simulator_discovery_refresh_session(
    host: str = "127.0.0.1",
    port: int = 8767,
    bundle_id: str = DEFAULT_BUNDLE_ID,
    token: str = DEFAULT_TOKEN,
    connection_timeout: float = 45,
    interval: float = 1.0,
    launch_app: bool = True,
    receipt_file: str = DEFAULT_SIMULATOR_DISCOVERY_REFRESH_RECEIPT,
    screenshot_file: str = DEFAULT_SIMULATOR_DISCOVERY_REFRESH_SCREENSHOT,
    simulator_launcher: Optional[Callable[[str, str], None]] = None,
    simulator_screenshotter: Optional[Callable[[str], None]] = None,
    status_fetcher: Callable[..., Mapping[str, Any]] = fetch_qa_status,
    out=None,
    err=None,
) -> int:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr
    server = create_http_server(host="0.0.0.0", port=port)
    actual_port = int(server.server_address[1])
    base_url = f"http://{host}:{actual_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    launcher = simulator_launcher or _launch_simulator_discovery_refresh_smoke
    screenshotter = simulator_screenshotter or _take_simulator_screenshot

    try:
        thread.start()
        print(f"Pocket Agent mock bridge listening on http://0.0.0.0:{actual_port}", file=out_stream, flush=True)
        print(f"Simulator endpoint without Bonjour payload: {base_url}", file=out_stream, flush=True)

        if launch_app:
            print(f"Launching Simulator discovery-refresh smoke for {bundle_id}", file=out_stream, flush=True)
            try:
                launcher(bundle_id, base_url)
            except Exception as error:
                print(f"Unable to launch Simulator discovery-refresh smoke: {error}", file=err_stream, flush=True)
                return 1
        else:
            print("Simulator discovery-refresh launch skipped; launch smoke mode manually.", file=out_stream, flush=True)

        result = _wait_for_status(
            base_url=base_url,
            token=token,
            timeout_seconds=connection_timeout,
            interval_seconds=interval,
            evaluator=evaluate_discovery_refresh,
            status_fetcher=status_fetcher,
            phase="discovery-refresh",
            receipt_file=receipt_file,
            out=out_stream,
            err=err_stream,
        )
        if result == 0 and screenshot_file:
            try:
                screenshotter(screenshot_file)
                print(f"Simulator discovery-refresh screenshot written to {screenshot_file}", file=out_stream, flush=True)
            except Exception as error:
                print(f"Unable to capture Simulator discovery-refresh screenshot: {error}", file=err_stream, flush=True)
                return 1
        return result
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def run_openai_compatible_simulator_session(
    host: str = "127.0.0.1",
    bridge_port: int = 8769,
    fake_openai_port: int = 8781,
    bundle_id: str = DEFAULT_BUNDLE_ID,
    token: str = DEFAULT_TOKEN,
    connection_timeout: float = 45,
    photo_timeout: float = 90,
    interval: float = 1.0,
    photo_pack_root: str = "photo-pack",
    output_format: str = "png",
    launch_app: bool = True,
    receipt_file: str = "docs/qa-receipts/simulator-openai-compatible-photo-flow.json",
    fake_openai_status_file: str = "docs/qa-receipts/simulator-openai-compatible-fake-openai-status.json",
    screenshot_file: str = "",
    simulator_launcher: Optional[Callable[[str, str, str], None]] = None,
    simulator_screenshotter: Optional[Callable[[str], None]] = None,
    status_fetcher: Callable[..., Mapping[str, Any]] = fetch_qa_status,
    out=None,
    err=None,
) -> int:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr
    launcher = simulator_launcher or _launch_simulator_smoke
    screenshotter = simulator_screenshotter or _take_simulator_screenshot
    fake_openai = create_fake_openai_server(host=host, port=fake_openai_port)
    fake_openai_thread = threading.Thread(target=fake_openai.serve_forever, daemon=True)
    bridge = None
    bridge_thread = None

    previous_env = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "OPENAI_BASE_URL": os.environ.get("OPENAI_BASE_URL"),
        "OPENAI_IMAGE_OUTPUT_FORMAT": os.environ.get("OPENAI_IMAGE_OUTPUT_FORMAT"),
    }

    try:
        fake_openai_thread.start()
        fake_openai_base_url = f"http://{host}:{int(fake_openai.server_address[1])}"
        os.environ["OPENAI_API_KEY"] = "test-key"
        os.environ["OPENAI_BASE_URL"] = fake_openai_base_url
        os.environ["OPENAI_IMAGE_OUTPUT_FORMAT"] = output_format
        print(f"Fake OpenAI Images server listening on {fake_openai_base_url}", file=out_stream, flush=True)

        app = create_app(photo_provider=build_photo_provider("openai", photo_pack_root=photo_pack_root))
        bridge = create_http_server(host="0.0.0.0", port=bridge_port, app=app)
        actual_bridge_port = int(bridge.server_address[1])
        base_url = f"http://{host}:{actual_bridge_port}"
        bridge_thread = threading.Thread(target=bridge.serve_forever, daemon=True)
        bridge_thread.start()
        print(f"Pocket Agent mock bridge listening on http://0.0.0.0:{actual_bridge_port}", file=out_stream, flush=True)
        print(f"Simulator endpoint: {base_url}", file=out_stream, flush=True)

        if launch_app:
            print(f"Launching Simulator smoke for {bundle_id}", file=out_stream, flush=True)
            try:
                launcher(bundle_id, base_url, token)
            except Exception as error:
                print(f"Unable to launch Simulator smoke: {error}", file=err_stream, flush=True)
                return 1
        else:
            print("Simulator launch skipped; launch smoke mode manually.", file=out_stream, flush=True)

        connection_result = _wait_for_status(
            base_url=base_url,
            token=token,
            timeout_seconds=connection_timeout,
            interval_seconds=interval,
            evaluator=evaluate_connection_restore,
            status_fetcher=status_fetcher,
            phase="connection",
            receipt_file=receipt_file,
            out=out_stream,
            err=err_stream,
        )
        if connection_result != 0:
            return connection_result

        photo_result = _wait_for_status(
            base_url=base_url,
            token=token,
            timeout_seconds=photo_timeout,
            interval_seconds=interval,
            evaluator=evaluate_photo_flow,
            status_fetcher=status_fetcher,
            phase="photo-flow",
            receipt_file=receipt_file,
            out=out_stream,
            err=err_stream,
        )
        if photo_result == 0 and screenshot_file:
            try:
                screenshotter(screenshot_file)
                print(f"Simulator screenshot written to {screenshot_file}", file=out_stream, flush=True)
            except Exception as error:
                print(f"Unable to capture Simulator screenshot: {error}", file=err_stream, flush=True)
                return 1
        return photo_result
    finally:
        _write_receipt(fake_openai_status_file, fake_openai.status_payload())
        if bridge is not None:
            bridge.shutdown()
        if bridge_thread is not None:
            bridge_thread.join(timeout=2)
        if bridge is not None:
            bridge.server_close()
        fake_openai.shutdown()
        fake_openai_thread.join(timeout=2)
        fake_openai.server_close()
        _restore_env(previous_env)


def run_local_recipe_simulator_session(
    host: str = "127.0.0.1",
    bridge_port: int = 8769,
    bundle_id: str = DEFAULT_BUNDLE_ID,
    token: str = DEFAULT_TOKEN,
    connection_timeout: float = 45,
    photo_timeout: float = 90,
    interval: float = 1.0,
    photo_pack_root: str = "photo-pack",
    launch_app: bool = True,
    receipt_file: str = "docs/qa-receipts/simulator-local-recipe-photo-flow.json",
    screenshot_file: str = "",
    simulator_launcher: Optional[Callable[[str, str, str], None]] = None,
    simulator_screenshotter: Optional[Callable[[str], None]] = None,
    status_fetcher: Callable[..., Mapping[str, Any]] = fetch_qa_status,
    out=None,
    err=None,
) -> int:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr
    launcher = simulator_launcher or _launch_simulator_smoke
    screenshotter = simulator_screenshotter or _take_simulator_screenshot

    app = create_app(photo_provider=build_photo_provider("recipe_local", photo_pack_root=photo_pack_root))
    bridge = create_http_server(host="0.0.0.0", port=bridge_port, app=app)
    actual_bridge_port = int(bridge.server_address[1])
    base_url = f"http://{host}:{actual_bridge_port}"
    bridge_thread = threading.Thread(target=bridge.serve_forever, daemon=True)

    try:
        bridge_thread.start()
        print(f"Pocket Agent mock bridge listening on http://0.0.0.0:{actual_bridge_port}", file=out_stream, flush=True)
        print(f"Simulator local recipe endpoint: {base_url}", file=out_stream, flush=True)

        if launch_app:
            print(f"Launching Simulator local-recipe smoke for {bundle_id}", file=out_stream, flush=True)
            try:
                launcher(bundle_id, base_url, token)
            except Exception as error:
                print(f"Unable to launch Simulator local-recipe smoke: {error}", file=err_stream, flush=True)
                return 1
        else:
            print("Simulator launch skipped; launch smoke mode manually.", file=out_stream, flush=True)

        connection_result = _wait_for_status(
            base_url=base_url,
            token=token,
            timeout_seconds=connection_timeout,
            interval_seconds=interval,
            evaluator=evaluate_connection_restore,
            status_fetcher=status_fetcher,
            phase="connection",
            receipt_file=receipt_file,
            out=out_stream,
            err=err_stream,
        )
        if connection_result != 0:
            return connection_result

        photo_result = _wait_for_status(
            base_url=base_url,
            token=token,
            timeout_seconds=photo_timeout,
            interval_seconds=interval,
            evaluator=evaluate_local_recipe_photo_flow,
            status_fetcher=status_fetcher,
            phase="photo-flow",
            receipt_file=receipt_file,
            out=out_stream,
            err=err_stream,
        )
        if photo_result == 0 and screenshot_file:
            try:
                screenshotter(screenshot_file)
                print(f"Simulator local-recipe screenshot written to {screenshot_file}", file=out_stream, flush=True)
            except Exception as error:
                print(f"Unable to capture Simulator local-recipe screenshot: {error}", file=err_stream, flush=True)
                return 1
        return photo_result
    finally:
        bridge.shutdown()
        bridge_thread.join(timeout=2)
        bridge.server_close()


def run_simulator_capture_ready_session(
    bundle_id: str = DEFAULT_BUNDLE_ID,
    screenshot_file: str = "/tmp/agent-pocket-simulator-capture-ready.png",
    receipt_file: str = DEFAULT_SIMULATOR_CAPTURE_READY_RECEIPT,
    launch_app: bool = True,
    settle_seconds: float = 1.0,
    ready_timeout: float = 5.0,
    ready_interval: float = 0.25,
    render_settle_seconds: float = 0.25,
    screenshot_attempts: int = 9,
    screenshot_retry_interval: float = 0.75,
    simulator_launcher: Optional[Callable[[str], None]] = None,
    simulator_screenshotter: Optional[Callable[[str], None]] = None,
    simulator_receipt_cleaner: Optional[Callable[[str], None]] = None,
    simulator_receipt_reader: Optional[Callable[[str], Mapping[str, Any]]] = None,
    sleeper: Callable[[float], None] = time.sleep,
    out=None,
    err=None,
) -> int:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr
    launcher = simulator_launcher or _launch_simulator_capture_ready_smoke
    screenshotter = simulator_screenshotter or _take_simulator_screenshot
    receipt_cleaner = simulator_receipt_cleaner or _remove_simulator_capture_ready_receipt
    receipt_reader = simulator_receipt_reader or _read_simulator_capture_ready_receipt

    if receipt_file:
        try:
            receipt_cleaner(bundle_id)
        except Exception:
            pass

    if launch_app:
        try:
            print(f"Launching Simulator capture-ready smoke for {bundle_id}", file=out_stream, flush=True)
            launcher(bundle_id)
        except Exception as error:
            print(f"Unable to launch Simulator capture-ready smoke: {error}", file=err_stream, flush=True)
            return 1
    else:
        print("Simulator capture-ready launch skipped; launch the debug view manually.", file=out_stream, flush=True)

    if settle_seconds > 0:
        sleeper(settle_seconds)

    receipt: Optional[dict[str, Any]] = None
    if receipt_file:
        try:
            receipt = _wait_for_capture_ready_receipt(
                bundle_id,
                receipt_reader=receipt_reader,
                timeout_seconds=ready_timeout,
                interval_seconds=ready_interval,
                sleeper=sleeper,
            )
            _write_receipt(receipt_file, receipt)
            print(f"Simulator capture-ready receipt written to {receipt_file}", file=out_stream, flush=True)
        except Exception as error:
            print(f"Unable to read Simulator capture-ready receipt: {error}", file=err_stream, flush=True)
            return 1

    if render_settle_seconds > 0:
        sleeper(render_settle_seconds)

    if screenshot_file:
        try:
            _take_simulator_screenshot_until_visible(
                screenshot_file,
                screenshotter=screenshotter,
                attempts=screenshot_attempts,
                interval_seconds=screenshot_retry_interval,
                sleeper=sleeper,
            )
            print(f"Simulator capture-ready screenshot written to {screenshot_file}", file=out_stream, flush=True)
        except Exception as error:
            print(f"Unable to capture Simulator capture-ready screenshot: {error}", file=err_stream, flush=True)
            return 1

    return 0


def _capture_ready_receipt_is_ready(receipt: Mapping[str, Any]) -> bool:
    return (
        receipt.get("phase") == "capture-ready"
        and receipt.get("ok") is True
        and receipt.get("state") == "ready"
        and receipt.get("has_prepared_upload") is True
        and _capture_ready_send_enabled(receipt) is True
        and receipt.get("selection_source") == "library_fixture"
        and receipt.get("preprocessing_path") == "CaptureFlowViewModel.prepareSelectedImage"
        and receipt.get("primary_action") in {"Send to Pocket Agent", "Send to Local Agent", "Send to Hermes"}
    )


def _capture_ready_send_enabled(receipt: Mapping[str, Any]) -> bool | None:
    if "send_to_local_agent_enabled" in receipt:
        return receipt.get("send_to_local_agent_enabled") is True
    if "send_to_hermes_enabled" in receipt:
        return receipt.get("send_to_hermes_enabled") is True
    return None


def _wait_for_capture_ready_receipt(
    bundle_id: str,
    receipt_reader: Callable[[str], Mapping[str, Any]],
    timeout_seconds: float,
    interval_seconds: float,
    sleeper: Callable[[float], None],
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_error = "capture-ready receipt file"
    last_receipt: dict[str, Any] = {}

    while True:
        try:
            last_receipt = dict(receipt_reader(bundle_id))
            if _capture_ready_receipt_is_ready(last_receipt):
                return last_receipt
            last_error = "Simulator capture-ready receipt did not prove ready state."
        except Exception as error:
            last_error = str(error)

        remaining = deadline - time.monotonic()
        if remaining <= 0 or interval_seconds <= 0:
            break
        sleeper(min(interval_seconds, remaining))

    if last_receipt:
        raise RuntimeError(last_error)
    raise RuntimeError(f"Timed out waiting for {last_error}.")


def run_simulator_capture_completed_session(
    bundle_id: str = DEFAULT_BUNDLE_ID,
    screenshot_file: str = DEFAULT_SIMULATOR_CAPTURE_COMPLETED_SCREENSHOT,
    receipt_file: str = DEFAULT_SIMULATOR_CAPTURE_COMPLETED_RECEIPT,
    launch_app: bool = True,
    settle_seconds: float = 3.0,
    screenshot_attempts: int = 9,
    screenshot_retry_interval: float = 0.75,
    simulator_launcher: Optional[Callable[[str], None]] = None,
    simulator_screenshotter: Optional[Callable[[str], None]] = None,
    simulator_receipt_cleaner: Optional[Callable[[str], None]] = None,
    simulator_receipt_reader: Optional[Callable[[str], Mapping[str, Any]]] = None,
    sleeper: Callable[[float], None] = time.sleep,
    out=None,
    err=None,
) -> int:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr
    launcher = simulator_launcher or _launch_simulator_capture_completed_smoke
    screenshotter = simulator_screenshotter or _take_simulator_screenshot
    receipt_cleaner = simulator_receipt_cleaner or _remove_simulator_capture_completed_receipt
    receipt_reader = simulator_receipt_reader or _read_simulator_capture_completed_receipt

    if receipt_file:
        try:
            receipt_cleaner(bundle_id)
        except Exception:
            pass

    if launch_app:
        try:
            print(f"Launching Simulator capture-completed smoke for {bundle_id}", file=out_stream, flush=True)
            launcher(bundle_id)
        except Exception as error:
            print(f"Unable to launch Simulator capture-completed smoke: {error}", file=err_stream, flush=True)
            return 1
    else:
        print("Simulator capture-completed launch skipped; launch the debug view manually.", file=out_stream, flush=True)

    if settle_seconds > 0:
        sleeper(settle_seconds)

    if screenshot_file:
        try:
            _take_simulator_screenshot_until_visible(
                screenshot_file,
                screenshotter=screenshotter,
                attempts=screenshot_attempts,
                interval_seconds=screenshot_retry_interval,
                sleeper=sleeper,
            )
            print(f"Simulator capture-completed screenshot written to {screenshot_file}", file=out_stream, flush=True)
        except Exception as error:
            print(f"Unable to capture Simulator capture-completed screenshot: {error}", file=err_stream, flush=True)
            return 1

    if receipt_file:
        try:
            receipt = dict(receipt_reader(bundle_id))
            _write_receipt(receipt_file, receipt)
            print(f"Simulator capture-completed receipt written to {receipt_file}", file=out_stream, flush=True)
        except Exception as error:
            print(f"Unable to read Simulator capture-completed receipt: {error}", file=err_stream, flush=True)
            return 1
        receipt_ok = _capture_completed_receipt_is_ready(receipt)
        if not receipt_ok:
            print("Simulator capture-completed receipt did not prove the Review Results primary action.", file=err_stream, flush=True)
            return 1

    return 0


def run_simulator_result_gallery_session(
    bundle_id: str = DEFAULT_BUNDLE_ID,
    screenshot_file: str = DEFAULT_SIMULATOR_RESULT_GALLERY_SCREENSHOT,
    receipt_file: str = DEFAULT_SIMULATOR_RESULT_GALLERY_RECEIPT,
    launch_app: bool = True,
    settle_seconds: float = 2.0,
    screenshot_attempts: int = 9,
    screenshot_retry_interval: float = 0.75,
    simulator_launcher: Optional[Callable[[str], None]] = None,
    simulator_screenshotter: Optional[Callable[[str], None]] = None,
    simulator_receipt_cleaner: Optional[Callable[[str], None]] = None,
    simulator_receipt_reader: Optional[Callable[[str], Mapping[str, Any]]] = None,
    sleeper: Callable[[float], None] = time.sleep,
    out=None,
    err=None,
) -> int:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr
    launcher = simulator_launcher or _launch_simulator_result_gallery_smoke
    screenshotter = simulator_screenshotter or _take_simulator_screenshot
    receipt_cleaner = simulator_receipt_cleaner or _remove_simulator_result_gallery_receipt
    receipt_reader = simulator_receipt_reader or _read_simulator_result_gallery_receipt

    if receipt_file:
        try:
            receipt_cleaner(bundle_id)
        except Exception:
            pass

    if launch_app:
        try:
            print(f"Launching Simulator result-gallery smoke for {bundle_id}", file=out_stream, flush=True)
            launcher(bundle_id)
        except Exception as error:
            print(f"Unable to launch Simulator result-gallery smoke: {error}", file=err_stream, flush=True)
            return 1
    else:
        print("Simulator result-gallery launch skipped; launch the debug view manually.", file=out_stream, flush=True)

    if settle_seconds > 0:
        sleeper(settle_seconds)

    if screenshot_file:
        try:
            _take_simulator_screenshot_until_visible(
                screenshot_file,
                screenshotter=screenshotter,
                attempts=screenshot_attempts,
                interval_seconds=screenshot_retry_interval,
                sleeper=sleeper,
            )
            print(f"Simulator result-gallery screenshot written to {screenshot_file}", file=out_stream, flush=True)
        except Exception as error:
            print(f"Unable to capture Simulator result-gallery screenshot: {error}", file=err_stream, flush=True)
            return 1

    if receipt_file:
        try:
            receipt = dict(receipt_reader(bundle_id))
            _write_receipt(receipt_file, receipt)
            print(f"Simulator result-gallery receipt written to {receipt_file}", file=out_stream, flush=True)
        except Exception as error:
            print(f"Unable to read Simulator result-gallery receipt: {error}", file=err_stream, flush=True)
            return 1
        receipt_ok = _result_gallery_receipt_is_ready(receipt)
        if not receipt_ok:
            print("Simulator result-gallery receipt did not prove a ready result review state.", file=err_stream, flush=True)
            return 1

    return 0


def run_simulator_result_gallery_downloaded_session(
    bundle_id: str = DEFAULT_BUNDLE_ID,
    screenshot_file: str = DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_SCREENSHOT,
    receipt_file: str = DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_RECEIPT,
    launch_app: bool = True,
    settle_seconds: float = 2.0,
    screenshot_attempts: int = 9,
    screenshot_retry_interval: float = 0.75,
    simulator_launcher: Optional[Callable[[str], None]] = None,
    simulator_screenshotter: Optional[Callable[[str], None]] = None,
    simulator_receipt_cleaner: Optional[Callable[[str], None]] = None,
    simulator_receipt_reader: Optional[Callable[[str], Mapping[str, Any]]] = None,
    sleeper: Callable[[float], None] = time.sleep,
    out=None,
    err=None,
) -> int:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr
    launcher = simulator_launcher or _launch_simulator_result_gallery_downloaded_smoke
    screenshotter = simulator_screenshotter or _take_simulator_screenshot
    receipt_cleaner = simulator_receipt_cleaner or _remove_simulator_result_gallery_downloaded_receipt
    receipt_reader = simulator_receipt_reader or _read_simulator_result_gallery_downloaded_receipt

    if receipt_file:
        try:
            receipt_cleaner(bundle_id)
        except Exception:
            pass

    if launch_app:
        try:
            print(f"Launching Simulator result-gallery downloaded smoke for {bundle_id}", file=out_stream, flush=True)
            launcher(bundle_id)
        except Exception as error:
            print(f"Unable to launch Simulator result-gallery downloaded smoke: {error}", file=err_stream, flush=True)
            return 1
    else:
        print("Simulator result-gallery downloaded launch skipped; launch the debug view manually.", file=out_stream, flush=True)

    if settle_seconds > 0:
        sleeper(settle_seconds)

    if screenshot_file:
        try:
            _take_simulator_screenshot_until_visible(
                screenshot_file,
                screenshotter=screenshotter,
                attempts=screenshot_attempts,
                interval_seconds=screenshot_retry_interval,
                sleeper=sleeper,
            )
            print(f"Simulator result-gallery downloaded screenshot written to {screenshot_file}", file=out_stream, flush=True)
        except Exception as error:
            print(f"Unable to capture Simulator result-gallery downloaded screenshot: {error}", file=err_stream, flush=True)
            return 1

    if receipt_file:
        try:
            receipt = dict(receipt_reader(bundle_id))
            _write_receipt(receipt_file, receipt)
            print(f"Simulator result-gallery downloaded receipt written to {receipt_file}", file=out_stream, flush=True)
        except Exception as error:
            print(f"Unable to read Simulator result-gallery downloaded receipt: {error}", file=err_stream, flush=True)
            return 1
        receipt_ok = _result_gallery_downloaded_receipt_is_ready(receipt)
        if not receipt_ok:
            print("Simulator result-gallery downloaded receipt did not prove a downloaded result state.", file=err_stream, flush=True)
            return 1

    return 0


def run_simulator_share_sheet_session(
    bundle_id: str = DEFAULT_BUNDLE_ID,
    screenshot_file: str = DEFAULT_SIMULATOR_SHARE_SHEET_SCREENSHOT,
    receipt_file: str = DEFAULT_SIMULATOR_SHARE_SHEET_RECEIPT,
    launch_app: bool = True,
    settle_seconds: float = 2.0,
    screenshot_attempts: int = 9,
    screenshot_retry_interval: float = 0.75,
    simulator_launcher: Optional[Callable[[str], None]] = None,
    simulator_screenshotter: Optional[Callable[[str], None]] = None,
    simulator_receipt_cleaner: Optional[Callable[[str], None]] = None,
    simulator_receipt_reader: Optional[Callable[[str], Mapping[str, Any]]] = None,
    sleeper: Callable[[float], None] = time.sleep,
    out=None,
    err=None,
) -> int:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr
    launcher = simulator_launcher or _launch_simulator_share_sheet_smoke
    screenshotter = simulator_screenshotter or _take_simulator_screenshot
    receipt_cleaner = simulator_receipt_cleaner or _remove_simulator_share_sheet_receipt
    receipt_reader = simulator_receipt_reader or _read_simulator_share_sheet_receipt

    if receipt_file:
        try:
            receipt_cleaner(bundle_id)
        except Exception:
            pass

    if launch_app:
        try:
            print(f"Launching Simulator share-sheet smoke for {bundle_id}", file=out_stream, flush=True)
            launcher(bundle_id)
        except Exception as error:
            print(f"Unable to launch Simulator share-sheet smoke: {error}", file=err_stream, flush=True)
            return 1
    else:
        print("Simulator share-sheet launch skipped; launch the debug view manually.", file=out_stream, flush=True)

    if settle_seconds > 0:
        sleeper(settle_seconds)

    if screenshot_file:
        try:
            _take_simulator_screenshot_until_visible(
                screenshot_file,
                screenshotter=screenshotter,
                attempts=screenshot_attempts,
                interval_seconds=screenshot_retry_interval,
                sleeper=sleeper,
            )
            print(f"Simulator share-sheet screenshot written to {screenshot_file}", file=out_stream, flush=True)
        except Exception as error:
            print(f"Unable to capture Simulator share-sheet screenshot: {error}", file=err_stream, flush=True)
            return 1

    if receipt_file:
        try:
            receipt = dict(receipt_reader(bundle_id))
            _write_receipt(receipt_file, receipt)
            print(f"Simulator share-sheet receipt written to {receipt_file}", file=out_stream, flush=True)
        except Exception as error:
            print(f"Unable to read Simulator share-sheet receipt: {error}", file=err_stream, flush=True)
            return 1
        receipt_ok = _share_sheet_receipt_is_ready(receipt)
        if not receipt_ok:
            print("Simulator share-sheet receipt did not prove a system share handoff.", file=err_stream, flush=True)
            return 1

    return 0


def run_simulator_picker_ui_session(
    bundle_id: str = DEFAULT_BUNDLE_ID,
    screenshot_file: str = DEFAULT_SIMULATOR_PICKER_UI_SCREENSHOT,
    launch_app: bool = True,
    settle_seconds: float = 1.0,
    screenshot_attempts: int = 9,
    screenshot_retry_interval: float = 0.75,
    simulator_launcher: Optional[Callable[[str], None]] = None,
    simulator_screenshotter: Optional[Callable[[str], None]] = None,
    sleeper: Callable[[float], None] = time.sleep,
    out=None,
    err=None,
) -> int:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr
    launcher = simulator_launcher or _launch_simulator_picker_ui_smoke
    screenshotter = simulator_screenshotter or _take_simulator_screenshot

    if launch_app:
        try:
            print(f"Launching Simulator picker UI smoke for {bundle_id}", file=out_stream, flush=True)
            launcher(bundle_id)
        except Exception as error:
            print(f"Unable to launch Simulator picker UI smoke: {error}", file=err_stream, flush=True)
            return 1
    else:
        print("Simulator picker UI launch skipped; launch the debug view manually.", file=out_stream, flush=True)

    if settle_seconds > 0:
        sleeper(settle_seconds)

    if screenshot_file:
        try:
            _take_simulator_screenshot_until_visible(
                screenshot_file,
                screenshotter=screenshotter,
                attempts=screenshot_attempts,
                interval_seconds=screenshot_retry_interval,
                sleeper=sleeper,
            )
            print(f"Simulator picker UI screenshot written to {screenshot_file}", file=out_stream, flush=True)
        except Exception as error:
            print(f"Unable to capture Simulator picker UI screenshot: {error}", file=err_stream, flush=True)
            return 1

    return 0


def run_simulator_seed_photo_library(
    device: str = "booted",
    image_file: str = DEFAULT_SIMULATOR_LIBRARY_FIXTURE,
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
) -> Mapping[str, Any]:
    _write_simulator_library_fixture(image_file)
    command = ["xcrun", "simctl", "addmedia", device, image_file]
    runner = command_runner or _run_command
    result = runner(command)
    ok = result.returncode == 0
    return {
        "ok": ok,
        "device": device,
        "image_file": image_file,
        "command": command,
        "stdout": result.stdout.strip(),
        "error": "" if ok else _clean_error(result),
    }


def run_simulator_suite(
    host: str = "127.0.0.1",
    bundle_id: str = DEFAULT_BUNDLE_ID,
    token: str = DEFAULT_TOKEN,
    connection_port: int = 8766,
    discovery_refresh_port: int = 8767,
    openai_bridge_port: int = 8769,
    fake_openai_port: int = 8781,
    simulator_ui_test_preflight_receipt: str = DEFAULT_SIMULATOR_UI_TEST_PREFLIGHT_RECEIPT,
    simulator_connection_receipt: str = "docs/qa-receipts/simulator-connection-latest.json",
    discovery_refresh_receipt: str = DEFAULT_SIMULATOR_DISCOVERY_REFRESH_RECEIPT,
    discovery_refresh_screenshot: str = DEFAULT_SIMULATOR_DISCOVERY_REFRESH_SCREENSHOT,
    library_fixture: str = DEFAULT_SIMULATOR_LIBRARY_FIXTURE,
    picker_ui_screenshot: str = DEFAULT_SIMULATOR_PICKER_UI_SCREENSHOT,
    capture_ready_screenshot: str = "/tmp/agent-pocket-simulator-capture-ready.png",
    capture_ready_receipt: str = DEFAULT_SIMULATOR_CAPTURE_READY_RECEIPT,
    capture_completed_screenshot: str = DEFAULT_SIMULATOR_CAPTURE_COMPLETED_SCREENSHOT,
    capture_completed_receipt: str = DEFAULT_SIMULATOR_CAPTURE_COMPLETED_RECEIPT,
    result_gallery_screenshot: str = DEFAULT_SIMULATOR_RESULT_GALLERY_SCREENSHOT,
    result_gallery_receipt: str = DEFAULT_SIMULATOR_RESULT_GALLERY_RECEIPT,
    result_gallery_downloaded_screenshot: str = DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_SCREENSHOT,
    result_gallery_downloaded_receipt: str = DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_RECEIPT,
    openai_receipt: str = "docs/qa-receipts/simulator-openai-compatible-photo-flow-screenshot.json",
    fake_openai_status_file: str = "docs/qa-receipts/simulator-openai-compatible-fake-openai-status-screenshot.json",
    openai_screenshot: str = "/tmp/agent-pocket-simulator-openai-provider-smoke-autocapture.png",
    suite_receipt_file: str = DEFAULT_SIMULATOR_SUITE_RECEIPT,
    connection_timeout: float = 45,
    photo_timeout: float = 90,
    interval: float = 1.0,
    photo_pack_root: str = "photo-pack",
    ui_test_preflight_builder: Optional[Callable[[], Mapping[str, Any]]] = None,
    seed_photo_library_runner: Optional[Callable[..., Mapping[str, Any]]] = None,
    connection_session_runner: Optional[Callable[..., int]] = None,
    discovery_refresh_session_runner: Optional[Callable[..., int]] = None,
    picker_ui_session_runner: Optional[Callable[..., int]] = None,
    capture_ready_session_runner: Optional[Callable[..., int]] = None,
    capture_completed_session_runner: Optional[Callable[..., int]] = None,
    result_gallery_session_runner: Optional[Callable[..., int]] = None,
    result_gallery_downloaded_session_runner: Optional[Callable[..., int]] = None,
    openai_session_runner: Optional[Callable[..., int]] = None,
    out=None,
    err=None,
) -> Mapping[str, Any]:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr
    ui_builder = ui_test_preflight_builder or (
        lambda: build_simulator_ui_test_preflight_report(bundle_id=bundle_id)
    )
    seed_runner = seed_photo_library_runner or run_simulator_seed_photo_library
    connection_runner = connection_session_runner or run_simulator_connection_session
    discovery_refresh_runner = discovery_refresh_session_runner or run_simulator_discovery_refresh_session
    picker_runner = picker_ui_session_runner or run_simulator_picker_ui_session
    capture_runner = capture_ready_session_runner or run_simulator_capture_ready_session
    capture_completed_runner = capture_completed_session_runner or run_simulator_capture_completed_session
    result_gallery_runner = result_gallery_session_runner or run_simulator_result_gallery_session
    result_gallery_downloaded_runner = result_gallery_downloaded_session_runner or run_simulator_result_gallery_downloaded_session
    openai_runner = openai_session_runner or run_openai_compatible_simulator_session

    steps: dict[str, Mapping[str, Any]] = {}

    print("Checking local Xcode UI test readiness...", file=out_stream, flush=True)
    ui_preflight = dict(ui_builder())
    _write_receipt(simulator_ui_test_preflight_receipt, ui_preflight)
    steps["ui_test_preflight"] = _simulator_suite_ui_step(ui_preflight, simulator_ui_test_preflight_receipt)

    print("Seeding Simulator photo library...", file=out_stream, flush=True)
    seed_result = seed_runner(device="booted", image_file=library_fixture)
    steps["seed_photo_library"] = {
        "ok": bool(seed_result.get("ok")),
        "required": True,
        "receipt": library_fixture,
        "detail": seed_result,
    }

    print("Running normal-app Simulator connection smoke...", file=out_stream, flush=True)
    connection_code = connection_runner(
        host=host,
        port=connection_port,
        bundle_id=bundle_id,
        token=token,
        connection_timeout=connection_timeout,
        interval=interval,
        receipt_file=simulator_connection_receipt,
        out=out_stream,
        err=err_stream,
    )
    steps["connection_smoke"] = _simulator_suite_returncode_step(
        connection_code,
        simulator_connection_receipt,
        required=True,
    )

    print("Running no-payload discovery refresh smoke...", file=out_stream, flush=True)
    discovery_refresh_code = discovery_refresh_runner(
        host=host,
        port=discovery_refresh_port,
        bundle_id=bundle_id,
        token=token,
        connection_timeout=connection_timeout,
        interval=interval,
        receipt_file=discovery_refresh_receipt,
        screenshot_file=discovery_refresh_screenshot,
        out=out_stream,
        err=err_stream,
    )
    steps["discovery_refresh_smoke"] = _simulator_suite_returncode_step(
        discovery_refresh_code,
        discovery_refresh_receipt,
        required=True,
    )
    steps["discovery_refresh_smoke"]["screenshot"] = discovery_refresh_screenshot

    print("Capturing connected PhotosPicker entry UI...", file=out_stream, flush=True)
    picker_code = picker_runner(
        bundle_id=bundle_id,
        screenshot_file=picker_ui_screenshot,
        out=out_stream,
        err=err_stream,
    )
    steps["picker_ui_smoke"] = _simulator_suite_returncode_step(
        picker_code,
        picker_ui_screenshot,
        required=True,
    )

    print("Capturing selected-photo ready UI...", file=out_stream, flush=True)
    capture_code = capture_runner(
        bundle_id=bundle_id,
        screenshot_file=capture_ready_screenshot,
        receipt_file=capture_ready_receipt,
        out=out_stream,
        err=err_stream,
    )
    steps["capture_ready_smoke"] = _simulator_suite_returncode_step(
        capture_code,
        capture_ready_receipt,
        required=True,
    )
    steps["capture_ready_smoke"]["screenshot"] = capture_ready_screenshot

    print("Capturing completed capture UI...", file=out_stream, flush=True)
    capture_completed_code = capture_completed_runner(
        bundle_id=bundle_id,
        screenshot_file=capture_completed_screenshot,
        receipt_file=capture_completed_receipt,
        out=out_stream,
        err=err_stream,
    )
    steps["capture_completed_smoke"] = _simulator_suite_returncode_step(
        capture_completed_code,
        capture_completed_receipt,
        required=True,
    )
    steps["capture_completed_smoke"]["screenshot"] = capture_completed_screenshot

    print("Capturing result gallery UI...", file=out_stream, flush=True)
    result_gallery_code = result_gallery_runner(
        bundle_id=bundle_id,
        screenshot_file=result_gallery_screenshot,
        receipt_file=result_gallery_receipt,
        out=out_stream,
        err=err_stream,
    )
    steps["result_gallery_smoke"] = _simulator_suite_returncode_step(
        result_gallery_code,
        result_gallery_receipt,
        required=True,
    )
    steps["result_gallery_smoke"]["screenshot"] = result_gallery_screenshot

    print("Capturing downloaded result gallery UI...", file=out_stream, flush=True)
    result_gallery_downloaded_code = result_gallery_downloaded_runner(
        bundle_id=bundle_id,
        screenshot_file=result_gallery_downloaded_screenshot,
        receipt_file=result_gallery_downloaded_receipt,
        out=out_stream,
        err=err_stream,
    )
    steps["result_gallery_downloaded_smoke"] = _simulator_suite_returncode_step(
        result_gallery_downloaded_code,
        result_gallery_downloaded_receipt,
        required=True,
    )
    steps["result_gallery_downloaded_smoke"]["screenshot"] = result_gallery_downloaded_screenshot

    print("Running OpenAI-compatible Simulator smoke with local fake OpenAI...", file=out_stream, flush=True)
    openai_code = openai_runner(
        host=host,
        bridge_port=openai_bridge_port,
        fake_openai_port=fake_openai_port,
        bundle_id=bundle_id,
        token=token,
        connection_timeout=connection_timeout,
        photo_timeout=photo_timeout,
        interval=interval,
        photo_pack_root=photo_pack_root,
        receipt_file=openai_receipt,
        fake_openai_status_file=fake_openai_status_file,
        screenshot_file=openai_screenshot,
        out=out_stream,
        err=err_stream,
    )
    steps["openai_smoke"] = _simulator_suite_returncode_step(
        openai_code,
        openai_receipt,
        required=True,
    )

    failed_required_steps = [
        name
        for name, step in steps.items()
        if step.get("required") and not step.get("ok")
    ]
    payload = {
        "ok": not failed_required_steps,
        "phase": "simulator-suite",
        "failed_required_steps": failed_required_steps,
        "steps": steps,
    }
    _write_receipt(suite_receipt_file, payload)
    return payload


def run_simulator_only_resume(
    root: str = ".",
    host: str = "127.0.0.1",
    bundle_id: str = DEFAULT_BUNDLE_ID,
    token: str = DEFAULT_TOKEN,
    connection_port: int = 8766,
    discovery_refresh_port: int = 8767,
    openai_bridge_port: int = 8769,
    fake_openai_port: int = 8781,
    gate_f_port: int = 8765,
    connection_timeout: float = 45,
    photo_timeout: float = 90,
    interval: float = 1.0,
    photo_pack_root: str = "photo-pack",
    suite_receipt_file: str = DEFAULT_SIMULATOR_SUITE_RECEIPT,
    simulator_ui_test_preflight_receipt: str = DEFAULT_SIMULATOR_UI_TEST_PREFLIGHT_RECEIPT,
    simulator_connection_receipt: str = "docs/qa-receipts/simulator-connection-latest.json",
    discovery_refresh_receipt: str = DEFAULT_SIMULATOR_DISCOVERY_REFRESH_RECEIPT,
    discovery_refresh_screenshot: str = DEFAULT_SIMULATOR_DISCOVERY_REFRESH_SCREENSHOT,
    library_fixture: str = DEFAULT_SIMULATOR_LIBRARY_FIXTURE,
    picker_ui_screenshot: str = DEFAULT_SIMULATOR_PICKER_UI_SCREENSHOT,
    capture_ready_screenshot: str = "/tmp/agent-pocket-simulator-capture-ready.png",
    capture_ready_receipt: str = DEFAULT_SIMULATOR_CAPTURE_READY_RECEIPT,
    capture_completed_screenshot: str = DEFAULT_SIMULATOR_CAPTURE_COMPLETED_SCREENSHOT,
    capture_completed_receipt: str = DEFAULT_SIMULATOR_CAPTURE_COMPLETED_RECEIPT,
    result_gallery_screenshot: str = DEFAULT_SIMULATOR_RESULT_GALLERY_SCREENSHOT,
    result_gallery_receipt: str = DEFAULT_SIMULATOR_RESULT_GALLERY_RECEIPT,
    result_gallery_downloaded_screenshot: str = DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_SCREENSHOT,
    result_gallery_downloaded_receipt: str = DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_RECEIPT,
    openai_receipt: str = "docs/qa-receipts/simulator-openai-compatible-photo-flow-screenshot.json",
    fake_openai_status_file: str = "docs/qa-receipts/simulator-openai-compatible-fake-openai-status-screenshot.json",
    openai_screenshot: str = "/tmp/agent-pocket-simulator-openai-provider-smoke-autocapture.png",
    gate_f_preflight_receipt: str = DEFAULT_GATE_F_PREFLIGHT_RECEIPT,
    physical_openai_receipt: str = "docs/qa-receipts/openai-photo-flow.json",
    resume_receipt_file: str = DEFAULT_SIMULATOR_ONLY_RESUME_RECEIPT,
    readiness_output_file: str = "docs/agent-pocket-readiness.md",
    gate_f_host: str = "",
    env_file: str = "",
    hermes_home: str = "",
    hermes_profile: str = "",
    out=None,
    err=None,
) -> Mapping[str, Any]:
    suite = run_simulator_suite(
        host=host,
        bundle_id=bundle_id,
        token=token,
        connection_port=connection_port,
        discovery_refresh_port=discovery_refresh_port,
        openai_bridge_port=openai_bridge_port,
        fake_openai_port=fake_openai_port,
        simulator_ui_test_preflight_receipt=simulator_ui_test_preflight_receipt,
        simulator_connection_receipt=simulator_connection_receipt,
        discovery_refresh_receipt=discovery_refresh_receipt,
        discovery_refresh_screenshot=discovery_refresh_screenshot,
        library_fixture=library_fixture,
        picker_ui_screenshot=picker_ui_screenshot,
        capture_ready_screenshot=capture_ready_screenshot,
        capture_ready_receipt=capture_ready_receipt,
        capture_completed_screenshot=capture_completed_screenshot,
        capture_completed_receipt=capture_completed_receipt,
        result_gallery_screenshot=result_gallery_screenshot,
        result_gallery_receipt=result_gallery_receipt,
        result_gallery_downloaded_screenshot=result_gallery_downloaded_screenshot,
        result_gallery_downloaded_receipt=result_gallery_downloaded_receipt,
        openai_receipt=openai_receipt,
        fake_openai_status_file=fake_openai_status_file,
        openai_screenshot=openai_screenshot,
        suite_receipt_file=suite_receipt_file,
        connection_timeout=connection_timeout,
        photo_timeout=photo_timeout,
        interval=interval,
        photo_pack_root=photo_pack_root,
        out=out,
        err=err,
    )
    provider_source_args = _provider_source_command_args(
        env_file=env_file,
        hermes_home=hermes_home,
        hermes_profile=hermes_profile,
    )
    env_values, effective_env_file, hermes_context = _provider_env_from_sources(
        env_file=env_file,
        hermes_home=hermes_home,
        hermes_profile=hermes_profile,
    )
    gate_f = build_gate_f_preflight_report(
        root=root,
        port=gate_f_port,
        bundle_id=bundle_id,
        photo_pack_root=photo_pack_root,
        physical_openai_receipt=physical_openai_receipt,
        host=gate_f_host,
        env=env_values,
        env_file=effective_env_file,
        provider_source_args=provider_source_args,
    )
    _write_receipt(gate_f_preflight_receipt, gate_f)

    audit = build_gate_audit_report(
        root=root,
        simulator_connection_receipt=simulator_connection_receipt,
        openai_receipt=openai_receipt,
        fake_openai_status_file=fake_openai_status_file,
        simulator_ui_test_preflight_receipt=simulator_ui_test_preflight_receipt,
        simulator_suite_receipt=suite_receipt_file,
        gate_f_preflight_receipt=gate_f_preflight_receipt,
        screenshot_file=openai_screenshot,
        picker_ui_screenshot_file=picker_ui_screenshot,
        discovery_refresh_receipt_file=discovery_refresh_receipt,
        discovery_refresh_screenshot_file=discovery_refresh_screenshot,
        capture_ready_receipt_file=capture_ready_receipt,
        capture_ready_screenshot_file=capture_ready_screenshot,
        capture_completed_receipt_file=capture_completed_receipt,
        capture_completed_screenshot_file=capture_completed_screenshot,
        result_gallery_receipt_file=result_gallery_receipt,
        result_gallery_screenshot_file=result_gallery_screenshot,
        result_gallery_downloaded_receipt_file=result_gallery_downloaded_receipt,
        result_gallery_downloaded_screenshot_file=result_gallery_downloaded_screenshot,
        physical_openai_receipt=physical_openai_receipt,
        env=env_values,
        provider_source_args=provider_source_args,
    )
    markdown = build_readiness_markdown(audit)
    if readiness_output_file:
        parent = os.path.dirname(readiness_output_file)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(readiness_output_file, "w", encoding="utf-8") as handle:
            handle.write(markdown)

    report = {
        "ok": bool(suite.get("ok")),
        "phase": "simulator-only-resume",
        "execution_mode": "local-mac-simulator-only",
        "physical_iphone_used": False,
        "physical_device_launch_attempted": False,
        "real_device_commands_executed": [],
        "resume_receipt": {
            "path": resume_receipt_file,
            "written": bool(resume_receipt_file),
        },
        "simulator_suite": suite,
        "gate_f_preflight": {
            "path": gate_f_preflight_receipt,
            "ok": bool(gate_f.get("ok")),
            "ready_to_run": bool(gate_f.get("ready_to_run")),
            "missing_to_start": gate_f.get("missing_to_start", []),
            "missing_to_close": gate_f.get("missing_to_close", []),
        },
        "provider_source": {
            "args": provider_source_args,
            "env_file": effective_env_file,
            "hermes": hermes_context,
        },
        "readiness_report": {
            "path": readiness_output_file,
            "written": bool(readiness_output_file),
        },
        "gate_audit_summary": audit.get("summary", {}),
    }
    if resume_receipt_file:
        _write_receipt(resume_receipt_file, report)
    return report


def run_test_receipt_command(
    name: str,
    command: Sequence[str],
    receipt_file: str,
    timeout_seconds: float = 300,
    command_runner: Optional[Callable[[list[str]], CommandResult]] = None,
    out=None,
    err=None,
) -> int:
    out_stream = out or sys.stdout
    err_stream = err or sys.stderr
    command = list(command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("test-receipt requires a command after --.", file=err_stream)
        return 2

    result = command_runner(command) if command_runner is not None else _run_command(command, timeout_seconds=timeout_seconds)
    payload = _test_receipt_payload(name=name, command=command, result=result)
    _write_receipt(receipt_file, payload)
    _print_json(payload, stream=out_stream if payload["ok"] else err_stream)
    return 0 if payload["ok"] else result.returncode or 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "commands":
        print("\n".join(build_physical_qa_commands(
            host=args.host,
            port=args.port,
            device_id=args.device_id,
            bundle_id=args.bundle_id,
        )))
        return 0

    if args.command == "status":
        status = fetch_qa_status(args.base_url, token=args.token)
        _print_json(status)
        return 0

    if args.command == "smoke-real-provider":
        smoke_mode = _smoke_real_provider_mode(args.mode, getattr(args, "provider", ""))
        provider = _smoke_real_provider_name(smoke_mode)
        missing_key = _smoke_real_provider_missing_key(provider)
        if missing_key:
            provider_flag = "--real" if smoke_mode == "real" else f"--provider {provider}"
            report = {
                "schema_version": "kaka.smoke_real_provider.v1",
                "surface": "mock_bridge_server_smoke",
                "ok": False,
                "mode": smoke_mode,
                "provider": provider,
                "base_url": str(args.base_url).rstrip("/"),
                "steps": [],
                "artifacts": {},
                "tasks": {},
                "recall": {},
                "error": {
                    "code": f"missing_{provider}_api_key",
                    "message": f"{missing_key} is required for smoke-real-provider {provider_flag}.",
                },
            }
            _print_json(report, stream=sys.stderr)
            return 2
        report = run_smoke_real_provider(
            mode=smoke_mode,
            base_url=args.base_url,
            host=args.host,
            port=args.port,
            token=args.token,
            timeout_seconds=args.timeout,
            interval_seconds=args.interval,
            image_file=args.image_file,
            photo_pack_root=args.photo_pack_root,
        )
        _print_json(report, stream=sys.stdout if report["ok"] else sys.stderr)
        return 0 if report["ok"] else 1

    if args.command == "preflight":
        _print_json(build_preflight_report(port=args.port, bundle_id=args.bundle_id))
        return 0

    if args.command == "physical-device-preflight":
        report = build_physical_device_preflight_report(
            project=args.project,
            scheme=args.scheme,
            device_id=args.device_id,
            target=args.target,
            configuration=args.configuration,
            build_check=args.build_check,
        )
        _write_receipt(args.receipt_file, report)
        _print_json(report)
        return 0

    if args.command == "simulator-preflight":
        _print_json(build_simulator_preflight_report(
            app_path=args.app_path,
            port=args.port,
            bundle_id=args.bundle_id,
            gate_f_host=args.gate_f_host,
        ))
        return 0

    if args.command == "simulator-ui-test-preflight":
        report = build_simulator_ui_test_preflight_report(
            project=args.project,
            scheme=args.scheme,
            test_target=args.test_target,
            bundle_id=args.bundle_id,
        )
        _write_receipt(args.receipt_file, report)
        _print_json(report)
        return 0

    if args.command == "simulator-suite":
        report = run_simulator_suite(
            host=args.host,
            bundle_id=args.bundle_id,
            token=args.token,
            connection_port=args.connection_port,
            discovery_refresh_port=args.discovery_refresh_port,
            openai_bridge_port=args.openai_port,
            fake_openai_port=args.fake_openai_port,
            simulator_ui_test_preflight_receipt=args.simulator_ui_test_preflight_receipt,
            simulator_connection_receipt=args.simulator_connection_receipt,
            discovery_refresh_receipt=args.discovery_refresh_receipt,
            discovery_refresh_screenshot=args.discovery_refresh_screenshot,
            library_fixture=args.library_fixture,
            picker_ui_screenshot=args.picker_ui_screenshot,
            capture_ready_screenshot=args.capture_ready_screenshot,
            capture_ready_receipt=args.capture_ready_receipt,
            capture_completed_screenshot=args.capture_completed_screenshot,
            capture_completed_receipt=args.capture_completed_receipt,
            result_gallery_screenshot=args.result_gallery_screenshot,
            result_gallery_receipt=args.result_gallery_receipt,
            result_gallery_downloaded_screenshot=args.result_gallery_downloaded_screenshot,
            result_gallery_downloaded_receipt=args.result_gallery_downloaded_receipt,
            openai_receipt=args.openai_receipt,
            fake_openai_status_file=args.fake_openai_status_file,
            openai_screenshot=args.openai_screenshot,
            suite_receipt_file=args.suite_receipt_file,
            connection_timeout=args.connection_timeout,
            photo_timeout=args.photo_timeout,
            interval=args.interval,
            photo_pack_root=args.photo_pack_root,
            out=sys.stderr,
            err=sys.stderr,
        )
        _print_json(report, stream=sys.stdout if report["ok"] else sys.stderr)
        return 0 if report["ok"] else 1

    if args.command == "simulator-only-resume":
        report = run_simulator_only_resume(
            root=args.root,
            host=args.host,
            bundle_id=args.bundle_id,
            token=args.token,
            connection_port=args.connection_port,
            discovery_refresh_port=args.discovery_refresh_port,
            openai_bridge_port=args.openai_port,
            fake_openai_port=args.fake_openai_port,
            gate_f_port=args.gate_f_port,
            connection_timeout=args.connection_timeout,
            photo_timeout=args.photo_timeout,
            interval=args.interval,
            photo_pack_root=args.photo_pack_root,
            suite_receipt_file=args.suite_receipt_file,
            gate_f_preflight_receipt=args.gate_f_preflight_receipt,
            resume_receipt_file=args.resume_receipt_file,
            physical_openai_receipt=args.physical_openai_receipt,
            readiness_output_file=args.readiness_output_file,
            gate_f_host=args.gate_f_host,
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
            out=sys.stderr,
            err=sys.stderr,
        )
        _print_json(report, stream=sys.stdout if report["ok"] else sys.stderr)
        return 0 if report["ok"] else 1

    if args.command == "provider-preflight":
        provider_source_args = _provider_source_command_args(
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
        )
        env_values, effective_env_file, hermes_context = _provider_env_from_sources(
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
        )
        report = build_provider_preflight_report(
            provider=args.photo_provider,
            photo_pack_root=args.photo_pack_root,
            env=env_values,
        )
        report = _with_provider_command_source_args(
            report,
            provider_source_args or _provider_source_command_args(env_file=effective_env_file),
        )
        if hermes_context:
            report = {**report, "hermes": hermes_context}
        if args.receipt_file:
            _write_receipt(args.receipt_file, report)
        _print_json(report)
        return 0

    if args.command == "provider-env-sources":
        report = build_provider_env_sources_report(
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
            include_hermes_cli_auth=True,
        )
        if args.receipt_file:
            _write_receipt(args.receipt_file, report)
        _print_json(report)
        return 0

    if args.command == "iphone-credential-boundary":
        report = build_iphone_credential_boundary_report(
            root=args.root,
            client_paths=args.client_path,
        )
        if args.receipt_file:
            _write_receipt(args.receipt_file, report)
        _print_json(report, stream=sys.stdout if report["ok"] else sys.stderr)
        return 0 if report["ok"] else 1

    if args.command == "hermes-openai-auth-import":
        report = build_hermes_openai_auth_import_report(
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
            scope=args.scope,
            label=args.label,
            key_env=args.key_env,
            base_url_env=args.base_url_env,
            write=not args.dry_run,
        )
        if args.receipt_file:
            _write_receipt(args.receipt_file, report)
        _print_json(report, stream=sys.stdout if report["ok"] else sys.stderr)
        return 0 if report["ok"] else 1

    if args.command == "gate-audit":
        provider_source_args = _provider_source_command_args(
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
        )
        env_values, _, _ = _provider_env_from_sources(
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
        )
        _print_json(build_gate_audit_report(
            root=args.root,
            simulator_connection_receipt=args.simulator_connection_receipt,
            fixture_receipt=args.fixture_receipt,
            script_receipt=args.script_receipt,
            openai_receipt=args.openai_receipt,
            fake_openai_status_file=args.fake_openai_status_file,
            python_test_receipt=args.python_test_receipt,
            swift_test_receipt=args.swift_test_receipt,
            simulator_ui_test_preflight_receipt=args.simulator_ui_test_preflight_receipt,
            simulator_suite_receipt=args.simulator_suite_receipt,
            simulator_only_resume_receipt=args.simulator_only_resume_receipt,
            provider_preflight_receipt=args.provider_preflight_receipt,
            provider_env_sources_receipt=args.provider_env_sources_receipt,
            provider_env_sources_all_profiles_receipt=args.provider_env_sources_all_profiles_receipt,
            iphone_credential_boundary_receipt=args.iphone_credential_boundary_receipt,
            gate_f_preflight_receipt=args.gate_f_preflight_receipt,
            gate_f_handoff_receipt=args.gate_f_handoff_receipt,
            physical_device_preflight_receipt=args.physical_device_preflight_receipt,
            screenshot_file=args.screenshot_file,
            picker_ui_screenshot_file=args.picker_ui_screenshot_file,
            discovery_refresh_receipt_file=args.discovery_refresh_receipt_file,
            discovery_refresh_screenshot_file=args.discovery_refresh_screenshot_file,
            capture_ready_receipt_file=args.capture_ready_receipt_file,
            capture_ready_screenshot_file=args.capture_ready_screenshot_file,
            capture_completed_receipt_file=args.capture_completed_receipt_file,
            capture_completed_screenshot_file=args.capture_completed_screenshot_file,
            result_gallery_receipt_file=args.result_gallery_receipt_file,
            result_gallery_screenshot_file=args.result_gallery_screenshot_file,
            result_gallery_downloaded_receipt_file=args.result_gallery_downloaded_receipt_file,
            result_gallery_downloaded_screenshot_file=args.result_gallery_downloaded_screenshot_file,
            physical_openai_receipt=args.physical_openai_receipt,
            env=env_values,
            provider_source_args=provider_source_args,
        ))
        return 0

    if args.command == "gate-f-provider-check":
        report = run_gate_f_provider_check(
            root=args.root,
            host=args.host,
            port=args.port,
            bundle_id=args.bundle_id,
            photo_pack_root=args.photo_pack_root,
            physical_openai_receipt=args.physical_openai_receipt,
            provider_preflight_receipt=args.provider_preflight_receipt,
            provider_env_sources_receipt=args.provider_env_sources_receipt,
            provider_env_sources_all_profiles_receipt=args.provider_env_sources_all_profiles_receipt,
            gate_f_preflight_receipt=args.gate_f_preflight_receipt,
            readiness_output_file=args.readiness_output_file,
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
        )
        _print_json(report, stream=sys.stdout if report["ok"] else sys.stderr)
        return 0 if report["ok"] else 1

    if args.command == "gate-f-preflight":
        provider_source_args = _provider_source_command_args(
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
        )
        env_values, effective_env_file, _ = _provider_env_from_sources(
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
        )
        report = build_gate_f_preflight_report(
            root=args.root,
            port=args.port,
            bundle_id=args.bundle_id,
            photo_pack_root=args.photo_pack_root,
            physical_openai_receipt=args.physical_openai_receipt,
            provider_preflight_receipt=args.provider_preflight_receipt,
            provider_env_sources_receipt=args.provider_env_sources_receipt,
            physical_device_preflight_receipt=args.physical_device_preflight_receipt,
            host=args.host,
            env=env_values,
            env_file=effective_env_file,
            provider_source_args=provider_source_args,
        )
        _write_receipt(args.receipt_file, report)
        _print_json(report)
        return 0

    if args.command == "gate-f-handoff":
        report = build_gate_f_handoff_report(
            root=args.root,
            simulator_only_resume_receipt=args.simulator_only_resume_receipt,
            gate_f_preflight_receipt=args.gate_f_preflight_receipt,
        )
        _write_receipt(args.receipt_file, report)
        _print_json(report, stream=sys.stdout if report["ok"] else sys.stderr)
        return 0 if report["ok"] else 1

    if args.command == "gate-f-resume":
        provider_source_args = _provider_source_command_args(
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
        )
        _, effective_env_file, _ = _provider_env_from_sources(
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
        )
        report = run_gate_f_resume(
            root=args.root,
            port=args.port,
            device_id=args.device_id,
            bundle_id=args.bundle_id,
            token=args.token,
            connection_timeout=args.connection_timeout,
            photo_timeout=args.photo_timeout,
            interval=args.interval,
            photo_pack_root=args.photo_pack_root,
            gate_f_preflight_receipt=args.gate_f_preflight_receipt,
            physical_openai_receipt=args.physical_openai_receipt,
            host=args.host,
            env_file=effective_env_file,
            provider_source_args=provider_source_args,
        )
        _print_json(report, stream=sys.stdout if report["ok"] else sys.stderr)
        return 0 if report["ok"] else 1

    if args.command == "readiness-report":
        provider_source_args = _provider_source_command_args(
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
        )
        env_values, _, _ = _provider_env_from_sources(
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
        )
        report = build_gate_audit_report(
            root=args.root,
            simulator_connection_receipt=args.simulator_connection_receipt,
            fixture_receipt=args.fixture_receipt,
            script_receipt=args.script_receipt,
            openai_receipt=args.openai_receipt,
            fake_openai_status_file=args.fake_openai_status_file,
            python_test_receipt=args.python_test_receipt,
            swift_test_receipt=args.swift_test_receipt,
            simulator_ui_test_preflight_receipt=args.simulator_ui_test_preflight_receipt,
            simulator_suite_receipt=args.simulator_suite_receipt,
            simulator_only_resume_receipt=args.simulator_only_resume_receipt,
            provider_preflight_receipt=args.provider_preflight_receipt,
            provider_env_sources_receipt=args.provider_env_sources_receipt,
            provider_env_sources_all_profiles_receipt=args.provider_env_sources_all_profiles_receipt,
            iphone_credential_boundary_receipt=args.iphone_credential_boundary_receipt,
            gate_f_preflight_receipt=args.gate_f_preflight_receipt,
            gate_f_handoff_receipt=args.gate_f_handoff_receipt,
            physical_device_preflight_receipt=args.physical_device_preflight_receipt,
            screenshot_file=args.screenshot_file,
            picker_ui_screenshot_file=args.picker_ui_screenshot_file,
            discovery_refresh_receipt_file=args.discovery_refresh_receipt_file,
            discovery_refresh_screenshot_file=args.discovery_refresh_screenshot_file,
            capture_ready_receipt_file=args.capture_ready_receipt_file,
            capture_ready_screenshot_file=args.capture_ready_screenshot_file,
            capture_completed_receipt_file=args.capture_completed_receipt_file,
            capture_completed_screenshot_file=args.capture_completed_screenshot_file,
            result_gallery_receipt_file=args.result_gallery_receipt_file,
            result_gallery_screenshot_file=args.result_gallery_screenshot_file,
            result_gallery_downloaded_receipt_file=args.result_gallery_downloaded_receipt_file,
            result_gallery_downloaded_screenshot_file=args.result_gallery_downloaded_screenshot_file,
            physical_openai_receipt=args.physical_openai_receipt,
            env=env_values,
            provider_source_args=provider_source_args,
        )
        markdown = build_readiness_markdown(report)
        if args.output_file:
            parent = os.path.dirname(args.output_file)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(args.output_file, "w", encoding="utf-8") as handle:
                handle.write(markdown)
        print(markdown, end="")
        return 0

    if args.command == "verify-receipt":
        with open(args.file, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
        result = verify_receipt_payload(
            receipt,
            expected_phase=args.phase,
            expected_provider=args.photo_provider,
        )
        payload = {"missing": result.missing, "ok": result.ok, "phase": args.phase}
        _print_json(payload, stream=sys.stdout if result.ok else sys.stderr)
        return 0 if result.ok else 1

    if args.command == "run-lan":
        env_overlay, _, _ = _provider_env_overlay_from_sources(
            env_file=args.env_file,
            hermes_home=args.hermes_home,
            hermes_profile=args.hermes_profile,
        )
        with _temporary_environ(env_overlay):
            return run_lan_qa_session(
                host=args.host,
                port=args.port,
                device_id=args.device_id,
                bundle_id=args.bundle_id,
                token=args.token,
                connection_timeout=args.connection_timeout,
                photo_timeout=args.photo_timeout,
                interval=args.interval,
                launch_app=not args.no_launch,
                connection_only=args.connection_only,
                advertise_bonjour=not args.no_bonjour,
                photo_provider=args.photo_provider,
                photo_pack_root=args.photo_pack_root,
                receipt_file=args.receipt_file,
            )

    if args.command == "simulator-connection-smoke":
        return run_simulator_connection_session(
            host=args.host,
            port=args.port,
            bundle_id=args.bundle_id,
            token=args.token,
            connection_timeout=args.connection_timeout,
            interval=args.interval,
            launch_app=not args.no_launch,
            advertise_bonjour=not args.no_bonjour,
            receipt_file=args.receipt_file,
        )

    if args.command == "simulator-discovery-refresh-smoke":
        return run_simulator_discovery_refresh_session(
            host=args.host,
            port=args.port,
            bundle_id=args.bundle_id,
            token=args.token,
            connection_timeout=args.connection_timeout,
            interval=args.interval,
            launch_app=not args.no_launch,
            receipt_file=args.receipt_file,
            screenshot_file=args.screenshot_file,
        )

    if args.command == "simulator-openai-smoke":
        return run_openai_compatible_simulator_session(
            host=args.host,
            bridge_port=args.port,
            fake_openai_port=args.fake_openai_port,
            bundle_id=args.bundle_id,
            token=args.token,
            connection_timeout=args.connection_timeout,
            photo_timeout=args.photo_timeout,
            interval=args.interval,
            photo_pack_root=args.photo_pack_root,
            output_format=args.output_format,
            launch_app=not args.no_launch,
            receipt_file=args.receipt_file,
            fake_openai_status_file=args.fake_openai_status_file,
            screenshot_file=args.screenshot_file,
        )

    if args.command == "simulator-local-recipe-smoke":
        return run_local_recipe_simulator_session(
            host=args.host,
            bridge_port=args.port,
            bundle_id=args.bundle_id,
            token=args.token,
            connection_timeout=args.connection_timeout,
            photo_timeout=args.photo_timeout,
            interval=args.interval,
            photo_pack_root=args.photo_pack_root,
            launch_app=not args.no_launch,
            receipt_file=args.receipt_file,
            screenshot_file=args.screenshot_file,
        )

    if args.command == "simulator-capture-ready-smoke":
        return run_simulator_capture_ready_session(
            bundle_id=args.bundle_id,
            screenshot_file=args.screenshot_file,
            receipt_file=args.receipt_file,
            launch_app=not args.no_launch,
            settle_seconds=args.settle_seconds,
        )

    if args.command == "simulator-capture-completed-smoke":
        return run_simulator_capture_completed_session(
            bundle_id=args.bundle_id,
            screenshot_file=args.screenshot_file,
            receipt_file=args.receipt_file,
            launch_app=not args.no_launch,
            settle_seconds=args.settle_seconds,
        )

    if args.command == "simulator-result-gallery-smoke":
        return run_simulator_result_gallery_session(
            bundle_id=args.bundle_id,
            screenshot_file=args.screenshot_file,
            receipt_file=args.receipt_file,
            launch_app=not args.no_launch,
            settle_seconds=args.settle_seconds,
        )

    if args.command == "simulator-result-gallery-downloaded-smoke":
        return run_simulator_result_gallery_downloaded_session(
            bundle_id=args.bundle_id,
            screenshot_file=args.screenshot_file,
            receipt_file=args.receipt_file,
            launch_app=not args.no_launch,
            settle_seconds=args.settle_seconds,
        )

    if args.command == "simulator-share-sheet-smoke":
        return run_simulator_share_sheet_session(
            bundle_id=args.bundle_id,
            screenshot_file=args.screenshot_file,
            receipt_file=args.receipt_file,
            launch_app=not args.no_launch,
            settle_seconds=args.settle_seconds,
        )

    if args.command == "simulator-picker-ui-smoke":
        return run_simulator_picker_ui_session(
            bundle_id=args.bundle_id,
            screenshot_file=args.screenshot_file,
            launch_app=not args.no_launch,
            settle_seconds=args.settle_seconds,
        )

    if args.command == "simulator-seed-photo-library":
        payload = run_simulator_seed_photo_library(
            device=args.device,
            image_file=args.image_file,
        )
        _print_json(payload, stream=sys.stdout if payload["ok"] else sys.stderr)
        return 0 if payload["ok"] else 1

    if args.command == "test-receipt":
        return run_test_receipt_command(
            name=args.name,
            command=args.test_command,
            receipt_file=args.receipt_file,
            timeout_seconds=args.timeout,
        )

    evaluator = evaluate_connection_restore if args.command == "wait-connection" else evaluate_photo_flow
    return _wait_for_status(
        base_url=args.base_url,
        token=args.token,
        timeout_seconds=args.timeout,
        interval_seconds=args.interval,
        evaluator=evaluator,
        phase="connection" if args.command == "wait-connection" else "photo-flow",
        receipt_file=args.receipt_file,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect Pocket Agent mock bridge QA status.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_hermes_provider_args(command_parser) -> None:
        command_parser.add_argument(
            "--hermes-home",
            default="",
            help="Optional Hermes home to inspect for server-side provider env/auth evidence. Defaults to ~/.hermes when --hermes-profile is set.",
        )
        command_parser.add_argument(
            "--hermes-profile",
            default="",
            help="Optional Hermes profile whose .env can provide server-side OPENAI_API_KEY evidence without printing the key.",
        )

    commands = subparsers.add_parser(
        "commands",
        help="Print the physical iPhone QA command sequence for LAN or Tailscale.",
    )
    commands.add_argument("--host", required=True, help="Mac LAN or Tailscale IP reachable from the iPhone.")
    commands.add_argument("--port", type=int, default=8765, help="Mock bridge port.")
    commands.add_argument("--device-id", required=True, help="CoreDevice id from xcrun devicectl list devices.")
    commands.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")

    preflight = subparsers.add_parser(
        "preflight",
        help="Print LAN, Tailscale, CoreDevice, and tool readiness for physical iPhone QA.",
    )
    preflight.add_argument("--port", type=int, default=8765, help="Mock bridge port.")
    preflight.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")

    physical_device_preflight = subparsers.add_parser(
        "physical-device-preflight",
        help="Print physical iPhone CoreDevice and Xcode destination readiness without launching the app.",
    )
    physical_device_preflight.add_argument(
        "--project",
        default="ios/AgentPocket.xcodeproj",
        help="Xcode project used for physical device destination discovery.",
    )
    physical_device_preflight.add_argument(
        "--scheme",
        default="AgentPocket",
        help="Xcode scheme used for physical device destination discovery.",
    )
    physical_device_preflight.add_argument(
        "--target",
        default="AgentPocket",
        help="Xcode target used for optional iphoneos CLI build readiness.",
    )
    physical_device_preflight.add_argument(
        "--configuration",
        default="Debug",
        help="Xcode configuration used for optional iphoneos CLI build readiness.",
    )
    physical_device_preflight.add_argument(
        "--device-id",
        default="",
        help="CoreDevice id to inspect. Defaults to the first connected paired iPhone.",
    )
    physical_device_preflight.add_argument(
        "--build-check",
        action="store_true",
        help="Also run a target-based iphoneos build to prove CLI real-device QA readiness.",
    )
    physical_device_preflight.add_argument(
        "--receipt-file",
        default=DEFAULT_PHYSICAL_DEVICE_PREFLIGHT_RECEIPT,
        help="Path to write the physical device preflight JSON receipt.",
    )

    simulator_preflight = subparsers.add_parser(
        "simulator-preflight",
        help="Print iOS Simulator readiness and commands for local mock bridge QA.",
    )
    simulator_preflight.add_argument(
        "--app-path",
        default="ios/build/Debug-iphonesimulator/AgentPocket.app",
        help="Built simulator Pocket Agent app bundle path.",
    )
    simulator_preflight.add_argument("--port", type=int, default=8766, help="Local mock bridge port.")
    simulator_preflight.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_preflight.add_argument(
        "--gate-f-host",
        default="",
        help="Explicit real-device Gate F endpoint host to preserve in the generated simulator-only resume command.",
    )

    simulator_ui_test_preflight = subparsers.add_parser(
        "simulator-ui-test-preflight",
        help="Print Xcode SDK, Simulator runtime, and UI test destination readiness.",
    )
    simulator_ui_test_preflight.add_argument(
        "--project",
        default="ios/AgentPocket.xcodeproj",
        help="Xcode project used for UI test destination discovery.",
    )
    simulator_ui_test_preflight.add_argument(
        "--scheme",
        default="AgentPocket",
        help="Xcode scheme used for UI test destination discovery.",
    )
    simulator_ui_test_preflight.add_argument(
        "--test-target",
        default="AgentPocketPickerUITests",
        help="UI test target to build and run.",
    )
    simulator_ui_test_preflight.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_ui_test_preflight.add_argument(
        "--receipt-file",
        default="",
        help="Optional path to write the UI test preflight JSON.",
    )

    simulator_suite = subparsers.add_parser(
        "simulator-suite",
        help="Run the local Simulator evidence suite without using a physical iPhone.",
    )
    simulator_suite.add_argument("--host", default="127.0.0.1", help="Host the Simulator can reach.")
    simulator_suite.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_suite.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer token for /mobile/v1/qa/status.")
    simulator_suite.add_argument("--connection-port", type=int, default=8766, help="Local connection smoke bridge port.")
    simulator_suite.add_argument("--discovery-refresh-port", type=int, default=8767, help="No-payload discovery refresh smoke bridge port.")
    simulator_suite.add_argument("--openai-port", type=int, default=8769, help="OpenAI-compatible bridge port.")
    simulator_suite.add_argument("--fake-openai-port", type=int, default=8781, help="Local fake OpenAI port.")
    simulator_suite.add_argument("--connection-timeout", type=float, default=45, help="Seconds to wait for connection.")
    simulator_suite.add_argument("--photo-timeout", type=float, default=90, help="Seconds to wait for photo flow.")
    simulator_suite.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds.")
    simulator_suite.add_argument(
        "--photo-pack-root",
        default="photo-pack",
        help="Path to the Photo Pack root containing provider adapters.",
    )
    simulator_suite.add_argument(
        "--suite-receipt-file",
        default=DEFAULT_SIMULATOR_SUITE_RECEIPT,
        help="Path to write the suite summary JSON.",
    )
    simulator_suite.add_argument(
        "--simulator-ui-test-preflight-receipt",
        default=DEFAULT_SIMULATOR_UI_TEST_PREFLIGHT_RECEIPT,
        help="Path to write the UI test preflight JSON.",
    )
    simulator_suite.add_argument(
        "--simulator-connection-receipt",
        default="docs/qa-receipts/simulator-connection-latest.json",
        help="Path to write the normal-app connection receipt.",
    )
    simulator_suite.add_argument(
        "--discovery-refresh-receipt",
        default=DEFAULT_SIMULATOR_DISCOVERY_REFRESH_RECEIPT,
        help="Path to write the no-payload discovery refresh receipt.",
    )
    simulator_suite.add_argument(
        "--discovery-refresh-screenshot",
        default=DEFAULT_SIMULATOR_DISCOVERY_REFRESH_SCREENSHOT,
        help="Path for the no-payload discovery refresh screenshot.",
    )
    simulator_suite.add_argument(
        "--library-fixture",
        default=DEFAULT_SIMULATOR_LIBRARY_FIXTURE,
        help="Path to write and import the generated Simulator library fixture.",
    )
    simulator_suite.add_argument(
        "--picker-ui-screenshot",
        default=DEFAULT_SIMULATOR_PICKER_UI_SCREENSHOT,
        help="Path for the PhotosPicker entry screenshot.",
    )
    simulator_suite.add_argument(
        "--capture-ready-screenshot",
        default="/tmp/agent-pocket-simulator-capture-ready.png",
        help="Path for the selected-photo ready screenshot.",
    )
    simulator_suite.add_argument(
        "--capture-ready-receipt",
        default=DEFAULT_SIMULATOR_CAPTURE_READY_RECEIPT,
        help="Path to write the app-authored selected-photo ready receipt.",
    )
    simulator_suite.add_argument(
        "--capture-completed-screenshot",
        default=DEFAULT_SIMULATOR_CAPTURE_COMPLETED_SCREENSHOT,
        help="Path for the completed capture screenshot.",
    )
    simulator_suite.add_argument(
        "--capture-completed-receipt",
        default=DEFAULT_SIMULATOR_CAPTURE_COMPLETED_RECEIPT,
        help="Path to write the app-authored completed capture receipt.",
    )
    simulator_suite.add_argument(
        "--result-gallery-screenshot",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_SCREENSHOT,
        help="Path for the result gallery screenshot.",
    )
    simulator_suite.add_argument(
        "--result-gallery-receipt",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_RECEIPT,
        help="Path to write the app-authored result gallery receipt.",
    )
    simulator_suite.add_argument(
        "--result-gallery-downloaded-screenshot",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_SCREENSHOT,
        help="Path for the downloaded result gallery screenshot.",
    )
    simulator_suite.add_argument(
        "--result-gallery-downloaded-receipt",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_RECEIPT,
        help="Path to write the app-authored downloaded result gallery receipt.",
    )
    simulator_suite.add_argument(
        "--openai-receipt",
        default="docs/qa-receipts/simulator-openai-compatible-photo-flow-screenshot.json",
        help="Path to write the OpenAI-compatible photo-flow receipt.",
    )
    simulator_suite.add_argument(
        "--fake-openai-status-file",
        default="docs/qa-receipts/simulator-openai-compatible-fake-openai-status-screenshot.json",
        help="Path to write fake OpenAI request status.",
    )
    simulator_suite.add_argument(
        "--openai-screenshot",
        default="/tmp/agent-pocket-simulator-openai-provider-smoke-autocapture.png",
        help="Path for the OpenAI-compatible smoke screenshot.",
    )

    simulator_only_resume = subparsers.add_parser(
        "simulator-only-resume",
        help="Refresh local Simulator evidence, Gate F preflight, and readiness without using a physical iPhone.",
    )
    simulator_only_resume.add_argument(
        "--root",
        default=".",
        help="Project root for resolving relative evidence paths.",
    )
    simulator_only_resume.add_argument("--host", default="127.0.0.1", help="Host the Simulator can reach.")
    simulator_only_resume.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_only_resume.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer token for /mobile/v1/qa/status.")
    simulator_only_resume.add_argument("--connection-port", type=int, default=8766, help="Local connection smoke bridge port.")
    simulator_only_resume.add_argument("--discovery-refresh-port", type=int, default=8767, help="No-payload discovery refresh smoke bridge port.")
    simulator_only_resume.add_argument("--openai-port", type=int, default=8769, help="OpenAI-compatible bridge port.")
    simulator_only_resume.add_argument("--fake-openai-port", type=int, default=8781, help="Local fake OpenAI port.")
    simulator_only_resume.add_argument("--gate-f-port", type=int, default=8765, help="Gate F real-device bridge port for generated resume commands.")
    simulator_only_resume.add_argument(
        "--gate-f-host",
        default="",
        help="Explicit real-device Gate F endpoint host to preserve in the refreshed preflight receipt.",
    )
    simulator_only_resume.add_argument("--connection-timeout", type=float, default=45, help="Seconds to wait for connection.")
    simulator_only_resume.add_argument("--photo-timeout", type=float, default=90, help="Seconds to wait for photo flow.")
    simulator_only_resume.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds.")
    simulator_only_resume.add_argument(
        "--photo-pack-root",
        default="photo-pack",
        help="Path to the Photo Pack root containing provider adapters.",
    )
    simulator_only_resume.add_argument(
        "--suite-receipt-file",
        default=DEFAULT_SIMULATOR_SUITE_RECEIPT,
        help="Path to write the suite summary JSON.",
    )
    simulator_only_resume.add_argument(
        "--gate-f-preflight-receipt",
        default=DEFAULT_GATE_F_PREFLIGHT_RECEIPT,
        help="Path to write the Gate F external preflight JSON receipt.",
    )
    simulator_only_resume.add_argument(
        "--resume-receipt-file",
        default=DEFAULT_SIMULATOR_ONLY_RESUME_RECEIPT,
        help="Path to write the simulator-only resume summary JSON receipt.",
    )
    simulator_only_resume.add_argument(
        "--physical-openai-receipt",
        default="docs/qa-receipts/openai-photo-flow.json",
        help="Physical iPhone OpenAI provider receipt required to close Gate F.",
    )
    simulator_only_resume.add_argument(
        "--readiness-output-file",
        default="docs/agent-pocket-readiness.md",
        help="Path to write the human-readable readiness Markdown report.",
    )
    simulator_only_resume.add_argument(
        "--env-file",
        default="",
        help="Optional server-side env file to load for Gate F provider readiness; secret values are never printed.",
    )
    add_hermes_provider_args(simulator_only_resume)

    provider_preflight = subparsers.add_parser(
        "provider-preflight",
        help="Print Photo Pack provider readiness without exposing secrets.",
    )
    provider_preflight.add_argument(
        "--photo-provider",
        default="openai",
        choices=PHOTO_PROVIDER_CHOICES,
        help="Photo provider to inspect.",
    )
    provider_preflight.add_argument(
        "--photo-pack-root",
        default="photo-pack",
        help="Path to the Photo Pack root containing provider adapters.",
    )
    provider_preflight.add_argument(
        "--env-file",
        default="",
        help="Optional server-side env file to load for provider checks; secret values are never printed.",
    )
    add_hermes_provider_args(provider_preflight)
    provider_preflight.add_argument(
        "--receipt-file",
        default="",
        help="Optional path to write the redacted provider readiness JSON receipt.",
    )

    provider_env_sources = subparsers.add_parser(
        "provider-env-sources",
        help="Probe server-side OPENAI_API_KEY sources without printing secret values.",
    )
    provider_env_sources.add_argument(
        "--env-file",
        default="",
        help="Optional server-side env file to check; secret values are never printed.",
    )
    add_hermes_provider_args(provider_env_sources)
    provider_env_sources.add_argument(
        "--receipt-file",
        default="",
        help="Optional path to write the redacted provider env source JSON receipt.",
    )

    iphone_credential_boundary = subparsers.add_parser(
        "iphone-credential-boundary",
        help="Verify iPhone client code contains no OpenAI provider credentials or direct Images API path.",
    )
    iphone_credential_boundary.add_argument(
        "--root",
        default=".",
        help="Project root for resolving client source paths.",
    )
    iphone_credential_boundary.add_argument(
        "--client-path",
        action="append",
        default=None,
        help="Client source path to scan. Repeat to override the default iOS client source paths.",
    )
    iphone_credential_boundary.add_argument(
        "--receipt-file",
        default=DEFAULT_IPHONE_CREDENTIAL_BOUNDARY_RECEIPT,
        help="Path to write the iPhone credential-boundary receipt.",
    )

    hermes_openai_auth_import = subparsers.add_parser(
        "hermes-openai-auth-import",
        help="Import server-side OPENAI_API_KEY from the current environment into Hermes openai/api_key auth without printing it.",
    )
    add_hermes_provider_args(hermes_openai_auth_import)
    hermes_openai_auth_import.add_argument(
        "--scope",
        default="profile",
        choices=["profile", "shared"],
        help="Write to the selected Hermes profile auth file or shared-auth/auth.json.",
    )
    hermes_openai_auth_import.add_argument(
        "--label",
        default="agent-pocket-openai-images",
        help="Credential label to add or replace in credential_pool.openai.",
    )
    hermes_openai_auth_import.add_argument(
        "--key-env",
        default="OPENAI_API_KEY",
        help="Environment variable containing the server-side OpenAI API key.",
    )
    hermes_openai_auth_import.add_argument(
        "--base-url-env",
        default="OPENAI_BASE_URL",
        help="Optional environment variable containing the OpenAI-compatible base URL.",
    )
    hermes_openai_auth_import.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the target auth file and env visibility without writing credentials.",
    )
    hermes_openai_auth_import.add_argument(
        "--receipt-file",
        default="",
        help="Path to write the redacted import receipt.",
    )

    gate_audit = subparsers.add_parser(
        "gate-audit",
        help="Print milestone Gate A-F evidence and remaining external QA gaps.",
    )
    gate_audit.add_argument(
        "--root",
        default=".",
        help="Project root for resolving relative evidence paths.",
    )
    gate_audit.add_argument(
        "--env-file",
        default="",
        help="Optional server-side env file to load for external provider readiness; secret values are never printed.",
    )
    add_hermes_provider_args(gate_audit)
    gate_audit.add_argument(
        "--simulator-connection-receipt",
        default="docs/qa-receipts/simulator-connection-latest.json",
        help="Simulator normal-app connection receipt.",
    )
    gate_audit.add_argument(
        "--fixture-receipt",
        default="docs/qa-receipts/simulator-photo-flow-smoke.json",
        help="Simulator fixture photo-flow receipt.",
    )
    gate_audit.add_argument(
        "--script-receipt",
        default="docs/qa-receipts/simulator-script-provider-photo-flow.json",
        help="Simulator script-provider photo-flow receipt.",
    )
    gate_audit.add_argument(
        "--openai-receipt",
        default="docs/qa-receipts/simulator-openai-compatible-photo-flow-screenshot.json",
        help="Simulator OpenAI-compatible photo-flow receipt.",
    )
    gate_audit.add_argument(
        "--fake-openai-status-file",
        default="docs/qa-receipts/simulator-openai-compatible-fake-openai-status-screenshot.json",
        help="Fake OpenAI request status receipt.",
    )
    gate_audit.add_argument(
        "--python-test-receipt",
        default="docs/qa-receipts/python-tests-latest.json",
        help="Latest Python test command receipt.",
    )
    gate_audit.add_argument(
        "--swift-test-receipt",
        default="docs/qa-receipts/swift-test-latest.json",
        help="Latest Swift test command receipt.",
    )
    gate_audit.add_argument(
        "--simulator-ui-test-preflight-receipt",
        default=DEFAULT_SIMULATOR_UI_TEST_PREFLIGHT_RECEIPT,
        help="Latest Simulator UI test preflight JSON receipt.",
    )
    gate_audit.add_argument(
        "--simulator-suite-receipt",
        default=DEFAULT_SIMULATOR_SUITE_RECEIPT,
        help="Latest local Simulator suite JSON receipt.",
    )
    gate_audit.add_argument(
        "--simulator-only-resume-receipt",
        default=DEFAULT_SIMULATOR_ONLY_RESUME_RECEIPT,
        help="Latest simulator-only resume JSON receipt proving no physical iPhone was used.",
    )
    gate_audit.add_argument(
        "--provider-preflight-receipt",
        default=DEFAULT_OPENAI_PROVIDER_PREFLIGHT_RECEIPT,
        help="Redacted OpenAI provider preflight receipt proving server-side key readiness.",
    )
    gate_audit.add_argument(
        "--provider-env-sources-receipt",
        default=DEFAULT_PROVIDER_ENV_SOURCES_RECEIPT,
        help="Redacted provider env source receipt proving which server-side key source is visible.",
    )
    gate_audit.add_argument(
        "--provider-env-sources-all-profiles-receipt",
        default=DEFAULT_PROVIDER_ENV_SOURCES_ALL_PROFILES_RECEIPT,
        help="Redacted provider env source receipt scanning every Hermes profile for diagnostics only.",
    )
    gate_audit.add_argument(
        "--iphone-credential-boundary-receipt",
        default=DEFAULT_IPHONE_CREDENTIAL_BOUNDARY_RECEIPT,
        help="Receipt proving iPhone client code does not contain OpenAI provider credentials or direct Images API endpoints.",
    )
    gate_audit.add_argument(
        "--gate-f-preflight-receipt",
        default=DEFAULT_GATE_F_PREFLIGHT_RECEIPT,
        help="Latest Gate F external preflight JSON receipt.",
    )
    gate_audit.add_argument(
        "--gate-f-handoff-receipt",
        default=DEFAULT_GATE_F_HANDOFF_RECEIPT,
        help="Latest Gate F no-device handoff JSON receipt.",
    )
    gate_audit.add_argument(
        "--physical-device-preflight-receipt",
        default=DEFAULT_PHYSICAL_DEVICE_PREFLIGHT_RECEIPT,
        help="Latest physical iPhone Xcode destination preflight JSON receipt.",
    )
    gate_audit.add_argument(
        "--screenshot-file",
        default="/tmp/agent-pocket-simulator-openai-provider-smoke-autocapture.png",
        help="Simulator screenshot evidence from the OpenAI-compatible smoke.",
    )
    gate_audit.add_argument(
        "--picker-ui-screenshot-file",
        default=DEFAULT_SIMULATOR_PICKER_UI_SCREENSHOT,
        help="Simulator screenshot evidence for the connected PhotosPicker entry state.",
    )
    gate_audit.add_argument(
        "--discovery-refresh-receipt-file",
        default=DEFAULT_SIMULATOR_DISCOVERY_REFRESH_RECEIPT,
        help="Simulator receipt proving no-payload discovery refreshes /pairing/dev before pairing.",
    )
    gate_audit.add_argument(
        "--discovery-refresh-screenshot-file",
        default=DEFAULT_SIMULATOR_DISCOVERY_REFRESH_SCREENSHOT,
        help="Simulator screenshot evidence for no-payload discovery refresh.",
    )
    gate_audit.add_argument(
        "--capture-ready-screenshot-file",
        default="/tmp/agent-pocket-simulator-capture-ready.png",
        help="Simulator screenshot evidence that selected-photo ready state shows Send to Pocket Agent.",
    )
    gate_audit.add_argument(
        "--capture-ready-receipt-file",
        default=DEFAULT_SIMULATOR_CAPTURE_READY_RECEIPT,
        help="App-authored receipt proving selected-photo ready state enables Send to Pocket Agent.",
    )
    gate_audit.add_argument(
        "--capture-completed-screenshot-file",
        default=DEFAULT_SIMULATOR_CAPTURE_COMPLETED_SCREENSHOT,
        help="Simulator screenshot evidence that completed capture shows Review Results.",
    )
    gate_audit.add_argument(
        "--capture-completed-receipt-file",
        default=DEFAULT_SIMULATOR_CAPTURE_COMPLETED_RECEIPT,
        help="App-authored receipt proving completed capture promotes Review Results.",
    )
    gate_audit.add_argument(
        "--result-gallery-screenshot-file",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_SCREENSHOT,
        help="Simulator screenshot evidence for the result gallery review state.",
    )
    gate_audit.add_argument(
        "--result-gallery-receipt-file",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_RECEIPT,
        help="App-authored receipt proving the result gallery can review returned variants.",
    )
    gate_audit.add_argument(
        "--result-gallery-downloaded-screenshot-file",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_SCREENSHOT,
        help="Simulator screenshot evidence for the downloaded result gallery state.",
    )
    gate_audit.add_argument(
        "--result-gallery-downloaded-receipt-file",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_RECEIPT,
        help="App-authored receipt proving Save and Share are available after download.",
    )
    gate_audit.add_argument(
        "--physical-openai-receipt",
        default="docs/qa-receipts/openai-photo-flow.json",
        help="Physical iPhone OpenAI provider receipt required to close Gate F.",
    )

    gate_f_provider_check = subparsers.add_parser(
        "gate-f-provider-check",
        help="Refresh Hermes/OpenAI provider receipts, Gate F preflight, and readiness after server-side key setup.",
    )
    gate_f_provider_check.add_argument(
        "--root",
        default=".",
        help="Project root for resolving relative evidence paths.",
    )
    gate_f_provider_check.add_argument(
        "--host",
        default="",
        help="Explicit Mac IP/host reachable from the iPhone. Counts as endpoint evidence without Tailscale CLI.",
    )
    gate_f_provider_check.add_argument("--port", type=int, default=8765, help="Mock bridge port for the real-device run command.")
    gate_f_provider_check.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    gate_f_provider_check.add_argument(
        "--photo-pack-root",
        default="photo-pack",
        help="Path to the Photo Pack root containing provider adapters.",
    )
    gate_f_provider_check.add_argument(
        "--physical-openai-receipt",
        default="docs/qa-receipts/openai-photo-flow.json",
        help="Physical iPhone OpenAI provider receipt required to close Gate F.",
    )
    gate_f_provider_check.add_argument(
        "--provider-preflight-receipt",
        default=DEFAULT_OPENAI_PROVIDER_PREFLIGHT_RECEIPT,
        help="Path to write the redacted OpenAI provider preflight receipt.",
    )
    gate_f_provider_check.add_argument(
        "--provider-env-sources-receipt",
        default=DEFAULT_PROVIDER_ENV_SOURCES_RECEIPT,
        help="Path to write the selected server-side provider env source receipt.",
    )
    gate_f_provider_check.add_argument(
        "--provider-env-sources-all-profiles-receipt",
        default=DEFAULT_PROVIDER_ENV_SOURCES_ALL_PROFILES_RECEIPT,
        help="Path to write the all-profile Hermes provider env source diagnostic receipt.",
    )
    gate_f_provider_check.add_argument(
        "--gate-f-preflight-receipt",
        default=DEFAULT_GATE_F_PREFLIGHT_RECEIPT,
        help="Path to write the Gate F external preflight JSON receipt.",
    )
    gate_f_provider_check.add_argument(
        "--readiness-output-file",
        default="docs/agent-pocket-readiness.md",
        help="Path to write the human-readable readiness Markdown report.",
    )
    gate_f_provider_check.add_argument(
        "--env-file",
        default="",
        help="Optional server-side env file to load for OpenAI provider readiness; secret values are never printed.",
    )
    add_hermes_provider_args(gate_f_provider_check)

    gate_f_preflight = subparsers.add_parser(
        "gate-f-preflight",
        help="Print Gate F external dependency readiness without launching or inspecting the physical iPhone.",
    )
    gate_f_preflight.add_argument(
        "--root",
        default=".",
        help="Project root for resolving relative evidence paths.",
    )
    gate_f_preflight.add_argument(
        "--host",
        default="",
        help="Explicit Mac IP/host reachable from the iPhone. Counts as endpoint evidence without Tailscale CLI.",
    )
    gate_f_preflight.add_argument("--port", type=int, default=8765, help="Mock bridge port for the real-device run command.")
    gate_f_preflight.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    gate_f_preflight.add_argument(
        "--photo-pack-root",
        default="photo-pack",
        help="Path to the Photo Pack root containing provider adapters.",
    )
    gate_f_preflight.add_argument(
        "--physical-openai-receipt",
        default="docs/qa-receipts/openai-photo-flow.json",
        help="Physical iPhone OpenAI provider receipt required to close Gate F.",
    )
    gate_f_preflight.add_argument(
        "--provider-preflight-receipt",
        default=DEFAULT_OPENAI_PROVIDER_PREFLIGHT_RECEIPT,
        help="Redacted OpenAI provider preflight receipt proving server-side key readiness.",
    )
    gate_f_preflight.add_argument(
        "--provider-env-sources-receipt",
        default=DEFAULT_PROVIDER_ENV_SOURCES_RECEIPT,
        help="Redacted provider env source receipt proving which server-side key source is visible.",
    )
    gate_f_preflight.add_argument(
        "--physical-device-preflight-receipt",
        default=DEFAULT_PHYSICAL_DEVICE_PREFLIGHT_RECEIPT,
        help="Physical iPhone preflight receipt used to fill the CoreDevice id in generated commands.",
    )
    gate_f_preflight.add_argument(
        "--env-file",
        default="",
        help="Optional server-side env file to load for OpenAI provider readiness; secret values are never printed.",
    )
    add_hermes_provider_args(gate_f_preflight)
    gate_f_preflight.add_argument(
        "--receipt-file",
        default=DEFAULT_GATE_F_PREFLIGHT_RECEIPT,
        help="Path to write the Gate F external preflight JSON receipt.",
    )

    gate_f_handoff = subparsers.add_parser(
        "gate-f-handoff",
        help="Write a no-device Gate F handoff receipt from current local Simulator and preflight evidence.",
    )
    gate_f_handoff.add_argument(
        "--root",
        default=".",
        help="Project root for resolving relative evidence paths.",
    )
    gate_f_handoff.add_argument(
        "--simulator-only-resume-receipt",
        default=DEFAULT_SIMULATOR_ONLY_RESUME_RECEIPT,
        help="Latest simulator-only resume JSON receipt proving no physical iPhone was used.",
    )
    gate_f_handoff.add_argument(
        "--gate-f-preflight-receipt",
        default=DEFAULT_GATE_F_PREFLIGHT_RECEIPT,
        help="Latest Gate F external preflight JSON receipt.",
    )
    gate_f_handoff.add_argument(
        "--receipt-file",
        default=DEFAULT_GATE_F_HANDOFF_RECEIPT,
        help="Path to write the Gate F no-device handoff JSON receipt.",
    )

    gate_f_resume = subparsers.add_parser(
        "gate-f-resume",
        help="Run the real iPhone OpenAI Gate F flow, then verify the generated receipt.",
    )
    gate_f_resume.add_argument(
        "--root",
        default=".",
        help="Project root for resolving relative evidence paths.",
    )
    gate_f_resume.add_argument(
        "--host",
        default="",
        help="Mac Tailscale IP reachable from the iPhone. Defaults to the preflight Tailscale IP.",
    )
    gate_f_resume.add_argument("--port", type=int, default=8765, help="Mock bridge port for the real-device run.")
    gate_f_resume.add_argument("--device-id", required=True, help="CoreDevice id from xcrun devicectl list devices.")
    gate_f_resume.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    gate_f_resume.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer token for /mobile/v1/qa/status.")
    gate_f_resume.add_argument("--connection-timeout", type=float, default=45, help="Seconds to wait for saved connection restore.")
    gate_f_resume.add_argument("--photo-timeout", type=float, default=180, help="Seconds to wait for the real iPhone photo flow.")
    gate_f_resume.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds.")
    gate_f_resume.add_argument(
        "--photo-pack-root",
        default="photo-pack",
        help="Path to the Photo Pack root containing provider adapters.",
    )
    gate_f_resume.add_argument(
        "--gate-f-preflight-receipt",
        default=DEFAULT_GATE_F_PREFLIGHT_RECEIPT,
        help="Path to write the Gate F external preflight JSON receipt.",
    )
    gate_f_resume.add_argument(
        "--physical-openai-receipt",
        default="docs/qa-receipts/openai-photo-flow.json",
        help="Path to write and verify the physical iPhone OpenAI receipt.",
    )
    gate_f_resume.add_argument(
        "--env-file",
        default="",
        help="Optional server-side env file to load before starting the OpenAI mock bridge; secret values are never printed.",
    )
    add_hermes_provider_args(gate_f_resume)

    readiness_report = subparsers.add_parser(
        "readiness-report",
        help="Print a human-readable MVP readiness report from the current gate evidence.",
    )
    readiness_report.add_argument(
        "--root",
        default=".",
        help="Project root for resolving relative evidence paths.",
    )
    readiness_report.add_argument(
        "--simulator-connection-receipt",
        default="docs/qa-receipts/simulator-connection-latest.json",
        help="Simulator normal-app connection receipt.",
    )
    readiness_report.add_argument(
        "--fixture-receipt",
        default="docs/qa-receipts/simulator-photo-flow-smoke.json",
        help="Simulator fixture photo-flow receipt.",
    )
    readiness_report.add_argument(
        "--script-receipt",
        default="docs/qa-receipts/simulator-script-provider-photo-flow.json",
        help="Simulator script-provider photo-flow receipt.",
    )
    readiness_report.add_argument(
        "--openai-receipt",
        default="docs/qa-receipts/simulator-openai-compatible-photo-flow-screenshot.json",
        help="Simulator OpenAI-compatible photo-flow receipt.",
    )
    readiness_report.add_argument(
        "--fake-openai-status-file",
        default="docs/qa-receipts/simulator-openai-compatible-fake-openai-status-screenshot.json",
        help="Fake OpenAI request status receipt.",
    )
    readiness_report.add_argument(
        "--python-test-receipt",
        default="docs/qa-receipts/python-tests-latest.json",
        help="Latest Python test command receipt.",
    )
    readiness_report.add_argument(
        "--swift-test-receipt",
        default="docs/qa-receipts/swift-test-latest.json",
        help="Latest Swift test command receipt.",
    )
    readiness_report.add_argument(
        "--simulator-ui-test-preflight-receipt",
        default=DEFAULT_SIMULATOR_UI_TEST_PREFLIGHT_RECEIPT,
        help="Latest Simulator UI test preflight JSON receipt.",
    )
    readiness_report.add_argument(
        "--simulator-suite-receipt",
        default=DEFAULT_SIMULATOR_SUITE_RECEIPT,
        help="Latest local Simulator suite JSON receipt.",
    )
    readiness_report.add_argument(
        "--simulator-only-resume-receipt",
        default=DEFAULT_SIMULATOR_ONLY_RESUME_RECEIPT,
        help="Latest simulator-only resume JSON receipt proving no physical iPhone was used.",
    )
    readiness_report.add_argument(
        "--provider-preflight-receipt",
        default=DEFAULT_OPENAI_PROVIDER_PREFLIGHT_RECEIPT,
        help="Redacted OpenAI provider preflight receipt proving server-side key readiness.",
    )
    readiness_report.add_argument(
        "--provider-env-sources-receipt",
        default=DEFAULT_PROVIDER_ENV_SOURCES_RECEIPT,
        help="Redacted provider env source receipt proving which server-side key source is visible.",
    )
    readiness_report.add_argument(
        "--provider-env-sources-all-profiles-receipt",
        default=DEFAULT_PROVIDER_ENV_SOURCES_ALL_PROFILES_RECEIPT,
        help="Redacted provider env source receipt scanning every Hermes profile for diagnostics only.",
    )
    readiness_report.add_argument(
        "--iphone-credential-boundary-receipt",
        default=DEFAULT_IPHONE_CREDENTIAL_BOUNDARY_RECEIPT,
        help="Receipt proving iPhone client code does not contain OpenAI provider credentials or direct Images API endpoints.",
    )
    readiness_report.add_argument(
        "--gate-f-preflight-receipt",
        default=DEFAULT_GATE_F_PREFLIGHT_RECEIPT,
        help="Latest Gate F external preflight JSON receipt.",
    )
    readiness_report.add_argument(
        "--gate-f-handoff-receipt",
        default=DEFAULT_GATE_F_HANDOFF_RECEIPT,
        help="Latest Gate F no-device handoff JSON receipt.",
    )
    readiness_report.add_argument(
        "--physical-device-preflight-receipt",
        default=DEFAULT_PHYSICAL_DEVICE_PREFLIGHT_RECEIPT,
        help="Latest physical iPhone Xcode destination preflight JSON receipt.",
    )
    readiness_report.add_argument(
        "--screenshot-file",
        default="/tmp/agent-pocket-simulator-openai-provider-smoke-autocapture.png",
        help="Simulator screenshot evidence from the OpenAI-compatible smoke.",
    )
    readiness_report.add_argument(
        "--picker-ui-screenshot-file",
        default=DEFAULT_SIMULATOR_PICKER_UI_SCREENSHOT,
        help="Simulator screenshot evidence for the connected PhotosPicker entry state.",
    )
    readiness_report.add_argument(
        "--discovery-refresh-receipt-file",
        default=DEFAULT_SIMULATOR_DISCOVERY_REFRESH_RECEIPT,
        help="Simulator receipt proving no-payload discovery refreshes /pairing/dev before pairing.",
    )
    readiness_report.add_argument(
        "--discovery-refresh-screenshot-file",
        default=DEFAULT_SIMULATOR_DISCOVERY_REFRESH_SCREENSHOT,
        help="Simulator screenshot evidence for no-payload discovery refresh.",
    )
    readiness_report.add_argument(
        "--capture-ready-screenshot-file",
        default="/tmp/agent-pocket-simulator-capture-ready.png",
        help="Simulator screenshot evidence that selected-photo ready state shows Send to Pocket Agent.",
    )
    readiness_report.add_argument(
        "--capture-ready-receipt-file",
        default=DEFAULT_SIMULATOR_CAPTURE_READY_RECEIPT,
        help="App-authored receipt proving selected-photo ready state enables Send to Pocket Agent.",
    )
    readiness_report.add_argument(
        "--capture-completed-screenshot-file",
        default=DEFAULT_SIMULATOR_CAPTURE_COMPLETED_SCREENSHOT,
        help="Simulator screenshot evidence that completed capture shows Review Results.",
    )
    readiness_report.add_argument(
        "--capture-completed-receipt-file",
        default=DEFAULT_SIMULATOR_CAPTURE_COMPLETED_RECEIPT,
        help="App-authored receipt proving completed capture promotes Review Results.",
    )
    readiness_report.add_argument(
        "--result-gallery-screenshot-file",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_SCREENSHOT,
        help="Simulator screenshot evidence for the result gallery review state.",
    )
    readiness_report.add_argument(
        "--result-gallery-receipt-file",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_RECEIPT,
        help="App-authored receipt proving the result gallery can review returned variants.",
    )
    readiness_report.add_argument(
        "--result-gallery-downloaded-screenshot-file",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_SCREENSHOT,
        help="Simulator screenshot evidence for the downloaded result gallery state.",
    )
    readiness_report.add_argument(
        "--result-gallery-downloaded-receipt-file",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_RECEIPT,
        help="App-authored receipt proving Save and Share are available after download.",
    )
    readiness_report.add_argument(
        "--physical-openai-receipt",
        default="docs/qa-receipts/openai-photo-flow.json",
        help="Physical iPhone OpenAI provider receipt required to close Gate F.",
    )
    readiness_report.add_argument(
        "--env-file",
        default="",
        help="Optional server-side env file to load for external provider readiness; secret values are never printed.",
    )
    add_hermes_provider_args(readiness_report)
    readiness_report.add_argument(
        "--output-file",
        default="",
        help="Optional Markdown file to write.",
    )

    verify_receipt = subparsers.add_parser(
        "verify-receipt",
        help="Verify a saved QA receipt JSON proves connection restore or full photo flow.",
    )
    verify_receipt.add_argument("--file", required=True, help="Path to a JSON receipt written by --receipt-file.")
    verify_receipt.add_argument(
        "--phase",
        choices=["connection", "discovery-refresh", "photo-flow", "iphone-credential-boundary"],
        required=True,
        help="Receipt phase to verify.",
    )
    verify_receipt.add_argument(
        "--photo-provider",
        default="",
        help="Optional expected provider name recorded in the QA receipt, such as script or openai.",
    )

    run_lan = subparsers.add_parser(
        "run-lan",
        help="Start a LAN mock bridge, optionally relaunch the iPhone app, and wait for QA receipts.",
    )
    run_lan.add_argument("--host", required=True, help="Mac LAN or Tailscale IP reachable from the iPhone.")
    run_lan.add_argument("--port", type=int, default=8765, help="Mock bridge port.")
    run_lan.add_argument("--device-id", default="", help="CoreDevice id from xcrun devicectl list devices.")
    run_lan.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    run_lan.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer token for /mobile/v1/qa/status.")
    run_lan.add_argument("--connection-timeout", type=float, default=60, help="Seconds to wait for saved restore.")
    run_lan.add_argument("--photo-timeout", type=float, default=180, help="Seconds to wait for the manual photo flow.")
    run_lan.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds.")
    run_lan.add_argument("--no-launch", action="store_true", help="Do not relaunch Pocket Agent through devicectl.")
    run_lan.add_argument("--connection-only", action="store_true", help="Stop after saved connection restore is proven.")
    run_lan.add_argument("--no-bonjour", action="store_true", help="Do not publish a Bonjour discovery advertisement.")
    run_lan.add_argument(
        "--photo-provider",
        default="fixture",
        choices=PHOTO_PROVIDER_CHOICES,
        help="Photo provider used by the mock bridge task endpoint.",
    )
    run_lan.add_argument(
        "--photo-pack-root",
        default="photo-pack",
        help="Path to the Photo Pack root containing provider adapters.",
    )
    run_lan.add_argument(
        "--env-file",
        default="",
        help="Optional server-side env file to load before starting the mock bridge; secret values are never printed.",
    )
    add_hermes_provider_args(run_lan)
    run_lan.add_argument("--receipt-file", default="", help="Write the final QA receipt JSON to this path.")

    simulator_connection_smoke = subparsers.add_parser(
        "simulator-connection-smoke",
        help="Start a local bridge, launch the normal Simulator app, and wait for connection restore or pairing.",
    )
    simulator_connection_smoke.add_argument("--host", default="127.0.0.1", help="Host the Simulator can reach.")
    simulator_connection_smoke.add_argument("--port", type=int, default=8766, help="Mock bridge port.")
    simulator_connection_smoke.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_connection_smoke.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer token for /mobile/v1/qa/status.")
    simulator_connection_smoke.add_argument("--connection-timeout", type=float, default=45, help="Seconds to wait for connection.")
    simulator_connection_smoke.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds.")
    simulator_connection_smoke.add_argument("--no-launch", action="store_true", help="Do not launch the Simulator app.")
    simulator_connection_smoke.add_argument("--no-bonjour", action="store_true", help="Do not publish Bonjour pairing metadata.")
    simulator_connection_smoke.add_argument(
        "--receipt-file",
        default="docs/qa-receipts/simulator-connection-latest.json",
        help="Write the Simulator connection QA receipt JSON to this path.",
    )

    simulator_discovery_refresh_smoke = subparsers.add_parser(
        "simulator-discovery-refresh-smoke",
        help="Run a Simulator smoke where a no-payload discovered runtime refreshes /pairing/dev before pairing.",
    )
    simulator_discovery_refresh_smoke.add_argument("--host", default="127.0.0.1", help="Host the Simulator can reach.")
    simulator_discovery_refresh_smoke.add_argument("--port", type=int, default=8767, help="Mock bridge port.")
    simulator_discovery_refresh_smoke.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_discovery_refresh_smoke.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer token for /mobile/v1/qa/status.")
    simulator_discovery_refresh_smoke.add_argument("--connection-timeout", type=float, default=45, help="Seconds to wait for connection.")
    simulator_discovery_refresh_smoke.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds.")
    simulator_discovery_refresh_smoke.add_argument("--no-launch", action="store_true", help="Do not launch the Simulator app.")
    simulator_discovery_refresh_smoke.add_argument(
        "--receipt-file",
        default=DEFAULT_SIMULATOR_DISCOVERY_REFRESH_RECEIPT,
        help="Write the Simulator no-payload discovery refresh receipt JSON to this path.",
    )
    simulator_discovery_refresh_smoke.add_argument(
        "--screenshot-file",
        default=DEFAULT_SIMULATOR_DISCOVERY_REFRESH_SCREENSHOT,
        help="Path for the Simulator screenshot.",
    )

    simulator_openai_smoke = subparsers.add_parser(
        "simulator-openai-smoke",
        help="Run a one-command iOS Simulator smoke test through the OpenAI adapter and a local fake OpenAI API.",
    )
    simulator_openai_smoke.add_argument("--host", default="127.0.0.1", help="Host the Simulator can reach.")
    simulator_openai_smoke.add_argument("--port", type=int, default=8769, help="Mock bridge port.")
    simulator_openai_smoke.add_argument(
        "--fake-openai-port",
        type=int,
        default=8781,
        help="Local fake OpenAI Images Edits API port.",
    )
    simulator_openai_smoke.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_openai_smoke.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer token for /mobile/v1/qa/status.")
    simulator_openai_smoke.add_argument("--connection-timeout", type=float, default=45, help="Seconds to wait for bridge restore.")
    simulator_openai_smoke.add_argument("--photo-timeout", type=float, default=90, help="Seconds to wait for photo flow completion.")
    simulator_openai_smoke.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds.")
    simulator_openai_smoke.add_argument("--no-launch", action="store_true", help="Do not launch the Simulator app.")
    simulator_openai_smoke.add_argument(
        "--photo-pack-root",
        default="photo-pack",
        help="Path to the Photo Pack root containing provider adapters.",
    )
    simulator_openai_smoke.add_argument(
        "--output-format",
        default="png",
        choices=["jpeg", "png", "webp"],
        help="OpenAI-compatible output format requested from the adapter.",
    )
    simulator_openai_smoke.add_argument(
        "--receipt-file",
        default="docs/qa-receipts/simulator-openai-compatible-photo-flow.json",
        help="Write the bridge QA receipt JSON to this path.",
    )
    simulator_openai_smoke.add_argument(
        "--fake-openai-status-file",
        default="docs/qa-receipts/simulator-openai-compatible-fake-openai-status.json",
        help="Write the fake OpenAI request status JSON to this path.",
    )
    simulator_openai_smoke.add_argument(
        "--screenshot-file",
        default="",
        help="Optional path for a Simulator screenshot after photo-flow success.",
    )

    simulator_local_recipe_smoke = subparsers.add_parser(
        "simulator-local-recipe-smoke",
        help="Run a one-command iOS Simulator smoke test through the local recipe adapter.",
    )
    simulator_local_recipe_smoke.add_argument("--host", default="127.0.0.1", help="Host the Simulator can reach.")
    simulator_local_recipe_smoke.add_argument("--port", type=int, default=8769, help="Mock bridge port.")
    simulator_local_recipe_smoke.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_local_recipe_smoke.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer token for /mobile/v1/qa/status.")
    simulator_local_recipe_smoke.add_argument("--connection-timeout", type=float, default=45, help="Seconds to wait for bridge restore.")
    simulator_local_recipe_smoke.add_argument("--photo-timeout", type=float, default=90, help="Seconds to wait for photo flow completion.")
    simulator_local_recipe_smoke.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds.")
    simulator_local_recipe_smoke.add_argument("--no-launch", action="store_true", help="Do not launch the Simulator app.")
    simulator_local_recipe_smoke.add_argument(
        "--photo-pack-root",
        default="photo-pack",
        help="Path to the Photo Pack root containing provider adapters.",
    )
    simulator_local_recipe_smoke.add_argument(
        "--receipt-file",
        default="docs/qa-receipts/simulator-local-recipe-photo-flow.json",
        help="Write the bridge QA receipt JSON to this path.",
    )
    simulator_local_recipe_smoke.add_argument(
        "--screenshot-file",
        default="",
        help="Optional path for a Simulator screenshot after photo-flow success.",
    )

    simulator_capture_ready_smoke = subparsers.add_parser(
        "simulator-capture-ready-smoke",
        help="Launch the Debug-only Simulator view with a prepared selected photo and capture a screenshot.",
    )
    simulator_capture_ready_smoke.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_capture_ready_smoke.add_argument("--no-launch", action="store_true", help="Do not launch the Simulator app.")
    simulator_capture_ready_smoke.add_argument(
        "--settle-seconds",
        type=float,
        default=1.0,
        help="Seconds to wait before taking the screenshot.",
    )
    simulator_capture_ready_smoke.add_argument(
        "--screenshot-file",
        default="/tmp/agent-pocket-simulator-capture-ready.png",
        help="Path for the Simulator screenshot.",
    )
    simulator_capture_ready_smoke.add_argument(
        "--receipt-file",
        default=DEFAULT_SIMULATOR_CAPTURE_READY_RECEIPT,
        help="Path to write the app-authored selected-photo ready receipt.",
    )

    simulator_capture_completed_smoke = subparsers.add_parser(
        "simulator-capture-completed-smoke",
        help="Launch the Debug-only Simulator view with a completed capture and capture a screenshot.",
    )
    simulator_capture_completed_smoke.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_capture_completed_smoke.add_argument("--no-launch", action="store_true", help="Do not launch the Simulator app.")
    simulator_capture_completed_smoke.add_argument(
        "--settle-seconds",
        type=float,
        default=3.0,
        help="Seconds to wait before taking the screenshot.",
    )
    simulator_capture_completed_smoke.add_argument(
        "--screenshot-file",
        default=DEFAULT_SIMULATOR_CAPTURE_COMPLETED_SCREENSHOT,
        help="Path for the Simulator screenshot.",
    )
    simulator_capture_completed_smoke.add_argument(
        "--receipt-file",
        default=DEFAULT_SIMULATOR_CAPTURE_COMPLETED_RECEIPT,
        help="Path to write the app-authored completed capture receipt.",
    )

    simulator_result_gallery_smoke = subparsers.add_parser(
        "simulator-result-gallery-smoke",
        help="Launch the Debug-only result gallery view and capture a screenshot.",
    )
    simulator_result_gallery_smoke.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_result_gallery_smoke.add_argument("--no-launch", action="store_true", help="Do not launch the Simulator app.")
    simulator_result_gallery_smoke.add_argument(
        "--settle-seconds",
        type=float,
        default=2.0,
        help="Seconds to wait before taking the screenshot.",
    )
    simulator_result_gallery_smoke.add_argument(
        "--screenshot-file",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_SCREENSHOT,
        help="Path for the Simulator screenshot.",
    )
    simulator_result_gallery_smoke.add_argument(
        "--receipt-file",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_RECEIPT,
        help="Path to write the app-authored result gallery receipt.",
    )

    simulator_result_gallery_downloaded_smoke = subparsers.add_parser(
        "simulator-result-gallery-downloaded-smoke",
        help="Launch the Debug-only downloaded result gallery view and capture a screenshot.",
    )
    simulator_result_gallery_downloaded_smoke.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_result_gallery_downloaded_smoke.add_argument("--no-launch", action="store_true", help="Do not launch the Simulator app.")
    simulator_result_gallery_downloaded_smoke.add_argument(
        "--settle-seconds",
        type=float,
        default=2.0,
        help="Seconds to wait before taking the screenshot.",
    )
    simulator_result_gallery_downloaded_smoke.add_argument(
        "--screenshot-file",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_SCREENSHOT,
        help="Path for the Simulator screenshot.",
    )
    simulator_result_gallery_downloaded_smoke.add_argument(
        "--receipt-file",
        default=DEFAULT_SIMULATOR_RESULT_GALLERY_DOWNLOADED_RECEIPT,
        help="Path to write the app-authored downloaded result gallery receipt.",
    )

    simulator_share_sheet_smoke = subparsers.add_parser(
        "simulator-share-sheet-smoke",
        help="Launch the Debug-only share-sheet handoff view and capture a screenshot.",
    )
    simulator_share_sheet_smoke.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_share_sheet_smoke.add_argument("--no-launch", action="store_true", help="Do not launch the Simulator app.")
    simulator_share_sheet_smoke.add_argument(
        "--settle-seconds",
        type=float,
        default=2.0,
        help="Seconds to wait before taking the screenshot.",
    )
    simulator_share_sheet_smoke.add_argument(
        "--screenshot-file",
        default=DEFAULT_SIMULATOR_SHARE_SHEET_SCREENSHOT,
        help="Path for the Simulator screenshot.",
    )
    simulator_share_sheet_smoke.add_argument(
        "--receipt-file",
        default=DEFAULT_SIMULATOR_SHARE_SHEET_RECEIPT,
        help="Path to write the app-authored share-sheet receipt.",
    )

    simulator_picker_ui_smoke = subparsers.add_parser(
        "simulator-picker-ui-smoke",
        help="Launch the Debug-only connected PhotosPicker UI view and capture a screenshot.",
    )
    simulator_picker_ui_smoke.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID, help="Pocket Agent app bundle id.")
    simulator_picker_ui_smoke.add_argument("--no-launch", action="store_true", help="Do not launch the Simulator app.")
    simulator_picker_ui_smoke.add_argument(
        "--settle-seconds",
        type=float,
        default=1.0,
        help="Seconds to wait before taking the screenshot.",
    )
    simulator_picker_ui_smoke.add_argument(
        "--screenshot-file",
        default=DEFAULT_SIMULATOR_PICKER_UI_SCREENSHOT,
        help="Path for the Simulator screenshot.",
    )

    simulator_seed_photo_library = subparsers.add_parser(
        "simulator-seed-photo-library",
        help="Generate a fixture image and add it to the booted iOS Simulator photo library.",
    )
    simulator_seed_photo_library.add_argument(
        "--device",
        default="booted",
        help="Simulator device UDID or 'booted'.",
    )
    simulator_seed_photo_library.add_argument(
        "--image-file",
        default=DEFAULT_SIMULATOR_LIBRARY_FIXTURE,
        help="Path where the generated fixture PNG should be written before addmedia.",
    )

    test_receipt = subparsers.add_parser(
        "test-receipt",
        help="Run a verification command and write a compact JSON receipt for gate-audit.",
    )
    test_receipt.add_argument("--name", required=True, help="Receipt name, such as python or swift.")
    test_receipt.add_argument("--receipt-file", required=True, help="Path to write the test receipt JSON.")
    test_receipt.add_argument("--timeout", type=float, default=300, help="Seconds before the verification command times out.")
    test_receipt.add_argument(
        "test_command",
        nargs=argparse.REMAINDER,
        help="Command to run after --, for example: -- swift test.",
    )

    status = subparsers.add_parser("status", help="Print the raw QA status JSON.")
    _add_connection_args(status)

    smoke_real_provider = subparsers.add_parser(
        "smoke-real-provider",
        help="Run a no-phone server-side HTTP smoke through image intake, universal intake, and Recall.",
    )
    mode = smoke_real_provider.add_mutually_exclusive_group()
    mode.add_argument(
        "--fake",
        action="store_const",
        const="fake",
        dest="mode",
        default="fake",
        help="Run against the deterministic fake provider. This is the default and is CI-safe.",
    )
    mode.add_argument(
        "--real",
        action="store_const",
        const="real",
        dest="mode",
        help="Run against the real Anthropic provider. Requires ANTHROPIC_API_KEY and is for manual local QA.",
    )
    smoke_real_provider.add_argument(
        "--provider",
        choices=["fake", "anthropic", "hermes"],
        default="",
        help="Manual provider selection for real-provider smoke. Defaults to --fake; --real remains an Anthropic shortcut.",
    )
    smoke_real_provider.add_argument(
        "--base-url",
        default="",
        help="Optional existing Mobile Bridge base URL. Defaults to starting a temporary loopback bridge.",
    )
    smoke_real_provider.add_argument("--host", default="127.0.0.1", help="Temporary bridge bind host.")
    smoke_real_provider.add_argument("--port", type=int, default=0, help="Temporary bridge port, or 0 for any free port.")
    smoke_real_provider.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer token for /mobile/v1.")
    smoke_real_provider.add_argument("--timeout", type=float, default=60.0, help="Maximum seconds for each HTTP/task wait.")
    smoke_real_provider.add_argument("--interval", type=float, default=0.5, help="Task polling interval in seconds.")
    smoke_real_provider.add_argument(
        "--image-file",
        default="",
        help="Optional local image to upload. Defaults to a generated PNG fixture.",
    )
    smoke_real_provider.add_argument(
        "--photo-pack-root",
        default="photo-pack",
        help="Path to the Photo Pack root for temporary bridge construction.",
    )

    wait_connection = subparsers.add_parser(
        "wait-connection",
        help="Wait until a launched iPhone app has restored the saved Hermes connection.",
    )
    _add_connection_args(wait_connection)
    _add_wait_args(wait_connection, timeout=60)

    wait_photo_flow = subparsers.add_parser(
        "wait-photo-flow",
        help="Wait until a real iPhone photo flow has uploaded, completed a task, and downloaded a result.",
    )
    _add_connection_args(wait_photo_flow)
    _add_wait_args(wait_photo_flow, timeout=180)

    return parser


def _add_connection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", required=True, help="Mock bridge base URL, such as http://192.168.1.42:8765.")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer token for /mobile/v1/qa/status.")


def _add_wait_args(parser: argparse.ArgumentParser, timeout: int) -> None:
    parser.add_argument("--timeout", type=float, default=timeout, help="Maximum seconds to wait.")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds.")
    parser.add_argument("--receipt-file", default="", help="Write the QA receipt JSON to this path.")


def _wait_for_status(
    base_url: str,
    token: str,
    timeout_seconds: float,
    interval_seconds: float,
    evaluator,
    status_fetcher: Callable[..., Mapping[str, Any]] = fetch_qa_status,
    phase: str = "status",
    receipt_file: str = "",
    out=None,
    err=None,
) -> int:
    deadline = time.monotonic() + timeout_seconds
    last_status: Mapping[str, Any] = {}
    last_result = EvaluationResult(ok=False, missing=["status"])
    last_error: Optional[str] = None

    while True:
        try:
            last_status = status_fetcher(base_url, token=token)
            last_error = None
            last_result = evaluator(last_status)
            if last_result.ok:
                payload = _receipt_payload(
                    phase=phase,
                    ok=True,
                    base_url=base_url,
                    status=last_status,
                    missing=[],
                )
                _write_receipt(receipt_file, payload)
                _print_json(payload, stream=out)
                return 0
        except Exception as error:
            last_error = str(error)
            last_result = EvaluationResult(ok=False, missing=["status"])
        remaining = deadline - time.monotonic()
        if remaining <= 0 or interval_seconds <= 0:
            break
        time.sleep(min(interval_seconds, remaining))

    payload = _receipt_payload(
        phase=phase,
        ok=False,
        base_url=base_url,
        status=last_status,
        missing=last_result.missing,
    )
    if last_error:
        payload["error"] = last_error
    _write_receipt(receipt_file, payload)
    _print_json(payload, stream=err or sys.stderr)
    return 1


def _receipt_provider_name(status: Mapping[str, Any]) -> str:
    provider = status.get("provider")
    if isinstance(provider, Mapping):
        name = provider.get("name")
        if isinstance(name, str):
            return name

    tasks = status.get("tasks")
    if isinstance(tasks, Mapping):
        last_task = tasks.get("last_task")
        if isinstance(last_task, Mapping):
            provider_name = last_task.get("provider")
            if isinstance(provider_name, str):
                return provider_name
    return ""


def _last_task(status: Mapping[str, Any]) -> Mapping[str, Any]:
    tasks = status.get("tasks")
    if not isinstance(tasks, Mapping):
        return {}
    last_task = tasks.get("last_task")
    return last_task if isinstance(last_task, Mapping) else {}


def _has_recipe_composition(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("selected_aspect_ratio"), str)
        and bool(value.get("selected_aspect_ratio"))
    )


def _has_recipe_crop(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    crop = value.get("crop")
    if not isinstance(crop, Mapping):
        return False
    required = ("x", "y", "width", "height")
    if not all(isinstance(crop.get(key), (int, float)) for key in required):
        return False
    return float(crop["width"]) > 0 and float(crop["height"]) > 0


def _has_recipe_difference_metrics(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    required = ("master_difference_score", "social_difference_score")
    return all(isinstance(value.get(key), (int, float)) and float(value[key]) > 0 for key in required)


def _count(status: Mapping[str, Any], section: str, key: str) -> int:
    value = status.get(section, {})
    if not isinstance(value, Mapping):
        return 0
    raw = value.get(key, 0)
    return raw if isinstance(raw, int) else 0


def _print_json(value: Mapping[str, Any], stream=None) -> None:
    print(json.dumps(value, indent=2, sort_keys=True), file=stream or sys.stdout)


def _receipt_payload(
    phase: str,
    ok: bool,
    base_url: str,
    status: Mapping[str, Any],
    missing: list[str],
) -> dict[str, Any]:
    return {
        "base_url": base_url,
        "missing": missing,
        "ok": ok,
        "phase": phase,
        "status": status,
    }


def _test_receipt_payload(name: str, command: list[str], result: CommandResult) -> dict[str, Any]:
    return {
        "phase": "test-command",
        "name": name,
        "command": command,
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout_tail": _tail_text(result.stdout),
        "stderr_tail": _tail_text(result.stderr),
    }


def _write_receipt(path: str, payload: Mapping[str, Any]) -> None:
    if not path:
        return
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _audit_files(root: str, paths: Sequence[str]) -> list[dict[str, Any]]:
    return [_audit_file(root, path) for path in paths]


def _audit_file(root: str, path: str) -> dict[str, Any]:
    return {
        "path": path,
        "exists": bool(path) and os.path.exists(_resolve_audit_path(root, path)),
    }


def _audit_simulator_screenshot(root: str, path: str) -> dict[str, Any]:
    resolved = _resolve_audit_path(root, path) if path else ""
    exists = bool(path) and os.path.exists(resolved)
    evidence: dict[str, Any] = {
        "path": path,
        "exists": exists,
        "ok": False,
        "missing": [],
    }
    if not exists:
        evidence["missing"] = [str(path or "Simulator screenshot file")]
        return evidence
    if not _simulator_screenshot_has_visible_content(resolved):
        evidence["missing"] = ["visible Simulator screenshot content"]
        return evidence
    evidence["ok"] = True
    return evidence


def _configured_tailscale_cli(env: Mapping[str, str]) -> str:
    return str(env.get("TAILSCALE_CLI", "")).strip()


def _tailscale_ip_command(env: Mapping[str, str]) -> list[str]:
    configured_cli = _configured_tailscale_cli(env)
    if configured_cli:
        return [configured_cli, "ip", "-4"]
    return ["tailscale", "ip", "-4"]


def _tailscale_cli_metadata(env: Mapping[str, str], default_path: str) -> dict[str, Any]:
    configured_cli = _configured_tailscale_cli(env)
    return {
        "path": configured_cli or default_path,
        "configured_by": "TAILSCALE_CLI" if configured_cli else "PATH",
    }


def _build_tailscale_report(
    runner: Callable[[list[str]], CommandResult],
    env: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    env_values = os.environ if env is None else env
    configured_cli = _configured_tailscale_cli(env_values)
    if configured_cli:
        cli = runner([configured_cli, "version"])
        cli_path = configured_cli
        cli_ok = cli.returncode == 0
        cli_error = "" if cli_ok else (_clean_error(cli) or "TAILSCALE_CLI is set but not runnable")
    else:
        cli = runner(["which", "tailscale"])
        cli_path = _first_line(cli.stdout)
        cli_ok = cli.returncode == 0
        cli_error = "" if cli_ok else (_clean_error(cli) or "tailscale CLI not found in PATH")

    if not cli_ok:
        ip_error = "Install or expose the tailscale CLI in PATH first."
        return {
            "ok": False,
            "ip": "",
            "error": cli_error,
            "cli": {
                "ok": False,
                "path": cli_path,
                "error": cli_error,
                "configured_by": "TAILSCALE_CLI" if configured_cli else "PATH",
            },
            "ip_check": {
                "ok": False,
                "value": "",
                "error": ip_error,
            },
        }

    ip = runner(_tailscale_ip_command(env_values))
    tailscale_ip = _first_line(ip.stdout)
    ip_ok = ip.returncode == 0 and bool(tailscale_ip)
    ip_error = "" if ip_ok else (_clean_error(ip) or "Tailscale IP unavailable. Log in or bring the tailnet connection up.")

    return {
        "ok": ip_ok,
        "ip": tailscale_ip,
        "error": "" if ip_ok else ip_error,
        "cli": {
            "ok": True,
            "path": cli_path,
            "error": "",
            "configured_by": "TAILSCALE_CLI" if configured_cli else "PATH",
        },
        "ip_check": {
            "ok": ip_ok,
            "value": tailscale_ip,
            "error": "" if ip_ok else ip_error,
        },
    }


def _audit_receipt(
    root: str,
    path: str,
    expected_phase: str,
    expected_provider: str = "",
) -> dict[str, Any]:
    if not path:
        return {
            "path": path,
            "exists": False,
            "ok": False,
            "phase": expected_phase,
            "provider": expected_provider,
            "missing": ["receipt file"],
        }

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return {
            "path": path,
            "exists": False,
            "ok": False,
            "phase": expected_phase,
            "provider": expected_provider,
            "missing": ["receipt file"],
        }

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            "path": path,
            "exists": True,
            "ok": False,
            "phase": expected_phase,
            "provider": expected_provider,
            "missing": [f"readable receipt JSON: {error}"],
        }

    result = verify_receipt_payload(
        receipt,
        expected_phase=expected_phase,
        expected_provider=expected_provider,
    )
    return {
        "path": path,
        "exists": True,
        "ok": result.ok,
        "phase": expected_phase,
        "provider": expected_provider,
        "missing": result.missing,
    }


def _audit_iphone_credential_boundary(root: str, path: str) -> dict[str, Any]:
    if not path:
        return {
            "path": path,
            "exists": False,
            "ok": False,
            "phase": "iphone-credential-boundary",
            "missing": ["receipt file"],
        }
    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return {
            "path": path,
            "exists": False,
            "ok": False,
            "phase": "iphone-credential-boundary",
            "missing": ["receipt file"],
        }
    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            "path": path,
            "exists": True,
            "ok": False,
            "phase": "iphone-credential-boundary",
            "missing": [f"readable receipt JSON: {error}"],
        }
    result = verify_receipt_payload(receipt, expected_phase="iphone-credential-boundary")
    return {
        "path": path,
        "exists": True,
        "ok": result.ok,
        "phase": "iphone-credential-boundary",
        "missing": result.missing,
        "scanned_files": receipt.get("scanned_files", 0),
        "violations": receipt.get("violations", []),
        "iphone_credential_required": receipt.get("iphone_credential_required"),
    }


def _audit_fake_openai_status(root: str, path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "missing": ["fake OpenAI status file"],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            status = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            "path": path,
            "exists": True,
            "ok": False,
            "missing": [f"readable fake OpenAI status JSON: {error}"],
        }

    missing: list[str] = []
    if int(status.get("request_count", 0) or 0) < 1:
        missing.append("fake OpenAI request")
    last_request = status.get("last_request")
    if not isinstance(last_request, Mapping):
        missing.append("last fake OpenAI request")
        last_request = {}
    request_path = last_request.get("path")
    if request_path not in {"/images/edits", "/v1/images/edits"}:
        missing.append("OpenAI Images Edits path")
    if last_request.get("authorization_present") is not True:
        missing.append("authorization header")
    if last_request.get("content_type") != "multipart/form-data":
        missing.append("multipart form request")

    fields = last_request.get("fields")
    if not isinstance(fields, Mapping):
        missing.append("OpenAI request fields")
        fields = {}
    if not fields.get("model"):
        missing.append("model field")
    if not fields.get("n"):
        missing.append("variant count field")
    if not fields.get("output_format"):
        missing.append("output_format field")

    files = last_request.get("files")
    if not isinstance(files, Mapping):
        missing.append("OpenAI request files")
        files = {}
    image = files.get("image")
    if not isinstance(image, Mapping):
        missing.append("uploaded image file")
    elif int(image.get("size_bytes", 0) or 0) <= 0:
        missing.append("uploaded image bytes")

    return {
        "path": path,
        "exists": True,
        "ok": not missing,
        "request_count": status.get("request_count", 0),
        "missing": missing,
    }


def _audit_capture_ready_receipt(root: str, path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "phase": "capture-ready",
        "missing": ["capture-ready receipt file"],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "missing": [f"readable capture-ready receipt JSON: {error}"],
        }

    missing: list[str] = []
    if receipt.get("phase") != "capture-ready":
        missing.append("capture-ready phase")
    if receipt.get("ok") is not True:
        missing.append("ok receipt flag")
    if receipt.get("state") != "ready":
        missing.append("ready state")
    if receipt.get("has_prepared_upload") is not True:
        missing.append("prepared upload")
    send_enabled = _capture_ready_send_enabled(receipt)
    if send_enabled is not True:
        missing.append("Send to Pocket Agent enabled")
    if not str(receipt.get("file_name", "")):
        missing.append("selected file name")
    if not str(receipt.get("intent_title", "")):
        missing.append("intent title")
    if receipt.get("selection_source") != "library_fixture":
        missing.append("library selection source")
    if receipt.get("preprocessing_path") != "CaptureFlowViewModel.prepareSelectedImage":
        missing.append("prepareSelectedImage preprocessing path")
    if receipt.get("primary_action") not in {"Send to Pocket Agent", "Send to Local Agent", "Send to Hermes"}:
        missing.append("Send to Pocket Agent primary action")
    if receipt.get("ready_status_accessibility_identifier") != "selectedPhotoReadyStatus":
        missing.append("selected photo ready accessibility identifier")
    if receipt.get("send_button_accessibility_identifier") not in {"sendToKakaButton", "sendToLocalAgentButton", "sendToHermesButton"}:
        missing.append("Send to Pocket Agent accessibility identifier")

    return {
        "path": path,
        "exists": True,
        "ok": not missing,
        "phase": "capture-ready",
        "state": str(receipt.get("state", "")),
        "file_name": str(receipt.get("file_name", "")),
        "intent_title": str(receipt.get("intent_title", "")),
        "selection_source": str(receipt.get("selection_source", "")),
        "preprocessing_path": str(receipt.get("preprocessing_path", "")),
        "primary_action": str(receipt.get("primary_action", "")),
        "send_to_local_agent_enabled": send_enabled is True,
        "ready_status_accessibility_identifier": str(receipt.get("ready_status_accessibility_identifier", "")),
        "send_button_accessibility_identifier": str(receipt.get("send_button_accessibility_identifier", "")),
        "missing": missing,
    }


def _audit_capture_completed_receipt(root: str, path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "phase": "capture-completed",
        "missing": ["capture-completed receipt file"],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "missing": [f"readable capture-completed receipt JSON: {error}"],
        }

    missing = _capture_completed_receipt_missing(receipt)
    return {
        "path": path,
        "exists": True,
        "ok": not missing,
        "phase": "capture-completed",
        "state": str(receipt.get("state", "")),
        "task_id": str(receipt.get("task_id", "")),
        "variants_count": int(receipt.get("variants_count", 0) or 0),
        "missing": missing,
    }


def _audit_result_gallery_receipt(root: str, path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "phase": "result-gallery",
        "missing": ["result-gallery receipt file"],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "missing": [f"readable result-gallery receipt JSON: {error}"],
        }

    missing = _result_gallery_receipt_missing(receipt)
    return {
        "path": path,
        "exists": True,
        "ok": not missing,
        "phase": "result-gallery",
        "state": str(receipt.get("state", "")),
        "task_status": str(receipt.get("task_status", "")),
        "variants_count": int(receipt.get("variants_count", 0) or 0),
        "selected_variant_id": str(receipt.get("selected_variant_id", "")),
        "missing": missing,
    }


def _audit_result_gallery_downloaded_receipt(root: str, path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "phase": "result-gallery-downloaded",
        "missing": ["result-gallery downloaded receipt file"],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "missing": [f"readable result-gallery downloaded receipt JSON: {error}"],
        }

    missing = _result_gallery_downloaded_receipt_missing(receipt)
    return {
        "path": path,
        "exists": True,
        "ok": not missing,
        "phase": "result-gallery-downloaded",
        "state": str(receipt.get("state", "")),
        "task_status": str(receipt.get("task_status", "")),
        "variants_count": int(receipt.get("variants_count", 0) or 0),
        "selected_variant_id": str(receipt.get("selected_variant_id", "")),
        "downloaded_asset_bytes": int(receipt.get("downloaded_asset_bytes", 0) or 0),
        "downloaded_mime_type": str(receipt.get("downloaded_mime_type", "")),
        "recipe_summary": str(receipt.get("recipe_summary", "")),
        "share_caption": str(receipt.get("share_caption", "")),
        "missing": missing,
    }


def _result_gallery_receipt_is_ready(receipt: Mapping[str, Any]) -> bool:
    return not _result_gallery_receipt_missing(receipt)


def _result_gallery_receipt_missing(receipt: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    if receipt.get("phase") != "result-gallery":
        missing.append("result-gallery phase")
    if receipt.get("ok") is not True:
        missing.append("ok receipt flag")
    if receipt.get("state") != "ready":
        missing.append("ready state")
    if receipt.get("task_status") != "completed":
        missing.append("completed task status")
    if int(receipt.get("variants_count", 0) or 0) < 1:
        missing.append("edited variants")
    if not str(receipt.get("selected_variant_id", "")):
        missing.append("selected variant")
    if not str(receipt.get("selected_asset_id", "")):
        missing.append("selected asset")
    if receipt.get("has_explanation") is not True:
        missing.append("result explanation")
    if receipt.get("download_selected_enabled") is not True:
        missing.append("Download Selected enabled")
    if receipt.get("save_enabled") is not False:
        missing.append("Save disabled before download")
    if receipt.get("share_enabled") is not False:
        missing.append("Share disabled before download")
    return missing


def _capture_completed_receipt_is_ready(receipt: Mapping[str, Any]) -> bool:
    return not _capture_completed_receipt_missing(receipt)


def _capture_completed_receipt_missing(receipt: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    if receipt.get("phase") != "capture-completed":
        missing.append("capture-completed phase")
    if receipt.get("ok") is not True:
        missing.append("ok receipt flag")
    if receipt.get("state") != "completed":
        missing.append("completed state")
    if not str(receipt.get("task_id", "")):
        missing.append("task id")
    if int(receipt.get("variants_count", 0) or 0) < 1:
        missing.append("edited variants")
    if receipt.get("review_results_enabled") is not True:
        missing.append("Review Results enabled")
    if receipt.get("review_results_primary") is not True:
        missing.append("Review Results primary action")
    send_enabled = receipt.get("send_to_local_agent_enabled")
    if send_enabled is None:
        send_enabled = receipt.get("send_to_hermes_enabled")
    if send_enabled is not False:
        missing.append("Send to Pocket Agent no longer primary")
    return missing


def _result_gallery_downloaded_receipt_is_ready(receipt: Mapping[str, Any]) -> bool:
    return not _result_gallery_downloaded_receipt_missing(receipt)


def _result_gallery_downloaded_receipt_missing(receipt: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    if receipt.get("phase") != "result-gallery-downloaded":
        missing.append("result-gallery-downloaded phase")
    if receipt.get("ok") is not True:
        missing.append("ok receipt flag")
    if receipt.get("state") != "downloaded":
        missing.append("downloaded state")
    if receipt.get("task_status") != "completed":
        missing.append("completed task status")
    if int(receipt.get("variants_count", 0) or 0) < 1:
        missing.append("edited variants")
    if not str(receipt.get("selected_variant_id", "")):
        missing.append("selected variant")
    if not str(receipt.get("selected_asset_id", "")):
        missing.append("selected asset")
    if int(receipt.get("downloaded_asset_bytes", 0) or 0) <= 0:
        missing.append("downloaded asset bytes")
    if not str(receipt.get("downloaded_mime_type", "")):
        missing.append("downloaded MIME type")
    if not str(receipt.get("share_caption", "")):
        missing.append("share caption")
    if receipt.get("download_selected_enabled") is not False:
        missing.append("Download Selected disabled after download")
    if receipt.get("save_enabled") is not True:
        missing.append("Save enabled after download")
    if receipt.get("share_enabled") is not True:
        missing.append("Share enabled after download")
    return missing


def _share_sheet_receipt_is_ready(receipt: Mapping[str, Any]) -> bool:
    return not _share_sheet_receipt_missing(receipt)


def _share_sheet_receipt_missing(receipt: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    if receipt.get("phase") != "share-sheet-handoff":
        missing.append("share-sheet-handoff phase")
    if receipt.get("ok") is not True:
        missing.append("ok receipt flag")
    if receipt.get("state") != "presented":
        missing.append("presented state")
    if not str(receipt.get("selected_variant_id", "")):
        missing.append("selected variant")
    if not str(receipt.get("selected_asset_id", "")):
        missing.append("selected asset")
    if int(receipt.get("downloaded_asset_bytes", 0) or 0) <= 0:
        missing.append("downloaded asset bytes")
    if not str(receipt.get("downloaded_mime_type", "")):
        missing.append("downloaded MIME type")
    if int(receipt.get("share_items_count", 0) or 0) < 2:
        missing.append("image and caption share items")
    if not str(receipt.get("share_caption", "")):
        missing.append("share caption")
    if receipt.get("handoff_attempted") is not True:
        missing.append("share handoff attempted")
    if receipt.get("share_sheet_presented") is not True:
        missing.append("share sheet presented")
    return missing


def _audit_test_receipt(root: str, path: str, expected_name: str) -> dict[str, Any]:
    missing_label = f"{expected_name} test receipt file"
    if not path:
        return {
            "path": path,
            "exists": False,
            "ok": False,
            "name": expected_name,
            "missing": [missing_label],
        }

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return {
            "path": path,
            "exists": False,
            "ok": False,
            "name": expected_name,
            "missing": [missing_label],
        }

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            "path": path,
            "exists": True,
            "ok": False,
            "name": expected_name,
            "missing": [f"readable {expected_name} test receipt JSON: {error}"],
        }

    missing: list[str] = []
    if receipt.get("phase") != "test-command":
        missing.append("test-command phase")
    if receipt.get("name") != expected_name:
        missing.append(f"{expected_name} test receipt name")
    if receipt.get("ok") is not True:
        missing.append(f"{expected_name} tests passing")
    if receipt.get("returncode") != 0:
        missing.append(f"{expected_name} test returncode")
    command = receipt.get("command")
    if not isinstance(command, list) or not command:
        missing.append(f"{expected_name} test command")
    stdout_tail = str(receipt.get("stdout_tail", ""))
    stderr_tail = str(receipt.get("stderr_tail", ""))

    return {
        "path": path,
        "exists": True,
        "ok": not missing,
        "name": expected_name,
        "command": command if isinstance(command, list) else [],
        "summary": _test_receipt_output_summary(expected_name, stdout_tail, stderr_tail),
        "missing": missing,
    }


def _test_receipt_output_summary(name: str, stdout_tail: str, stderr_tail: str) -> str:
    text = "\n".join(part for part in [stdout_tail.strip(), stderr_tail.strip()] if part)
    if not text:
        return ""

    if name == "python":
        passed_matches = re.findall(r"\b(\d+)\s+passed\b", text)
        if passed_matches:
            return f"{passed_matches[-1]} passed"

    if name == "swift":
        executed_matches = re.findall(
            r"Executed\s+(\d+)\s+tests,\s+with\s+(\d+)\s+failures",
            text,
        )
        if executed_matches:
            tests, failures = executed_matches[-1]
            return f"{tests} tests, {failures} failures"

    return "passed" if "passed" in text.lower() else ""


def _audit_simulator_suite(root: str, path: str) -> dict[str, Any]:
    required_step_names = [
        "seed_photo_library",
        "connection_smoke",
        "discovery_refresh_smoke",
        "picker_ui_smoke",
        "capture_ready_smoke",
        "capture_completed_smoke",
        "result_gallery_smoke",
        "result_gallery_downloaded_smoke",
        "openai_smoke",
    ]
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "status": "missing_receipt",
        "required_steps": required_step_names,
        "failed_required_steps": [],
        "missing": ["simulator suite receipt"],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "status": "unreadable_receipt",
            "missing": [f"readable simulator suite JSON: {error}"],
        }

    steps = receipt.get("steps")
    if not isinstance(steps, Mapping):
        steps = {}

    missing: list[str] = []
    failed_required_steps: list[str] = []
    if receipt.get("phase") != "simulator-suite":
        missing.append("simulator-suite phase")
    for name in required_step_names:
        step = steps.get(name)
        if not isinstance(step, Mapping):
            missing.append(f"{name} step")
            failed_required_steps.append(name)
            continue
        if step.get("required") is not True:
            missing.append(f"{name} required")
        if step.get("ok") is not True:
            failed_required_steps.append(name)

    receipt_failed_steps = receipt.get("failed_required_steps")
    if isinstance(receipt_failed_steps, list):
        for name in receipt_failed_steps:
            name_text = str(name)
            if name_text and name_text not in failed_required_steps:
                failed_required_steps.append(name_text)

    if failed_required_steps:
        missing.append("required simulator suite steps passing")
    if receipt.get("ok") is not True:
        missing.append("simulator suite ok")

    missing = list(dict.fromkeys(missing))
    failed_required_steps = list(dict.fromkeys(failed_required_steps))

    return {
        "path": path,
        "exists": True,
        "ok": not missing,
        "status": "passed" if not missing else "failed",
        "required_steps": required_step_names,
        "failed_required_steps": failed_required_steps,
        "missing": missing,
    }


def _audit_simulator_only_resume(root: str, path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "status": "missing_receipt",
        "execution_mode": "",
        "physical_iphone_used": None,
        "physical_device_launch_attempted": None,
        "real_device_commands_executed": [],
        "missing": ["simulator-only resume receipt"],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "status": "unreadable_receipt",
            "missing": [f"readable simulator-only resume JSON: {error}"],
        }

    commands = receipt.get("real_device_commands_executed", [])
    if not isinstance(commands, list):
        commands = ["real_device_commands_executed list"]
    commands = [str(command) for command in commands]

    missing: list[str] = []
    if receipt.get("phase") != "simulator-only-resume":
        missing.append("simulator-only-resume phase")
    if receipt.get("ok") is not True:
        missing.append("ok receipt flag")
    if receipt.get("execution_mode") != "local-mac-simulator-only":
        missing.append("local Mac Simulator execution mode")
    if receipt.get("physical_iphone_used") is not False:
        missing.append("physical iPhone not used")
    if receipt.get("physical_device_launch_attempted") is not False:
        missing.append("no physical device launch attempt")
    if commands:
        missing.append("no real-device commands executed")
    suite = receipt.get("simulator_suite", {})
    if not isinstance(suite, Mapping) or suite.get("ok") is not True:
        missing.append("simulator suite passed inside resume")

    return {
        "path": path,
        "exists": True,
        "ok": not missing,
        "status": "passed" if not missing else "failed",
        "execution_mode": str(receipt.get("execution_mode", "")),
        "physical_iphone_used": receipt.get("physical_iphone_used"),
        "physical_device_launch_attempted": receipt.get("physical_device_launch_attempted"),
        "real_device_commands_executed": commands,
        "missing": missing,
    }


def _audit_gate_f_preflight(root: str, path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "ready_to_run": False,
        "status": "missing_receipt",
        "missing_to_start": [],
        "missing_to_close": [],
        "missing": ["Gate F preflight receipt"],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "status": "unreadable_receipt",
            "missing": [f"readable Gate F preflight JSON: {error}"],
        }

    missing_to_start = receipt.get("missing_to_start", [])
    missing_to_close = receipt.get("missing_to_close", [])
    if not isinstance(missing_to_start, list):
        missing_to_start = ["missing_to_start list"]
    if not isinstance(missing_to_close, list):
        missing_to_close = ["missing_to_close list"]
    commands = receipt.get("commands", {})
    if not isinstance(commands, Mapping):
        commands = {}
    checks = receipt.get("checks", {})
    if not isinstance(checks, Mapping):
        checks = {}
    endpoint = checks.get("endpoint", receipt.get("endpoint", {}))
    if not isinstance(endpoint, Mapping):
        endpoint = {}
    physical_device_preflight = checks.get("physical_device_preflight", {})
    if not isinstance(physical_device_preflight, Mapping):
        physical_device_preflight = {}
    provider_env_sources = checks.get("provider_env_sources_receipt", {})
    if not isinstance(provider_env_sources, Mapping):
        provider_env_sources = {}
    start_blockers = receipt.get("start_blockers", [])
    if not isinstance(start_blockers, list):
        start_blockers = []
    server_diagnostics = receipt.get("server_diagnostics", {})
    if not isinstance(server_diagnostics, Mapping):
        server_diagnostics = {}
    endpoint_missing = endpoint.get("missing", []) if endpoint else []
    if not isinstance(endpoint_missing, list):
        endpoint_missing = []

    ready_to_run = bool(receipt.get("ready_to_run"))
    ok = receipt.get("ok") is True
    if ok:
        status = "passed"
    elif missing_to_start:
        status = "blocked_to_start"
    elif ready_to_run:
        status = "ready_for_real_iphone_run"
    else:
        status = "not_ready"

    missing: list[str] = []
    if "ready_to_run" not in receipt:
        missing.append("ready_to_run")
    if "missing_to_start" not in receipt:
        missing.append("missing_to_start")
    if "missing_to_close" not in receipt:
        missing.append("missing_to_close")

    return {
        "path": path,
        "exists": True,
        "ok": ok,
        "ready_to_run": ready_to_run,
        "status": status,
        "missing_to_start": [str(item) for item in missing_to_start],
        "missing_to_close": [str(item) for item in missing_to_close],
        "commands": {
            str(key): str(value)
            for key, value in commands.items()
            if key in [
                "provider_preflight",
                "provider_env_sources",
                "hermes_auth_add_openai",
                "hermes_openai_auth_import",
                "run_real_iphone_openai",
                "verify_real_iphone_openai",
                "gate_f_resume",
            ]
        },
        "endpoint": {
            "ok": bool(endpoint.get("ok")),
            "source": str(endpoint.get("source", "")),
            "host": str(endpoint.get("host", "")),
            "missing": [str(item) for item in endpoint_missing],
        } if endpoint else {},
        "physical_device_preflight": physical_device_preflight,
        "provider_env_sources": provider_env_sources,
        "start_blockers": [dict(item) for item in start_blockers if isinstance(item, Mapping)],
        "server_diagnostics": dict(server_diagnostics),
        "missing": missing,
    }


def _audit_provider_preflight(root: str, path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "status": "missing_receipt",
        "provider": "",
        "env": {"OPENAI_API_KEY": "missing"},
        "adapter": {},
        "missing": ["provider preflight receipt"],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "status": "unreadable_receipt",
            "missing": [f"readable provider preflight JSON: {error}"],
        }

    env = receipt.get("env", {})
    if not isinstance(env, Mapping):
        env = {}
    adapter = receipt.get("adapter", {})
    if not isinstance(adapter, Mapping):
        adapter = {}
    config = receipt.get("config", {})
    if not isinstance(config, Mapping):
        config = {}
    base_url = config.get("OPENAI_BASE_URL", {})
    if not isinstance(base_url, Mapping):
        base_url = {}
    hermes = receipt.get("hermes", {})
    if not isinstance(hermes, Mapping):
        hermes = {}
    provider = str(receipt.get("provider", ""))
    key_state = str(env.get("OPENAI_API_KEY", "missing"))

    missing: list[str] = []
    if provider != "openai":
        missing.append("provider openai")
    if key_state != "set":
        missing.append("OPENAI_API_KEY")
    if key_state not in {"set", "missing"}:
        missing.append("redacted OPENAI_API_KEY state")
    if adapter and adapter.get("exists") is False:
        missing.append("OpenAI Photo Pack adapter")

    ok = receipt.get("ok") is True and not missing
    return {
        "path": path,
        "exists": True,
        "ok": ok,
        "status": "passed" if ok else "missing_provider_evidence",
        "provider": provider,
        "env": {"OPENAI_API_KEY": key_state if key_state in {"set", "missing"} else "invalid"},
        "adapter": {
            "path": str(adapter.get("path", "")),
            "exists": bool(adapter.get("exists")) if "exists" in adapter else False,
        },
        "config": {
            "OPENAI_BASE_URL": {
                "state": str(base_url.get("state", "")),
                "value": str(base_url.get("value", "")),
                "redacted": bool(base_url.get("redacted")),
            },
        },
        "hermes": dict(hermes),
        "missing": missing,
    }


def _audit_provider_env_sources(root: str, path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "status": "missing_receipt",
        "key": "OPENAI_API_KEY",
        "env": {"OPENAI_API_KEY": "missing"},
        "hermes": {},
        "sources": [],
        "set_sources": [],
        "next_actions": [],
        "missing": ["provider env source receipt"],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "status": "unreadable_receipt",
            "missing": [f"readable provider env source JSON: {error}"],
        }

    key = str(receipt.get("key", "OPENAI_API_KEY")) or "OPENAI_API_KEY"
    env = receipt.get("env", {})
    if not isinstance(env, Mapping):
        env = {}
    key_state = str(env.get(key, "missing"))
    if key_state not in {"set", "missing"}:
        key_state = "invalid"
    hermes = receipt.get("hermes", {})
    if not isinstance(hermes, Mapping):
        hermes = {}
    set_sources = receipt.get("set_sources", [])
    if not isinstance(set_sources, list):
        set_sources = []
    sources = receipt.get("sources", [])
    if not isinstance(sources, list):
        sources = []
    shell_startup_files = receipt.get("shell_startup_files", {})
    if not isinstance(shell_startup_files, Mapping):
        shell_startup_files = {}
    shell_files = shell_startup_files.get("files", [])
    if not isinstance(shell_files, list):
        shell_files = []
    shell_set_files = shell_startup_files.get("set_files", [])
    if not isinstance(shell_set_files, list):
        shell_set_files = []
    next_actions = receipt.get("next_actions", [])
    if not isinstance(next_actions, list):
        next_actions = ["next_actions list"]
    missing: list[str] = []
    if key_state != "set":
        missing.append(key)
    if key_state == "invalid":
        missing.append(f"redacted {key} state")

    ok = receipt.get("ok") is True and key_state == "set" and bool(set_sources)
    return {
        "path": path,
        "exists": True,
        "ok": ok,
        "status": "passed" if ok else "missing_provider_env_source",
        "key": key,
        "env": {key: key_state},
        "hermes": dict(hermes),
        "shell_startup_files": {
            "home": str(shell_startup_files.get("home", "")),
            "key": str(shell_startup_files.get("key", key)),
            "state": str(shell_startup_files.get("state", "")),
            "counts_for_provider_readiness": bool(shell_startup_files.get("counts_for_provider_readiness")),
            "files": [
                {
                    "source": str(source.get("source", "")),
                    "path": str(source.get("path", "")),
                    key: str(source.get(key, "")),
                    "counts_for_provider_readiness": bool(source.get("counts_for_provider_readiness")),
                }
                for source in shell_files
                if isinstance(source, Mapping)
            ],
            "set_files": [
                {
                    "source": str(source.get("source", "")),
                    "path": str(source.get("path", "")),
                }
                for source in shell_set_files
                if isinstance(source, Mapping)
            ],
        },
        "sources": [
            {
                "source": str(source.get("source", "")),
                key: str(source.get(key, "")),
                "force_env": str(source.get("force_env", "")),
                "profile": str(source.get("profile", "")),
                "path": str(source.get("path", "")),
                "pid": str(source.get("pid", "")),
            }
            for source in sources
            if isinstance(source, Mapping)
        ],
        "set_sources": [
            {
                "source": str(source.get("source", "")),
                "profile": str(source.get("profile", "")),
                "path": str(source.get("path", "")),
                "pid": str(source.get("pid", "")),
            }
            for source in set_sources
            if isinstance(source, Mapping)
        ],
        "next_actions": [str(item) for item in next_actions],
        "missing": missing,
    }


def _audit_gate_f_handoff(root: str, path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "status": "missing_receipt",
        "execution_mode": "",
        "physical_iphone_used": None,
        "physical_device_launch_attempted": None,
        "remaining_to_start": [],
        "remaining_to_close": [],
        "endpoint": {},
        "next_actions": [],
        "missing": ["Gate F no-device handoff receipt"],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "status": "unreadable_receipt",
            "missing": [f"readable Gate F no-device handoff JSON: {error}"],
        }

    remaining_to_start = receipt.get("remaining_to_start", [])
    remaining_to_close = receipt.get("remaining_to_close", [])
    if not isinstance(remaining_to_start, list):
        remaining_to_start = ["remaining_to_start list"]
    if not isinstance(remaining_to_close, list):
        remaining_to_close = ["remaining_to_close list"]
    real_device_commands = receipt.get("real_device_commands_executed", [])
    if not isinstance(real_device_commands, list):
        real_device_commands = ["real_device_commands_executed list"]
    next_actions = receipt.get("next_actions", [])
    if not isinstance(next_actions, list):
        next_actions = ["next_actions list"]
    endpoint = receipt.get("endpoint", {})
    if not isinstance(endpoint, Mapping):
        endpoint = {}
    endpoint_missing = endpoint.get("missing", []) if endpoint else []
    if not isinstance(endpoint_missing, list):
        endpoint_missing = []

    missing: list[str] = []
    if receipt.get("phase") != "gate-f-handoff":
        missing.append("gate-f-handoff phase")
    if receipt.get("ok") is not True:
        missing.append("ok receipt flag")
    if receipt.get("execution_mode") != "local-mac-simulator-only":
        missing.append("local Mac Simulator execution mode")
    if receipt.get("safe_without_physical_iphone") is not True:
        missing.append("safe without physical iPhone flag")
    if receipt.get("physical_iphone_used") is not False:
        missing.append("physical iPhone not used")
    if receipt.get("physical_device_launch_attempted") is not False:
        missing.append("no physical device launch attempt")
    if real_device_commands:
        missing.append("no real-device commands executed")

    return {
        "path": path,
        "exists": True,
        "ok": not missing,
        "status": str(receipt.get("status", "failed")) if not missing else "failed",
        "execution_mode": str(receipt.get("execution_mode", "")),
        "physical_iphone_used": receipt.get("physical_iphone_used"),
        "physical_device_launch_attempted": receipt.get("physical_device_launch_attempted"),
        "remaining_to_start": [str(item) for item in remaining_to_start],
        "remaining_to_close": [str(item) for item in remaining_to_close],
        "endpoint": {
            "ok": bool(endpoint.get("ok")),
            "source": str(endpoint.get("source", "")),
            "host": str(endpoint.get("host", "")),
            "missing": [str(item) for item in endpoint_missing],
        } if endpoint else {},
        "next_actions": [str(item) for item in next_actions],
        "missing": missing,
    }


def _audit_physical_device_preflight(root: str, path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "status": "missing_receipt",
        "device": {},
        "ineligible": [],
        "target_build": {},
        "missing": [],
        "next_actions": [],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "status": "unreadable_receipt",
            "missing": [f"readable physical device preflight JSON: {error}"],
        }

    device = receipt.get("device", {})
    if not isinstance(device, Mapping):
        device = {}
    xcode_destination = receipt.get("xcode_destination", {})
    if not isinstance(xcode_destination, Mapping):
        xcode_destination = {}
    target_build = receipt.get("target_build", {})
    if not isinstance(target_build, Mapping):
        target_build = {}
    ineligible = xcode_destination.get("ineligible", [])
    if not isinstance(ineligible, list):
        ineligible = []
    missing = receipt.get("missing", [])
    if not isinstance(missing, list):
        missing = ["missing list"]
    next_actions = receipt.get("next_actions", [])
    if not isinstance(next_actions, list):
        next_actions = ["next_actions list"]

    return {
        "path": path,
        "exists": True,
        "ok": receipt.get("ok") is True,
        "status": str(receipt.get("status", "unknown")),
        "device": {
            "id": str(device.get("id", "")),
            "name": str(device.get("name", "")),
            "state": str(device.get("state", "")),
            "model": str(device.get("model", "")),
        },
        "ineligible": [str(item) for item in ineligible],
        "target_build": {
            "checked": bool(target_build.get("checked")),
            "ok": target_build.get("ok") is True,
            "target": str(target_build.get("target", "")),
            "configuration": str(target_build.get("configuration", "")),
            "sdk": str(target_build.get("sdk", "")),
            "command": str(target_build.get("command", "")),
            "error": str(target_build.get("error", "")),
        },
        "missing": [str(item) for item in missing],
        "next_actions": [str(item) for item in next_actions],
    }


def _audit_simulator_ui_test_preflight(root: str, path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "path": path,
        "exists": False,
        "ok": False,
        "status": "missing_receipt",
        "sdk_latest": "",
        "runtime_latest": "",
        "reason": "",
        "ineligible": [],
        "missing": ["simulator UI test preflight receipt"],
    }
    if not path:
        return base

    resolved = _resolve_audit_path(root, path)
    if not os.path.exists(resolved):
        return base

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return {
            **base,
            "exists": True,
            "status": "unreadable_receipt",
            "missing": [f"readable simulator UI test preflight JSON: {error}"],
        }

    sdk = receipt.get("sdk")
    runtime = receipt.get("runtime")
    destinations = receipt.get("destinations")
    mismatch = receipt.get("mismatch")
    sdk_latest = str(sdk.get("latest", "")) if isinstance(sdk, Mapping) else ""
    runtime_latest = str(runtime.get("latest", "")) if isinstance(runtime, Mapping) else ""
    destination_ok = bool(destinations.get("ok")) if isinstance(destinations, Mapping) else False
    ineligible = destinations.get("ineligible", []) if isinstance(destinations, Mapping) else []
    if not isinstance(ineligible, list):
        ineligible = []
    mismatch_ok = bool(mismatch.get("ok")) if isinstance(mismatch, Mapping) else False
    reason = str(mismatch.get("reason", "")) if isinstance(mismatch, Mapping) else ""
    ok = receipt.get("ok") is True

    if ok:
        status = "runnable"
        missing: list[str] = []
    elif not mismatch_ok:
        status = "blocked_by_local_xcode_runtime"
        missing = []
    elif not destination_ok:
        status = "blocked_by_xcode_destination"
        missing = []
    else:
        status = "not_runnable"
        missing = []

    return {
        "path": path,
        "exists": True,
        "ok": ok,
        "status": status,
        "sdk_latest": sdk_latest,
        "runtime_latest": runtime_latest,
        "reason": reason,
        "ineligible": ineligible,
        "missing": missing,
    }


def _simulator_suite_ui_step(preflight: Mapping[str, Any], receipt: str) -> dict[str, Any]:
    mismatch = preflight.get("mismatch")
    destinations = preflight.get("destinations")
    mismatch_ok = bool(mismatch.get("ok")) if isinstance(mismatch, Mapping) else False
    destination_ok = bool(destinations.get("ok")) if isinstance(destinations, Mapping) else False
    if preflight.get("ok"):
        status = "runnable"
    elif not mismatch_ok:
        status = "blocked_by_local_xcode_runtime"
    elif not destination_ok:
        status = "blocked_by_xcode_destination"
    else:
        status = "not_runnable"
    return {
        "ok": True,
        "required": False,
        "receipt": receipt,
        "runnable": bool(preflight.get("ok")),
        "status": status,
    }


def _simulator_suite_returncode_step(returncode: int, receipt: str, required: bool) -> dict[str, Any]:
    return {
        "ok": returncode == 0,
        "required": required,
        "returncode": returncode,
        "receipt": receipt,
    }


def _receipt_missing(receipt: Mapping[str, Any]) -> list[str]:
    missing = list(receipt.get("missing", []))
    if not receipt.get("ok") and not missing:
        missing.append(str(receipt.get("path", "receipt")))
    return missing


def _status_missing(status: Mapping[str, Any]) -> list[str]:
    missing = list(status.get("missing", []))
    if not status.get("ok") and not missing:
        missing.append(str(status.get("path", "status")))
    return missing


def _file_missing(file_evidence: Mapping[str, Any]) -> list[str]:
    if file_evidence.get("exists") and file_evidence.get("ok", True):
        return []
    missing = list(file_evidence.get("missing", []))
    return missing or [str(file_evidence.get("path", "file"))]


def _resolve_audit_path(root: str, path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(root, path)


def _tail_text(value: str, max_chars: int = 4000) -> str:
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


def _format_duration(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _first_line(value: str) -> str:
    return value.strip().splitlines()[0].strip() if value.strip() else ""


def _clean_error(result: CommandResult) -> str:
    return (result.stderr or result.stdout).strip()


def _write_simulator_library_fixture(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(_simulator_library_fixture_png())


def _simulator_library_fixture_png(width: int = 640, height: int = 480) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)

    rows = bytearray()
    max_x = max(width - 1, 1)
    max_y = max(height - 1, 1)
    for y in range(height):
        rows.append(0)
        for x in range(width):
            red = 32 + int(160 * x / max_x)
            green = 96 + int(112 * y / max_y)
            blue = 220 - int(96 * x / max_x)
            diagonal = abs((x / max_x) - (y / max_y)) < 0.015
            if diagonal:
                red, green, blue = 255, 255, 255
            rows.extend((red, green, blue))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + chunk(b"IEND", b"")
    )


def _first_connected_device_id(output: str) -> str:
    uuid_pattern = re.compile(r"\b[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}\b")
    usable_states = ("connected", "available", "paired")
    for line in output.splitlines():
        lowered = line.lower()
        if not any(state in lowered for state in usable_states):
            continue
        match = uuid_pattern.search(line)
        if match:
            return match.group(0)
    return ""


def _simulator_devices(output: str) -> list[dict[str, str]]:
    devices: list[dict[str, str]] = []
    pattern = re.compile(
        r"^\s*(?P<name>.+?)\s+\((?P<id>[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12})\)\s+\((?P<state>[^)]+)\)"
    )
    for line in output.splitlines():
        match = pattern.match(line)
        if match:
            devices.append(
                {
                    "id": match.group("id"),
                    "name": match.group("name").strip(),
                    "state": match.group("state").strip(),
                }
            )
    return devices


def _ios_simulator_sdk_versions(output: str) -> list[str]:
    versions: list[str] = []
    pattern = re.compile(r"Simulator - iOS\s+([0-9]+(?:\.[0-9]+)*)\s+-sdk\s+iphonesimulator")
    for line in output.splitlines():
        match = pattern.search(line)
        if match:
            versions.append(match.group(1))
    return sorted(set(versions), key=_version_key)


def _ios_runtime_versions(output: str) -> list[str]:
    versions: list[str] = []
    pattern = re.compile(r"^iOS\s+([0-9]+(?:\.[0-9]+)*)\s+\(")
    for line in output.splitlines():
        match = pattern.search(line.strip())
        if match:
            versions.append(match.group(1))
    return sorted(set(versions), key=_version_key)


def _latest_version(versions: Sequence[str]) -> str:
    return sorted(versions, key=_version_key)[-1] if versions else ""


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def _ios_simulator_destinations(output: str) -> list[dict[str, str]]:
    destinations: list[dict[str, str]] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{") or "platform:iOS Simulator" not in stripped or "error:" in stripped:
            continue
        destinations.append({
            "raw": stripped,
            "id": _destination_field(stripped, "id"),
            "name": _destination_field(stripped, "name"),
            "os": _destination_field(stripped, "OS"),
        })
    return destinations


def _ios_physical_destinations(output: str) -> list[dict[str, str]]:
    destinations: list[dict[str, str]] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{") or "platform:iOS," not in stripped or "error:" in stripped:
            continue
        destinations.append({
            "raw": stripped,
            "id": _destination_field(stripped, "id"),
            "name": _destination_field(stripped, "name"),
            "os": _destination_field(stripped, "OS"),
        })
    return destinations


def _ineligible_destinations(output: str) -> list[str]:
    return [
        line.strip()
        for line in output.splitlines()
        if line.strip().startswith("{") and "error:" in line
    ]


def _destination_field(destination: str, name: str) -> str:
    match = re.search(rf"{re.escape(name)}:([^,}}]+)", destination)
    return match.group(1).strip() if match else ""


def _preferred_xcode_destination_note(ineligible: Sequence[Any]) -> str:
    notes = [str(item) for item in ineligible]
    for note in notes:
        if "Any iOS Device" in note or "DVTiPhonePlaceholder" in note or "iOS Simulator" in note:
            return note
    return notes[0] if notes else ""


def _physical_device_summary(output: str, device_id: str) -> dict[str, str]:
    if not device_id:
        return {}
    for line in output.splitlines():
        if device_id not in line:
            continue
        columns = re.split(r"\s{2,}", line.strip())
        return {
            "name": columns[0] if len(columns) > 0 else "",
            "hostname": columns[1] if len(columns) > 1 else "",
            "id": columns[2] if len(columns) > 2 else device_id,
            "state": columns[3] if len(columns) > 3 else "",
            "model": columns[4] if len(columns) > 4 else "",
            "raw": line.strip(),
        }
    return {"id": device_id}


def _run_command(command: list[str], timeout_seconds: float = 10) -> CommandResult:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds)
        return CommandResult(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
    except (OSError, subprocess.TimeoutExpired) as error:
        return CommandResult(returncode=1, stdout="", stderr=str(error))


def _restore_env(previous_env: Mapping[str, Optional[str]]) -> None:
    for key, value in previous_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _launch_ios_app(device_id: str, bundle_id: str) -> None:
    subprocess.run(
        [
            "xcrun",
            "devicectl",
            "device",
            "process",
            "launch",
            "--device",
            device_id,
            "--terminate-existing",
            bundle_id,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _launch_simulator_smoke(bundle_id: str, base_url: str, token: str) -> None:
    subprocess.run(
        [
            "xcrun",
            "simctl",
            "launch",
            "--terminate-running-process",
            "booted",
            bundle_id,
            "--agent-pocket-simulator-smoke",
            "--agent-pocket-smoke-base-url",
            base_url,
            "--agent-pocket-smoke-token",
            token,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _launch_simulator_discovery_refresh_smoke(bundle_id: str, base_url: str) -> None:
    subprocess.run(
        [
            "xcrun",
            "simctl",
            "launch",
            "--terminate-running-process",
            "booted",
            bundle_id,
            "--agent-pocket-simulator-discovery-refresh-smoke",
            "--agent-pocket-smoke-base-url",
            base_url,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _read_simulator_app_receipt(bundle_id: str, filename: str, label: str) -> Mapping[str, Any]:
    result = _run_command(["xcrun", "simctl", "get_app_container", "booted", bundle_id, "data"])
    if result.returncode != 0:
        raise RuntimeError(_clean_error(result))
    container_path = result.stdout.strip()
    if not container_path:
        raise RuntimeError("Simulator app data container was not reported.")
    receipt_path = os.path.join(container_path, "Documents", filename)
    with open(receipt_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise RuntimeError(f"Simulator {label} receipt is not a JSON object.")
    return payload


def _remove_simulator_app_receipt(bundle_id: str, filename: str) -> None:
    result = _run_command(["xcrun", "simctl", "get_app_container", "booted", bundle_id, "data"])
    if result.returncode != 0:
        return
    container_path = result.stdout.strip()
    if not container_path:
        return
    receipt_path = os.path.join(container_path, "Documents", filename)
    try:
        os.remove(receipt_path)
    except FileNotFoundError:
        pass


def _read_simulator_capture_ready_receipt(bundle_id: str) -> Mapping[str, Any]:
    return _read_simulator_app_receipt(
        bundle_id,
        "agent-pocket-capture-ready-smoke.json",
        "capture-ready",
    )


def _remove_simulator_capture_ready_receipt(bundle_id: str) -> None:
    _remove_simulator_app_receipt(bundle_id, "agent-pocket-capture-ready-smoke.json")


def _read_simulator_capture_completed_receipt(bundle_id: str) -> Mapping[str, Any]:
    return _read_simulator_app_receipt(
        bundle_id,
        "agent-pocket-capture-completed-smoke.json",
        "capture-completed",
    )


def _remove_simulator_capture_completed_receipt(bundle_id: str) -> None:
    _remove_simulator_app_receipt(bundle_id, "agent-pocket-capture-completed-smoke.json")


def _read_simulator_result_gallery_receipt(bundle_id: str) -> Mapping[str, Any]:
    return _read_simulator_app_receipt(
        bundle_id,
        "agent-pocket-result-gallery-smoke.json",
        "result-gallery",
    )


def _remove_simulator_result_gallery_receipt(bundle_id: str) -> None:
    _remove_simulator_app_receipt(bundle_id, "agent-pocket-result-gallery-smoke.json")


def _read_simulator_result_gallery_downloaded_receipt(bundle_id: str) -> Mapping[str, Any]:
    return _read_simulator_app_receipt(
        bundle_id,
        "agent-pocket-result-gallery-downloaded-smoke.json",
        "result-gallery-downloaded",
    )


def _remove_simulator_result_gallery_downloaded_receipt(bundle_id: str) -> None:
    _remove_simulator_app_receipt(bundle_id, "agent-pocket-result-gallery-downloaded-smoke.json")


def _read_simulator_share_sheet_receipt(bundle_id: str) -> Mapping[str, Any]:
    return _read_simulator_app_receipt(
        bundle_id,
        "agent-pocket-share-sheet-smoke.json",
        "share-sheet",
    )


def _remove_simulator_share_sheet_receipt(bundle_id: str) -> None:
    _remove_simulator_app_receipt(bundle_id, "agent-pocket-share-sheet-smoke.json")


def _launch_simulator_capture_ready_smoke(bundle_id: str) -> None:
    subprocess.run(
        [
            "xcrun",
            "simctl",
            "launch",
            "--terminate-running-process",
            "booted",
            bundle_id,
            "--agent-pocket-simulator-capture-ready-smoke",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _launch_simulator_capture_completed_smoke(bundle_id: str) -> None:
    subprocess.run(
        [
            "xcrun",
            "simctl",
            "launch",
            "--terminate-running-process",
            "booted",
            bundle_id,
            "--agent-pocket-simulator-capture-completed-smoke",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _launch_simulator_result_gallery_smoke(bundle_id: str) -> None:
    subprocess.run(
        [
            "xcrun",
            "simctl",
            "launch",
            "--terminate-running-process",
            "booted",
            bundle_id,
            "--agent-pocket-simulator-result-gallery-smoke",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _launch_simulator_result_gallery_downloaded_smoke(bundle_id: str) -> None:
    subprocess.run(
        [
            "xcrun",
            "simctl",
            "launch",
            "--terminate-running-process",
            "booted",
            bundle_id,
            "--agent-pocket-simulator-result-gallery-downloaded-smoke",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _launch_simulator_share_sheet_smoke(bundle_id: str) -> None:
    subprocess.run(
        [
            "xcrun",
            "simctl",
            "launch",
            "--terminate-running-process",
            "booted",
            bundle_id,
            "--agent-pocket-simulator-share-sheet-smoke",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _launch_simulator_picker_ui_smoke(bundle_id: str) -> None:
    subprocess.run(
        [
            "xcrun",
            "simctl",
            "launch",
            "--terminate-running-process",
            "booted",
            bundle_id,
            "--agent-pocket-simulator-picker-ui-smoke",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _launch_simulator_app(bundle_id: str) -> None:
    subprocess.run(
        [
            "xcrun",
            "simctl",
            "launch",
            "--terminate-running-process",
            "booted",
            bundle_id,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _take_simulator_screenshot(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    subprocess.run(
        [
            "xcrun",
            "simctl",
            "io",
            "booted",
            "screenshot",
            path,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    if not os.path.exists(path):
        raise RuntimeError(f"Simulator screenshot was not written: {path}")
    if not _simulator_screenshot_has_visible_content(path):
        raise RuntimeError(f"Simulator screenshot has a blank content area: {path}")


def _take_simulator_screenshot_until_visible(
    path: str,
    *,
    screenshotter: Callable[[str], None],
    attempts: int,
    interval_seconds: float,
    sleeper: Callable[[float], None],
) -> None:
    last_error: Optional[BaseException] = None
    max_attempts = max(1, attempts)
    for attempt in range(max_attempts):
        try:
            screenshotter(path)
            return
        except Exception as error:
            last_error = error
            if attempt == max_attempts - 1:
                break
            if interval_seconds > 0:
                sleeper(interval_seconds)

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Simulator screenshot was not written: {path}")


def _simulator_screenshot_has_visible_content(path: str) -> bool:
    try:
        width, height, rows, color_type = _read_png_rows(path)
    except (OSError, ValueError, zlib.error):
        return False

    if width <= 0 or height <= 0:
        return False

    y_start = min(height, max(0, int(height * 0.16)))
    y_end = min(height, max(y_start + 1, int(height * 0.92)))
    total = 0
    visible = 0
    for y in range(y_start, y_end):
        row = rows[y]
        for x in range(width):
            red, green, blue = _png_rgb_at(row, x, color_type)
            total += 1
            if red < 245 or green < 245 or blue < 245:
                visible += 1

    return total > 0 and (visible / total) >= 0.002


def _read_png_rows(path: str) -> tuple[int, int, list[bytes], int]:
    with open(path, "rb") as handle:
        data = handle.read()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG")

    width = 0
    height = 0
    bit_depth = 0
    color_type = 0
    idat = bytearray()
    offset = 8
    while offset + 8 <= len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        chunk_data = data[offset + 8:offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk_data)
        elif kind == b"IDAT":
            idat.extend(chunk_data)
        elif kind == b"IEND":
            break

    if bit_depth != 8 or color_type not in (0, 2, 6):
        raise ValueError("unsupported PNG color format")
    if width <= 0 or height <= 0 or not idat:
        raise ValueError("invalid PNG")

    channels = {0: 1, 2: 3, 6: 4}[color_type]
    row_length = width * channels
    inflated = zlib.decompress(bytes(idat))
    rows: list[bytes] = []
    previous = bytearray(row_length)
    cursor = 0
    for _ in range(height):
        if cursor >= len(inflated):
            raise ValueError("truncated PNG data")
        filter_type = inflated[cursor]
        cursor += 1
        raw = bytearray(inflated[cursor:cursor + row_length])
        cursor += row_length
        if len(raw) != row_length:
            raise ValueError("truncated PNG row")
        reconstructed = _unfilter_png_row(raw, previous, channels, filter_type)
        rows.append(bytes(reconstructed))
        previous = reconstructed
    return width, height, rows, color_type


def _unfilter_png_row(raw: bytearray, previous: bytearray, channels: int, filter_type: int) -> bytearray:
    row = bytearray(len(raw))
    for index, value in enumerate(raw):
        left = row[index - channels] if index >= channels else 0
        up = previous[index]
        up_left = previous[index - channels] if index >= channels else 0
        if filter_type == 0:
            predictor = 0
        elif filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = up
        elif filter_type == 3:
            predictor = (left + up) // 2
        elif filter_type == 4:
            predictor = _png_paeth(left, up, up_left)
        else:
            raise ValueError("unsupported PNG filter")
        row[index] = (value + predictor) & 0xFF
    return row


def _png_paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    up_left_distance = abs(estimate - up_left)
    if left_distance <= up_distance and left_distance <= up_left_distance:
        return left
    if up_distance <= up_left_distance:
        return up
    return up_left


def _png_rgb_at(row: bytes, x: int, color_type: int) -> tuple[int, int, int]:
    if color_type == 0:
        value = row[x]
        return value, value, value
    if color_type == 2:
        index = x * 3
        return row[index], row[index + 1], row[index + 2]
    index = x * 4
    return row[index], row[index + 1], row[index + 2]


if __name__ == "__main__":
    raise SystemExit(main())
