import AgentPocketCore
import Foundation

public struct CaptureScreenPresentation: Equatable, Sendable {
    public struct PrimaryAction: Equatable, Sendable {
        public let title: String
        public let systemImage: String
        public let isEnabled: Bool
    }

    public struct ModeTab: Equatable, Identifiable, Sendable {
        public let mode: SmartCameraMode
        public let title: String
        public let systemImage: String
        public let isSelected: Bool
        public let isEnabled: Bool

        public var id: String { mode.id }
    }

    public let title: String
    public let connectedBadge: String
    public let statusText: String
    public let galleryTitle: String
    public let cameraTitle: String
    public let primaryAction: PrimaryAction
    public let modeTabs: [ModeTab]
    public let zoomStops: [CameraZoomStop]
    public let isProcessing: Bool

    public init(
        state: CaptureFlowViewModel.State,
        selectedCameraMode: SmartCameraMode,
        selectedIntent: EditIntent,
        language: AppLanguage,
        connectedRuntimeName: String?,
        hasPreparedUpload: Bool = false
    ) {
        title = Self.title(language: language)
        connectedBadge = Self.connectedBadge(language: language, connectedRuntimeName: connectedRuntimeName)
        statusText = Self.statusText(
            for: state,
            selectedCameraMode: selectedCameraMode,
            selectedIntent: selectedIntent,
            language: language
        )
        galleryTitle = language == .chinese ? "相册" : "Gallery"
        cameraTitle = language == .chinese ? "拍照" : "Camera"
        primaryAction = Self.primaryAction(
            for: state,
            selectedCameraMode: selectedCameraMode,
            language: language,
            hasPreparedUpload: hasPreparedUpload
        )
        isProcessing = Self.isProcessing(state)
        modeTabs = []
        zoomStops = CameraZoomStop.allCases
    }

    private static func isProcessing(_ state: CaptureFlowViewModel.State) -> Bool {
        switch state {
        case .uploading, .startingTask, .submitted, .running:
            return true
        case .empty, .loadingPhoto, .ready, .completed, .failed:
            return false
        }
    }

    private static func title(language: AppLanguage) -> String {
        switch language {
        case .chinese:
            return "智能相机"
        case .english:
            return "Smart Camera"
        }
    }

    private static func connectedBadge(language: AppLanguage, connectedRuntimeName: String?) -> String {
        let name = Self.friendlyRuntimeName(connectedRuntimeName)
        switch language {
        case .chinese:
            return "已连接 · \(name ?? "本机智能体")"
        case .english:
            return "Connected · \(name ?? "Local Agent")"
        }
    }

    private static func friendlyRuntimeName(_ value: String?) -> String? {
        guard let value else {
            return nil
        }
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.isEmpty == false else {
            return nil
        }
        if trimmed == "localhost" || trimmed == "127.0.0.1" || isIPv4Address(trimmed) {
            return nil
        }
        return trimmed
    }

    private static func isIPv4Address(_ value: String) -> Bool {
        let parts = value.split(separator: ".", omittingEmptySubsequences: false)
        guard parts.count == 4 else {
            return false
        }
        return parts.allSatisfy { part in
            guard let number = Int(part), String(number) == part else {
                return false
            }
            return (0...255).contains(number)
        }
    }

    private static func primaryAction(
        for state: CaptureFlowViewModel.State,
        selectedCameraMode: SmartCameraMode,
        language: AppLanguage,
        hasPreparedUpload: Bool
    ) -> PrimaryAction {
        switch state {
        case .ready:
            return PrimaryAction(
                title: language == .chinese ? "发送给 Kaka" : "Send to Kaka",
                systemImage: "paperplane.fill",
                isEnabled: true
            )
        case .completed:
            return PrimaryAction(
                title: language == .chinese ? "查看结果" : "View Result",
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
                title: language == .chinese ? "拍摄" : "Shoot",
                systemImage: "camera.fill",
                isEnabled: true
            )
        }
    }

    private static func statusText(
        for state: CaptureFlowViewModel.State,
        selectedCameraMode: SmartCameraMode,
        selectedIntent: EditIntent,
        language: AppLanguage
    ) -> String {
        switch (state, language) {
        case (.empty, .chinese):
            return "拍一张照片，让 Kaka 判断可以做什么。"
        case (.empty, .english):
            return "Take a photo and let Kaka decide what it can do."
        case (.loadingPhoto, .chinese):
            return "正在准备照片..."
        case (.loadingPhoto, .english):
            return "Preparing selected photo..."
        case (.ready, .chinese):
            return "照片已准备好，Kaka 会先判断适合做什么。"
        case (.ready, .english):
            return "The photo is ready. Kaka will decide what it can do first."
        case (.uploading, .chinese):
            return "正在发送照片到本机智能体..."
        case (.uploading, .english):
            return "Uploading photo to your local agent..."
        case (.startingTask, .chinese):
            return "正在启动图片理解..."
        case (.startingTask, .english):
            return "Starting image understanding..."
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
            return "已完成图片理解，正在打开对话。"
        case (.completed, .english):
            return "Image understanding is ready. Opening chat."
        case let (.failed(message), language):
            return Self.localizedFailureMessage(message, language: language)
        }
    }

    private static func localizedFailureMessage(_ message: String, language: AppLanguage) -> String {
        guard language == .chinese else {
            return message
        }

        switch message {
        case "Camera is not available on this device. Choose a photo from the library instead.":
            return "这台设备没有可用相机。请从相册选择照片。"
        case "Camera input is not available.":
            return "无法启动相机输入。"
        case "Camera output is not available.":
            return "无法启动相机拍摄输出。"
        case "Camera zoom is not available.":
            return "当前相机不支持这个变焦档位。"
        case "Camera access is disabled. Allow camera access in Settings or choose a photo from the library.":
            return "相机权限未开启。请在系统设置中允许相机访问，或从相册选择照片。"
        case "This camera photo could not be loaded.":
            return "无法读取这张相机照片。"
        case "This camera photo could not be prepared.":
            return "无法准备这张相机照片。"
        case "This photo could not be loaded.":
            return "无法读取这张照片。"
        case SmartCameraMode.unavailableFailureMessage:
            return "此智能相机模式的智能体任务协议尚未接入。照片已保留，可切回成片继续处理。"
        case "This local agent runtime is missing Vision tasks.":
            return "这个本机智能体还没有接入视觉任务。"
        case "Could not submit vision task.":
            return "无法提交智能视觉任务。"
        case "Vision task did not complete.":
            return "智能视觉任务没有完成。"
        case "The vision provider failed. Check local agent provider credentials or logs.":
            return "视觉提供器处理失败。请检查本机智能体的模型配置或日志。"
        case "Could not inspect image.":
            return "无法理解这张图片。"
        case "Image intake did not complete.":
            return "图片理解任务没有完成。"
        case "The image intake provider failed. Check local agent provider credentials or logs.":
            return "图片理解提供器处理失败。请检查本机智能体的模型配置或日志。"
        default:
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
