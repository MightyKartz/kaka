from __future__ import annotations

import argparse
import base64
import io
import json
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlparse


TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class FakeOpenAIHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.requests: List[Mapping[str, Any]] = []

    def record_request(self, request: Mapping[str, Any]) -> None:
        self.requests.append(dict(request))

    def status_payload(self) -> Mapping[str, Any]:
        return {
            "request_count": len(self.requests),
            "last_request": self.requests[-1] if self.requests else None,
        }


class FakeOpenAIRequestHandler(BaseHTTPRequestHandler):
    server: FakeOpenAIHTTPServer

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/status":
            self._send_json(self.server.status_payload())
            return
        self._send_json({"error": {"message": "not found"}}, status_code=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/images/edits", "/v1/images/edits"}:
            self._send_json({"error": {"message": "not found"}}, status_code=404)
            return

        content_type = self.headers.get("Content-Type", "")
        body = self._read_body()
        parsed = _parse_multipart_form(content_type, body)
        fields = {key: value for key, value in parsed.items() if isinstance(value, str)}
        files = {
            key: {
                "filename": value[1],
                "mime_type": value[2],
                "size_bytes": len(value[0].getvalue()),
            }
            for key, value in parsed.items()
            if isinstance(value, tuple) and len(value) >= 3 and isinstance(value[0], io.BytesIO)
        }

        self.server.record_request(
            {
                "path": path,
                "authorization_present": bool(self.headers.get("Authorization")),
                "content_type": content_type.split(";", 1)[0],
                "body_size": len(body),
                "fields": fields,
                "files": files,
            }
        )
        self._send_json({"data": [{"b64_json": _fake_image_b64()} for _ in range(_variant_count(fields))]})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def _send_json(self, payload: Mapping[str, Any], status_code: int = 200) -> None:
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def create_fake_openai_server(host: str = "127.0.0.1", port: int = 8781) -> FakeOpenAIHTTPServer:
    return FakeOpenAIHTTPServer((host, port), FakeOpenAIRequestHandler)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a local OpenAI Images Edits compatible fake server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", default=8781, type=int, help="Bind port.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    server = create_fake_openai_server(host=args.host, port=args.port)
    actual_port = int(server.server_address[1])
    print(f"Fake OpenAI Images server listening on http://{args.host}:{actual_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


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


def _variant_count(fields: Mapping[str, str]) -> int:
    try:
        requested = int(fields.get("n", "1"))
    except ValueError:
        requested = 1
    return max(1, min(requested, 3))


def _fake_image_b64() -> str:
    return base64.b64encode(TINY_PNG).decode("ascii")


if __name__ == "__main__":
    raise SystemExit(main())
