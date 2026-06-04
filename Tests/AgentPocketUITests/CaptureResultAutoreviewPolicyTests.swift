import XCTest
@testable import AgentPocketUI

final class CaptureResultAutoreviewPolicyTests: XCTestCase {
    func testOpensResultWhenCompletedTaskHasNotBeenReviewed() {
        XCTAssertTrue(
            CaptureResultAutoreviewPolicy.shouldOpenResult(
                taskID: "task_123",
                alreadyOpenedTaskID: nil,
                hasCompletedStatus: true
            )
        )
    }

    func testDoesNotOpenWithoutCompletedStatus() {
        XCTAssertFalse(
            CaptureResultAutoreviewPolicy.shouldOpenResult(
                taskID: "task_123",
                alreadyOpenedTaskID: nil,
                hasCompletedStatus: false
            )
        )
    }

    func testDoesNotOpenWithoutTaskID() {
        XCTAssertFalse(
            CaptureResultAutoreviewPolicy.shouldOpenResult(
                taskID: nil,
                alreadyOpenedTaskID: nil,
                hasCompletedStatus: true
            )
        )
    }

    func testDoesNotReopenResultForTheSameCompletedTask() {
        XCTAssertFalse(
            CaptureResultAutoreviewPolicy.shouldOpenResult(
                taskID: "task_123",
                alreadyOpenedTaskID: "task_123",
                hasCompletedStatus: true
            )
        )
    }

    func testOpensResultForANewCompletedTask() {
        XCTAssertTrue(
            CaptureResultAutoreviewPolicy.shouldOpenResult(
                taskID: "task_456",
                alreadyOpenedTaskID: "task_123",
                hasCompletedStatus: true
            )
        )
    }
}
