from pathlib import Path


def test_inbox_result_recall_uses_source_inbox_item_id():
    root = Path(__file__).resolve().parents[2]
    inbox_view = (
        root / "Sources" / "AgentPocketUI" / "InboxView.swift"
    ).read_text(encoding="utf-8")
    app_intents = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "Sources" / "AgentPocketUI" / "AppIntents").rglob("*.swift")
    )

    assert "sourceInboxItemID: context?.sourceInboxItemID" in inbox_view
    assert "Context Snapshot selected; supported runtimes receive it with this task." in inbox_view
    assert "submitRecallAction" not in app_intents
    assert "RecallActionRequest" not in app_intents
