import plistlib
from pathlib import Path


def test_info_plist_declares_local_network_bonjour_service():
    info_plist = Path(__file__).resolve().parents[1] / "AgentPocket" / "Info.plist"

    with info_plist.open("rb") as handle:
        plist = plistlib.load(handle)

    assert plist["NSLocalNetworkUsageDescription"]
    assert plist["NSAppTransportSecurity"]["NSAllowsLocalNetworking"] is True
    assert "_agent-pocket._tcp" in plist["NSBonjourServices"]


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
