import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class ResultScreenPresentationTests: XCTestCase {
    func testChinesePresentationPromotesDownloadBeforeVariantIsReady() throws {
        let viewModel = ResultGalleryViewModel(status: try completedLocalRecipeStatus())

        let presentation = ResultScreenPresentation(
            comparison: viewModel.comparisonPresentation,
            variants: viewModel.variants,
            selectedVariantID: viewModel.selectedVariantID,
            state: viewModel.state,
            saveState: .idle,
            language: .chinese,
            canShare: false
        )

        XCTAssertEqual(presentation.title, "成片结果")
        XCTAssertEqual(presentation.beforeLabel, "原图")
        XCTAssertEqual(presentation.afterLabel, "大师")
        XCTAssertEqual(presentation.variantTabs.map(\.title), ["大师", "社交"])
        XCTAssertEqual(presentation.downloadAction.title, "下载成片")
        XCTAssertTrue(presentation.downloadAction.isEnabled)
        XCTAssertFalse(presentation.saveAction.isEnabled)
        XCTAssertFalse(presentation.shareAction.isEnabled)
    }

    func testEnglishDownloadedPresentationEnablesSaveAndShare() throws {
        let edited = DownloadedAsset(data: Data([0x89, 0x50, 0x4E, 0x47]), mimeType: "image/png")
        let viewModel = ResultGalleryViewModel(
            status: try completedLocalRecipeStatus(),
            initialDownloadedAssets: ["variant_clean_pro": edited]
        )

        let presentation = ResultScreenPresentation(
            comparison: viewModel.comparisonPresentation,
            variants: viewModel.variants,
            selectedVariantID: viewModel.selectedVariantID,
            state: viewModel.state,
            saveState: .idle,
            language: .english,
            canShare: true
        )

        XCTAssertEqual(presentation.title, "Master Result")
        XCTAssertEqual(presentation.beforeLabel, "Original")
        XCTAssertEqual(presentation.afterLabel, "Master")
        XCTAssertEqual(presentation.downloadAction.title, "Downloaded")
        XCTAssertFalse(presentation.downloadAction.isEnabled)
        XCTAssertEqual(presentation.saveAction.title, "Save")
        XCTAssertTrue(presentation.saveAction.isEnabled)
        XCTAssertEqual(presentation.shareAction.title, "Share")
        XCTAssertTrue(presentation.shareAction.isEnabled)
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
          "renderer": "local_parametric",
          "composition": {
            "selected_aspect_ratio": "original",
            "crop": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
          },
          "qa": {
            "master_difference_score": 0.18,
            "social_difference_score": 0.31
          },
          "recipe_summary": "Balanced exposure while preserving the original frame.",
          "share_caption": "Shot polished locally with Pocket Agent."
        }
        """.data(using: .utf8)!

        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }
}
