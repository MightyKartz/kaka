from __future__ import annotations

import base64
import hashlib
import html
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import parse_qs, unquote, urlsplit

from kaka_mobile_runtime_kit.image_intake import build_image_intake_result
from kaka_mobile_runtime_kit.pairing import PairingManager
from kaka_mobile_runtime_kit.recall_export import build_recall_export_artifact
from kaka_mobile_runtime_kit.recall_search import (
    RecallSearchProvider,
    build_recall_search_provider,
)
from kaka_mobile_runtime_kit.retention_purge import build_runtime_retention_purge_receipt

try:
    from kaka_mobile_runtime_kit.runtime_store import (
        RuntimeAssetRecord,
        RuntimeRecallItem,
        RuntimeTaskEvent,
        RuntimeTaskRecord,
    )
except Exception:
    RuntimeAssetRecord = None
    RuntimeRecallItem = None
    RuntimeTaskEvent = None
    RuntimeTaskRecord = None


DEV_MOBILE_TOKEN = "dev-mobile-token"
DEV_PAIRING_CODE = "pair_dev"
DEV_DISPLAY_NAME = "Agent Pocket Mock Hermes"
DEFAULT_INPUT_ASSETS_DAYS = 7
DEFAULT_OUTPUT_ASSETS_DAYS = 30
DEFAULT_TASK_HISTORY_DAYS = 30
UNSAFE_TASK_METADATA_KEY_MARKERS = (
    "endpoint",
    "token",
    "api_key",
    "apikey",
    "secret",
    "credential",
    "password",
    "hidden_prompt",
    "raw_provider",
    "raw_response",
    "private_key",
    "runtime_store_path",
    "sqlite",
    "path",
)
UNSAFE_TASK_METADATA_VALUE_MARKERS = (
    "://",
    "bearer ",
    "data:image",
    "dev-mobile-token",
    ".sqlite",
    "ivbor",
    "mobile_token",
    "/users/",
    "provider_endpoint",
    "runtime_store_path",
    "source-image",
    "token=",
    "sk-",
)


def _normalized_public_key_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64:
        return ""
    if any(char not in "0123456789abcdef" for char in normalized):
        return ""
    return normalized


def _unsafe_task_metadata_key(key: Any) -> bool:
    normalized = str(key).strip().replace("-", "_").lower()
    return any(marker in normalized for marker in UNSAFE_TASK_METADATA_KEY_MARKERS)


def _unsafe_task_metadata_string(value: str) -> bool:
    normalized = value.strip().lower()
    return any(marker in normalized for marker in UNSAFE_TASK_METADATA_VALUE_MARKERS)


def _safe_json_value(value: Any) -> Any:
    if value is None:
        return value
    if isinstance(value, str):
        return None if _unsafe_task_metadata_string(value) else value
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, Mapping):
        safe_mapping: Dict[str, Any] = {}
        for key, raw_child in value.items():
            if _unsafe_task_metadata_key(key):
                continue
            child = _safe_json_value(raw_child)
            if child is not None:
                safe_mapping[str(key)] = child
        return safe_mapping
    if isinstance(value, list):
        return [child for raw_child in value if (child := _safe_json_value(raw_child)) is not None]
    return None


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
        variants = [
            {
                "id": "variant_clean_pro",
                "label": "Master",
                "mime_type": "image/png",
                "bytes": TINY_PNG,
                "explanation": "Mock bridge returned a deterministic master fixture image.",
            },
            {
                "id": "variant_social_pop",
                "label": "Social",
                "mime_type": "image/png",
                "bytes": TINY_PNG,
                "explanation": "Mock bridge returned a deterministic social fixture image.",
            },
        ]
        requested = max(1, min(int(return_variants), len(variants)))
        return variants[:requested]


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

    def delete(self, path: str, headers: Optional[Mapping[str, str]] = None) -> MockResponse:
        return self.app.handle("DELETE", path, headers=headers or {})


class MockBridgeApp:
    CONTEXT_SNAPSHOT_ALLOWED_FIELDS = frozenset(
        (
            "timestamp",
            "timezone",
            "locale",
            "source_surface",
            "network",
            "battery",
            "motion",
            "location_label",
            "location_precision",
            "calendar_availability",
        )
    )

    def __init__(
        self,
        pairing_codes: Optional[Mapping[str, str]] = None,
        mobile_token: str = DEV_MOBILE_TOKEN,
        photo_provider: Optional[PhotoProvider] = None,
        vision_provider: Optional[VisionProvider] = None,
        advertised_endpoint: str = "",
        runtime_id: str = "hermes",
        runtime_display_name: str = DEV_DISPLAY_NAME,
        pairing_scheme: str = "http",
        recall_search_provider: str | RecallSearchProvider = "local",
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
    ) -> None:
        self.mobile_token = mobile_token
        self.photo_provider = photo_provider or FixturePhotoProvider()
        self.vision_provider = vision_provider or FixtureVisionProvider()
        self.advertised_endpoint = advertised_endpoint.strip().rstrip("/")
        self.runtime_id = runtime_id.strip() or "hermes"
        self.runtime_display_name = runtime_display_name.strip() or DEV_DISPLAY_NAME
        self.pairing_scheme = pairing_scheme.strip() or "http"
        self.recall_search_provider = (
            build_recall_search_provider(recall_search_provider, endpoint=recall_search_endpoint)
            if isinstance(recall_search_provider, str)
            else recall_search_provider
        )
        self.runtime_store = runtime_store
        self.runtime_store_path = runtime_store_path.strip()
        self.pairing_manager = pairing_manager
        self.trusted_local_tls_required = bool(trusted_local_tls_required)
        self.tls_certificate_label = tls_certificate_label.strip()
        self.tls_public_key_sha256 = _normalized_public_key_sha256(tls_public_key_sha256)
        self.retention_policy = {
            "input_assets_days": int(input_assets_days),
            "output_assets_days": int(output_assets_days),
            "task_history_days": int(task_history_days),
        }
        self.pairing_codes: Dict[str, str] = dict(pairing_codes or {DEV_PAIRING_CODE: self.runtime_display_name})
        self._dev_pairing_sequence = 1
        self._task_sequence = 1
        self._recall_sequence = 1
        self._task_lock = threading.Lock()
        self._recall_lock = threading.Lock()
        self.used_pairing_codes: set[str] = set()
        self.assets: MutableMapping[str, Dict[str, Any]] = {}
        self.tasks: MutableMapping[str, Dict[str, Any]] = {}
        self.recall_items: MutableMapping[str, Dict[str, Any]] = {}
        self.download_requests: List[Dict[str, Any]] = []
        self.request_counts: Dict[str, int] = {
            "health": 0,
            "capabilities": 0,
            "pairing_qr": 0,
            "pairing_dev": 0,
            "pairing_exchange": 0,
            "pairing_revoke": 0,
            "asset_upload": 0,
            "photo_task_create": 0,
            "vision_task_create": 0,
            "image_intake_task_create": 0,
            "intake_task_create": 0,
            "task_status": 0,
            "task_events": 0,
            "task_list": 0,
            "task_cancel": 0,
            "task_approval": 0,
            "asset_download": 0,
            "recall_action": 0,
            "recall_items": 0,
            "recall_search": 0,
            "recall_export": 0,
            "recall_delete": 0,
            "runtime_settings": 0,
        }

    def test_client(self) -> MockClient:
        return MockClient(self)

    def purge_retention(self, *, now_iso: str, dry_run: bool = True) -> Mapping[str, Any]:
        return build_runtime_retention_purge_receipt(
            runtime=self.runtime_id,
            policy=self.retention_policy,
            now_iso=now_iso,
            dry_run=dry_run,
            store=self.runtime_store,
            memory_assets=self.assets,
        )

    def _next_task_id(self) -> str:
        with self._task_lock:
            task_id = f"task_{self._task_sequence:04d}"
            self._task_sequence += 1
            return task_id

    def _next_recall_id(self) -> str:
        with self._recall_lock:
            item_id = f"recall_{self._recall_sequence:04d}"
            self._recall_sequence += 1
            return item_id

    def _asset_created_at(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _asset_store_enabled(self) -> bool:
        return (
            self.runtime_store is not None
            and RuntimeAssetRecord is not None
            and hasattr(self.runtime_store, "upsert_asset")
            and hasattr(self.runtime_store, "get_asset")
            and hasattr(self.runtime_store, "list_assets")
        )

    def _asset_to_runtime_record(self, asset_id: str, asset: Mapping[str, Any]) -> Any:
        raw_metadata = asset.get("metadata", {})
        metadata: Mapping[str, Any]
        if isinstance(raw_metadata, Mapping):
            metadata = dict(raw_metadata)
        elif isinstance(raw_metadata, str) and raw_metadata.strip():
            try:
                decoded_metadata = json.loads(raw_metadata)
            except json.JSONDecodeError:
                decoded_metadata = {}
            metadata = dict(decoded_metadata) if isinstance(decoded_metadata, Mapping) else {}
        else:
            metadata = {}
        return RuntimeAssetRecord(
            asset_id=asset_id,
            role=str(asset.get("role") or ("output" if asset_id.startswith("asset_result_") else "input")),
            created_at=str(asset.get("created_at") or asset.get("retention_created_at") or self._asset_created_at()),
            filename=str(asset.get("filename", "")),
            mime_type=str(asset.get("mime_type", "application/octet-stream")),
            size_bytes=int(asset.get("size_bytes", len(asset.get("bytes", b"")))),
            sha256=str(asset.get("sha256", "")),
            body=bytes(asset.get("bytes", b"")),
            metadata=metadata,
        )

    def _asset_to_mapping(self, record: Any) -> Dict[str, Any]:
        metadata = dict(record.metadata or {})
        return {
            "id": record.asset_id,
            "bytes": record.body,
            "role": record.role,
            "created_at": record.created_at,
            "filename": record.filename,
            "mime_type": record.mime_type,
            "metadata": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            "size_bytes": record.size_bytes,
            "sha256": record.sha256,
        }

    def _save_asset(self, asset_id: str, asset: Mapping[str, Any]) -> None:
        if self._asset_store_enabled():
            self.runtime_store.upsert_asset(self._asset_to_runtime_record(asset_id, asset))
            return
        self.assets[asset_id] = dict(asset)

    def _get_asset(self, asset_id: str) -> Dict[str, Any] | None:
        if self._asset_store_enabled():
            record = self.runtime_store.get_asset(asset_id)
            return self._asset_to_mapping(record) if record is not None else None
        asset = self.assets.get(asset_id)
        return dict(asset) if asset is not None else None

    def _asset_exists(self, asset_id: str) -> bool:
        return self._get_asset(asset_id) is not None

    def _list_assets(self) -> list[tuple[str, Dict[str, Any]]]:
        if self._asset_store_enabled():
            return [(record.asset_id, self._asset_to_mapping(record)) for record in self.runtime_store.list_assets()]
        return [(asset_id, dict(asset)) for asset_id, asset in self.assets.items()]

    def handle(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str],
        json_body: Optional[Mapping[str, Any]] = None,
        form_data: Optional[Mapping[str, Any]] = None,
    ) -> MockResponse:
        query_params: Dict[str, str] = {}
        if "?" in path:
            parsed_url = urlsplit(path)
            path = parsed_url.path
            query_params = {
                key: values[-1]
                for key, values in parse_qs(parsed_url.query, keep_blank_values=True).items()
            }

        if method == "GET" and path == "/mobile/v1/health":
            self._count_request("health")
            return self._json(
                {
                    "ok": True,
                    "runtime": self.runtime_id,
                    "runtime_version": "2026.5.16",
                    "bridge_version": "0.1.0",
                }
            )

        if method == "POST" and path == "/mobile/v1/pairing/exchange":
            self._count_request("pairing_exchange")
            return self._pairing_exchange(json_body or {})

        if method == "GET" and path == "/mobile/v1/pairing/qr":
            self._count_request("pairing_qr")
            return self._json(self._production_pairing_payload(headers))

        if method == "GET" and path == "/mobile/v1/pairing/qr.html":
            self._count_request("pairing_qr")
            return self._production_pairing_page(headers)

        if method == "GET" and path == "/mobile/v1/pairing/dev":
            self._count_request("pairing_dev")
            return self._json(self._development_pairing_payload(headers))

        if method == "GET" and path == "/mobile/v1/pairing/dev.html":
            self._count_request("pairing_dev")
            return self._development_pairing_page(headers)

        auth_error = self._require_auth(headers)
        if auth_error is not None:
            return auth_error

        if method == "POST" and path == "/mobile/v1/pairing/revoke":
            self._count_request("pairing_revoke")
            return self._revoke_current_mobile_token(headers)

        if method == "GET" and path == "/mobile/v1/capabilities":
            self._count_request("capabilities")
            return self._json(self._capabilities())

        if method == "GET" and path == "/mobile/v1/qa/status":
            return self._json(self._qa_status())

        if method == "GET" and path == "/mobile/v1/runtime/settings":
            self._count_request("runtime_settings")
            return self._runtime_settings()

        if method == "GET" and path == "/mobile/v1/tasks":
            self._count_request("task_list")
            return self._runtime_tasks()

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

        if method == "POST" and path == "/mobile/v1/tasks/intake":
            self._count_request("intake_task_create")
            return self._create_universal_intake_task(json_body or {})

        if method == "POST" and path == "/mobile/v1/recall/actions":
            self._count_request("recall_action")
            return self._recall_action(json_body or {})

        if method == "POST" and path == "/mobile/v1/recall/search":
            self._count_request("recall_search")
            return self._recall_search(json_body or {})

        if method == "GET" and path == "/mobile/v1/recall/items":
            self._count_request("recall_items")
            raw_limit = query_params.get("limit", "").strip()
            limit: Optional[int] = None
            if raw_limit:
                try:
                    limit = max(int(raw_limit), 0)
                except ValueError:
                    limit = None
            return self._recall_items(
                query=query_params.get("query", "").strip(),
                limit=limit,
            )

        if method == "GET" and path == "/mobile/v1/recall/export":
            self._count_request("recall_export")
            return self._recall_export()

        if method == "DELETE" and path.startswith("/mobile/v1/recall/items/"):
            self._count_request("recall_delete")
            item_id = unquote(path.removeprefix("/mobile/v1/recall/items/"))
            return self._delete_recall_item(item_id)

        if method == "POST" and path.startswith("/mobile/v1/tasks/") and path.endswith("/cancel"):
            self._count_request("task_cancel")
            task_id = unquote(path.removeprefix("/mobile/v1/tasks/").removesuffix("/cancel"))
            return self._cancel_runtime_task(task_id)

        if method == "POST" and path.startswith("/mobile/v1/tasks/") and path.endswith("/approval"):
            self._count_request("task_approval")
            task_id = unquote(path.removeprefix("/mobile/v1/tasks/").removesuffix("/approval"))
            return self._approve_runtime_task(task_id, json_body or {})

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
        authorization = headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return self._error("unauthorized", "The mobile token is missing or invalid.", 401)
        token = authorization.removeprefix("Bearer ").strip()
        if self.pairing_manager is not None:
            if not self.pairing_manager.is_mobile_token_active(token):
                return self._error("unauthorized", "The mobile token is missing or invalid.", 401)
            return None
        if token != self.mobile_token:
            return self._error("unauthorized", "The mobile token is missing or invalid.", 401)
        return None

    def _pairing_exchange(self, payload: Mapping[str, Any]) -> MockResponse:
        pairing_code = str(payload.get("pairing_code", ""))
        if self.pairing_manager is not None:
            result = self.pairing_manager.exchange_pairing_code(
                pairing_code,
                device_name=str(payload.get("device_name", "")),
                device_public_id=str(payload.get("device_public_id", "")),
            )
            if not result.ok:
                status_code = 409 if result.error_code == "pairing_already_used" else 404
                return self._error(result.error_code, result.error_message, status_code)
            return self._json(result.to_mobile_bridge())

        display_name = self.pairing_codes.get(pairing_code)
        if display_name is None:
            return self._error("pairing_expired", "The pairing code is missing or expired.", 404)
        if pairing_code in self.used_pairing_codes:
            return self._error("pairing_already_used", "The pairing code has already been used.", 409)

        self.used_pairing_codes.add(pairing_code)
        return self._json(
            {
                "endpoint_id": f"endpoint_mock_{self.runtime_id}",
                "display_name": display_name,
                "runtime": self.runtime_id,
                "runtime_version": "2026.5.16",
                "mobile_token": self.mobile_token,
                "token_expires_at": None,
            }
        )

    def _production_pairing_payload(self, headers: Mapping[str, str]) -> Mapping[str, Any]:
        if self.pairing_manager is None:
            return self._development_pairing_payload(headers)
        host = headers.get("Host") or "127.0.0.1:8765"
        endpoint = self.advertised_endpoint or f"{self.pairing_scheme}://{host}"
        session = self.pairing_manager.issue_pairing_session(
            endpoint=endpoint,
            runtime=self.runtime_id,
            display_name=self.runtime_display_name,
        )
        return self.pairing_manager.pairing_payload(session)

    def _production_pairing_page(self, headers: Mapping[str, str]) -> MockResponse:
        payload = self._production_pairing_payload(headers)
        payload_json = json.dumps(payload, indent=2, sort_keys=True)
        compact_payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        qr_data_uri = self._development_pairing_qr_data_uri(compact_payload_json)
        escaped_payload = html.escape(payload_json)
        escaped_payload_attribute = html.escape(compact_payload_json, quote=True)
        qr_markup = ""
        if qr_data_uri:
            qr_markup = f"""
    <figure class="pairing-qr-card">
      <div class="qr-shell">
        <img class="pairing-qr" src="{qr_data_uri}" alt="Pairing QR code for Agent Pocket" data-pairing-payload="{escaped_payload_attribute}">
      </div>
    </figure>
"""
        body = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Agent Pocket Production Pairing</title></head>
<body>
  <main>
    <h1>Kaka Mobile Bridge Pairing</h1>
{qr_markup}
    <pre>{escaped_payload}</pre>
  </main>
</body>
</html>
"""
        return MockResponse(
            status_code=200,
            content_type="text/html; charset=utf-8",
            data=body.encode("utf-8"),
        )

    def _revoke_current_mobile_token(self, headers: Mapping[str, str]) -> MockResponse:
        authorization = headers.get("Authorization", "")
        token = authorization.removeprefix("Bearer ").strip()
        if self.pairing_manager is None:
            return self._json({"status": "revoked"})
        if not self.pairing_manager.revoke_mobile_token(token):
            return self._error("unauthorized", "The mobile token is missing or invalid.", 401)
        return self._json({"status": "revoked"})

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
        payload: Dict[str, Any] = {
            "version": 1,
            "endpoint": endpoint,
            "runtime": self.runtime_id,
            "display_name": self.pairing_codes.get(pairing_code, self.runtime_display_name),
            "pairing_code": pairing_code,
            "expires_at": "2099-01-01T00:00:00Z",
        }
        payload.update(self._development_pairing_tls_metadata())
        return payload

    def _development_pairing_tls_metadata(self) -> Mapping[str, Any]:
        metadata: Dict[str, Any] = {}
        if self.trusted_local_tls_required:
            metadata["trusted_local_tls_required"] = True
        if self.tls_certificate_label:
            metadata["tls_certificate_label"] = self.tls_certificate_label
        if self.tls_public_key_sha256:
            metadata["tls_public_key_sha256"] = self.tls_public_key_sha256
        return metadata

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
                    "capabilities": ["photo_edit", "vision", "image_intake", "intake"],
                }
            ],
            "tasks": {
                "photo_edit": {
                    "max_upload_mb": 30,
                    "accepted_mime_types": ["image/jpeg"],
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
                    "return_variants_max": 2,
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
                "intake": {
                    "accepted_types": ["text", "url", "image", "pdf"],
                    "provider": "heuristic_universal_intake",
                    "supports_context_snapshot": True,
                    "supports_voice_followup": True,
                    "supports_recall_actions": True,
                    "supports_sse": False,
                },
            },
            "retention": dict(self.retention_policy),
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
        self._save_asset(asset_id, {
            "id": asset_id,
            "bytes": raw,
            "role": "input",
            "created_at": self._asset_created_at(),
            "filename": filename,
            "mime_type": mime_type,
            "metadata": form_data.get("metadata", "{}"),
            "size_bytes": len(raw),
            "sha256": digest,
        })
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
        source_asset = self._get_asset(asset_id)
        if source_asset is None:
            return self._error("not_found", "The source asset does not exist.", 404)

        task_id = self._next_task_id()
        provider_name = self._provider_name()
        try:
            provider_variants = self.photo_provider.edit(
                source_bytes=source_asset["bytes"],
                style=str(payload.get("style", "natural_enhance")),
                instruction=str(payload.get("instruction", "")),
                return_variants=int(payload.get("return_variants", 1)),
            )
        except Exception:
            task = {
                "task_id": task_id,
                "status": "failed",
                "progress": 1.0,
                "message": "The photo provider failed. Check Hermes provider credentials or logs.",
                "failure_code": "provider_failed",
                "provider": provider_name,
            }
            self.tasks[task_id] = task
            self._store_runtime_task(task)
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
            self._save_asset(result_asset_id, {
                "id": result_asset_id,
                "bytes": variant_bytes,
                "role": "output",
                "created_at": self._asset_created_at(),
                "filename": f"variant_{index}.png",
                "mime_type": mime_type,
                "metadata": json.dumps(
                    {"variant_id": provider_variant.get("id", f"variant_{index}"), "recipe": variant_recipe_metadata}
                    if isinstance(variant_recipe_metadata, Mapping)
                    else {}
                ),
                "size_bytes": len(variant_bytes),
                "sha256": hashlib.sha256(variant_bytes).hexdigest(),
            })
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
        self._store_runtime_task(task)
        return self._json(
            {
                "task_id": task_id,
                "status": "queued",
                "events_url": f"/mobile/v1/tasks/{task_id}/events",
            }
        )

    def _create_vision_task(self, payload: Mapping[str, Any]) -> MockResponse:
        asset_id = str(payload.get("asset_id", ""))
        source_asset = self._get_asset(asset_id)
        if source_asset is None:
            return self._error("not_found", "The source asset does not exist.", 404)

        mode = str(payload.get("mode", ""))
        if mode not in {"scan", "identify", "translate", "food"}:
            return self._error("vision_unavailable", "The requested vision mode is not available.", 400)

        task_id = self._next_task_id()
        provider_name = self._vision_provider_name()
        try:
            vision_result = _sanitize_vision_result(
                self.vision_provider.analyze(
                    source_bytes=source_asset["bytes"],
                    mode=mode,
                    instruction=str(payload.get("instruction", "")),
                    locale=payload.get("locale"),
                )
            )
        except Exception:
            task = {
                "task_id": task_id,
                "status": "failed",
                "progress": 1.0,
                "message": "The vision provider failed. Check Hermes provider credentials or logs.",
                "failure_code": "vision_failed",
                "provider": provider_name,
                "result_type": "vision",
            }
            self.tasks[task_id] = task
            self._store_runtime_task(task)
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
        task = {
            "task_id": task_id,
            "status": "completed",
            "progress": 1.0,
            "message": "Completed.",
            "result_type": "vision",
            "vision": vision_result,
            "provider": provider_name,
        }
        self.tasks[task_id] = task
        self._store_runtime_task(task)
        return self._json(
            {
                "task_id": task_id,
                "status": "queued",
                "events_url": f"/mobile/v1/tasks/{task_id}/events",
            }
        )

    def _create_image_intake_task(self, payload: Mapping[str, Any]) -> MockResponse:
        asset_id = str(payload.get("asset_id", ""))
        if not self._asset_exists(asset_id):
            return self._error("not_found", "The source asset does not exist.", 404)

        task_id = self._next_task_id()
        try:
            image_intake = self._build_image_intake_result_for_asset(asset_id, payload)
        except Exception:
            task = {
                "task_id": task_id,
                "status": "failed",
                "progress": 1.0,
                "message": "The image intake provider failed. Check runtime logs.",
                "failure_code": "image_intake_failed",
                "provider": "heuristic_image_intake",
                "result_type": "image_intake",
            }
            self.tasks[task_id] = task
            self._store_runtime_task(task)
            return self._json(
                {
                    "task_id": task_id,
                    "status": "queued",
                    "events_url": f"/mobile/v1/tasks/{task_id}/events",
                }
            )

        task = {
            "task_id": task_id,
            "status": "completed",
            "progress": 1.0,
            "message": "Completed.",
            "result_type": "image_intake",
            "image_intake": image_intake,
            "provider": "heuristic_image_intake",
        }
        self.tasks[task_id] = task
        self._store_runtime_task(task)
        return self._json(
            {
                "task_id": task_id,
                "status": "queued",
                "events_url": f"/mobile/v1/tasks/{task_id}/events",
            }
        )

    def _create_universal_intake_task(self, payload: Mapping[str, Any]) -> MockResponse:
        intake_type = str(payload.get("type", payload.get("kind", ""))).strip().lower()
        if intake_type not in {"text", "url", "image", "pdf"}:
            return self._error("intake_unavailable", "The requested intake type is not available.", 400)

        asset_id = self._source_asset_id(payload)
        if intake_type in {"image", "pdf"}:
            if not asset_id:
                return self._error("invalid_intake_payload", "The intake source must include an asset_id.", 400)
            if not self._asset_exists(asset_id):
                return self._error("not_found", "The source asset does not exist.", 404)

        if intake_type == "text" and not self._source_text(payload):
            return self._error("invalid_intake_payload", "Text intake requires a non-empty text field.", 400)
        if intake_type == "url" and not self._source_url(payload):
            return self._error("invalid_intake_payload", "URL intake requires a non-empty url field.", 400)

        task_id = self._next_task_id()
        try:
            intake = self._build_universal_intake_result(intake_type, payload)
        except Exception:
            task = {
                "task_id": task_id,
                "status": "failed",
                "progress": 1.0,
                "message": "The universal intake provider failed. Check runtime logs.",
                "failure_code": "intake_failed",
                "provider": "heuristic_universal_intake",
                "result_type": "intake",
            }
            self.tasks[task_id] = task
            self._store_runtime_task(task)
            return self._task_create_response(task_id)

        task = {
            "task_id": task_id,
            "status": "completed",
            "progress": 1.0,
            "message": "Completed.",
            "result_type": "intake",
            "intake": intake,
            "provider": "heuristic_universal_intake",
        }
        image_intake = intake.get("image_intake")
        if isinstance(image_intake, Mapping):
            task["image_intake"] = image_intake
        self.tasks[task_id] = task
        self._store_runtime_task(task)
        return self._task_create_response(task_id)

    def _recall_action(self, payload: Mapping[str, Any]) -> MockResponse:
        action = str(payload.get("action", "")).strip()
        summary = str(payload.get("user_visible_summary", "")).strip()
        if action not in {"remember", "use_once", "forget"}:
            return self._error("invalid_recall_action", "The recall action must be remember, use_once, or forget.", 400)
        if not summary:
            return self._error("invalid_recall_payload", "Recall actions require a user_visible_summary.", 400)

        if action == "remember":
            item = self._remember_recall_item(summary=summary, payload=payload)
            return self._json(
                {
                    "action": "remember",
                    "status": "remembered",
                    "item": item,
                    "deleted_item_ids": [],
                    "deleted_index_ids": [],
                }
            )

        if action == "use_once":
            return self._json(
                {
                    "action": "use_once",
                    "status": "used_once",
                    "item": None,
                    "deleted_item_ids": [],
                    "deleted_index_ids": [],
                }
            )

        deleted_item_ids, deleted_index_ids = self._forget_recall_items_by_source(payload)
        return self._json(
            {
                "action": "forget",
                "status": "forgotten",
                "item": None,
                "deleted_item_ids": deleted_item_ids,
                "deleted_index_ids": deleted_index_ids,
            }
        )

    def _remember_recall_item(self, summary: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        item_id = self._next_recall_id()
        created_at = "2026-06-05T00:00:00Z"
        provenance = self._recall_provenance(payload)
        if self.runtime_store is not None and RuntimeRecallItem is not None:
            item = RuntimeRecallItem(
                item_id=item_id,
                summary=summary,
                created_at=created_at,
                source_task_id=str(provenance.get("source_task_id", "")),
                source_inbox_item_id=str(provenance.get("source_inbox_item_id", "")),
                source_surface=str(payload.get("source_surface", "")).strip(),
            )
            self.runtime_store.remember_recall(item, index_ids=[f"embedding_{item_id}"])
            return item.to_mobile_bridge()

        item = {
            "item_id": item_id,
            "summary": summary,
            "created_at": created_at,
            "provenance": provenance,
        }
        with self._recall_lock:
            self.recall_items[item_id] = item
        return dict(item)

    def _recall_provenance(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        provenance: Dict[str, Any] = {}
        source_task_id = str(payload.get("source_task_id", "")).strip()
        source_inbox_item_id = str(payload.get("source_inbox_item_id", "")).strip()
        if source_task_id:
            provenance["source_task_id"] = source_task_id
        if source_inbox_item_id:
            provenance["source_inbox_item_id"] = source_inbox_item_id
        return provenance

    def _forget_recall_items_by_source(self, payload: Mapping[str, Any]) -> tuple[List[str], List[str]]:
        source_task_id = str(payload.get("source_task_id", "")).strip()
        source_inbox_item_id = str(payload.get("source_inbox_item_id", "")).strip()
        if not source_task_id and not source_inbox_item_id:
            return [], []

        if self.runtime_store is not None and hasattr(self.runtime_store, "delete_recall_by_source"):
            receipt = self.runtime_store.delete_recall_by_source(
                source_task_id=source_task_id,
                source_inbox_item_id=source_inbox_item_id,
            )
            return list(receipt.deleted_item_ids), list(receipt.deleted_index_ids)

        deleted_item_ids: List[str] = []
        with self._recall_lock:
            for item_id, item in list(self.recall_items.items()):
                provenance = item.get("provenance")
                if not isinstance(provenance, Mapping):
                    continue
                matches_task = not source_task_id or provenance.get("source_task_id") == source_task_id
                matches_inbox = not source_inbox_item_id or provenance.get("source_inbox_item_id") == source_inbox_item_id
                if matches_task and matches_inbox:
                    deleted_item_ids.append(item_id)
                    del self.recall_items[item_id]
        deleted_index_ids = [f"embedding_{deleted_item_id}" for deleted_item_id in deleted_item_ids]
        return deleted_item_ids, deleted_index_ids

    def _recall_items(self, query: str = "", limit: Optional[int] = None) -> MockResponse:
        if self.runtime_store is not None:
            items = self.runtime_store.list_recall(query=query, limit=limit)
            return self._json({"items": [item.to_mobile_bridge() for item in items]})

        normalized_query = query.lower()
        with self._recall_lock:
            items = [
                dict(item)
                for _, item in sorted(self.recall_items.items(), reverse=True)
            ]
        if normalized_query:
            items = [
                item
                for item in items
                if normalized_query in str(item.get("summary", "")).lower()
            ]
        if limit is not None:
            items = items[:limit]
        return self._json({"items": items})

    def _recall_search(self, payload: Mapping[str, Any]) -> MockResponse:
        query = str(payload.get("query", "")).strip()
        limit = self._parse_positive_limit(payload.get("limit"), default=10)
        if not query:
            return self._error("invalid_recall_payload", "Recall search requires a non-empty query.", 400)

        retrieval_mode = self._semantic_recall_mode()
        if self.runtime_store is not None and hasattr(self.runtime_store, "search_recall_semantic"):
            results = self.runtime_store.search_recall_semantic(query, limit)
            return self._json(
                {
                    "query": query,
                    "mode": "semantic",
                    "retrieval_mode": retrieval_mode,
                    "items": [_safe_recall_search_result(result) for result in results],
                }
            )

        results = self._search_memory_recall(query=query, limit=limit)
        return self._json(
            {
                "query": query,
                "mode": "semantic",
                "retrieval_mode": retrieval_mode,
                "items": results,
            }
        )

    def _search_memory_recall(self, query: str, limit: int) -> List[Dict[str, Any]]:
        with self._recall_lock:
            items = [dict(item) for item in self.recall_items.values()]
        recall_items = [_MemoryRecallItem(item) for item in items]
        results = self.recall_search_provider.search(query=query, items=recall_items, limit=limit)
        return [_safe_recall_search_result(result.to_mobile_bridge()) for result in results]

    def _runtime_settings(self) -> MockResponse:
        has_runtime_store = self.runtime_store is not None
        semantic_mode = self._semantic_recall_mode()
        semantic_recall: Dict[str, Any] = {
            "available": True,
            "owner": "runtime" if semantic_mode == "provider_backed" or (
                has_runtime_store and hasattr(self.runtime_store, "search_recall_semantic")
            ) else "mock_bridge",
            "mode": semantic_mode,
        }
        if semantic_mode == "provider_backed":
            semantic_recall["provider_label"] = "Runtime provider"
        return self._json(
            {
                "recall_store": {
                    "enabled": has_runtime_store,
                    "owner": "runtime" if has_runtime_store else "mock_bridge",
                    "label": "Local Kaka Recall and task store" if has_runtime_store else "In-memory development store",
                    "phone_can_change": False,
                },
                "semantic_recall": semantic_recall,
                "retention": self._capabilities()["retention"],
                "connection_security": self._connection_security_summary(),
            }
        )

    def _connection_security_summary(self) -> Mapping[str, Any]:
        if self.pairing_manager is not None:
            return self.pairing_manager.phone_safe_security_summary()
        return {
            "pairing_code_ttl_seconds": None,
            "mobile_token_ttl_seconds": None,
            "mobile_token_revocation_supported": False,
            "trusted_local_tls_required": self.trusted_local_tls_required,
            "tls_trust_state": "development_http",
            "tls_certificate_label": self.tls_certificate_label,
            **({"tls_public_key_sha256": self.tls_public_key_sha256} if self.tls_public_key_sha256 else {}),
        }

    def _semantic_recall_mode(self) -> str:
        provider_mode = str(getattr(self.recall_search_provider, "provider_mode", "")).strip()
        if provider_mode == "provider_backed":
            return "provider_backed"
        if self.runtime_store is not None:
            store_provider = getattr(self.runtime_store, "recall_search_provider", None)
            store_provider_mode = str(getattr(store_provider, "provider_mode", "")).strip()
            if store_provider_mode == "provider_backed":
                return "provider_backed"
        return "local_deterministic"

    def _parse_positive_limit(self, value: Any, default: int) -> int:
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            return default

    def _recall_export(self) -> MockResponse:
        if self.runtime_store is not None:
            return self._json(self.runtime_store.export_recall())

        with self._recall_lock:
            items = [
                dict(item)
                for _, item in sorted(self.recall_items.items(), reverse=True)
            ]
        return self._json(
            build_recall_export_artifact(
                items=items,
                generated_at="2026-06-05T00:00:00Z",
            )
        )

    def _delete_recall_item(self, item_id: str) -> MockResponse:
        if self.runtime_store is not None:
            return self._json(self.runtime_store.delete_recall(item_id).to_mobile_bridge())

        deleted_item_ids: List[str] = []
        with self._recall_lock:
            if item_id in self.recall_items:
                del self.recall_items[item_id]
                deleted_item_ids.append(item_id)
        deleted_index_ids = [f"embedding_{deleted_item_id}" for deleted_item_id in deleted_item_ids]
        return self._json(
            {
                "status": "forgotten",
                "deleted_item_ids": deleted_item_ids,
                "deleted_index_ids": deleted_index_ids,
            }
        )

    def _runtime_tasks(self) -> MockResponse:
        if self.runtime_store is not None:
            tasks = [self._stored_task_to_mobile_bridge(task) for task in self.runtime_store.list_tasks()]
            return self._json({"tasks": self._sort_runtime_task_summaries(tasks)})

        with self._task_lock:
            tasks = [
                self._runtime_task_summary(task)
                for _, task in self.tasks.items()
            ]
        return self._json({"tasks": self._sort_runtime_task_summaries(tasks)})

    def _cancel_runtime_task(self, task_id: str) -> MockResponse:
        if self.runtime_store is not None:
            task = self.runtime_store.get_task(task_id)
            if task is None:
                return self._error("not_found", "The runtime task does not exist.", 404)
            summary = self._update_stored_task(
                task,
                status="cancelled",
                progress=1.0,
                message="Cancelled.",
                event_type="task_cancelled",
            )
            return self._json({"status": "cancelled", "task": summary})

        with self._task_lock:
            task = self.tasks.get(task_id)
            if task is None:
                return self._error("not_found", "The runtime task does not exist.", 404)
            task["status"] = "cancelled"
            task["progress"] = 1.0
            task["message"] = "Cancelled."
            task["updated_at"] = "2026-06-05T09:35:00Z"
            summary = self._runtime_task_summary(task)
        return self._json({"status": "cancelled", "task": summary})

    def _approve_runtime_task(self, task_id: str, payload: Mapping[str, Any]) -> MockResponse:
        raw_action = payload.get("action")
        if not isinstance(raw_action, str):
            return self._error("invalid_task_approval", "Task approval action must be approve or reject.", 400)
        action = raw_action.strip()
        if action not in {"approve", "reject"}:
            return self._error("invalid_task_approval", "Task approval action must be approve or reject.", 400)
        if self.runtime_store is not None:
            task = self.runtime_store.get_task(task_id)
            if task is None:
                return self._error("not_found", "The runtime task does not exist.", 404)
            if action == "approve":
                summary = self._update_stored_task(
                    task,
                    status="running",
                    progress=max(self._stored_task_progress(task), 0.5),
                    message="Approved.",
                    event_type="task_approved",
                )
                return self._json({"status": "approved", "task": summary})
            summary = self._update_stored_task(
                task,
                status="cancelled",
                progress=1.0,
                message="Rejected.",
                event_type="task_rejected",
            )
            return self._json({"status": "rejected", "task": summary})

        with self._task_lock:
            task = self.tasks.get(task_id)
            if task is None:
                return self._error("not_found", "The runtime task does not exist.", 404)
            if action == "approve":
                task["status"] = "running"
                task["progress"] = max(float(task.get("progress", 0.0)), 0.5)
                task["message"] = "Approved."
                response_status = "approved"
            else:
                task["status"] = "cancelled"
                task["progress"] = 1.0
                task["message"] = "Rejected."
                response_status = "rejected"
            task["updated_at"] = "2026-06-05T09:35:00Z"
            summary = self._runtime_task_summary(task)
        return self._json({"status": response_status, "task": summary})

    def _runtime_task_summary(self, task: Mapping[str, Any]) -> Dict[str, Any]:
        task_id = str(task.get("task_id", task.get("id", "")))
        title = str(task.get("title", "")).strip()
        if not title:
            intake = task.get("intake")
            image_intake = task.get("image_intake")
            vision = task.get("vision")
            if isinstance(intake, Mapping):
                title = str(intake.get("title", "")).strip()
            elif isinstance(image_intake, Mapping):
                title = str(image_intake.get("title", "")).strip()
            elif isinstance(vision, Mapping):
                title = str(vision.get("title", "")).strip()
        if not title:
            title = "Runtime task"
        return {
            "id": task_id,
            "title": title,
            "status": str(task.get("status", "queued")),
            "progress": float(task.get("progress", 0.0)),
            "message": task.get("message"),
            "updated_at": str(task.get("updated_at", "2026-06-05T09:30:00Z")),
        }

    def _task_result_metadata(self, task: Mapping[str, Any]) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        variants = self._safe_task_variants(task.get("variants"))
        if variants:
            metadata["variants"] = variants
        for key in (
            "provider",
            "result_type",
            "explanation",
            "recipe_metadata",
            "renderer",
            "composition",
            "qa",
            "crop",
            "share_caption",
            "recipe_summary",
            "safety",
            "upscale",
        ):
            value = _safe_json_value(task.get(key))
            if value not in (None, "", [], {}):
                metadata[key] = value
        return metadata

    def _safe_task_variants(self, raw_variants: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw_variants, list):
            return []
        variants: List[Dict[str, Any]] = []
        for raw_variant in raw_variants:
            if not isinstance(raw_variant, Mapping):
                continue
            variant: Dict[str, Any] = {}
            for key in ("id", "label", "asset_id"):
                value = raw_variant.get(key)
                if isinstance(value, str) and value:
                    variant[key] = value
            if variant.get("asset_id"):
                variants.append(variant)
        return variants

    def _sort_runtime_task_summaries(self, tasks: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        waiting = [dict(task) for task in tasks if task.get("status") == "waiting_for_approval"]
        other = [dict(task) for task in tasks if task.get("status") != "waiting_for_approval"]
        waiting.sort(key=lambda task: str(task.get("updated_at", "")), reverse=True)
        other.sort(key=lambda task: str(task.get("updated_at", "")), reverse=True)
        return waiting + other

    def _store_runtime_task(self, task: Mapping[str, Any]) -> None:
        if self.runtime_store is None or RuntimeTaskRecord is None:
            return
        summary = self._runtime_task_summary(task)
        task_id = str(summary["id"])
        metadata = {
            "progress": summary["progress"],
            "message": _safe_json_value(summary.get("message")),
        }
        for key in ("result_type", "provider"):
            value = _safe_json_value(task.get(key, ""))
            if value not in (None, "", [], {}):
                metadata[key] = value
        metadata.update(self._task_result_metadata(task))
        record = RuntimeTaskRecord(
            task_id=task_id,
            title=str(summary["title"]),
            status=str(summary["status"]),
            updated_at=str(summary["updated_at"]),
            detail=str(summary.get("message") or ""),
            approval_required=summary.get("status") == "waiting_for_approval",
            metadata=metadata,
        )
        self.runtime_store.upsert_task(record)
        self._append_stored_task_event(
            event_id=f"event_{task_id}_{summary['status']}",
            task_id=task_id,
            event_type="task_status",
            message=str(summary.get("message") or "Task status changed."),
            created_at=str(summary["updated_at"]),
            metadata={"status": summary["status"], "progress": summary["progress"]},
        )

    def _stored_task_to_mobile_bridge(self, task: Any) -> Dict[str, Any]:
        metadata = dict(task.metadata or {})
        progress = self._progress_from_metadata(metadata, str(task.status))
        message = metadata.get("message")
        if message in (None, ""):
            message = task.detail or None
        return {
            "id": task.task_id,
            "title": task.title,
            "status": task.status,
            "progress": progress,
            "message": message,
            "updated_at": task.updated_at,
        }

    def _stored_task_detail_to_mobile_bridge(self, task: Any) -> Dict[str, Any]:
        metadata = dict(task.metadata or {})
        body = self._stored_task_to_mobile_bridge(task)
        for key in (
            "provider",
            "result_type",
            "explanation",
            "recipe_metadata",
            "renderer",
            "composition",
            "qa",
            "crop",
            "share_caption",
            "recipe_summary",
            "safety",
            "upscale",
        ):
            value = metadata.get(key)
            if value not in (None, "", [], {}):
                body[key] = value
        variants = self._safe_task_variants(metadata.get("variants"))
        if variants:
            body["variants"] = [
                {
                    **variant,
                    "download_url": f"/mobile/v1/assets/{variant['asset_id']}/download",
                }
                for variant in variants
            ]
        return body

    def _stored_task_progress(self, task: Any) -> float:
        return self._progress_from_metadata(dict(task.metadata or {}), str(task.status))

    def _progress_from_metadata(self, metadata: Mapping[str, Any], status: str) -> float:
        try:
            return float(metadata.get("progress", 0.0))
        except (TypeError, ValueError):
            pass
        if status in {"completed", "failed", "cancelled"}:
            return 1.0
        if status == "running":
            return 0.5
        return 0.0

    def _update_stored_task(
        self,
        task: Any,
        status: str,
        progress: float,
        message: str,
        event_type: str,
    ) -> Dict[str, Any]:
        metadata = dict(task.metadata or {})
        metadata["progress"] = progress
        metadata["message"] = message
        updated_at = "2026-06-05T09:35:00Z"
        updated = RuntimeTaskRecord(
            task_id=task.task_id,
            title=task.title,
            status=status,
            updated_at=updated_at,
            detail=message,
            approval_required=status == "waiting_for_approval",
            metadata=metadata,
        )
        self.runtime_store.upsert_task(updated)
        self._append_stored_task_event(
            event_id=f"event_{task.task_id}_{event_type}",
            task_id=task.task_id,
            event_type=event_type,
            message=message,
            created_at=updated_at,
            metadata={"status": status, "progress": progress},
        )
        return self._stored_task_to_mobile_bridge(updated)

    def _append_stored_task_event(
        self,
        event_id: str,
        task_id: str,
        event_type: str,
        message: str,
        created_at: str,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if self.runtime_store is None or RuntimeTaskEvent is None:
            return
        self.runtime_store.append_task_event(
            RuntimeTaskEvent(
                event_id=event_id,
                task_id=task_id,
                type=event_type,
                message=message,
                created_at=created_at,
                metadata=metadata or {},
            )
        )

    def _build_universal_intake_result(self, intake_type: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        metadata = self._universal_intake_metadata(payload)
        if intake_type == "text":
            text_value = self._source_text(payload)
            result = {
                "title": "Shared text ready",
                "summary": f"Kaka received {len(text_value)} characters of text from {metadata.get('source_app', 'an app')}.",
                "suggestions": [
                    self._intake_suggestion("summarize", "Summarize"),
                    self._intake_suggestion("extract_tasks", "Extract Tasks"),
                    self._intake_suggestion("remember", "Remember", requires_confirmation=True),
                ],
            }
        elif intake_type == "url":
            url_value = self._source_url(payload)
            result = {
                "title": "Shared link ready",
                "summary": f"Kaka received a link from {metadata.get('source_app', 'an app')}: {url_value}",
                "suggestions": [
                    self._intake_suggestion("summarize", "Summarize"),
                    self._intake_suggestion("remember", "Remember", requires_confirmation=True),
                    self._intake_suggestion("forget", "Forget", requires_confirmation=True),
                ],
            }
        elif intake_type == "image":
            asset_id = self._source_asset_id(payload)
            image_intake = self._build_image_intake_result_for_asset(asset_id, payload)
            result = {
                "title": image_intake.get("title", "Image ready"),
                "summary": image_intake.get("summary", "Kaka can inspect this image and suggest visual skills."),
                "suggestions": [
                    self._intake_suggestion("open_image_conversation", "Open Image Conversation"),
                    self._intake_suggestion("forget", "Forget", requires_confirmation=True),
                ],
                "image_intake": image_intake,
            }
        else:
            filename = str(metadata.get("filename") or "PDF").strip() or "PDF"
            page_count = metadata.get("page_count")
            pages = f" with {page_count} pages" if page_count else ""
            result = {
                "title": "PDF ready",
                "summary": f"Kaka received {filename}{pages} for local runtime intake.",
                "suggestions": [
                    self._intake_suggestion("summarize", "Summarize"),
                    self._intake_suggestion("extract_tasks", "Extract Tasks"),
                    self._intake_suggestion("forget", "Forget", requires_confirmation=True),
                ],
            }

        result.update(
            {
                "kind": intake_type,
                "type": intake_type,
                "metadata": metadata,
            }
        )
        return result

    def _build_image_intake_result_for_asset(self, asset_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        source_asset = self._get_asset(asset_id)
        if source_asset is None:
            raise KeyError(asset_id)
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
        return image_intake

    def _source_mapping(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        source = payload.get("source")
        return source if isinstance(source, Mapping) else {}

    def _source_text(self, payload: Mapping[str, Any]) -> str:
        source = self._source_mapping(payload)
        return str(payload.get("text", source.get("text", ""))).strip()

    def _source_url(self, payload: Mapping[str, Any]) -> str:
        source = self._source_mapping(payload)
        return str(payload.get("url", source.get("url", ""))).strip()

    def _source_asset_id(self, payload: Mapping[str, Any]) -> str:
        source = self._source_mapping(payload)
        return str(payload.get("asset_id", source.get("asset_id", ""))).strip()

    def _universal_intake_metadata(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        source = dict(self._source_mapping(payload))
        metadata: Dict[str, Any] = {}
        for key in (
            "asset_id",
            "filename",
            "mime_type",
            "page_count",
            "text",
            "url",
        ):
            value = payload.get(key, source.get(key))
            if value not in (None, ""):
                metadata[key] = value
        for key in (
            "note",
            "locale",
            "preferred_profile_id",
            "source_app",
            "received_at",
        ):
            value = payload.get(key)
            if value not in (None, ""):
                metadata[key] = value
        context_snapshot = payload.get("context_snapshot")
        if isinstance(context_snapshot, Mapping):
            sanitized_snapshot = self._sanitized_context_snapshot(context_snapshot)
            if sanitized_snapshot:
                metadata["context_snapshot"] = sanitized_snapshot

        asset_id = self._source_asset_id(payload)
        asset = self._get_asset(asset_id)
        if asset is not None:
            metadata.setdefault("asset_id", asset_id)
            metadata.setdefault("filename", asset.get("filename"))
            metadata.setdefault("mime_type", asset.get("mime_type"))
            metadata.setdefault("size_bytes", asset.get("size_bytes"))
            metadata.setdefault("sha256", asset.get("sha256"))
            raw_asset_metadata = asset.get("metadata")
            if isinstance(raw_asset_metadata, str) and raw_asset_metadata.strip():
                try:
                    decoded_asset_metadata = json.loads(raw_asset_metadata)
                except json.JSONDecodeError:
                    decoded_asset_metadata = None
                if isinstance(decoded_asset_metadata, Mapping):
                    metadata.setdefault("asset_metadata", dict(decoded_asset_metadata))
                    if "page_count" in decoded_asset_metadata:
                        metadata.setdefault("page_count", decoded_asset_metadata["page_count"])
        return {key: value for key, value in metadata.items() if value is not None}

    def _sanitized_context_snapshot(self, context_snapshot: Mapping[str, Any]) -> Dict[str, str]:
        sanitized: Dict[str, str] = {}
        for key in self.CONTEXT_SNAPSHOT_ALLOWED_FIELDS:
            value = context_snapshot.get(key)
            if isinstance(value, str) and value.strip():
                sanitized[key] = value
        return sanitized

    def _intake_suggestion(
        self,
        suggestion_id: str,
        label: str,
        requires_confirmation: bool = False,
    ) -> Mapping[str, Any]:
        return {
            "id": suggestion_id,
            "label": label,
            "requires_confirmation": requires_confirmation,
            "is_available": True,
        }

    def _task_create_response(self, task_id: str) -> MockResponse:
        return self._json(
            {
                "task_id": task_id,
                "status": "queued",
                "status_url": f"/mobile/v1/tasks/{task_id}",
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
        if self.runtime_store is not None:
            task = self.runtime_store.get_task(task_id)
            if task is None:
                return self._error("not_found", "The task does not exist.", 404)
            body = self._stored_task_detail_to_mobile_bridge(task)
            body["task_id"] = task.task_id
            return self._json(body)

        task = self.tasks.get(task_id)
        if task is None:
            return self._error("not_found", "The task does not exist.", 404)
        return self._json(task)

    def _task_events(self, task_id: str) -> MockResponse:
        if self.runtime_store is not None:
            task = self.runtime_store.get_task(task_id)
            if task is None:
                return self._error("not_found", "The task does not exist.", 404)
            events = self.runtime_store.list_task_events(task_id)
            if events:
                chunks: List[str] = []
                for event in events:
                    metadata = dict(event.metadata or {})
                    progress = self._progress_from_metadata(metadata, str(task.status))
                    message = event.message or metadata.get("message")
                    chunks.append(
                        "event: task.progress\n"
                        f"data: {json.dumps({'progress': progress, 'message': message})}\n\n"
                    )
                if task.status in {"completed", "failed", "cancelled"}:
                    variant_count = len(self._safe_task_variants(dict(task.metadata or {}).get("variants")))
                    chunks.append(
                        "event: task.completed\n"
                        f"data: {json.dumps({'variant_count': variant_count})}\n\n"
                    )
                payload = "".join(chunks)
            else:
                summary = self._stored_task_to_mobile_bridge(task)
                payload = (
                    "event: task.progress\n"
                    f"data: {json.dumps({'progress': summary['progress'], 'message': summary.get('message')})}\n\n"
                )
            return MockResponse(status_code=200, data=payload.encode("utf-8"), content_type="text/event-stream")

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
        elif task.get("result_type") in {"vision", "image_intake", "intake"}:
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
        asset = self._get_asset(asset_id)
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
        assets = self._list_assets()
        uploaded_assets = [
            (asset_id, asset)
            for asset_id, asset in assets
            if not asset_id.startswith("asset_result_")
        ]
        result_assets = [
            (asset_id, asset)
            for asset_id, asset in assets
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


class _MemoryRecallItem:
    def __init__(self, item: Mapping[str, Any]) -> None:
        self.item = dict(item)
        self.item_id = str(self.item.get("item_id", ""))
        self.summary = str(self.item.get("summary", ""))
        self.created_at = str(self.item.get("created_at", ""))

    def to_mobile_bridge(self) -> dict[str, Any]:
        return dict(self.item)


def _safe_recall_search_result(result: Mapping[str, Any]) -> Dict[str, Any]:
    item = result.get("item")
    safe_item: Dict[str, Any] = {}
    if isinstance(item, Mapping):
        safe_item = {
            "item_id": str(item.get("item_id", "")),
            "summary": str(item.get("summary", "")),
            "created_at": str(item.get("created_at", "")),
            "provenance": _safe_recall_provenance(item.get("provenance", {})),
        }
    try:
        score = float(result.get("score", 0))
    except (TypeError, ValueError):
        score = 0.0
    match_reason = _safe_match_reason(result.get("match_reason", ""))
    return {
        "item": safe_item,
        "score": score,
        "match_reason": match_reason,
    }


def _safe_recall_provenance(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    safe: Dict[str, Any] = {}
    for key in ("source_task_id", "source_inbox_item_id", "source_surface"):
        raw = value.get(key)
        if raw in (None, ""):
            continue
        text = str(raw)
        if _contains_runtime_secret_marker(text):
            continue
        safe[key] = text
    return safe


def _safe_match_reason(value: Any) -> str:
    text = str(value or "").strip()
    if not text or _contains_runtime_secret_marker(text):
        return "Matched runtime Recall provider."
    return text


_DROP = object()


def _sanitize_vision_result(value: Mapping[str, Any]) -> Dict[str, Any]:
    top_level_keys = ("mode", "title", "summary", "text", "language", "confidence", "sections", "items")
    safe: Dict[str, Any] = {}
    for key in top_level_keys:
        if key not in value:
            continue
        if key == "sections":
            sections = _sanitize_vision_sections(value.get(key))
            if sections:
                safe[key] = sections
            continue
        if key == "items":
            items = _sanitize_vision_items(value.get(key))
            if items:
                safe[key] = items
            continue
        cleaned = _sanitize_vision_scalar(value.get(key))
        if cleaned is not _DROP:
            safe[key] = cleaned
    return safe


def _sanitize_vision_sections(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    sections: List[Dict[str, Any]] = []
    for raw_section in value:
        if not isinstance(raw_section, Mapping):
            continue
        section: Dict[str, Any] = {}
        for key in ("title", "kind", "summary"):
            cleaned = _sanitize_vision_scalar(raw_section.get(key))
            if cleaned is not _DROP:
                section[key] = cleaned
        items = _sanitize_vision_items(raw_section.get("items"))
        if items:
            section["items"] = items
        if section:
            sections.append(section)
    return sections


def _sanitize_vision_items(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: List[Dict[str, Any]] = []
    for raw_item in value:
        if not isinstance(raw_item, Mapping):
            continue
        item: Dict[str, Any] = {}
        for key in ("title", "value", "subtitle", "kind", "label", "confidence"):
            cleaned = _sanitize_vision_scalar(raw_item.get(key))
            if cleaned is not _DROP:
                item[key] = cleaned
        if item:
            items.append(item)
    return items


def _sanitize_vision_scalar(value: Any) -> object:
    if value is None:
        return _DROP
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text or _contains_runtime_secret_marker(text):
        return _DROP
    return text


def _contains_runtime_secret_marker(value: str) -> bool:
    lowered = value.lower()
    markers = (
        "provider_endpoint",
        "recall_search_endpoint",
        "runtime_store_path",
        "sqlite_path",
        "raw_embedding",
        "raw_provider_response",
        "hidden_prompt",
        "task_logs",
        "openai_api_key",
        "bearer ",
        "sk-",
        "http://",
        "https://",
        ".sqlite",
        ".sqlite3",
        "embedding_",
        "index_rows",
    )
    return any(marker in lowered for marker in markers)


def create_app(
    pairing_codes: Optional[Mapping[str, str]] = None,
    mobile_token: str = DEV_MOBILE_TOKEN,
    photo_provider: Optional[PhotoProvider] = None,
    vision_provider: Optional[VisionProvider] = None,
    advertised_endpoint: str = "",
    runtime_id: str = "hermes",
    runtime_display_name: str = DEV_DISPLAY_NAME,
    pairing_scheme: str = "http",
    recall_search_provider: str | RecallSearchProvider = "local",
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
    return MockBridgeApp(
        pairing_codes=pairing_codes,
        mobile_token=mobile_token,
        photo_provider=photo_provider,
        vision_provider=vision_provider,
        advertised_endpoint=advertised_endpoint,
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


def build_vision_provider(
    name: str = "fixture",
    endpoint: str = "",
) -> VisionProvider:
    if name == "fixture":
        return FixtureVisionProvider()
    if name == "runtime_http":
        return RuntimeHTTPVisionProvider(endpoint)
    raise ValueError(f"Unsupported vision provider: {name}")
