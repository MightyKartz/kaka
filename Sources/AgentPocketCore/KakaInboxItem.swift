import Foundation

public enum KakaInboxRoute: String, Codable, Equatable, Sendable {
    case universalIntake = "intake"
    case imageIntake = "image_intake"

    public static func defaultRoute(for kind: UniversalIntakeKind) -> KakaInboxRoute {
        switch kind {
        case .image, .screenshot:
            return .imageIntake
        case .text, .url, .pdf:
            return .universalIntake
        }
    }
}

public struct KakaInboxItem: Codable, Equatable, Identifiable, Sendable {
    private static let defaultSourceSurface = "share_extension"

    public let id: UUID
    public let kind: UniversalIntakeKind
    public let receivedAt: Date
    public let sourceApp: String?
    public let sourceSurface: String
    public let note: String?
    public let locale: String?
    public let preferredProfileID: String?
    public let text: String?
    public let url: String?
    public let fileName: String?
    public let mimeType: String?
    public let relativeFilePath: String?
    public let route: KakaInboxRoute

    public var createdAt: Date { receivedAt }

    public init(
        id: UUID = UUID(),
        kind: UniversalIntakeKind,
        receivedAt: Date = Date(),
        sourceApp: String? = nil,
        sourceSurface: String = "share_extension",
        note: String? = nil,
        locale: String? = nil,
        preferredProfileID: String? = nil,
        text: String? = nil,
        url: String? = nil,
        fileName: String? = nil,
        mimeType: String? = nil,
        relativeFilePath: String? = nil,
        route: KakaInboxRoute? = nil
    ) {
        self.id = id
        self.kind = kind
        self.receivedAt = receivedAt
        self.sourceApp = sourceApp
        self.sourceSurface = Self.normalizedSourceSurface(sourceSurface)
        self.note = note
        self.locale = locale
        self.preferredProfileID = preferredProfileID
        self.text = text
        self.url = url
        self.fileName = fileName
        self.mimeType = mimeType
        self.relativeFilePath = relativeFilePath
        self.route = route ?? KakaInboxRoute.defaultRoute(for: kind)
    }

    public init(
        id: UUID = UUID(),
        kind: UniversalIntakeKind,
        createdAt: Date = Date(),
        source: IntakeSource,
        text: String? = nil,
        url: String? = nil,
        fileName: String? = nil,
        mimeType: String? = nil,
        relativeFilePath: String? = nil
    ) {
        self.init(
            id: id,
            kind: kind,
            receivedAt: createdAt,
            sourceApp: source.hostApp,
            sourceSurface: source.surface,
            text: text,
            url: url,
            fileName: fileName,
            mimeType: mimeType,
            relativeFilePath: relativeFilePath
        )
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case kind
        case receivedAt = "received_at"
        case createdAt = "created_at"
        case sourceApp = "source_app"
        case sourceSurface = "source_surface"
        case source
        case note
        case locale
        case preferredProfileID = "preferred_profile_id"
        case text
        case url
        case fileName = "file_name"
        case mimeType = "mime_type"
        case relativeFilePath = "relative_file_path"
        case route
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        kind = try container.decode(UniversalIntakeKind.self, forKey: .kind)

        if let receivedAtString = try container.decodeIfPresent(String.self, forKey: .receivedAt) {
            receivedAt = try MobileBridgeDateCoding.decode(receivedAtString, key: CodingKeys.receivedAt)
        } else if let createdAtString = try container.decodeIfPresent(String.self, forKey: .createdAt) {
            receivedAt = try MobileBridgeDateCoding.decode(createdAtString, key: CodingKeys.createdAt)
        } else {
            receivedAt = Date(timeIntervalSince1970: 0)
        }

        let source = try container.decodeIfPresent(IntakeSource.self, forKey: .source)
        sourceApp = try container.decodeIfPresent(String.self, forKey: .sourceApp) ?? source?.hostApp
        sourceSurface = Self.normalizedSourceSurface(try container.decodeIfPresent(String.self, forKey: .sourceSurface)
            ?? source?.surface
            ?? Self.defaultSourceSurface)
        note = try container.decodeIfPresent(String.self, forKey: .note)
        locale = try container.decodeIfPresent(String.self, forKey: .locale)
        preferredProfileID = try container.decodeIfPresent(String.self, forKey: .preferredProfileID)
        text = try container.decodeIfPresent(String.self, forKey: .text)
        url = try container.decodeIfPresent(String.self, forKey: .url)
        fileName = try container.decodeIfPresent(String.self, forKey: .fileName)
        mimeType = try container.decodeIfPresent(String.self, forKey: .mimeType)
        relativeFilePath = try container.decodeIfPresent(String.self, forKey: .relativeFilePath)
        route = try container.decodeIfPresent(KakaInboxRoute.self, forKey: .route)
            ?? KakaInboxRoute.defaultRoute(for: kind)
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(kind, forKey: .kind)
        try container.encode(MobileBridgeDateCoding.encode(receivedAt), forKey: .receivedAt)
        try container.encodeIfPresent(sourceApp, forKey: .sourceApp)
        try container.encode(sourceSurface, forKey: .sourceSurface)
        try container.encodeIfPresent(note, forKey: .note)
        try container.encodeIfPresent(locale, forKey: .locale)
        try container.encodeIfPresent(preferredProfileID, forKey: .preferredProfileID)
        try container.encodeIfPresent(text, forKey: .text)
        try container.encodeIfPresent(url, forKey: .url)
        try container.encodeIfPresent(fileName, forKey: .fileName)
        try container.encodeIfPresent(mimeType, forKey: .mimeType)
        try container.encodeIfPresent(relativeFilePath, forKey: .relativeFilePath)
        try container.encode(route, forKey: .route)
    }

    private static func normalizedSourceSurface(_ sourceSurface: String) -> String {
        let trimmed = sourceSurface.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? defaultSourceSurface : trimmed
    }
}
