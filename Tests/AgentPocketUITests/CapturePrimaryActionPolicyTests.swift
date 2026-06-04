import XCTest
@testable import AgentPocketUI

final class CapturePrimaryActionPolicyTests: XCTestCase {
    func testEmptyStatePrimaryActionOpensCamera() {
        XCTAssertEqual(
            CapturePrimaryActionPolicy.mode(
                captureState: .empty,
                hasPreparedUpload: false,
                hasCompletedStatus: false
            ),
            .openCamera
        )
    }

    func testReadyStatePrimaryActionSubmitsPreparedPhoto() {
        XCTAssertEqual(
            CapturePrimaryActionPolicy.mode(
                captureState: .ready(fileName: "camera.jpg", intentTitle: "Natural"),
                hasPreparedUpload: true,
                hasCompletedStatus: false
            ),
            .submitPreparedPhoto
        )
    }

    func testCompletedStatePrimaryActionReviewsResult() {
        XCTAssertEqual(
            CapturePrimaryActionPolicy.mode(
                captureState: .completed(taskID: "task_123"),
                hasPreparedUpload: true,
                hasCompletedStatus: true
            ),
            .reviewCompletedResult
        )
    }

    func testProcessingStatePrimaryActionIsDisabled() {
        XCTAssertEqual(
            CapturePrimaryActionPolicy.mode(
                captureState: .uploading,
                hasPreparedUpload: true,
                hasCompletedStatus: false
            ),
            .disabled
        )
    }
}
