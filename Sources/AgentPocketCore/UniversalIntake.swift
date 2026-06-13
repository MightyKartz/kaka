import Foundation

public enum UniversalIntakeKind: String, Codable, CaseIterable, Sendable {
    case text
    case url
    case image
    case screenshot
    case pdf
    case video
}

public struct IntakeSource: Codable, Equatable, Sendable {
    public let surface: String
    public let hostApp: String?

    public init(surface: String, hostApp: String? = nil) {
        self.surface = surface
        self.hostApp = hostApp
    }

    private enum CodingKeys: String, CodingKey {
        case surface
        case hostApp = "host_app"
    }
}

public struct UniversalIntakeTaskRequest: Codable, Equatable, Sendable {
    public let kind: UniversalIntakeKind
    public let assetID: String?
    public let text: String?
    public let url: String?
    public let note: String?
    public let locale: String?
    public let preferredProfileID: String?
    public let sourceApp: String?
    public let receivedAt: Date?
    public let source: IntakeSource?
    public let contextSnapshot: ContextSnapshotPayload?
    public let userInstruction: String?

    public init(
        kind: UniversalIntakeKind,
        assetID: String? = nil,
        text: String? = nil,
        url: String? = nil,
        note: String? = nil,
        locale: String? = nil,
        preferredProfileID: String? = nil,
        sourceApp: String? = nil,
        receivedAt: Date? = nil,
        source: IntakeSource? = nil,
        contextSnapshot: ContextSnapshotPayload? = nil,
        userInstruction: String? = nil
    ) {
        self.kind = kind
        self.assetID = assetID
        self.text = text
        self.url = url
        self.note = note
        self.locale = locale
        self.preferredProfileID = preferredProfileID
        self.sourceApp = sourceApp ?? source?.hostApp
        self.receivedAt = receivedAt
        self.source = source
        self.contextSnapshot = contextSnapshot
        self.userInstruction = userInstruction
    }

    public init(
        profileID: String,
        kind: UniversalIntakeKind,
        assetID: String? = nil,
        text: String? = nil,
        url: String? = nil,
        source: IntakeSource,
        contextSnapshot: ContextSnapshotPayload? = nil,
        userInstruction: String? = nil,
        note: String? = nil,
        locale: String? = nil,
        sourceApp: String? = nil,
        receivedAt: Date? = nil
    ) {
        self.init(
            kind: kind,
            assetID: assetID,
            text: text,
            url: url,
            note: note ?? userInstruction,
            locale: locale,
            preferredProfileID: profileID,
            sourceApp: sourceApp ?? source.hostApp,
            receivedAt: receivedAt,
            source: source,
            contextSnapshot: contextSnapshot,
            userInstruction: userInstruction
        )
    }

    private enum CodingKeys: String, CodingKey {
        case kind
        case assetID = "asset_id"
        case text
        case url
        case note
        case locale
        case preferredProfileID = "preferred_profile_id"
        case sourceApp = "source_app"
        case receivedAt = "received_at"
        case source
        case contextSnapshot = "context_snapshot"
        case userInstruction = "user_instruction"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        kind = try container.decode(UniversalIntakeKind.self, forKey: .kind)
        assetID = try container.decodeIfPresent(String.self, forKey: .assetID)
        text = try container.decodeIfPresent(String.self, forKey: .text)
        url = try container.decodeIfPresent(String.self, forKey: .url)
        note = try container.decodeIfPresent(String.self, forKey: .note)
        locale = try container.decodeIfPresent(String.self, forKey: .locale)
        preferredProfileID = try container.decodeIfPresent(String.self, forKey: .preferredProfileID)
        source = try container.decodeIfPresent(IntakeSource.self, forKey: .source)
        sourceApp = try container.decodeIfPresent(String.self, forKey: .sourceApp) ?? source?.hostApp
        contextSnapshot = try container.decodeIfPresent(ContextSnapshotPayload.self, forKey: .contextSnapshot)
        userInstruction = try container.decodeIfPresent(String.self, forKey: .userInstruction)

        if let receivedAtString = try container.decodeIfPresent(String.self, forKey: .receivedAt) {
            receivedAt = try MobileBridgeDateCoding.decode(receivedAtString, key: CodingKeys.receivedAt)
        } else {
            receivedAt = nil
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(kind, forKey: .kind)
        try container.encodeIfPresent(assetID, forKey: .assetID)
        try container.encodeIfPresent(text, forKey: .text)
        try container.encodeIfPresent(url, forKey: .url)
        try container.encodeIfPresent(note, forKey: .note)
        try container.encodeIfPresent(locale, forKey: .locale)
        try container.encodeIfPresent(preferredProfileID, forKey: .preferredProfileID)
        try container.encodeIfPresent(sourceApp, forKey: .sourceApp)
        if let receivedAt {
            try container.encode(MobileBridgeDateCoding.encode(receivedAt), forKey: .receivedAt)
        }
        try container.encodeIfPresent(source, forKey: .source)
        try container.encodeIfPresent(contextSnapshot, forKey: .contextSnapshot)
        try container.encodeIfPresent(userInstruction, forKey: .userInstruction)
    }
}

public struct UniversalIntakeResult: Codable, Equatable, Sendable {
    public let kind: UniversalIntakeKind
    public let title: String
    public let summary: String
    public let suggestions: [UniversalIntakeSuggestion]

    public init(
        kind: UniversalIntakeKind,
        title: String,
        summary: String,
        suggestions: [UniversalIntakeSuggestion] = []
    ) {
        self.kind = kind
        self.title = title
        self.summary = summary
        self.suggestions = suggestions
    }

    private enum CodingKeys: String, CodingKey {
        case kind
        case title
        case summary
        case suggestions
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        kind = try container.decode(UniversalIntakeKind.self, forKey: .kind)
        title = try container.decode(String.self, forKey: .title)
        summary = try container.decode(String.self, forKey: .summary)
        suggestions = try container.decodeIfPresent([UniversalIntakeSuggestion].self, forKey: .suggestions) ?? []
    }
}

public struct UniversalIntakeSuggestion: Codable, Equatable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let requiresConfirmation: Bool
    public let isAvailable: Bool

    public init(
        id: String,
        label: String,
        requiresConfirmation: Bool,
        isAvailable: Bool
    ) {
        self.id = id
        self.label = label
        self.requiresConfirmation = requiresConfirmation
        self.isAvailable = isAvailable
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case label
        case requiresConfirmation = "requires_confirmation"
        case isAvailable = "is_available"
    }
}

enum MobileBridgeDateCoding {
    static func encode(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.string(from: date)
    }

    static func decode<Key: CodingKey>(_ value: String, key: Key) throws -> Date {
        for options in [
            ISO8601DateFormatter.Options.withInternetDateTime,
            [.withInternetDateTime, .withFractionalSeconds]
        ] {
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = options
            if let date = formatter.date(from: value) {
                return date
            }
        }

        throw DecodingError.dataCorrupted(
            .init(codingPath: [key], debugDescription: "Expected ISO-8601 date string.")
        )
    }
}
