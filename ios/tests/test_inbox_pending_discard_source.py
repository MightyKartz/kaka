from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_inbox_discard_action_is_visible_confirmed_and_local_only():
    inbox_view = (ROOT / "Sources/AgentPocketUI/InboxView.swift").read_text(encoding="utf-8")

    assert "@State private var pendingDiscardItem: KakaInboxItem?" in inbox_view
    assert "pendingDiscardItem = item" in inbox_view
    assert 'Label(language == .chinese ? "丢弃" : "Discard", systemImage: "trash")' in inbox_view
    assert ".confirmationDialog(" in inbox_view
    assert "discardConfirmationTitle" in inbox_view
    assert "discardConfirmationMessage" in inbox_view
    row_action = inbox_view.split('Label(language == .chinese ? "丢弃" : "Discard", systemImage: "trash")')[0].split("Button {")[-1]
    assert "pendingDiscardItem = item" in row_action
    assert "discardPendingItem" not in row_action
    confirmation_action = inbox_view.split(".confirmationDialog(")[1].split(".task {")[0]
    assert "guard isSubmitting == false" in confirmation_action
    assert "viewModel.items.contains(where: { $0.id == item.id })" in confirmation_action
    assert "viewModel.discardPendingItem(id: item.id)" in inbox_view


def test_discard_pending_item_callers_are_allowlisted():
    callers = []

    for path in (ROOT / "Sources").rglob("*.swift"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "discardPendingItem" in line:
                callers.append((str(path.relative_to(ROOT)), line.strip()))

    expected_callers = [
        (
            "Sources/AgentPocketUI/InboxView.swift",
            "_ = viewModel.discardPendingItem(id: item.id)",
        ),
        (
            "Sources/AgentPocketUI/InboxViewModel.swift",
            "public func discardPendingItem(id: UUID) -> Bool {",
        ),
    ]
    assert sorted(callers) == sorted(expected_callers)


def test_inbox_discard_does_not_add_background_submit_recall_or_bridge_paths():
    app_intents = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "Sources/AgentPocketUI/AppIntents").rglob("*.swift")
    )
    bridge_models = (ROOT / "Sources/AgentPocketCore/MobileBridgeModels.swift").read_text(encoding="utf-8")
    bridge_http = (ROOT / "Sources/AgentPocketCore/MobileBridgeHTTPClient.swift").read_text(encoding="utf-8")

    assert "DiscardKakaInboxItemIntent" not in app_intents
    assert "discardPendingItem" not in app_intents
    assert "submitRecallAction" not in app_intents
    assert "deleteRecallItem" not in app_intents
    assert "discardPendingItem" not in bridge_models
    assert "DiscardKakaInboxItem" not in bridge_models
    assert "/mobile/v1/inbox" not in bridge_http
