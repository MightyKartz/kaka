from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol, Sequence
from urllib import error as urllib_error
from urllib import request as urllib_request


class RecallSearchItem(Protocol):
    item_id: str
    summary: str
    created_at: str

    def to_mobile_bridge(self) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class RecallSearchResult:
    item: RecallSearchItem
    score: float
    match_reason: str
    provider_mode: str = "local_deterministic"

    def to_mobile_bridge(self) -> dict[str, Any]:
        return {
            "item": self.item.to_mobile_bridge(),
            "score": float(self.score),
            "match_reason": self.match_reason,
        }


class RecallSearchProvider(Protocol):
    provider_mode: str

    def search(
        self,
        query: str,
        items: Sequence[RecallSearchItem],
        limit: int,
    ) -> list[RecallSearchResult]:
        ...


class TokenOverlapRecallSearchProvider:
    def __init__(self, provider_mode: str = "local_deterministic") -> None:
        self.provider_mode = provider_mode

    def search(
        self,
        query: str,
        items: Sequence[RecallSearchItem],
        limit: int,
    ) -> list[RecallSearchResult]:
        query_tokens = _tokenize(query)
        if not query_tokens or limit <= 0:
            return []

        query_token_set = set(query_tokens)
        ranked: list[tuple[float, str, str, RecallSearchResult]] = []
        for item in items:
            item_token_set = set(_tokenize(item.summary))
            matched_tokens = sorted(query_token_set & item_token_set)
            if not matched_tokens:
                continue
            score = len(matched_tokens) / len(query_token_set)
            result = RecallSearchResult(
                item=item,
                score=score,
                match_reason=f"Matched recall terms: {', '.join(matched_tokens)}.",
                provider_mode=self.provider_mode,
            )
            ranked.append((score, item.created_at, item.item_id, result))

        ranked.sort(key=lambda result: (-result[0], result[1], result[2]))
        return [result for _, _, _, result in ranked[: max(int(limit), 0)]]


class RuntimeHTTPRecallSearchProvider:
    provider_mode = "provider_backed"

    def __init__(
        self,
        endpoint: str,
        fallback: RecallSearchProvider | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.endpoint = endpoint.strip()
        if not self.endpoint:
            raise ValueError("runtime_http Recall search provider requires an endpoint.")
        self.fallback = fallback or TokenOverlapRecallSearchProvider()
        self.timeout_seconds = timeout_seconds

    def search(
        self,
        query: str,
        items: Sequence[RecallSearchItem],
        limit: int,
    ) -> list[RecallSearchResult]:
        if limit <= 0:
            return []

        fallback_results = self.fallback.search(query=query, items=items, limit=limit)
        item_by_id = {item.item_id: item for item in items}
        payload = {
            "query": query,
            "limit": max(int(limit), 0),
            "items": [_item_payload(item) for item in items],
        }
        try:
            request = urllib_request.Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib_request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
            decoded = json.loads(raw.decode("utf-8"))
        except (OSError, ValueError, urllib_error.HTTPError, urllib_error.URLError, json.JSONDecodeError):
            return fallback_results

        results = _decode_provider_results(decoded, item_by_id=item_by_id, limit=limit)
        return results if results else fallback_results


def build_recall_search_provider(
    name: str = "local",
    endpoint: str = "",
) -> RecallSearchProvider:
    if name == "local":
        return TokenOverlapRecallSearchProvider()
    if name == "fixture":
        return TokenOverlapRecallSearchProvider(provider_mode="provider_backed")
    if name == "runtime_http":
        return RuntimeHTTPRecallSearchProvider(endpoint=endpoint)
    raise ValueError(f"Unsupported Recall search provider: {name}")


def _decode_provider_results(
    decoded: Any,
    item_by_id: dict[str, RecallSearchItem],
    limit: int,
) -> list[RecallSearchResult]:
    if not isinstance(decoded, dict):
        return []
    raw_items = decoded.get("items", [])
    if not isinstance(raw_items, list):
        return []

    results: list[RecallSearchResult] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        item_id = str(raw_item.get("item_id", "")).strip()
        item = item_by_id.get(item_id)
        if item is None:
            continue
        try:
            score = float(raw_item.get("score"))
        except (TypeError, ValueError):
            continue
        match_reason = str(raw_item.get("match_reason", "")).strip() or "Matched runtime Recall provider."
        results.append(
            RecallSearchResult(
                item=item,
                score=score,
                match_reason=match_reason,
                provider_mode="provider_backed",
            )
        )
        if len(results) >= max(int(limit), 0):
            break
    return results


def _item_payload(item: RecallSearchItem) -> dict[str, Any]:
    mobile_item = item.to_mobile_bridge()
    return {
        "item_id": str(mobile_item.get("item_id", "")),
        "summary": str(mobile_item.get("summary", "")),
        "created_at": str(mobile_item.get("created_at", "")),
        "provenance": _safe_recall_provider_provenance(mobile_item.get("provenance", {})),
    }


def _safe_recall_provider_provenance(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    safe: dict[str, str] = {}
    for key in ("source_task_id", "source_inbox_item_id", "source_surface"):
        raw = value.get(key)
        if raw is not None and str(raw):
            safe[key] = str(raw)
    return safe


def _tokenize(value: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    return [_normalize_token(token) for token in tokens if token]


def _normalize_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token
