import AgentPocketCore
import Foundation

public enum SmartCameraMode: String, CaseIterable, Identifiable, Sendable {
    case masterShot = "master_shot"
    case scan
    case identify
    case translate
    case food

    public var id: String { rawValue }

    public var isSelectable: Bool {
        switch self {
        case .masterShot, .scan, .identify, .translate, .food:
            return true
        }
    }

    public var visionTaskKind: VisionTaskKind? {
        switch self {
        case .masterShot:
            return nil
        case .scan:
            return .scan
        case .identify:
            return .identify
        case .translate:
            return .translate
        case .food:
            return .food
        }
    }

    public func title(language: AppLanguage) -> String {
        switch (self, language) {
        case (.masterShot, .chinese):
            return "拍摄"
        case (.masterShot, .english):
            return "Photo"
        case (.scan, .chinese):
            return "扫描"
        case (.scan, .english):
            return "Scan"
        case (.identify, .chinese):
            return "识别"
        case (.identify, .english):
            return "Identify"
        case (.translate, .chinese):
            return "翻译"
        case (.translate, .english):
            return "Translate"
        case (.food, .chinese):
            return "食物"
        case (.food, .english):
            return "Food"
        }
    }

    public func primaryActionTitle(language: AppLanguage) -> String {
        switch (self, language) {
        case (.masterShot, .chinese):
            return "拍摄"
        case (.masterShot, .english):
            return "Shoot"
        case (.scan, .chinese):
            return "扫描"
        case (.scan, .english):
            return "Scan"
        case (.identify, .chinese):
            return "识别"
        case (.identify, .english):
            return "Identify"
        case (.translate, .chinese):
            return "翻译"
        case (.translate, .english):
            return "Translate"
        case (.food, .chinese):
            return "估算"
        case (.food, .english):
            return "Estimate"
        }
    }

    public func readyActionTitle(language: AppLanguage) -> String {
        switch (self, language) {
        case (.masterShot, .chinese):
            return "发送本机智能体"
        case (.masterShot, .english):
            return "Send to Local Agent"
        case (.scan, .chinese):
            return "开始扫描"
        case (.scan, .english):
            return "Start Scan"
        case (.identify, .chinese):
            return "开始识别"
        case (.identify, .english):
            return "Start Identify"
        case (.translate, .chinese):
            return "开始翻译"
        case (.translate, .english):
            return "Start Translate"
        case (.food, .chinese):
            return "估算热量"
        case (.food, .english):
            return "Estimate Calories"
        }
    }

    public func emptyStatus(language: AppLanguage) -> String {
        switch (self, language) {
        case (.masterShot, .chinese):
            return "对准画面，点击拍摄。"
        case (.masterShot, .english):
            return "Frame your shot, then shoot."
        case (.scan, .chinese):
            return "对准文档、二维码、包装或海报。"
        case (.scan, .english):
            return "Frame a document, code, package, or poster."
        case (.identify, .chinese):
            return "对准物品、植物、动物或地标。"
        case (.identify, .english):
            return "Frame an object, plant, animal, or landmark."
        case (.translate, .chinese):
            return "对准菜单、说明书、路牌或屏幕文字。"
        case (.translate, .english):
            return "Frame a menu, manual, sign, or screen text."
        case (.food, .chinese):
            return "对准食物，估算热量范围。"
        case (.food, .english):
            return "Frame food to estimate a calorie range."
        }
    }

    public func readyStatus(fileName: String, selectedIntent: EditIntent, language: AppLanguage) -> String {
        switch (self, language) {
        case (.masterShot, .chinese):
            return "\(fileName) 已准备好，场景：\(selectedIntent.localizedSceneTitle(language: language))。"
        case (.masterShot, .english):
            return "\(fileName) is ready for \(selectedIntent.localizedSceneTitle(language: language))."
        case (.scan, .chinese):
            return "\(fileName) 已准备好，点击开始扫描。"
        case (.scan, .english):
            return "\(fileName) is ready to scan."
        case (.identify, .chinese):
            return "\(fileName) 已准备好，点击开始识别。"
        case (.identify, .english):
            return "\(fileName) is ready to identify."
        case (.translate, .chinese):
            return "\(fileName) 已准备好，点击开始翻译。"
        case (.translate, .english):
            return "\(fileName) is ready to translate."
        case (.food, .chinese):
            return "\(fileName) 已准备好，点击估算热量。"
        case (.food, .english):
            return "\(fileName) is ready for calorie estimation."
        }
    }

    public var systemImage: String {
        switch self {
        case .masterShot:
            return "sparkles"
        case .scan:
            return "doc.text.viewfinder"
        case .identify:
            return "viewfinder.circle"
        case .translate:
            return "translate"
        case .food:
            return "fork.knife"
        }
    }

    public static let unavailableFailureMessage =
        "This smart camera mode is not connected yet. Keep the photo or switch to Master Shot."
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
