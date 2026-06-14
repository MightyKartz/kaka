import Foundation

public enum RuntimeTaskActivityPhase: String, Codable, Equatable, Hashable, Sendable {
    case queued
    case running
    case needsApproval = "needs_approval"
    case completed
    case failed
    case cancelled

    public init(status: RuntimeTaskStatus) {
        switch status {
        case .queued:
            self = .queued
        case .running:
            self = .running
        case .waitingForApproval:
            self = .needsApproval
        case .completed:
            self = .completed
        case .failed:
            self = .failed
        case .cancelled:
            self = .cancelled
        }
    }

    public var statusLabel: String {
        switch self {
        case .queued:
            return "Queued"
        case .running:
            return "Running"
        case .needsApproval:
            return "Needs approval"
        case .completed:
            return "Completed"
        case .failed:
            return "Failed"
        case .cancelled:
            return "Cancelled"
        }
    }

    public var shortLabel: String {
        switch self {
        case .queued:
            return "Queue"
        case .running:
            return "Run"
        case .needsApproval:
            return "Review"
        case .completed:
            return "Done"
        case .failed:
            return "Fail"
        case .cancelled:
            return "Stop"
        }
    }

    public var activityTitle: String {
        switch self {
        case .needsApproval:
            return "Review task in Pocket Agent"
        case .completed:
            return "Pocket Agent task completed"
        case .failed:
            return "Pocket Agent task failed"
        case .cancelled:
            return "Pocket Agent task cancelled"
        case .queued, .running:
            return "Pocket Agent task"
        }
    }
}

public struct RuntimeTaskActivitySnapshot: Codable, Equatable, Hashable, Sendable {
    public static let phoneSafeFieldNames = ["task_id", "title", "phase", "approval_needed", "progress", "message"]

    public let taskID: String
    public let title: String
    public let phase: RuntimeTaskActivityPhase
    public let approvalNeeded: Bool
    public let progress: Double
    public let message: String?

    public init(
        taskID: String,
        title: String,
        phase: RuntimeTaskActivityPhase,
        approvalNeeded: Bool,
        progress: Double,
        message: String?
    ) {
        self.taskID = taskID
        self.title = title
        self.phase = phase
        self.approvalNeeded = approvalNeeded
        self.progress = min(max(progress, 0), 1)
        self.message = message?.trimmingCharacters(in: .whitespacesAndNewlines).nilIfEmpty
    }

    public init(task: RuntimeTaskSummary) {
        let phase = RuntimeTaskActivityPhase(status: task.status)
        self.init(
            taskID: task.id,
            title: phase.activityTitle,
            phase: phase,
            approvalNeeded: task.requiresUserAction,
            progress: task.progress,
            message: task.message
        )
    }

    public var isTerminal: Bool {
        switch phase {
        case .completed, .failed, .cancelled:
            return true
        case .queued, .running, .needsApproval:
            return false
        }
    }

    private enum CodingKeys: String, CodingKey {
        case taskID = "task_id"
        case title
        case phase
        case approvalNeeded = "approval_needed"
        case progress
        case message
    }
}

private extension String {
    var nilIfEmpty: String? {
        isEmpty ? nil : self
    }
}

#if os(iOS) && canImport(ActivityKit)
@preconcurrency import ActivityKit

public struct RuntimeTaskActivityAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable, Sendable {
        public let phase: RuntimeTaskActivityPhase
        public let approvalNeeded: Bool
        public let progress: Double
        public let message: String?

        public init(snapshot: RuntimeTaskActivitySnapshot) {
            self.phase = snapshot.phase
            self.approvalNeeded = snapshot.approvalNeeded
            self.progress = snapshot.progress
            self.message = snapshot.message
        }
    }

    public let taskID: String
    public let title: String

    public init(snapshot: RuntimeTaskActivitySnapshot) {
        self.taskID = snapshot.taskID
        self.title = snapshot.title
    }
}
#endif
