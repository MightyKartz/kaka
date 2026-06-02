import AgentPocketCore
import Foundation

public struct CaptureScreenPresentation: Equatable, Sendable {
    public struct PrimaryAction: Equatable, Sendable {
        public let title: String
        public let systemImage: String
        public let isEnabled: Bool
    }

    public struct SceneTab: Equatable, Identifiable, Sendable {
        public let intent: EditIntent
        public let title: String
        public let isSelected: Bool

        public var id: String { intent.id }
    }

    public let title: String
    public let connectedBadge: String
    public let statusText: String
    public let galleryTitle: String
    public let cameraTitle: String
    public let frameBadge: String
    public let primaryAction: PrimaryAction
    public let sceneTabs: [SceneTab]
    public let zoomStops: [String]

    public init(
        state: CaptureFlowViewModel.State,
        selectedIntent: EditIntent,
        language: AppLanguage,
        connectedRuntimeName: String?,
        hasPreparedUpload: Bool = false
    ) {
        title = Self.title(language: language)
        connectedBadge = Self.connectedBadge(language: language, connectedRuntimeName: connectedRuntimeName)
        statusText = Self.statusText(for: state, selectedIntent: selectedIntent, language: language)
        galleryTitle = language == .chinese ? "相册" : "Gallery"
        cameraTitle = language == .chinese ? "拍照" : "Camera"
        frameBadge = language == .chinese ? "4:5 裁切" : "4:5 Frame"
        primaryAction = Self.primaryAction(for: state, language: language, hasPreparedUpload: hasPreparedUpload)
        sceneTabs = EditIntent.allCases.map { intent in
            SceneTab(
                intent: intent,
                title: intent.localizedSceneTitle(language: language),
                isSelected: intent == selectedIntent
            )
        }
        zoomStops = ["0.5", "1x", "2", "5"]
    }

    private static func title(language: AppLanguage) -> String {
        switch language {
        case .chinese:
            return "大师成片"
        case .english:
            return "Master Shot"
        }
    }

    private static func connectedBadge(language: AppLanguage, connectedRuntimeName: String?) -> String {
        let name = connectedRuntimeName?.isEmpty == false ? connectedRuntimeName! : nil
        switch language {
        case .chinese:
            return "已连接 · \(name ?? "本机智能体")"
        case .english:
            return "Connected · \(name ?? "Local Agent")"
        }
    }

    private static func primaryAction(
        for state: CaptureFlowViewModel.State,
        language: AppLanguage,
        hasPreparedUpload: Bool
    ) -> PrimaryAction {
        switch state {
        case .ready:
            return PrimaryAction(
                title: language == .chinese ? "发送本机智能体" : "Send to Local Agent",
                systemImage: "paperplane.fill",
                isEnabled: true
            )
        case .completed:
            return PrimaryAction(
                title: language == .chinese ? "查看成片" : "Review Results",
                systemImage: "rectangle.on.rectangle",
                isEnabled: true
            )
        case .loadingPhoto, .uploading, .startingTask, .submitted, .running:
            return PrimaryAction(
                title: language == .chinese ? "处理中" : "Processing",
                systemImage: "hourglass",
                isEnabled: false
            )
        case .failed where hasPreparedUpload:
            return PrimaryAction(
                title: language == .chinese ? "重新发送" : "Retry Send",
                systemImage: "paperplane.fill",
                isEnabled: true
            )
        case .empty, .failed:
            return PrimaryAction(
                title: language == .chinese ? "一键成片" : "Master Shot",
                systemImage: "sparkles",
                isEnabled: false
            )
        }
    }

    private static func statusText(
        for state: CaptureFlowViewModel.State,
        selectedIntent: EditIntent,
        language: AppLanguage
    ) -> String {
        switch (state, language) {
        case (.empty, .chinese):
            return "拍照或选择一张照片开始。"
        case (.empty, .english):
            return "Take or choose a photo to begin."
        case (.loadingPhoto, .chinese):
            return "正在准备照片..."
        case (.loadingPhoto, .english):
            return "Preparing selected photo..."
        case let (.ready(fileName, _), .chinese):
            return "\(fileName) 已准备好，场景：\(selectedIntent.localizedSceneTitle(language: language))。"
        case let (.ready(fileName, _), .english):
            return "\(fileName) is ready for \(selectedIntent.localizedSceneTitle(language: language))."
        case (.uploading, .chinese):
            return "正在发送照片到本机智能体..."
        case (.uploading, .english):
            return "Uploading photo to your local agent..."
        case (.startingTask, .chinese):
            return "正在启动修图任务..."
        case (.startingTask, .english):
            return "Starting photo edit..."
        case let (.submitted(taskID), .chinese):
            return "任务已提交：\(taskID)"
        case let (.submitted(taskID), .english):
            return "Submitted \(taskID)."
        case let (.running(taskID, progress, message), .chinese):
            let percent = Int((progress * 100).rounded())
            return message ?? "正在处理 \(taskID)，\(percent)%"
        case let (.running(taskID, progress, message), .english):
            let percent = Int((progress * 100).rounded())
            return message ?? "Editing \(taskID), \(percent)%"
        case (.completed, .chinese):
            return "已生成可对比的成片。"
        case (.completed, .english):
            return "Edited variants are ready to review."
        case let (.failed(message), _):
            return message
        }
    }
}

private extension EditIntent {
    func localizedSceneTitle(language: AppLanguage) -> String {
        switch (self, language) {
        case (.naturalEnhance, .chinese):
            return "自然"
        case (.naturalEnhance, .english):
            return "Natural"
        case (.portraitPolish, .chinese):
            return "人像"
        case (.portraitPolish, .english):
            return "Portrait"
        case (.productShot, .chinese):
            return "产品"
        case (.productShot, .english):
            return "Product"
        case (.socialCover, .chinese):
            return "社交"
        case (.socialCover, .english):
            return "Social"
        }
    }
}
