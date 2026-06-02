#!/usr/bin/env python3
"""Deterministic Photo Pack script adapter for Agent Pocket smoke tests."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List


STYLE_LABELS = {
    "natural_enhance": "Natural Enhance",
    "portrait_polish": "Portrait Polish",
    "product_shot": "Product Shot",
    "social_cover": "Social Cover",
}


def run_edit(input_path: Path, output_dir: Path, style: str, instruction: str) -> Dict[str, Any]:
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    if style not in STYLE_LABELS:
        raise ValueError(f"Unsupported style: {style}")
    if not input_path.exists():
        raise FileNotFoundError(str(input_path))

    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = input_path.suffix or ".jpg"
    output_path = output_dir / f"{style}{suffix}"
    shutil.copyfile(input_path, output_path)

    result = {
        "status": "completed",
        "style": style,
        "instruction": instruction,
        "variants": [
            {
                "id": f"variant_{style}",
                "label": STYLE_LABELS[style],
                "path": str(output_path),
            }
        ],
        "explanation": (
            "Script adapter copied the source image as a deterministic smoke-test "
            "variant. Replace this adapter with a real image pipeline for production."
        ),
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Agent Pocket Photo Pack script adapter.")
    parser.add_argument("--input", required=True, type=Path, help="Input image path.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for edited variants.")
    parser.add_argument("--style", required=True, choices=sorted(STYLE_LABELS), help="Edit intent style.")
    parser.add_argument("--instruction", required=True, help="User or default edit instruction.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_edit(
        input_path=args.input,
        output_dir=args.output_dir,
        style=args.style,
        instruction=args.instruction,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
