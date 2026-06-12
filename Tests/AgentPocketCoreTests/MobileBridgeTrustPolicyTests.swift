import XCTest
@testable import AgentPocketCore

final class MobileBridgeTrustPolicyTests: XCTestCase {
    func testUsesPinnedPublicKeyForHTTPSPairingFingerprint() throws {
        let endpoint = try AgentEndpoint(
            rawURL: "https://macbook-pro.local:8765",
            runtime: "hermes",
            displayName: "Hermes"
        )

        let policy = MobileBridgeTrustPolicy.policy(
            for: endpoint,
            tlsPublicKeySHA256: "AA11BB22CC33DD44EE55FF6600112233445566778899AABBCCDDEEFF00112233"
        )

        XCTAssertEqual(
            policy,
            .pinnedPublicKeySHA256("aa11bb22cc33dd44ee55ff6600112233445566778899aabbccddeeff00112233")
        )
    }

    func testUsesSystemDefaultForHTTPSWithoutFingerprint() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://macbook-pro.local:8765")

        XCTAssertEqual(
            MobileBridgeTrustPolicy.policy(for: endpoint, tlsPublicKeySHA256: nil),
            .systemDefault
        )
    }

    func testUsesSystemDefaultForLocalHTTPEvenWithFingerprint() throws {
        let endpoint = try AgentEndpoint(rawURL: "http://macbook-pro.local:8765")

        XCTAssertEqual(
            MobileBridgeTrustPolicy.policy(
                for: endpoint,
                tlsPublicKeySHA256: String(repeating: "a", count: 64)
            ),
            .systemDefault
        )
    }

    func testRejectsMalformedFingerprint() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://macbook-pro.local:8765")

        XCTAssertEqual(
            MobileBridgeTrustPolicy.policy(for: endpoint, tlsPublicKeySHA256: "not-a-fingerprint"),
            .systemDefault
        )
    }

    func testPinnedPublicKeyHashComparisonNormalizesPresentedHash() {
        XCTAssertTrue(
            MobileBridgePinnedTrustDelegate.publicKeySHA256Matches(
                presentedSHA256: "AA11BB22CC33DD44EE55FF6600112233445566778899AABBCCDDEEFF00112233",
                pinnedSHA256: "aa11bb22cc33dd44ee55ff6600112233445566778899aabbccddeeff00112233"
            )
        )
        XCTAssertFalse(
            MobileBridgePinnedTrustDelegate.publicKeySHA256Matches(
                presentedSHA256: "bb11bb22cc33dd44ee55ff6600112233445566778899aabbccddeeff00112233",
                pinnedSHA256: "aa11bb22cc33dd44ee55ff6600112233445566778899aabbccddeeff00112233"
            )
        )
    }
}
