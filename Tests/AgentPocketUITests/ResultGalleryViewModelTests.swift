import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class ResultGalleryViewModelTests: XCTestCase {
    func testStartsWithFirstVariantSelected() throws {
        let viewModel = ResultGalleryViewModel(status: try completedStatus())

        XCTAssertEqual(viewModel.selectedVariant?.id, "variant_1")
        XCTAssertEqual(viewModel.state, .ready)
    }

    func testSelectingVariantUpdatesSelection() throws {
        let viewModel = ResultGalleryViewModel(status: try completedStatus())

        viewModel.selectVariant(id: "variant_2")

        XCTAssertEqual(viewModel.selectedVariant?.id, "variant_2")
    }

    func testMarkDownloadedStoresAssetForSelectedVariant() throws {
        let viewModel = ResultGalleryViewModel(status: try completedStatus())
        let asset = DownloadedAsset(data: Data([1, 2, 3]), mimeType: "image/png")

        viewModel.markDownloaded(asset)

        XCTAssertEqual(viewModel.state, .downloaded(variantID: "variant_1"))
        XCTAssertEqual(viewModel.downloadedAsset(for: "variant_1"), asset)
    }

    func testEmptyCompletedStatusFailsClearly() throws {
        let data = """
        {"task_id":"task_123","status":"completed","progress":1.0,"message":"Done.","variants":[]}
        """.data(using: .utf8)!

        let status = try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
        let viewModel = ResultGalleryViewModel(status: status)

        XCTAssertEqual(viewModel.state, .failed(message: "No edited variants were returned."))
    }

    func testDownloadSelectedVariantUsesRuntimeConnectionAndStoresAsset() async throws {
        let asset = DownloadedAsset(data: Data([0x89, 0x50, 0x4E, 0x47]), mimeType: "image/png")
        let downloader = StubResultAssetDownloader(result: asset)
        let viewModel = ResultGalleryViewModel(status: try completedStatus(), downloader: downloader)

        await viewModel.downloadSelectedVariant(connection: try storedConnection())

        XCTAssertEqual(downloader.calls.map(\.downloadURL), ["/mobile/v1/assets/asset_1/download"])
        XCTAssertEqual(downloader.calls.map(\.connection.mobileToken), ["mobile_secret"])
        XCTAssertEqual(viewModel.state, .downloaded(variantID: "variant_1"))
        XCTAssertEqual(viewModel.downloadedAsset(for: "variant_1"), asset)
    }

    func testDownloadSelectedVariantIfNeededDownloadsMissingSelectedVariant() async throws {
        let asset = DownloadedAsset(data: Data([0x89, 0x50, 0x4E, 0x47]), mimeType: "image/png")
        let downloader = StubResultAssetDownloader(result: asset)
        let viewModel = ResultGalleryViewModel(status: try completedLocalRecipeStatus(), downloader: downloader)

        await viewModel.downloadSelectedVariantIfNeeded(connection: try storedConnection())

        XCTAssertEqual(downloader.calls.map(\.downloadURL), ["/mobile/v1/assets/asset_master/download"])
        XCTAssertEqual(viewModel.state, .downloaded(variantID: "variant_clean_pro"))
        XCTAssertEqual(viewModel.downloadedAssetForSelectedVariant, asset)
        XCTAssertTrue(viewModel.comparisonPresentation.hasEditedPreview)
    }

    func testSelectVariantAndDownloadIfNeededDownloadsNewlySelectedMissingVariant() async throws {
        let socialAsset = DownloadedAsset(data: Data([0x89, 0x50, 0x4E, 0x47]), mimeType: "image/png")
        let masterAsset = DownloadedAsset(data: Data([0xFF, 0xD8, 0xFF]), mimeType: "image/jpeg")
        let downloader = StubResultAssetDownloader(result: socialAsset)
        let viewModel = ResultGalleryViewModel(
            status: try completedLocalRecipeStatus(),
            downloader: downloader,
            initialDownloadedAssets: ["variant_clean_pro": masterAsset]
        )

        await viewModel.selectVariantAndDownloadIfNeeded(id: "variant_social_pop", connection: try storedConnection())

        XCTAssertEqual(viewModel.selectedVariant?.id, "variant_social_pop")
        XCTAssertEqual(downloader.calls.map(\.downloadURL), ["/mobile/v1/assets/asset_social/download"])
        XCTAssertEqual(viewModel.state, .downloaded(variantID: "variant_social_pop"))
        XCTAssertEqual(viewModel.downloadedAssetForSelectedVariant, socialAsset)
        XCTAssertEqual(viewModel.comparisonPresentation.afterLabel, "Social")
    }

    func testDownloadSelectedVariantWithoutConnectionFailsClearly() async throws {
        let viewModel = ResultGalleryViewModel(
            status: try completedStatus(),
            downloader: StubResultAssetDownloader(result: DownloadedAsset(data: Data(), mimeType: "image/png"))
        )

        await viewModel.downloadSelectedVariant(connection: nil)

        XCTAssertEqual(viewModel.state, .failed(message: "Connect to your local agent before downloading this variant."))
    }

    func testDownloadSelectedVariantUnauthorizedAsksForRepairing() async throws {
        let viewModel = ResultGalleryViewModel(
            status: try completedStatus(),
            downloader: StubResultAssetDownloader(error: MobileBridgeHTTPClient.ClientError.httpStatus(401, nil))
        )

        await viewModel.downloadSelectedVariant(connection: try storedConnection())

        XCTAssertEqual(viewModel.state, .failed(message: "The local agent token was rejected. Change runtime and pair again."))
    }

    func testDownloadedAssetForSelectedVariantReturnsCachedAsset() throws {
        let viewModel = ResultGalleryViewModel(status: try completedStatus())
        let asset = DownloadedAsset(data: Data([1, 2, 3]), mimeType: "image/png")
        viewModel.markDownloaded(asset)

        XCTAssertEqual(viewModel.downloadedAssetForSelectedVariant, asset)
    }

    func testInitialDownloadedAssetStartsDownloadedForSelectedVariant() throws {
        let asset = DownloadedAsset(data: Data([1, 2, 3]), mimeType: "image/png")
        let viewModel = ResultGalleryViewModel(
            status: try completedStatus(),
            initialDownloadedAssets: ["variant_1": asset]
        )

        XCTAssertEqual(viewModel.state, .downloaded(variantID: "variant_1"))
        XCTAssertEqual(viewModel.downloadedAssetForSelectedVariant, asset)
    }

    func testRecipeSummaryOverridesLegacyExplanationAndShareCaptionIsAvailable() throws {
        let viewModel = ResultGalleryViewModel(status: try completedLocalRecipeStatus())

        XCTAssertEqual(viewModel.explanation, "Balanced exposure and reframed to 4:5.")
        XCTAssertEqual(viewModel.shareCaptionForSelectedVariant, "Shot polished locally with Kaka.")
        XCTAssertEqual(viewModel.selectedVariant?.label, "Master")
    }

    func testComparisonPresentationUsesSelectedVariantRecommendationAndDifferenceScore() throws {
        let viewModel = ResultGalleryViewModel(status: try completedLocalRecipeStatus())

        XCTAssertEqual(viewModel.comparisonPresentation.beforeLabel, "Original")
        XCTAssertEqual(viewModel.comparisonPresentation.afterLabel, "Master")
        XCTAssertEqual(viewModel.comparisonPresentation.afterDetail, "Save-ready Master")
        XCTAssertEqual(viewModel.comparisonPresentation.differenceScore, 0.18)
        XCTAssertFalse(viewModel.comparisonPresentation.isDownloaded)

        viewModel.selectVariant(id: "variant_social_pop")

        XCTAssertEqual(viewModel.comparisonPresentation.afterLabel, "Social")
        XCTAssertEqual(viewModel.comparisonPresentation.afterDetail, "Share-ready Social")
        XCTAssertEqual(viewModel.comparisonPresentation.differenceScore, 0.31)
    }

    func testComparisonPresentationReportsRenderableOriginalAndDownloadedVariant() throws {
        let original = DownloadedAsset(data: Data([0xFF, 0xD8, 0xFF]), mimeType: "image/jpeg")
        let edited = DownloadedAsset(data: Data([0x89, 0x50, 0x4E, 0x47]), mimeType: "image/png")
        let viewModel = ResultGalleryViewModel(
            status: try completedLocalRecipeStatus(),
            initialOriginalAsset: original,
            initialDownloadedAssets: ["variant_clean_pro": edited]
        )

        XCTAssertEqual(viewModel.originalPreviewAsset, original)
        XCTAssertTrue(viewModel.comparisonPresentation.hasOriginalPreview)
        XCTAssertTrue(viewModel.comparisonPresentation.hasEditedPreview)
    }

    func testRecipePresentationTurnsLocalRecipeMetadataIntoMasterShotChips() throws {
        let viewModel = ResultGalleryViewModel(status: try completedLocalRecipeStatus())

        XCTAssertEqual(
            viewModel.recipePresentation?.chips,
            ["4:5 Crop", "Lift Shadows", "Tune Color", "Boost Subject"]
        )
        XCTAssertEqual(
            viewModel.recipePresentation?.note,
            "Keeps real detail while tuning crop, light, and subject depth."
        )
    }

    private func completedStatus() throws -> TaskStatusResponse {
        let data = """
        {"task_id":"task_123","status":"completed","progress":1.0,"message":"Done.","variants":[{"id":"variant_1","label":"Natural","asset_id":"asset_1","download_url":"/mobile/v1/assets/asset_1/download"},{"id":"variant_2","label":"Bright","asset_id":"asset_2","download_url":"/mobile/v1/assets/asset_2/download"}],"explanation":"Balanced exposure."}
        """.data(using: .utf8)!

        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }

    private func completedLocalRecipeStatus() throws -> TaskStatusResponse {
        let data = """
        {
          "task_id": "task_123",
          "status": "completed",
          "progress": 1.0,
          "message": "Done.",
          "variants": [
            {"id":"variant_clean_pro","label":"Master","asset_id":"asset_master","download_url":"/mobile/v1/assets/asset_master/download","recommended_for":"save"},
            {"id":"variant_social_pop","label":"Social","asset_id":"asset_social","download_url":"/mobile/v1/assets/asset_social/download","recommended_for":"share"}
          ],
          "explanation": "Legacy explanation.",
          "renderer": "local_parametric",
          "composition": {
            "selected_aspect_ratio": "4:5",
            "crop": {"x": 0.2, "y": 0.0, "width": 0.6, "height": 1.0}
          },
          "qa": {
            "master_difference_score": 0.18,
            "social_difference_score": 0.31
          },
          "recipe_summary": "Balanced exposure and reframed to 4:5.",
          "share_caption": "Shot polished locally with Kaka."
        }
        """.data(using: .utf8)!

        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }

    private func storedConnection() throws -> StoredConnection {
        StoredConnection(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            displayName: "Hermes Mac",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "mobile_secret",
            tokenExpiresAt: nil
        )
    }
}

private final class StubResultAssetDownloader: ResultAssetDownloading, @unchecked Sendable {
    struct Call: Equatable {
        let downloadURL: String
        let connection: StoredConnection
    }

    private(set) var calls: [Call] = []
    private let result: DownloadedAsset?
    private let error: Error?

    init(result: DownloadedAsset) {
        self.result = result
        self.error = nil
    }

    init(error: Error) {
        self.result = nil
        self.error = error
    }

    func download(downloadURL: String, connection: StoredConnection) async throws -> DownloadedAsset {
        calls.append(Call(downloadURL: downloadURL, connection: connection))
        if let error {
            throw error
        }
        return result!
    }
}
