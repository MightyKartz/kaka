from __future__ import annotations

import base64
import json
from urllib import request

from kaka_mobile_runtime_kit.vision_server import (
    RecognizedTextLine,
    build_vision_result,
    create_vision_endpoint_server,
)


def _encoded_image_payload(mode: str, locale: str = "zh-Hans") -> dict[str, object]:
    return {
        "schema_version": 1,
        "task": "vision",
        "mode": mode,
        "instruction": "Read visible text.",
        "locale": locale,
        "image_base64": base64.b64encode(b"fake-image").decode("ascii"),
    }


def test_scan_result_uses_recognized_text_lines():
    class FakeRecognizer:
        def recognize(self, image_bytes, locale=None):
            assert image_bytes == b"fake-image"
            assert locale == "zh-Hans"
            return [
                RecognizedTextLine(text="NATIVE WOOD PULP", confidence=0.92),
                RecognizedTextLine(text="100% 原生木浆", confidence=0.88),
            ]

    vision = build_vision_result(_encoded_image_payload("scan"), text_recognizer=FakeRecognizer())

    assert vision["mode"] == "scan"
    assert vision["text"] == "NATIVE WOOD PULP\n100% 原生木浆"
    assert vision["summary"] == "识别到 2 行文字。"
    assert vision["confidence"] == 0.9
    assert vision["sections"][0]["kind"] == "ocr"
    assert vision["sections"][0]["items"][0]["title"] == "文本 1"
    assert vision["sections"][0]["items"][0]["value"] == "NATIVE WOOD PULP"
    assert vision["sections"][0]["items"][1]["value"] == "100% 原生木浆"


def test_translate_result_uses_recognized_source_text_without_endpoint_placeholder():
    class FakeRecognizer:
        def recognize(self, image_bytes, locale=None):
            assert image_bytes == b"fake-image"
            return [RecognizedTextLine(text="LIME AND LICORICE", confidence=0.9)]

    vision = build_vision_result(_encoded_image_payload("translate"), text_recognizer=FakeRecognizer())

    visible_copy = json.dumps(vision, ensure_ascii=False).lower()
    assert "endpoint" not in visible_copy
    assert "等待真实" not in visible_copy
    assert "开发实现" not in visible_copy
    assert vision["text"] == "LIME AND LICORICE"
    assert vision["sections"][0]["items"][0]["title"] == "原文"
    assert vision["sections"][0]["items"][0]["value"] == "LIME AND LICORICE"
    assert vision["sections"][0]["items"][1]["title"] == "译文"


def test_translate_result_translates_known_english_lines_to_chinese():
    class FakeRecognizer:
        def recognize(self, image_bytes, locale=None):
            return [
                RecognizedTextLine(
                    text="Stronger color, contrast, and subject separation for sharing.",
                    confidence=0.92,
                )
            ]

    vision = build_vision_result(_encoded_image_payload("translate"), text_recognizer=FakeRecognizer())

    assert vision["summary"] == "已翻译 1 行文字。"
    assert vision["text"] == "更强的色彩、对比度和主体分离，适合分享。"
    assert vision["sections"][0]["items"][0]["title"] == "原文"
    assert vision["sections"][0]["items"][1]["title"] == "译文"
    assert vision["sections"][0]["items"][1]["value"] == "更强的色彩、对比度和主体分离，适合分享。"


def test_scan_result_without_text_returns_user_guidance_not_debug_copy():
    class EmptyRecognizer:
        def recognize(self, image_bytes, locale=None):
            return []

    vision = build_vision_result(_encoded_image_payload("scan"), text_recognizer=EmptyRecognizer())

    visible_copy = json.dumps(vision, ensure_ascii=False).lower()
    assert "endpoint" not in visible_copy
    assert "等待真实" not in visible_copy
    assert "开发实现" not in visible_copy
    assert vision["summary"] == "没有识别到清晰文字。请靠近文字并保持画面稳定。"
    assert vision["sections"][0]["items"][0]["value"] == "未识别到文字"


def test_identify_result_does_not_return_endpoint_placeholder():
    vision = build_vision_result(_encoded_image_payload("identify"))

    visible_copy = json.dumps(vision, ensure_ascii=False).lower()
    assert "endpoint" not in visible_copy
    assert "等待真实" not in visible_copy
    assert "开发实现" not in visible_copy
    assert vision["title"] == "识别结果"
    assert vision["confidence"] <= 0.2
    assert vision["sections"][0]["items"][0]["value"] == "未配置主体识别模型"


def test_identify_result_uses_recognized_text_clues_when_available():
    class FakeRecognizer:
        def recognize(self, image_bytes, locale=None):
            return [RecognizedTextLine(text="iPhone 16 Pro", confidence=0.87)]

    vision = build_vision_result(_encoded_image_payload("identify"), text_recognizer=FakeRecognizer())

    assert vision["title"] == "识别结果"
    assert vision["summary"] == "根据图片文字线索识别到：iPhone。"
    assert vision["confidence"] > 0.4
    assert vision["sections"][0]["kind"] == "candidates"
    assert vision["sections"][0]["items"][0]["value"] == "iPhone"
    assert vision["sections"][0]["items"][0]["subtitle"] == "线索：iPhone 16 Pro"


def test_food_result_does_not_return_placeholder_calorie_estimate():
    vision = build_vision_result(_encoded_image_payload("food"))

    visible_copy = json.dumps(vision, ensure_ascii=False).lower()
    assert "320-460" not in visible_copy
    assert "endpoint" not in visible_copy
    assert "等待真实" not in visible_copy
    assert "开发估算" not in visible_copy
    assert vision["title"] == "食物估算"
    assert vision["confidence"] <= 0.2
    assert vision["sections"][0]["items"][0]["value"] == "未配置食物识别模型"


def test_food_result_estimates_from_menu_text_clues():
    class FakeRecognizer:
        def recognize(self, image_bytes, locale=None):
            return [RecognizedTextLine(text="牛肉面", confidence=0.88)]

    vision = build_vision_result(_encoded_image_payload("food"), text_recognizer=FakeRecognizer())

    assert vision["title"] == "食物估算"
    assert vision["summary"] == "根据图片文字线索估算：牛肉面约 550-850 kcal。"
    assert vision["confidence"] > 0.4
    assert vision["sections"][0]["kind"] == "nutrition"
    assert vision["sections"][0]["items"][0]["title"] == "食物线索"
    assert vision["sections"][0]["items"][0]["value"] == "牛肉面"
    assert vision["sections"][0]["items"][1]["value"] == "550-850 kcal"


def test_vision_endpoint_returns_structured_food_result():
    server = create_vision_endpoint_server("127.0.0.1", 0)
    try:
        host, port = server.server_address
        thread = server.serve_in_background()
        payload = {
            "schema_version": 1,
            "task": "vision",
            "mode": "food",
            "instruction": "Estimate calories.",
            "locale": "zh-Hans",
            "image_base64": base64.b64encode(b"fake-image").decode("ascii"),
        }
        response = request.urlopen(
            request.Request(
                f"http://{host}:{port}/kaka/vision",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            ),
            timeout=5,
        )

        body = json.loads(response.read().decode("utf-8"))

        assert body["vision"]["mode"] == "food"
        assert body["vision"]["title"] == "食物估算"
        assert body["vision"]["sections"][0]["kind"] == "assumptions"
        assert body["vision"]["sections"][0]["items"][0]["title"] == "模型状态"
        assert body["vision"]["sections"][0]["items"][0]["value"] == "未配置食物识别模型"
        assert thread.is_alive()
    finally:
        server.shutdown()
        server.server_close()


def test_vision_endpoint_rejects_bad_path():
    server = create_vision_endpoint_server("127.0.0.1", 0)
    try:
        host, port = server.server_address
        server.serve_in_background()
        payload = {"mode": "identify", "image_base64": ""}
        req = request.Request(
            f"http://{host}:{port}/wrong",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            request.urlopen(req, timeout=5)
        except Exception as exc:
            assert "HTTP Error 404" in str(exc)
        else:
            raise AssertionError("Expected /wrong to return 404")
    finally:
        server.shutdown()
        server.server_close()
