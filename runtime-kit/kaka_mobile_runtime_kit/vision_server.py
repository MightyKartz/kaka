from __future__ import annotations

import argparse
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping, Optional, Sequence

from kaka_mobile_runtime_kit.local_vision_heuristics import (
    estimate_food,
    infer_subject,
    translate_lines,
)
from kaka_mobile_runtime_kit.vision_classification import (
    AppleVisionImageClassifier,
    ClassifiedImageLabel,
    ImageClassifier,
)
from kaka_mobile_runtime_kit.vision_ocr import (
    AppleVisionTextRecognizer,
    RecognizedTextLine,
    TextRecognizer,
)


class VisionEndpointServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
        text_recognizer: Optional[TextRecognizer] = None,
        image_classifier: Optional[ImageClassifier] = None,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.text_recognizer = text_recognizer or AppleVisionTextRecognizer()
        self.image_classifier = image_classifier or AppleVisionImageClassifier()

    def serve_in_background(self) -> threading.Thread:
        thread = threading.Thread(target=self.serve_forever, daemon=True)
        thread.start()
        return thread


class VisionEndpointHandler(BaseHTTPRequestHandler):
    server: VisionEndpointServer

    def do_POST(self) -> None:
        if self.path != "/kaka/vision":
            self._send_json({"error": "not_found"}, status=404)
            return

        try:
            payload = self._read_json()
            vision = build_vision_result(
                payload,
                text_recognizer=self.server.text_recognizer,
                image_classifier=self.server.image_classifier,
            )
        except ValueError as exc:
            self._send_json({"error": "bad_request", "message": str(exc)}, status=400)
            return

        self._send_json({"vision": vision})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> Mapping[str, Any]:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("invalid content length") from exc
        try:
            decoded = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("invalid JSON body") from exc
        if not isinstance(decoded, Mapping):
            raise ValueError("request body must be a JSON object")
        return decoded

    def _send_json(self, payload: Mapping[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_vision_endpoint_server(
    host: str = "127.0.0.1",
    port: int = 8787,
    text_recognizer: Optional[TextRecognizer] = None,
    image_classifier: Optional[ImageClassifier] = None,
) -> VisionEndpointServer:
    return VisionEndpointServer(
        (host, port),
        VisionEndpointHandler,
        text_recognizer=text_recognizer,
        image_classifier=image_classifier,
    )


def build_vision_result(
    payload: Mapping[str, Any],
    text_recognizer: Optional[TextRecognizer] = None,
    image_classifier: Optional[ImageClassifier] = None,
) -> Mapping[str, Any]:
    mode = str(payload.get("mode", "")).strip()
    if mode not in {"scan", "identify", "translate", "food"}:
        raise ValueError("mode must be scan, identify, translate, or food")

    locale = payload.get("locale")
    is_chinese = str(locale or "").lower().startswith("zh")
    image_bytes = _decode_image_bytes(payload.get("image_base64"))
    size_kb = max(1, round(len(image_bytes) / 1024))

    if mode == "scan":
        return _scan_result(
            mode=mode,
            locale=locale,
            image_bytes=image_bytes,
            size_kb=size_kb,
            is_chinese=is_chinese,
            text_recognizer=text_recognizer,
        )

    if mode == "translate":
        return _translate_result(
            mode=mode,
            locale=locale,
            image_bytes=image_bytes,
            is_chinese=is_chinese,
            text_recognizer=text_recognizer,
        )

    if mode == "food":
        return _food_result(
            mode=mode,
            locale=locale,
            image_bytes=image_bytes,
            size_kb=size_kb,
            is_chinese=is_chinese,
            text_recognizer=text_recognizer,
            image_classifier=image_classifier,
        )

    return _identify_result(
        mode=mode,
        locale=locale,
        image_bytes=image_bytes,
        size_kb=size_kb,
        is_chinese=is_chinese,
        text_recognizer=text_recognizer,
        image_classifier=image_classifier,
    )


def _scan_result(
    mode: str,
    locale: Any,
    image_bytes: bytes,
    size_kb: int,
    is_chinese: bool,
    text_recognizer: Optional[TextRecognizer],
) -> Mapping[str, Any]:
    lines = _recognized_lines(text_recognizer, image_bytes, locale)
    text = _joined_text(lines)
    confidence = _average_confidence(lines, default=0.18)
    if lines:
        summary = (
            f"识别到 {len(lines)} 行文字。"
            if is_chinese
            else f"Recognized {len(lines)} text line{'s' if len(lines) != 1 else ''}."
        )
        items = _line_items(lines, is_chinese)
    else:
        summary = (
            "没有识别到清晰文字。请靠近文字并保持画面稳定。"
            if is_chinese
            else "No clear text was recognized. Move closer to the text and keep the frame steady."
        )
        text = "未识别到文字" if is_chinese else "No text recognized"
        items = [
            {
                "title": "文字状态" if is_chinese else "Text status",
                "value": text,
                "subtitle": (
                    "请让文字占据更多画面，并避免反光或模糊。"
                    if is_chinese
                    else "Let the text fill more of the frame and avoid glare or blur."
                ),
                "confidence": confidence,
            }
        ]

    return {
        "mode": mode,
        "title": "扫描结果" if is_chinese else "Scan Result",
        "summary": summary,
        "text": text,
        "language": locale or ("zh-Hans" if is_chinese else "en"),
        "confidence": confidence,
        "sections": [
            {
                "title": "文本" if is_chinese else "Text",
                "kind": "ocr",
                "items": items,
            },
            _asset_section(size_kb, is_chinese),
        ],
        "items": items[:3],
    }


def _translate_result(
    mode: str,
    locale: Any,
    image_bytes: bytes,
    is_chinese: bool,
    text_recognizer: Optional[TextRecognizer],
) -> Mapping[str, Any]:
    lines = _recognized_lines(text_recognizer, image_bytes, locale)
    source_text = _joined_text(lines)
    confidence = _average_confidence(lines, default=0.16)
    translated_lines = translate_lines(lines, is_chinese)
    if source_text:
        if translated_lines:
            translated_value = "\n".join(line.target for line in translated_lines)
            translated_confidence = _average_values([line.confidence for line in translated_lines], default=0.42)
            summary = (
                f"已翻译 {len(translated_lines)} 行文字。"
                if is_chinese
                else f"Translated {len(translated_lines)} text line{'s' if len(translated_lines) != 1 else ''}."
            )
            translated_subtitle = (
                "本机 OCR 线索翻译" if is_chinese else "Local OCR clue translation"
            )
            text = translated_value
        else:
            summary = (
                f"已提取 {len(lines)} 行原文；未配置本机翻译引擎。"
                if is_chinese
                else f"Extracted {len(lines)} source line{'s' if len(lines) != 1 else ''}; no local translation engine is configured."
            )
            translated_value = "未配置本机翻译引擎" if is_chinese else "No local translation engine configured"
            translated_subtitle = (
                "接入 Hermes/OpenClaw 翻译模型后会在这里显示译文。"
                if is_chinese
                else "Connect a Hermes/OpenClaw translation model to show translated text here."
            )
            translated_confidence = 0.2
            text = source_text
    else:
        source_text = "未识别到可翻译文字" if is_chinese else "No translatable text recognized"
        summary = (
            "没有识别到可翻译文字。请让文字更清晰地出现在画面中。"
            if is_chinese
            else "No translatable text was recognized. Keep the text sharper and more visible in the frame."
        )
        translated_value = "无法生成译文" if is_chinese else "No translation available"
        translated_subtitle = (
            "先识别到原文后才能翻译。"
            if is_chinese
            else "Source text must be recognized before translation."
        )
        translated_confidence = 0.1
        text = source_text

    items = [
        {
            "title": "原文" if is_chinese else "Source",
            "value": source_text,
            "subtitle": "本机文字识别" if is_chinese else "Local text recognition",
            "confidence": confidence,
        },
        {
            "title": "译文" if is_chinese else "Translation",
            "value": translated_value,
            "subtitle": translated_subtitle,
            "confidence": translated_confidence,
        },
    ]
    return {
        "mode": mode,
        "title": "翻译结果" if is_chinese else "Translation",
        "summary": summary,
        "text": text,
        "language": locale or ("zh-Hans" if is_chinese else "en"),
        "confidence": confidence,
        "sections": [
            {
                "title": "翻译" if is_chinese else "Translation",
                "kind": "ocr",
                "items": items,
            }
        ],
        "items": items,
    }


def _identify_result(
    mode: str,
    locale: Any,
    image_bytes: bytes,
    size_kb: int,
    is_chinese: bool,
    text_recognizer: Optional[TextRecognizer],
    image_classifier: Optional[ImageClassifier],
) -> Mapping[str, Any]:
    lines = _recognized_lines(text_recognizer, image_bytes, locale)
    labels = _classified_labels(image_classifier, image_bytes, locale)
    candidate = infer_subject(lines, labels, is_chinese)
    if candidate is not None:
        subtitle = f"线索：{candidate.evidence}" if is_chinese else f"Clue: {candidate.evidence}"
        items = [
            {
                "title": "候选主体" if is_chinese else "Candidate subject",
                "value": candidate.label,
                "subtitle": subtitle,
                "confidence": candidate.confidence,
            }
        ]
        if labels:
            items.append(
                {
                    "title": "本机分类" if is_chinese else "Local classification",
                    "value": ", ".join(_display_label(label) for label in labels[:3]),
                    "subtitle": "Apple Vision" if is_chinese else "Apple Vision",
                    "confidence": _average_confidence_from_labels(labels[:3], default=candidate.confidence),
                }
            )
        from_text = candidate.source == "text"
        summary = (
            f"根据图片文字线索识别到：{candidate.label}。"
            if from_text
            else f"根据本机图片分类识别到：{candidate.label}。"
        )
        if not is_chinese:
            summary = (
                f"Identified from image text clues: {candidate.label}."
                if from_text
                else f"Identified from local image classification: {candidate.label}."
            )
        return {
            "mode": mode,
            "title": "识别结果" if is_chinese else "Identify Result",
            "summary": summary,
            "text": f"{candidate.label}\n{subtitle}",
            "language": locale or ("zh-Hans" if is_chinese else "en"),
            "confidence": candidate.confidence,
            "sections": [
                {
                    "title": "候选主体" if is_chinese else "Candidate subjects",
                    "kind": "candidates",
                    "items": items,
                },
                _asset_section(size_kb, is_chinese),
            ],
            "items": items[:3],
        }

    return {
        "mode": mode,
        "title": "识别结果" if is_chinese else "Identify Result",
        "summary": (
            "当前未配置主体识别模型，无法可靠判断画面中的物体。"
            if is_chinese
            else "No subject recognition model is configured, so visible objects cannot be judged reliably."
        ),
        "text": (
            "请接入多模态识别模型，或切换到扫描/翻译读取文字。"
            if is_chinese
            else "Connect a multimodal recognition model, or switch to Scan/Translate to read text."
        ),
        "language": locale or ("zh-Hans" if is_chinese else "en"),
        "confidence": 0.18,
        "sections": [
            {
                "title": "候选主体" if is_chinese else "Candidate subjects",
                "kind": "candidates",
                "items": [
                    {
                        "title": "模型状态" if is_chinese else "Model status",
                        "value": "未配置主体识别模型" if is_chinese else "No subject recognition model configured",
                        "subtitle": (
                            "避免在没有可靠线索时给出猜测主体。"
                            if is_chinese
                            else "Avoids guessing subjects without reliable clues."
                        ),
                        "confidence": 0.18,
                    }
                ],
            },
            _asset_section(size_kb, is_chinese),
        ],
        "items": [
            {
                "title": "模型状态" if is_chinese else "Model status",
                "value": "未配置主体识别模型" if is_chinese else "No subject recognition model configured",
                "confidence": 0.18,
            }
        ],
    }


def _food_result(
    mode: str,
    locale: Any,
    image_bytes: bytes,
    size_kb: int,
    is_chinese: bool,
    text_recognizer: Optional[TextRecognizer],
    image_classifier: Optional[ImageClassifier],
) -> Mapping[str, Any]:
    lines = _recognized_lines(text_recognizer, image_bytes, locale)
    labels = _classified_labels(image_classifier, image_bytes, locale)
    estimate = estimate_food(lines, labels)
    if estimate is not None:
        evidence_subtitle = f"线索：{estimate.evidence}" if is_chinese else f"Clue: {estimate.evidence}"
        items = [
            {
                "title": "食物线索" if is_chinese else "Food clue",
                "value": estimate.label,
                "subtitle": evidence_subtitle,
                "confidence": estimate.confidence,
            },
            {
                "title": "热量范围" if is_chinese else "Calorie range",
                "value": estimate.calories,
                "subtitle": (
                    "基于本机文字/分类线索的谨慎估算"
                    if is_chinese
                    else "Careful estimate from local text/classification clues"
                ),
                "confidence": estimate.confidence,
            },
        ]
        from_text = estimate.source == "text"
        summary = (
            f"根据图片文字线索估算：{estimate.label}约 {estimate.calories}。"
            if from_text
            else f"根据本机图片分类估算：{estimate.label}约 {estimate.calories}。"
        )
        if not is_chinese:
            summary = (
                f"Estimated from image text clues: {estimate.label}, about {estimate.calories}."
                if from_text
                else f"Estimated from local image classification: {estimate.label}, about {estimate.calories}."
            )
        return {
            "mode": mode,
            "title": "食物估算" if is_chinese else "Food Estimate",
            "summary": summary,
            "text": f"{estimate.label}: {estimate.calories}\n{evidence_subtitle}",
            "language": locale or ("zh-Hans" if is_chinese else "en"),
            "confidence": estimate.confidence,
            "sections": [
                {
                    "title": "热量估算" if is_chinese else "Nutrition estimate",
                    "kind": "nutrition",
                    "items": items,
                },
                _asset_section(size_kb, is_chinese),
            ],
            "items": items,
        }

    return {
        "mode": mode,
        "title": "食物估算" if is_chinese else "Food Estimate",
        "summary": (
            "当前未配置食物识别模型，暂不进行热量估算。"
            if is_chinese
            else "No food recognition model is configured, so calorie estimation is paused."
        ),
        "text": (
            "请接入多模态食物模型后再使用热量估算。"
            if is_chinese
            else "Connect a multimodal food model before using calorie estimates."
        ),
        "language": locale or ("zh-Hans" if is_chinese else "en"),
        "confidence": 0.18,
        "sections": [
            {
                "title": "估算状态" if is_chinese else "Estimate status",
                "kind": "assumptions",
                "items": [
                    {
                        "title": "模型状态" if is_chinese else "Model status",
                        "value": "未配置食物识别模型" if is_chinese else "No food recognition model configured",
                        "subtitle": (
                            "避免在无法识别食材和分量时给出不可靠热量。"
                            if is_chinese
                            else "Avoids giving unreliable calories when ingredients and portions cannot be recognized."
                        ),
                        "confidence": 0.18,
                    },
                    {
                        "title": "拍摄建议" if is_chinese else "Capture tip",
                        "value": "完整拍下餐盘和分量参照物" if is_chinese else "Capture the whole plate with a portion reference",
                        "confidence": 0.9,
                    },
                ],
            },
            _asset_section(size_kb, is_chinese),
        ],
        "items": [
            {
                "title": "模型状态" if is_chinese else "Model status",
                "value": "未配置食物识别模型" if is_chinese else "No food recognition model configured",
                "confidence": 0.18,
            }
        ],
    }


def _recognized_lines(
    text_recognizer: Optional[TextRecognizer],
    image_bytes: bytes,
    locale: Any,
) -> Sequence[RecognizedTextLine]:
    recognizer = text_recognizer or AppleVisionTextRecognizer()
    try:
        raw_lines = recognizer.recognize(image_bytes, locale=str(locale) if locale else None)
    except Exception:
        return []
    normalized: list[RecognizedTextLine] = []
    for line in raw_lines:
        text = str(line.text).strip()
        if not text:
            continue
        normalized.append(RecognizedTextLine(text=text, confidence=_clamp_confidence(float(line.confidence))))
    return normalized


def _classified_labels(
    image_classifier: Optional[ImageClassifier],
    image_bytes: bytes,
    locale: Any,
) -> Sequence[ClassifiedImageLabel]:
    classifier = image_classifier or AppleVisionImageClassifier()
    try:
        raw_labels = classifier.classify(image_bytes, locale=str(locale) if locale else None)
    except Exception:
        return []
    normalized: list[ClassifiedImageLabel] = []
    for label in raw_labels:
        identifier = str(label.identifier).strip()
        if not identifier:
            continue
        normalized.append(
            ClassifiedImageLabel(
                identifier=identifier,
                confidence=_clamp_confidence(float(label.confidence)),
            )
        )
    return normalized


def _line_items(lines: Sequence[RecognizedTextLine], is_chinese: bool) -> list[Mapping[str, Any]]:
    return [
        {
            "title": f"文本 {index + 1}" if is_chinese else f"Text {index + 1}",
            "value": line.text,
            "confidence": _clamp_confidence(float(line.confidence)),
        }
        for index, line in enumerate(lines)
    ]


def _joined_text(lines: Sequence[RecognizedTextLine]) -> str:
    return "\n".join(line.text for line in lines if line.text.strip())


def _average_confidence(lines: Sequence[RecognizedTextLine], default: float) -> float:
    if not lines:
        return default
    return round(sum(_clamp_confidence(float(line.confidence)) for line in lines) / len(lines), 2)


def _average_values(values: Sequence[float], default: float) -> float:
    if not values:
        return default
    return round(sum(_clamp_confidence(float(value)) for value in values) / len(values), 2)


def _average_confidence_from_labels(labels: Sequence[ClassifiedImageLabel], default: float) -> float:
    if not labels:
        return default
    return round(sum(_clamp_confidence(float(label.confidence)) for label in labels) / len(labels), 2)


def _display_label(label: ClassifiedImageLabel) -> str:
    return f"{label.identifier.replace('_', ' ')} ({round(_clamp_confidence(float(label.confidence)) * 100)}%)"


def _clamp_confidence(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value


def _decode_image_bytes(value: Any) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError("image_base64 is required")
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError("image_base64 must be valid base64") from exc


def _asset_section(size_kb: int, is_chinese: bool) -> Mapping[str, Any]:
    return {
        "title": "输入图片" if is_chinese else "Input image",
        "kind": "assumptions",
        "items": [_asset_item(size_kb, is_chinese)],
    }


def _asset_item(size_kb: int, is_chinese: bool) -> Mapping[str, Any]:
    return {
        "title": "文件大小" if is_chinese else "File size",
        "value": f"{size_kb} KB",
        "subtitle": "输入照片已接收" if is_chinese else "Input photo received",
        "confidence": 0.95,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a local Kaka /kaka/vision endpoint.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)

    server = create_vision_endpoint_server(args.host, args.port)
    print(f"Kaka vision endpoint listening on http://{args.host}:{args.port}/kaka/vision", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
