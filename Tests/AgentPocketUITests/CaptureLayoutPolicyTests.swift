import XCTest
@testable import AgentPocketUI

final class CaptureLayoutPolicyTests: XCTestCase {
    func testInitialEmptyCaptureDefersControlsBelowTallFirstViewport() {
        XCTAssertEqual(
            CaptureLayoutPolicy.preControlsSpacerHeight(for: 932, isInitialEmptyCapture: true),
            208
        )
    }

    func testPreparedCaptureKeepsControlsImmediatelyReachable() {
        XCTAssertEqual(
            CaptureLayoutPolicy.preControlsSpacerHeight(for: 932, isInitialEmptyCapture: false),
            0
        )
    }
}
