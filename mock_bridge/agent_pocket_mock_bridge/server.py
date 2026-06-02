from __future__ import annotations

import argparse
import io
import json
import os
import socket
import subprocess
from contextlib import contextmanager
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol
from urllib.parse import urlparse

from agent_pocket_mock_bridge.app import MockBridgeApp, MockResponse, create_app
from agent_pocket_mock_bridge.photo_providers import build_photo_provider

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
        launcher: Optional[Callable[[List[str]], BonjourProcess]] = None,
    ) -> None:
        self.name = name
        self.host = host
        self.port = port
        self.pairing_code = pairing_code
        self.runtime = runtime
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
        return [
            "dns-sd",
            "-R",
            self.name,
            self.service_type,
            "local",
            str(self.port),
            f"display_name={self.name}",
            f"runtime={self.runtime}",
            "scheme=http",
            f"endpoint=http://{self.host}:{self.port}",
            f"pairing_code={self.pairing_code}",
            "expires_at=2099-01-01T00:00:00Z",
        ]


class MockBridgeRequestHandler(BaseHTTPRequestHandler):
    server: MockBridgeHTTPServer

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle(self, method: str) -> None:
        content_type = self.headers.get("Content-Type", "")
        body = self._read_body()
        json_body: Optional[Mapping[str, Any]] = None
        form_data: Optional[Mapping[str, Any]] = None

        if method == "POST" and body:
            if content_type.startswith("application/json"):
                json_body = json.loads(body.decode("utf-8"))
            elif content_type.startswith("multipart/form-data"):
                form_data = _parse_multipart_form(content_type, body)

        response = self.server.app.handle(
            method,
            urlparse(self.path).path,
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
) -> MockBridgeHTTPServer:
    return MockBridgeHTTPServer((host, port), MockBridgeRequestHandler, app or create_app())


def build_app_for_provider(
    photo_provider: str = "fixture",
    photo_pack_root: str = "photo-pack",
) -> MockBridgeApp:
    return create_app(photo_provider=build_photo_provider(photo_provider, photo_pack_root=photo_pack_root))


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
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    with _temporary_environ(_provider_env_overlay(
        env_file=args.env_file,
        hermes_home=args.hermes_home,
        hermes_profile=args.hermes_profile,
    )):
        app = build_app_for_provider(args.photo_provider, photo_pack_root=args.photo_pack_root)
        server = create_http_server(host=args.host, port=args.port, app=app)
        actual_port = int(server.server_address[1])
        bonjour: Optional[BonjourAdvertisement] = None
        if args.bonjour:
            advertised_host = args.bonjour_host or resolve_advertised_host(args.host)
            bonjour = BonjourAdvertisement(
                name=args.bonjour_name,
                host=advertised_host,
                port=actual_port,
                pairing_code=args.pairing_code,
                runtime=args.runtime,
            )
            try:
                bonjour.start()
                print(
                    f"Bonjour advertising {args.bonjour_name} at http://{advertised_host}:{actual_port}",
                    flush=True,
                )
            except OSError as error:
                print(f"Bonjour advertisement did not start: {error}", flush=True)
        print(f"Agent Pocket mock bridge listening on http://{args.host}:{actual_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            if bonjour is not None:
                bonjour.stop()
            server.server_close()
    return 0


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
