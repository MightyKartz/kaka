import AgentPocketCore
import Foundation

public protocol InboxImagePayloadLoading: Sendable {
    func preparedUpload(for item: KakaInboxItem) throws -> PreparedImageUpload
}

public struct FileInboxImagePayloadLoader: InboxImagePayloadLoading {
    public enum LoadError: Error, Equatable {
        case missingRelativePath
        case missingMimeType
    }

    private let containerURL: URL
    private let maxUploadMB: Int
    private let preprocessor: ImagePreprocessor

    public init(
        containerURL: URL,
        maxUploadMB: Int = 30,
        preprocessor: ImagePreprocessor = ImagePreprocessor()
    ) {
        self.containerURL = containerURL
        self.maxUploadMB = maxUploadMB
        self.preprocessor = preprocessor
    }

    public init(
        appGroupIdentifier: String = FileKakaInboxStore.defaultAppGroupIdentifier,
        maxUploadMB: Int = 30,
        fileManager: FileManager = .default,
        preprocessor: ImagePreprocessor = ImagePreprocessor()
    ) {
        let directoryURL = fileManager.containerURL(forSecurityApplicationGroupIdentifier: appGroupIdentifier)
            ?? fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask)
                .first!
                .appendingPathComponent(appGroupIdentifier, isDirectory: true)
        self.init(containerURL: directoryURL, maxUploadMB: maxUploadMB, preprocessor: preprocessor)
    }

    public func preparedUpload(for item: KakaInboxItem) throws -> PreparedImageUpload {
        guard let relativePath = item.relativeFilePath else {
            throw LoadError.missingRelativePath
        }
        guard let mimeType = item.mimeType else {
            throw LoadError.missingMimeType
        }
        let fileURL = containerURL.appendingPathComponent(relativePath)
        let data = try Data(contentsOf: fileURL)
        return try preprocessor.prepareForUpload(
            data: data,
            sourceMimeType: mimeType,
            originalFileName: item.fileName ?? fileURL.lastPathComponent,
            maxUploadMB: maxUploadMB
        )
    }
}
