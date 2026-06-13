import Foundation

public struct LocalAgentLensAction: Equatable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let subtitle: String
    public let systemImageName: String
    public let isEnabled: Bool

    public init(
        id: String,
        title: String,
        subtitle: String,
        systemImageName: String,
        isEnabled: Bool
    ) {
        self.id = id
        self.title = title
        self.subtitle = subtitle
        self.systemImageName = systemImageName
        self.isEnabled = isEnabled
    }
}

public struct LocalAgentLensPresentation: Equatable, Sendable {
    public let connectionTitle: String
    public let connectionHint: String
    public let actions: [LocalAgentLensAction]

    public init(isConnected: Bool, language: AppLanguage, runtimeAddress: String? = nil) {
        connectionTitle = Self.connectionTitle(isConnected: isConnected, language: language)
        connectionHint = Self.connectionHint(
            isConnected: isConnected,
            runtimeAddress: runtimeAddress,
            language: language
        )
        actions = Self.actions(language: language)
    }

    private static func connectionTitle(isConnected: Bool, language: AppLanguage) -> String {
        switch (isConnected, language) {
        case (true, .chinese):
            return "本机智能体已连接"
        case (true, .english):
            return "Local Agent Connected"
        case (false, .chinese):
            return "本机智能体离线"
        case (false, .english):
            return "Local Agent Offline"
        }
    }

    private static func connectionHint(
        isConnected: Bool,
        runtimeAddress: String?,
        language: AppLanguage
    ) -> String {
        if isConnected {
            if let runtimeAddress, runtimeAddress.isEmpty == false {
                return runtimeAddress
            }
            return language == .chinese ? "同一 Wi-Fi / LAN" : "Same Wi-Fi / LAN"
        }
        return language == .chinese
            ? "发送前请先连接同一 Wi-Fi 上的本机智能体。"
            : "Connect to your local agent on Wi-Fi before sending."
    }

    private static func actions(language: AppLanguage) -> [LocalAgentLensAction] {
        [
            LocalAgentLensAction(
                id: "agent_scanner",
                title: text("Scan", "扫码", language),
                subtitle: text("Codes, links, visible text", "二维码、链接、可见文本", language),
                systemImageName: "qrcode.viewfinder",
                isEnabled: true
            ),
            LocalAgentLensAction(
                id: "document_scan",
                title: text("Document", "文档", language),
                subtitle: text("Scan to Inbox", "扫描到收件箱", language),
                systemImageName: "doc.viewfinder",
                isEnabled: true
            ),
            LocalAgentLensAction(
                id: "video_intake",
                title: text("Video", "视频", language),
                subtitle: text("Short clip analysis", "短视频理解", language),
                systemImageName: "video.badge.waveform",
                isEnabled: true
            ),
            LocalAgentLensAction(
                id: "voice_recorder",
                title: text("Record", "录音", language),
                subtitle: text("Transcript and summary", "转写与摘要", language),
                systemImageName: "mic.circle",
                isEnabled: true
            ),
            LocalAgentLensAction(
                id: "inbox",
                title: text("Inbox", "收件箱", language),
                subtitle: text("Review before sending", "发送前审核", language),
                systemImageName: "tray.full",
                isEnabled: true
            ),
            LocalAgentLensAction(
                id: "tasks",
                title: text("Activity", "活动", language),
                subtitle: text("Approvals and progress", "审批与进度", language),
                systemImageName: "waveform.path.ecg.rectangle",
                isEnabled: true
            )
        ]
    }

    private static func text(_ english: String, _ chinese: String, _ language: AppLanguage) -> String {
        language == .chinese ? chinese : english
    }
}
