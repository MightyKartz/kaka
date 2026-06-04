import AgentPocketCore
import Foundation

struct ImageConversationResultPresentation: Equatable, Sendable {
    enum Kind: Equatable, Sendable {
        case photo
        case vision
        case generic
    }

    struct DetailRow: Equatable, Sendable {
        let title: String
        let value: String
    }

    let kind: Kind
    let title: String
    let subtitle: String?
    let bodyText: String?
    let detailRows: [DetailRow]
    let actionTitle: String?
    let systemImage: String

    init(status: TaskStatusResponse, language: AppLanguage) {
        if let variants = status.variants, variants.isEmpty == false {
            kind = .photo
            title = language == .chinese ? "修图结果" : "Photo Result"
            subtitle = Self.variantCountText(variants.count, language: language)
            bodyText = Self.firstNonEmpty(status.recipeSummary, status.explanation, status.message)
            detailRows = variants.prefix(3).map { variant in
                DetailRow(
                    title: variant.label,
                    value: Self.variantDetailText(variant.recommendedFor, language: language)
                )
            }
            actionTitle = language == .chinese ? "查看修图结果" : "View Photo Result"
            systemImage = "wand.and.stars"
            return
        }

        if let vision = status.vision {
            kind = .vision
            title = vision.title
            subtitle = "Vision · \(vision.mode)"
            bodyText = Self.firstNonEmpty(vision.text)
            detailRows = Self.visionRows(from: vision)
            actionTitle = language == .chinese ? "查看完整结果" : "View Full Result"
            systemImage = Self.systemImage(for: vision.mode)
            return
        }

        kind = .generic
        title = status.resultType ?? status.status
        subtitle = nil
        bodyText = Self.firstNonEmpty(status.message, status.explanation)
        detailRows = []
        actionTitle = nil
        systemImage = "checkmark.seal"
    }

    private static func variantCountText(_ count: Int, language: AppLanguage) -> String {
        if language == .chinese {
            return "已生成 \(count) 个版本"
        }
        return count == 1 ? "Generated 1 version" : "Generated \(count) versions"
    }

    private static func variantDetailText(_ value: String?, language: AppLanguage) -> String {
        switch value {
        case "review":
            return language == .chinese ? "适合查看细节" : "Best for review"
        case "share":
            return language == .chinese ? "适合分享" : "Best for sharing"
        case "save":
            return language == .chinese ? "适合保存" : "Best for saving"
        default:
            return language == .chinese ? "已生成" : "Generated"
        }
    }

    private static func visionRows(from vision: TaskStatusResponse.VisionResult) -> [DetailRow] {
        let sectionRows = vision.sections
            .flatMap(\.items)
            .compactMap(Self.row(from:))
        if sectionRows.isEmpty == false {
            return Array(sectionRows.prefix(4))
        }

        return Array(vision.items.compactMap(Self.row(from:)).prefix(4))
    }

    private static func row(from item: TaskStatusResponse.VisionItem) -> DetailRow? {
        let value = firstNonEmpty(item.value, item.subtitle)
        guard let value else {
            return nil
        }
        return DetailRow(title: item.title, value: value)
    }

    private static func firstNonEmpty(_ values: String?...) -> String? {
        values
            .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
            .first { $0.isEmpty == false }
    }

    private static func systemImage(for mode: String) -> String {
        switch mode {
        case "scan":
            return "doc.text.viewfinder"
        case "translate":
            return "translate"
        case "food":
            return "fork.knife"
        case "identify":
            return "viewfinder.circle"
        default:
            return "sparkles"
        }
    }
}
