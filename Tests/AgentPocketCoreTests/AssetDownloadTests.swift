import Foundation
import XCTest
@testable import AgentPocketCore

final class AssetDownloadTests: XCTestCase {
    override func tearDown() {
        AssetDownloadMockURLProtocol.requestHandler = nil
        super.tearDown()
    }

    func testAssetDownloadRequestAcceptsRelativeDownloadURL() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")

        let request = MobileBridgeClient.makeAssetDownloadRequest(
            endpoint: endpoint,
            token: "abc123",
            downloadURL: "/mobile/v1/assets/asset_result/download"
        )

        XCTAssertEqual(request.httpMethod, "GET")
        XCTAssertEqual(request.url?.absoluteString, "https://hermes.example.com/mobile/v1/assets/asset_result/download")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
    }

    func testHTTPClientDownloadsAssetBytesAndMimeType() async throws {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [AssetDownloadMockURLProtocol.self]
        let session = URLSession(configuration: configuration)
        let client = MobileBridgeHTTPClient(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            token: "abc123",
            session: session
        )

        AssetDownloadMockURLProtocol.requestHandler = { request in
            XCTAssertEqual(request.url?.path, "/mobile/v1/assets/asset_result/download")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "image/png"]
            )!
            return (response, Data([0x89, 0x50, 0x4E, 0x47]))
        }

        let asset = try await client.downloadAsset(downloadURL: "/mobile/v1/assets/asset_result/download")

        XCTAssertEqual(asset.mimeType, "image/png")
        XCTAssertEqual(asset.data, Data([0x89, 0x50, 0x4E, 0x47]))
    }
}

private final class AssetDownloadMockURLProtocol: URLProtocol {
    nonisolated(unsafe) static var requestHandler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    override class func canInit(with request: URLRequest) -> Bool {
        true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        guard let requestHandler = Self.requestHandler else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
            return
        }

        do {
            let (response, data) = try requestHandler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}
