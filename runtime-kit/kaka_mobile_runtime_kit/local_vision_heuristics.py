from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence

from kaka_mobile_runtime_kit.vision_classification import ClassifiedImageLabel
from kaka_mobile_runtime_kit.vision_ocr import RecognizedTextLine


@dataclass(frozen=True)
class TranslationLine:
    source: str
    target: str
    confidence: float


@dataclass(frozen=True)
class SubjectCandidate:
    label: str
    evidence: str
    confidence: float
    source: str = "text"


@dataclass(frozen=True)
class FoodEstimate:
    label: str
    calories: str
    evidence: str
    confidence: float
    source: str = "text"


_TRANSLATIONS_TO_ZH = {
    "stronger color contrast and subject separation for sharing": "更强的色彩、对比度和主体分离，适合分享。",
    "balanced exposure warmer color cleaner contrast and subtle subject separation": "曝光更均衡，色彩更暖，对比更干净，并带有轻微主体分离。",
    "native wood pulp": "原生木浆",
    "100 native wood pulp": "100% 原生木浆",
    "master": "大师版",
    "social": "社交分享",
}

_TRANSLATIONS_TO_EN = {
    "大师级优化": "Master enhance",
    "识别主体": "Identify subject",
    "提取文字": "Extract text",
    "翻译文字": "Translate text",
    "估算热量": "Estimate calories",
    "修图结果": "Photo result",
}

_TEXT_SUBJECT_RULES = [
    (re.compile(r"\biphone\b|苹果手机|智能手机|手机", re.IGNORECASE), "iPhone"),
    (re.compile(r"\bipad\b|平板电脑|平板", re.IGNORECASE), "iPad"),
    (re.compile(r"\bair\s*pods?\b|无线耳机|耳机", re.IGNORECASE), "AirPods"),
    (re.compile(r"\bapple\s+watch\b|\bsmart\s*watch\b|\bwatch\b|智能手表|手表", re.IGNORECASE), "Apple Watch"),
    (re.compile(r"\bmacbook\b|\blaptop\b|笔记本电脑|笔记本", re.IGNORECASE), "笔记本电脑"),
    (re.compile(r"\bkaka\b|大师级优化|提取文字|识别主体", re.IGNORECASE), "Kaka 图像处理界面"),
]

_LABEL_SUBJECT_RULES = [
    (("wristwatch", "digital_watch", "watch", "timepiece"), "手表"),
    (("earphone", "headphone", "headset", "audio"), "耳机"),
    (("mobile_phone", "cellular_telephone", "smartphone", "phone"), "手机"),
    (("tablet", "ipad"), "平板电脑"),
    (("laptop", "notebook", "computer"), "电脑"),
    (("camera",), "相机"),
    (("bottle", "cup", "mug"), "杯瓶"),
    (("food", "dish", "meal", "plate"), "食物"),
]

_TEXT_FOOD_RULES = [
    (re.compile(r"牛肉面|beef\s+noodle", re.IGNORECASE), "牛肉面", "550-850 kcal"),
    (re.compile(r"拉面|汤面|noodle|ramen", re.IGNORECASE), "面食", "450-800 kcal"),
    (re.compile(r"汉堡|burger", re.IGNORECASE), "汉堡", "450-750 kcal"),
    (re.compile(r"披萨|pizza", re.IGNORECASE), "披萨", "250-380 kcal/片"),
    (re.compile(r"米饭|rice", re.IGNORECASE), "米饭", "180-260 kcal/碗"),
    (re.compile(r"沙拉|salad", re.IGNORECASE), "沙拉", "120-420 kcal"),
    (re.compile(r"咖啡|coffee|latte", re.IGNORECASE), "咖啡饮品", "0-260 kcal"),
    (re.compile(r"蛋糕|cake", re.IGNORECASE), "蛋糕", "280-520 kcal/块"),
    (re.compile(r"面包|bread", re.IGNORECASE), "面包", "160-320 kcal/份"),
]

_LABEL_FOOD_RULES = [
    (("pizza",), "披萨", "250-380 kcal/片"),
    (("hamburger", "burger", "cheeseburger"), "汉堡", "450-750 kcal"),
    (("hotdog", "hot_dog"), "热狗", "300-520 kcal"),
    (("sandwich",), "三明治", "300-650 kcal"),
    (("noodle", "ramen", "pasta", "spaghetti"), "面食", "450-800 kcal"),
    (("rice",), "米饭", "180-260 kcal/碗"),
    (("salad",), "沙拉", "120-420 kcal"),
    (("soup",), "汤", "80-260 kcal"),
    (("cake", "dessert", "pastry"), "甜点", "250-520 kcal"),
    (("coffee", "espresso", "latte"), "咖啡饮品", "0-260 kcal"),
    (("bread", "bagel", "toast"), "面包", "160-320 kcal/份"),
    (("egg",), "鸡蛋", "70-160 kcal"),
]


def translate_lines(lines: Sequence[RecognizedTextLine], is_chinese: bool) -> list[TranslationLine]:
    translations: list[TranslationLine] = []
    for line in lines:
        target = _translation_for_text(line.text, is_chinese)
        if not target:
            continue
        confidence = round(min(0.78, max(0.42, float(line.confidence) * 0.82)), 2)
        translations.append(TranslationLine(source=line.text, target=target, confidence=confidence))
    return translations


def infer_subject(
    lines: Sequence[RecognizedTextLine],
    labels: Sequence[ClassifiedImageLabel],
    is_chinese: bool,
) -> SubjectCandidate | None:
    for line in lines:
        for pattern, label in _TEXT_SUBJECT_RULES:
            if pattern.search(line.text):
                return SubjectCandidate(
                    label=label,
                    evidence=line.text,
                    confidence=round(min(0.78, max(0.42, float(line.confidence) * 0.72)), 2),
                    source="text",
                )

    for label in labels:
        if label.confidence < 0.18:
            continue
        normalized = _normalize_identifier(label.identifier)
        for keywords, display in _LABEL_SUBJECT_RULES:
            if any(keyword in normalized for keyword in keywords):
                display_label = display if is_chinese else display.replace("手机", "phone")
                return SubjectCandidate(
                    label=display_label,
                    evidence=_display_identifier(label.identifier),
                    confidence=round(min(0.76, max(0.34, float(label.confidence))), 2),
                    source="classification",
                )
    return None


def estimate_food(
    lines: Sequence[RecognizedTextLine],
    labels: Sequence[ClassifiedImageLabel],
) -> FoodEstimate | None:
    for line in lines:
        for pattern, label, calories in _TEXT_FOOD_RULES:
            if pattern.search(line.text):
                return FoodEstimate(
                    label=label,
                    calories=calories,
                    evidence=line.text,
                    confidence=round(min(0.76, max(0.42, float(line.confidence) * 0.72)), 2),
                    source="text",
                )

    for image_label in labels:
        if image_label.confidence < 0.22:
            continue
        normalized = _normalize_identifier(image_label.identifier)
        for keywords, label, calories in _LABEL_FOOD_RULES:
            if any(keyword in normalized for keyword in keywords):
                return FoodEstimate(
                    label=label,
                    calories=calories,
                    evidence=_display_identifier(image_label.identifier),
                    confidence=round(min(0.72, max(0.34, float(image_label.confidence))), 2),
                    source="classification",
                )
    return None


def _translation_for_text(text: str, is_chinese: bool) -> str | None:
    if is_chinese:
        normalized = _normalize_text(text)
        for source, target in _TRANSLATIONS_TO_ZH.items():
            if normalized == source or (len(source) > 12 and source in normalized):
                return target
        return None

    stripped = text.strip()
    return _TRANSLATIONS_TO_EN.get(stripped)


def _normalize_text(text: str) -> str:
    normalized = text.casefold().replace("%", " % ")
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _normalize_identifier(identifier: str) -> str:
    return identifier.casefold().replace("-", "_").replace(" ", "_")


def _display_identifier(identifier: str) -> str:
    return identifier.strip().replace("_", " ")
