import Foundation

public enum RecallAction: String, Codable, Equatable, Sendable {
    case remember
    case useOnce = "use_once"
    case forget
}

public struct RecallActionRequest: Codable, Equatable, Sendable {
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

    private enum CodingKeys: String, CodingKey {
        case action
        case sourceTaskID = "source_task_id"
        case sourceInboxItemID = "source_inbox_item_id"
        case userVisibleSummary = "user_visible_summary"
    }
}

public struct RecallItem: Decodable, Equatable, Sendable {
    public let itemID: String
    public let summary: String
    public let createdAt: String
    public let provenance: Provenance

    public init(
        itemID: String,
        summary: String,
        createdAt: String,
        provenance: Provenance
    ) {
        self.itemID = itemID
        self.summary = summary
        self.createdAt = createdAt
        self.provenance = provenance
    }

    private enum CodingKeys: String, CodingKey {
        case itemID = "item_id"
        case summary
        case createdAt = "created_at"
        case provenance
    }

    public struct Provenance: Decodable, Equatable, Sendable {
        public let sourceTaskID: String?
        public let sourceInboxItemID: UUID?

        public init(sourceTaskID: String? = nil, sourceInboxItemID: UUID? = nil) {
            self.sourceTaskID = sourceTaskID
            self.sourceInboxItemID = sourceInboxItemID
        }

        private enum CodingKeys: String, CodingKey {
            case sourceTaskID = "source_task_id"
            case sourceInboxItemID = "source_inbox_item_id"
        }
    }
}

public struct RecallActionResponse: Decodable, Equatable, Sendable {
    public let action: RecallAction
    public let status: String
    public let item: RecallItem?
    public let deletedItemIDs: [String]

    public init(
        action: RecallAction,
        status: String,
        item: RecallItem? = nil,
        deletedItemIDs: [String] = []
    ) {
        self.action = action
        self.status = status
        self.item = item
        self.deletedItemIDs = deletedItemIDs
    }

    private enum CodingKeys: String, CodingKey {
        case action
        case status
        case item
        case deletedItemIDs = "deleted_item_ids"
    }
}

public struct RecallItemsResponse: Decodable, Equatable, Sendable {
    public let items: [RecallItem]

    public init(items: [RecallItem]) {
        self.items = items
    }
}

public struct RecallDeleteResponse: Decodable, Equatable, Sendable {
    public let status: String
    public let deletedItemIDs: [String]

    public init(status: String, deletedItemIDs: [String]) {
        self.status = status
        self.deletedItemIDs = deletedItemIDs
    }

    private enum CodingKeys: String, CodingKey {
        case status
        case deletedItemIDs = "deleted_item_ids"
    }
}
