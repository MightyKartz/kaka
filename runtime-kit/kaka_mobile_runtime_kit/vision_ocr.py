from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol, Sequence


@dataclass(frozen=True)
class RecognizedTextLine:
    text: str
    confidence: float = 0.0


class TextRecognizer(Protocol):
    def recognize(
        self,
        image_bytes: bytes,
        locale: Optional[str] = None,
    ) -> Sequence[RecognizedTextLine]:
        ...


class AppleVisionTextRecognizer:
    def recognize(
        self,
        image_bytes: bytes,
        locale: Optional[str] = None,
    ) -> Sequence[RecognizedTextLine]:
        if not image_bytes:
            return []

        try:
            from Foundation import NSData
            from Vision import (
                VNImageRequestHandler,
                VNRecognizeTextRequest,
                VNRequestTextRecognitionLevelAccurate,
            )
        except Exception:
            return []

        data = NSData.dataWithBytes_length_(image_bytes, len(image_bytes))
        request = VNRecognizeTextRequest.alloc().init()
        if hasattr(request, "setRecognitionLevel_"):
            request.setRecognitionLevel_(VNRequestTextRecognitionLevelAccurate)
        if hasattr(request, "setUsesLanguageCorrection_"):
            request.setUsesLanguageCorrection_(True)

        languages = _recognition_languages(locale)
        if languages and hasattr(request, "setRecognitionLanguages_"):
            request.setRecognitionLanguages_(languages)

        handler = VNImageRequestHandler.alloc().initWithData_options_(data, {})
        try:
            success, _ = handler.performRequests_error_([request], None)
        except Exception:
            return []
        if not success:
            return []

        lines: List[RecognizedTextLine] = []
        seen: set[str] = set()
        for observation in list(request.results() or []):
            candidates = observation.topCandidates_(1)
            if not candidates:
                continue
            candidate = candidates[0]
            text = str(candidate.string() or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            try:
                confidence = float(candidate.confidence())
            except Exception:
                confidence = 0.0
            lines.append(RecognizedTextLine(text=text, confidence=_clamp_confidence(confidence)))
        return lines


def _recognition_languages(locale: Optional[str]) -> list[str]:
    normalized = str(locale or "").lower()
    if normalized.startswith("zh"):
        return ["zh-Hans", "zh-Hant", "en-US"]
    if normalized.startswith("ja"):
        return ["ja-JP", "en-US", "zh-Hans"]
    if normalized.startswith("ko"):
        return ["ko-KR", "en-US", "zh-Hans"]
    return ["en-US", "zh-Hans", "zh-Hant"]


def _clamp_confidence(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value
