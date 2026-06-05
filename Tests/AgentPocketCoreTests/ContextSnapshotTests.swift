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
            locationLabel: "near_home"
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
        XCTAssertNil(object["locationLabel"])
    }

    private func encodedJSONObject(_ snapshot: ContextSnapshotPayload) throws -> [String: Any] {
        let data = try JSONEncoder.mobileBridge.encode(snapshot)
        return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }
}
