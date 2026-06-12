import XCTest
@testable import AgentPocketCore

final class RuntimeTaskActivityTests: XCTestCase {
    func testBuildsActivitySnapshotFromVisibleRuntimeTaskFieldsOnly() {
        let task = RuntimeTaskSummary(
            id: "task_approval_1",
            title: "Approve Recall write",
            status: .waitingForApproval,
            progress: 0.42,
            message: "Hidden approval detail should stay in app UI",
            updatedAt: "2026-06-05T09:32:00Z"
        )

        let snapshot = RuntimeTaskActivitySnapshot(task: task)

        XCTAssertEqual(snapshot.taskID, "task_approval_1")
        XCTAssertEqual(snapshot.title, "Review task in Kaka")
        XCTAssertEqual(snapshot.phase, .needsApproval)
        XCTAssertTrue(snapshot.approvalNeeded)
        XCTAssertEqual(RuntimeTaskActivitySnapshot.phoneSafeFieldNames, ["task_id", "title", "phase", "approval_needed"])
    }

    func testActivitySnapshotDoesNotExposeRuntimeControlledTaskTitle() {
        let task = RuntimeTaskSummary(
            id: "task_sensitive",
            title: "Provider key sk-live-secret should remember private calendar context",
            status: .running,
            progress: 0.5,
            message: "Keep this message inside the app UI"
        )

        let snapshot = RuntimeTaskActivitySnapshot(task: task)

        XCTAssertEqual(snapshot.title, "Kaka task")
        XCTAssertFalse(snapshot.title.contains("sk-live-secret"))
        XCTAssertFalse(snapshot.title.contains("calendar"))
    }

    func testActivityPhaseLabelsAreShortAndPhoneSafe() {
        XCTAssertEqual(RuntimeTaskActivityPhase.queued.statusLabel, "Queued")
        XCTAssertEqual(RuntimeTaskActivityPhase.running.statusLabel, "Running")
        XCTAssertEqual(RuntimeTaskActivityPhase.needsApproval.statusLabel, "Needs approval")
        XCTAssertEqual(RuntimeTaskActivityPhase.completed.statusLabel, "Completed")
        XCTAssertEqual(RuntimeTaskActivityPhase.failed.statusLabel, "Failed")
        XCTAssertEqual(RuntimeTaskActivityPhase.cancelled.statusLabel, "Cancelled")
    }

    func testActivityPhaseShortLabelsFitDynamicIsland() {
        XCTAssertEqual(RuntimeTaskActivityPhase.queued.shortLabel, "Queue")
        XCTAssertEqual(RuntimeTaskActivityPhase.running.shortLabel, "Run")
        XCTAssertEqual(RuntimeTaskActivityPhase.needsApproval.shortLabel, "Review")
        XCTAssertEqual(RuntimeTaskActivityPhase.completed.shortLabel, "Done")
        XCTAssertEqual(RuntimeTaskActivityPhase.failed.shortLabel, "Fail")
        XCTAssertEqual(RuntimeTaskActivityPhase.cancelled.shortLabel, "Stop")
    }

    func testActivitySnapshotsMarkTerminalTasks() {
        let task = RuntimeTaskSummary(
            id: "task_done",
            title: "Summarize PDF",
            status: .completed,
            progress: 1.0
        )

        let snapshot = RuntimeTaskActivitySnapshot(task: task)

        XCTAssertTrue(snapshot.isTerminal)
        XCTAssertFalse(snapshot.approvalNeeded)
    }
}
