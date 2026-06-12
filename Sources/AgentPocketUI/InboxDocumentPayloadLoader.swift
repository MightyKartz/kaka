import AgentPocketCore
import Foundation

public protocol InboxDocumentPayloadLoading: Sendable {
    func preparedUpload(for item: KakaInboxItem) throws -> PreparedAssetUpload
}

public struct FileInboxDocumentPayloadLoader: InboxDocumentPayloadLoading {
    public enum LoadError: Error, Equatable {
        case unsupportedKind
        case missingRelativePath
        case unsafeRelativePath
        case unsupportedMimeType
        case exceedsMaxUploadSize
    }

    private let containerURL: URL
    private let maxUploadMB: Int

    public init(containerURL: URL, maxUploadMB: Int = 25) {
        self.containerURL = containerURL
        self.maxUploadMB = maxUploadMB
    }

    public init(
        appGroupIdentifier: String = FileKakaInboxStore.defaultAppGroupIdentifier,
        maxUploadMB: Int = 25,
        fileManager: FileManager = .default
    ) {
        let directoryURL = fileManager.containerURL(forSecurityApplicationGroupIdentifier: appGroupIdentifier)
            ?? fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask)
                .first!
                .appendingPathComponent(appGroupIdentifier, isDirectory: true)
        self.init(containerURL: directoryURL, maxUploadMB: maxUploadMB)
    }

    public func preparedUpload(for item: KakaInboxItem) throws -> PreparedAssetUpload {
        guard item.kind == .pdf else {
            throw LoadError.unsupportedKind
        }
        guard let relativePath = item.relativeFilePath else {
            throw LoadError.missingRelativePath
        }
        let mimeType = item.mimeType ?? "application/pdf"
        guard mimeType.lowercased() == "application/pdf" else {
            throw LoadError.unsupportedMimeType
        }

        let fileURL = try payloadURL(relativePath: relativePath)
        let resourceValues = try fileURL.resourceValues(forKeys: [.fileSizeKey])
        if let fileSize = resourceValues.fileSize,
           fileSize > maxUploadBytes {
            throw LoadError.exceedsMaxUploadSize
        }
        let data = try Data(contentsOf: fileURL)
        guard data.count <= maxUploadBytes else {
            throw LoadError.exceedsMaxUploadSize
        }

        let fileName = item.fileName ?? fileURL.lastPathComponent
        return PreparedAssetUpload(
            data: data,
            mimeType: mimeType,
            fileName: fileName,
            metadata: AssetUploadMetadata(
                source: item.sourceSurface,
                originalFileName: fileName,
                stripSensitiveMetadata: true
            )
        )
    }

    private var maxUploadBytes: Int {
        maxUploadMB * 1_024 * 1_024
    }

    private func payloadURL(relativePath: String) throws -> URL {
        guard relativePath.hasPrefix("/") == false,
              (relativePath as NSString).pathComponents.contains("..") == false else {
            throw LoadError.unsafeRelativePath
        }

        let baseURL = containerURL.standardizedFileURL.resolvingSymlinksInPath()
        let payloadURL = baseURL.appendingPathComponent(relativePath)
            .standardizedFileURL
            .resolvingSymlinksInPath()
        let basePath = baseURL.path.hasSuffix("/") ? baseURL.path : "\(baseURL.path)/"
        guard payloadURL.path.hasPrefix(basePath) else {
            throw LoadError.unsafeRelativePath
        }
        return payloadURL
    }
}
