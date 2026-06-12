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
        XCTAssertNil(payload.tlsPublicKeySHA256)
        XCTAssertFalse(payload.trustedLocalTLSRequired)
    }

    func testDecodesOptionalTLSPublicKeyFingerprint() throws {
        let json = """
        {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z","tls_public_key_sha256":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA","trusted_local_tls_required":true,"tls_certificate_label":"Kaka Local Runtime"}
        """

        let payload = try PairingPayload(
            jsonString: json,
            now: ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
        )

        XCTAssertEqual(payload.tlsPublicKeySHA256, String(repeating: "a", count: 64))
        XCTAssertTrue(payload.trustedLocalTLSRequired)
        XCTAssertEqual(payload.tlsCertificateLabel, "Kaka Local Runtime")
    }

    func testRejectsRequiredLocalTLSWithoutFingerprint() {
        let json = """
        {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z","trusted_local_tls_required":true}
        """

        XCTAssertThrowsError(
            try PairingPayload(
                jsonString: json,
                now: ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
            )
        ) { error in
            XCTAssertEqual(error as? PairingPayload.ValidationError, .missingRequiredTLSPublicKeyFingerprint)
        }
    }

    func testRejectsRequiredLocalTLSWithMalformedFingerprint() {
        let json = """
        {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z","trusted_local_tls_required":true,"tls_public_key_sha256":"not-a-fingerprint"}
        """

        XCTAssertThrowsError(
            try PairingPayload(
                jsonString: json,
                now: ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
            )
        ) { error in
            XCTAssertEqual(error as? PairingPayload.ValidationError, .malformedRequiredTLSPublicKeyFingerprint)
        }
    }

    func testRejectsRequiredLocalTLSForHTTPEndpoint() {
        let json = """
        {"version":1,"endpoint":"http://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z","trusted_local_tls_required":true,"tls_public_key_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
        """

        XCTAssertThrowsError(
            try PairingPayload(
                jsonString: json,
                now: ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
            )
        ) { error in
            XCTAssertEqual(error as? PairingPayload.ValidationError, .trustedLocalTLSRequiresHTTPSEndpoint)
        }
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
