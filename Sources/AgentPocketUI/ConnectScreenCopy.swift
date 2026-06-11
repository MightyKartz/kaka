import Foundation

public enum AppLanguage: String, CaseIterable, Identifiable, Sendable {
    case chinese = "zh-Hans"
    case english = "en"

    public var id: String { rawValue }

    public static func resolved(
        storedValue: String?,
        preferredLanguages: [String] = Locale.preferredLanguages
    ) -> AppLanguage {
        let firstPreferredLanguage = preferredLanguages.first?.lowercased() ?? ""
        if firstPreferredLanguage.hasPrefix("zh") {
            return .chinese
        }
        return .english
    }

    public var displayTitle: String {
        switch self {
        case .chinese:
            return "中文"
        case .english:
            return "English"
        }
    }
}

public struct ConnectScreenCopy: Equatable, Sendable {
    public let appName = "Kaka"
    public let connectTitle: String
    public let connectSubtitle: String
    public let deviceName: String
    public let onlineTrustedTitle: String
    public let trustBadgeTitles: [String]
    public let primaryButtonTitle: String
    public let scanCodeTitle: String
    public let privacyLine: String
    public let settingsTitle: String
    public let runtimeTitle: String
    public let runtimeDescription: String
    public let runtimeValue: String
    public let privacyTitle: String
    public let privacyDescription: String
    public let privacyValue: String
    public let defaultSceneTitle: String
    public let defaultSceneDescription: String
    public let defaultSceneValue: String
    public let manualTitle: String
    public let endpointPlaceholder: String
    public let tokenPlaceholder: String
    public let testConnectionTitle: String
    public let enterManuallyTitle: String
    public let nearbyRuntimeTitle: String
    public let nearbyRuntimeDescription: String
    public let connectRuntimeTitle: String

    public init(
        state: ConnectionState,
        language: AppLanguage,
        fallbackDeviceName: String
    ) {
        switch language {
        case .chinese:
            let connectedRuntime = state.connectedRuntime
            connectTitle = state.localizedConnectTitle(language: language)
            connectSubtitle = state.localizedConnectSubtitle(language: language, connectedRuntime: connectedRuntime)
            deviceName = connectedRuntime?.displayName ?? fallbackDeviceName
            onlineTrustedTitle = state.localizedOnlineTrustedTitle(language: language)
            trustBadgeTitles = state.localizedTrustBadgeTitles(language: language)
            primaryButtonTitle = state.localizedPrimaryButtonTitle(language: language)
            scanCodeTitle = state == .scanning ? "手动输入" : "扫描二维码"
            privacyLine = "照片和密钥留在你的设备与本机运行时"
            settingsTitle = "项目设置"
            runtimeTitle = "本机运行时"
            runtimeDescription = "管理当前连接和信任状态。"
            runtimeValue = connectedRuntime == nil ? "待连接" : "已连接"
            privacyTitle = "隐私边界"
            privacyDescription = "模型和渲染在本机运行时处理。"
            privacyValue = "本地"
            defaultSceneTitle = "默认场景包"
            defaultSceneDescription = "拍照后优先使用的成片风格。"
            defaultSceneValue = "自然"
            manualTitle = "手动连接"
            endpointPlaceholder = "https://你的本机运行时.local"
            tokenPlaceholder = "移动端令牌"
            testConnectionTitle = "测试连接"
            enterManuallyTitle = "手动输入"
            nearbyRuntimeTitle = "附近的本机智能体"
            nearbyRuntimeDescription = "确认这台 Mac 后，Kaka 会保存一个移动端令牌，下次自动连接。"
            connectRuntimeTitle = "连接"
        case .english:
            let connectedRuntime = state.connectedRuntime
            connectTitle = state.localizedConnectTitle(language: language)
            connectSubtitle = state.localizedConnectSubtitle(language: language, connectedRuntime: connectedRuntime)
            deviceName = connectedRuntime?.displayName ?? fallbackDeviceName
            onlineTrustedTitle = state.localizedOnlineTrustedTitle(language: language)
            trustBadgeTitles = state.localizedTrustBadgeTitles(language: language)
            primaryButtonTitle = state.localizedPrimaryButtonTitle(language: language)
            scanCodeTitle = state == .scanning ? "Enter Manually" : "Scan Code"
            privacyLine = "Photos and secrets stay on your devices and local runtime"
            settingsTitle = "Project Settings"
            runtimeTitle = "Local Runtime"
            runtimeDescription = "Current pairing and trust."
            runtimeValue = connectedRuntime == nil ? "Not Connected" : "Connected"
            privacyTitle = "Privacy Boundary"
            privacyDescription = "Processing stays on this Mac."
            privacyValue = "Local"
            defaultSceneTitle = "Default Scene Pack"
            defaultSceneDescription = "Preferred look after capture."
            defaultSceneValue = "Natural"
            manualTitle = "Manual Connection"
            endpointPlaceholder = "https://your-runtime.local"
            tokenPlaceholder = "Mobile token"
            testConnectionTitle = "Test Connection"
            enterManuallyTitle = "Enter Manually"
            nearbyRuntimeTitle = "Nearby Local Agents"
            nearbyRuntimeDescription = "Confirm this Mac once. Kaka stores a mobile token and reconnects next time."
            connectRuntimeTitle = "Connect"
        }
    }

    public var visibleCopy: String {
        [
            appName,
            connectTitle,
            connectSubtitle,
            deviceName,
            onlineTrustedTitle,
            trustBadgeTitles.joined(separator: " "),
            primaryButtonTitle,
            scanCodeTitle,
            privacyLine,
            settingsTitle,
            runtimeTitle,
            runtimeDescription,
            runtimeValue,
            privacyTitle,
            privacyDescription,
            privacyValue,
            defaultSceneTitle,
            defaultSceneDescription,
            defaultSceneValue,
            manualTitle,
            endpointPlaceholder,
            tokenPlaceholder,
            testConnectionTitle,
            enterManuallyTitle,
            nearbyRuntimeTitle,
            nearbyRuntimeDescription,
            connectRuntimeTitle
        ].joined(separator: " ")
    }
}

private extension ConnectionState {
    var connectedRuntime: ConnectedRuntime? {
        if case .connected(let runtime) = self {
            return runtime
        }
        return nil
    }

    func localizedConnectTitle(language: AppLanguage) -> String {
        switch (self, language) {
        case (.connected, .chinese):
            return "已连接到本机智能体"
        case (.connected, .english):
            return "Connected to Local Agent"
        case (.scanning, .chinese):
            return "扫描配对二维码"
        case (.scanning, .english):
            return "Scan Pairing QR"
        case (.discovering, .chinese):
            return "正在发现本机智能体"
        case (.discovering, .english):
            return "Finding Local Agent"
        case (.testing, .chinese):
            return "正在测试连接"
        case (.testing, .english):
            return "Testing Connection"
        case (.offline, .chinese):
            return "本机运行时离线"
        case (.offline, .english):
            return "Runtime Offline"
        case (.localNetworkPermissionRequired, .chinese):
            return "需要本地网络权限"
        case (.localNetworkPermissionRequired, .english):
            return "Local Network Access Needed"
        case (.unauthorized, .chinese):
            return "令牌未被接受"
        case (.unauthorized, .english):
            return "Token Not Accepted"
        case (.invalidCertificate, .chinese):
            return "证书需要处理"
        case (.invalidCertificate, .english):
            return "Certificate Problem"
        case (.missingPhotoEdit, .chinese):
            return "缺少照片处理能力"
        case (.missingPhotoEdit, .english):
            return "Photo Pack Missing"
        case (.failed, .chinese):
            return "连接失败"
        case (.failed, .english):
            return "Connection Failed"
        case (_, .chinese):
            return "连接我的本机智能体"
        case (_, .english):
            return "Connect My Local Agent"
        }
    }

    func localizedConnectSubtitle(language: AppLanguage, connectedRuntime: ConnectedRuntime?) -> String {
        switch (self, language) {
        case (.connected, .chinese):
            return "\(connectedRuntime?.displayName ?? "本机智能体") 已准备好处理照片。"
        case (.connected, .english):
            return "\(connectedRuntime?.displayName ?? "Local agent") is ready for photo edits."
        case (.scanning, .chinese):
            return "对准本机智能体显示的配对二维码。"
        case (.scanning, .english):
            return "Point the camera at the pairing code shown by your local agent."
        case (.discovering, .chinese):
            return "正在查找本地网络中的私有运行时。"
        case (.discovering, .english):
            return "Looking for private runtimes on your local network."
        case (.testing, .chinese):
            return "正在检查健康状态和照片处理能力。"
        case (.testing, .english):
            return "Checking health and photo editing capabilities."
        case (.offline, .chinese):
            return "请确认本机智能体正在运行，并且 iPhone 可访问。"
        case (.offline, .english):
            return "Make sure your local agent is running and reachable from this iPhone."
        case (.localNetworkPermissionRequired, .chinese):
            return "允许 Kaka 在本地网络中发现你的智能体。"
        case (.localNetworkPermissionRequired, .english):
            return "Allow Kaka to find your local agent on the local network."
        case (.unauthorized, .chinese):
            return "请在本机智能体里生成新的移动端配对码。"
        case (.unauthorized, .english):
            return "Create a new mobile pairing code in your local agent, then try again."
        case (.invalidCertificate, .chinese):
            return "请使用可信 HTTPS 证书、Tailscale HTTPS 或本地开发模式。"
        case (.invalidCertificate, .english):
            return "Use a trusted HTTPS certificate, Tailscale HTTPS, or local developer mode."
        case (.missingPhotoEdit, .chinese):
            return "运行时可访问，但照片处理能力还未安装。"
        case (.missingPhotoEdit, .english):
            return "This runtime is reachable, but the Photo Pack is not installed."
        case (.failed(let message), .chinese):
            return Self.localizedFailureMessage(message, language: language)
        case (.failed(let message), .english):
            return message
        case (_, .chinese):
            return "发现附近运行时，确认后即可拍照成片。"
        case (_, .english):
            return "Find a nearby runtime, confirm trust, then start shooting."
        }
    }

    static func localizedFailureMessage(_ message: String, language: AppLanguage) -> String {
        guard language == .chinese else {
            return message
        }

        switch message {
        case "Pairing code expired.":
            return "配对二维码已过期。请在本机运行时刷新二维码后重新扫码。"
        case "Pairing code already used. Scan a new QR code.":
            return "这个配对二维码已经使用过。请在本机运行时生成新的二维码。"
        case "QR code is not a Kaka pairing code.":
            return "这不是 Kaka 配对二维码。请扫描本机运行时显示的 Kaka Mobile Bridge 二维码。"
        case "No local agent runtime found. Scan a pairing QR or enter an endpoint.":
            return "没有发现本机智能体。请扫描配对二维码，或手动输入本机地址。"
        case "Could not search the local network. Check Local Network permission and try again.":
            return "无法搜索本地网络。请检查本地网络权限后重试。"
        case "Scan the pairing QR shown by your local agent to finish connecting.":
            return "请扫描本机智能体显示的配对二维码完成连接。"
        case "Enter the mobile token from your local agent.":
            return "请输入本机智能体生成的移动端令牌。"
        case "Remote endpoints must use HTTPS.":
            return "远程地址必须使用 HTTPS。"
        case "Enter a valid local agent endpoint.":
            return "请输入有效的本机智能体地址。"
        case "Could not save local agent credentials.":
            return "无法保存本机智能体凭证。"
        case "Could not restore local agent connection.":
            return "无法恢复已保存连接。请确认本机运行时正在运行，或重新扫码配对。"
        case "Could not forget local agent connection.":
            return "无法清除已保存连接。请稍后重试。"
        default:
            return message
        }
    }

    func localizedPrimaryButtonTitle(language: AppLanguage) -> String {
        switch (self, language) {
        case (.scanning, .chinese):
            return "扫描中..."
        case (.scanning, .english):
            return "Scanning..."
        case (.discovering, .chinese):
            return "发现中..."
        case (.discovering, .english):
            return "Finding..."
        case (.testing, .chinese):
            return "测试中..."
        case (.testing, .english):
            return "Testing..."
        case (.connected, .chinese):
            return "开始拍摄"
        case (.connected, .english):
            return "Start Shooting"
        case (.localNetworkPermissionRequired, .chinese):
            return "打开设置"
        case (.localNetworkPermissionRequired, .english):
            return "Open Settings"
        case (.missingPhotoEdit, .chinese):
            return "打开设置指南"
        case (.missingPhotoEdit, .english):
            return "Open Setup Guide"
        case (.offline, .chinese):
            return "重新发现"
        case (.offline, .english):
            return "Discover Again"
        case (_, .chinese):
            return "连接"
        case (_, .english):
            return "Connect"
        }
    }

    func localizedOnlineTrustedTitle(language: AppLanguage) -> String {
        switch (self, language) {
        case (.connected, .chinese):
            return "在线 · 已信任"
        case (.connected, .english):
            return "Online · Trusted"
        case (.discovering, .chinese):
            return "发现中"
        case (.discovering, .english):
            return "Discovering"
        case (.testing, .chinese):
            return "测试中"
        case (.testing, .english):
            return "Testing"
        case (.offline, .chinese):
            return "离线"
        case (.offline, .english):
            return "Offline"
        case (.scanning, .chinese):
            return "等待扫码配对"
        case (.scanning, .english):
            return "Scan to Pair"
        case (.failed, .chinese):
            return "需要重新连接"
        case (.failed, .english):
            return "Reconnect Needed"
        case (.idle, .chinese):
            return "点击连接后发现"
        case (.idle, .english):
            return "Tap Connect to Find"
        case (_, .chinese):
            return "待连接"
        case (_, .english):
            return "Not Connected"
        }
    }

    func localizedTrustBadgeTitles(language: AppLanguage) -> [String] {
        switch (self, language) {
        case (.connected, .chinese):
            return ["本地网络", "已信任"]
        case (.connected, .english):
            return ["Local Network", "Trusted"]
        case (_, .chinese):
            return ["本地网络", "待确认"]
        case (_, .english):
            return ["Local Network", "Confirm"]
        }
    }
}
