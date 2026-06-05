import XCTest
@testable import AgentPocketUI

@MainActor
final class VoiceCaptureViewModelTests: XCTestCase {
    func testTranscriptMustBeNonEmptyBeforeSubmit() {
        let viewModel = VoiceCaptureViewModel()

        viewModel.markTranscriptReady("   \n  ")

        XCTAssertEqual(viewModel.state, .ready)
        XCTAssertFalse(viewModel.canSubmit)

        viewModel.editableTranscript = "  提取文字  "

        XCTAssertTrue(viewModel.canSubmit)
        XCTAssertEqual(viewModel.transcript, "提取文字")
    }

    func testResetClearsTranscriptAndReturnsIdle() {
        let viewModel = VoiceCaptureViewModel()
        viewModel.markTranscriptReady("翻译这张图片")

        viewModel.reset()

        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertEqual(viewModel.transcript, "")
        XCTAssertEqual(viewModel.editableTranscript, "")
        XCTAssertFalse(viewModel.canSubmit)
    }
}
