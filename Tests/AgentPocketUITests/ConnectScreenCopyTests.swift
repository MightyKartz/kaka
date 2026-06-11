import XCTest
@testable import AgentPocketUI

final class ConnectScreenCopyTests: XCTestCase {
    func testDefaultLanguageFollowsEnglishSystemPreference() {
        XCTAssertEqual(
            AppLanguage.resolved(storedValue: nil, preferredLanguages: ["en-US", "zh-Hans"]),
            .english
        )
    }

    func testDefaultLanguageFollowsChineseSystemPreference() {
        XCTAssertEqual(
            AppLanguage.resolved(storedValue: nil, preferredLanguages: ["zh-Hans-CN", "en-US"]),
            .chinese
        )
    }

    func testStoredLanguageNoLongerOverridesSystemPreference() {
        XCTAssertEqual(
            AppLanguage.resolved(storedValue: AppLanguage.chinese.rawValue, preferredLanguages: ["en-US"]),
            .english
        )
    }

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

    func testChineseFailureCopyCoversKnownPairingAndRestoreFailures() {
        let cases: [(String, String)] = [
            ("Pairing code expired.", "配对二维码已过期。请在本机运行时刷新二维码后重新扫码。"),
            ("Pairing code already used. Scan a new QR code.", "这个配对二维码已经使用过。请在本机运行时生成新的二维码。"),
            ("QR code is not a Kaka pairing code.", "这不是 Kaka 配对二维码。请扫描本机运行时显示的 Kaka Mobile Bridge 二维码。"),
            ("Could not restore local agent connection.", "无法恢复已保存连接。请确认本机运行时正在运行，或重新扫码配对。"),
            ("Could not forget local agent connection.", "无法清除已保存连接。请稍后重试。")
        ]

        for (message, expectedSubtitle) in cases {
            let copy = ConnectScreenCopy(
                state: .failed(message: message),
                language: .chinese,
                fallbackDeviceName: "我的电脑"
            )

            XCTAssertEqual(copy.connectTitle, "连接失败")
            XCTAssertEqual(copy.connectSubtitle, expectedSubtitle)
        }
    }
}

private extension String {
    var containsCJKCharacters: Bool {
        unicodeScalars.contains { scalar in
            (0x4E00...0x9FFF).contains(Int(scalar.value))
        }
    }
}
