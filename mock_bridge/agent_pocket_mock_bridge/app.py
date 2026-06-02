from __future__ import annotations

import base64
import hashlib
import html
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Protocol


DEV_MOBILE_TOKEN = "dev-mobile-token"
DEV_PAIRING_CODE = "pair_dev"
DEV_DISPLAY_NAME = "Agent Pocket Mock Hermes"

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class PhotoProvider(Protocol):
    def edit(
        self,
        source_bytes: bytes,
        style: str,
        instruction: str,
        return_variants: int,
    ) -> List[Mapping[str, Any]]:
        ...


class FixturePhotoProvider:
    provider_name = "fixture"

    def edit(
        self,
        source_bytes: bytes,
        style: str,
        instruction: str,
        return_variants: int,
    ) -> List[Mapping[str, Any]]:
        return [
            {
                "id": "variant_mock",
                "label": "Mock Natural",
                "mime_type": "image/png",
                "bytes": TINY_PNG,
                "explanation": "Mock bridge returned a deterministic fixture image.",
            }
        ][: max(return_variants, 1)]


@dataclass
class MockResponse:
    status_code: int
    body: Optional[Mapping[str, Any]] = None
    data: bytes = b""
    content_type: str = "application/json"

    def get_json(self) -> Mapping[str, Any]:
        if self.body is None:
            return {}
        return self.body


class MockClient:
    def __init__(self, app: "MockBridgeApp") -> None:
        self.app = app

    def get(self, path: str, headers: Optional[Mapping[str, str]] = None) -> MockResponse:
        return self.app.handle("GET", path, headers=headers or {})

    def post(
        self,
        path: str,
        headers: Optional[Mapping[str, str]] = None,
        json: Optional[Mapping[str, Any]] = None,
        data: Optional[Mapping[str, Any]] = None,
    ) -> MockResponse:
        return self.app.handle("POST", path, headers=headers or {}, json_body=json, form_data=data)


class MockBridgeApp:
    def __init__(
        self,
        pairing_codes: Optional[Mapping[str, str]] = None,
        mobile_token: str = DEV_MOBILE_TOKEN,
        photo_provider: Optional[PhotoProvider] = None,
    ) -> None:
        self.mobile_token = mobile_token
        self.photo_provider = photo_provider or FixturePhotoProvider()
        self.pairing_codes: Dict[str, str] = dict(pairing_codes or {DEV_PAIRING_CODE: DEV_DISPLAY_NAME})
        self._dev_pairing_sequence = 1
        self.used_pairing_codes: set[str] = set()
        self.assets: MutableMapping[str, Dict[str, Any]] = {}
        self.tasks: MutableMapping[str, Dict[str, Any]] = {}
        self.download_requests: List[Dict[str, Any]] = []
        self.request_counts: Dict[str, int] = {
            "health": 0,
            "capabilities": 0,
            "pairing_dev": 0,
            "pairing_exchange": 0,
            "asset_upload": 0,
            "photo_task_create": 0,
            "task_status": 0,
            "task_events": 0,
            "asset_download": 0,
        }

    def test_client(self) -> MockClient:
        return MockClient(self)

    def handle(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str],
        json_body: Optional[Mapping[str, Any]] = None,
        form_data: Optional[Mapping[str, Any]] = None,
    ) -> MockResponse:
        if method == "GET" and path == "/mobile/v1/health":
            self._count_request("health")
            return self._json(
                {
                    "ok": True,
                    "runtime": "hermes",
                    "runtime_version": "2026.5.16",
                    "bridge_version": "0.1.0",
                }
            )

        if method == "POST" and path == "/mobile/v1/pairing/exchange":
            self._count_request("pairing_exchange")
            return self._pairing_exchange(json_body or {})

        if method == "GET" and path == "/mobile/v1/pairing/dev":
            self._count_request("pairing_dev")
            return self._json(self._development_pairing_payload(headers))

        if method == "GET" and path == "/mobile/v1/pairing/dev.html":
            self._count_request("pairing_dev")
            return self._development_pairing_page(headers)

        auth_error = self._require_auth(headers)
        if auth_error is not None:
            return auth_error

        if method == "GET" and path == "/mobile/v1/capabilities":
            self._count_request("capabilities")
            return self._json(self._capabilities())

        if method == "GET" and path == "/mobile/v1/qa/status":
            return self._json(self._qa_status())

        if method == "POST" and path == "/mobile/v1/assets":
            self._count_request("asset_upload")
            return self._upload_asset(form_data or {})

        if method == "POST" and path == "/mobile/v1/tasks/photo-edit":
            self._count_request("photo_task_create")
            return self._create_photo_task(json_body or {})

        if method == "GET" and path.startswith("/mobile/v1/tasks/"):
            suffix = path.removeprefix("/mobile/v1/tasks/")
            if suffix.endswith("/events"):
                self._count_request("task_events")
                return self._task_events(suffix.removesuffix("/events"))
            self._count_request("task_status")
            return self._task_status(suffix)

        if method == "GET" and path.startswith("/mobile/v1/assets/") and path.endswith("/download"):
            asset_id = path.removeprefix("/mobile/v1/assets/").removesuffix("/download")
            self._count_request("asset_download")
            return self._download_asset(asset_id)

        return self._error("not_found", "The requested mock bridge route does not exist.", 404)

    def _require_auth(self, headers: Mapping[str, str]) -> Optional[MockResponse]:
        if headers.get("Authorization") != f"Bearer {self.mobile_token}":
            return self._error("unauthorized", "The mobile token is missing or invalid.", 401)
        return None

    def _pairing_exchange(self, payload: Mapping[str, Any]) -> MockResponse:
        pairing_code = str(payload.get("pairing_code", ""))
        display_name = self.pairing_codes.get(pairing_code)
        if display_name is None:
            return self._error("pairing_expired", "The pairing code is missing or expired.", 404)
        if pairing_code in self.used_pairing_codes:
            return self._error("pairing_already_used", "The pairing code has already been used.", 409)

        self.used_pairing_codes.add(pairing_code)
        return self._json(
            {
                "endpoint_id": "endpoint_mock_hermes",
                "display_name": display_name,
                "runtime": "hermes",
                "runtime_version": "2026.5.16",
                "mobile_token": self.mobile_token,
                "token_expires_at": None,
            }
        )

    def _current_development_pairing_code(self) -> str:
        display_name = self.pairing_codes.get(DEV_PAIRING_CODE, DEV_DISPLAY_NAME)
        self.pairing_codes.setdefault(DEV_PAIRING_CODE, display_name)
        if DEV_PAIRING_CODE not in self.used_pairing_codes:
            return DEV_PAIRING_CODE

        prefix = f"{DEV_PAIRING_CODE}_"
        for code in sorted(self.pairing_codes):
            if code.startswith(prefix) and code not in self.used_pairing_codes:
                return code

        while True:
            self._dev_pairing_sequence += 1
            code = f"{prefix}{self._dev_pairing_sequence:04d}"
            if code not in self.pairing_codes and code not in self.used_pairing_codes:
                self.pairing_codes[code] = display_name
                return code

    def _development_pairing_payload(self, headers: Mapping[str, str]) -> Mapping[str, Any]:
        host = headers.get("Host") or "127.0.0.1:8765"
        pairing_code = self._current_development_pairing_code()
        return {
            "version": 1,
            "endpoint": f"http://{host}",
            "runtime": "hermes",
            "display_name": self.pairing_codes.get(pairing_code, DEV_DISPLAY_NAME),
            "pairing_code": pairing_code,
            "expires_at": "2099-01-01T00:00:00Z",
        }

    def _development_pairing_page(self, headers: Mapping[str, str]) -> MockResponse:
        payload = self._development_pairing_payload(headers)
        endpoint = str(payload["endpoint"])
        payload_json = json.dumps(payload, indent=2, sort_keys=True)
        compact_payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        qr_data_uri = self._development_pairing_qr_data_uri(compact_payload_json)
        escaped_endpoint = html.escape(endpoint)
        escaped_payload = html.escape(payload_json)
        escaped_payload_attribute = html.escape(compact_payload_json, quote=True)
        health_command = html.escape(f"curl {endpoint}/mobile/v1/health")
        capabilities_command = html.escape(
            f'curl -H "Authorization: Bearer {self.mobile_token}" {endpoint}/mobile/v1/capabilities'
        )
        qr_markup = ""
        if qr_data_uri:
            qr_markup = f"""
    <figure class="pairing-qr-card">
      <div class="qr-shell">
        <img class="pairing-qr" src="{qr_data_uri}" alt="Pairing QR code for Agent Pocket" data-pairing-payload="{escaped_payload_attribute}">
      </div>
      <figcaption>Scan this QR in Agent Pocket to pair with the mock Hermes bridge.</figcaption>
    </figure>
"""

        body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agent Pocket Mock Hermes Pairing</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
      line-height: 1.45;
      background: Canvas;
      color: CanvasText;
    }}
    body {{
      margin: 0;
      padding: 32px;
    }}
    main {{
      max-width: 760px;
      margin: 0 auto;
    }}
    h1 {{
      font-size: clamp(2rem, 7vw, 4rem);
      line-height: 1;
      margin: 0 0 16px;
    }}
    .endpoint {{
      display: inline-block;
      font-weight: 700;
      padding: 10px 12px;
      border: 1px solid color-mix(in srgb, CanvasText 18%, transparent);
      border-radius: 8px;
      word-break: break-all;
    }}
    .pairing-qr-card {{
      margin: 24px 0;
      padding: 16px;
      border: 1px solid color-mix(in srgb, CanvasText 14%, transparent);
      border-radius: 8px;
      background: color-mix(in srgb, CanvasText 3%, Canvas);
    }}
    .qr-shell {{
      display: inline-flex;
      padding: 18px;
      border-radius: 8px;
      background: #fff;
    }}
    .pairing-qr {{
      display: block;
      width: min(280px, 70vw);
      height: auto;
      image-rendering: pixelated;
    }}
    figcaption {{
      margin-top: 12px;
      color: color-mix(in srgb, CanvasText 68%, transparent);
    }}
    pre {{
      overflow-x: auto;
      padding: 16px;
      border-radius: 8px;
      background: color-mix(in srgb, CanvasText 7%, Canvas);
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.95rem;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Mock Hermes Pairing</h1>
    <p>Open Agent Pocket, choose Scan Pairing QR or Discover Local Runtime, then use this development payload for local QA.</p>
    <p class="endpoint">{escaped_endpoint}</p>
{qr_markup}

    <h2>Pairing Payload</h2>
    <pre><code>{escaped_payload}</code></pre>

    <h2>Verify Bridge</h2>
    <pre><code>{health_command}
{capabilities_command}</code></pre>
  </main>
</body>
</html>
"""
        return MockResponse(
            status_code=200,
            data=body.encode("utf-8"),
            content_type="text/html; charset=utf-8",
        )

    def _development_pairing_qr_data_uri(self, payload_json: str) -> Optional[str]:
        try:
            from Foundation import NSData, NSMutableData
            from Quartz import (
                CIFilter,
                CIContext,
                CGAffineTransformMakeScale,
                CGImageDestinationAddImage,
                CGImageDestinationCreateWithData,
                CGImageDestinationFinalize,
            )
        except Exception:
            return None

        payload_bytes = payload_json.encode("utf-8")
        qr_filter = CIFilter.filterWithName_("CIQRCodeGenerator")
        if qr_filter is None:
            return None

        qr_filter.setValue_forKey_(
            NSData.dataWithBytes_length_(payload_bytes, len(payload_bytes)),
            "inputMessage",
        )
        qr_filter.setValue_forKey_("M", "inputCorrectionLevel")
        image = qr_filter.outputImage()
        if image is None:
            return None

        scaled_image = image.imageByApplyingTransform_(CGAffineTransformMakeScale(8, 8))
        context = CIContext.contextWithOptions_(None)
        cg_image = context.createCGImage_fromRect_(scaled_image, scaled_image.extent())
        if cg_image is None:
            return None

        png_data = NSMutableData.data()
        destination = CGImageDestinationCreateWithData(png_data, "public.png", 1, None)
        if destination is None:
            return None
        CGImageDestinationAddImage(destination, cg_image, None)
        if not CGImageDestinationFinalize(destination):
            return None

        encoded = base64.b64encode(bytes(png_data)).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _capabilities(self) -> Mapping[str, Any]:
        return {
            "profiles": [
                {
                    "id": "photo-agent",
                    "display_name": "Photo Agent",
                    "capabilities": ["photo_edit"],
                }
            ],
            "tasks": {
                "photo_edit": {
                    "max_upload_mb": 30,
                    "accepted_mime_types": ["image/jpeg", "image/heic", "image/png"],
                    "styles": [
                        "natural_enhance",
                        "portrait_polish",
                        "product_shot",
                        "social_cover",
                    ],
                    "provider": "recipe_local",
                    "renderer": "local_parametric",
                    "variant_labels": ["Master", "Social"],
                    "variant_ids": ["variant_clean_pro", "variant_social_pop"],
                    "crop_aspects": ["original", "4:5", "1:1"],
                    "supports_crop_candidates": True,
                    "supports_upscale_policy": True,
                    "supports_sse": True,
                    "return_variants_max": 3,
                }
            },
            "retention": {
                "input_assets_days": 7,
                "output_assets_days": 30,
                "task_history_days": 30,
            },
        }

    def _upload_asset(self, form_data: Mapping[str, Any]) -> MockResponse:
        file_value = form_data.get("file")
        if not isinstance(file_value, tuple) or len(file_value) < 3:
            return self._error("unsupported_media_type", "The upload must include a file field.", 415)

        file_obj, filename, mime_type = file_value[:3]
        raw = file_obj.read() if hasattr(file_obj, "read") else bytes(file_obj)
        if not raw:
            return self._error("unsupported_media_type", "The uploaded file is empty.", 415)

        digest = hashlib.sha256(raw).hexdigest()
        asset_id = f"asset_{digest[:16]}"
        self.assets[asset_id] = {
            "bytes": raw,
            "filename": filename,
            "mime_type": mime_type,
            "metadata": form_data.get("metadata", "{}"),
            "size_bytes": len(raw),
            "sha256": digest,
        }
        return self._json(
            {
                "asset_id": asset_id,
                "mime_type": mime_type,
                "size_bytes": len(raw),
                "sha256": digest,
            }
        )

    def _create_photo_task(self, payload: Mapping[str, Any]) -> MockResponse:
        asset_id = str(payload.get("asset_id", ""))
        if asset_id not in self.assets:
            return self._error("not_found", "The source asset does not exist.", 404)

        task_id = f"task_{len(self.tasks) + 1:04d}"
        source_asset = self.assets[asset_id]
        provider_name = self._provider_name()
        try:
            provider_variants = self.photo_provider.edit(
                source_bytes=source_asset["bytes"],
                style=str(payload.get("style", "natural_enhance")),
                instruction=str(payload.get("instruction", "")),
                return_variants=int(payload.get("return_variants", 1)),
            )
        except Exception:
            self.tasks[task_id] = {
                "task_id": task_id,
                "status": "failed",
                "progress": 1.0,
                "message": "The photo provider failed. Check Hermes provider credentials or logs.",
                "failure_code": "provider_failed",
                "provider": provider_name,
            }
            return self._json(
                {
                    "task_id": task_id,
                    "status": "queued",
                    "events_url": f"/mobile/v1/tasks/{task_id}/events",
                }
            )
        variants = []
        explanation = "Photo provider completed the edit."
        recipe_metadata: Mapping[str, Any] = {}
        for index, provider_variant in enumerate(provider_variants, start=1):
            variant_bytes = provider_variant["bytes"]
            mime_type = provider_variant.get("mime_type", "image/png")
            variant_recipe_metadata = provider_variant.get("recipe_metadata")
            if not recipe_metadata and isinstance(variant_recipe_metadata, Mapping):
                recipe_metadata = variant_recipe_metadata
            result_asset_id = f"asset_result_{len(self.tasks) + 1:04d}_{index}"
            self.assets[result_asset_id] = {
                "bytes": variant_bytes,
                "filename": f"variant_{index}.png",
                "mime_type": mime_type,
                "metadata": json.dumps(
                    {"variant_id": provider_variant.get("id", f"variant_{index}"), "recipe": variant_recipe_metadata}
                    if isinstance(variant_recipe_metadata, Mapping)
                    else {}
                ),
                "size_bytes": len(variant_bytes),
                "sha256": hashlib.sha256(variant_bytes).hexdigest(),
            }
            variants.append(
                {
                    "id": provider_variant.get("id", f"variant_{index}"),
                    "label": provider_variant.get("label", f"Variant {index}"),
                    "asset_id": result_asset_id,
                    "download_url": f"/mobile/v1/assets/{result_asset_id}/download",
                }
            )
            explanation = str(provider_variant.get("explanation", explanation))

        task = {
            "task_id": task_id,
            "status": "completed",
            "progress": 1.0,
            "message": "Completed.",
            "variants": variants,
            "explanation": explanation,
            "provider": provider_name,
        }
        if recipe_metadata:
            task["recipe_metadata"] = dict(recipe_metadata)
            for key in (
                "renderer",
                "composition",
                "qa",
                "share_caption",
                "recipe_summary",
                "safety",
                "upscale",
            ):
                if key in recipe_metadata:
                    task[key] = recipe_metadata[key]
        self.tasks[task_id] = task
        return self._json(
            {
                "task_id": task_id,
                "status": "queued",
                "events_url": f"/mobile/v1/tasks/{task_id}/events",
            }
        )

    def _task_status(self, task_id: str) -> MockResponse:
        task = self.tasks.get(task_id)
        if task is None:
            return self._error("not_found", "The task does not exist.", 404)
        return self._json(task)

    def _task_events(self, task_id: str) -> MockResponse:
        task = self.tasks.get(task_id)
        if task is None:
            return self._error("not_found", "The task does not exist.", 404)
        if task.get("status") == "failed":
            payload = (
                'event: task.progress\n'
                'data: {"progress":1.0,"message":"The photo provider failed."}\n\n'
            )
        else:
            variant_count = len(task.get("variants", [])) if isinstance(task.get("variants"), list) else 0
            payload = (
                'event: task.progress\ndata: {"progress":1.0,"message":"Completed."}\n\n'
                f'event: task.completed\ndata: {{"variant_count":{variant_count}}}\n\n'
            )
        return MockResponse(status_code=200, data=payload.encode("utf-8"), content_type="text/event-stream")

    def _download_asset(self, asset_id: str) -> MockResponse:
        asset = self.assets.get(asset_id)
        if asset is None:
            return self._error("not_found", "The asset does not exist.", 404)
        self.download_requests.append(
            {
                "asset_id": asset_id,
                "mime_type": asset["mime_type"],
                "size_bytes": asset["size_bytes"],
            }
        )
        return MockResponse(status_code=200, data=asset["bytes"], content_type=asset["mime_type"])

    def _qa_status(self) -> Mapping[str, Any]:
        uploaded_assets = [
            (asset_id, asset)
            for asset_id, asset in self.assets.items()
            if not asset_id.startswith("asset_result_")
        ]
        result_assets = [
            (asset_id, asset)
            for asset_id, asset in self.assets.items()
            if asset_id.startswith("asset_result_")
        ]
        last_upload = uploaded_assets[-1] if uploaded_assets else None
        tasks = list(self.tasks.values())
        last_task = tasks[-1] if tasks else None
        completed = [task for task in tasks if task.get("status") == "completed"]
        failed = [task for task in tasks if task.get("status") == "failed"]

        return {
            "pairing": {
                "used_codes": sorted(self.used_pairing_codes),
                "current_development_code": self._current_development_pairing_code(),
            },
            "requests": dict(self.request_counts),
            "assets": {
                "uploaded_count": len(uploaded_assets),
                "result_count": len(result_assets),
                "download_request_count": len(self.download_requests),
                "last_upload": self._qa_asset_summary(*last_upload) if last_upload else None,
                "last_download": self.download_requests[-1] if self.download_requests else None,
            },
            "tasks": {
                "total": len(tasks),
                "completed": len(completed),
                "failed": len(failed),
                "last_task": self._qa_task_summary(last_task) if last_task else None,
            },
            "provider": {
                "name": self._provider_name(),
            },
        }

    def _qa_asset_summary(self, asset_id: str, asset: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "asset_id": asset_id,
            "filename": asset["filename"],
            "mime_type": asset["mime_type"],
            "size_bytes": asset["size_bytes"],
        }

    def _qa_task_summary(self, task: Mapping[str, Any]) -> Mapping[str, Any]:
        summary = {
            "task_id": task["task_id"],
            "status": task["status"],
            "progress": task.get("progress"),
            "message": task.get("message"),
        }
        if "failure_code" in task:
            summary["failure_code"] = task["failure_code"]
        if "provider" in task:
            summary["provider"] = task["provider"]
        if "variants" in task:
            summary["variant_count"] = len(task["variants"])
        for key in (
            "renderer",
            "composition",
            "qa",
            "share_caption",
            "recipe_summary",
            "safety",
            "upscale",
        ):
            if key in task:
                summary[key] = task[key]
        return summary

    def _provider_name(self) -> str:
        explicit = getattr(self.photo_provider, "provider_name", None)
        if explicit:
            return str(explicit)
        return type(self.photo_provider).__name__

    def _count_request(self, name: str) -> None:
        self.request_counts[name] = self.request_counts.get(name, 0) + 1

    def _json(self, body: Mapping[str, Any], status_code: int = 200) -> MockResponse:
        return MockResponse(status_code=status_code, body=body, data=json.dumps(body).encode("utf-8"))

    def _error(self, code: str, message: str, status_code: int) -> MockResponse:
        return self._json(
            {
                "error": {
                    "code": code,
                    "message": message,
                    "recoverable": status_code < 500,
                }
            },
            status_code=status_code,
        )


def create_app(
    pairing_codes: Optional[Mapping[str, str]] = None,
    mobile_token: str = DEV_MOBILE_TOKEN,
    photo_provider: Optional[PhotoProvider] = None,
) -> MockBridgeApp:
    return MockBridgeApp(
        pairing_codes=pairing_codes,
        mobile_token=mobile_token,
        photo_provider=photo_provider,
    )
