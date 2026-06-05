import Foundation

public struct PreparedAssetUpload: Equatable, Sendable {
    public let data: Data
    public let mimeType: String
    public let fileName: String
    public let metadata: AssetUploadMetadata

    public init(
        data: Data,
        mimeType: String,
        fileName: String,
        metadata: AssetUploadMetadata = AssetUploadMetadata()
    ) {
        self.data = data
        self.mimeType = mimeType
        self.fileName = fileName
        self.metadata = metadata
    }
}

public struct AssetUploadMetadata: Codable, Equatable, Sendable {
    public let source: String?
    public let originalFileName: String?
    public let stripSensitiveMetadata: Bool?
    public let width: Int?
    public let height: Int?
    public let localCreationTime: String?
    public let stripSensitiveEXIF: Bool?

    public init(
        source: String? = nil,
        originalFileName: String? = nil,
        stripSensitiveMetadata: Bool? = nil,
        width: Int? = nil,
        height: Int? = nil,
        localCreationTime: String? = nil,
        stripSensitiveEXIF: Bool? = nil
    ) {
        self.source = source
        self.originalFileName = originalFileName
        self.stripSensitiveMetadata = stripSensitiveMetadata
        self.width = width
        self.height = height
        self.localCreationTime = localCreationTime
        self.stripSensitiveEXIF = stripSensitiveEXIF
    }

    private enum CodingKeys: String, CodingKey {
        case source
        case originalFileName = "original_file_name"
        case stripSensitiveMetadata = "strip_sensitive_metadata"
        case width
        case height
        case localCreationTime = "local_creation_time"
        case stripSensitiveEXIF = "strip_sensitive_exif"
    }
}
