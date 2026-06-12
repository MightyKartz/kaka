import XCTest
@testable import AgentPocketCore

final class ContextSnapshotTests: XCTestCase {
    func testMinimalSnapshotEncodingUsesSnakeCaseAndOmitsNilFields() throws {
        let snapshot = ContextSnapshotPayload(
            timestamp: "2026-06-05T09:30:00Z",
            timezone: "Asia/Shanghai",
            sourceSurface: "share_extension"
        )

        let object = try encodedJSONObject(snapshot)

        XCTAssertEqual(object["timestamp"] as? String, "2026-06-05T09:30:00Z")
        XCTAssertEqual(object["timezone"] as? String, "Asia/Shanghai")
        XCTAssertEqual(object["source_surface"] as? String, "share_extension")
        XCTAssertNil(object["sourceSurface"])
        XCTAssertNil(object["locale"])
        XCTAssertNil(object["network"])
        XCTAssertNil(object["battery"])
        XCTAssertNil(object["motion"])
        XCTAssertNil(object["location_label"])
        XCTAssertNil(object["location_precision"])
        XCTAssertNil(object["calendar_availability"])
    }

    func testExpandedSnapshotEncodingUsesSnakeCaseAndOmitsNilFields() throws {
        let snapshot = ContextSnapshotPayload(
            timestamp: "2026-06-05T09:30:00Z",
            timezone: "Asia/Shanghai",
            locale: "zh-Hans",
            sourceSurface: "share_extension",
            network: "wifi",
            battery: "charging",
            motion: "stationary",
            locationLabel: "near_home",
            locationPrecision: "coarse",
            calendarAvailability: "busy_soon"
        )

        let object = try encodedJSONObject(snapshot)

        XCTAssertEqual(object["timestamp"] as? String, "2026-06-05T09:30:00Z")
        XCTAssertEqual(object["timezone"] as? String, "Asia/Shanghai")
        XCTAssertEqual(object["locale"] as? String, "zh-Hans")
        XCTAssertEqual(object["source_surface"] as? String, "share_extension")
        XCTAssertEqual(object["network"] as? String, "wifi")
        XCTAssertEqual(object["battery"] as? String, "charging")
        XCTAssertEqual(object["motion"] as? String, "stationary")
        XCTAssertEqual(object["location_label"] as? String, "near_home")
        XCTAssertEqual(object["location_precision"] as? String, "coarse")
        XCTAssertEqual(object["calendar_availability"] as? String, "busy_soon")
        XCTAssertNil(object["locationLabel"])
        XCTAssertNil(object["locationPrecision"])
        XCTAssertNil(object["calendarAvailability"])
    }

    func testPermissionedCollectorMergesFieldStatusesWithoutThrowingOnDeniedContext() async throws {
        let collector = PermissionedContextSnapshotCollector(
            sourceSurface: "share_extension",
            localeProvider: { "zh-Hans" },
            dateProvider: { Date(timeIntervalSince1970: 1_780_665_000) },
            timeZoneProvider: { TimeZone(identifier: "Asia/Shanghai")! },
            fieldCollector: StaticContextSnapshotFieldCollector(
                values: ContextSnapshotFieldValues(
                    network: "wifi",
                    battery: "charging_80_percent",
                    motion: "permission_denied",
                    locationLabel: "permission_denied",
                    locationPrecision: "none",
                    calendarAvailability: "unavailable"
                )
            )
        )

        let snapshot = try await collector.collectContextSnapshot()
        let object = try encodedJSONObject(snapshot)

        XCTAssertEqual(object["source_surface"] as? String, "share_extension")
        XCTAssertEqual(object["network"] as? String, "wifi")
        XCTAssertEqual(object["battery"] as? String, "charging_80_percent")
        XCTAssertEqual(object["motion"] as? String, "permission_denied")
        XCTAssertEqual(object["location_label"] as? String, "permission_denied")
        XCTAssertEqual(object["location_precision"] as? String, "none")
        XCTAssertEqual(object["calendar_availability"] as? String, "unavailable")
    }

    func testNetworkPathStatusMapperUsesOnlyCoarseLabels() {
        XCTAssertEqual(
            ContextSnapshotNetworkPathState(isSatisfied: false, isConstrained: false, interfaces: []).snapshotNetworkStatus,
            "offline"
        )
        XCTAssertEqual(
            ContextSnapshotNetworkPathState(isSatisfied: true, isConstrained: true, interfaces: [.wifi]).snapshotNetworkStatus,
            "constrained"
        )
        XCTAssertEqual(
            ContextSnapshotNetworkPathState(isSatisfied: true, isConstrained: false, interfaces: [.wifi]).snapshotNetworkStatus,
            "wifi"
        )
        XCTAssertEqual(
            ContextSnapshotNetworkPathState(isSatisfied: true, isConstrained: false, interfaces: [.cellular]).snapshotNetworkStatus,
            "cellular"
        )
        XCTAssertEqual(
            ContextSnapshotNetworkPathState(isSatisfied: true, isConstrained: false, interfaces: [.other]).snapshotNetworkStatus,
            "unknown"
        )
    }

    func testSystemCollectorUsesInjectedNetworkPathSampler() async {
        let collector = SystemContextSnapshotFieldCollector(
            networkPathSampler: StaticContextSnapshotNetworkPathSampler(status: "cellular")
        )

        let fields = await collector.collectContextSnapshotFields()

        XCTAssertEqual(fields.network, "cellular")
    }

    func testStaticUnavailableSamplerKeepsNetworkFieldPreviewable() async throws {
        let collector = PermissionedContextSnapshotCollector(
            sourceSurface: "share_extension",
            localeProvider: { "en-US" },
            dateProvider: { Date(timeIntervalSince1970: 1_780_665_000) },
            timeZoneProvider: { TimeZone(identifier: "America/Los_Angeles")! },
            fieldCollector: SystemContextSnapshotFieldCollector(
                networkPathSampler: StaticContextSnapshotNetworkPathSampler(status: "unavailable")
            )
        )

        let snapshot = try await collector.collectContextSnapshot()

        XCTAssertEqual(snapshot.network, "unavailable")
    }

    func testMotionActivityStatusMapperUsesOnlyCoarseLabels() {
        XCTAssertEqual(
            ContextSnapshotMotionActivityState(isStationary: true).snapshotMotionStatus,
            "stationary"
        )
        XCTAssertEqual(
            ContextSnapshotMotionActivityState(isWalking: true).snapshotMotionStatus,
            "walking"
        )
        XCTAssertEqual(
            ContextSnapshotMotionActivityState(isRunning: true).snapshotMotionStatus,
            "running"
        )
        XCTAssertEqual(
            ContextSnapshotMotionActivityState(isWalking: true, isAutomotive: true).snapshotMotionStatus,
            "driving"
        )
        XCTAssertEqual(
            ContextSnapshotMotionActivityState().snapshotMotionStatus,
            "unknown"
        )
    }

    func testMotionAuthorizationMapperDoesNotPromptForUndeterminedOrDeniedStates() {
        XCTAssertEqual(
            ContextSnapshotMotionActivityAuthorizationStatus.notDetermined.snapshotMotionStatus,
            "not_requested"
        )
        XCTAssertEqual(
            ContextSnapshotMotionActivityAuthorizationStatus.denied.snapshotMotionStatus,
            "permission_denied"
        )
        XCTAssertEqual(
            ContextSnapshotMotionActivityAuthorizationStatus.restricted.snapshotMotionStatus,
            "permission_denied"
        )
        XCTAssertNil(ContextSnapshotMotionActivityAuthorizationStatus.authorized.snapshotMotionStatus)
    }

    func testSystemCollectorUsesInjectedMotionActivitySampler() async {
        let collector = SystemContextSnapshotFieldCollector(
            networkPathSampler: StaticContextSnapshotNetworkPathSampler(status: "wifi"),
            motionActivitySampler: StaticContextSnapshotMotionActivitySampler(status: "walking")
        )

        let fields = await collector.collectContextSnapshotFields()

        XCTAssertEqual(fields.motion, "walking")
    }

    func testCalendarBusyWindowUsesOnlyAvailabilityLabels() {
        let now = Date(timeIntervalSince1970: 1_780_665_000)
        let end = now.addingTimeInterval(30 * 60)

        XCTAssertEqual(
            ContextSnapshotCalendarAvailabilityWindow(
                now: now,
                end: end,
                busyIntervals: []
            ).snapshotCalendarAvailability,
            "free"
        )
        XCTAssertEqual(
            ContextSnapshotCalendarAvailabilityWindow(
                now: now,
                end: end,
                busyIntervals: [
                    ContextSnapshotCalendarBusyInterval(
                        start: now.addingTimeInterval(-60),
                        end: now.addingTimeInterval(60)
                    )
                ]
            ).snapshotCalendarAvailability,
            "busy"
        )
        XCTAssertEqual(
            ContextSnapshotCalendarAvailabilityWindow(
                now: now,
                end: end,
                busyIntervals: [
                    ContextSnapshotCalendarBusyInterval(
                        start: now.addingTimeInterval(10 * 60),
                        end: now.addingTimeInterval(20 * 60)
                    )
                ]
            ).snapshotCalendarAvailability,
            "busy_soon"
        )
        XCTAssertEqual(
            ContextSnapshotCalendarAvailabilityWindow(
                now: now,
                end: end,
                busyIntervals: [
                    ContextSnapshotCalendarBusyInterval(
                        start: now.addingTimeInterval(45 * 60),
                        end: now.addingTimeInterval(50 * 60)
                    )
                ]
            ).snapshotCalendarAvailability,
            "free"
        )
    }

    func testCalendarAuthorizationMapperDoesNotRequestAccessForUnreadableStates() {
        XCTAssertEqual(
            ContextSnapshotCalendarAuthorizationStatus.notDetermined.snapshotCalendarAvailability,
            "not_requested"
        )
        XCTAssertEqual(
            ContextSnapshotCalendarAuthorizationStatus.denied.snapshotCalendarAvailability,
            "permission_denied"
        )
        XCTAssertEqual(
            ContextSnapshotCalendarAuthorizationStatus.restricted.snapshotCalendarAvailability,
            "permission_denied"
        )
        XCTAssertEqual(
            ContextSnapshotCalendarAuthorizationStatus.writeOnly.snapshotCalendarAvailability,
            "write_only"
        )
        XCTAssertNil(ContextSnapshotCalendarAuthorizationStatus.readable.snapshotCalendarAvailability)
    }

    func testSystemCollectorUsesInjectedCalendarAvailabilitySampler() async {
        let collector = SystemContextSnapshotFieldCollector(
            networkPathSampler: StaticContextSnapshotNetworkPathSampler(status: "wifi"),
            calendarAvailabilitySampler: StaticContextSnapshotCalendarAvailabilitySampler(status: "busy_soon")
        )

        let fields = await collector.collectContextSnapshotFields()

        XCTAssertEqual(fields.calendarAvailability, "busy_soon")
    }

    private func encodedJSONObject(_ snapshot: ContextSnapshotPayload) throws -> [String: Any] {
        let data = try JSONEncoder.mobileBridge.encode(snapshot)
        return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }
}
