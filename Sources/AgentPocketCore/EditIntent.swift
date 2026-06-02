import Foundation

public enum EditIntent: String, CaseIterable, Identifiable, Codable, Equatable, Sendable {
    case naturalEnhance = "natural_enhance"
    case portraitPolish = "portrait_polish"
    case productShot = "product_shot"
    case socialCover = "social_cover"

    public var id: String { rawValue }

    public var displayTitle: String {
        switch self {
        case .naturalEnhance:
            return "Natural Enhance"
        case .portraitPolish:
            return "Portrait Polish"
        case .productShot:
            return "Product Shot"
        case .socialCover:
            return "Social Cover"
        }
    }

    public var sceneTitle: String {
        switch self {
        case .naturalEnhance:
            return "Natural"
        case .portraitPolish:
            return "Portrait"
        case .productShot:
            return "Product"
        case .socialCover:
            return "Social"
        }
    }

    public static var masterShotCompositionBadge: String {
        "4:5 Frame"
    }

    public var summary: String {
        switch self {
        case .naturalEnhance:
            return "Realistic exposure, color, clarity, and composition cleanup."
        case .portraitPolish:
            return "Face-aware lighting and restrained retouching."
        case .productShot:
            return "Cleaner background, sharper subject, commercial lighting."
        case .socialCover:
            return "Dramatic crop, color, and title-safe composition."
        }
    }

    public var defaultInstruction: String {
        switch self {
        case .naturalEnhance:
            return "Keep it realistic. Improve exposure, color, clarity, and composition without making the image look artificial."
        case .portraitPolish:
            return "Polish the portrait with natural skin texture. Do not change identity, face shape, age, or distinctive features."
        case .productShot:
            return "Keep the product accurate. Clean the background, sharpen the subject, and improve commercial lighting without changing product details."
        case .socialCover:
            return "Create a stronger social cover crop with richer color and title-safe composition while preserving the original subject."
        }
    }
}
