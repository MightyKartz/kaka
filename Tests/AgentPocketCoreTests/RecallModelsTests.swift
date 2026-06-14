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
          "summary": "Pocket Agent should answer launch notes in Chinese.",
          "created_at": "2026-06-05T09:30:00Z",
          "provenance": {
            "source_task_id": "task_123",
            "source_inbox_item_id": "12345678-1234-1234-1234-1234567890AB"
          }
        }
        """.data(using: .utf8)!

        let item = try JSONDecoder.mobileBridge.decode(RecallItem.self, from: data)

        XCTAssertEqual(item.itemID, "recall_0001")
        XCTAssertEqual(item.summary, "Pocket Agent should answer launch notes in Chinese.")
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
        XCTAssertEqual(deletion.deletedIndexIDs, [])
        XCTAssertEqual(seenPaths.value, ["/mobile/v1/recall/items", "/mobile/v1/recall/items/recall_0001"])
    }

    func testRecallItemsRequestEncodesQueryAndLimit() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")

        let request = MobileBridgeClient.makeRecallItemsRequest(
            endpoint: endpoint,
            token: "abc123",
            query: "Chinese summaries",
            limit: 10
        )
        let components = URLComponents(url: try XCTUnwrap(request.url), resolvingAgainstBaseURL: false)
        let queryItems = Dictionary(
            uniqueKeysWithValues: (components?.queryItems ?? []).map { ($0.name, $0.value ?? "") }
        )

        XCTAssertEqual(request.httpMethod, "GET")
        XCTAssertEqual(request.url?.path, "/mobile/v1/recall/items")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
        XCTAssertEqual(queryItems["query"], "Chinese summaries")
        XCTAssertEqual(queryItems["limit"], "10")
    }

    func testRecallDeleteResponseDecodesIndexDeletionReceipt() throws {
        let data = """
        {
          "status": "forgotten",
          "deleted_item_ids": ["recall_0001"],
          "deleted_index_ids": ["embedding_recall_0001"]
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder.mobileBridge.decode(RecallDeleteResponse.self, from: data)

        XCTAssertEqual(response.status, "forgotten")
        XCTAssertEqual(response.deletedItemIDs, ["recall_0001"])
        XCTAssertEqual(response.deletedIndexIDs, ["embedding_recall_0001"])
    }

    func testSemanticRecallSearchRequestEncodesQueryLimitAndContext() throws {
        let request = RecallSearchRequest(
            query: "launch summary language",
            limit: 8,
            context: RecallSearchContext(sourceSurface: "voice", sourceTaskID: "task_123")
        )

        let body = String(data: try JSONEncoder.mobileBridge.encode(request), encoding: .utf8) ?? ""

        XCTAssertTrue(body.contains("\"query\":\"launch summary language\""))
        XCTAssertTrue(body.contains("\"limit\":8"))
        XCTAssertTrue(body.contains("\"source_surface\":\"voice\""))
        XCTAssertTrue(body.contains("\"source_task_id\":\"task_123\""))
    }

    func testSemanticRecallSearchResponseDecodesScoresAndReasons() throws {
        let data = """
        {
          "query": "launch summary language",
          "mode": "semantic",
          "items": [
            {
              "item": {
                "item_id": "recall_0001",
                "summary": "Answer launch summaries in Chinese.",
                "created_at": "2026-06-05T09:30:00Z",
                "provenance": {"source_task_id": "task_123"}
              },
              "score": 0.91,
              "match_reason": "Matched language preference and launch-summary context."
            }
          ]
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder.mobileBridge.decode(RecallSearchResponse.self, from: data)

        XCTAssertEqual(response.query, "launch summary language")
        XCTAssertEqual(response.mode, "semantic")
        XCTAssertEqual(response.items.first?.item.itemID, "recall_0001")
        XCTAssertEqual(response.items.first?.score, 0.91)
        XCTAssertEqual(response.items.first?.matchReason, "Matched language preference and launch-summary context.")
    }

    func testBuildsSemanticRecallSearchRequestWithBearerTokenAndJSONBody() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")
        let search = RecallSearchRequest(query: "Chinese summaries", limit: 5)

        let request = try MobileBridgeClient.makeRecallSearchRequest(
            endpoint: endpoint,
            token: "abc123",
            search: search
        )
        let body = String(data: request.httpBody ?? Data(), encoding: .utf8) ?? ""

        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url?.absoluteString, "https://hermes.example.com/mobile/v1/recall/search")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
        XCTAssertTrue(body.contains("\"query\":\"Chinese summaries\""))
    }

    func testHTTPClientSearchesSemanticRecallAndDecodesRankedResults() async throws {
        let client = try makeClient()

        RecallMockURLProtocol.state.setRequestHandler { request in
            let body = String(data: request.httpBodyStreamData(), encoding: .utf8) ?? ""
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.path, "/mobile/v1/recall/search")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
            XCTAssertTrue(body.contains("\"query\":\"launch summary language\""))

            let data = """
            {
              "query": "launch summary language",
              "mode": "semantic",
              "items": [
                {
                  "item": {
                    "item_id": "recall_0001",
                    "summary": "Answer launch summaries in Chinese.",
                    "created_at": "2026-06-05T09:30:00Z",
                    "provenance": {"source_task_id": "task_123"}
                  },
                  "score": 0.91,
                  "match_reason": "Matched language preference and launch-summary context."
                }
              ]
            }
            """.data(using: .utf8)!
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
        }

        let response = try await client.searchRecall(
            RecallSearchRequest(query: "launch summary language", limit: 5)
        )

        XCTAssertEqual(response.mode, "semantic")
        XCTAssertEqual(response.items.first?.item.itemID, "recall_0001")
        XCTAssertEqual(response.items.first?.score, 0.91)
    }

    func testHTTPClientSearchesRecallItemsAndExportsRecallJSON() async throws {
        let client = try makeClient()
        let seen = LockedValue<[(method: String, path: String, query: String?)]>([])

        RecallMockURLProtocol.state.setRequestHandler { request in
            seen.update {
                $0.append((request.httpMethod ?? "", request.url?.path ?? "", request.url?.query))
            }
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")

            if request.url?.path == "/mobile/v1/recall/export" {
                let data = """
                {
                  "format": "json",
                  "generated_at": "2026-06-05T10:00:00Z",
                  "items": [
                    {
                      "item_id": "recall_0001",
                      "summary": "Remember Chinese summaries.",
                      "created_at": "2026-06-05T09:30:00Z",
                      "provenance": {"source_task_id": "task_123"}
                    }
                  ]
                }
                """.data(using: .utf8)!
                return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
            }

            let data = """
            {"items":[{"item_id":"recall_0001","summary":"Remember Chinese summaries.","created_at":"2026-06-05T09:30:00Z","provenance":{"source_task_id":"task_123"}}]}
            """.data(using: .utf8)!
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, data)
        }

        let items = try await client.fetchRecallItems(query: "Chinese", limit: 5)
        let export = try await client.exportRecallItems()

        XCTAssertEqual(items.map(\.itemID), ["recall_0001"])
        XCTAssertEqual(export.format, "json")
        XCTAssertEqual(export.generatedAt, "2026-06-05T10:00:00Z")
        XCTAssertEqual(export.items.map(\.itemID), ["recall_0001"])
        XCTAssertEqual(seen.value.map(\.path), ["/mobile/v1/recall/items", "/mobile/v1/recall/export"])
        XCTAssertTrue(seen.value[0].query?.contains("query=Chinese") == true)
        XCTAssertTrue(seen.value[0].query?.contains("limit=5") == true)
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
