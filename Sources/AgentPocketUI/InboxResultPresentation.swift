import AgentPocketCore
import Foundation

public struct InboxResultPresentation: Equatable, Sendable {
    public let title: String
    public let summary: String?
    public let sourceText: String?
    public let contextText: String?

    public init(
        status: TaskStatusResponse,
        context: InboxSubmissionContext?,
        language: AppLanguage
    ) {
        title = status.intake?.title
            ?? status.imageIntake?.title
            ?? (language == .chinese ? "已完成" : "Completed")
        summary = status.intake?.summary
            ?? status.imageIntake?.summary
            ?? status.message

        if let context {
            sourceText = Self.sourceText(context, language: language)
            contextText = Self.contextText(context, language: language)
        } else {
            sourceText = nil
            contextText = nil
        }
    }
}

private extension InboxResultPresentation {
    static func sourceText(_ context: InboxSubmissionContext, language: AppLanguage) -> String {
        let sourceSurface = context.sourceSurface ?? context.sourceApp ?? context.kind.rawValue
        let source = localizedSource(sourceSurface, language: language)
        let sourceWithApp = sourceTextWithApp(
            source,
            sourceSurface: sourceSurface,
            sourceApp: context.sourceApp,
            language: language
        )
        if language == .chinese {
            return "来源：\(sourceWithApp)"
        }
        return "Source: \(sourceWithApp)"
    }

    static func sourceTextWithApp(
        _ source: String,
        sourceSurface: String,
        sourceApp: String?,
        language: AppLanguage
    ) -> String {
        guard let app = visible(sourceApp),
              shouldShowSourceApp(sourceSurface, source: source, app: app) else {
            return source
        }
        return language == .chinese ? "\(source)来自 \(app)" : "\(source) from \(app)"
    }

    static func shouldShowSourceApp(_ sourceSurface: String, source: String, app: String) -> Bool {
        switch sourceSurface {
        case "file_picker", "document_picker":
            return app != "Files"
        default:
            return app != source
        }
    }

    static func contextText(_ context: InboxSubmissionContext, language: AppLanguage) -> String {
        if context.contextSelected {
            return language == .chinese
                ? "已选择 Context Snapshot；支持的运行时会随本次任务接收。"
                : "Context Snapshot selected; supported runtimes receive it with this task."
        }
        return language == .chinese
            ? "本次任务未选择 Context Snapshot。"
            : "No Context Snapshot selected for this task."
    }

    static func localizedSource(_ source: String, language: AppLanguage) -> String {
        switch source {
        case "paste":
            return language == .chinese ? "粘贴" : "Paste"
        case "voice":
            return language == .chinese ? "语音" : "Voice"
        case "share_extension":
            return language == .chinese ? "系统分享" : "Share Extension"
        case "file_picker", "document_picker":
            return language == .chinese ? "文件" : "Files"
        case AgentLensSourceSurface.agentScanner.rawValue:
            return language == .chinese ? "扫描" : "Scanner"
        case AgentLensSourceSurface.documentScanner.rawValue:
            return language == .chinese ? "文档扫描" : "Document Scan"
        case AgentLensSourceSurface.videoCapture.rawValue:
            return language == .chinese ? "视频" : "Video"
        default:
            return source
        }
    }

    static func visible(_ value: String?) -> String? {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed?.isEmpty == false ? trimmed : nil
    }
}
