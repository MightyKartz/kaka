import AgentPocketCore
import Foundation

@MainActor
public final class ResultGalleryViewModel: ObservableObject {
    public enum State: Equatable, Sendable {
        case ready
        case downloading(variantID: String)
        case downloaded(variantID: String)
        case failed(message: String)
    }

    public struct ComparisonPresentation: Equatable, Sendable {
        public let beforeLabel: String
        public let afterLabel: String
        public let afterDetail: String
        public let differenceScore: Double?
        public let isDownloaded: Bool
        public let hasOriginalPreview: Bool
        public let hasEditedPreview: Bool
    }

    public let status: TaskStatusResponse
    public let variants: [TaskStatusResponse.Variant]
    public let explanation: String?
    public let shareCaption: String?
    public let originalPreviewAsset: DownloadedAsset?

    @Published public private(set) var state: State
    @Published public private(set) var selectedVariantID: String?

    private let downloader: any ResultAssetDownloading
    private var downloadedAssets: [String: DownloadedAsset] = [:]

    public init(
        status: TaskStatusResponse,
        downloader: any ResultAssetDownloading = MobileBridgeResultAssetDownloader(),
        initialOriginalAsset: DownloadedAsset? = nil,
        initialDownloadedAssets: [String: DownloadedAsset] = [:]
    ) {
        self.status = status
        self.variants = status.variants ?? []
        self.explanation = status.recipeSummary ?? status.explanation
        self.shareCaption = status.shareCaption
        self.originalPreviewAsset = initialOriginalAsset
        self.downloader = downloader
        self.downloadedAssets = initialDownloadedAssets
        let initiallySelectedVariantID = variants.first?.id
        self.selectedVariantID = initiallySelectedVariantID
        if variants.isEmpty {
            self.state = .failed(message: "No edited variants were returned.")
        } else if let initiallySelectedVariantID, initialDownloadedAssets[initiallySelectedVariantID] != nil {
            self.state = .downloaded(variantID: initiallySelectedVariantID)
        } else {
            self.state = .ready
        }
    }

    public var selectedVariant: TaskStatusResponse.Variant? {
        guard let selectedVariantID else {
            return nil
        }
        return variants.first { $0.id == selectedVariantID }
    }

    public func selectVariant(id: String) {
        guard variants.contains(where: { $0.id == id }) else {
            return
        }
        selectedVariantID = id
        if downloadedAssets[id] == nil {
            state = .ready
        } else {
            state = .downloaded(variantID: id)
        }
    }

    public func markDownloading() {
        guard let selectedVariantID else {
            state = .failed(message: "Select a variant to download.")
            return
        }
        state = .downloading(variantID: selectedVariantID)
    }

    public func markDownloaded(_ asset: DownloadedAsset) {
        guard let selectedVariantID else {
            state = .failed(message: "Select a variant to download.")
            return
        }
        downloadedAssets[selectedVariantID] = asset
        state = .downloaded(variantID: selectedVariantID)
    }

    public func markFailed(_ message: String) {
        state = .failed(message: message)
    }

    public func downloadSelectedVariant(connection: StoredConnection?) async {
        guard let connection else {
            state = .failed(message: "Connect to your local agent before downloading this variant.")
            return
        }
        guard let selectedVariant else {
            state = .failed(message: "Select a variant to download.")
            return
        }

        state = .downloading(variantID: selectedVariant.id)
        do {
            let asset = try await downloader.download(
                downloadURL: selectedVariant.downloadURL,
                connection: connection
            )
            downloadedAssets[selectedVariant.id] = asset
            state = .downloaded(variantID: selectedVariant.id)
        } catch MobileBridgeHTTPClient.ClientError.httpStatus(401, _) {
            state = .failed(message: "The local agent token was rejected. Change runtime and pair again.")
        } catch let error as URLError where error.isLikelyOffline {
            state = .failed(message: "Your local agent is offline. Check the network and try again.")
        } catch {
            state = .failed(message: "Could not download this variant.")
        }
    }

    public func downloadSelectedVariantIfNeeded(connection: StoredConnection?) async {
        guard downloadedAssetForSelectedVariant == nil else {
            return
        }
        guard connection != nil else {
            return
        }
        await downloadSelectedVariant(connection: connection)
    }

    public func selectVariantAndDownloadIfNeeded(id: String, connection: StoredConnection?) async {
        selectVariant(id: id)
        await downloadSelectedVariantIfNeeded(connection: connection)
    }

    public func downloadedAsset(for variantID: String) -> DownloadedAsset? {
        downloadedAssets[variantID]
    }

    public var downloadedAssetForSelectedVariant: DownloadedAsset? {
        guard let selectedVariantID else {
            return nil
        }
        return downloadedAssets[selectedVariantID]
    }

    public var comparisonPresentation: ComparisonPresentation {
        let variant = selectedVariant
        let label = variant?.label ?? "Edited"
        return ComparisonPresentation(
            beforeLabel: "Original",
            afterLabel: label,
            afterDetail: afterDetail(for: variant),
            differenceScore: differenceScore(for: variant),
            isDownloaded: downloadedAssetForSelectedVariant != nil,
            hasOriginalPreview: originalPreviewAsset != nil,
            hasEditedPreview: downloadedAssetForSelectedVariant != nil
        )
    }

    public var shareCaptionForSelectedVariant: String? {
        guard selectedVariant != nil else {
            return nil
        }
        return shareCaption
    }

    private func afterDetail(for variant: TaskStatusResponse.Variant?) -> String {
        guard let variant else {
            return "Select a variant"
        }
        switch variant.recommendedFor {
        case "save":
            return "Save-ready \(variant.label)"
        case "share":
            return "Share-ready \(variant.label)"
        default:
            return "\(variant.label) result"
        }
    }

    private func differenceScore(for variant: TaskStatusResponse.Variant?) -> Double? {
        guard let variant else {
            return nil
        }
        if variant.recommendedFor == "share" || variant.id == "variant_social_pop" {
            return status.qa?.socialDifferenceScore
        }
        if variant.recommendedFor == "save" || variant.id == "variant_clean_pro" {
            return status.qa?.masterDifferenceScore
        }
        return nil
    }
}

private extension URLError {
    var isLikelyOffline: Bool {
        switch code {
        case .cannotConnectToHost, .networkConnectionLost, .notConnectedToInternet, .timedOut:
            return true
        default:
            return false
        }
    }
}
