import AgentPocketCore
import Foundation

public protocol RuntimeTaskInboxPerforming: Sendable {
    func fetchRuntimeTasks(connection: StoredConnection) async throws -> [RuntimeTaskSummary]

    func cancelRuntimeTask(
        taskID: String,
        connection: StoredConnection
    ) async throws -> RuntimeTaskActionResponse

    func approveRuntimeTask(
        taskID: String,
        approval: RuntimeTaskApprovalRequest,
        connection: StoredConnection
    ) async throws -> RuntimeTaskActionResponse
}

public struct MobileBridgeRuntimeTaskInboxPerformer: RuntimeTaskInboxPerforming {
    private let session: URLSession?

    public init(session: URLSession? = nil) {
        self.session = session
    }

    public func fetchRuntimeTasks(connection: StoredConnection) async throws -> [RuntimeTaskSummary] {
        let client = MobileBridgeHTTPClient(
            connection: connection,
            session: session
        )
        return try await client.fetchRuntimeTasks()
    }

    public func cancelRuntimeTask(
        taskID: String,
        connection: StoredConnection
    ) async throws -> RuntimeTaskActionResponse {
        let client = MobileBridgeHTTPClient(
            connection: connection,
            session: session
        )
        return try await client.cancelRuntimeTask(taskID: taskID)
    }

    public func approveRuntimeTask(
        taskID: String,
        approval: RuntimeTaskApprovalRequest,
        connection: StoredConnection
    ) async throws -> RuntimeTaskActionResponse {
        let client = MobileBridgeHTTPClient(
            connection: connection,
            session: session
        )
        return try await client.approveRuntimeTask(taskID: taskID, approval: approval)
    }
}

@MainActor
public final class TaskInboxViewModel: ObservableObject {
    public enum State: Equatable, Sendable {
        case idle
        case loading
        case loaded
        case submitting
        case failed(String)
    }

    @Published public private(set) var tasks: [RuntimeTaskSummary] = []
    @Published public private(set) var state: State = .idle

    private let performer: any RuntimeTaskInboxPerforming
    private let activityCoordinator: any RuntimeTaskActivityCoordinating

    public init(
        performer: any RuntimeTaskInboxPerforming = MobileBridgeRuntimeTaskInboxPerformer(),
        activityCoordinator: any RuntimeTaskActivityCoordinating = ActivityKitRuntimeTaskActivityCoordinator()
    ) {
        self.performer = performer
        self.activityCoordinator = activityCoordinator
    }

    public func load(connection: StoredConnection?) async {
        guard let connection else {
            state = .failed("Connect to your local agent before loading tasks.")
            return
        }

        state = .loading
        do {
            tasks = Self.sorted(try await performer.fetchRuntimeTasks(connection: connection))
            await syncRuntimeTaskActivities()
            state = .loaded
        } catch {
            state = .failed("Could not load runtime tasks.")
        }
    }

    public func cancel(taskID: String, connection: StoredConnection?) async {
        guard let connection else {
            state = .failed("Connect to your local agent before updating tasks.")
            return
        }

        state = .submitting
        do {
            let response = try await performer.cancelRuntimeTask(taskID: taskID, connection: connection)
            apply(response)
            await syncRuntimeTaskActivities()
            state = .loaded
        } catch {
            state = .failed("Could not update runtime task.")
        }
    }

    public func approve(taskID: String, note: String? = nil, connection: StoredConnection?) async {
        guard let connection else {
            state = .failed("Connect to your local agent before updating tasks.")
            return
        }

        state = .submitting
        do {
            let response = try await performer.approveRuntimeTask(
                taskID: taskID,
                approval: RuntimeTaskApprovalRequest(action: .approve, note: note),
                connection: connection
            )
            apply(response)
            await syncRuntimeTaskActivities()
            state = .loaded
        } catch {
            state = .failed("Could not update runtime task.")
        }
    }

    private func apply(_ response: RuntimeTaskActionResponse) {
        guard let task = response.task else {
            return
        }
        tasks.removeAll { $0.id == task.id }
        tasks.append(task)
        tasks = Self.sorted(tasks)
    }

    private func syncRuntimeTaskActivities() async {
        await activityCoordinator.sync(tasks: tasks)
    }

    private static func sorted(_ tasks: [RuntimeTaskSummary]) -> [RuntimeTaskSummary] {
        tasks.sorted { lhs, rhs in
            if lhs.requiresUserAction != rhs.requiresUserAction {
                return lhs.requiresUserAction
            }
            return (lhs.updatedAt ?? "") > (rhs.updatedAt ?? "")
        }
    }
}
