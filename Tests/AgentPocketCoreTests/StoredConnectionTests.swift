import XCTest
@testable import AgentPocketCore

final class StoredConnectionTests: XCTestCase {
    func testStoredConnectionRoundTripsThroughBridgeJSONCoding() throws {
        let connection = StoredConnection(
            endpoint: try AgentEndpoint(
                rawURL: "https://hermes.example.com",
                runtime: "hermes",
                displayName: "Kartz MacBook Hermes"
            ),
            displayName: "Kartz MacBook Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "mobile_secret",
            tokenExpiresAt: "2026-06-01T00:00:00Z",
            tlsPublicKeySHA256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )

        let data = try JSONEncoder.mobileBridge.encode(connection)
        let decoded = try JSONDecoder.mobileBridge.decode(StoredConnection.self, from: data)

        XCTAssertEqual(decoded, connection)
        XCTAssertEqual(decoded.tlsPublicKeySHA256, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        XCTAssertEqual(
            decoded.trustPolicy,
            .pinnedPublicKeySHA256("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        )
    }

    func testStoredConnectionDecodesLegacyPayloadWithoutTLSPin() throws {
        let data = Data(
            """
            {"endpoint":"https://hermes.example.com","display_name":"Kartz MacBook Hermes","runtime":"hermes","runtime_version":"2026.5.16","mobile_token":"mobile_secret","token_expires_at":null}
            """.utf8
        )

        let decoded = try JSONDecoder.mobileBridge.decode(StoredConnection.self, from: data)

        XCTAssertNil(decoded.tlsPublicKeySHA256)
        XCTAssertEqual(decoded.trustPolicy, .systemDefault)
    }

    func testKeychainStoreSavesLoadsAndClearsConnection() throws {
        let store = KeychainConnectionStore(
            service: "com.kaka.AgentPocket.tests.\(UUID().uuidString)",
            account: "connection"
        )
        let connection = StoredConnection(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            displayName: "Kartz MacBook Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "mobile_secret",
            tokenExpiresAt: nil
        )
        defer { try? store.clear() }

        try store.save(connection)

        XCTAssertEqual(try store.load(), connection)

        try store.clear()

        XCTAssertNil(try store.load())
    }
}
