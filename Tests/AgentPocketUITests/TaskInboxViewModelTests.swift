import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class TaskInboxViewModelTests: XCTestCase {
    func testLoadTasksSortsUserActionFirstThenNewest() async throws {
        let waiting = RuntimeTaskSummary(
            id: "task_waiting",
            title: "Approve Recall write",
            status: .waitingForApproval,
            progress: 0.4,
            message: "Review memory write",
            updatedAt: "2026-06-05T09:31:00Z"
        )
        let running = RuntimeTaskSummary(
            id: "task_running",
            title: "Summarize PDF",
            status: .running,
            progress: 0.2,
            message: nil,
            updatedAt: "2026-06-05T09:32:00Z"
        )
        let performer = StubRuntimeTaskInboxPerformer(tasks: [running, waiting])
        let viewModel = TaskInboxViewModel(performer: performer)

        await viewModel.load(connection: try storedConnection())

        XCTAssertEqual(viewModel.tasks.map(\.id), ["task_waiting", "task_running"])
        XCTAssertEqual(viewModel.state, .loaded)
    }

    func testCancelTaskUpdatesTaskFromBridgeResponse() async throws {
        let running = RuntimeTaskSummary(
            id: "task_running",
            title: "Summarize PDF",
            status: .running,
            progress: 0.2
        )
        let cancelled = RuntimeTaskSummary(
            id: "task_running",
            title: "Summarize PDF",
            status: .cancelled,
            progress: 1.0,
            message: "Cancelled."
        )
        let performer = StubRuntimeTaskInboxPerformer(tasks: [running], actionResponse: RuntimeTaskActionResponse(status: "cancelled", task: cancelled))
        let viewModel = TaskInboxViewModel(performer: performer)

        await viewModel.load(connection: try storedConnection())
        await viewModel.cancel(taskID: "task_running", connection: try storedConnection())

        XCTAssertEqual(performer.cancelledTaskIDs, ["task_running"])
        XCTAssertEqual(viewModel.tasks.first?.status, .cancelled)
        XCTAssertEqual(viewModel.state, .loaded)
    }

    func testApproveTaskSubmitsApprovalAction() async throws {
        let waiting = RuntimeTaskSummary(
            id: "task_waiting",
            title: "Approve Recall write",
            status: .waitingForApproval,
            progress: 0.4
        )
        let approved = RuntimeTaskSummary(
            id: "task_waiting",
            title: "Approve Recall write",
            status: .running,
            progress: 0.5,
            message: "Approved."
        )
        let performer = StubRuntimeTaskInboxPerformer(tasks: [waiting], actionResponse: RuntimeTaskActionResponse(status: "approved", task: approved))
        let viewModel = TaskInboxViewModel(performer: performer)

        await viewModel.load(connection: try storedConnection())
        await viewModel.approve(taskID: "task_waiting", note: "Yes", connection: try storedConnection())

        XCTAssertEqual(performer.approvals, [RuntimeTaskApprovalRequest(action: .approve, note: "Yes")])
        XCTAssertEqual(viewModel.tasks.first?.status, .running)
        XCTAssertEqual(viewModel.state, .loaded)
    }

    func testLoadTasksSyncsVisibleLiveActivitySnapshots() async throws {
        let waiting = RuntimeTaskSummary(
            id: "task_waiting",
            title: "Approve Recall write",
            status: .waitingForApproval,
            progress: 0.4,
            message: "Keep this detail inside the app UI"
        )
        let performer = StubRuntimeTaskInboxPerformer(tasks: [waiting])
        let activityCoordinator = RecordingRuntimeTaskActivityCoordinator()
        let viewModel = TaskInboxViewModel(
            performer: performer,
            activityCoordinator: activityCoordinator
        )

        await viewModel.load(connection: try storedConnection())

        XCTAssertEqual(activityCoordinator.syncedSnapshots.count, 1)
        XCTAssertEqual(activityCoordinator.syncedSnapshots.first?.taskID, "task_waiting")
        XCTAssertEqual(activityCoordinator.syncedSnapshots.first?.phase, .needsApproval)
        XCTAssertEqual(activityCoordinator.syncedSnapshots.first?.approvalNeeded, true)
    }

    func testTerminalTaskUpdateEndsLiveActivitySnapshot() async throws {
        let running = RuntimeTaskSummary(
            id: "task_running",
            title: "Summarize PDF",
            status: .running,
            progress: 0.2
        )
        let completed = RuntimeTaskSummary(
            id: "task_running",
            title: "Summarize PDF",
            status: .completed,
            progress: 1.0
        )
        let performer = StubRuntimeTaskInboxPerformer(
            tasks: [running],
            actionResponse: RuntimeTaskActionResponse(status: "completed", task: completed)
        )
        let activityCoordinator = RecordingRuntimeTaskActivityCoordinator()
        let viewModel = TaskInboxViewModel(
            performer: performer,
            activityCoordinator: activityCoordinator
        )

        await viewModel.load(connection: try storedConnection())
        await viewModel.approve(taskID: "task_running", connection: try storedConnection())

        XCTAssertEqual(activityCoordinator.endedTaskIDs, ["task_running"])
    }

    func testActivityPlannerEndsTaskThatDisappearsFromLatestRuntimeList() {
        let running = RuntimeTaskSummary(
            id: "task_running",
            title: "Summarize PDF",
            status: .running,
            progress: 0.2
        )
        let planner = RuntimeTaskActivitySyncPlanner()

        let initialPlan = planner.plan(tasks: [running])
        let emptyPlan = planner.plan(tasks: [])

        XCTAssertEqual(initialPlan.activeSnapshots.map(\.taskID), ["task_running"])
        XCTAssertEqual(initialPlan.endedTaskIDs, [])
        XCTAssertEqual(emptyPlan.activeSnapshots, [])
        XCTAssertEqual(emptyPlan.endedTaskIDs, ["task_running"])
    }

    func testActivityPlannerCanSeedExistingActivityIDsAfterCoordinatorRecreation() {
        let planner = RuntimeTaskActivitySyncPlanner()

        planner.seedActiveTaskIDs(["task_running", "task_waiting"])
        let plan = planner.plan(tasks: [])

        XCTAssertEqual(plan.activeSnapshots, [])
        XCTAssertEqual(plan.endedTaskIDs, ["task_running", "task_waiting"])
    }

    func testActivityPlannerUsesClientGeneratedSafeTitles() {
        let sensitive = RuntimeTaskSummary(
            id: "task_sensitive",
            title: "Approve Recall write from private provider sk-live-secret",
            status: .waitingForApproval,
            progress: 0.4
        )
        let planner = RuntimeTaskActivitySyncPlanner()

        let plan = planner.plan(tasks: [sensitive])

        XCTAssertEqual(plan.activeSnapshots.first?.title, "Review task in Pocket Agent")
    }

    func testMissingConnectionFailsClearly() async {
        let viewModel = TaskInboxViewModel(performer: StubRuntimeTaskInboxPerformer(tasks: []))

        await viewModel.load(connection: nil)

        XCTAssertEqual(viewModel.state, .failed("Connect to your local agent before loading tasks."))
    }
}

private final class StubRuntimeTaskInboxPerformer: RuntimeTaskInboxPerforming, @unchecked Sendable {
    let tasks: [RuntimeTaskSummary]
    let actionResponse: RuntimeTaskActionResponse
    private(set) var cancelledTaskIDs: [String] = []
    private(set) var approvals: [RuntimeTaskApprovalRequest] = []

    init(
        tasks: [RuntimeTaskSummary],
        actionResponse: RuntimeTaskActionResponse = RuntimeTaskActionResponse(status: "ok", task: nil)
    ) {
        self.tasks = tasks
        self.actionResponse = actionResponse
    }

    func fetchRuntimeTasks(connection: StoredConnection) async throws -> [RuntimeTaskSummary] {
        tasks
    }

    func cancelRuntimeTask(taskID: String, connection: StoredConnection) async throws -> RuntimeTaskActionResponse {
        cancelledTaskIDs.append(taskID)
        return actionResponse
    }

    func approveRuntimeTask(
        taskID: String,
        approval: RuntimeTaskApprovalRequest,
        connection: StoredConnection
    ) async throws -> RuntimeTaskActionResponse {
        approvals.append(approval)
        return actionResponse
    }
}

@MainActor
private final class RecordingRuntimeTaskActivityCoordinator: RuntimeTaskActivityCoordinating {
    private(set) var syncedSnapshots: [RuntimeTaskActivitySnapshot] = []
    private(set) var endedTaskIDs: [String] = []

    func sync(tasks: [RuntimeTaskSummary]) async {
        let snapshots = tasks.map(RuntimeTaskActivitySnapshot.init(task:))
        syncedSnapshots = snapshots.filter { $0.isTerminal == false }
        endedTaskIDs.append(contentsOf: snapshots.filter(\.isTerminal).map(\.taskID))
    }
}

private func storedConnection() throws -> StoredConnection {
    StoredConnection(
        endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
        displayName: "Hermes Mac",
        runtime: "hermes",
        runtimeVersion: "2026.5.16",
        mobileToken: "mobile_secret",
        tokenExpiresAt: nil
    )
}
