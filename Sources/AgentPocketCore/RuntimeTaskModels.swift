import Foundation

public enum RuntimeTaskStatus: String, Codable, Equatable, Sendable {
    case queued
    case running
    case waitingForApproval = "waiting_for_approval"
    case completed
    case failed
    case cancelled
}

public struct RuntimeTaskSummary: Codable, Equatable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let status: RuntimeTaskStatus
    public let progress: Double
    public let message: String?
    public let updatedAt: String?

    public init(
        id: String,
        title: String,
        status: RuntimeTaskStatus,
        progress: Double,
        message: String? = nil,
        updatedAt: String? = nil
    ) {
        self.id = id
        self.title = title
        self.status = status
        self.progress = progress
        self.message = message
        self.updatedAt = updatedAt
    }

    public var requiresUserAction: Bool {
        status == .waitingForApproval
    }

    public var isTerminal: Bool {
        switch status {
        case .completed, .failed, .cancelled:
            return true
        case .queued, .running, .waitingForApproval:
            return false
        }
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case title
        case status
        case progress
        case message
        case updatedAt = "updated_at"
    }
}

public struct RuntimeTaskListResponse: Decodable, Equatable, Sendable {
    public let tasks: [RuntimeTaskSummary]

    public init(tasks: [RuntimeTaskSummary]) {
        self.tasks = tasks
    }
}

public enum RuntimeTaskApprovalAction: String, Codable, Equatable, Sendable {
    case approve
    case reject
}

public struct RuntimeTaskApprovalRequest: Codable, Equatable, Sendable {
    public let action: RuntimeTaskApprovalAction
    public let note: String?

    public init(action: RuntimeTaskApprovalAction, note: String? = nil) {
        self.action = action
        self.note = note
    }
}

public struct RuntimeTaskActionResponse: Decodable, Equatable, Sendable {
    public let status: String
    public let task: RuntimeTaskSummary?

    public init(status: String, task: RuntimeTaskSummary? = nil) {
        self.status = status
        self.task = task
    }
}
