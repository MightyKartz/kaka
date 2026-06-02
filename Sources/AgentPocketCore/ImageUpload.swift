import Foundation

public struct ImageUploadPolicy: Equatable, Sendable {
    public enum ValidationError: Error, Equatable {
        case unsupportedMimeType
        case exceedsMaxUploadSize
        case invalidDimensions
    }

    public let maxUploadMB: Int
    public let acceptedMimeTypes: Set<String>

    public init(
        maxUploadMB: Int,
        acceptedMimeTypes: Set<String> = ["image/jpeg", "image/heic", "image/png"]
    ) {
        self.maxUploadMB = maxUploadMB
        self.acceptedMimeTypes = acceptedMimeTypes
    }

    public func prepare(
        data: Data,
        mimeType: String,
        fileName: String,
        width: Int,
        height: Int,
        localCreationTime: String?
    ) throws -> PreparedImageUpload {
        guard acceptedMimeTypes.contains(mimeType) else {
            throw ValidationError.unsupportedMimeType
        }
        guard width > 0, height > 0 else {
            throw ValidationError.invalidDimensions
        }
        guard data.count <= maxUploadBytes else {
            throw ValidationError.exceedsMaxUploadSize
        }

        return PreparedImageUpload(
            data: data,
            mimeType: mimeType,
            fileName: fileName,
            metadata: ImageUploadMetadata(
                width: width,
                height: height,
                localCreationTime: localCreationTime,
                stripSensitiveEXIF: true
            )
        )
    }

    private var maxUploadBytes: Int {
        maxUploadMB * 1_024 * 1_024
    }
}

public struct PreparedImageUpload: Equatable, Sendable {
    public let data: Data
    public let mimeType: String
    public let fileName: String
    public let metadata: ImageUploadMetadata
}

public struct ImageUploadMetadata: Codable, Equatable, Sendable {
    public let width: Int
    public let height: Int
    public let localCreationTime: String?
    public let stripSensitiveEXIF: Bool

    private enum CodingKeys: String, CodingKey {
        case width
        case height
        case localCreationTime = "local_creation_time"
        case stripSensitiveEXIF = "strip_sensitive_exif"
    }
}
