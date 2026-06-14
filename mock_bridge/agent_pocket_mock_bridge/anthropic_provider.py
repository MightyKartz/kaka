from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, List, Mapping, Optional

try:
    import anthropic
except ImportError:  # pragma: no cover - exercised only when optional SDK is absent.
    anthropic = None  # type: ignore[assignment]


DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 16000


class AnthropicProviderError(RuntimeError):
    pass


class AnthropicProviderConfigurationError(AnthropicProviderError):
    pass


class AnthropicProvider:
    provider_name = "anthropic"

    def __init__(
        self,
        client: Optional[Any] = None,
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model = (model or os.environ.get("KAKA_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
        self.max_tokens = int(max_tokens)
        if client is None:
            ensure_anthropic_api_key()
            if anthropic is None:
                raise AnthropicProviderConfigurationError(
                    "The anthropic Python package is required. Install it with `pip install anthropic`."
                )
            client = anthropic.Anthropic()
        self._client = client

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
                    _image_block(source_bytes, mime_type),
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
                    _image_block(source_bytes, mime_type or "image/jpeg"),
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
        content: List[Mapping[str, Any]] = []
        normalized_type = intake_type.strip().lower()
        if normalized_type == "image" and source_bytes is not None:
            content.append(_image_block(source_bytes, mime_type or "image/jpeg"))
        elif normalized_type == "pdf" and source_bytes is not None:
            content.append(_document_block(source_bytes, mime_type or "application/pdf"))
        elif normalized_type == "video" and source_bytes is not None:
            content.append(
                {
                    "type": "text",
                    "text": f"Video asset received: {len(source_bytes)} bytes, MIME {mime_type or 'video/quicktime'}.",
                }
            )
        content.append({"type": "text", "text": _universal_intake_instruction(normalized_type, payload)})
        return _normalize_universal_intake(
            self._call_json(
                task=f"intake_{normalized_type}",
                instruction="Return only strict JSON for the universal intake result.",
                content=content,
            )
        )

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
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": messages_content,
                    }
                ],
            )
        except _anthropic_exceptions() as exc:
            raise AnthropicProviderError(f"Anthropic provider request failed for {task}.") from exc
        except Exception as exc:
            raise AnthropicProviderError(f"Anthropic provider request failed for {task}.") from exc

        text = _extract_text(response)
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AnthropicProviderError(f"Anthropic provider returned invalid JSON for {task}.") from exc
        if not isinstance(decoded, Mapping):
            raise AnthropicProviderError(f"Anthropic provider returned a non-object JSON result for {task}.")
        return dict(decoded)


def _normalize_image_intake(value: Mapping[str, Any]) -> Mapping[str, Any]:
    suggestions: List[Mapping[str, Any]] = []
    raw_suggestions = value.get("suggestions")
    if isinstance(raw_suggestions, list):
        for raw_suggestion in raw_suggestions:
            if not isinstance(raw_suggestion, Mapping):
                continue
            suggestion = dict(raw_suggestion)
            suggestion.setdefault("is_available", True)
            suggestions.append(suggestion)
    result = dict(value)
    result["suggestions"] = suggestions
    return result


def _normalize_universal_intake(value: Mapping[str, Any]) -> Mapping[str, Any]:
    suggestions: List[Mapping[str, Any]] = []
    raw_suggestions = value.get("suggestions")
    if isinstance(raw_suggestions, list):
        for raw_suggestion in raw_suggestions:
            if not isinstance(raw_suggestion, Mapping):
                continue
            suggestion = dict(raw_suggestion)
            suggestion.setdefault("is_available", True)
            suggestion.setdefault("requires_confirmation", False)
            suggestions.append(suggestion)
    result = dict(value)
    result["suggestions"] = suggestions
    image_intake = result.get("image_intake")
    if isinstance(image_intake, Mapping):
        result["image_intake"] = _normalize_image_intake(image_intake)
    return result


def ensure_anthropic_api_key(env: Optional[Mapping[str, str]] = None) -> None:
    values = os.environ if env is None else env
    if not str(values.get("ANTHROPIC_API_KEY", "")).strip():
        raise AnthropicProviderConfigurationError("ANTHROPIC_API_KEY is required for --provider anthropic.")


def build_anthropic_provider() -> AnthropicProvider:
    return AnthropicProvider()


def _anthropic_exceptions() -> tuple[type[BaseException], ...]:
    if anthropic is None:
        return ()
    candidates = [
        getattr(anthropic, "APIStatusError", None),
        getattr(anthropic, "APIConnectionError", None),
        getattr(anthropic, "APITimeoutError", None),
        getattr(anthropic, "APIError", None),
    ]
    return tuple(candidate for candidate in candidates if isinstance(candidate, type) and issubclass(candidate, BaseException))


def _extract_text(response: Any) -> str:
    content = getattr(response, "content", None)
    if not isinstance(content, list):
        raise AnthropicProviderError("Anthropic provider returned an unexpected response shape.")
    chunks: List[str] = []
    for block in content:
        block_type = getattr(block, "type", None)
        text = getattr(block, "text", None)
        if isinstance(block, Mapping):
            block_type = block.get("type", block_type)
            text = block.get("text", text)
        if block_type == "text" and isinstance(text, str):
            chunks.append(text)
    result = "".join(chunks).strip()
    if result.startswith("```"):
        result = _strip_json_fence(result)
    if not result:
        raise AnthropicProviderError("Anthropic provider returned empty text.")
    return result


def _strip_json_fence(value: str) -> str:
    lines = value.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _image_block(source_bytes: bytes, mime_type: str) -> Mapping[str, Any]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": mime_type or "image/jpeg",
            "data": base64.b64encode(source_bytes).decode("ascii"),
        },
    }


def _document_block(source_bytes: bytes, mime_type: str) -> Mapping[str, Any]:
    return {
        "type": "document",
        "source": {
            "type": "base64",
            "media_type": mime_type or "application/pdf",
            "data": base64.b64encode(source_bytes).decode("ascii"),
        },
    }


def _image_intake_instruction(locale: Optional[str]) -> str:
    return (
        "Analyze the image for Pocket Agent image_intake. Return JSON with keys: "
        "image_type, title, summary, confidence, suggestions. suggestions must be an array of "
        "objects with skill, title, reason, confidence, and optional is_available. Prefer skills "
        "from: ocr, translate_text, identify_subject, nutrition_estimate, photo_enhance. "
        f"Use locale {locale or 'the user locale'} for user-visible text."
    )


def _vision_instruction(mode: str, user_instruction: str, locale: Optional[str]) -> str:
    mode_guidance = {
        "scan": "Extract visible text, codes, and document structure.",
        "translate": "Extract visible text and translate it into the user's locale.",
        "identify": "Identify the main subject, candidates, brands, objects, plants, or landmarks.",
        "food": "Estimate visible food, calories, nutrition, portions, and assumptions.",
    }.get(mode, "Analyze the image.")
    return (
        f"Perform Pocket Agent vision mode `{mode}`. {mode_guidance} "
        "Return JSON with keys: mode, title, summary, text, language, confidence, sections, items. "
        "sections is an array with title, kind, summary, items. items is an array with title, value, "
        "subtitle, kind, label, confidence. "
        f"User instruction: {user_instruction or '(none)'}. Locale: {locale or 'user locale'}."
    )


def _universal_intake_instruction(intake_type: str, payload: Mapping[str, Any]) -> str:
    visible_payload = _visible_payload(payload)
    return (
        f"Summarize a Pocket Agent universal intake item of type `{intake_type}`. "
        "Return JSON with keys: title, summary, suggestions. suggestions must be an array of objects "
        "with id, label, optional requires_confirmation, and optional is_available. "
        "For image intake you may also include image_intake with the image_intake schema. "
        "Useful suggestion ids include summarize, extract_tasks, remember, forget, open_image_conversation. "
        f"Visible non-secret intake payload: {json.dumps(visible_payload, ensure_ascii=False, sort_keys=True)}"
    )


def _visible_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    visible: Dict[str, Any] = {}
    for key in (
        "type",
        "kind",
        "text",
        "url",
        "note",
        "locale",
        "preferred_profile_id",
        "source_app",
        "received_at",
        "source",
        "context_snapshot",
    ):
        value = payload.get(key)
        if value not in (None, ""):
            visible[key] = value
    return visible
