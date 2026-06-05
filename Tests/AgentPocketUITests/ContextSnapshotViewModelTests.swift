import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class ContextSnapshotViewModelTests: XCTestCase {
    func testIncludeContextDefaultsFalse() {
        let viewModel = ContextSnapshotViewModel(
            collector: StubContextSnapshotCollector(result: .success(.minimal))
        )

        XCTAssertFalse(viewModel.includeContext)
        XCTAssertNil(viewModel.selectedSnapshotForSubmission)
    }

    func testSelectedSnapshotForSubmissionIsNilWhenIncludeContextIsFalse() async {
        let viewModel = ContextSnapshotViewModel(
            collector: StubContextSnapshotCollector(result: .success(.minimal))
        )

        await viewModel.refresh()

        XCTAssertNotNil(viewModel.snapshotPreview)
        XCTAssertNil(viewModel.selectedSnapshotForSubmission)
    }

    func testDeniedCollectorSetsPermissionMessageWithoutForcingIncludeContext() async {
        let viewModel = ContextSnapshotViewModel(
            collector: StubContextSnapshotCollector(result: .failure(.permissionDenied("Location unavailable.")))
        )

        await viewModel.refresh()

        XCTAssertEqual(viewModel.permissionMessage, "Location unavailable.")
        XCTAssertNil(viewModel.snapshotPreview)
        XCTAssertFalse(viewModel.includeContext)
        XCTAssertNil(viewModel.selectedSnapshotForSubmission)
    }

    func testSuccessfulCollectorCanBeIncludedWhenIncludeContextIsTrue() async {
        let snapshot = ContextSnapshotPayload(
            timestamp: "2026-06-05T09:30:00Z",
            timezone: "Asia/Shanghai",
            locale: "zh-Hans",
            sourceSurface: "share_extension",
            network: "wifi"
        )
        let viewModel = ContextSnapshotViewModel(
            collector: StubContextSnapshotCollector(result: .success(snapshot))
        )

        await viewModel.refresh()
        viewModel.includeContext = true

        XCTAssertEqual(viewModel.snapshotPreview, snapshot)
        XCTAssertEqual(viewModel.selectedSnapshotForSubmission, snapshot)
        XCTAssertNil(viewModel.permissionMessage)
    }

    func testResetPerTaskConsentTurnsIncludeContextOff() {
        let viewModel = ContextSnapshotViewModel(
            includeContext: true,
            collector: StubContextSnapshotCollector(result: .success(.minimal))
        )

        viewModel.resetPerTaskConsent()

        XCTAssertFalse(viewModel.includeContext)
        XCTAssertNil(viewModel.selectedSnapshotForSubmission)
    }
}

private struct StubContextSnapshotCollector: ContextSnapshotCollecting {
    let result: Result<ContextSnapshotPayload, ContextSnapshotCollectionError>

    func collectContextSnapshot() async throws -> ContextSnapshotPayload {
        try result.get()
    }
}

private extension ContextSnapshotPayload {
    static let minimal = ContextSnapshotPayload(
        timestamp: "2026-06-05T09:30:00Z",
        timezone: "Asia/Shanghai",
        sourceSurface: "share_extension"
    )
}
