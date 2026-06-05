import Foundation
import XCTest
@testable import AgentPocketCore

final class RecallModelsTests: XCTestCase {
    override func tearDown() {
        RecallMockURLProtocol.state.reset()
        super.tearDown()
    }

    func testRecallActionRequestEncodesUseOnceAsSnakeCaseWithVisibleSource() throws {
        let inboxItemID = UUID(uuidString: "12345678-1234-1234-1234-1234567890AB")!
        let request = RecallActionRequest(
            action: .useOnce,
            sourceTaskID: "task_123",
            sourceInboxItemID: inboxItemID,
            userVisibleSummary: "Use this preference only for the current answer."
        )

        let body = String(data: try JSONEncoder.mobileBridge.encode(request), encoding: .utf8) ?? ""

        XCTAssertTrue(body.contains("\"action\":\"use_once\""))
        XCTAssertTrue(body.contains("\"source_task_id\":\"task_123\""))
        XCTAssertTrue(body.contains("\"source_inbox_item_id\":\"12345678-1234-1234-1234-1234567890AB\""))
        XCTAssertTrue(body.contains("\"user_visible_summary\":\"Use this preference only for the current answer.\""))
    }

    func testRecallItemDecodesSummaryProvenanceAndCreatedAt() throws {
        let data = """
        {
          "item_id": "recall_0001",
          "summary": "Kaka should answer launch notes in Chinese.",
          "created_at": "2026-06-05T09:30:00Z",
          "provenance": {
            "source_task_id": "task_123",
            "source_inbox_item_id": "12345678-1234-1234-1234-1234567890AB"
          }
        }
        """.data(using: .utf8)!

        let item = try JSONDecoder.mobileBridge.decode(RecallItem.self, from: data)

        XCTAssertEqual(item.itemID, "recall_0001")
        XCTAssertEqual(item.summary, "Kaka should answer launch notes in Chinese.")
        XCTAssertEqual(item.createdAt, "2026-06-05T09:30:00Z")
        XCTAssertEqual(item.provenance.sourceTaskID, "task_123")
        XCTAssertEqual(item.provenance.sourceInboxItemID?.uuidString, "12345678-1234-1234-1234-1234567890AB")
    }

    func testBuildsRecallActionRequestWithBearerTokenAndJSONBody() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")
        let action = RecallActionRequest(
            action: .remember,
            sourceTaskID: "task_123",
            userVisibleSummary: "Remember my preferred summary language."
        )

        let request = try MobileBridgeClient.makeRecallActionRequest(
            endpoint: endpoint,
            token: "abc123",
            action: action
        )
        let body = String(data: request.httpBody ?? Data(), encoding: .utf8) ?? ""

        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url?.absoluteString, "https://hermes.example.com/mobile/v1/recall/actions")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
        XCTAssertTrue(body.contains("\"action\":\"remember\""))
        XCTAssertTrue(body.contains("\"source_task_id\":\"task_123\""))
    }

    func testHTTPClientSubmitsRecallActionAndDecodesResponse() async throws {
        let client = try makeClient()
        let action = RecallActionRequest(
            action: .remember,
            sourceTaskID: "task_123",
            userVisibleSummary: "Remember my preferred summary language."
        )

        RecallMockURLProtocol.state.setRequestHandler { request in
            let body = String(data: request.httpBodyStreamData(), encoding: .utf8) ?? ""
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.path, "/mobile/v1/recall/actions")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
            XCTAssertTrue(body.contains("\"action\":\"remember\""))
            XCTAssertTrue(body.contains("\"source_task_id\":\"task_123\""))

            let data = """
            {
              "action": "remember",
              "status": "remembered",
              "item": {
                "item_id": "recall_0001",
                "summary": "Remember my preferred summary language.",
                "created_at": "2026-06-05T09:30:00Z",
                "provenance": {"source_task_id": "task_123"}
              },
              "deleted_item_ids": []
            }
            """.data(using: .utf8)!
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
        }

        let response = try await client.submitRecallAction(action)

        XCTAssertEqual(response.action, .remember)
        XCTAssertEqual(response.status, "remembered")
        XCTAssertEqual(response.item?.itemID, "recall_0001")
        XCTAssertEqual(response.item?.provenance.sourceTaskID, "task_123")
        XCTAssertEqual(response.deletedItemIDs, [])
    }

    func testHTTPClientFetchesAndDeletesRecallItems() async throws {
        let client = try makeClient()
        let seenPaths = LockedValue<[String]>([])

        RecallMockURLProtocol.state.setRequestHandler { request in
            seenPaths.update { $0.append(request.url?.path ?? "") }
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
            if request.httpMethod == "GET" {
                let data = """
                {"items":[{"item_id":"recall_0001","summary":"Remember Chinese summaries.","created_at":"2026-06-05T09:30:00Z","provenance":{"source_task_id":"task_123"}}]}
                """.data(using: .utf8)!
                return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
            }
            XCTAssertEqual(request.httpMethod, "DELETE")
            let data = """
            {"status":"forgotten","deleted_item_ids":["recall_0001"]}
            """.data(using: .utf8)!
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
        }

        let items = try await client.fetchRecallItems()
        let deletion = try await client.deleteRecallItem(itemID: "recall_0001")

        XCTAssertEqual(items.map(\.itemID), ["recall_0001"])
        XCTAssertEqual(deletion.deletedItemIDs, ["recall_0001"])
        XCTAssertEqual(seenPaths.value, ["/mobile/v1/recall/items", "/mobile/v1/recall/items/recall_0001"])
    }

    func testDeleteRecallItemRequestEncodesPathSegment() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")

        let request = MobileBridgeClient.makeDeleteRecallItemRequest(
            endpoint: endpoint,
            token: "abc123",
            itemID: "recall 100%/unsafe"
        )

        XCTAssertTrue(
            request.url?.absoluteString.hasSuffix("/mobile/v1/recall/items/recall%20100%25%2Funsafe") == true
        )
    }

    private func makeClient() throws -> MobileBridgeHTTPClient {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [RecallMockURLProtocol.self]
        let session = URLSession(configuration: configuration)
        return MobileBridgeHTTPClient(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            token: "abc123",
            session: session
        )
    }
}

private final class RecallMockURLProtocol: URLProtocol {
    static let state = RecallMockURLProtocolState()

    override class func canInit(with request: URLRequest) -> Bool {
        true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
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

private final class RecallMockURLProtocolState: @unchecked Sendable {
    private let lock = NSLock()
    private var handler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    func reset() {
        lock.withCriticalSection {
            handler = nil
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
}

private final class LockedValue<Value>: @unchecked Sendable {
    private let lock = NSLock()
    private var storage: Value

    init(_ value: Value) {
        self.storage = value
    }

    var value: Value {
        lock.withCriticalSection {
            storage
        }
    }

    func update(_ body: (inout Value) -> Void) {
        lock.withCriticalSection {
            body(&storage)
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
        guard let httpBodyStream else {
            return Data()
        }
        httpBodyStream.open()
        defer {
            httpBodyStream.close()
        }
        let bufferSize = 1024
        var data = Data()
        let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: bufferSize)
        defer {
            buffer.deallocate()
        }
        while httpBodyStream.hasBytesAvailable {
            let read = httpBodyStream.read(buffer, maxLength: bufferSize)
            if read <= 0 {
                break
            }
            data.append(buffer, count: read)
        }
        return data
    }
}
