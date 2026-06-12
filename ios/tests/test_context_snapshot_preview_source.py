from pathlib import Path


def test_context_snapshot_preview_refreshes_initially_included_context():
    source = (
        Path(__file__).resolve().parents[2]
        / "Sources"
        / "AgentPocketUI"
        / "ContextSnapshotPreviewView.swift"
    ).read_text(encoding="utf-8")

    assert ".task" in source
    assert "await viewModel.refreshForInclusionIfNeeded()" in source


def test_inbox_send_guard_only_blocks_context_consuming_universal_intake():
    source = (
        Path(__file__).resolve().parents[2]
        / "Sources"
        / "AgentPocketUI"
        / "InboxView.swift"
    ).read_text(encoding="utf-8")

    assert "item.route == .universalIntake && isContextSnapshotPreparingForSubmission" in source


def test_inbox_voice_draft_is_visible_sheet_not_system_recording():
    root = Path(__file__).resolve().parents[2]
    inbox_view = (root / "Sources" / "AgentPocketUI" / "InboxView.swift").read_text(
        encoding="utf-8"
    )
    app_intents = (
        root / "Sources" / "AgentPocketUI" / "AppIntents" / "KakaAppIntents.swift"
    ).read_text(encoding="utf-8")

    assert "VoiceCaptureView(" in inbox_view
    assert "appendVoiceTranscript" in inbox_view
    assert "case .draft" in inbox_view
    assert "return viewModel.appendVoiceTranscript(transcript)" in inbox_view
    assert ".sheet(item: $voiceCaptureMode)" in inbox_view
    assert "startRecording" not in app_intents


def test_inbox_voice_capture_uses_context_specific_presentation():
    root = Path(__file__).resolve().parents[2]
    inbox_view = (root / "Sources" / "AgentPocketUI" / "InboxView.swift").read_text(
        encoding="utf-8"
    )
    voice_capture = (
        root / "Sources" / "AgentPocketUI" / "VoiceCaptureView.swift"
    ).read_text(encoding="utf-8")

    assert "presentation: voiceCapturePresentation(for: mode)" in inbox_view
    assert "private func voiceCapturePresentation(for mode: VoiceCaptureMode)" in inbox_view
    assert ".inboxDraft(language: language)" in inbox_view
    assert ".inboxInstruction(" in inbox_view
    assert "hasExistingInstruction:" in inbox_view
    assert "presentation: VoiceCapturePresentation = .defaultDraft" in voice_capture


def test_inbox_voice_instruction_updates_existing_item_note():
    root = Path(__file__).resolve().parents[2]
    inbox_view = (root / "Sources" / "AgentPocketUI" / "InboxView.swift").read_text(
        encoding="utf-8"
    )
    instruction_presentation = (
        root / "Sources" / "AgentPocketUI" / "InboxInstructionPresentation.swift"
    ).read_text(encoding="utf-8")
    app_intents = (
        root / "Sources" / "AgentPocketUI" / "AppIntents" / "KakaAppIntents.swift"
    ).read_text(encoding="utf-8")

    assert "Voice Instruction" in instruction_presentation
    assert "updateVoiceInstruction" in inbox_view
    assert "case .instruction" in inbox_view
    assert "item.route == .universalIntake" in inbox_view
    assert "InboxInstructionPresentation(item: item, language: language)" in inbox_view
    assert "clearVoiceInstruction" in inbox_view
    assert "submitPreviewText" in inbox_view
    assert "Edit Instruction" in instruction_presentation
    assert "Clear Instruction" in instruction_presentation
    assert "ForEach(instructionPresentation.templates)" in inbox_view
    assert "applyInstructionTemplate(template.template" in inbox_view
    assert "startRecording" not in app_intents
    assert "instruction templates" not in app_intents.lower()
