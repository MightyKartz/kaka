import AgentPocketCore
import Foundation

public protocol ResultAssetDownloading: Sendable {
    func download(downloadURL: String, connection: StoredConnection) async throws -> DownloadedAsset
}

public struct MobileBridgeResultAssetDownloader: ResultAssetDownloading {
    private let session: URLSession?

    public init(session: URLSession? = nil) {
        self.session = session
    }

    public func download(downloadURL: String, connection: StoredConnection) async throws -> DownloadedAsset {
        try await MobileBridgeHTTPClient(
            connection: connection,
            session: session
        ).downloadAsset(downloadURL: downloadURL)
    }
}
