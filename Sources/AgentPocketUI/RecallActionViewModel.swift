import AgentPocketCore
import Foundation
import SwiftUI

public protocol RecallActionPerforming: Sendable {
    func submitRecallAction(
        _ request: RecallActionRequest,
        connection: StoredConnection
    ) async throws -> RecallActionResponse

    func fetchRecallItems(connection: StoredConnection) async throws -> [RecallItem]

    func deleteRecallItem(itemID: String, connection: StoredConnection) async throws -> RecallDeleteResponse
}

public struct MobileBridgeRecallActionSubmitter: RecallActionPerforming {
    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    public func submitRecallAction(
        _ request: RecallActionRequest,
        connection: StoredConnection
    ) async throws -> RecallActionResponse {
        let client = MobileBridgeHTTPClient(
            endpoint: connection.endpoint,
            token: connection.mobileToken,
            session: session
        )
        return try await client.submitRecallAction(request)
    }

    public func fetchRecallItems(connection: StoredConnection) async throws -> [RecallItem] {
        let client = MobileBridgeHTTPClient(
            endpoint: connection.endpoint,
            token: connection.mobileToken,
            session: session
        )
        return try await client.fetchRecallItems()
    }

    public func deleteRecallItem(itemID: String, connection: StoredConnection) async throws -> RecallDeleteResponse {
        let client = MobileBridgeHTTPClient(
            endpoint: connection.endpoint,
            token: connection.mobileToken,
            session: session
        )
        return try await client.deleteRecallItem(itemID: itemID)
    }
}

public struct RecallActionConfirmation: Equatable, Sendable {
    public let action: RecallAction
    public let sourceTaskID: String?
    public let sourceInboxItemID: UUID?
    public let userVisibleSummary: String

    public init(
        action: RecallAction,
        sourceTaskID: String? = nil,
        sourceInboxItemID: UUID? = nil,
        userVisibleSummary: String
    ) {
        self.action = action
        self.sourceTaskID = sourceTaskID
        self.sourceInboxItemID = sourceInboxItemID
        self.userVisibleSummary = userVisibleSummary
    }
}

public enum RecallActionViewState: Equatable, Sendable {
    case idle
    case confirming(RecallActionConfirmation)
    case submitting
    case succeeded(RecallActionResponse)
    case failed(message: String)
}

@MainActor
public final class RecallActionViewModel: ObservableObject {
    @Published public private(set) var state: RecallActionViewState = .idle
    @Published public private(set) var items: [RecallItem] = []

    private let performer: any RecallActionPerforming

    public init(performer: any RecallActionPerforming = MobileBridgeRecallActionSubmitter()) {
        self.performer = performer
    }

    public func perform(
        _ action: RecallAction,
        sourceTaskID: String? = nil,
        sourceInboxItemID: UUID? = nil,
        userVisibleSummary: String,
        connection: StoredConnection?
    ) async {
        let trimmedSummary = userVisibleSummary.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmedSummary.isEmpty == false else {
            state = .failed(message: "Add a visible summary before using Recall.")
            return
        }
        guard let connection else {
            state = .failed(message: "请先连接本机智能体。")
            return
        }
        let request = RecallActionRequest(
            action: action,
            sourceTaskID: sourceTaskID,
            sourceInboxItemID: sourceInboxItemID,
            userVisibleSummary: trimmedSummary
        )

        switch action {
        case .remember, .forget:
            state = .confirming(
                RecallActionConfirmation(
                    action: action,
                    sourceTaskID: sourceTaskID,
                    sourceInboxItemID: sourceInboxItemID,
                    userVisibleSummary: trimmedSummary
                )
            )
        case .useOnce:
            await submit(request, connection: connection)
        }
    }

    public func confirmPendingAction(connection: StoredConnection?) async {
        guard case .confirming(let confirmation) = state else {
            return
        }
        let request = RecallActionRequest(
            action: confirmation.action,
            sourceTaskID: confirmation.sourceTaskID,
            sourceInboxItemID: confirmation.sourceInboxItemID,
            userVisibleSummary: confirmation.userVisibleSummary
        )
        await submit(request, connection: connection)
    }

    public func cancelConfirmation() {
        guard case .confirming = state else {
            return
        }
        state = .idle
    }

    public func loadItems(connection: StoredConnection?) async {
        guard let connection else {
            state = .failed(message: "请先连接本机智能体。")
            return
        }

        do {
            items = try await performer.fetchRecallItems(connection: connection)
        } catch {
            state = .failed(message: "Recall 暂时不可用。")
        }
    }

    public func deleteItem(itemID: String, connection: StoredConnection?) async {
        guard let connection else {
            state = .failed(message: "请先连接本机智能体。")
            return
        }

        state = .submitting
        do {
            let response = try await performer.deleteRecallItem(itemID: itemID, connection: connection)
            items.removeAll { response.deletedItemIDs.contains($0.itemID) }
            state = .idle
        } catch {
            state = .failed(message: "Recall 暂时不可用。")
        }
    }

    private func submit(_ request: RecallActionRequest, connection: StoredConnection?) async {
        guard let connection else {
            state = .failed(message: "请先连接本机智能体。")
            return
        }

        state = .submitting
        do {
            let response = try await performer.submitRecallAction(request, connection: connection)
            if let item = response.item {
                items.removeAll { $0.itemID == item.itemID }
                items.insert(item, at: 0)
            }
            if response.deletedItemIDs.isEmpty == false {
                items.removeAll { response.deletedItemIDs.contains($0.itemID) }
            }
            state = .succeeded(response)
        } catch {
            state = .failed(message: "Recall 暂时不可用。")
        }
    }
}
