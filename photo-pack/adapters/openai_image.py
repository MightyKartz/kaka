#!/usr/bin/env python3
"""OpenAI Images Edits adapter for Agent Pocket Photo Pack."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple


STYLE_LABELS = {
    "natural_enhance": "Natural Enhance",
    "portrait_polish": "Portrait Polish",
    "product_shot": "Product Shot",
    "social_cover": "Social Cover",
}

STYLE_PROMPTS = {
    "natural_enhance": (
        "Improve exposure, contrast, color balance, and fine detail while keeping the "
        "photo realistic and faithful to the original scene."
    ),
    "portrait_polish": (
        "Polish the portrait with natural skin tone, cleaner lighting, and subtle "
        "background refinement while preserving identity, age, expression, and body shape."
    ),
    "product_shot": (
        "Create a clean product-photo treatment with improved lighting, sharper edges, "
        "controlled reflections, and an uncluttered commercial presentation."
    ),
    "social_cover": (
        "Prepare a social-cover-ready image with strong framing, balanced negative space, "
        "and a composition that remains readable behind title text."
    ),
}

DEFAULT_MODEL = "gpt-image-1.5"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
OUTPUT_EXTENSIONS = {
    "jpeg": ".jpg",
    "png": ".png",
    "webp": ".webp",
}
OUTPUT_MIME_TYPES = {
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

HTTPPost = Callable[[str, Mapping[str, str], bytes, str, int], Mapping[str, Any]]


class OpenAIImageEditError(RuntimeError):
    """Raised when the OpenAI image edit adapter cannot complete a task."""


def run_edit(
    input_path: Path,
    output_dir: Path,
    style: str,
    instruction: str,
    return_variants: int = 1,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    http_post: Optional[HTTPPost] = None,
    base_url: Optional[str] = None,
    quality: Optional[str] = None,
    size: Optional[str] = None,
    output_format: Optional[str] = None,
    timeout: int = 120,
) -> Dict[str, Any]:
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    model = model or os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_MODEL)
    base_url = (base_url or os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
    quality = quality or os.environ.get("OPENAI_IMAGE_QUALITY", "medium")
    size = size or os.environ.get("OPENAI_IMAGE_SIZE", "auto")
    output_format = output_format or os.environ.get("OPENAI_IMAGE_OUTPUT_FORMAT", "jpeg")

    _validate_inputs(input_path, style, return_variants, api_key, output_format)
    prompt = build_prompt(style, instruction)
    output_dir.mkdir(parents=True, exist_ok=True)

    body, content_type = _build_multipart_body(
        fields={
            "model": model,
            "prompt": prompt,
            "n": str(return_variants),
            "quality": quality,
            "size": size,
            "output_format": output_format,
        },
        files=[
            (
                "image",
                input_path.name,
                _guess_mime_type(input_path),
                input_path.read_bytes(),
            )
        ],
    )

    post = http_post or _default_http_post
    response = post(
        f"{base_url}/images/edits",
        {"Authorization": f"Bearer {api_key}"},
        body,
        content_type,
        timeout,
    )
    variants = _write_variants(
        response=response,
        output_dir=output_dir,
        style=style,
        output_format=output_format,
        limit=return_variants,
    )

    result = {
        "status": "completed",
        "provider": "openai",
        "model": model,
        "style": style,
        "instruction": instruction,
        "variants": variants,
        "explanation": "OpenAI Images Edits generated the requested photo variant.",
    }
    (output_dir / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def build_prompt(style: str, instruction: str) -> str:
    if style not in STYLE_PROMPTS:
        raise ValueError(f"Unsupported style: {style}")
    return "\n".join(
        [
            STYLE_PROMPTS[style],
            f"User instruction: {instruction}",
            (
                "Preserve the subject, identity, important product details, and original "
                "intent. Avoid fake-looking filters, extra limbs, unwanted text, or invented logos."
            ),
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Agent Pocket OpenAI image edit adapter.")
    parser.add_argument("--input", required=True, type=Path, help="Input image path.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for edited variants.")
    parser.add_argument("--style", required=True, choices=sorted(STYLE_LABELS), help="Edit intent style.")
    parser.add_argument("--instruction", required=True, help="User or default edit instruction.")
    parser.add_argument("--return-variants", default=1, type=int, help="Number of variants to request, 1-3.")
    parser.add_argument("--model", default=None, help=f"OpenAI image model. Defaults to {DEFAULT_MODEL}.")
    parser.add_argument("--quality", default=None, help="Image quality: low, medium, high, or auto.")
    parser.add_argument("--size", default=None, help="Output size, such as auto or 1024x1024.")
    parser.add_argument("--output-format", default=None, help="Output format: jpeg, png, or webp.")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible API base URL.")
    parser.add_argument("--timeout", default=120, type=int, help="Request timeout in seconds.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_edit(
        input_path=args.input,
        output_dir=args.output_dir,
        style=args.style,
        instruction=args.instruction,
        return_variants=args.return_variants,
        model=args.model,
        quality=args.quality,
        size=args.size,
        output_format=args.output_format,
        base_url=args.base_url,
        timeout=args.timeout,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def _validate_inputs(
    input_path: Path,
    style: str,
    return_variants: int,
    api_key: Optional[str],
    output_format: str,
) -> None:
    if style not in STYLE_LABELS:
        raise ValueError(f"Unsupported style: {style}")
    if not input_path.exists():
        raise FileNotFoundError(str(input_path))
    if return_variants < 1 or return_variants > 3:
        raise ValueError("return_variants must be between 1 and 3")
    if not api_key:
        raise OpenAIImageEditError("OPENAI_API_KEY is required for the OpenAI image edit adapter.")
    if output_format not in OUTPUT_EXTENSIONS:
        raise ValueError(f"Unsupported output format: {output_format}")


def _guess_mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _build_multipart_body(
    fields: Mapping[str, str],
    files: Iterable[Tuple[str, str, str, bytes]],
) -> Tuple[bytes, str]:
    boundary = f"agent-pocket-{uuid.uuid4().hex}"
    chunks: List[bytes] = []

    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )

    for name, filename, mime_type, content in files:
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"),
                content,
                b"\r\n",
            ]
        )

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _default_http_post(
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    content_type: str,
    timeout: int,
) -> Mapping[str, Any]:
    request_headers = dict(headers)
    request_headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise OpenAIImageEditError(f"OpenAI image edit failed ({error.code}): {detail}") from error
    except urllib.error.URLError as error:
        raise OpenAIImageEditError(f"OpenAI image edit failed: {error.reason}") from error

    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise OpenAIImageEditError("OpenAI image edit returned invalid JSON.") from error


def _write_variants(
    response: Mapping[str, Any],
    output_dir: Path,
    style: str,
    output_format: str,
    limit: int,
) -> List[Dict[str, str]]:
    data = response.get("data")
    if not isinstance(data, list) or not data:
        raise OpenAIImageEditError("OpenAI image edit response did not include image data.")

    extension = OUTPUT_EXTENSIONS[output_format]
    mime_type = OUTPUT_MIME_TYPES[output_format]
    variants: List[Dict[str, str]] = []
    for index, item in enumerate(data[:limit], start=1):
        if not isinstance(item, Mapping) or not item.get("b64_json"):
            raise OpenAIImageEditError("OpenAI image edit response contained a variant without b64_json.")
        try:
            image_bytes = base64.b64decode(str(item["b64_json"]))
        except ValueError as error:
            raise OpenAIImageEditError("OpenAI image edit response contained invalid base64 image data.") from error

        output_path = output_dir / f"{style}_{index}{extension}"
        output_path.write_bytes(image_bytes)
        variants.append(
            {
                "id": f"variant_{style}_{index}",
                "label": f"{STYLE_LABELS[style]} {index}",
                "path": str(output_path),
                "mime_type": mime_type,
            }
        )

    return variants


if __name__ == "__main__":
    raise SystemExit(main())
