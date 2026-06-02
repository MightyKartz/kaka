import AgentPocketCore
import Foundation

public enum PhotoSaveResult: Equatable, Sendable {
    case saved
    case permissionDenied
}

public protocol PhotoLibrarySaving: Sendable {
    func save(_ asset: DownloadedAsset) async throws -> PhotoSaveResult
}

#if os(iOS)
import Photos

public struct IOSPhotoLibrarySaver: PhotoLibrarySaving {
    public init() {}

    public func save(_ asset: DownloadedAsset) async throws -> PhotoSaveResult {
        let status = await PHPhotoLibrary.requestAuthorization(for: .addOnly)
        guard status == .authorized || status == .limited else {
            return .permissionDenied
        }

        try await PHPhotoLibrary.shared().performChanges {
            let request = PHAssetCreationRequest.forAsset()
            let options = PHAssetResourceCreationOptions()
            request.addResource(with: resourceType(for: asset.mimeType), data: asset.data, options: options)
        }
        return .saved
    }

    private func resourceType(for mimeType: String) -> PHAssetResourceType {
        switch mimeType {
        case "image/heic", "image/heif":
            return .photo
        default:
            return .photo
        }
    }
}
#endif
