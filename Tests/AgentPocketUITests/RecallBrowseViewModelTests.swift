import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class RecallBrowseViewModelTests: XCTestCase {
    func testLoadUsesDefaultLimitAndNoQuery() async throws {
        let browser = StubRecallBrowser(items: [.fixture(itemID: "recall_0001", summary: "Remember Chinese summaries.")])
        let viewModel = RecallBrowseViewModel(browser: browser)

        await viewModel.load(connection: try storedConnection())

        XCTAssertEqual(browser.fetches, [RecallFetchCall(query: nil, limit: 25)])
        XCTAssertTrue(browser.semanticSearches.isEmpty)
        XCTAssertEqual(viewModel.items.map(\.itemID), ["recall_0001"])
        XCTAssertTrue(viewModel.lastSearchMatches.isEmpty)
        XCTAssertEqual(viewModel.state, .loaded)
    }

    func testSemanticSearchUsesSearchEndpointWhenQueryIsPresent() async throws {
        let semanticResult = RecallSearchResponse.Result(
            item: .fixture(itemID: "recall_semantic_0001", summary: "Answer launch summaries in Chinese."),
            score: 0.91,
            matchReason: "Matched language preference and launch-summary context."
        )
        let browser = StubRecallBrowser(
            semanticResults: RecallSearchResponse(
                query: "launch summary language",
                mode: "semantic",
                items: [semanticResult]
            )
        )
        let viewModel = RecallBrowseViewModel(browser: browser)

        await viewModel.search(query: "  launch summary language  ", connection: try storedConnection())

        XCTAssertEqual(browser.semanticSearches, [RecallSemanticSearchCall(query: "launch summary language", limit: 25)])
        XCTAssertTrue(browser.fetches.isEmpty)
        XCTAssertEqual(viewModel.items.map(\.itemID), ["recall_semantic_0001"])
        XCTAssertEqual(viewModel.lastSearchMatches.first?.matchReason, "Matched language preference and launch-summary context.")
        XCTAssertEqual(viewModel.state, .loaded)
    }

    func testSemanticSearchFallsBackToListSearchWhenUnavailable() async throws {
        let browser = StubRecallBrowser(
            items: [.fixture(itemID: "recall_fallback_0001", summary: "Launch summary language fallback.")],
            semanticError: StubRecallBrowser.Error.unavailable
        )
        let viewModel = RecallBrowseViewModel(browser: browser)

        await viewModel.search(query: "  launch summary language  ", connection: try storedConnection())

        XCTAssertEqual(browser.semanticSearches, [RecallSemanticSearchCall(query: "launch summary language", limit: 25)])
        XCTAssertEqual(browser.fetches, [RecallFetchCall(query: "launch summary language", limit: 25)])
        XCTAssertEqual(viewModel.items.map(\.itemID), ["recall_fallback_0001"])
        XCTAssertTrue(viewModel.lastSearchMatches.isEmpty)
        XCTAssertEqual(viewModel.state, .loaded)
    }

    func testDeleteRecordsIndexReceiptAndRemovesDeletedItems() async throws {
        let browser = StubRecallBrowser(
            items: [
                .fixture(itemID: "recall_0001", summary: "Remember Chinese summaries."),
                .fixture(itemID: "recall_0002", summary: "Keep this recall item.")
            ],
            deletion: RecallDeleteResponse(
                status: "forgotten",
                deletedItemIDs: ["recall_0001"],
                deletedIndexIDs: ["embedding_recall_0001"]
            )
        )
        let viewModel = RecallBrowseViewModel(browser: browser)

        await viewModel.load(connection: try storedConnection())
        await viewModel.delete(itemID: "recall_0001", connection: try storedConnection())

        XCTAssertEqual(browser.deletedItemIDs, ["recall_0001"])
        XCTAssertEqual(viewModel.items.map(\.itemID), ["recall_0002"])
        XCTAssertEqual(viewModel.lastDeletionIndexIDs, ["embedding_recall_0001"])
        XCTAssertEqual(viewModel.state, .loaded)
    }

    func testExportStoresBridgeResponse() async throws {
        let export = RecallExportResponse(
            format: "json",
            generatedAt: "2026-06-05T10:00:00Z",
            items: [.fixture(itemID: "recall_0001", summary: "Remember Chinese summaries.")]
        )
        let browser = StubRecallBrowser(export: export)
        let viewModel = RecallBrowseViewModel(browser: browser)

        await viewModel.export(connection: try storedConnection())

        XCTAssertEqual(browser.exportCount, 1)
        XCTAssertEqual(viewModel.lastExport, export)
        XCTAssertEqual(viewModel.state, .exported(export))
    }

    func testNilConnectionFailsClearlyWithoutCallingBrowser() async {
        let browser = StubRecallBrowser()
        let viewModel = RecallBrowseViewModel(browser: browser)

        await viewModel.search(query: "Chinese", connection: nil)

        XCTAssertEqual(viewModel.state, .failed(message: "请先连接本机智能体。"))
        XCTAssertTrue(browser.fetches.isEmpty)
        XCTAssertTrue(browser.deletedItemIDs.isEmpty)
        XCTAssertEqual(browser.exportCount, 0)
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

private final class StubRecallBrowser: RecallBrowsing, @unchecked Sendable {
    enum Error: Swift.Error {
        case unavailable
    }

    private let items: [RecallItem]
    private let deletion: RecallDeleteResponse
    private let exportResponse: RecallExportResponse
    private let semanticResults: RecallSearchResponse?
    private let semanticError: Swift.Error?
    private(set) var fetches: [RecallFetchCall] = []
    private(set) var semanticSearches: [RecallSemanticSearchCall] = []
    private(set) var deletedItemIDs: [String] = []
    private(set) var exportCount = 0

    init(
        items: [RecallItem] = [],
        deletion: RecallDeleteResponse = RecallDeleteResponse(status: "forgotten", deletedItemIDs: [], deletedIndexIDs: []),
        export: RecallExportResponse = RecallExportResponse(format: "json", generatedAt: "2026-06-05T10:00:00Z", items: []),
        semanticResults: RecallSearchResponse? = nil,
        semanticError: Swift.Error? = nil
    ) {
        self.items = items
        self.deletion = deletion
        self.exportResponse = export
        self.semanticResults = semanticResults
        self.semanticError = semanticError
    }

    func fetchRecallItems(query: String?, limit: Int?, connection: StoredConnection) async throws -> [RecallItem] {
        fetches.append(RecallFetchCall(query: query, limit: limit))
        return items
    }

    func searchRecall(_ request: RecallSearchRequest, connection: StoredConnection) async throws -> RecallSearchResponse {
        semanticSearches.append(RecallSemanticSearchCall(query: request.query, limit: request.limit))
        if let semanticError {
            throw semanticError
        }
        return semanticResults ?? RecallSearchResponse(query: request.query, mode: "semantic", items: [])
    }

    func deleteRecallItem(itemID: String, connection: StoredConnection) async throws -> RecallDeleteResponse {
        deletedItemIDs.append(itemID)
        return deletion
    }

    func exportRecallItems(connection: StoredConnection) async throws -> RecallExportResponse {
        exportCount += 1
        return exportResponse
    }
}

private struct RecallFetchCall: Equatable {
    let query: String?
    let limit: Int?
}

private struct RecallSemanticSearchCall: Equatable {
    let query: String
    let limit: Int
}

private extension RecallItem {
    static func fixture(itemID: String, summary: String) -> RecallItem {
        RecallItem(
            itemID: itemID,
            summary: summary,
            createdAt: "2026-06-05T09:30:00Z",
            provenance: RecallItem.Provenance(sourceTaskID: "task_123", sourceInboxItemID: nil)
        )
    }
}
