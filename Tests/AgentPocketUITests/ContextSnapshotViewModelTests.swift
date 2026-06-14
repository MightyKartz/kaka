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

    func testPermissionedCollectorKeepsDeniedFieldStatusesPreviewableWithoutForcingSubmission() async throws {
        let collector = PermissionedContextSnapshotCollector(
            sourceSurface: "share_extension",
            localeProvider: { "zh-Hans" },
            dateProvider: { Date(timeIntervalSince1970: 1_780_665_000) },
            timeZoneProvider: { TimeZone(identifier: "Asia/Shanghai")! },
            fieldCollector: StaticContextSnapshotFieldCollector(
                values: ContextSnapshotFieldValues(
                    network: "wifi",
                    battery: "unavailable",
                    motion: "permission_denied",
                    locationLabel: "not_requested",
                    locationPrecision: "none",
                    calendarAvailability: "permission_denied"
                )
            )
        )
        let viewModel = ContextSnapshotViewModel(collector: collector)

        await viewModel.refresh()

        XCTAssertEqual(viewModel.snapshotPreview?.network, "wifi")
        XCTAssertEqual(viewModel.snapshotPreview?.battery, "unavailable")
        XCTAssertEqual(viewModel.snapshotPreview?.motion, "permission_denied")
        XCTAssertEqual(viewModel.snapshotPreview?.locationLabel, "not_requested")
        XCTAssertEqual(viewModel.snapshotPreview?.locationPrecision, "none")
        XCTAssertEqual(viewModel.snapshotPreview?.calendarAvailability, "permission_denied")
        XCTAssertNil(viewModel.permissionMessage)
        XCTAssertFalse(viewModel.includeContext)
        XCTAssertNil(viewModel.selectedSnapshotForSubmission)
    }

    func testPreviewRowsDescribePermissionSentinelsWithoutChangingSubmittedSnapshot() async {
        let snapshot = ContextSnapshotPayload(
            timestamp: "2026-06-07T10:00:00Z",
            timezone: "Asia/Shanghai",
            locale: "zh-Hans",
            sourceSurface: "share_extension",
            network: "wifi",
            battery: "unavailable",
            motion: "permission_denied",
            locationLabel: "not_requested",
            locationPrecision: "none",
            calendarAvailability: "permission_denied"
        )
        let viewModel = ContextSnapshotViewModel(
            collector: StubContextSnapshotCollector(result: .success(snapshot))
        )

        await viewModel.refresh()
        viewModel.includeContext = true

        XCTAssertEqual(
            viewModel.previewRows.map(\.label),
            ["Time", "Timezone", "Locale", "Source", "Network", "Battery", "Motion", "Location", "Precision", "Calendar"]
        )
        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Motion", value: "Permission denied")))
        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Location", value: "Not requested for this task")))
        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Battery", value: "Unavailable")))
        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Precision", value: "Not included")))
        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Calendar", value: "Permission denied")))
        XCTAssertEqual(viewModel.selectedSnapshotForSubmission?.motion, "permission_denied")
        XCTAssertEqual(viewModel.selectedSnapshotForSubmission?.locationLabel, "not_requested")
        XCTAssertFalse(viewModel.isContextSnapshotPreparing)
    }

    func testPreviewRowsDescribeCoarseContextValues() async {
        let snapshot = ContextSnapshotPayload(
            timestamp: "2026-06-07T10:00:00Z",
            timezone: "Asia/Shanghai",
            sourceSurface: "share_extension",
            network: "constrained",
            battery: "charging_80_percent",
            motion: "available",
            locationLabel: "available",
            locationPrecision: "coarse",
            calendarAvailability: "write_only"
        )
        let viewModel = ContextSnapshotViewModel(
            collector: StubContextSnapshotCollector(result: .success(snapshot))
        )

        await viewModel.refresh()

        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Network", value: "Limited network")))
        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Battery", value: "Charging, 80%")))
        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Motion", value: "Available")))
        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Location", value: "Allowed for this task")))
        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Precision", value: "Approximate")))
        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Calendar", value: "Write-only access")))
        XCTAssertEqual(viewModel.snapshotPreview?.network, "constrained")
        XCTAssertEqual(viewModel.snapshotPreview?.battery, "charging_80_percent")
        XCTAssertFalse(viewModel.isContextSnapshotPreparing)
    }

    func testPreviewRowsUseUserFacingLocalAgentLensSources() async {
        let cases: [(AgentLensSourceSurface, String)] = [
            (.agentScanner, "Scanner"),
            (.documentScanner, "Document Scan"),
            (.videoCapture, "Video")
        ]

        for (sourceSurface, expectedValue) in cases {
            let snapshot = ContextSnapshotPayload(
                timestamp: "2026-06-07T10:00:00Z",
                timezone: "Asia/Shanghai",
                sourceSurface: sourceSurface.rawValue
            )
            let viewModel = ContextSnapshotViewModel(
                collector: StubContextSnapshotCollector(result: .success(snapshot))
            )

            await viewModel.refresh()

            XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Source", value: expectedValue)))
        }
    }

    func testPreviewRowsDescribeMotionAndCalendarBusyWindowValuesWithoutChangingPayload() async {
        let snapshot = ContextSnapshotPayload(
            timestamp: "2026-06-07T10:00:00Z",
            timezone: "Asia/Shanghai",
            sourceSurface: "share_extension",
            motion: "walking",
            calendarAvailability: "busy_soon"
        )
        let viewModel = ContextSnapshotViewModel(
            collector: StubContextSnapshotCollector(result: .success(snapshot))
        )

        await viewModel.refresh()
        viewModel.includeContext = true

        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Motion", value: "Walking")))
        XCTAssertTrue(viewModel.previewRows.contains(.init(label: "Calendar", value: "Busy in the next 30 minutes")))
        XCTAssertEqual(viewModel.selectedSnapshotForSubmission?.motion, "walking")
        XCTAssertEqual(viewModel.selectedSnapshotForSubmission?.calendarAvailability, "busy_soon")
    }

    func testCollectExposesPreparingStateAndResetClearsIt() async {
        let collector = DelayedContextSnapshotCollector()
        let viewModel = ContextSnapshotViewModel(collector: collector)

        let refreshTask = Task { @MainActor in
            await viewModel.refresh()
        }
        await collector.waitUntilStarted()

        XCTAssertTrue(viewModel.isContextSnapshotPreparing)

        viewModel.resetPerTaskConsent()

        XCTAssertFalse(viewModel.isContextSnapshotPreparing)

        await collector.complete(
            with: ContextSnapshotPayload(
                timestamp: "2026-06-07T10:00:00Z",
                timezone: "Asia/Shanghai",
                sourceSurface: "share_extension",
                network: "wifi"
            )
        )
        await refreshTask.value

        XCTAssertNil(viewModel.snapshotPreview)
        XCTAssertFalse(viewModel.isContextSnapshotPreparing)
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

    func testResetPerTaskConsentClearsCachedPreviewForNextTask() async {
        let viewModel = ContextSnapshotViewModel(
            includeContext: true,
            collector: StubContextSnapshotCollector(result: .success(.minimal))
        )

        await viewModel.refresh()
        viewModel.resetPerTaskConsent()

        XCTAssertFalse(viewModel.includeContext)
        XCTAssertNil(viewModel.snapshotPreview)
        XCTAssertNil(viewModel.permissionMessage)
        XCTAssertNil(viewModel.selectedSnapshotForSubmission)
    }

    func testRefreshForInclusionCollectsFreshPreviewAfterReset() async {
        let collector = SequenceContextSnapshotCollector(snapshots: [
            ContextSnapshotPayload(
                timestamp: "2026-06-05T09:30:00Z",
                timezone: "Asia/Shanghai",
                sourceSurface: "share_extension",
                battery: "normal"
            ),
            ContextSnapshotPayload(
                timestamp: "2026-06-05T09:31:00Z",
                timezone: "Asia/Shanghai",
                sourceSurface: "share_extension",
                battery: "low"
            )
        ])
        let viewModel = ContextSnapshotViewModel(collector: collector)

        await viewModel.refresh()
        viewModel.includeContext = true
        XCTAssertEqual(viewModel.selectedSnapshotForSubmission?.timestamp, "2026-06-05T09:30:00Z")

        viewModel.resetPerTaskConsent()
        viewModel.includeContext = true
        await viewModel.refreshForInclusionIfNeeded()

        XCTAssertEqual(viewModel.snapshotPreview?.timestamp, "2026-06-05T09:31:00Z")
        XCTAssertEqual(viewModel.selectedSnapshotForSubmission?.battery, "low")
    }

    func testResetThenIncludeAgainCollectsFreshNetworkStatus() async {
        let collector = SequenceContextSnapshotCollector(snapshots: [
            ContextSnapshotPayload(
                timestamp: "2026-06-05T09:30:00Z",
                timezone: "Asia/Shanghai",
                sourceSurface: "share_extension",
                network: "wifi"
            ),
            ContextSnapshotPayload(
                timestamp: "2026-06-05T09:31:00Z",
                timezone: "Asia/Shanghai",
                sourceSurface: "share_extension",
                network: "cellular"
            )
        ])
        let viewModel = ContextSnapshotViewModel(collector: collector)

        await viewModel.refresh()
        viewModel.includeContext = true
        XCTAssertEqual(viewModel.selectedSnapshotForSubmission?.network, "wifi")

        viewModel.resetPerTaskConsent()
        viewModel.includeContext = true
        await viewModel.refreshForInclusionIfNeeded()

        XCTAssertEqual(viewModel.selectedSnapshotForSubmission?.network, "cellular")
    }

    func testResetIgnoresInFlightSnapshotResult() async {
        let collector = DelayedContextSnapshotCollector()
        let viewModel = ContextSnapshotViewModel(collector: collector)

        let refreshTask = Task { @MainActor in
            await viewModel.refresh()
        }
        await collector.waitUntilStarted()
        viewModel.resetPerTaskConsent()
        await collector.complete(
            with: ContextSnapshotPayload(
                timestamp: "2026-06-05T09:30:00Z",
                timezone: "Asia/Shanghai",
                sourceSurface: "share_extension",
                network: "wifi"
            )
        )
        await refreshTask.value

        XCTAssertNil(viewModel.snapshotPreview)
        XCTAssertNil(viewModel.permissionMessage)
        XCTAssertNil(viewModel.selectedSnapshotForSubmission)
    }
}

private struct StubContextSnapshotCollector: ContextSnapshotCollecting {
    let result: Result<ContextSnapshotPayload, ContextSnapshotCollectionError>

    func collectContextSnapshot() async throws -> ContextSnapshotPayload {
        try result.get()
    }
}

private actor SequenceContextSnapshotCollector: ContextSnapshotCollecting {
    private var snapshots: [ContextSnapshotPayload]

    init(snapshots: [ContextSnapshotPayload]) {
        self.snapshots = snapshots
    }

    func collectContextSnapshot() async throws -> ContextSnapshotPayload {
        snapshots.removeFirst()
    }
}

private actor DelayedContextSnapshotCollector: ContextSnapshotCollecting {
    private var continuation: CheckedContinuation<ContextSnapshotPayload, Error>?

    func collectContextSnapshot() async throws -> ContextSnapshotPayload {
        try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation
        }
    }

    func waitUntilStarted() async {
        while continuation == nil {
            await Task.yield()
        }
    }

    func complete(with snapshot: ContextSnapshotPayload) {
        continuation?.resume(returning: snapshot)
        continuation = nil
    }
}

private extension ContextSnapshotPayload {
    static let minimal = ContextSnapshotPayload(
        timestamp: "2026-06-05T09:30:00Z",
        timezone: "Asia/Shanghai",
        sourceSurface: "share_extension"
    )
}
