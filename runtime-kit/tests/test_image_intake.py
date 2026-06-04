from kaka_mobile_runtime_kit.image_intake import (
    RecognizedTextLine,
    build_image_intake_result,
)


def test_text_heavy_image_suggests_ocr_and_translate():
    result = build_image_intake_result(
        image_bytes=b"fake",
        locale="zh-Hans",
        recognized_lines=[
            RecognizedTextLine(text="NATIVE WOOD PULP", confidence=0.9),
            RecognizedTextLine(text="100% 原生木浆", confidence=0.86),
            RecognizedTextLine(text="净含量 15g", confidence=0.8),
        ],
    )

    assert result["image_type"] == "text"
    assert result["title"] == "检测到文字"
    assert [item["skill"] for item in result["suggestions"][:2]] == ["ocr", "translate_text"]


def test_non_text_image_suggests_photo_enhance_and_identify():
    result = build_image_intake_result(
        image_bytes=b"fake",
        locale="zh-Hans",
        recognized_lines=[],
    )

    assert result["image_type"] == "photo"
    assert [item["skill"] for item in result["suggestions"][:2]] == ["photo_enhance", "identify_subject"]
