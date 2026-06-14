from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class RecognizedTextLine:
    text: str
    confidence: float = 0.0


def build_image_intake_result(
    image_bytes: bytes,
    locale: str | None,
    recognized_lines: Iterable[RecognizedTextLine],
) -> Mapping[str, object]:
    is_chinese = str(locale or "").lower().startswith("zh")
    lines = [line for line in recognized_lines if line.text.strip()]
    text_score = min(1.0, len(lines) / 6.0)
    has_text = len(lines) >= 2

    if has_text:
        return {
            "image_type": "text",
            "title": "检测到文字" if is_chinese else "Text detected",
            "summary": (
                f"我看到这张图片里有 {len(lines)} 行可读文字。"
                if is_chinese
                else f"I found {len(lines)} readable text lines in this image."
            ),
            "confidence": round(max(0.58, text_score), 2),
            "suggestions": [
                _suggestion(
                    "ocr",
                    "提取文字",
                    "Extract Text",
                    "画面中有多行可读文字。",
                    "The image contains multiple readable text lines.",
                    text_score,
                    is_chinese,
                ),
                _suggestion(
                    "translate_text",
                    "翻译文字",
                    "Translate Text",
                    "可以把识别到的文字翻译成当前语言。",
                    "The detected text can be translated into your current language.",
                    min(0.8, text_score),
                    is_chinese,
                ),
                _suggestion(
                    "photo_enhance",
                    "大师级优化",
                    "Master Enhance",
                    "也可以优化这张照片的清晰度和观感。",
                    "The photo can also be enhanced for clarity and appearance.",
                    0.46,
                    is_chinese,
                ),
            ],
        }

    return {
        "image_type": "photo",
        "title": "已看到照片" if is_chinese else "Photo ready",
        "summary": (
            "我可以帮你优化这张照片，或尝试识别画面里的主体。"
            if is_chinese
            else "I can enhance this photo or try to identify the main subject."
        ),
        "confidence": 0.52,
        "suggestions": [
            _suggestion(
                "photo_enhance",
                "大师级优化",
                "Master Enhance",
                "适合先做自然增强和构图优化。",
                "A natural enhancement and composition polish is a good first step.",
                0.62,
                is_chinese,
            ),
            _suggestion(
                "identify_subject",
                "识别主体",
                "Identify Subject",
                "可以尝试判断画面中的主要物体。",
                "Pocket Agent can try to identify the main visible subject.",
                0.48,
                is_chinese,
            ),
            _suggestion(
                "ocr",
                "提取文字",
                "Extract Text",
                "如果你想读背景文字，也可以提取文字。",
                "If you want background text, Pocket Agent can extract it too.",
                0.25,
                is_chinese,
            ),
        ],
    }


def _suggestion(
    skill: str,
    zh_title: str,
    en_title: str,
    zh_reason: str,
    en_reason: str,
    confidence: float,
    is_chinese: bool,
) -> Mapping[str, object]:
    return {
        "skill": skill,
        "title": zh_title if is_chinese else en_title,
        "reason": zh_reason if is_chinese else en_reason,
        "confidence": round(max(0.0, min(1.0, confidence)), 2),
        "is_available": True,
    }
