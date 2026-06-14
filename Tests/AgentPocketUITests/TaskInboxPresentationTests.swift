import XCTest
@testable import AgentPocketUI

final class TaskInboxPresentationTests: XCTestCase {
    func testChineseActivityTitleLocalizesRuntimeFallback() {
        XCTAssertEqual(
            TaskInboxPresentation.taskTitle("Runtime task", language: .chinese),
            "运行时任务"
        )
    }

    func testChineseActivityTitleUsesLocalFallbackForBlankTitle() {
        XCTAssertEqual(
            TaskInboxPresentation.taskTitle("   ", language: .chinese),
            "运行时任务"
        )
    }

    func testActivityTitleKeepsRuntimeProvidedSpecificTitle() {
        XCTAssertEqual(
            TaskInboxPresentation.taskTitle("小红书封面构图已完成", language: .chinese),
            "小红书封面构图已完成"
        )
    }
}
