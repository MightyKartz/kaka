from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_inbox_pending_item_review_details_is_visible_and_row_level():
    inbox_view = (ROOT / "Sources/AgentPocketUI/InboxView.swift").read_text(encoding="utf-8")
    presentation_path = ROOT / "Sources/AgentPocketUI/InboxPendingItemReviewPresentation.swift"

    assert presentation_path.exists()
    assert "@State private var expandedReviewItemIDs: Set<UUID>" in inbox_view
    assert "InboxPendingItemReviewPresentation(" in inbox_view
    assert "contextIncluded:" in inbox_view
    assert "contextSnapshotViewModel.includeContext" in inbox_view
    assert "reviewDetails(" in inbox_view
    assert "toggleReviewDetails(for: item.id)" in inbox_view
    assert '"info.circle"' in inbox_view


def test_inbox_pending_item_review_details_stays_client_side_and_local_only():
    forbidden = [
        "URLSession",
        "Data(contentsOf:",
        "FileManager",
        "PDFKit",
        "VNRecognizeTextRequest",
        "startAccessingSecurityScopedResource",
        "removeItem",
        "/mobile/v1/inbox",
        "submitRecallAction",
        "deleteRecallItem",
        "RetryInbox",
        "CancelRuntimeTask",
    ]

    sources = [
        ROOT / "Sources/AgentPocketUI/InboxPendingItemReviewPresentation.swift",
        ROOT / "Sources/AgentPocketUI/InboxView.swift",
    ]
    for path in sources:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source

    app_intents = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "Sources/AgentPocketUI/AppIntents").rglob("*.swift")
    )
    bridge_models = (ROOT / "Sources/AgentPocketCore/MobileBridgeModels.swift").read_text(encoding="utf-8")
    bridge_http = (ROOT / "Sources/AgentPocketCore/MobileBridgeHTTPClient.swift").read_text(encoding="utf-8")

    assert "InboxPendingItemReview" not in app_intents
    assert "InboxPendingItemReview" not in bridge_models
    assert "/mobile/v1/inbox" not in bridge_http
