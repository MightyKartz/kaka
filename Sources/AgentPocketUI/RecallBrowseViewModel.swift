import AgentPocketCore
import Foundation

public protocol RecallBrowsing: Sendable {
    func fetchRecallItems(query: String?, limit: Int?, connection: StoredConnection) async throws -> [RecallItem]

    func searchRecall(_ request: RecallSearchRequest, connection: StoredConnection) async throws -> RecallSearchResponse

    func deleteRecallItem(itemID: String, connection: StoredConnection) async throws -> RecallDeleteResponse

    func exportRecallItems(connection: StoredConnection) async throws -> RecallExportResponse
}

public struct MobileBridgeRecallBrowser: RecallBrowsing {
    private let session: URLSession?

    public init(session: URLSession? = nil) {
        self.session = session
    }

    public func fetchRecallItems(query: String?, limit: Int?, connection: StoredConnection) async throws -> [RecallItem] {
        let client = MobileBridgeHTTPClient(
            connection: connection,
            session: session
        )
        return try await client.fetchRecallItems(query: query, limit: limit)
    }

    public func searchRecall(_ request: RecallSearchRequest, connection: StoredConnection) async throws -> RecallSearchResponse {
        let client = MobileBridgeHTTPClient(
            connection: connection,
            session: session
        )
        return try await client.searchRecall(request)
    }

    public func deleteRecallItem(itemID: String, connection: StoredConnection) async throws -> RecallDeleteResponse {
        let client = MobileBridgeHTTPClient(
            connection: connection,
            session: session
        )
        return try await client.deleteRecallItem(itemID: itemID)
    }

    public func exportRecallItems(connection: StoredConnection) async throws -> RecallExportResponse {
        let client = MobileBridgeHTTPClient(
            connection: connection,
            session: session
        )
        return try await client.exportRecallItems()
    }
}

public enum RecallBrowseState: Equatable, Sendable {
    case idle
    case loading
    case loaded
    case deleting
    case exporting
    case exported(RecallExportResponse)
    case failed(message: String)
}

@MainActor
public final class RecallBrowseViewModel: ObservableObject {
    public static let defaultLimit = 25
    public static let missingConnectionMessage = "请先连接本机智能体。"

    @Published public var query: String = ""
    @Published public private(set) var state: RecallBrowseState = .idle
    @Published public private(set) var items: [RecallItem] = []
    @Published public private(set) var lastSearchMatches: [RecallSearchResponse.Result] = []
    @Published public private(set) var lastDeletionIndexIDs: [String] = []
    @Published public private(set) var lastExport: RecallExportResponse?

    private let browser: any RecallBrowsing
    private let limit: Int

    public init(
        browser: any RecallBrowsing = MobileBridgeRecallBrowser(),
        limit: Int = RecallBrowseViewModel.defaultLimit
    ) {
        self.browser = browser
        self.limit = limit
    }

    public func load(connection: StoredConnection?) async {
        await fetch(query: nil, connection: connection)
    }

    public func search(query: String, connection: StoredConnection?) async {
        self.query = query
        await fetch(query: query, connection: connection)
    }

    public func delete(itemID: String, connection: StoredConnection?) async {
        guard let connection else {
            state = .failed(message: Self.missingConnectionMessage)
            return
        }

        state = .deleting
        do {
            let receipt = try await browser.deleteRecallItem(itemID: itemID, connection: connection)
            lastDeletionIndexIDs = receipt.deletedIndexIDs
            items.removeAll { receipt.deletedItemIDs.contains($0.itemID) }
            lastSearchMatches.removeAll { receipt.deletedItemIDs.contains($0.item.itemID) }
            state = .loaded
        } catch {
            state = .failed(message: "Recall 暂时不可用。")
        }
    }

    public func export(connection: StoredConnection?) async {
        guard let connection else {
            state = .failed(message: Self.missingConnectionMessage)
            return
        }

        state = .exporting
        do {
            let response = try await browser.exportRecallItems(connection: connection)
            lastExport = response
            state = .exported(response)
        } catch {
            state = .failed(message: "Recall 暂时不可用。")
        }
    }

    private func fetch(query: String?, connection: StoredConnection?) async {
        guard let connection else {
            state = .failed(message: Self.missingConnectionMessage)
            return
        }

        state = .loading
        do {
            let trimmedQuery = query?.trimmingCharacters(in: .whitespacesAndNewlines)
            let searchQuery = trimmedQuery?.isEmpty == false ? trimmedQuery : nil
            if let searchQuery {
                do {
                    let response = try await browser.searchRecall(
                        RecallSearchRequest(query: searchQuery, limit: limit),
                        connection: connection
                    )
                    lastSearchMatches = response.items
                    items = response.items.map(\.item)
                } catch {
                    lastSearchMatches = []
                    items = try await browser.fetchRecallItems(query: searchQuery, limit: limit, connection: connection)
                }
            } else {
                lastSearchMatches = []
                items = try await browser.fetchRecallItems(query: nil, limit: limit, connection: connection)
            }
            state = .loaded
        } catch {
            state = .failed(message: "Recall 暂时不可用。")
        }
    }
}
