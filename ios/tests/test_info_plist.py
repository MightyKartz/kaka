import plistlib
from pathlib import Path


def test_info_plist_declares_local_network_bonjour_service():
    info_plist = Path(__file__).resolve().parents[1] / "AgentPocket" / "Info.plist"

    with info_plist.open("rb") as handle:
        plist = plistlib.load(handle)

    assert plist["NSLocalNetworkUsageDescription"]
    assert plist["NSAppTransportSecurity"]["NSAllowsLocalNetworking"] is True
    assert "_agent-pocket._tcp" in plist["NSBonjourServices"]
