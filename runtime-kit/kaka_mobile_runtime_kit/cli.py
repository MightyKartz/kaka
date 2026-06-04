from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


DEFAULT_PORT = 8765
DEFAULT_PHOTO_PROVIDER = "recipe_local"
DEFAULT_BONJOUR_NAME = "Kaka Mobile Bridge"
PROVIDER_CHOICES = ("fixture", "script", "recipe_local", "openai")
VISION_PROVIDER_CHOICES = ("fixture", "runtime_http")


@dataclass(frozen=True)
class BridgeConfig:
    repo_root: Path = Path(".")
    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    lan: bool = False
    bonjour: bool = False
    bonjour_host: str = ""
    bonjour_name: str = DEFAULT_BONJOUR_NAME
    pairing_code: str = "pair_dev"
    runtime: str = "hermes"
    photo_provider: str = DEFAULT_PHOTO_PROVIDER
    photo_pack_root: str = "photo-pack"
    vision_provider: str = "fixture"
    vision_endpoint: str = ""
    hermes_home: str = ""
    hermes_profile: str = ""
    env_file: str = ""

    @property
    def bind_host(self) -> str:
        return "0.0.0.0" if self.lan else self.host

    @property
    def advertised_host(self) -> str:
        if self.bonjour_host:
            return self.bonjour_host
        if self.lan:
            return "<mac-lan-ip>"
        return self.host


def build_server_command(config: BridgeConfig) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "agent_pocket_mock_bridge.server",
        "--host",
        config.bind_host,
        "--port",
        str(config.port),
        "--runtime",
        config.runtime,
        "--photo-provider",
        config.photo_provider,
        "--photo-pack-root",
        config.photo_pack_root,
        "--vision-provider",
        config.vision_provider,
    ]
    if config.vision_endpoint:
        command.extend(["--vision-endpoint", config.vision_endpoint])
    if config.bonjour:
        command.append("--bonjour")
        command.extend(["--bonjour-name", config.bonjour_name])
        command.extend(["--pairing-code", config.pairing_code])
        if config.bonjour_host:
            command.extend(["--bonjour-host", config.bonjour_host])
    if config.hermes_home:
        command.extend(["--hermes-home", config.hermes_home])
    if config.hermes_profile:
        command.extend(["--hermes-profile", config.hermes_profile])
    if config.env_file:
        command.extend(["--env-file", config.env_file])
    return command


def build_bridge_environment(
    repo_root: Path,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(os.environ if base_env is None else base_env)
    mock_bridge_path = str((repo_root / "mock_bridge").resolve())
    existing = env.get("PYTHONPATH", "")
    parts = [mock_bridge_path]
    if existing:
        parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def pairing_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/mobile/v1/pairing/dev.html"


def validate_start_config(config: BridgeConfig) -> list[str]:
    errors: list[str] = []
    if config.photo_provider not in PROVIDER_CHOICES:
        errors.append(f"Unsupported photo provider: {config.photo_provider}")
    if config.vision_provider not in VISION_PROVIDER_CHOICES:
        errors.append(f"Unsupported vision provider: {config.vision_provider}")
    if config.vision_provider == "runtime_http" and not config.vision_endpoint:
        errors.append("--vision-endpoint is required when --vision-provider runtime_http.")
    if config.bonjour and not config.lan and not config.bonjour_host:
        errors.append("Bonjour discovery for iPhone requires --lan or --bonjour-host.")
    if config.lan and config.host not in ("127.0.0.1", "localhost"):
        errors.append("Use --lan by itself instead of combining it with a custom --host.")
    return errors


def doctor_report(repo_root: Path, photo_pack_root: str = "photo-pack") -> Mapping[str, object]:
    root = repo_root.resolve()
    mock_bridge_dir = root / "mock_bridge"
    photo_pack_dir = root / photo_pack_root
    adapter_path = photo_pack_dir / "adapters" / "recipe_local.py"
    checks: dict[str, Mapping[str, object]] = {
        "python": {
            "ok": True,
            "detail": sys.executable,
        },
        "mock_bridge_directory": {
            "ok": mock_bridge_dir.exists(),
            "detail": str(mock_bridge_dir),
        },
        "photo_pack_directory": {
            "ok": photo_pack_dir.exists(),
            "detail": str(photo_pack_dir),
        },
        "recipe_local_adapter": {
            "ok": adapter_path.exists(),
            "detail": str(adapter_path),
        },
        "dns_sd": {
            "ok": bool(shutil.which("dns-sd")),
            "detail": shutil.which("dns-sd") or "missing; Bonjour discovery will not work until dns-sd is available",
            "required_for": "bonjour",
        },
    }

    import_ok, import_detail = _can_import_mock_bridge(mock_bridge_dir)
    checks["mock_bridge_import"] = {
        "ok": import_ok,
        "detail": import_detail,
    }
    required = ("python", "mock_bridge_directory", "photo_pack_directory", "recipe_local_adapter", "mock_bridge_import")
    ok = all(bool(checks[name]["ok"]) for name in required)
    return {
        "ok": ok,
        "scope": "local Kaka Mobile Bridge launcher",
        "secrets": "not inspected or printed",
        "checks": checks,
    }


def run_doctor(args: argparse.Namespace) -> int:
    report = doctor_report(Path(args.repo_root), photo_pack_root=args.photo_pack_root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


def run_pairing_url(args: argparse.Namespace) -> int:
    print(pairing_url(args.host, args.port))
    return 0


def run_start(args: argparse.Namespace) -> int:
    config = BridgeConfig(
        repo_root=Path(args.repo_root),
        host=args.host,
        port=args.port,
        lan=args.lan,
        bonjour=args.bonjour,
        bonjour_host=args.bonjour_host,
        bonjour_name=args.bonjour_name,
        pairing_code=args.pairing_code,
        runtime=args.runtime,
        photo_provider=args.photo_provider,
        photo_pack_root=args.photo_pack_root,
        vision_provider=args.vision_provider,
        vision_endpoint=args.vision_endpoint,
        hermes_home=args.hermes_home,
        hermes_profile=args.hermes_profile,
        env_file=args.env_file,
    )
    errors = validate_start_config(config)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2

    repo_root = config.repo_root.resolve()
    command = build_server_command(config)
    summary = {
        "bridge": "Kaka Mobile Bridge",
        "runtime": config.runtime,
        "bind_url": f"http://{config.bind_host}:{config.port}",
        "lan_exposed": config.lan,
        "bonjour": config.bonjour,
        "pairing_page": pairing_url(config.advertised_host, config.port),
        "photo_provider": config.photo_provider,
        "vision_provider": config.vision_provider,
        "command": command,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if args.dry_run:
        return 0
    env = build_bridge_environment(repo_root)
    return subprocess.call(command, cwd=repo_root, env=env)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kaka-mobile-runtime-kit",
        description="Explicit local launcher for Kaka Mobile Bridge development and runtime adapters.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local runtime-kit prerequisites without printing secrets.")
    doctor.add_argument("--repo-root", default=".", help="Kaka repository root.")
    doctor.add_argument("--photo-pack-root", default="photo-pack", help="Photo Pack root relative to repo root.")
    doctor.set_defaults(func=run_doctor)

    start = subparsers.add_parser("start", help="Explicitly start the local Mobile Bridge.")
    start.add_argument("--repo-root", default=".", help="Kaka repository root.")
    start.add_argument("--host", default="127.0.0.1", help="Loopback bind host for local development.")
    start.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bridge port.")
    start.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 so an iPhone on the same LAN can connect.")
    start.add_argument("--bonjour", action="store_true", help="Advertise through Bonjour after explicit start.")
    start.add_argument("--bonjour-host", default="", help="LAN IP or hostname published in Bonjour TXT records.")
    start.add_argument("--bonjour-name", default=DEFAULT_BONJOUR_NAME, help="Bonjour display name.")
    start.add_argument("--pairing-code", default="pair_dev", help="Development pairing code.")
    start.add_argument("--runtime", default="hermes", help="Runtime id, for example hermes, openclaw, or sidecar.")
    start.add_argument("--photo-provider", default=DEFAULT_PHOTO_PROVIDER, choices=PROVIDER_CHOICES)
    start.add_argument("--photo-pack-root", default="photo-pack")
    start.add_argument("--vision-provider", default="fixture", choices=VISION_PROVIDER_CHOICES)
    start.add_argument("--vision-endpoint", default="")
    start.add_argument("--hermes-home", default="")
    start.add_argument("--hermes-profile", default="")
    start.add_argument("--env-file", default="")
    start.add_argument("--dry-run", action="store_true", help="Print the exact server command but do not start it.")
    start.set_defaults(func=run_start)

    url = subparsers.add_parser("pairing-url", help="Print the development pairing page URL.")
    url.add_argument("--host", default="127.0.0.1")
    url.add_argument("--port", default=DEFAULT_PORT, type=int)
    url.set_defaults(func=run_pairing_url)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


def _can_import_mock_bridge(mock_bridge_dir: Path) -> tuple[bool, str]:
    if not mock_bridge_dir.exists():
        return False, "mock_bridge directory missing"
    path = str(mock_bridge_dir.resolve())
    inserted = False
    if path not in sys.path:
        sys.path.insert(0, path)
        inserted = True
    try:
        importlib.import_module("agent_pocket_mock_bridge.server")
        return True, "agent_pocket_mock_bridge.server importable"
    except Exception as error:  # pragma: no cover - detail belongs in doctor output
        return False, f"{type(error).__name__}: {error}"
    finally:
        if inserted:
            try:
                sys.path.remove(path)
            except ValueError:
                pass
