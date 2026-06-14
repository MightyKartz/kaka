import XCTest
@testable import AgentPocketUI

final class InboxActionFeedbackPresentationTests: XCTestCase {
    func testEnglishFailureShowsDismissibleErrorBanner() {
        let presentation = InboxActionFeedbackPresentation(
            state: .failed("Connect to your local agent before submitting inbox items."),
            progressText: "Uploading",
            language: .english
        )

        XCTAssertEqual(presentation?.title, "Needs Review")
        XCTAssertEqual(presentation?.message, "Connect to your local agent before submitting inbox items.")
        XCTAssertEqual(presentation?.systemImage, "exclamationmark.triangle.fill")
        XCTAssertTrue(presentation?.isFailure == true)
        XCTAssertTrue(presentation?.canDismiss == true)
    }

    func testBlankFailureMessageFallsBackToLocalizedReviewCopy() {
        let english = InboxActionFeedbackPresentation(
            state: .failed(" \n "),
            progressText: nil,
            language: .english
        )
        let chinese = InboxActionFeedbackPresentation(
            state: .failed(""),
            progressText: nil,
            language: .chinese
        )

        XCTAssertEqual(english?.message, "Pocket Agent could not finish that Inbox action. Review the item and try again.")
        XCTAssertEqual(chinese?.message, "Pocket Agent 未能完成这次收件箱操作。请查看项目后重试。")
    }

    func testEnglishSubmittingShowsProgressBanner() {
        let presentation = InboxActionFeedbackPresentation(
            state: .submitting,
            progressText: "Uploading",
            language: .english
        )

        XCTAssertEqual(presentation?.title, "Sending")
        XCTAssertEqual(presentation?.message, "Uploading")
        XCTAssertEqual(presentation?.systemImage, "arrow.triangle.2.circlepath")
        XCTAssertFalse(presentation?.isFailure == true)
        XCTAssertFalse(presentation?.canDismiss == true)
    }

    func testChineseSubmittingFallbackIsLocalized() {
        let presentation = InboxActionFeedbackPresentation(
            state: .submitting,
            progressText: nil,
            language: .chinese
        )

        XCTAssertEqual(presentation?.title, "发送中")
        XCTAssertEqual(presentation?.message, "正在发送到本地智能体。")
    }

    func testCompletedIdleAndLoadingDoNotCreateFeedbackBanner() {
        XCTAssertNil(InboxActionFeedbackPresentation(state: .completed, progressText: nil, language: .english))
        XCTAssertNil(InboxActionFeedbackPresentation(state: .idle, progressText: nil, language: .english))
        XCTAssertNil(InboxActionFeedbackPresentation(state: .loading, progressText: nil, language: .english))
    }
}
