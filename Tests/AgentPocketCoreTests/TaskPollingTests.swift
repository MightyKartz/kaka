import XCTest
@testable import AgentPocketCore

final class TaskPollingTests: XCTestCase {
    func testTaskStatusResponseIdentifiesTerminalStates() throws {
        XCTAssertFalse(try taskStatus(status: "queued").isTerminal)
        XCTAssertFalse(try taskStatus(status: "running").isTerminal)
        XCTAssertTrue(try taskStatus(status: "completed").isTerminal)
        XCTAssertTrue(try taskStatus(status: "failed").isTerminal)
        XCTAssertTrue(try taskStatus(status: "cancelled").isTerminal)
    }

    func testTaskPollerFetchesUntilCompleted() async throws {
        var responses = [
            try taskStatus(status: "queued"),
            try taskStatus(status: "running"),
            try taskStatus(status: "completed")
        ]
        let poller = TaskPoller(intervalNanoseconds: 0)

        let final = try await poller.pollUntilTerminal {
            responses.removeFirst()
        }

        XCTAssertEqual(final.status, "completed")
        XCTAssertTrue(responses.isEmpty)
    }

    func testTaskStatusRequestUsesTaskPathAndBearerToken() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")

        let request = MobileBridgeClient.makeTaskStatusRequest(
            endpoint: endpoint,
            token: "abc123",
            taskID: "task_123"
        )

        XCTAssertEqual(request.httpMethod, "GET")
        XCTAssertEqual(request.url?.absoluteString, "https://hermes.example.com/mobile/v1/tasks/task_123")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
    }

    func testHTTPClientFetchesTaskStatus() async throws {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [TaskStatusMockURLProtocol.self]
        let session = URLSession(configuration: configuration)
        let client = MobileBridgeHTTPClient(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            token: "abc123",
            session: session
        )

        TaskStatusMockURLProtocol.requestHandler = { request in
            XCTAssertEqual(request.url?.path, "/mobile/v1/tasks/task_123")
            let data = """
            {"task_id":"task_123","status":"running","progress":0.45,"message":"Analyzing lighting."}
            """.data(using: .utf8)!
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
        }

        let status = try await client.fetchTaskStatus(taskID: "task_123")

        XCTAssertEqual(status.taskID, "task_123")
        XCTAssertEqual(status.status, "running")
        XCTAssertEqual(status.progress, 0.45)
    }

    override func tearDown() {
        TaskStatusMockURLProtocol.requestHandler = nil
        super.tearDown()
    }

    private func taskStatus(status: String) throws -> TaskStatusResponse {
        let data = """
        {"task_id":"task_123","status":"\(status)","progress":0.5,"message":"Working."}
        """.data(using: .utf8)!
        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }
}

private final class TaskStatusMockURLProtocol: URLProtocol {
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
