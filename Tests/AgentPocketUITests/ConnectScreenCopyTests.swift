import XCTest
@testable import AgentPocketUI

final class ConnectScreenCopyTests: XCTestCase {
    func testChineseCopyLocalizesConnectHomeAndSettings() {
        let copy = ConnectScreenCopy(
            state: .idle,
            language: .chinese,
            fallbackDeviceName: "我的电脑"
        )

        XCTAssertEqual(copy.connectTitle, "连接我的本机智能体")
        XCTAssertEqual(copy.primaryButtonTitle, "连接")
        XCTAssertEqual(copy.scanCodeTitle, "扫描二维码")
        XCTAssertEqual(copy.nearbyRuntimeDescription, "确认这台 Mac 后，Kaka 会保存一个移动端令牌，下次自动连接。")
        XCTAssertEqual(copy.settingsTitle, "项目设置")
        XCTAssertEqual(copy.languageTitle, "界面语言")
        XCTAssertEqual(copy.deviceName, "我的电脑")
        XCTAssertEqual(copy.onlineTrustedTitle, "点击连接后发现")
        XCTAssertEqual(copy.trustBadgeTitles, ["本地网络", "待确认"])
        XCTAssertFalse(copy.visibleCopy.localizedCaseInsensitiveContains("Connect My Local Agent"))
    }

    func testEnglishCopyDoesNotContainChineseText() {
        let copy = ConnectScreenCopy(
            state: .idle,
            language: .english,
            fallbackDeviceName: "Local Mac"
        )

        XCTAssertEqual(copy.connectTitle, "Connect My Local Agent")
        XCTAssertEqual(copy.primaryButtonTitle, "Connect")
        XCTAssertEqual(copy.scanCodeTitle, "Scan Code")
        XCTAssertEqual(copy.nearbyRuntimeDescription, "Confirm this Mac once. Kaka stores a mobile token and reconnects next time.")
        XCTAssertEqual(copy.settingsTitle, "Project Settings")
        XCTAssertEqual(copy.languageTitle, "Interface Language")
        XCTAssertEqual(copy.onlineTrustedTitle, "Tap Connect to Find")
        XCTAssertEqual(copy.trustBadgeTitles, ["Local Network", "Confirm"])
        XCTAssertFalse(copy.visibleCopy.containsCJKCharacters)
    }

    func testConnectedCopyNamesRuntimeAndShowsTrustedState() {
        let runtime = ConnectedRuntime(
            displayName: "OpenClaw Studio",
            runtime: "openclaw",
            runtimeVersion: "2026.6"
        )

        let copy = ConnectScreenCopy(
            state: .connected(runtime),
            language: .chinese,
            fallbackDeviceName: "我的电脑"
        )

        XCTAssertEqual(copy.deviceName, "OpenClaw Studio")
        XCTAssertEqual(copy.onlineTrustedTitle, "在线 · 已信任")
        XCTAssertEqual(copy.trustBadgeTitles, ["本地网络", "已信任"])
        XCTAssertTrue(copy.visibleCopy.contains("OpenClaw Studio"))
        XCTAssertFalse(copy.visibleCopy.localizedCaseInsensitiveContains("Hermes"))
    }

    func testChineseFailureCopyLocalizesKnownRuntimeDiscoveryFailure() {
        let copy = ConnectScreenCopy(
            state: .failed(message: "No local agent runtime found. Scan a pairing QR or enter an endpoint."),
            language: .chinese,
            fallbackDeviceName: "我的电脑"
        )

        XCTAssertEqual(copy.connectTitle, "连接失败")
        XCTAssertEqual(copy.connectSubtitle, "没有发现本机智能体。请扫描配对二维码，或手动输入本机地址。")
        XCTAssertFalse(copy.visibleCopy.localizedCaseInsensitiveContains("No local agent runtime found"))
        XCTAssertFalse(copy.visibleCopy.localizedCaseInsensitiveContains("enter an endpoint"))
    }
}

private extension String {
    var containsCJKCharacters: Bool {
        unicodeScalars.contains { scalar in
            (0x4E00...0x9FFF).contains(Int(scalar.value))
        }
    }
}
