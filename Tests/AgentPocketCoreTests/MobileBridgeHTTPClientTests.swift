import Foundation
import XCTest
@testable import AgentPocketCore

final class MobileBridgeHTTPClientTests: XCTestCase {
    override func tearDown() {
        MockURLProtocol.requestHandler = nil
        super.tearDown()
    }

    func testFetchHealthDecodesRuntimeStatus() async throws {
        let client = try makeClient()

        MockURLProtocol.requestHandler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(request.url?.path, "/mobile/v1/health")

            let data = """
            {"ok":true,"runtime":"hermes","runtime_version":"2026.5.16","bridge_version":"0.1.0"}
            """.data(using: .utf8)!
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
        }

        let response = try await client.fetchHealth()

        XCTAssertEqual(response.runtime, "hermes")
        XCTAssertEqual(response.runtimeVersion, "2026.5.16")
    }

    func testFetchCapabilitiesUsesBearerTokenAndDecodesPhotoEditCapability() async throws {
        let client = try makeClient()

        MockURLProtocol.requestHandler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(request.url?.path, "/mobile/v1/capabilities")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")

            let data = """
            {"profiles":[{"id":"photo-agent","display_name":"Photo Agent","capabilities":["photo_edit"]}],"tasks":{"photo_edit":{"max_upload_mb":30,"accepted_mime_types":["image/jpeg"],"styles":["natural_enhance"],"provider":"recipe_local","renderer":"local_parametric","variant_labels":["Master","Social"],"variant_ids":["variant_clean_pro","variant_social_pop"],"crop_aspects":["original","4:5","1:1"],"supports_crop_candidates":true,"supports_upscale_policy":true,"supports_sse":true,"return_variants_max":3}},"retention":{"input_assets_days":7,"output_assets_days":30,"task_history_days":30}}
            """.data(using: .utf8)!
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
        }

        let response = try await client.fetchCapabilities()

        XCTAssertEqual(response.tasks.photoEdit.maxUploadMB, 30)
        XCTAssertEqual(response.tasks.photoEdit.styles, ["natural_enhance"])
        XCTAssertEqual(response.tasks.photoEdit.provider, "recipe_local")
        XCTAssertEqual(response.tasks.photoEdit.renderer, "local_parametric")
        XCTAssertEqual(response.tasks.photoEdit.variantLabels, ["Master", "Social"])
        XCTAssertEqual(response.tasks.photoEdit.cropAspects, ["original", "4:5", "1:1"])
    }

    func testExchangePairingCodeSendsDevicePayloadAndDecodesMobileToken() async throws {
        let client = try makeClient()

        MockURLProtocol.requestHandler = { request in
            let body = String(data: request.httpBodyStreamData(), encoding: .utf8) ?? ""
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.path, "/mobile/v1/pairing/exchange")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            XCTAssertTrue(body.contains("\"pairing_code\":\"pair_123\""))
            XCTAssertTrue(body.contains("\"device_name\":\"Kartz iPhone\""))
            XCTAssertTrue(body.contains("\"device_public_id\":\"device_abc\""))

            let data = """
            {"endpoint_id":"endpoint_123","display_name":"Kartz MacBook Hermes","runtime":"hermes","runtime_version":"2026.5.16","mobile_token":"mobile_secret","token_expires_at":null}
            """.data(using: .utf8)!
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
        }

        let response = try await client.exchangePairingCode(
            pairingCode: "pair_123",
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(response.mobileToken, "mobile_secret")
        XCTAssertEqual(response.displayName, "Kartz MacBook Hermes")
    }

    func testFetchDevelopmentPairingPayloadReturnsRawPayloadWithoutBearerToken() async throws {
        let client = try makeClient()

        MockURLProtocol.requestHandler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(request.url?.path, "/mobile/v1/pairing/dev")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))

            let data = """
            {"version":1,"endpoint":"https://hermes.example.com","runtime":"hermes","display_name":"Hermes","pairing_code":"pair_dev_0002","expires_at":"2099-01-01T00:00:00Z"}
            """.data(using: .utf8)!
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
        }

        let payload = try await client.fetchDevelopmentPairingPayload()

        XCTAssertTrue(payload.contains("\"pairing_code\":\"pair_dev_0002\""))
    }

    func testUploadAssetSendsMultipartRequestAndDecodesResponse() async throws {
        let client = try makeClient()
        let upload = try ImageUploadPolicy(maxUploadMB: 30).prepare(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "photo.jpg",
            width: 640,
            height: 480,
            localCreationTime: nil
        )

        MockURLProtocol.requestHandler = { request in
            let body = String(data: request.httpBodyStreamData(), encoding: .utf8) ?? ""
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.path, "/mobile/v1/assets")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
            XCTAssertTrue(request.value(forHTTPHeaderField: "Content-Type")?.contains("multipart/form-data") == true)
            XCTAssertTrue(body.contains("name=\"file\"; filename=\"photo.jpg\""))

            let data = """
            {"asset_id":"asset_123","mime_type":"image/jpeg","size_bytes":10,"sha256":"abc"}
            """.data(using: .utf8)!
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
        }

        let response = try await client.uploadAsset(upload)

        XCTAssertEqual(response.assetID, "asset_123")
    }

    func testStartPhotoEditTaskSendsJSONAndDecodesResponse() async throws {
        let client = try makeClient()
        let task = PhotoEditTaskRequest(
            profileID: "photo-agent",
            assetID: "asset_123",
            intent: .naturalEnhance,
            returnVariants: 3
        )

        MockURLProtocol.requestHandler = { request in
            let body = String(data: request.httpBodyStreamData(), encoding: .utf8) ?? ""
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.path, "/mobile/v1/tasks/photo-edit")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
            XCTAssertTrue(body.contains("\"asset_id\":\"asset_123\""))
            XCTAssertTrue(body.contains("\"style\":\"natural_enhance\""))

            let data = """
            {"task_id":"task_123","status":"queued","events_url":"/mobile/v1/tasks/task_123/events"}
            """.data(using: .utf8)!
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
        }

        let response = try await client.startPhotoEditTask(task)

        XCTAssertEqual(response.taskID, "task_123")
        XCTAssertEqual(response.eventsURL, "/mobile/v1/tasks/task_123/events")
    }

    private func makeClient() throws -> MobileBridgeHTTPClient {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [MockURLProtocol.self]
        let session = URLSession(configuration: configuration)
        return MobileBridgeHTTPClient(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            token: "abc123",
            session: session
        )
    }
}

private final class MockURLProtocol: URLProtocol {
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

private extension URLRequest {
    func httpBodyStreamData() -> Data {
        if let httpBody {
            return httpBody
        }
        guard let stream = httpBodyStream else {
            return Data()
        }

        stream.open()
        defer { stream.close() }

        var data = Data()
        let bufferSize = 1_024
        let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: bufferSize)
        defer { buffer.deallocate() }

        while stream.hasBytesAvailable {
            let count = stream.read(buffer, maxLength: bufferSize)
            if count <= 0 {
                break
            }
            data.append(buffer, count: count)
        }
        return data
    }
}
