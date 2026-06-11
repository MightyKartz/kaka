import XCTest
@testable import AgentPocketUI

final class AppIntentPresentationTests: XCTestCase {
    func testSystemSurfaceIntentCatalogContainsOnlySafeForegroundActions() {
        XCTAssertEqual(
            KakaAppIntentCatalog.safeActionIDs,
            [
                "open_inbox",
                "open_tasks",
                "review_inbox_item",
                "review_runtime_task"
            ]
        )
        XCTAssertTrue(KakaAppIntentCatalog.requiresForegroundConfirmation)
        XCTAssertFalse(KakaAppIntentCatalog.allowsBackgroundSubmission)
        XCTAssertFalse(KakaAppIntentCatalog.allowsProviderConfiguration)
        XCTAssertFalse(KakaAppIntentCatalog.allowsHiddenCapture)
    }

    func testSystemSurfaceIntentMetadataUsesUserVisibleLabels() {
        XCTAssertEqual(KakaSystemSurface.inbox.intentTitle, "Open Inbox")
        XCTAssertEqual(KakaSystemSurface.tasks.intentTitle, "Show Tasks")
        XCTAssertEqual(KakaSystemSurface.reviewInboxItem.intentTitle, "Review Inbox Item")
        XCTAssertEqual(KakaSystemSurface.reviewRuntimeTask.intentTitle, "Review Runtime Task")
        XCTAssertEqual(KakaAppIntentCatalog.destinationParameterTitle, "Destination")
        XCTAssertEqual(KakaAppIntentCatalog.taskIDParameterTitle, "Task ID")
        XCTAssertEqual(KakaAppIntentCatalog.taskActionParameterTitle, "Task Action")
    }

    func testActionButtonRecommendedShortcutsStayForegroundReviewOnly() {
        XCTAssertEqual(
            KakaAppIntentCatalog.actionButtonRecommendedActionIDs,
            [
                "open_inbox",
                "open_tasks"
            ]
        )
        XCTAssertTrue(KakaAppIntentCatalog.actionButtonUsesForegroundHandoff)
        XCTAssertFalse(KakaAppIntentCatalog.actionButtonAllowsBackgroundTaskMutation)
        XCTAssertFalse(KakaAppIntentCatalog.actionButtonAllowsRecallMutation)
        XCTAssertFalse(KakaAppIntentCatalog.actionButtonAllowsContextSnapshotCollection)
        XCTAssertFalse(KakaAppIntentCatalog.actionButtonAllowsRuntimeSettingsChanges)
    }

    func testActionButtonShortcutMetadataMatchesVisibleReviewSurfaces() {
        XCTAssertEqual(
            KakaAppIntentCatalog.actionButtonShortcuts,
            [
                KakaActionButtonShortcutMetadata(
                    actionID: "open_inbox",
                    shortTitle: "Open Inbox",
                    systemImageName: "tray.full",
                    targetSurface: .inbox
                ),
                KakaActionButtonShortcutMetadata(
                    actionID: "open_tasks",
                    shortTitle: "Show Tasks",
                    systemImageName: "list.bullet.rectangle",
                    targetSurface: .tasks
                )
            ]
        )
    }

    func testOnlyTopLevelReviewSurfacesAreActionButtonRecommended() {
        XCTAssertTrue(KakaSystemSurface.inbox.isActionButtonRecommended)
        XCTAssertTrue(KakaSystemSurface.tasks.isActionButtonRecommended)
        XCTAssertFalse(KakaSystemSurface.reviewInboxItem.isActionButtonRecommended)
        XCTAssertFalse(KakaSystemSurface.reviewRuntimeTask.isActionButtonRecommended)
    }

    func testActionButtonShortcutTitlesAreUserVisibleReviewLabels() {
        XCTAssertEqual(
            KakaAppIntentCatalog.actionButtonShortcuts.map(\.shortTitle),
            [
                "Open Inbox",
                "Show Tasks"
            ]
        )
        XCTAssertEqual(
            KakaAppIntentCatalog.actionButtonShortcuts.map(\.systemImageName),
            [
                "tray.full",
                "list.bullet.rectangle"
            ]
        )
    }
}
