import XCTest
@testable import AgentPocketCore

final class TaskEventsTests: XCTestCase {
    func testParsesProgressAndCompletedSSEEvents() throws {
        let text = """
        event: task.progress
        data: {"progress":0.25,"message":"Analyzing scene."}

        event: task.completed
        data: {"variant_count":3}

        """

        let events = try TaskEventParser.parse(text)

        XCTAssertEqual(
            events,
            [
                .progress(progress: 0.25, message: "Analyzing scene."),
                .completed(variantCount: 3)
            ]
        )
    }

    func testMalformedSSEDataThrowsParseFailureForPollingFallback() {
        let text = """
        event: task.progress
        data: {"progress":

        """

        XCTAssertThrowsError(try TaskEventParser.parse(text)) { error in
            XCTAssertEqual(error as? TaskEventParser.ParseError, .invalidData)
        }
    }

    func testTaskEventsRequestUsesEventStreamAcceptHeader() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")

        let request = MobileBridgeClient.makeTaskEventsRequest(
            endpoint: endpoint,
            token: "abc123",
            eventsURL: "/mobile/v1/tasks/task_123/events"
        )

        XCTAssertEqual(request.httpMethod, "GET")
        XCTAssertEqual(request.url?.absoluteString, "https://hermes.example.com/mobile/v1/tasks/task_123/events")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Accept"), "text/event-stream")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
    }

    func testProgressTransportPrefersSSEOnlyWhenAdvertised() {
        XCTAssertEqual(TaskProgressTransport.preferred(supportsSSE: true), .serverSentEvents)
        XCTAssertEqual(TaskProgressTransport.preferred(supportsSSE: false), .polling)
        XCTAssertEqual(TaskProgressTransport.fallback(after: .parseFailure), .polling)
        XCTAssertEqual(TaskProgressTransport.fallback(after: .disconnected), .polling)
    }

    func testHTTPClientFetchesAndParsesTaskEventsSnapshot() async throws {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [TaskEventsMockURLProtocol.self]
        let client = MobileBridgeHTTPClient(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            token: "abc123",
            session: URLSession(configuration: configuration)
        )

        TaskEventsMockURLProtocol.requestHandler = { request in
            XCTAssertEqual(request.value(forHTTPHeaderField: "Accept"), "text/event-stream")
            let text = """
            event: task.progress
            data: {"progress":0.60,"message":"Generating variants."}

            event: task.completed
            data: {"variant_count":3}

            """
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "text/event-stream"]
            )!
            return (response, Data(text.utf8))
        }

        let events = try await client.fetchTaskEvents(eventsURL: "/mobile/v1/tasks/task_123/events")

        XCTAssertEqual(
            events,
            [
                .progress(progress: 0.60, message: "Generating variants."),
                .completed(variantCount: 3)
            ]
        )
    }

    override func tearDown() {
        TaskEventsMockURLProtocol.requestHandler = nil
        super.tearDown()
    }
}

private final class TaskEventsMockURLProtocol: URLProtocol {
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
