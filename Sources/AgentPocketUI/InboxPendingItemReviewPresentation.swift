import AgentPocketCore
import Foundation

public struct InboxPendingItemReviewRow: Equatable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let value: String
    public let systemImage: String
}

public struct InboxPendingItemReviewPresentation: Equatable, Sendable {
    public let title: String
    public let collapsedActionTitle: String
    public let expandedActionTitle: String
    public let rows: [InboxPendingItemReviewRow]

    public init(item: KakaInboxItem, contextIncluded: Bool, language: AppLanguage) {
        title = Self.text("Review Details", "查看详情", language)
        collapsedActionTitle = title
        expandedActionTitle = Self.text("Hide Details", "收起详情", language)

        var nextRows: [InboxPendingItemReviewRow] = []
        nextRows.append(Self.row("source", Self.label("Source", "来源", language), Self.sourceText(item, language), "square.and.arrow.down"))
        nextRows.append(Self.row("type", Self.label("Type", "类型", language), Self.kindText(item.kind, language), "tag"))

        if let content = Self.contentText(item) {
            let label = Self.label(
                item.kind == .url ? "URL" : "Content",
                item.kind == .url ? "链接" : "内容",
                language
            )
            nextRows.append(Self.row("content", label, content, item.kind == .url ? "link" : "text.alignleft"))
        }

        if let fileName = Self.visible(item.fileName) {
            nextRows.append(Self.row("file", Self.label("File", "文件", language), fileName, "doc"))
        }

        if let mimeType = Self.visible(item.mimeType) {
            nextRows.append(Self.row("mime_type", Self.label("MIME Type", "MIME 类型", language), mimeType, "doc.badge.gearshape"))
        }

        if item.relativeFilePath != nil {
            nextRows.append(Self.row("local_payload", Self.label("Local Payload", "本地副本", language), Self.text("Copied into Kaka Inbox", "已复制到 Kaka 收件箱", language), "tray.full"))
        }

        if item.route == .universalIntake,
           let note = Self.visible(item.note) {
            nextRows.append(Self.row("instruction", Self.label("Instruction", "指令", language), Self.excerpt(note), "text.bubble"))
        }

        nextRows.append(Self.row("context", Self.label("Context Snapshot", "Context Snapshot", language), Self.contextText(item: item, contextIncluded: contextIncluded, language: language), item.route == .universalIntake && contextIncluded ? "location.circle.fill" : "location.slash"))
        nextRows.append(Self.row("route", Self.label("Route", "路径", language), Self.routeText(item.route, language), "arrow.triangle.branch"))

        if let locale = Self.visible(item.locale) {
            nextRows.append(Self.row("locale", Self.label("Locale", "语言地区", language), locale, "globe"))
        }

        if let profile = Self.visible(item.preferredProfileID) {
            nextRows.append(Self.row("profile", Self.label("Profile", "档案", language), profile, "person.crop.circle"))
        }

        rows = nextRows
    }

    public func actionTitle(isExpanded: Bool) -> String {
        isExpanded ? expandedActionTitle : collapsedActionTitle
    }
}

private extension InboxPendingItemReviewPresentation {
    static func row(_ id: String, _ label: String, _ value: String, _ systemImage: String) -> InboxPendingItemReviewRow {
        InboxPendingItemReviewRow(id: id, label: label, value: value, systemImage: systemImage)
    }

    static func label(_ english: String, _ chinese: String, _ language: AppLanguage) -> String {
        text(english, chinese, language)
    }

    static func text(_ english: String, _ chinese: String, _ language: AppLanguage) -> String {
        language == .chinese ? chinese : english
    }

    static func visible(_ value: String?) -> String? {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed?.isEmpty == false ? trimmed : nil
    }

    static func excerpt(_ value: String, maxLength: Int = 120) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count > maxLength else {
            return trimmed
        }
        let endIndex = trimmed.index(trimmed.startIndex, offsetBy: maxLength)
        return "\(trimmed[..<endIndex])..."
    }

    static func contentText(_ item: KakaInboxItem) -> String? {
        switch item.kind {
        case .url:
            return visible(item.url).map { excerpt($0) }
        case .text:
            return visible(item.text).map { excerpt($0) }
        case .image, .screenshot, .pdf:
            return nil
        }
    }

    static func sourceText(_ item: KakaInboxItem, _ language: AppLanguage) -> String {
        let source = localizedSource(item.sourceSurface, language)
        guard let app = visible(item.sourceApp) else {
            return source
        }
        return language == .chinese ? "\(source)来自 \(app)" : "\(source) from \(app)"
    }

    static func localizedSource(_ source: String, _ language: AppLanguage) -> String {
        switch source {
        case "paste":
            return text("Paste", "粘贴", language)
        case "voice":
            return text("Voice", "语音", language)
        case "share_extension":
            return text("Share Extension", "系统分享", language)
        case "file_picker", "document_picker":
            return text("Files", "文件", language)
        default:
            return source
        }
    }

    static func kindText(_ kind: UniversalIntakeKind, _ language: AppLanguage) -> String {
        switch kind {
        case .text:
            return text("Text", "文本", language)
        case .url:
            return text("Link", "链接", language)
        case .image:
            return text("Image", "图片", language)
        case .screenshot:
            return text("Screenshot", "截图", language)
        case .pdf:
            return text("PDF", "PDF", language)
        }
    }

    static func contextText(item: KakaInboxItem, contextIncluded: Bool, language: AppLanguage) -> String {
        guard item.route == .universalIntake else {
            return text("Not sent with image intake", "图片任务不会随本次发送", language)
        }
        return contextIncluded
            ? text("Selected for this task", "本次任务已选择", language)
            : text("Not selected for this task", "本次任务未选择", language)
    }

    static func routeText(_ route: KakaInboxRoute, _ language: AppLanguage) -> String {
        switch route {
        case .universalIntake:
            return text("Universal Intake", "通用处理", language)
        case .imageIntake:
            return text("Image Intake", "图片处理", language)
        }
    }
}
