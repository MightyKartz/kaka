from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_inbox_files_import_is_visible_and_reviewed():
    source = (ROOT / "Sources/AgentPocketUI/InboxView.swift").read_text()
    assert ".fileImporter(" in source
    assert "InboxFileImporter.supportedContentTypes" in source
    assert "viewModel.importFile(from:" in source


def test_file_import_does_not_add_mobile_bridge_or_app_intent_submit_path():
    app_intents = (ROOT / "Sources/AgentPocketUI/AppIntents/KakaAppIntents.swift").read_text()
    assert "ImportKakaFileIntent" not in app_intents
    assert "submitFile" not in app_intents
    assert "file_picker" not in app_intents
    bridge_models = (ROOT / "Sources/AgentPocketCore/MobileBridgeModels.swift").read_text()
    assert "file_picker" not in bridge_models
