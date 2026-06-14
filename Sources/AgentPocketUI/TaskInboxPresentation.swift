import Foundation

enum TaskInboxPresentation {
    static func taskTitle(_ rawTitle: String, language: AppLanguage) -> String {
        let trimmed = rawTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.isEmpty == false else {
            return defaultTaskTitle(language: language)
        }

        if language == .chinese && trimmed == "Runtime task" {
            return "运行时任务"
        }

        return rawTitle
    }

    static func statusTitle(_ rawValue: String, language: AppLanguage) -> String {
        guard language == .chinese else {
            return rawValue.replacingOccurrences(of: "_", with: " ")
        }

        switch rawValue {
        case "queued":
            return "排队中"
        case "running":
            return "运行中"
        case "completed":
            return "已完成"
        case "failed":
            return "失败"
        case "cancelled", "canceled":
            return "已取消"
        case "requires_user_action", "waiting_for_approval":
            return "等待确认"
        default:
            return rawValue.replacingOccurrences(of: "_", with: " ")
        }
    }

    static func taskMessage(_ message: String, language: AppLanguage) -> String {
        guard language == .chinese else {
            return message
        }

        switch message {
        case "Completed.":
            return "已完成。"
        case "Cancelled.", "Canceled.":
            return "已取消。"
        case "Waiting for approval.":
            return "等待确认。"
        case "Running.":
            return "运行中。"
        default:
            return message
        }
    }

    private static func defaultTaskTitle(language: AppLanguage) -> String {
        language == .chinese ? "运行时任务" : "Runtime task"
    }
}
