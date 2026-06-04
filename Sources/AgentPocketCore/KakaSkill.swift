import Foundation

public enum KakaSkillID: String, Codable, CaseIterable, Identifiable, Sendable {
    case photoEnhance = "photo_enhance"
    case ocr
    case translateText = "translate_text"
    case identifySubject = "identify_subject"
    case nutritionEstimate = "nutrition_estimate"

    public var id: String { rawValue }

    public var visionTaskKind: VisionTaskKind? {
        switch self {
        case .photoEnhance:
            nil
        case .ocr:
            .scan
        case .translateText:
            .translate
        case .identifySubject:
            .identify
        case .nutritionEstimate:
            .food
        }
    }
}

public struct KakaSkillSuggestion: Decodable, Equatable, Identifiable, Sendable {
    public let skill: KakaSkillID
    public let title: String
    public let reason: String
    public let confidence: Double?
    public let isAvailable: Bool

    public var id: String { skill.rawValue }

    public init(
        skill: KakaSkillID,
        title: String,
        reason: String,
        confidence: Double?,
        isAvailable: Bool
    ) {
        self.skill = skill
        self.title = title
        self.reason = reason
        self.confidence = confidence
        self.isAvailable = isAvailable
    }

    private enum CodingKeys: String, CodingKey {
        case skill
        case title
        case reason
        case confidence
        case isAvailable = "is_available"
    }
}

public struct ImageIntakeResult: Decodable, Equatable, Sendable {
    public let imageType: String
    public let title: String
    public let summary: String
    public let confidence: Double?
    public let suggestions: [KakaSkillSuggestion]

    private enum CodingKeys: String, CodingKey {
        case imageType = "image_type"
        case title
        case summary
        case confidence
        case suggestions
    }
}
