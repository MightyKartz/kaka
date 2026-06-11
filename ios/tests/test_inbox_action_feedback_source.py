from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_inbox_feedback_banner_is_visible_and_local_only():
    inbox_view = (ROOT / "Sources/AgentPocketUI/InboxView.swift").read_text(encoding="utf-8")
    presentation_path = ROOT / "Sources/AgentPocketUI/InboxActionFeedbackPresentation.swift"

    assert presentation_path.exists()
    presentation = presentation_path.read_text(encoding="utf-8")
    assert "InboxActionFeedbackPresentation(" in inbox_view
    assert "viewModel.state" in inbox_view
    assert "viewModel.progressText" in inbox_view
    assert "feedbackBanner(" in inbox_view
    assert "viewModel.dismissFailure()" in inbox_view
    assert "case .failed(let failureMessage)" in presentation
    assert "case .submitting" in presentation


def test_inbox_feedback_does_not_add_runtime_recall_or_system_actions():
    forbidden_in_view = [
        "retry",
        "cancelTask",
        "deleteRecallItem",
        "submitRecallAction",
        "/mobile/v1/inbox",
        "DiscardKakaInboxItemIntent",
    ]
    inbox_view = (ROOT / "Sources/AgentPocketUI/InboxView.swift").read_text(encoding="utf-8")
    for forbidden in forbidden_in_view:
        assert forbidden not in inbox_view

    app_intents = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "Sources/AgentPocketUI/AppIntents").rglob("*.swift")
    )
    bridge_models = (ROOT / "Sources/AgentPocketCore/MobileBridgeModels.swift").read_text(encoding="utf-8")
    bridge_http = (ROOT / "Sources/AgentPocketCore/MobileBridgeHTTPClient.swift").read_text(encoding="utf-8")

    assert "InboxActionFeedback" not in app_intents
    assert "InboxActionFeedback" not in bridge_models
    assert "/mobile/v1/inbox" not in bridge_http
