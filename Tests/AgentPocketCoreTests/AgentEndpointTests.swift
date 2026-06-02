import XCTest
@testable import AgentPocketCore

final class AgentEndpointTests: XCTestCase {
    func testAcceptsHttpsRemoteEndpoint() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")

        XCTAssertEqual(endpoint.baseURL.absoluteString, "https://hermes.example.com")
        XCTAssertEqual(endpoint.displayName, "hermes.example.com")
        XCTAssertFalse(endpoint.isTrustedLocalDevelopmentEndpoint)
    }

    func testRejectsHttpRemoteEndpoint() {
        XCTAssertThrowsError(try AgentEndpoint(rawURL: "http://example.com")) { error in
            XCTAssertEqual(error as? AgentEndpoint.ValidationError, .remoteEndpointRequiresHTTPS)
        }
    }

    func testAcceptsLocalhostHttpForDevelopment() throws {
        let endpoint = try AgentEndpoint(rawURL: "http://127.0.0.1:8765")

        XCTAssertTrue(endpoint.isTrustedLocalDevelopmentEndpoint)
    }

    func testAcceptsPrivateLANHttpForDevelopment() throws {
        let endpoint = try AgentEndpoint(rawURL: "http://192.168.1.42:8765")

        XCTAssertEqual(endpoint.baseURL.absoluteString, "http://192.168.1.42:8765")
        XCTAssertTrue(endpoint.isTrustedLocalDevelopmentEndpoint)
    }

    func testAcceptsTailscaleCGNATHttpForDevelopment() throws {
        let endpoint = try AgentEndpoint(rawURL: "http://100.88.12.34:8765")

        XCTAssertTrue(endpoint.isTrustedLocalDevelopmentEndpoint)
    }

    func testAcceptsBonjourLocalHTTPForDevelopment() throws {
        let endpoint = try AgentEndpoint(rawURL: "http://macbook-pro.local:8765")

        XCTAssertTrue(endpoint.isTrustedLocalDevelopmentEndpoint)
    }

    func testRejectsPublicHttpEndpoint() {
        XCTAssertThrowsError(try AgentEndpoint(rawURL: "http://8.8.8.8:8765")) { error in
            XCTAssertEqual(error as? AgentEndpoint.ValidationError, .remoteEndpointRequiresHTTPS)
        }
    }

    func testRejectsMissingHost() {
        XCTAssertThrowsError(try AgentEndpoint(rawURL: "https:///mobile/v1")) { error in
            XCTAssertEqual(error as? AgentEndpoint.ValidationError, .invalidURL)
        }
    }
}
