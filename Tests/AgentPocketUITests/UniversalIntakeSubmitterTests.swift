import Foundation
import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

final class UniversalIntakeSubmitterTests: XCTestCase {
    override func tearDown() {
        UniversalIntakeMockURLProtocol.reset()
        super.tearDown()
    }

    func testPDFItemUploadsAssetBeforeStartingUniversalIntake() async throws {
        let upload = PreparedAssetUpload(
            data: Data("%PDF-1.7".utf8),
            mimeType: "application/pdf",
            fileName: "brief.pdf",
            metadata: AssetUploadMetadata(
                source: "share_extension",
                originalFileName: "brief.pdf",
                stripSensitiveMetadata: true
            )
        )
        let submitter = MobileBridgeUniversalIntakeSubmitter(
            session: mockSession(),
            poller: TaskPoller(intervalNanoseconds: 0),
            documentLoader: StubDocumentPayloadLoader(upload: upload)
        )
        let progress = ProgressRecorder()
        UniversalIntakeMockURLProtocol.state.setRequestHandler { request in
            try UniversalIntakeHTTPRecording.response(for: request)
        }

        let status = try await submitter.submit(
            item: KakaInboxItem(
                kind: .pdf,
                sourceApp: "Files",
                fileName: "brief.pdf",
                mimeType: "application/pdf",
                relativeFilePath: "SharedPayloads/brief.pdf"
            ),
            connection: try storedConnection(),
            contextSnapshot: nil,
            progress: { event in await progress.append(event) }
        )

        XCTAssertEqual(
            UniversalIntakeMockURLProtocol.state.snapshot().requestPaths,
            [
                "/mobile/v1/capabilities",
                "/mobile/v1/assets",
                "/mobile/v1/tasks/intake",
                "/mobile/v1/tasks/task_intake_pdf"
            ]
        )
        XCTAssertEqual(status.intake?.kind, .pdf)
        XCTAssertEqual(UniversalIntakeMockURLProtocol.state.snapshot().startedIntakeAssetIDs, ["asset_pdf_123"])
        let recordedEvents = await progress.recordedEvents()
        XCTAssertEqual(recordedEvents, [.uploading, .startingTask, .submitted(taskID: "task_intake_pdf")])
    }

    func testProvidedContextSnapshotIsEncodedWhenRuntimeSupportsContextSnapshot() async throws {
        UniversalIntakeMockURLProtocol.state.update { state in
            state.supportsContextSnapshot = true
            state.expectedContextSnapshot = [
                "timestamp": "2026-06-05T09:30:00Z",
                "timezone": "Asia/Shanghai",
                "locale": "zh-Hans",
                "source_surface": "share_extension",
                "network": "wifi",
                "battery": "charging"
            ]
        }
        let submitter = MobileBridgeUniversalIntakeSubmitter(
            session: mockSession(),
            poller: TaskPoller(intervalNanoseconds: 0)
        )
        let progress = ProgressRecorder()
        UniversalIntakeMockURLProtocol.state.setRequestHandler { request in
            try UniversalIntakeHTTPRecording.response(for: request)
        }

        let status = try await submitter.submit(
            item: KakaInboxItem(
                kind: .text,
                sourceApp: "Notes",
                text: "Remember this."
            ),
            connection: try storedConnection(),
            contextSnapshot: ContextSnapshotPayload(
                timestamp: "2026-06-05T09:30:00Z",
                timezone: "Asia/Shanghai",
                locale: "zh-Hans",
                sourceSurface: "share_extension",
                network: "wifi",
                battery: "charging"
            ),
            progress: { event in await progress.append(event) }
        )

        XCTAssertEqual(
            UniversalIntakeMockURLProtocol.state.snapshot().requestPaths,
            [
                "/mobile/v1/capabilities",
                "/mobile/v1/tasks/intake",
                "/mobile/v1/tasks/task_intake_text"
            ]
        )
        XCTAssertEqual(status.intake?.kind, .text)
        XCTAssertEqual(UniversalIntakeMockURLProtocol.state.snapshot().startedIntakeTexts, ["Remember this."])
        let recordedEvents = await progress.recordedEvents()
        XCTAssertEqual(recordedEvents, [.startingTask, .submitted(taskID: "task_intake_text")])
    }

    func testContextSnapshotIsNotEncodedWhenRuntimeOmitsContextSnapshotSupport() async throws {
        let submitter = MobileBridgeUniversalIntakeSubmitter(
            session: mockSession(),
            poller: TaskPoller(intervalNanoseconds: 0)
        )
        UniversalIntakeMockURLProtocol.state.setRequestHandler { request in
            try UniversalIntakeHTTPRecording.response(for: request)
        }

        _ = try await submitter.submit(
            item: KakaInboxItem(
                kind: .text,
                sourceApp: "Notes",
                text: "Remember this."
            ),
            connection: try storedConnection(),
            contextSnapshot: ContextSnapshotPayload(
                timestamp: "2026-06-05T09:30:00Z",
                timezone: "Asia/Shanghai",
                locale: "zh-Hans",
                sourceSurface: "share_extension"
            ),
            progress: { _ in }
        )

        XCTAssertFalse(UniversalIntakeMockURLProtocol.state.snapshot().contextSnapshotWasPresent)
    }

    func testContextSnapshotIsNotEncodedWhenRuntimeDisablesContextSnapshotSupport() async throws {
        UniversalIntakeMockURLProtocol.state.update { state in
            state.supportsContextSnapshot = false
        }
        let submitter = MobileBridgeUniversalIntakeSubmitter(
            session: mockSession(),
            poller: TaskPoller(intervalNanoseconds: 0)
        )
        UniversalIntakeMockURLProtocol.state.setRequestHandler { request in
            try UniversalIntakeHTTPRecording.response(for: request)
        }

        _ = try await submitter.submit(
            item: KakaInboxItem(
                kind: .text,
                sourceApp: "Notes",
                text: "Remember this."
            ),
            connection: try storedConnection(),
            contextSnapshot: ContextSnapshotPayload(
                timestamp: "2026-06-05T09:30:00Z",
                timezone: "Asia/Shanghai",
                locale: "zh-Hans",
                sourceSurface: "share_extension"
            ),
            progress: { _ in }
        )

        XCTAssertFalse(UniversalIntakeMockURLProtocol.state.snapshot().contextSnapshotWasPresent)
    }

    private func mockSession() -> URLSession {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [UniversalIntakeMockURLProtocol.self]
        return URLSession(configuration: configuration)
    }

    private func storedConnection() throws -> StoredConnection {
        StoredConnection(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            displayName: "Hermes Mac",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "mobile_secret",
            tokenExpiresAt: nil
        )
    }
}

private struct StubDocumentPayloadLoader: InboxDocumentPayloadLoading {
    let upload: PreparedAssetUpload

    func preparedUpload(for item: KakaInboxItem) throws -> PreparedAssetUpload {
        upload
    }
}

private actor ProgressRecorder {
    private(set) var events: [PhotoEditSubmissionProgress] = []

    func append(_ event: PhotoEditSubmissionProgress) {
        events.append(event)
    }

    func recordedEvents() -> [PhotoEditSubmissionProgress] {
        events
    }
}

private enum UniversalIntakeHTTPRecording {
    static func response(for request: URLRequest) throws -> (HTTPURLResponse, Data) {
        let path = request.url?.path ?? ""
        switch (request.httpMethod, path) {
        case ("GET", "/mobile/v1/capabilities"):
            let supportsContextSnapshot = UniversalIntakeMockURLProtocol.state.snapshot().supportsContextSnapshot
            let contextSnapshotCapability = supportsContextSnapshot.map {
                ",\"supports_context_snapshot\":\($0 ? "true" : "false")"
            } ?? ""
            return ok(request, """
            {
              "profiles": [{"id":"photo-agent","display_name":"Photo Agent","capabilities":["photo_edit","intake"]}],
              "tasks": {
                "photo_edit": {"max_upload_mb":30,"accepted_mime_types":["image/jpeg"],"styles":["natural_enhance"],"provider":"recipe_local","renderer":"local_parametric","variant_labels":["Master"],"variant_ids":["variant_clean_pro"],"crop_aspects":["original"],"supports_crop_candidates":false,"supports_upscale_policy":true,"supports_sse":false,"return_variants_max":1},
                "intake": {"accepted_types":["text","url","image","pdf"],"provider":"heuristic_universal_intake","supports_sse":false\(contextSnapshotCapability)}
              },
              "retention": {"input_assets_days":7,"output_assets_days":30,"task_history_days":30}
            }
            """)
        case ("POST", "/mobile/v1/assets"):
            let body = String(data: request.httpBodyStreamData(), encoding: .utf8) ?? ""
            XCTAssertTrue(body.contains("name=\"file\"; filename=\"brief.pdf\""))
            XCTAssertTrue(body.contains("Content-Type: application/pdf"))
            XCTAssertTrue(body.contains("\"source\":\"share_extension\""))
            return ok(request, """
            {"asset_id":"asset_pdf_123","mime_type":"application/pdf","size_bytes":8,"sha256":"def"}
            """)
        case ("POST", "/mobile/v1/tasks/intake"):
            let payload = try JSONSerialization.jsonObject(with: request.httpBodyStreamData()) as? [String: Any]
            UniversalIntakeMockURLProtocol.state.appendStartedIntakeAssetID(payload?["asset_id"] as? String ?? "")
            if let text = payload?["text"] as? String {
                UniversalIntakeMockURLProtocol.state.appendStartedIntakeText(text)
            }
            let kind = payload?["kind"] as? String
            if kind == "pdf" {
                XCTAssertEqual(payload?["source_app"] as? String, "Files")
            } else {
                XCTAssertEqual(kind, "text")
                XCTAssertEqual(payload?["source_app"] as? String, "Notes")
            }
            assertContextSnapshot(payload?["context_snapshot"] as? [String: Any])
            let taskID = "task_intake_\(kind ?? "unknown")"
            return ok(request, """
            {"task_id":"\(taskID)","status":"queued","events_url":"/mobile/v1/tasks/\(taskID)/events"}
            """)
        case ("GET", "/mobile/v1/tasks/task_intake_pdf"):
            return ok(request, """
            {"task_id":"task_intake_pdf","status":"completed","progress":1.0,"result_type":"intake","intake":{"kind":"pdf","title":"PDF ready","summary":"Kaka received a PDF.","suggestions":[]}}
            """)
        case ("GET", "/mobile/v1/tasks/task_intake_text"):
            return ok(request, """
            {"task_id":"task_intake_text","status":"completed","progress":1.0,"result_type":"intake","intake":{"kind":"text","title":"Text ready","summary":"Kaka received text.","suggestions":[]}}
            """)
        default:
            throw URLError(.badServerResponse)
        }
    }

    private static func assertContextSnapshot(_ contextSnapshot: [String: Any]?) {
        if contextSnapshot != nil {
            UniversalIntakeMockURLProtocol.state.markContextSnapshotPresent()
        }
        let expectedContextSnapshot = UniversalIntakeMockURLProtocol.state.snapshot().expectedContextSnapshot
        guard let expectedContextSnapshot else {
            XCTAssertNil(contextSnapshot)
            return
        }

        for (key, value) in expectedContextSnapshot {
            XCTAssertEqual(contextSnapshot?[key] as? String, value)
        }
        XCTAssertNil(contextSnapshot?["motion"])
    }

    private static func ok(_ request: URLRequest, _ body: String) -> (HTTPURLResponse, Data) {
        (
            HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!,
            Data(body.utf8)
        )
    }
}

private final class UniversalIntakeMockURLProtocol: URLProtocol {
    static let state = UniversalIntakeMockState()

    static func reset() {
        state.reset()
    }

    override class func canInit(with request: URLRequest) -> Bool {
        true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        Self.state.appendRequestPath(request.url?.path ?? "")
        guard let requestHandler = Self.state.requestHandler() else {
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

private struct UniversalIntakeMockSnapshot {
    var requestPaths: [String] = []
    var startedIntakeAssetIDs: [String] = []
    var startedIntakeTexts: [String] = []
    var expectedContextSnapshot: [String: String]?
    var supportsContextSnapshot: Bool?
    var contextSnapshotWasPresent = false
}

private final class UniversalIntakeMockState: @unchecked Sendable {
    private let lock = NSLock()
    private var storage = UniversalIntakeMockSnapshot()
    private var handler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    func reset() {
        lock.withCriticalSection {
            storage = UniversalIntakeMockSnapshot()
            handler = nil
        }
    }

    func snapshot() -> UniversalIntakeMockSnapshot {
        lock.withCriticalSection {
            storage
        }
    }

    func update(_ body: (inout UniversalIntakeMockSnapshot) -> Void) {
        lock.withCriticalSection {
            body(&storage)
        }
    }

    func setRequestHandler(_ handler: @escaping (URLRequest) throws -> (HTTPURLResponse, Data)) {
        lock.withCriticalSection {
            self.handler = handler
        }
    }

    func requestHandler() -> ((URLRequest) throws -> (HTTPURLResponse, Data))? {
        lock.withCriticalSection {
            handler
        }
    }

    func appendRequestPath(_ path: String) {
        update {
            $0.requestPaths.append(path)
        }
    }

    func appendStartedIntakeAssetID(_ assetID: String) {
        update {
            $0.startedIntakeAssetIDs.append(assetID)
        }
    }

    func appendStartedIntakeText(_ text: String) {
        update {
            $0.startedIntakeTexts.append(text)
        }
    }

    func markContextSnapshotPresent() {
        update {
            $0.contextSnapshotWasPresent = true
        }
    }
}

private extension NSLock {
    func withCriticalSection<T>(_ body: () throws -> T) rethrows -> T {
        lock()
        defer { unlock() }
        return try body()
    }
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
