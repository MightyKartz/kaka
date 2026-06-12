from pathlib import Path


def test_pasteboard_is_read_only_by_clipboard_courier():
    root = Path(__file__).resolve().parents[2]
    matches = []

    for path in (root / "Sources").rglob("*.swift"):
        source = path.read_text(encoding="utf-8")
        if "UIPasteboard" in source:
            matches.append(str(path.relative_to(root)))

    assert matches == ["Sources/AgentPocketUI/ClipboardCourier.swift"]


def test_inbox_paste_action_is_visible_and_explicit():
    root = Path(__file__).resolve().parents[2]
    inbox_view = (root / "Sources" / "AgentPocketUI" / "InboxView.swift").read_text(
        encoding="utf-8"
    )
    app_intents = (
        root / "Sources" / "AgentPocketUI" / "AppIntents" / "KakaAppIntents.swift"
    ).read_text(encoding="utf-8")

    assert 'Label(language == .chinese ? "粘贴" : "Paste", systemImage: "doc.on.clipboard")' in inbox_view
    assert "private let clipboardReader: any ClipboardCourierReading" in inbox_view
    assert "viewModel.importClipboard(reader: clipboardReader)" in inbox_view
    assert "UIPasteboard" not in inbox_view
    assert "importClipboard" not in app_intents
    assert "UIPasteboard" not in app_intents


def test_import_clipboard_production_callers_are_allowlisted():
    root = Path(__file__).resolve().parents[2]
    callers = []

    for path in (root / "Sources").rglob("*.swift"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "importClipboard(" in line:
                callers.append(
                    (
                        str(path.relative_to(root)),
                        line.strip(),
                    )
                )

    expected_callers = [
        (
            "Sources/AgentPocketUI/InboxViewModel.swift",
            "public func importClipboard(",
        ),
        (
            "Sources/AgentPocketUI/InboxView.swift",
            "_ = viewModel.importClipboard(reader: clipboardReader)",
        ),
    ]

    assert sorted(callers) == sorted(expected_callers)
