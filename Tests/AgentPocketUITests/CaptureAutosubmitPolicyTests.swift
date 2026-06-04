import XCTest
@testable import AgentPocketUI

final class CaptureAutosubmitPolicyTests: XCTestCase {
    func testAutoSubmitsPreparedCameraPhotoWhenConnectionIsAvailable() {
        XCTAssertTrue(
            CaptureAutosubmitPolicy.shouldSubmitPreparedPhoto(
                source: .camera,
                hasPreparedUpload: true,
                hasActiveConnection: true
            )
        )
    }

    func testDoesNotAutoSubmitLibrarySelection() {
        XCTAssertFalse(
            CaptureAutosubmitPolicy.shouldSubmitPreparedPhoto(
                source: .photoLibrary,
                hasPreparedUpload: true,
                hasActiveConnection: true
            )
        )
    }

    func testDoesNotAutoSubmitWithoutPreparedUpload() {
        XCTAssertFalse(
            CaptureAutosubmitPolicy.shouldSubmitPreparedPhoto(
                source: .camera,
                hasPreparedUpload: false,
                hasActiveConnection: true
            )
        )
    }

    func testDoesNotAutoSubmitWithoutConnection() {
        XCTAssertFalse(
            CaptureAutosubmitPolicy.shouldSubmitPreparedPhoto(
                source: .camera,
                hasPreparedUpload: true,
                hasActiveConnection: false
            )
        )
    }

    func testDoesNotAutoSubmitWhenCurrentModeDoesNotAllowIt() {
        XCTAssertFalse(
            CaptureAutosubmitPolicy.shouldSubmitPreparedPhoto(
                source: .camera,
                hasPreparedUpload: true,
                hasActiveConnection: true,
                allowsAutosubmit: false
            )
        )
    }
}
