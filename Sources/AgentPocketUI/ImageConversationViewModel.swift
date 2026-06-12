import AgentPocketCore
import Foundation

public protocol ImageSkillExecuting: Sendable {
    func execute(
        skill: KakaSkillID,
        userInstruction: String?,
        upload: PreparedImageUpload,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse
}

public struct KakaImageMessage: Equatable, Identifiable, Sendable {
    public enum Role: Equatable, Sendable {
        case assistant
        case user
        case result
    }

    public let id: UUID
    public let role: Role
    public let text: String
    public let result: TaskStatusResponse?

    public init(
        id: UUID = UUID(),
        role: Role,
        text: String,
        result: TaskStatusResponse? = nil
    ) {
        self.id = id
        self.role = role
        self.text = text
        self.result = result
    }
}

@MainActor
public final class ImageConversationViewModel: ObservableObject {
    @Published public var prompt = ""
    @Published public private(set) var messages: [KakaImageMessage]
    @Published public private(set) var isExecuting = false

    public let intakeStatus: TaskStatusResponse
    public let originalAsset: DownloadedAsset?
    public let preparedUpload: PreparedImageUpload
    public let suggestions: [KakaSkillSuggestion]

    private let skillExecutor: any ImageSkillExecuting

    public init(
        intakeStatus: TaskStatusResponse,
        originalAsset: DownloadedAsset?,
        preparedUpload: PreparedImageUpload,
        skillExecutor: any ImageSkillExecuting = UnavailableImageSkillExecutor()
    ) {
        self.intakeStatus = intakeStatus
        self.originalAsset = originalAsset
        self.preparedUpload = preparedUpload
        self.skillExecutor = skillExecutor

        let intake = intakeStatus.imageIntake
        suggestions = Self.coreSuggestions(
            merging: intake?.suggestions ?? [],
            language: AppLanguage.resolved(storedValue: nil)
        )
        messages = [
            KakaImageMessage(
                role: .assistant,
                text: intake?.summary ?? "我已经看到这张图片，可以告诉我你想怎么处理。"
            )
        ]
    }

    private static func coreSuggestions(
        merging intakeSuggestions: [KakaSkillSuggestion],
        language: AppLanguage
    ) -> [KakaSkillSuggestion] {
        var merged = intakeSuggestions
        var seen = Set(intakeSuggestions.map(\.skill))
        for suggestion in defaultSuggestions(language: language) where seen.contains(suggestion.skill) == false {
            merged.append(suggestion)
            seen.insert(suggestion.skill)
        }
        return merged
    }

    private static func defaultSuggestions(language: AppLanguage) -> [KakaSkillSuggestion] {
        [
            KakaSkillSuggestion(
                skill: .photoEnhance,
                title: language == .chinese ? "大师级优化" : "Master Enhance",
                reason: language == .chinese
                    ? "增强色彩、对比和主体分离。"
                    : "Improve color, contrast, and subject separation.",
                confidence: nil,
                isAvailable: true
            ),
            KakaSkillSuggestion(
                skill: .identifySubject,
                title: language == .chinese ? "识别主体" : "Identify",
                reason: language == .chinese
                    ? "判断画面中的主要物体。"
                    : "Identify the main visible subject.",
                confidence: nil,
                isAvailable: true
            ),
            KakaSkillSuggestion(
                skill: .ocr,
                title: language == .chinese ? "提取文字" : "Extract Text",
                reason: language == .chinese
                    ? "读取图片里的可见文字。"
                    : "Read visible text in the image.",
                confidence: nil,
                isAvailable: true
            ),
            KakaSkillSuggestion(
                skill: .translateText,
                title: language == .chinese ? "翻译文字" : "Translate",
                reason: language == .chinese
                    ? "识别并翻译图片里的文字。"
                    : "Read and translate visible text.",
                confidence: nil,
                isAvailable: true
            ),
            KakaSkillSuggestion(
                skill: .nutritionEstimate,
                title: language == .chinese ? "估算热量" : "Calories",
                reason: language == .chinese
                    ? "识别食物并给出谨慎估算。"
                    : "Estimate food calories with uncertainty.",
                confidence: nil,
                isAvailable: true
            ),
        ]
    }

    public func executeSuggestion(_ suggestion: KakaSkillSuggestion, connection: StoredConnection?) async {
        guard suggestion.isAvailable else {
            messages.append(KakaImageMessage(role: .assistant, text: "这个技能当前没有接入视觉模型。"))
            return
        }
        messages.append(KakaImageMessage(role: .user, text: suggestion.title))
        _ = await execute(skill: suggestion.skill, userInstruction: suggestion.title, connection: connection)
    }

    @discardableResult
    public func submitPrompt(connection: StoredConnection?) async -> String? {
        let text = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard text.isEmpty == false else {
            return nil
        }
        prompt = ""
        messages.append(KakaImageMessage(role: .user, text: text))
        return await execute(skill: KakaSkillRouter.route(text), userInstruction: text, connection: connection)
    }

    @discardableResult
    public func submitVoiceTranscript(_ transcript: String, connection: StoredConnection?) async -> String? {
        let text = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
        guard text.isEmpty == false else {
            return nil
        }
        prompt = text
        return await submitPrompt(connection: connection)
    }

    private func execute(skill: KakaSkillID, userInstruction: String?, connection: StoredConnection?) async -> String? {
        guard let connection else {
            let message = "请先连接本机智能体。"
            messages.append(KakaImageMessage(role: .assistant, text: message))
            return message
        }

        isExecuting = true
        defer {
            isExecuting = false
        }

        do {
            let status = try await skillExecutor.execute(
                skill: skill,
                userInstruction: userInstruction,
                upload: preparedUpload,
                connection: connection
            ) { [weak self] progress in
                await self?.apply(progress)
            }
            let summary = Self.summaryText(for: status)
            messages.append(
                KakaImageMessage(
                    role: .result,
                    text: summary,
                    result: status
                )
            )
            return summary
        } catch {
            let message = "这个技能暂时还不能执行，请稍后再试。"
            messages.append(KakaImageMessage(role: .assistant, text: message))
            return message
        }
    }

    private func apply(_ progress: PhotoEditSubmissionProgress) {
        switch progress {
        case .uploading:
            break
        case .startingTask:
            break
        case .submitted(let taskID):
            messages.append(KakaImageMessage(role: .assistant, text: "任务已提交：\(taskID)"))
        case .running:
            break
        }
    }

    private static func summaryText(for status: TaskStatusResponse) -> String {
        if let summary = status.vision?.summary, summary.isEmpty == false {
            return summary
        }
        if let summary = status.imageIntake?.summary, summary.isEmpty == false {
            return summary
        }
        if let explanation = status.explanation, explanation.isEmpty == false {
            return explanation
        }
        if let message = status.message, message.isEmpty == false {
            return message
        }
        return status.status == "completed" ? "已完成。" : "任务没有完成。"
    }
}

public struct UnavailableImageSkillExecutor: ImageSkillExecuting {
    public init() {}

    public func execute(
        skill: KakaSkillID,
        userInstruction: String?,
        upload: PreparedImageUpload,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        throw URLError(.unsupportedURL)
    }
}
