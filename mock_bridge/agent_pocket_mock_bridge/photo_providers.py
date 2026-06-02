from __future__ import annotations

import importlib.util
import inspect
import mimetypes
import os
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlsplit, urlunsplit

from agent_pocket_mock_bridge.app import FixturePhotoProvider, PhotoProvider


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"

PROVIDER_ADAPTERS = {
    "script": Path("adapters/script.py"),
    "recipe_local": Path("adapters/recipe_local.py"),
    "openai": Path("adapters/openai_image.py"),
}


class PhotoPackAdapterProvider:
    def __init__(self, adapter_path: Path | str, provider_name: str = "") -> None:
        self.adapter_path = Path(adapter_path)
        self.provider_name = provider_name or self.adapter_path.stem

    def edit(
        self,
        source_bytes: bytes,
        style: str,
        instruction: str,
        return_variants: int,
    ) -> List[Mapping[str, Any]]:
        module = self._load_adapter()
        with tempfile.TemporaryDirectory(prefix="agent-pocket-photo-pack-") as temp:
            temp_dir = Path(temp)
            input_path = temp_dir / "input.jpg"
            output_dir = temp_dir / "out"
            input_path.write_bytes(source_bytes)
            result = self._run_adapter(
                module=module,
                input_path=input_path,
                output_dir=output_dir,
                style=style,
                instruction=instruction,
                return_variants=return_variants,
            )
            return self._variants_from_manifest(result, output_dir)

    def _load_adapter(self) -> ModuleType:
        if not self.adapter_path.exists():
            raise FileNotFoundError(str(self.adapter_path))
        spec = importlib.util.spec_from_file_location(
            f"agent_pocket_photo_provider_{self.adapter_path.stem}",
            self.adapter_path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load photo adapter: {self.adapter_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _run_adapter(
        self,
        module: ModuleType,
        input_path: Path,
        output_dir: Path,
        style: str,
        instruction: str,
        return_variants: int,
    ) -> Mapping[str, Any]:
        run_edit = getattr(module, "run_edit", None)
        if run_edit is None:
            raise RuntimeError(f"Photo adapter {self.adapter_path} does not expose run_edit.")

        kwargs: Dict[str, Any] = {
            "input_path": input_path,
            "output_dir": output_dir,
            "style": style,
            "instruction": instruction,
        }
        if "return_variants" in inspect.signature(run_edit).parameters:
            kwargs["return_variants"] = return_variants

        result = run_edit(**kwargs)
        if result is None:
            manifest_path = output_dir / "manifest.json"
            if not manifest_path.exists():
                raise RuntimeError("Photo adapter did not return a manifest or write manifest.json.")
            import json

            result = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(result, Mapping):
            raise RuntimeError("Photo adapter returned an invalid manifest.")
        if result.get("status") != "completed":
            raise RuntimeError("Photo adapter did not complete.")
        return result

    def _variants_from_manifest(self, result: Mapping[str, Any], output_dir: Path) -> List[Mapping[str, Any]]:
        raw_variants = result.get("variants")
        if not isinstance(raw_variants, list) or not raw_variants:
            raise RuntimeError("Photo adapter manifest did not include variants.")

        explanation = str(result.get("explanation", "Photo Pack adapter completed the edit."))
        recipe_metadata = self._recipe_metadata_from_manifest(result)
        variants: List[Mapping[str, Any]] = []
        for index, raw_variant in enumerate(raw_variants, start=1):
            if not isinstance(raw_variant, Mapping):
                raise RuntimeError("Photo adapter manifest contained an invalid variant.")
            path_value = raw_variant.get("path")
            if not path_value:
                raise RuntimeError("Photo adapter variant did not include a path.")
            output_path = Path(str(path_value))
            if not output_path.is_absolute():
                output_path = output_dir / output_path
            image_bytes = output_path.read_bytes()
            mime_type = str(
                raw_variant.get("mime_type")
                or mimetypes.guess_type(output_path.name)[0]
                or "application/octet-stream"
            )
            variant: Dict[str, Any] = {
                "id": raw_variant.get("id", f"variant_{index}"),
                "label": raw_variant.get("label", f"Variant {index}"),
                "mime_type": mime_type,
                "bytes": image_bytes,
                "explanation": raw_variant.get("explanation", explanation),
            }
            if recipe_metadata:
                variant["recipe_metadata"] = recipe_metadata
            variants.append(variant)
        return variants

    def _recipe_metadata_from_manifest(self, result: Mapping[str, Any]) -> Mapping[str, Any]:
        metadata_keys = (
            "provider",
            "renderer",
            "composition",
            "qa",
            "share_caption",
            "recipe_summary",
            "safety",
            "upscale",
            "schema_version",
        )
        return {
            key: result[key]
            for key in metadata_keys
            if key in result
        }


def build_photo_provider(
    provider: str,
    photo_pack_root: Path | str = "photo-pack",
) -> PhotoProvider:
    if provider == "fixture":
        return FixturePhotoProvider()
    if provider not in PROVIDER_ADAPTERS:
        raise ValueError(f"Unsupported photo provider: {provider}")
    return PhotoPackAdapterProvider(
        Path(photo_pack_root) / PROVIDER_ADAPTERS[provider],
        provider_name=provider,
    )


def build_openai_base_url_report(env: Mapping[str, str]) -> Mapping[str, Any]:
    raw_value = str(env.get("OPENAI_BASE_URL", "")).strip()
    effective_value = raw_value or DEFAULT_OPENAI_BASE_URL
    safe_value, redacted = _redact_base_url(effective_value)
    return {
        "state": "custom" if raw_value else "default",
        "value": safe_value,
        "redacted": redacted,
    }


def _redact_base_url(value: str) -> tuple[str, bool]:
    value = value.strip()
    if not value:
        return DEFAULT_OPENAI_BASE_URL, False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<invalid-openai-base-url>", True

    redacted = bool(parsed.username or parsed.password or parsed.query or parsed.fragment)
    if not parsed.scheme or not parsed.netloc:
        if "@" in value or "?" in value or "#" in value:
            return "<redacted-openai-base-url>", True
        return value, False

    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    try:
        port = parsed.port
    except ValueError:
        port = None
        redacted = True
    netloc = f"{host}:{port}" if port else host
    safe = urlunsplit((parsed.scheme, netloc, parsed.path.rstrip("/") or "", "", ""))
    return safe, redacted


def build_provider_preflight_report(
    provider: str,
    photo_pack_root: Path | str = "photo-pack",
    env: Optional[Mapping[str, str]] = None,
) -> Mapping[str, Any]:
    env_values = os.environ if env is None else env
    adapter_path: Optional[Path] = None
    adapter_exists = True
    env_report: Dict[str, str] = {}
    config_report: Dict[str, Mapping[str, Any]] = {}
    missing: List[str] = []

    if provider == "fixture":
        adapter_path = None
    elif provider in PROVIDER_ADAPTERS:
        adapter_path = Path(photo_pack_root) / PROVIDER_ADAPTERS[provider]
        adapter_exists = adapter_path.exists()
        if not adapter_exists:
            missing.append("adapter file")
    else:
        missing.append("supported provider")
        adapter_exists = False

    if provider == "openai":
        has_key = bool(env_values.get("OPENAI_API_KEY"))
        env_report["OPENAI_API_KEY"] = "set" if has_key else "missing"
        config_report["OPENAI_BASE_URL"] = build_openai_base_url_report(env_values)
        if not has_key:
            missing.append("OPENAI_API_KEY")

    server_env_file_arg = " --env-file /path/to/hermes-openai.env" if provider == "openai" else ""
    commands = {
        "server": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.server "
            f"--host 0.0.0.0 --port 8765 --bonjour --photo-provider {provider}"
            f"{server_env_file_arg}"
        ),
        "qa": (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa run-lan "
            f"--host <mac-ip> --port 8765 --photo-provider {provider}"
        ),
    }
    if provider == "openai":
        commands["fake_openai"] = (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.fake_openai "
            "--host 127.0.0.1 --port 8781"
        )
        commands["simulator_openai_smoke"] = (
            "PYTHONPATH=mock_bridge python3 -m agent_pocket_mock_bridge.qa simulator-openai-smoke "
            "--host 127.0.0.1 --port 8769 --fake-openai-port 8781 "
            "--receipt-file docs/qa-receipts/simulator-openai-compatible-photo-flow.json "
            "--fake-openai-status-file docs/qa-receipts/simulator-openai-compatible-fake-openai-status.json "
            "--screenshot-file /tmp/agent-pocket-simulator-openai-provider-smoke.png"
        )

    return {
        "ok": not missing,
        "provider": provider,
        "missing": missing,
        "adapter": {
            "path": str(adapter_path) if adapter_path else "",
            "exists": adapter_exists,
        },
        "env": env_report,
        "config": config_report,
        "commands": commands,
    }
