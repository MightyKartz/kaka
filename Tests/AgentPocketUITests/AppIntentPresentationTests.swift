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
                "review_runtime_task",
                "open_agent_scanner",
                "scan_document",
                "capture_video",
                "record_voice"
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
        XCTAssertEqual(KakaSystemSurface.agentScanner.intentTitle, "Scan")
        XCTAssertEqual(KakaSystemSurface.documentScanner.intentTitle, "Document Scan")
        XCTAssertEqual(KakaSystemSurface.videoCapture.intentTitle, "Video")
        XCTAssertEqual(KakaSystemSurface.voiceRecorder.intentTitle, "Record")
        XCTAssertEqual(KakaAppIntentCatalog.destinationParameterTitle, "Destination")
        XCTAssertEqual(KakaAppIntentCatalog.taskIDParameterTitle, "Task ID")
        XCTAssertEqual(KakaAppIntentCatalog.taskActionParameterTitle, "Task Action")
    }

    func testActionButtonRecommendedShortcutsStayForegroundReviewOnly() {
        XCTAssertEqual(
            KakaAppIntentCatalog.actionButtonRecommendedActionIDs,
            [
                "open_inbox",
                "open_tasks",
                "open_agent_scanner",
                "scan_document",
                "capture_video",
                "record_voice"
            ]
        )
        XCTAssertTrue(KakaAppIntentCatalog.actionButtonUsesForegroundHandoff)
        XCTAssertFalse(KakaAppIntentCatalog.actionButtonAllowsBackgroundTaskMutation)
        XCTAssertFalse(KakaAppIntentCatalog.actionButtonAllowsRecallMutation)
        XCTAssertFalse(KakaAppIntentCatalog.actionButtonAllowsContextSnapshotCollection)
        XCTAssertFalse(KakaAppIntentCatalog.actionButtonAllowsRuntimeSettingsChanges)
    }

    func testLocalAgentLensShortcutsAreForegroundOnly() {
        XCTAssertEqual(
            KakaAppIntentCatalog.localAgentLensShortcutIDs,
            ["open_agent_scanner", "scan_document", "capture_video", "record_voice"]
        )
        XCTAssertTrue(KakaAppIntentCatalog.actionButtonUsesForegroundHandoff)
        XCTAssertFalse(KakaAppIntentCatalog.actionButtonAllowsBackgroundTaskMutation)
        XCTAssertFalse(KakaAppIntentCatalog.actionButtonAllowsRecallMutation)
        XCTAssertFalse(KakaAppIntentCatalog.actionButtonAllowsContextSnapshotCollection)
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
                ),
                KakaActionButtonShortcutMetadata(
                    actionID: "open_agent_scanner",
                    shortTitle: "Scan",
                    systemImageName: "qrcode.viewfinder",
                    targetSurface: .agentScanner
                ),
                KakaActionButtonShortcutMetadata(
                    actionID: "scan_document",
                    shortTitle: "Document",
                    systemImageName: "doc.viewfinder",
                    targetSurface: .documentScanner
                ),
                KakaActionButtonShortcutMetadata(
                    actionID: "capture_video",
                    shortTitle: "Video",
                    systemImageName: "video.badge.waveform",
                    targetSurface: .videoCapture
                ),
                KakaActionButtonShortcutMetadata(
                    actionID: "record_voice",
                    shortTitle: "Record",
                    systemImageName: "mic.circle",
                    targetSurface: .voiceRecorder
                )
            ]
        )
    }

    func testOnlyTopLevelReviewSurfacesAreActionButtonRecommended() {
        XCTAssertTrue(KakaSystemSurface.inbox.isActionButtonRecommended)
        XCTAssertTrue(KakaSystemSurface.tasks.isActionButtonRecommended)
        XCTAssertTrue(KakaSystemSurface.agentScanner.isActionButtonRecommended)
        XCTAssertTrue(KakaSystemSurface.documentScanner.isActionButtonRecommended)
        XCTAssertTrue(KakaSystemSurface.videoCapture.isActionButtonRecommended)
        XCTAssertTrue(KakaSystemSurface.voiceRecorder.isActionButtonRecommended)
        XCTAssertFalse(KakaSystemSurface.reviewInboxItem.isActionButtonRecommended)
        XCTAssertFalse(KakaSystemSurface.reviewRuntimeTask.isActionButtonRecommended)
    }

    func testActionButtonShortcutTitlesAreUserVisibleReviewLabels() {
        XCTAssertEqual(
            KakaAppIntentCatalog.actionButtonShortcuts.map(\.shortTitle),
            [
                "Open Inbox",
                "Show Tasks",
                "Scan",
                "Document",
                "Video",
                "Record"
            ]
        )
        XCTAssertEqual(
            KakaAppIntentCatalog.actionButtonShortcuts.map(\.systemImageName),
            [
                "tray.full",
                "list.bullet.rectangle",
                "qrcode.viewfinder",
                "doc.viewfinder",
                "video.badge.waveform",
                "mic.circle"
            ]
        )
    }
}
