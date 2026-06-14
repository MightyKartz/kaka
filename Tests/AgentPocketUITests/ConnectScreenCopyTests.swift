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

        XCTAssertEqual(copy.connectTitle, "连接你的本机运行时")
        XCTAssertEqual(copy.connectSubtitle, "首次连接需要扫描 Mac 上的配对二维码。之后 Pocket Agent 会自动连接。")
        XCTAssertEqual(copy.primaryButtonTitle, "扫描二维码连接")
        XCTAssertEqual(copy.scanCodeTitle, "扫描二维码")
        XCTAssertEqual(copy.nearbyRuntimeDescription, "首次建议扫描 Mac 上的二维码；发现附近运行时可作为备选连接方式。")
        XCTAssertEqual(copy.settingsTitle, "项目设置")
        XCTAssertEqual(copy.deviceName, "我的电脑")
        XCTAssertEqual(copy.onlineTrustedTitle, "首次扫码建立信任")
        XCTAssertEqual(copy.trustBadgeTitles, ["本地网络", "待确认"])
        XCTAssertFalse(copy.visibleCopy.localizedCaseInsensitiveContains("Connect My Local Agent"))
    }

    func testEnglishCopyDoesNotContainChineseText() {
        let copy = ConnectScreenCopy(
            state: .idle,
            language: .english,
            fallbackDeviceName: "Local Mac"
        )

        XCTAssertEqual(copy.connectTitle, "Connect Your Local Runtime")
        XCTAssertEqual(copy.primaryButtonTitle, "Scan Pairing QR")
        XCTAssertEqual(copy.scanCodeTitle, "Scan Code")
        XCTAssertEqual(copy.nearbyRuntimeDescription, "Scan the QR on your Mac first. Nearby discovery is available as a fallback.")
        XCTAssertEqual(copy.settingsTitle, "Project Settings")
        XCTAssertEqual(copy.onlineTrustedTitle, "Scan Once to Trust")
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
        XCTAssertEqual(copy.connectSubtitle, "OpenClaw Studio 已准备好接收手机动作。")
        XCTAssertEqual(copy.primaryButtonTitle, "打开 Lens")
        XCTAssertEqual(copy.privacyLine, "输入留在你的设备，密钥留在本机运行时")
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
            ("QR code is not a Kaka pairing code.", "这不是 Pocket Agent 配对二维码。请扫描本机运行时显示的 Pocket Agent Mobile Bridge 二维码。"),
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

    func testSavedOfflineCopyExplainsMacActionBeforeReconnect() {
        let copy = ConnectScreenCopy(
            state: .savedConnectionOffline(displayName: "Kartz Mac"),
            language: .chinese,
            fallbackDeviceName: "我的电脑"
        )

        XCTAssertEqual(copy.connectTitle, "Mac 上的本机运行时未启动")
        XCTAssertEqual(copy.connectSubtitle, "Kartz Mac 的配对还在。请先在 Mac 上启动 Hermes/OpenClaw 或 runtime-kit，再回到这里重新连接。")
        XCTAssertEqual(copy.primaryButtonTitle, "我已启动，重新连接")
        XCTAssertEqual(copy.onlineTrustedTitle, "配对已保存 · Mac 待启动")
        XCTAssertEqual(copy.trustBadgeTitles, ["配对已保存", "Mac 待启动"])
    }
}

private extension String {
    var containsCJKCharacters: Bool {
        unicodeScalars.contains { scalar in
            (0x4E00...0x9FFF).contains(Int(scalar.value))
        }
    }
}
