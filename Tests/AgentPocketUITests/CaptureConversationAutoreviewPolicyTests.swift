import XCTest
@testable import AgentPocketUI

final class CaptureConversationAutoreviewPolicyTests: XCTestCase {
    func testOpensConversationForNewImageIntakeTask() {
        XCTAssertTrue(CaptureConversationAutoreviewPolicy.shouldOpenConversation(
            taskID: "task_intake_1",
            alreadyOpenedTaskID: nil,
            hasImageIntake: true
        ))
    }

    func testDoesNotReopenAlreadyOpenedConversation() {
        XCTAssertFalse(CaptureConversationAutoreviewPolicy.shouldOpenConversation(
            taskID: "task_intake_1",
            alreadyOpenedTaskID: "task_intake_1",
            hasImageIntake: true
        ))
    }

    func testDoesNotOpenConversationForNonIntakeResult() {
        XCTAssertFalse(CaptureConversationAutoreviewPolicy.shouldOpenConversation(
            taskID: "task_vision_1",
            alreadyOpenedTaskID: nil,
            hasImageIntake: false
        ))
    }
}
