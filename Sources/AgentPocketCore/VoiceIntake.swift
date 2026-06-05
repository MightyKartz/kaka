import Foundation

public struct VoiceFollowUpDraft: Codable, Equatable, Sendable {
    public let transcript: String
    public let sourceTaskID: String?
    public let sourceInboxItemID: UUID?

    public init(
        transcript: String,
        sourceTaskID: String? = nil,
        sourceInboxItemID: UUID? = nil
    ) {
        self.transcript = transcript
        self.sourceTaskID = sourceTaskID
        self.sourceInboxItemID = sourceInboxItemID
    }

    private enum CodingKeys: String, CodingKey {
        case transcript
        case sourceTaskID = "source_task_id"
        case sourceInboxItemID = "source_inbox_item_id"
    }
}
