from __future__ import annotations

import argparse
import io
import json
import os
import socket
import subprocess
import ssl
import sys
from contextlib import contextmanager
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol
from urllib.parse import urlsplit

from agent_pocket_mock_bridge.app import (
    DEFAULT_INPUT_ASSETS_DAYS,
    DEFAULT_OUTPUT_ASSETS_DAYS,
    DEFAULT_TASK_HISTORY_DAYS,
    MockBridgeApp,
    MockResponse,
    build_recall_search_provider,
    build_vision_provider,
    create_app,
)
from agent_pocket_mock_bridge.photo_providers import build_photo_provider
from kaka_mobile_runtime_kit.pairing import (
    InMemoryPairingStore,
    PairingManager,
    PairingSecurityConfig,
)

HERMES_PROVIDER_ENV_FORCE_PREFIX = "_HERMES_FORCE_"
OPENAI_PROVIDER_ENV_KEYS = ("OPENAI_API_KEY", "OPENAI_BASE_URL")


class MockBridgeHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, app: MockBridgeApp):
        super().__init__(server_address, RequestHandlerClass)
        self.app = app


class BonjourProcess(Protocol):
    def terminate(self) -> None:
        ...

    def wait(self, timeout: Optional[float] = None) -> Any:
        ...


class BonjourAdvertisement:
    service_type = "_agent-pocket._tcp"

    def __init__(
        self,
        name: str,
        host: str,
        port: int,
        pairing_code: str,
        runtime: str = "hermes",
        scheme: str = "http",
        pairing_page: str = "",
        expires_at: str = "2099-01-01T00:00:00Z",
        trusted_local_tls_required: bool = False,
        tls_certificate_label: str = "",
        tls_public_key_sha256: str = "",
        launcher: Optional[Callable[[List[str]], BonjourProcess]] = None,
    ) -> None:
        self.name = name
        self.host = host
        self.port = port
        self.pairing_code = pairing_code
        self.runtime = runtime
        self.scheme = scheme
        self.pairing_page = pairing_page
        self.expires_at = expires_at
        self.trusted_local_tls_required = bool(trusted_local_tls_required)
        self.tls_certificate_label = tls_certificate_label.strip()
        self.tls_public_key_sha256 = tls_public_key_sha256.strip().lower()
        self.launcher = launcher or _launch_dns_sd
        self.process: Optional[BonjourProcess] = None

    def start(self) -> None:
        if self.process is not None:
            return
        self.process = self.launcher(self.command())

    def stop(self) -> None:
        if self.process is None:
            return
        process = self.process
        self.process = None
        process.terminate()
        process.wait(timeout=2)

    def command(self) -> List[str]:
        command = [
            "dns-sd",
            "-R",
            self.name,
            self.service_type,
            "local",
            str(self.port),
            f"display_name={self.name}",
            f"runtime={self.runtime}",
            f"scheme={self.scheme}",
            f"endpoint={self.scheme}://{self.host}:{self.port}",
        ]
        if self.pairing_code:
            command.append(f"pairing_code={self.pairing_code}")
        if self.expires_at:
            command.append(f"expires_at={self.expires_at}")
        if self.pairing_page:
            command.append(f"pairing_page={self.pairing_page}")
        if self.trusted_local_tls_required:
            command.append("trusted_local_tls_required=true")
        if self.tls_certificate_label:
            command.append(f"tls_certificate_label={self.tls_certificate_label}")
        if self.tls_public_key_sha256:
            command.append(f"tls_public_key_sha256={self.tls_public_key_sha256}")
        return command


class MockBridgeRequestHandler(BaseHTTPRequestHandler):
    server: MockBridgeHTTPServer

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_DELETE(self) -> None:
        self._handle("DELETE")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle(self, method: str) -> None:
        content_type = self.headers.get("Content-Type", "")
        body = self._read_body()
        json_body: Optional[Mapping[str, Any]] = None
        form_data: Optional[Mapping[str, Any]] = None

        if method in {"POST", "DELETE"} and body:
            if content_type.startswith("application/json"):
                json_body = json.loads(body.decode("utf-8"))
            elif content_type.startswith("multipart/form-data"):
                form_data = _parse_multipart_form(content_type, body)

        response = self.server.app.handle(
            method,
            self.path,
            headers=dict(self.headers),
            json_body=json_body,
            form_data=form_data,
        )
        self._send_response(response)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def _send_response(self, response: MockResponse) -> None:
        self.send_response(response.status_code)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.data)))
        self.end_headers()
        self.wfile.write(response.data)


def create_http_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    app: Optional[MockBridgeApp] = None,
    tls_certificate_chain_path: str = "",
    tls_private_key_path: str = "",
) -> MockBridgeHTTPServer:
    server = MockBridgeHTTPServer((host, port), MockBridgeRequestHandler, app or create_app())
    certificate_chain_path = tls_certificate_chain_path.strip()
    private_key_path = tls_private_key_path.strip()
    if certificate_chain_path or private_key_path:
        if not certificate_chain_path or not private_key_path:
            raise ValueError("Both TLS certificate chain path and private key path are required.")
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=certificate_chain_path, keyfile=private_key_path)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def build_app_for_provider(
    photo_provider: str = "fixture",
    photo_pack_root: str = "photo-pack",
    vision_provider: str = "fixture",
    vision_endpoint: str = "",
    runtime_id: str = "hermes",
    runtime_display_name: str = "Agent Pocket Mock Hermes",
    pairing_scheme: str = "http",
    recall_search_provider: str = "local",
    recall_search_endpoint: str = "",
    runtime_store: Optional[Any] = None,
    runtime_store_path: str = "",
    pairing_manager: Optional[PairingManager] = None,
    trusted_local_tls_required: bool = False,
    tls_certificate_label: str = "",
    tls_public_key_sha256: str = "",
    input_assets_days: int = DEFAULT_INPUT_ASSETS_DAYS,
    output_assets_days: int = DEFAULT_OUTPUT_ASSETS_DAYS,
    task_history_days: int = DEFAULT_TASK_HISTORY_DAYS,
) -> MockBridgeApp:
    return create_app(
        photo_provider=build_photo_provider(photo_provider, photo_pack_root=photo_pack_root),
        vision_provider=build_vision_provider(vision_provider, endpoint=vision_endpoint),
        runtime_id=runtime_id,
        runtime_display_name=runtime_display_name,
        pairing_scheme=pairing_scheme,
        recall_search_provider=recall_search_provider,
        recall_search_endpoint=recall_search_endpoint,
        runtime_store=runtime_store,
        runtime_store_path=runtime_store_path,
        pairing_manager=pairing_manager,
        trusted_local_tls_required=trusted_local_tls_required,
        tls_certificate_label=tls_certificate_label,
        tls_public_key_sha256=tls_public_key_sha256,
        input_assets_days=input_assets_days,
        output_assets_days=output_assets_days,
        task_history_days=task_history_days,
    )


def _default_hermes_home() -> str:
    return os.path.join(os.path.expanduser("~"), ".hermes")


def _hermes_profile_env_file(hermes_home: str = "", hermes_profile: str = "") -> str:
    profile = hermes_profile.strip()
    if not profile:
        return ""
    home = os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home()))
    return os.path.join(home, "profiles", profile, ".env")


def _hermes_home_env_file(hermes_home: str = "", hermes_profile: str = "") -> str:
    if not hermes_home.strip() and not hermes_profile.strip():
        return ""
    home = os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home()))
    return os.path.join(home, ".env")


def _hermes_auth_file(hermes_home: str = "", hermes_profile: str = "") -> str:
    if not hermes_home.strip() and not hermes_profile.strip():
        return ""
    profile = hermes_profile.strip()
    home = os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home()))
    if not profile:
        return os.path.join(home, "auth.json")
    return os.path.join(home, "profiles", profile, "auth.json")


def _hermes_shared_auth_file(hermes_home: str = "", hermes_profile: str = "") -> str:
    if not hermes_home.strip() and not hermes_profile.strip():
        return ""
    home = os.path.abspath(os.path.expanduser(hermes_home or _default_hermes_home()))
    return os.path.join(home, "shared-auth", "auth.json")


def _hermes_openai_auth_env(auth_file: str) -> Dict[str, str]:
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


def _provider_env_overlay(
    env_file: str = "",
    hermes_home: str = "",
    hermes_profile: str = "",
) -> Dict[str, str]:
    values = _provider_visible_env(_parse_env_file(env_file))
    hermes_home_env_file = _hermes_home_env_file(
        hermes_home=hermes_home,
        hermes_profile=hermes_profile,
    )
    if hermes_home_env_file and os.path.exists(hermes_home_env_file):
        values.update(_provider_visible_env(_parse_env_file(hermes_home_env_file)))
    hermes_env_file = _hermes_profile_env_file(
        hermes_home=hermes_home,
        hermes_profile=hermes_profile,
    )
    if hermes_env_file and os.path.exists(hermes_env_file):
        values.update(_provider_visible_env(_parse_env_file(hermes_env_file)))
    auth_files = [
        _hermes_auth_file(hermes_home=hermes_home, hermes_profile=hermes_profile),
        _hermes_shared_auth_file(hermes_home=hermes_home, hermes_profile=hermes_profile),
    ]
    for auth_file in auth_files:
        auth_env = _hermes_openai_auth_env(auth_file)
        if auth_env.get("OPENAI_API_KEY") and not values.get("OPENAI_API_KEY"):
            values["OPENAI_API_KEY"] = auth_env["OPENAI_API_KEY"]
        if auth_env.get("OPENAI_BASE_URL") and not values.get("OPENAI_BASE_URL"):
            values["OPENAI_BASE_URL"] = auth_env["OPENAI_BASE_URL"]
    forced_env = _provider_visible_env(os.environ)
    for key in OPENAI_PROVIDER_ENV_KEYS:
        if forced_env.get(key) and not values.get(key):
            values[key] = forced_env[key]
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Agent Pocket mock Mobile Bridge HTTP server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Use 0.0.0.0 for device LAN testing.")
    parser.add_argument("--port", default=8765, type=int, help="Bind port.")
    parser.add_argument("--bonjour", action="store_true", help="Advertise the mock bridge through Bonjour.")
    parser.add_argument("--bonjour-name", default="Agent Pocket Mock Hermes", help="Bonjour service display name.")
    parser.add_argument("--bonjour-host", default=None, help="Host or LAN IP to publish in the Bonjour endpoint TXT record.")
    parser.add_argument("--pairing-code", default="pair_dev", help="Development pairing code to publish through Bonjour.")
    parser.add_argument("--pairing-mode", default="development", choices=["development", "production"])
    parser.add_argument("--pairing-code-ttl-seconds", default=120, type=int)
    parser.add_argument("--token-ttl-seconds", default=0, type=int)
    parser.add_argument("--trusted-local-tls", action="store_true")
    parser.add_argument("--tls-trust-state", default="not_configured")
    parser.add_argument("--tls-certificate-label", default="")
    parser.add_argument("--tls-public-key-sha256", default="")
    parser.add_argument("--tls-certificate-chain-path", default="")
    parser.add_argument("--tls-private-key-path", default="")
    parser.add_argument("--runtime", default="hermes", help="Runtime identifier published through Bonjour.")
    parser.add_argument(
        "--photo-provider",
        default="fixture",
        choices=["fixture", "script", "recipe_local", "openai"],
        help="Photo provider used by /mobile/v1/tasks/photo-edit.",
    )
    parser.add_argument(
        "--photo-pack-root",
        default="photo-pack",
        help="Path to the Photo Pack root containing provider adapters.",
    )
    parser.add_argument(
        "--vision-provider",
        default="fixture",
        choices=["fixture", "runtime_http"],
        help="Vision provider used by /mobile/v1/tasks/vision.",
    )
    parser.add_argument(
        "--vision-endpoint",
        default="",
        help="Runtime-local HTTP endpoint for --vision-provider runtime_http.",
    )
    parser.add_argument(
        "--recall-search-provider",
        default="local",
        choices=["local", "fixture", "runtime_http"],
        help="Recall search provider used by /mobile/v1/recall/search.",
    )
    parser.add_argument(
        "--recall-search-endpoint",
        default="",
        help="Runtime-local HTTP endpoint for --recall-search-provider runtime_http.",
    )
    parser.add_argument(
        "--env-file",
        default="",
        help="Optional server-side env file to load before creating the photo provider; secret values are never printed.",
    )
    parser.add_argument(
        "--hermes-home",
        default="",
        help="Optional Hermes home containing a root .env and profiles. Defaults to ~/.hermes when --hermes-profile is set.",
    )
    parser.add_argument(
        "--hermes-profile",
        default="",
        help="Optional Hermes profile whose .env can provide server-side OPENAI_API_KEY.",
    )
    parser.add_argument(
        "--runtime-store-path",
        default="",
        help="Optional SQLite path for runtime-owned Recall and task persistence.",
    )
    parser.add_argument("--input-assets-days", default=DEFAULT_INPUT_ASSETS_DAYS, type=int)
    parser.add_argument("--output-assets-days", default=DEFAULT_OUTPUT_ASSETS_DAYS, type=int)
    parser.add_argument("--task-history-days", default=DEFAULT_TASK_HISTORY_DAYS, type=int)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_server_config(args)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    with _temporary_environ(_provider_env_overlay(
        env_file=args.env_file,
        hermes_home=args.hermes_home,
        hermes_profile=args.hermes_profile,
    )):
        app = _build_app_with_optional_vision(args)
        if args.trusted_local_tls:
            server = create_http_server(
                host=args.host,
                port=args.port,
                app=app,
                tls_certificate_chain_path=args.tls_certificate_chain_path,
                tls_private_key_path=args.tls_private_key_path,
            )
        else:
            server = create_http_server(host=args.host, port=args.port, app=app)
        actual_port = int(server.server_address[1])
        scheme = "https" if args.trusted_local_tls else "http"
        advertised_endpoint = resolve_pairing_advertised_endpoint(args, actual_port)
        if advertised_endpoint and hasattr(app, "advertised_endpoint"):
            app.advertised_endpoint = advertised_endpoint
        bonjour: Optional[BonjourAdvertisement] = None
        if args.bonjour:
            advertised_host = args.bonjour_host or resolve_advertised_host(args.host)
            pairing_page = (
                f"{scheme}://{advertised_host}:{actual_port}/mobile/v1/pairing/qr.html"
                if args.pairing_mode == "production"
                else ""
            )
            bonjour = BonjourAdvertisement(
                name=args.bonjour_name,
                host=advertised_host,
                port=actual_port,
                pairing_code=args.pairing_code if args.pairing_mode == "development" else "",
                runtime=args.runtime,
                scheme=scheme,
                pairing_page=pairing_page,
                expires_at="2099-01-01T00:00:00Z" if args.pairing_mode == "development" else "",
                trusted_local_tls_required=bool(getattr(args, "trusted_local_tls", False)),
                tls_certificate_label=str(getattr(args, "tls_certificate_label", "")),
                tls_public_key_sha256=str(getattr(args, "tls_public_key_sha256", "")),
            )
            try:
                bonjour.start()
                print(
                    f"Bonjour advertising {args.bonjour_name} at {scheme}://{advertised_host}:{actual_port}",
                    flush=True,
                )
            except OSError as error:
                print(f"Bonjour advertisement did not start: {error}", flush=True)
        print(f"Agent Pocket mock bridge listening on {scheme}://{args.host}:{actual_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            if bonjour is not None:
                bonjour.stop()
            server.server_close()
    return 0


def validate_server_config(args: argparse.Namespace) -> List[str]:
    errors: List[str] = []
    if (
        str(getattr(args, "recall_search_provider", "")).strip() == "runtime_http"
        and not str(getattr(args, "recall_search_endpoint", "")).strip()
    ):
        errors.append("--recall-search-endpoint is required when --recall-search-provider runtime_http.")
    if str(getattr(args, "recall_search_provider", "")).strip() == "runtime_http":
        endpoint = str(getattr(args, "recall_search_endpoint", "")).strip()
        if endpoint and not _is_http_endpoint(endpoint):
            errors.append("--recall-search-endpoint must be an http:// or https:// URL.")
        elif endpoint and not _is_local_or_private_endpoint(endpoint):
            errors.append("--recall-search-endpoint must point to localhost, Tailscale, or a private LAN endpoint.")
    if bool(getattr(args, "trusted_local_tls", False)):
        if not str(getattr(args, "tls_certificate_chain_path", "")).strip():
            errors.append("--tls-certificate-chain-path is required when --trusted-local-tls starts the bridge.")
        if not str(getattr(args, "tls_private_key_path", "")).strip():
            errors.append("--tls-private-key-path is required when --trusted-local-tls starts the bridge.")
    for flag, attr, default in (
        ("--input-assets-days", "input_assets_days", DEFAULT_INPUT_ASSETS_DAYS),
        ("--output-assets-days", "output_assets_days", DEFAULT_OUTPUT_ASSETS_DAYS),
        ("--task-history-days", "task_history_days", DEFAULT_TASK_HISTORY_DAYS),
    ):
        value = int(getattr(args, attr, default))
        if value < 1 or value > 3650:
            errors.append(f"{flag} must be between 1 and 3650.")
    return errors


def _is_http_endpoint(value: str) -> bool:
    parsed = urlsplit(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_local_or_private_endpoint(value: str) -> bool:
    parsed = urlsplit(value.strip())
    host = (parsed.hostname or "").lower()
    if host in {"localhost"} or host.endswith(".local"):
        return True
    try:
        address = ip_address(host)
    except ValueError:
        return False
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_reserved
        or _is_tailscale_cgnat(address)
    )


def _is_tailscale_cgnat(address) -> bool:
    return address.version == 4 and int(ip_address("100.64.0.0")) <= int(address) <= int(ip_address("100.127.255.255"))


def resolve_pairing_advertised_endpoint(args: argparse.Namespace, actual_port: int) -> str:
    should_publish_lan_endpoint = args.bonjour or args.host in {"0.0.0.0", "::"}
    if not should_publish_lan_endpoint:
        return ""
    advertised_host = args.bonjour_host or resolve_advertised_host(args.host)
    scheme = "https" if bool(getattr(args, "trusted_local_tls", False)) else "http"
    return f"{scheme}://{advertised_host}:{actual_port}"


def _build_app_with_optional_vision(args: argparse.Namespace) -> MockBridgeApp:
    runtime_store = _runtime_store_from_args(args)
    store_kwargs = {
        "runtime_store": runtime_store,
        "runtime_store_path": str(getattr(args, "runtime_store_path", "")).strip(),
    } if runtime_store is not None else {}
    pairing_manager = _pairing_manager_from_args(args, runtime_store)
    pairing_kwargs = {"pairing_manager": pairing_manager} if pairing_manager is not None else {}
    runtime_kwargs = {
        "runtime_id": str(getattr(args, "runtime", "hermes")).strip() or "hermes",
        "runtime_display_name": str(getattr(args, "bonjour_name", "Agent Pocket Mock Hermes")).strip()
        or "Agent Pocket Mock Hermes",
        "pairing_scheme": "https" if bool(getattr(args, "trusted_local_tls", False)) else "http",
        "trusted_local_tls_required": bool(getattr(args, "trusted_local_tls", False)),
        "tls_certificate_label": str(getattr(args, "tls_certificate_label", "")),
        "tls_public_key_sha256": str(getattr(args, "tls_public_key_sha256", "")),
    }
    retention_kwargs = {
        "input_assets_days": int(getattr(args, "input_assets_days", DEFAULT_INPUT_ASSETS_DAYS)),
        "output_assets_days": int(getattr(args, "output_assets_days", DEFAULT_OUTPUT_ASSETS_DAYS)),
        "task_history_days": int(getattr(args, "task_history_days", DEFAULT_TASK_HISTORY_DAYS)),
    }
    recall_kwargs = _recall_search_kwargs_from_args(args)
    if args.vision_provider == "fixture" and not args.vision_endpoint:
        return build_app_for_provider(
            args.photo_provider,
            photo_pack_root=args.photo_pack_root,
            **runtime_kwargs,
            **retention_kwargs,
            **recall_kwargs,
            **store_kwargs,
            **pairing_kwargs,
        )
    return build_app_for_provider(
        args.photo_provider,
        photo_pack_root=args.photo_pack_root,
        vision_provider=args.vision_provider,
        vision_endpoint=args.vision_endpoint,
        **runtime_kwargs,
        **retention_kwargs,
        **recall_kwargs,
        **store_kwargs,
        **pairing_kwargs,
    )


def _pairing_manager_from_args(args: argparse.Namespace, runtime_store: Optional[Any]) -> Optional[PairingManager]:
    if str(getattr(args, "pairing_mode", "development")) != "production":
        return None
    token_ttl_seconds = int(getattr(args, "token_ttl_seconds", 0))
    store = runtime_store or InMemoryPairingStore()
    return PairingManager(
        store=store,
        config=PairingSecurityConfig(
            code_ttl_seconds=int(getattr(args, "pairing_code_ttl_seconds", 120)),
            token_ttl_seconds=token_ttl_seconds if token_ttl_seconds > 0 else None,
            trusted_local_tls_required=bool(getattr(args, "trusted_local_tls", False)),
            tls_trust_state=str(getattr(args, "tls_trust_state", "not_configured")),
            tls_certificate_label=str(getattr(args, "tls_certificate_label", "")),
            tls_public_key_sha256=str(getattr(args, "tls_public_key_sha256", "")),
            tls_private_key_path=str(getattr(args, "tls_private_key_path", "")),
        ),
    )


def _recall_search_kwargs_from_args(args: argparse.Namespace) -> Dict[str, str]:
    provider = str(getattr(args, "recall_search_provider", "local")).strip()
    endpoint = str(getattr(args, "recall_search_endpoint", "")).strip()
    if provider == "local" and not endpoint:
        return {}
    return {
        "recall_search_provider": provider,
        "recall_search_endpoint": endpoint,
    }


def _runtime_store_from_args(args: argparse.Namespace):
    runtime_store_path = str(getattr(args, "runtime_store_path", "")).strip()
    if not runtime_store_path:
        return None
    from kaka_mobile_runtime_kit.runtime_store import SQLiteRuntimeStore

    store = SQLiteRuntimeStore(
        runtime_store_path,
        recall_search_provider=build_recall_search_provider(
            str(getattr(args, "recall_search_provider", "local")),
            endpoint=str(getattr(args, "recall_search_endpoint", "")),
        ),
    )
    store.initialize()
    return store


def _parse_env_file(path: str) -> Dict[str, str]:
    if not path:
        return {}
    values: Dict[str, str] = {}
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
            value = value.strip().strip('"').strip("'")
            if key:
                values[key] = value
    return values


def _provider_visible_env(values: Mapping[str, str]) -> Dict[str, str]:
    normalized = dict(values)
    for key in OPENAI_PROVIDER_ENV_KEYS:
        forced_key = f"{HERMES_PROVIDER_ENV_FORCE_PREFIX}{key}"
        forced_value = str(normalized.get(forced_key, "")).strip()
        if forced_value:
            normalized[key] = normalized[forced_key]
        normalized.pop(forced_key, None)
    return normalized


@contextmanager
def _temporary_environ(values: Mapping[str, str]):
    if not values:
        yield
        return
    previous = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def resolve_advertised_host(bind_host: str) -> str:
    if bind_host not in {"", "0.0.0.0", "::", "127.0.0.1", "localhost"}:
        return bind_host

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            host = probe.getsockname()[0]
            if host and not host.startswith("127."):
                return host
    except OSError:
        pass

    try:
        host = socket.gethostbyname(socket.gethostname())
        if host and not host.startswith("127."):
            return host
    except OSError:
        pass

    return "127.0.0.1"


def _launch_dns_sd(command: List[str]) -> BonjourProcess:
    return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def _parse_multipart_form(content_type: str, body: bytes) -> Dict[str, Any]:
    message = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    form: Dict[str, Any] = {}
    if not message.is_multipart():
        return form

    for part in message.iter_parts():
        disposition = part.get_content_disposition()
        if disposition != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_param("filename", header="content-disposition")
        payload = part.get_payload(decode=True) or b""
        if filename:
            form[str(name)] = (
                io.BytesIO(payload),
                str(filename),
                part.get_content_type(),
            )
        else:
            form[str(name)] = payload.decode(part.get_content_charset() or "utf-8")
    return form


if __name__ == "__main__":
    raise SystemExit(main())
