import plistlib
from pathlib import Path


def test_info_plist_declares_local_network_bonjour_service():
    info_plist = Path(__file__).resolve().parents[1] / "AgentPocket" / "Info.plist"

    with info_plist.open("rb") as handle:
        plist = plistlib.load(handle)

    assert plist["NSLocalNetworkUsageDescription"]
    assert plist["NSAppTransportSecurity"]["NSAllowsLocalNetworking"] is True
    assert "_agent-pocket._tcp" in plist["NSBonjourServices"]


def test_info_plist_declares_live_activity_support():
    info_plist = Path(__file__).resolve().parents[1] / "AgentPocket" / "Info.plist"

    with info_plist.open("rb") as handle:
        plist = plistlib.load(handle)

    assert plist["NSSupportsLiveActivities"] is True


def test_task_activity_widget_declares_widgetkit_extension():
    widget_plist = Path(__file__).resolve().parents[1] / "AgentPocketTaskActivityWidget" / "Info.plist"

    with widget_plist.open("rb") as handle:
        plist = plistlib.load(handle)

    extension = plist["NSExtension"]
    assert extension["NSExtensionPointIdentifier"] == "com.apple.widgetkit-extension"
    assert "NSExtensionPrincipalClass" not in extension


def test_project_embeds_task_activity_widget_extension():
    project = Path(__file__).resolve().parents[1] / "AgentPocket.xcodeproj" / "project.pbxproj"

    text = project.read_text(encoding="utf-8")

    assert "AgentPocketTaskActivityWidget.appex" in text
    assert "AgentPocketTaskActivityWidget.appex in Embed App Extensions" in text


def test_share_extension_declares_share_services():
    extension_plist = Path(__file__).resolve().parents[1] / "KakaShareExtension" / "Info.plist"

    with extension_plist.open("rb") as handle:
        plist = plistlib.load(handle)

    extension = plist["NSExtension"]
    activation = extension["NSExtensionAttributes"]["NSExtensionActivationRule"]

    assert extension["NSExtensionPointIdentifier"] == "com.apple.share-services"
    assert activation["NSExtensionActivationSupportsText"] is True
    assert activation["NSExtensionActivationSupportsWebURLWithMaxCount"] == 1
    assert activation["NSExtensionActivationSupportsImageWithMaxCount"] == 1
    assert activation["NSExtensionActivationSupportsFileWithMaxCount"] == 1


def test_app_and_share_extension_use_same_app_group():
    ios_root = Path(__file__).resolve().parents[1]
    app_entitlements = ios_root / "AgentPocket" / "AgentPocket.entitlements"
    extension_entitlements = ios_root / "KakaShareExtension" / "KakaShareExtension.entitlements"

    with app_entitlements.open("rb") as handle:
        app = plistlib.load(handle)
    with extension_entitlements.open("rb") as handle:
        extension = plistlib.load(handle)

    app_groups = app["com.apple.security.application-groups"]
    extension_groups = extension["com.apple.security.application-groups"]
    assert app_groups == extension_groups
    assert "group.dev.kartz.Kaka" in app_groups


def test_system_surfaces_do_not_add_background_or_siri_entitlements():
    ios_root = Path(__file__).resolve().parents[1]
    app_entitlements = ios_root / "AgentPocket" / "AgentPocket.entitlements"

    with app_entitlements.open("rb") as handle:
        app = plistlib.load(handle)

    assert set(app.keys()) == {"com.apple.security.application-groups"}
    assert "aps-environment" not in app
    assert "com.apple.developer.siri" not in app


def test_action_button_handoff_does_not_add_new_entitlements():
    ios_root = Path(__file__).resolve().parents[1]
    app_entitlements = ios_root / "AgentPocket" / "AgentPocket.entitlements"

    with app_entitlements.open("rb") as handle:
        app = plistlib.load(handle)

    assert set(app.keys()) == {"com.apple.security.application-groups"}
    assert "com.apple.developer.siri" not in app
    assert "aps-environment" not in app
