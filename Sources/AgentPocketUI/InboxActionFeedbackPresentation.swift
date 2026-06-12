import Foundation

public struct InboxActionFeedbackPresentation: Equatable, Sendable {
    public let title: String
    public let message: String
    public let systemImage: String
    public let isFailure: Bool
    public let canDismiss: Bool

    public init?(
        state: InboxViewModel.State,
        progressText: String?,
        language: AppLanguage
    ) {
        switch state {
        case .submitting:
            title = language == .chinese ? "发送中" : "Sending"
            if let progressText,
               progressText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false {
                message = progressText
            } else {
                message = language == .chinese ? "正在发送到本地智能体。" : "Sending to your local agent."
            }
            systemImage = "arrow.triangle.2.circlepath"
            isFailure = false
            canDismiss = false
        case .failed(let failureMessage):
            title = language == .chinese ? "需要处理" : "Needs Review"
            message = failureMessage
            systemImage = "exclamationmark.triangle.fill"
            isFailure = true
            canDismiss = true
        case .idle, .loading, .completed:
            return nil
        }
    }
}
