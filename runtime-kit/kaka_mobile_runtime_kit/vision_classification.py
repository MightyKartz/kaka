from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence


@dataclass(frozen=True)
class ClassifiedImageLabel:
    identifier: str
    confidence: float = 0.0


class ImageClassifier(Protocol):
    def classify(self, image_bytes: bytes, locale: Optional[str] = None) -> Sequence[ClassifiedImageLabel]:
        ...


class AppleVisionImageClassifier:
    def classify(self, image_bytes: bytes, locale: Optional[str] = None) -> Sequence[ClassifiedImageLabel]:
        if not image_bytes:
            return []

        try:
            from Foundation import NSData
            from Vision import VNClassifyImageRequest, VNImageRequestHandler
        except Exception:
            return []

        data = NSData.dataWithBytes_length_(image_bytes, len(image_bytes))
        request = VNClassifyImageRequest.alloc().init()
        handler = VNImageRequestHandler.alloc().initWithData_options_(data, {})
        try:
            success, _ = handler.performRequests_error_([request], None)
        except Exception:
            return []
        if not success:
            return []

        labels: list[ClassifiedImageLabel] = []
        seen: set[str] = set()
        for observation in list(request.results() or []):
            identifier = str(observation.identifier() or "").strip()
            if not identifier or identifier in seen:
                continue
            seen.add(identifier)
            try:
                confidence = float(observation.confidence())
            except Exception:
                confidence = 0.0
            labels.append(ClassifiedImageLabel(identifier=identifier, confidence=_clamp_confidence(confidence)))
        return labels


def _clamp_confidence(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value
