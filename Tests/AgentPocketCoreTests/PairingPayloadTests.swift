import XCTest
@testable import AgentPocketCore

final class PairingPayloadTests: XCTestCase {
    func testDecodesValidPairingPayload() throws {
        let json = """
        {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z"}
        """

        let payload = try PairingPayload(
            jsonString: json,
            now: ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
        )

        XCTAssertEqual(payload.endpoint.baseURL.absoluteString, "https://macbook-pro.local:8765")
        XCTAssertEqual(payload.runtime, "hermes")
        XCTAssertEqual(payload.displayName, "Kartz MacBook Hermes")
        XCTAssertEqual(payload.pairingCode, "pair_123")
    }

    func testRejectsExpiredPairingPayload() {
        let json = """
        {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z"}
        """

        XCTAssertThrowsError(
            try PairingPayload(
                jsonString: json,
                now: ISO8601DateFormatter().date(from: "2026-05-30T16:31:00Z")!
            )
        ) { error in
            XCTAssertEqual(error as? PairingPayload.ValidationError, .expired)
        }
    }

    func testRejectsUnsupportedVersion() {
        let json = """
        {"version":2,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z"}
        """

        XCTAssertThrowsError(
            try PairingPayload(
                jsonString: json,
                now: ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
            )
        ) { error in
            XCTAssertEqual(error as? PairingPayload.ValidationError, .unsupportedVersion)
        }
    }
}
