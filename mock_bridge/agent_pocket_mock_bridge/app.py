from __future__ import annotations

import base64
import hashlib
import html
import json
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request

from kaka_mobile_runtime_kit.image_intake import build_image_intake_result


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


class VisionProvider(Protocol):
    def analyze(
        self,
        source_bytes: bytes,
        mode: str,
        instruction: str,
        locale: Optional[str],
    ) -> Mapping[str, Any]:
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


class FixtureVisionProvider:
    provider_name = "fixture_vision"

    def analyze(
        self,
        source_bytes: bytes,
        mode: str,
        instruction: str,
        locale: Optional[str],
    ) -> Mapping[str, Any]:
        is_chinese = str(locale or "").lower().startswith("zh")
        size_kb = max(1, round(len(source_bytes) / 1024))
        if mode == "scan":
            return {
                "mode": mode,
                "title": "扫描结果" if is_chinese else "Scan Result",
                "summary": (
                    "当前为测试视觉提供器，已返回扫描结果结构；接入真实智能体后会显示 OCR 文本、二维码和文档信息。"
                    if is_chinese
                    else "This is the test vision provider. It returns scan-result structure; a real agent will return OCR text, codes, and document details."
                ),
                "text": (
                    "Mock Bridge：fixture_vision 不读取真实图片文字。"
                    if is_chinese
                    else "Mock Bridge: fixture_vision does not read real image text."
                ),
                "language": locale or ("zh-Hans" if is_chinese else "en"),
                "confidence": 0.74,
                "sections": [
                    {
                        "title": "文本" if is_chinese else "Text",
                        "kind": "ocr",
                        "items": [
                            {
                                "title": "OCR 状态" if is_chinese else "OCR status",
                                "value": "等待真实智能体接入" if is_chinese else "Waiting for a real agent provider",
                                "subtitle": "fixture_vision 只验证协议和 UI。" if is_chinese else "fixture_vision validates protocol and UI only.",
                                "confidence": 0.1,
                            }
                        ],
                    },
                    {
                        "title": "代码和文档" if is_chinese else "Codes and document",
                        "kind": "codes",
                        "items": [
                            {
                                "title": "上传资产" if is_chinese else "Uploaded asset",
                                "value": f"{size_kb} KB",
                                "subtitle": "本地 Mobile Bridge 已收到照片。" if is_chinese else "The local Mobile Bridge received the photo.",
                                "confidence": 0.98,
                            }
                        ],
                    },
                ],
                "items": [
                    {
                        "title": "文件大小" if is_chinese else "File size",
                        "value": f"{size_kb} KB",
                        "subtitle": "本地上传资产" if is_chinese else "Local uploaded asset",
                        "confidence": 0.98,
                    }
                ],
            }
        if mode == "translate":
            return {
                "mode": mode,
                "title": "翻译结果" if is_chinese else "Translation",
                "summary": (
                    "当前为测试视觉提供器，已返回翻译结果结构；接入真实智能体后会显示原文和译文。"
                    if is_chinese
                    else "This is the test vision provider. It returns translation structure; a real agent will return source and translated text."
                ),
                "text": (
                    "Mock Bridge：真实智能体会在这里返回原文和译文。"
                    if is_chinese
                    else "Mock Bridge: a real agent would return source text and translation here."
                ),
                "language": locale or ("zh-Hans" if is_chinese else "en"),
                "confidence": 0.70,
                "sections": [
                    {
                        "title": "翻译" if is_chinese else "Translation",
                        "kind": "ocr",
                        "items": [
                            {
                                "title": "原文" if is_chinese else "Source",
                                "value": "等待真实 OCR" if is_chinese else "Waiting for real OCR",
                                "confidence": 0.1,
                            },
                            {
                                "title": "译文" if is_chinese else "Translated",
                                "value": "本地视觉任务已接通" if is_chinese else "Local vision task is connected",
                                "confidence": 0.68,
                            },
                        ],
                    }
                ],
                "items": [
                    {
                        "title": "译文" if is_chinese else "Translation",
                        "value": "本地视觉任务已接通" if is_chinese else "Local vision task is connected",
                        "confidence": 0.68,
                    }
                ],
            }
        if mode == "food":
            return {
                "mode": mode,
                "title": "食物估算" if is_chinese else "Food Estimate",
                "summary": (
                    "示例估算：约 320-460 千卡。真实智能体接入后会根据可见食材、分量和烹饪方式细化。"
                    if is_chinese
                    else "Example estimate: about 320-460 kcal. A real agent will refine it from visible ingredients, portions, and cooking method."
                ),
                "text": (
                    "建议把餐盘完整放入画面，避免遮挡。"
                    if is_chinese
                    else "For better estimates, keep the whole plate visible and avoid occlusion."
                ),
                "language": locale or ("zh-Hans" if is_chinese else "en"),
                "confidence": 0.66,
                "sections": [
                    {
                        "title": "热量和营养" if is_chinese else "Calories and nutrition",
                        "kind": "nutrition",
                        "items": [
                            {
                                "title": "热量范围" if is_chinese else "Calories",
                                "value": "320-460 kcal",
                                "subtitle": "示例值；真实模型会按食材和分量估算。" if is_chinese else "Example value; a real model estimates from ingredients and portion size.",
                                "confidence": 0.61,
                            },
                            {
                                "title": "蛋白质" if is_chinese else "Protein",
                                "value": "12-24 g",
                                "subtitle": "取决于肉类、蛋类或豆制品可见分量。" if is_chinese else "Depends on visible meat, eggs, or legumes.",
                                "confidence": 0.48,
                            },
                            {
                                "title": "碳水" if is_chinese else "Carbs",
                                "value": "35-58 g",
                                "subtitle": "取决于主食、酱料和甜品。" if is_chinese else "Depends on staple food, sauce, and dessert.",
                                "confidence": 0.45,
                            },
                            {
                                "title": "脂肪" if is_chinese else "Fat",
                                "value": "10-22 g",
                                "subtitle": "取决于烹调用油和酱料。" if is_chinese else "Depends on cooking oil and sauce.",
                                "confidence": 0.42,
                            },
                        ],
                    },
                    {
                        "title": "估算依据" if is_chinese else "Assumptions",
                        "kind": "assumptions",
                        "items": [
                            {
                                "title": "拍摄建议" if is_chinese else "Capture tip",
                                "value": "完整拍下餐盘和分量参照物" if is_chinese else "Capture the whole plate with a portion reference",
                                "subtitle": "遮挡或近距离局部图会显著降低准确性。" if is_chinese else "Occlusion or close crops reduce accuracy.",
                                "confidence": 0.9,
                            }
                        ],
                    },
                ],
                "items": [
                    {
                        "title": "热量范围" if is_chinese else "Calories",
                        "value": "320-460 kcal",
                        "subtitle": "按可见分量粗略估算" if is_chinese else "Rough estimate from visible portions",
                        "confidence": 0.61,
                    }
                ],
            }
        return {
            "mode": "identify",
            "title": "识别结果" if is_chinese else "Identification",
            "summary": (
                "当前为测试视觉提供器，已返回识别结果结构；接入真实智能体后会显示主体、候选项和置信度。"
                if is_chinese
                else "This is the test vision provider. It returns identification structure; a real agent will return subjects, candidates, and confidence."
            ),
            "text": (
                "Mock Bridge：真实智能体会在这里返回更细的对象、品牌、植物或地标信息。"
                if is_chinese
                else "Mock Bridge: a real agent would return richer object, product, plant, or landmark details here."
            ),
            "language": locale or ("zh-Hans" if is_chinese else "en"),
            "confidence": 0.76,
            "sections": [
                {
                    "title": "候选识别" if is_chinese else "Candidates",
                    "kind": "candidates",
                    "items": [
                        {
                            "title": "候选主体" if is_chinese else "Candidate subject",
                            "value": "本地测试照片" if is_chinese else "Local test photo",
                            "subtitle": "fixture_vision 只验证协议；不会读取真实物体。" if is_chinese else "fixture_vision validates protocol only; it does not identify real objects.",
                            "confidence": 0.12,
                        },
                        {
                            "title": "下一步" if is_chinese else "Next step",
                            "value": "接入真实 Hermes/OpenClaw 视觉 provider" if is_chinese else "Connect a real Hermes/OpenClaw vision provider",
                            "confidence": 0.95,
                        },
                    ],
                }
            ],
            "items": [
                {
                    "title": "主要物体" if is_chinese else "Main object",
                    "value": "本地测试照片" if is_chinese else "Local test photo",
                    "subtitle": "由 mock 视觉提供器生成" if is_chinese else "Generated by the mock vision provider",
                    "confidence": 0.72,
                }
            ],
        }


class RuntimeHTTPVisionProvider:
    provider_name = "runtime_http_vision"

    def __init__(self, endpoint: str, timeout_seconds: float = 30.0) -> None:
        self.endpoint = endpoint.strip()
        self.timeout_seconds = timeout_seconds
        if not self.endpoint:
            raise ValueError("runtime_http vision endpoint is required.")

    def analyze(
        self,
        source_bytes: bytes,
        mode: str,
        instruction: str,
        locale: Optional[str],
    ) -> Mapping[str, Any]:
        payload = {
            "schema_version": 1,
            "task": "vision",
            "mode": mode,
            "instruction": instruction,
            "locale": locale,
            "image_base64": base64.b64encode(source_bytes).decode("ascii"),
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib_request.Request(
            self.endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except (urllib_error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"runtime_http vision endpoint is unavailable: {exc}") from exc
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("runtime_http vision endpoint returned invalid JSON.") from exc
        if not isinstance(decoded, Mapping):
            raise RuntimeError("runtime_http vision endpoint must return a JSON object.")
        vision = decoded.get("vision", decoded)
        if not isinstance(vision, Mapping):
            raise RuntimeError("runtime_http vision endpoint response must contain a vision object.")
        return dict(vision)


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
        vision_provider: Optional[VisionProvider] = None,
        advertised_endpoint: str = "",
    ) -> None:
        self.mobile_token = mobile_token
        self.photo_provider = photo_provider or FixturePhotoProvider()
        self.vision_provider = vision_provider or FixtureVisionProvider()
        self.advertised_endpoint = advertised_endpoint.strip().rstrip("/")
        self.pairing_codes: Dict[str, str] = dict(pairing_codes or {DEV_PAIRING_CODE: DEV_DISPLAY_NAME})
        self._dev_pairing_sequence = 1
        self._task_sequence = 1
        self._task_lock = threading.Lock()
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
            "vision_task_create": 0,
            "image_intake_task_create": 0,
            "task_status": 0,
            "task_events": 0,
            "asset_download": 0,
        }

    def test_client(self) -> MockClient:
        return MockClient(self)

    def _next_task_id(self) -> str:
        with self._task_lock:
            task_id = f"task_{self._task_sequence:04d}"
            self._task_sequence += 1
            return task_id

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

        if method == "POST" and path == "/mobile/v1/tasks/vision":
            self._count_request("vision_task_create")
            return self._create_vision_task(json_body or {})

        if method == "POST" and path == "/mobile/v1/tasks/image-intake":
            self._count_request("image_intake_task_create")
            return self._create_image_intake_task(json_body or {})

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
        endpoint = self.advertised_endpoint or f"http://{host}"
        pairing_code = self._current_development_pairing_code()
        return {
            "version": 1,
            "endpoint": endpoint,
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
                    "capabilities": ["photo_edit", "vision", "image_intake"],
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
                    "crop_aspects": ["original"],
                    "supports_crop_candidates": False,
                    "supports_upscale_policy": True,
                    "supports_sse": True,
                    "return_variants_max": 3,
                },
                "vision": {
                    "max_upload_mb": 30,
                    "accepted_mime_types": ["image/jpeg", "image/heic", "image/png"],
                    "modes": ["scan", "identify", "translate", "food"],
                    "provider": self._vision_provider_name(),
                    "supports_sse": True,
                },
                "image_intake": {
                    "max_upload_mb": 30,
                    "accepted_mime_types": ["image/jpeg", "image/heic", "image/png"],
                    "provider": "heuristic_image_intake",
                    "supports_sse": True,
                },
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

        task_id = self._next_task_id()
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
            result_asset_id = f"asset_result_{task_id.removeprefix('task_')}_{index}"
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

    def _create_vision_task(self, payload: Mapping[str, Any]) -> MockResponse:
        asset_id = str(payload.get("asset_id", ""))
        if asset_id not in self.assets:
            return self._error("not_found", "The source asset does not exist.", 404)

        mode = str(payload.get("mode", ""))
        if mode not in {"scan", "identify", "translate", "food"}:
            return self._error("vision_unavailable", "The requested vision mode is not available.", 400)

        task_id = self._next_task_id()
        source_asset = self.assets[asset_id]
        provider_name = self._vision_provider_name()
        try:
            vision_result = dict(
                self.vision_provider.analyze(
                    source_bytes=source_asset["bytes"],
                    mode=mode,
                    instruction=str(payload.get("instruction", "")),
                    locale=payload.get("locale"),
                )
            )
        except Exception:
            self.tasks[task_id] = {
                "task_id": task_id,
                "status": "failed",
                "progress": 1.0,
                "message": "The vision provider failed. Check Hermes provider credentials or logs.",
                "failure_code": "vision_failed",
                "provider": provider_name,
                "result_type": "vision",
            }
            return self._json(
                {
                    "task_id": task_id,
                    "status": "queued",
                    "events_url": f"/mobile/v1/tasks/{task_id}/events",
                }
            )

        vision_result.setdefault("mode", mode)
        vision_result.setdefault("title", mode.title())
        vision_result.setdefault("summary", "Vision task completed.")
        vision_result.setdefault("items", [])
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": "completed",
            "progress": 1.0,
            "message": "Completed.",
            "result_type": "vision",
            "vision": vision_result,
            "provider": provider_name,
        }
        return self._json(
            {
                "task_id": task_id,
                "status": "queued",
                "events_url": f"/mobile/v1/tasks/{task_id}/events",
            }
        )

    def _create_image_intake_task(self, payload: Mapping[str, Any]) -> MockResponse:
        asset_id = str(payload.get("asset_id", ""))
        if asset_id not in self.assets:
            return self._error("not_found", "The source asset does not exist.", 404)

        task_id = self._next_task_id()
        source_asset = self.assets[asset_id]
        try:
            image_intake = dict(
                build_image_intake_result(
                    image_bytes=source_asset["bytes"],
                    locale=payload.get("locale"),
                    recognized_lines=[],
                )
            )
            image_intake["suggestions"] = self._capability_aware_intake_suggestions(
                image_intake.get("suggestions", [])
            )
        except Exception:
            self.tasks[task_id] = {
                "task_id": task_id,
                "status": "failed",
                "progress": 1.0,
                "message": "The image intake provider failed. Check runtime logs.",
                "failure_code": "image_intake_failed",
                "provider": "heuristic_image_intake",
                "result_type": "image_intake",
            }
            return self._json(
                {
                    "task_id": task_id,
                    "status": "queued",
                    "events_url": f"/mobile/v1/tasks/{task_id}/events",
                }
            )

        self.tasks[task_id] = {
            "task_id": task_id,
            "status": "completed",
            "progress": 1.0,
            "message": "Completed.",
            "result_type": "image_intake",
            "image_intake": image_intake,
            "provider": "heuristic_image_intake",
        }
        return self._json(
            {
                "task_id": task_id,
                "status": "queued",
                "events_url": f"/mobile/v1/tasks/{task_id}/events",
            }
        )

    def _capability_aware_intake_suggestions(self, suggestions: Any) -> List[Mapping[str, Any]]:
        if not isinstance(suggestions, list):
            return []
        skill_modes = {
            "ocr": "scan",
            "translate_text": "translate",
            "identify_subject": "identify",
            "nutrition_estimate": "food",
        }
        vision_modes = set(self._capabilities()["tasks"]["vision"]["modes"])
        fixture_only_unavailable = {"identify_subject", "nutrition_estimate"}
        vision_provider_name = self._vision_provider_name()
        normalized: List[Mapping[str, Any]] = []
        for raw_suggestion in suggestions:
            if not isinstance(raw_suggestion, Mapping):
                continue
            suggestion = dict(raw_suggestion)
            skill = str(suggestion.get("skill", ""))
            if skill == "photo_enhance":
                suggestion["is_available"] = True
            elif skill in fixture_only_unavailable and vision_provider_name == "fixture_vision":
                suggestion["is_available"] = False
            elif skill in skill_modes:
                suggestion["is_available"] = skill_modes[skill] in vision_modes
            else:
                suggestion.setdefault("is_available", True)
            normalized.append(suggestion)
        return normalized

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
            if task.get("result_type") == "vision":
                message = "The vision provider failed."
            elif task.get("result_type") == "image_intake":
                message = "The image intake provider failed."
            else:
                message = "The photo provider failed."
            payload = (
                'event: task.progress\n'
                f'data: {json.dumps({"progress": 1.0, "message": message})}\n\n'
            )
        elif task.get("result_type") in {"vision", "image_intake"}:
            result_type = task.get("result_type")
            payload = (
                'event: task.progress\ndata: {"progress":1.0,"message":"Completed."}\n\n'
                f'event: task.completed\ndata: {{"result_type":"{result_type}"}}\n\n'
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
                "vision_name": self._vision_provider_name(),
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
        if "result_type" in task:
            summary["result_type"] = task["result_type"]
        if "variants" in task:
            summary["variant_count"] = len(task["variants"])
        if isinstance(task.get("vision"), Mapping):
            summary["vision"] = {
                "mode": task["vision"].get("mode"),
                "title": task["vision"].get("title"),
            }
        if isinstance(task.get("image_intake"), Mapping):
            summary["image_intake"] = {
                "image_type": task["image_intake"].get("image_type"),
                "title": task["image_intake"].get("title"),
            }
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

    def _vision_provider_name(self) -> str:
        explicit = getattr(self.vision_provider, "provider_name", None)
        if explicit:
            return str(explicit)
        return type(self.vision_provider).__name__

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
    vision_provider: Optional[VisionProvider] = None,
    advertised_endpoint: str = "",
) -> MockBridgeApp:
    return MockBridgeApp(
        pairing_codes=pairing_codes,
        mobile_token=mobile_token,
        photo_provider=photo_provider,
        vision_provider=vision_provider,
        advertised_endpoint=advertised_endpoint,
    )


def build_vision_provider(
    name: str = "fixture",
    endpoint: str = "",
) -> VisionProvider:
    if name == "fixture":
        return FixtureVisionProvider()
    if name == "runtime_http":
        return RuntimeHTTPVisionProvider(endpoint)
    raise ValueError(f"Unsupported vision provider: {name}")
