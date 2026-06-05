import Foundation

public extension JSONDecoder {
    static var mobileBridge: JSONDecoder {
        JSONDecoder()
    }
}

public extension JSONEncoder {
    static var mobileBridge: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return encoder
    }
}

public struct HealthResponse: Decodable, Equatable, Sendable {
    public let ok: Bool
    public let runtime: String
    public let runtimeVersion: String
    public let bridgeVersion: String

    private enum CodingKeys: String, CodingKey {
        case ok
        case runtime
        case runtimeVersion = "runtime_version"
        case bridgeVersion = "bridge_version"
    }
}

public struct CapabilitiesResponse: Decodable, Equatable, Sendable {
    public let profiles: [Profile]
    public let tasks: Tasks
    public let retention: Retention

    public struct Profile: Decodable, Equatable, Sendable {
        public let id: String
        public let displayName: String
        public let capabilities: [String]

        private enum CodingKeys: String, CodingKey {
            case id
            case displayName = "display_name"
            case capabilities
        }
    }

    public struct Tasks: Decodable, Equatable, Sendable {
        public let photoEdit: PhotoEditCapability
        public let vision: VisionCapability?
        public let imageIntake: ImageIntakeCapability?
        public let intake: UniversalIntakeCapability?

        private enum CodingKeys: String, CodingKey {
            case photoEdit = "photo_edit"
            case vision
            case imageIntake = "image_intake"
            case intake
        }
    }

    public struct PhotoEditCapability: Decodable, Equatable, Sendable {
        public let maxUploadMB: Int
        public let acceptedMimeTypes: [String]
        public let styles: [String]
        public let provider: String?
        public let renderer: String?
        public let variantLabels: [String]
        public let variantIDs: [String]
        public let cropAspects: [String]
        public let supportsCropCandidates: Bool
        public let supportsUpscalePolicy: Bool
        public let supportsSSE: Bool
        public let returnVariantsMax: Int

        private enum CodingKeys: String, CodingKey {
            case maxUploadMB = "max_upload_mb"
            case acceptedMimeTypes = "accepted_mime_types"
            case styles
            case provider
            case renderer
            case variantLabels = "variant_labels"
            case variantIDs = "variant_ids"
            case cropAspects = "crop_aspects"
            case supportsCropCandidates = "supports_crop_candidates"
            case supportsUpscalePolicy = "supports_upscale_policy"
            case supportsSSE = "supports_sse"
            case returnVariantsMax = "return_variants_max"
        }

        public init(from decoder: Decoder) throws {
            let container = try decoder.container(keyedBy: CodingKeys.self)
            maxUploadMB = try container.decode(Int.self, forKey: .maxUploadMB)
            acceptedMimeTypes = try container.decode([String].self, forKey: .acceptedMimeTypes)
            styles = try container.decode([String].self, forKey: .styles)
            provider = try container.decodeIfPresent(String.self, forKey: .provider)
            renderer = try container.decodeIfPresent(String.self, forKey: .renderer)
            variantLabels = try container.decodeIfPresent([String].self, forKey: .variantLabels) ?? []
            variantIDs = try container.decodeIfPresent([String].self, forKey: .variantIDs) ?? []
            cropAspects = try container.decodeIfPresent([String].self, forKey: .cropAspects) ?? []
            supportsCropCandidates = try container.decodeIfPresent(Bool.self, forKey: .supportsCropCandidates) ?? false
            supportsUpscalePolicy = try container.decodeIfPresent(Bool.self, forKey: .supportsUpscalePolicy) ?? false
            supportsSSE = try container.decode(Bool.self, forKey: .supportsSSE)
            returnVariantsMax = try container.decode(Int.self, forKey: .returnVariantsMax)
        }
    }

    public struct VisionCapability: Decodable, Equatable, Sendable {
        public let maxUploadMB: Int
        public let acceptedMimeTypes: [String]
        public let modes: [String]
        public let provider: String?
        public let supportsSSE: Bool

        private enum CodingKeys: String, CodingKey {
            case maxUploadMB = "max_upload_mb"
            case acceptedMimeTypes = "accepted_mime_types"
            case modes
            case provider
            case supportsSSE = "supports_sse"
        }
    }

    public struct ImageIntakeCapability: Decodable, Equatable, Sendable {
        public let maxUploadMB: Int
        public let acceptedMimeTypes: [String]
        public let provider: String?
        public let supportsSSE: Bool

        private enum CodingKeys: String, CodingKey {
            case maxUploadMB = "max_upload_mb"
            case acceptedMimeTypes = "accepted_mime_types"
            case provider
            case supportsSSE = "supports_sse"
        }
    }

    public struct UniversalIntakeCapability: Decodable, Equatable, Sendable {
        public let acceptedTypes: [UniversalIntakeKind]
        public let supportsSSE: Bool
        public let supportsContextSnapshot: Bool
        public let supportsVoiceFollowup: Bool
        public let supportsRecallActions: Bool

        public var acceptedKinds: [UniversalIntakeKind] { acceptedTypes }

        private enum CodingKeys: String, CodingKey {
            case acceptedTypes = "accepted_types"
            case acceptedKinds = "accepted_kinds"
            case supportsSSE = "supports_sse"
            case supportsContextSnapshot = "supports_context_snapshot"
            case supportsVoiceFollowup = "supports_voice_followup"
            case supportsRecallActions = "supports_recall_actions"
        }

        public init(from decoder: Decoder) throws {
            let container = try decoder.container(keyedBy: CodingKeys.self)
            acceptedTypes = try container.decodeIfPresent([UniversalIntakeKind].self, forKey: .acceptedTypes)
                ?? container.decodeIfPresent([UniversalIntakeKind].self, forKey: .acceptedKinds)
                ?? []
            supportsSSE = try container.decodeIfPresent(Bool.self, forKey: .supportsSSE) ?? false
            supportsContextSnapshot = try container.decodeIfPresent(Bool.self, forKey: .supportsContextSnapshot) ?? false
            supportsVoiceFollowup = try container.decodeIfPresent(Bool.self, forKey: .supportsVoiceFollowup) ?? false
            supportsRecallActions = try container.decodeIfPresent(Bool.self, forKey: .supportsRecallActions) ?? false
        }
    }

    public struct Retention: Decodable, Equatable, Sendable {
        public let inputAssetsDays: Int
        public let outputAssetsDays: Int
        public let taskHistoryDays: Int

        private enum CodingKeys: String, CodingKey {
            case inputAssetsDays = "input_assets_days"
            case outputAssetsDays = "output_assets_days"
            case taskHistoryDays = "task_history_days"
        }
    }
}

public struct PairingExchangeResponse: Decodable, Equatable, Sendable {
    public let endpointID: String
    public let displayName: String
    public let runtime: String
    public let runtimeVersion: String
    public let mobileToken: String
    public let tokenExpiresAt: String?

    public init(
        endpointID: String,
        displayName: String,
        runtime: String,
        runtimeVersion: String,
        mobileToken: String,
        tokenExpiresAt: String?
    ) {
        self.endpointID = endpointID
        self.displayName = displayName
        self.runtime = runtime
        self.runtimeVersion = runtimeVersion
        self.mobileToken = mobileToken
        self.tokenExpiresAt = tokenExpiresAt
    }

    private enum CodingKeys: String, CodingKey {
        case endpointID = "endpoint_id"
        case displayName = "display_name"
        case runtime
        case runtimeVersion = "runtime_version"
        case mobileToken = "mobile_token"
        case tokenExpiresAt = "token_expires_at"
    }
}

public struct PairingExchangeRequest: Encodable, Equatable, Sendable {
    public let pairingCode: String
    public let deviceName: String
    public let devicePublicID: String

    public init(pairingCode: String, deviceName: String, devicePublicID: String) {
        self.pairingCode = pairingCode
        self.deviceName = deviceName
        self.devicePublicID = devicePublicID
    }

    private enum CodingKeys: String, CodingKey {
        case pairingCode = "pairing_code"
        case deviceName = "device_name"
        case devicePublicID = "device_public_id"
    }
}

public struct BridgeErrorResponse: Decodable, Equatable, Sendable {
    public let error: BridgeError

    public init(error: BridgeError) {
        self.error = error
    }

    public struct BridgeError: Decodable, Equatable, Sendable {
        public let code: String
        public let message: String
        public let recoverable: Bool

        public init(code: String, message: String, recoverable: Bool) {
            self.code = code
            self.message = message
            self.recoverable = recoverable
        }
    }
}

public struct AssetUploadResponse: Decodable, Equatable, Sendable {
    public let assetID: String
    public let mimeType: String
    public let sizeBytes: Int
    public let sha256: String

    private enum CodingKeys: String, CodingKey {
        case assetID = "asset_id"
        case mimeType = "mime_type"
        case sizeBytes = "size_bytes"
        case sha256
    }
}

public struct PhotoEditTaskRequest: Encodable, Equatable, Sendable {
    public let profileID: String
    public let assetID: String
    public let style: String
    public let instruction: String
    public let returnVariants: Int

    public init(
        profileID: String,
        assetID: String,
        intent: EditIntent,
        instruction: String? = nil,
        returnVariants: Int
    ) {
        self.profileID = profileID
        self.assetID = assetID
        self.style = intent.rawValue
        self.instruction = instruction ?? intent.defaultInstruction
        self.returnVariants = min(max(returnVariants, 1), 3)
    }

    private enum CodingKeys: String, CodingKey {
        case profileID = "profile_id"
        case assetID = "asset_id"
        case style
        case instruction
        case returnVariants = "return_variants"
    }
}

public enum VisionTaskKind: String, Codable, CaseIterable, Identifiable, Sendable {
    case scan
    case identify
    case translate
    case food

    public var id: String { rawValue }
}

public struct VisionTaskRequest: Encodable, Equatable, Sendable {
    public let profileID: String
    public let assetID: String
    public let mode: VisionTaskKind
    public let instruction: String
    public let locale: String?

    public init(
        profileID: String,
        assetID: String,
        mode: VisionTaskKind,
        instruction: String? = nil,
        locale: String? = nil
    ) {
        self.profileID = profileID
        self.assetID = assetID
        self.mode = mode
        self.instruction = instruction ?? mode.defaultInstruction
        self.locale = locale
    }

    private enum CodingKeys: String, CodingKey {
        case profileID = "profile_id"
        case assetID = "asset_id"
        case mode
        case instruction
        case locale
    }
}

public struct ImageIntakeTaskRequest: Encodable, Equatable, Sendable {
    public let profileID: String
    public let assetID: String
    public let locale: String?

    public init(profileID: String, assetID: String, locale: String? = nil) {
        self.profileID = profileID
        self.assetID = assetID
        self.locale = locale
    }

    private enum CodingKeys: String, CodingKey {
        case profileID = "profile_id"
        case assetID = "asset_id"
        case locale
    }
}

public extension VisionTaskKind {
    var defaultInstruction: String {
        switch self {
        case .scan:
            return "Extract useful text, codes, and document details from the image. Keep the answer concise."
        case .identify:
            return "Identify the main visible objects, plants, animals, products, or landmarks. Include confidence when useful."
        case .translate:
            return "Read visible text and translate it into the user's locale. Preserve important names and numbers."
        case .food:
            return "Identify visible food and estimate a reasonable calorie range. Mention uncertainty and visible assumptions."
        }
    }
}

public struct VisionTaskCreateResponse: Decodable, Equatable, Sendable {
    public let taskID: String
    public let status: String
    public let eventsURL: String?

    private enum CodingKeys: String, CodingKey {
        case taskID = "task_id"
        case status
        case eventsURL = "events_url"
    }
}

public struct PhotoEditTaskCreateResponse: Decodable, Equatable, Sendable {
    public let taskID: String
    public let status: String
    public let eventsURL: String?

    private enum CodingKeys: String, CodingKey {
        case taskID = "task_id"
        case status
        case eventsURL = "events_url"
    }
}

public struct TaskStatusResponse: Decodable, Equatable, Sendable {
    public let taskID: String
    public let status: String
    public let progress: Double?
    public let message: String?
    public let variants: [Variant]?
    public let explanation: String?
    public let failureCode: String?
    public let renderer: String?
    public let composition: Composition?
    public let qa: QualityAssessment?
    public let recipeSummary: String?
    public let shareCaption: String?
    public let resultType: String?
    public let vision: VisionResult?
    public let imageIntake: ImageIntakeResult?
    public let intake: UniversalIntakeResult?

    private enum CodingKeys: String, CodingKey {
        case taskID = "task_id"
        case status
        case progress
        case message
        case variants
        case explanation
        case failureCode = "failure_code"
        case renderer
        case composition
        case qa
        case recipeSummary = "recipe_summary"
        case shareCaption = "share_caption"
        case resultType = "result_type"
        case vision
        case imageIntake = "image_intake"
        case intake
    }

    public struct Variant: Decodable, Equatable, Sendable {
        public let id: String
        public let label: String
        public let assetID: String
        public let downloadURL: String
        public let recommendedFor: String?

        private enum CodingKeys: String, CodingKey {
            case id
            case label
            case assetID = "asset_id"
            case downloadURL = "download_url"
            case recommendedFor = "recommended_for"
        }
    }

    public struct Composition: Decodable, Equatable, Sendable {
        public let selectedAspectRatio: String?
        public let crop: Crop?

        private enum CodingKeys: String, CodingKey {
            case selectedAspectRatio = "selected_aspect_ratio"
            case crop
        }
    }

    public struct Crop: Decodable, Equatable, Sendable {
        public let x: Double
        public let y: Double
        public let width: Double
        public let height: Double
    }

    public struct QualityAssessment: Decodable, Equatable, Sendable {
        public let masterDifferenceScore: Double?
        public let socialDifferenceScore: Double?

        private enum CodingKeys: String, CodingKey {
            case masterDifferenceScore = "master_difference_score"
            case socialDifferenceScore = "social_difference_score"
        }
    }

    public struct VisionResult: Decodable, Equatable, Sendable {
        public let mode: String
        public let title: String
        public let summary: String
        public let text: String?
        public let language: String?
        public let confidence: Double?
        public let sections: [VisionSection]
        public let items: [VisionItem]

        private enum CodingKeys: String, CodingKey {
            case mode
            case title
            case summary
            case text
            case language
            case confidence
            case sections
            case items
        }

        public init(from decoder: Decoder) throws {
            let container = try decoder.container(keyedBy: CodingKeys.self)
            mode = try container.decode(String.self, forKey: .mode)
            title = try container.decode(String.self, forKey: .title)
            summary = try container.decode(String.self, forKey: .summary)
            text = try container.decodeIfPresent(String.self, forKey: .text)
            language = try container.decodeIfPresent(String.self, forKey: .language)
            confidence = try container.decodeIfPresent(Double.self, forKey: .confidence)
            sections = try container.decodeIfPresent([VisionSection].self, forKey: .sections) ?? []
            items = try container.decodeIfPresent([VisionItem].self, forKey: .items) ?? []
        }
    }

    public struct VisionSection: Decodable, Equatable, Sendable {
        public let title: String
        public let kind: String?
        public let items: [VisionItem]

        private enum CodingKeys: String, CodingKey {
            case title
            case kind
            case items
        }

        public init(from decoder: Decoder) throws {
            let container = try decoder.container(keyedBy: CodingKeys.self)
            title = try container.decode(String.self, forKey: .title)
            kind = try container.decodeIfPresent(String.self, forKey: .kind)
            items = try container.decodeIfPresent([VisionItem].self, forKey: .items) ?? []
        }
    }

    public struct VisionItem: Decodable, Equatable, Sendable {
        public let title: String
        public let value: String?
        public let subtitle: String?
        public let confidence: Double?

        private enum CodingKeys: String, CodingKey {
            case title
            case value
            case subtitle
            case confidence
        }
    }
}

public extension TaskStatusResponse {
    var isTerminal: Bool {
        switch status {
        case "completed", "failed", "cancelled":
            return true
        default:
            return false
        }
    }
}
