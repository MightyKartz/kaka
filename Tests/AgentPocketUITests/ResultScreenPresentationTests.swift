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
            recipe: viewModel.recipePresentation,
            explanation: viewModel.explanation,
            state: viewModel.state,
            saveState: .idle,
            language: .chinese,
            canShare: false
        )

        XCTAssertEqual(presentation.title, "成片结果")
        XCTAssertEqual(presentation.beforeLabel, "原图")
        XCTAssertEqual(presentation.afterLabel, "Master")
        XCTAssertEqual(presentation.variantTabs.map(\.title), ["Master", "Social"])
        XCTAssertEqual(presentation.recipeTitle, "修图配方")
        XCTAssertEqual(presentation.recipeChips, ["4:5 裁切", "提亮暗部", "校正色温", "增强主体"])
        XCTAssertEqual(presentation.downloadAction.title, "下载成片")
        XCTAssertTrue(presentation.downloadAction.isEnabled)
        XCTAssertFalse(presentation.saveAction.isEnabled)
        XCTAssertFalse(presentation.shareAction.isEnabled)
        XCTAssertEqual(presentation.sharePlatformTitles, ["微信", "朋友圈", "小红书", "X"])
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
            recipe: viewModel.recipePresentation,
            explanation: viewModel.explanation,
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
        XCTAssertEqual(presentation.sharePlatformTitles, ["WeChat", "Moments", "RED", "X"])
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
}
