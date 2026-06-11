from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from kaka_mobile_runtime_kit.recall_search import (
    RuntimeHTTPRecallSearchProvider,
    TokenOverlapRecallSearchProvider,
)
from kaka_mobile_runtime_kit.runtime_store import RuntimeRecallItem


def test_token_overlap_provider_ranks_without_index_leakage():
    provider = TokenOverlapRecallSearchProvider()
    items = [
        RuntimeRecallItem(
            item_id="recall_0001",
            summary="Answer launch summaries in Chinese.",
            created_at="2026-06-05T09:30:00Z",
            source_surface="voice",
        ),
        RuntimeRecallItem(
            item_id="recall_0002",
            summary="Use concise photo edit recipes.",
            created_at="2026-06-05T09:31:00Z",
            source_surface="image_conversation",
        ),
    ]

    results = provider.search("launch summary language", items, limit=5)
    rendered = json.dumps([result.to_mobile_bridge() for result in results], ensure_ascii=False)

    assert [result.item.item_id for result in results] == ["recall_0001"]
    assert results[0].score > 0
    assert "launch" in results[0].match_reason.lower()
    assert "embedding" not in rendered


def test_runtime_http_provider_posts_sanitized_candidates_and_validates_response():
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            received["path"] = self.path
            received["payload"] = json.loads(self.rfile.read(length).decode("utf-8"))
            body = json.dumps(
                {
                    "items": [
                        {
                            "item_id": "recall_0002",
                            "score": 0.98,
                            "match_reason": "Matched provider-side summary preference.",
                        },
                        {
                            "item_id": "unknown",
                            "score": 0.97,
                            "match_reason": "This should be ignored.",
                        },
                        {
                            "item_id": "recall_0001",
                            "score": "bad-score",
                            "match_reason": "This should be ignored.",
                        },
                    ]
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_address[1]}/kaka/recall/search"

    try:
        provider = RuntimeHTTPRecallSearchProvider(endpoint=endpoint, timeout_seconds=2)
        items = [
            RuntimeRecallItem(
                item_id="recall_0001",
                summary="Answer launch summaries in Chinese.",
                created_at="2026-06-05T09:30:00Z",
                source_surface="voice",
            ),
            RuntimeRecallItem(
                item_id="recall_0002",
                summary="Prefer provider-ranked launch notes.",
                created_at="2026-06-05T09:31:00Z",
                source_surface="inbox",
            ),
        ]

        results = provider.search("launch summary language", items, limit=5)
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    rendered_request = json.dumps(received["payload"], ensure_ascii=False, sort_keys=True)
    rendered_results = json.dumps([result.to_mobile_bridge() for result in results], ensure_ascii=False)
    assert received["path"] == "/kaka/recall/search"
    assert received["payload"]["query"] == "launch summary language"
    assert received["payload"]["limit"] == 5
    assert [item["item_id"] for item in received["payload"]["items"]] == ["recall_0001", "recall_0002"]
    assert "embedding" not in rendered_request
    assert "sqlite" not in rendered_request.lower()
    assert [result.item.item_id for result in results] == ["recall_0002"]
    assert results[0].score == 0.98
    assert results[0].match_reason == "Matched provider-side summary preference."
    assert "unknown" not in rendered_results


def test_runtime_http_provider_allowlists_outbound_provenance():
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            received["payload"] = json.loads(self.rfile.read(length).decode("utf-8"))
            body = json.dumps(
                {
                    "items": [
                        {
                            "item_id": "recall_0001",
                            "score": 0.91,
                            "match_reason": "Matched safe provenance.",
                        }
                    ]
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    class LeakyRecallItem:
        item_id = "recall_0001"
        summary = "Answer launch summaries in Chinese."
        created_at = "2026-06-05T09:30:00Z"

        def to_mobile_bridge(self):
            return {
                "item_id": self.item_id,
                "summary": self.summary,
                "created_at": self.created_at,
                "provenance": {
                    "source_task_id": "task_123",
                    "source_inbox_item_id": "inbox_123",
                    "source_surface": "voice",
                    "runtime_store_path": "/private/kaka.sqlite3",
                    "provider_endpoint": "https://api.example.com/recall",
                    "raw_embeddings": [0.1, 0.2],
                },
            }

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_address[1]}/kaka/recall/search"

    try:
        provider = RuntimeHTTPRecallSearchProvider(endpoint=endpoint, timeout_seconds=2)
        provider.search("launch summary", [LeakyRecallItem()], limit=5)
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    provenance = received["payload"]["items"][0]["provenance"]
    rendered_request = json.dumps(received["payload"], ensure_ascii=False, sort_keys=True)
    assert provenance == {
        "source_task_id": "task_123",
        "source_inbox_item_id": "inbox_123",
        "source_surface": "voice",
    }
    assert "runtime_store_path" not in rendered_request
    assert "provider_endpoint" not in rendered_request
    assert "raw_embeddings" not in rendered_request


def test_runtime_http_provider_falls_back_to_local_provider_on_error():
    provider = RuntimeHTTPRecallSearchProvider(
        endpoint="http://127.0.0.1:1/not-running",
        timeout_seconds=0.2,
    )
    items = [
        RuntimeRecallItem(
            item_id="recall_0001",
            summary="Answer launch summaries in Chinese.",
            created_at="2026-06-05T09:30:00Z",
        )
    ]

    results = provider.search("launch summary language", items, limit=5)

    assert [result.item.item_id for result in results] == ["recall_0001"]
    assert results[0].provider_mode == "local_deterministic"


def test_runtime_http_provider_falls_back_to_local_provider_on_malformed_endpoint():
    provider = RuntimeHTTPRecallSearchProvider(endpoint="not-a-url", timeout_seconds=0.2)
    items = [
        RuntimeRecallItem(
            item_id="recall_0001",
            summary="Answer launch summaries in Chinese.",
            created_at="2026-06-05T09:30:00Z",
        )
    ]

    results = provider.search("launch summary language", items, limit=5)

    assert [result.item.item_id for result in results] == ["recall_0001"]
    assert results[0].provider_mode == "local_deterministic"


def test_runtime_http_provider_requires_endpoint():
    try:
        RuntimeHTTPRecallSearchProvider(endpoint="")
    except ValueError as error:
        assert "endpoint" in str(error)
    else:
        raise AssertionError("runtime_http provider should require an endpoint")
