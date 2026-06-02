import AgentPocketCore
import Foundation

public protocol ResultAssetDownloading: Sendable {
    func download(downloadURL: String, connection: StoredConnection) async throws -> DownloadedAsset
}

public struct MobileBridgeResultAssetDownloader: ResultAssetDownloading {
    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    public func download(downloadURL: String, connection: StoredConnection) async throws -> DownloadedAsset {
        try await MobileBridgeHTTPClient(
            endpoint: connection.endpoint,
            token: connection.mobileToken,
            session: session
        ).downloadAsset(downloadURL: downloadURL)
    }
}
