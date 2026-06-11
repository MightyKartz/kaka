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

public struct RecallSearchContext: Codable, Equatable, Sendable {
    public let sourceSurface: String?
    public let sourceTaskID: String?
    public let sourceInboxItemID: UUID?

    public init(sourceSurface: String? = nil, sourceTaskID: String? = nil, sourceInboxItemID: UUID? = nil) {
        self.sourceSurface = sourceSurface
        self.sourceTaskID = sourceTaskID
        self.sourceInboxItemID = sourceInboxItemID
    }

    private enum CodingKeys: String, CodingKey {
        case sourceSurface = "source_surface"
        case sourceTaskID = "source_task_id"
        case sourceInboxItemID = "source_inbox_item_id"
    }
}

public struct RecallSearchRequest: Codable, Equatable, Sendable {
    public let query: String
    public let limit: Int
    public let context: RecallSearchContext?

    public init(query: String, limit: Int = 10, context: RecallSearchContext? = nil) {
        self.query = query
        self.limit = limit
        self.context = context
    }
}

public struct RecallSearchResponse: Decodable, Equatable, Sendable {
    public let query: String
    public let mode: String
    public let items: [Result]

    public init(query: String, mode: String, items: [Result]) {
        self.query = query
        self.mode = mode
        self.items = items
    }

    public struct Result: Decodable, Equatable, Sendable {
        public let item: RecallItem
        public let score: Double
        public let matchReason: String

        public init(item: RecallItem, score: Double, matchReason: String) {
            self.item = item
            self.score = score
            self.matchReason = matchReason
        }

        private enum CodingKeys: String, CodingKey {
            case item
            case score
            case matchReason = "match_reason"
        }
    }
}

public struct RecallExportResponse: Decodable, Equatable, Sendable {
    public let format: String
    public let generatedAt: String
    public let items: [RecallItem]

    public init(format: String, generatedAt: String, items: [RecallItem]) {
        self.format = format
        self.generatedAt = generatedAt
        self.items = items
    }

    private enum CodingKeys: String, CodingKey {
        case format
        case generatedAt = "generated_at"
        case items
    }
}

public struct RecallDeleteResponse: Decodable, Equatable, Sendable {
    public let status: String
    public let deletedItemIDs: [String]
    public let deletedIndexIDs: [String]

    public init(status: String, deletedItemIDs: [String], deletedIndexIDs: [String] = []) {
        self.status = status
        self.deletedItemIDs = deletedItemIDs
        self.deletedIndexIDs = deletedIndexIDs
    }

    private enum CodingKeys: String, CodingKey {
        case status
        case deletedItemIDs = "deleted_item_ids"
        case deletedIndexIDs = "deleted_index_ids"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        status = try container.decode(String.self, forKey: .status)
        deletedItemIDs = try container.decode([String].self, forKey: .deletedItemIDs)
        deletedIndexIDs = try container.decodeIfPresent([String].self, forKey: .deletedIndexIDs) ?? []
    }
}
