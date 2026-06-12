from __future__ import annotations

import base64
import json
import os
import socket
from typing import Any, Dict, List, Mapping, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlsplit, urlunsplit

from agent_pocket_mock_bridge.anthropic_provider import (
    _image_intake_instruction,
    _normalize_image_intake,
    _normalize_universal_intake,
    _universal_intake_instruction,
    _vision_instruction,
)


DEFAULT_BASE_URL = "http://127.0.0.1:8642/v1"
DEFAULT_TIMEOUT_SECONDS = 60.0
PDF_UNSUPPORTED_FAILURE_CODE = "pdf_not_supported_by_hermes_provider"


class HermesProviderError(RuntimeError):
    pass


class HermesProviderConfigurationError(HermesProviderError):
    pass


class HermesProviderUnsupportedInputError(HermesProviderError):
    def __init__(self, message: str, failure_code: str) -> None:
        super().__init__(message)
        self.failure_code = failure_code


class HermesProvider:
    provider_name = "hermes"

    def __init__(self) -> None:
        self.base_url = _normalized_base_url(os.environ.get("KAKA_HERMES_BASE_URL", DEFAULT_BASE_URL))
        self._api_key = ensure_hermes_api_key()
        self.timeout_seconds = _timeout_seconds(os.environ.get("KAKA_HERMES_TIMEOUT_SECONDS"))
        configured_model = str(os.environ.get("KAKA_HERMES_MODEL", "")).strip()
        discovered_model = self._probe_startup()
        self.model = configured_model or discovered_model
        if not self.model:
            raise HermesProviderConfigurationError("Hermes provider could not discover a model from /v1/models.")

    def image_intake(
        self,
        source_bytes: bytes,
        mime_type: str,
        locale: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return _normalize_image_intake(
            self._call_json(
                task="image_intake",
                instruction=_image_intake_instruction(locale),
                content=[
                    _image_url_block(source_bytes, mime_type),
                ],
            )
        )

    def analyze(
        self,
        source_bytes: bytes,
        mode: str,
        instruction: str,
        locale: Optional[str],
        mime_type: str = "image/jpeg",
    ) -> Mapping[str, Any]:
        result = dict(
            self._call_json(
                task=f"vision_{mode}",
                instruction=_vision_instruction(mode=mode, user_instruction=instruction, locale=locale),
                content=[
                    _image_url_block(source_bytes, mime_type or "image/jpeg"),
                ],
            )
        )
        result.setdefault("mode", mode)
        return result

    def universal_intake(
        self,
        intake_type: str,
        payload: Mapping[str, Any],
        source_bytes: Optional[bytes] = None,
        mime_type: str = "",
    ) -> Mapping[str, Any]:
        normalized_type = intake_type.strip().lower()
        if normalized_type == "pdf":
            raise HermesProviderUnsupportedInputError(
                "Hermes provider does not support PDF intake because Hermes chat completions do not accept PDF files.",
                failure_code=PDF_UNSUPPORTED_FAILURE_CODE,
            )
        content: List[Mapping[str, Any]] = []
        if normalized_type == "image" and source_bytes is not None:
            content.append(_image_url_block(source_bytes, mime_type or "image/jpeg"))
        content.append({"type": "text", "text": _universal_intake_instruction(normalized_type, payload)})
        return _normalize_universal_intake(
            self._call_json(
                task=f"intake_{normalized_type}",
                instruction="Return only strict JSON for the universal intake result.",
                content=content,
            )
        )

    def _probe_startup(self) -> str:
        try:
            self._request_json("GET", self._health_url(), task="/health")
        except HermesProviderError as exc:
            raise HermesProviderConfigurationError("Hermes provider startup probe failed for /health.") from exc
        try:
            models = self._request_json("GET", self._url("/models"), task="/v1/models")
        except HermesProviderError as exc:
            raise HermesProviderConfigurationError("Hermes provider startup probe failed for /v1/models.") from exc
        return _first_model_id(models)

    def _call_json(
        self,
        task: str,
        instruction: str,
        content: List[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        messages_content = [
            {
                "type": "text",
                "text": (
                    f"{instruction}\n\n"
                    "Respond with one JSON object only. Do not include Markdown fences, commentary, "
                    "or any provider secrets. The JSON must match the requested schema."
                ),
            },
            *content,
        ]
        response = self._request_json(
            "POST",
            self._url("/chat/completions"),
            task=task,
            payload={
                "model": self.model,
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": messages_content,
                    }
                ],
            },
        )
        text = _extract_chat_text(response)
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HermesProviderError(f"Hermes provider returned invalid JSON for {task}.") from exc
        if not isinstance(decoded, Mapping):
            raise HermesProviderError(f"Hermes provider returned a non-object JSON result for {task}.")
        return dict(decoded)

    def _request_json(
        self,
        method: str,
        url: str,
        task: str,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        body = None
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib_request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib_request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read()
        except urllib_error.HTTPError as exc:
            raise HermesProviderError(f"Hermes API returned HTTP {exc.code} for {task}.") from exc
        except (urllib_error.URLError, TimeoutError, socket.timeout) as exc:
            raise HermesProviderError(f"Hermes provider request failed for {task}.") from exc
        try:
            decoded = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HermesProviderError(f"Hermes provider returned invalid JSON for {task}.") from exc
        if not isinstance(decoded, Mapping):
            raise HermesProviderError(f"Hermes provider returned a non-object JSON response for {task}.")
        return dict(decoded)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _health_url(self) -> str:
        parsed = urlsplit(self.base_url)
        path = parsed.path.rstrip("/")
        if path.endswith("/v1"):
            path = path[:-3]
        path = f"{path.rstrip('/')}/health" if path else "/health"
        return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def ensure_hermes_api_key(env: Optional[Mapping[str, str]] = None) -> str:
    values = os.environ if env is None else env
    api_key = str(values.get("KAKA_HERMES_API_KEY", "")).strip()
    if not api_key:
        raise HermesProviderConfigurationError("KAKA_HERMES_API_KEY is required for --provider hermes.")
    return api_key


def build_hermes_provider() -> HermesProvider:
    return HermesProvider()


def _normalized_base_url(value: str) -> str:
    raw = (value or DEFAULT_BASE_URL).strip().rstrip("/") or DEFAULT_BASE_URL
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HermesProviderConfigurationError("KAKA_HERMES_BASE_URL must be an http:// or https:// URL.")
    if not parsed.path.rstrip("/").endswith("/v1"):
        raw = f"{raw}/v1"
    return raw


def _timeout_seconds(value: Optional[str]) -> float:
    if value in (None, ""):
        return DEFAULT_TIMEOUT_SECONDS
    try:
        timeout = float(str(value).strip())
    except ValueError as exc:
        raise HermesProviderConfigurationError("KAKA_HERMES_TIMEOUT_SECONDS must be a positive number.") from exc
    if timeout <= 0:
        raise HermesProviderConfigurationError("KAKA_HERMES_TIMEOUT_SECONDS must be a positive number.")
    return timeout


def _first_model_id(value: Mapping[str, Any]) -> str:
    data = value.get("data")
    if isinstance(data, list):
        for raw_model in data:
            if not isinstance(raw_model, Mapping):
                continue
            model_id = str(raw_model.get("id", "")).strip()
            if model_id:
                return model_id
    return ""


def _extract_chat_text(response: Mapping[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise HermesProviderError("Hermes provider returned an unexpected chat completion shape.")
    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise HermesProviderError("Hermes provider returned an unexpected chat completion choice.")
    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        raise HermesProviderError("Hermes provider returned an unexpected chat completion message.")
    content = message.get("content")
    if isinstance(content, str):
        text = content.strip()
    elif isinstance(content, list):
        chunks: List[str] = []
        for block in content:
            if not isinstance(block, Mapping):
                continue
            block_text = block.get("text")
            if isinstance(block_text, str):
                chunks.append(block_text)
        text = "".join(chunks).strip()
    else:
        text = ""
    if text.startswith("```"):
        text = _strip_json_fence(text)
    if not text:
        raise HermesProviderError("Hermes provider returned empty text.")
    return text


def _strip_json_fence(value: str) -> str:
    lines = value.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _image_url_block(source_bytes: bytes, mime_type: str) -> Mapping[str, Any]:
    safe_mime_type = (mime_type or "image/jpeg").strip() or "image/jpeg"
    data = base64.b64encode(source_bytes).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{safe_mime_type};base64,{data}",
        },
    }
