import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class PhotoEditSubmitterTests: XCTestCase {
    func testSubmitUsesSSEWhenAdvertisedBeforeFetchingFinalStatus() async throws {
        SubmitterMockURLProtocol.reset()
        let submitter = MobileBridgePhotoEditSubmitter(
            session: URLSession(configuration: mockSessionConfiguration()),
            poller: TaskPoller(intervalNanoseconds: 0)
        )
        let progress = ProgressRecorder()
        SubmitterMockURLProtocol.requestHandler = responseWithValidEvents

        let status = try await submitter.submit(
            upload: upload(),
            intent: .naturalEnhance,
            connection: try storedConnection()
        ) { event in
            await progress.append(event)
        }

        XCTAssertEqual(status.status, "completed")
        XCTAssertEqual(
            SubmitterMockURLProtocol.requestPaths,
            [
                "/mobile/v1/capabilities",
                "/mobile/v1/assets",
                "/mobile/v1/tasks/photo-edit",
                "/mobile/v1/tasks/task_123/events",
                "/mobile/v1/tasks/task_123",
            ]
        )
        let recordedEvents = await progress.recordedEvents()
        XCTAssertEqual(
            recordedEvents,
            [
                .uploading,
                .startingTask,
                .submitted(taskID: "task_123"),
                .running(taskID: "task_123", progress: 0.6, message: "Generating variants."),
            ]
        )
    }

    func testSubmitFallsBackToPollingWhenSSEEventsCannotBeParsed() async throws {
        SubmitterMockURLProtocol.reset()
        let submitter = MobileBridgePhotoEditSubmitter(
            session: URLSession(configuration: mockSessionConfiguration()),
            poller: TaskPoller(intervalNanoseconds: 0)
        )
        let progress = ProgressRecorder()
        SubmitterMockURLProtocol.requestHandler = responseWithMalformedEvents

        let status = try await submitter.submit(
            upload: upload(),
            intent: .portraitPolish,
            connection: try storedConnection()
        ) { event in
            await progress.append(event)
        }

        XCTAssertEqual(status.status, "completed")
        XCTAssertEqual(
            SubmitterMockURLProtocol.requestPaths,
            [
                "/mobile/v1/capabilities",
                "/mobile/v1/assets",
                "/mobile/v1/tasks/photo-edit",
                "/mobile/v1/tasks/task_123/events",
                "/mobile/v1/tasks/task_123",
            ]
        )
        let recordedEvents = await progress.recordedEvents()
        XCTAssertEqual(
            recordedEvents,
            [
                .uploading,
                .startingTask,
                .submitted(taskID: "task_123"),
            ]
        )
    }

    override func tearDown() {
        SubmitterMockURLProtocol.reset()
        super.tearDown()
    }

    private func responseWithValidEvents(_ request: URLRequest) throws -> (HTTPURLResponse, Data) {
        try response(for: request) {
            """
            event: task.progress
            data: {"progress":0.60,"message":"Generating variants."}

            event: task.completed
            data: {"variant_count":1}

            """
        }
    }

    private func responseWithMalformedEvents(_ request: URLRequest) throws -> (HTTPURLResponse, Data) {
        try response(for: request) {
            """
            event: task.progress
            data: {"progress":

            """
        }
    }

    private func response(
        for request: URLRequest,
        eventsBody: () -> String
    ) throws -> (HTTPURLResponse, Data) {
        let body: String
        let contentType: String
        switch request.url?.path {
        case "/mobile/v1/capabilities":
            body = """
            {"profiles":[{"id":"photo-agent","display_name":"Photo Agent","capabilities":["photo_edit"]}],"tasks":{"photo_edit":{"max_upload_mb":30,"accepted_mime_types":["image/jpeg"],"styles":["natural_enhance","portrait_polish"],"supports_sse":true,"return_variants_max":2}},"retention":{"input_assets_days":7,"output_assets_days":30,"task_history_days":30}}
            """
            contentType = "application/json"
        case "/mobile/v1/assets":
            body = """
            {"asset_id":"asset_123","mime_type":"image/jpeg","size_bytes":10,"sha256":"abc"}
            """
            contentType = "application/json"
        case "/mobile/v1/tasks/photo-edit":
            body = """
            {"task_id":"task_123","status":"queued","events_url":"/mobile/v1/tasks/task_123/events"}
            """
            contentType = "application/json"
        case "/mobile/v1/tasks/task_123/events":
            body = eventsBody()
            contentType = "text/event-stream"
        case "/mobile/v1/tasks/task_123":
            body = """
            {"task_id":"task_123","status":"completed","progress":1.0,"message":"Done.","variants":[{"id":"variant_1","label":"Natural","asset_id":"asset_result_1","download_url":"/mobile/v1/assets/asset_result_1/download"}],"explanation":"Balanced exposure."}
            """
            contentType = "application/json"
        default:
            throw URLError(.badURL)
        }
        return (
            HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": contentType]
            )!,
            Data(body.utf8)
        )
    }

    private func mockSessionConfiguration() -> URLSessionConfiguration {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [SubmitterMockURLProtocol.self]
        return configuration
    }

    private func upload() -> PreparedImageUpload {
        PreparedImageUpload(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "photo.jpg",
            metadata: ImageUploadMetadata(
                width: 100,
                height: 80,
                localCreationTime: nil,
                stripSensitiveEXIF: true
            )
        )
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

private actor ProgressRecorder {
    private(set) var events: [PhotoEditSubmissionProgress] = []

    func append(_ event: PhotoEditSubmissionProgress) {
        events.append(event)
    }

    func recordedEvents() -> [PhotoEditSubmissionProgress] {
        events
    }
}

private final class SubmitterMockURLProtocol: URLProtocol {
    nonisolated(unsafe) static var requestHandler: ((URLRequest) throws -> (HTTPURLResponse, Data))?
    nonisolated(unsafe) static var requestPaths: [String] = []

    static func reset() {
        requestHandler = nil
        requestPaths = []
    }

    override class func canInit(with request: URLRequest) -> Bool {
        true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        Self.requestPaths.append(request.url?.path ?? "")
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
