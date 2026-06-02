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
            tokenExpiresAt: "2026-06-01T00:00:00Z"
        )

        let data = try JSONEncoder.mobileBridge.encode(connection)
        let decoded = try JSONDecoder.mobileBridge.decode(StoredConnection.self, from: data)

        XCTAssertEqual(decoded, connection)
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
