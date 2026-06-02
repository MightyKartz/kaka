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

        private enum CodingKeys: String, CodingKey {
            case photoEdit = "photo_edit"
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
