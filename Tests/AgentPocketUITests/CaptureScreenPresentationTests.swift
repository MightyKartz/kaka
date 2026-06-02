import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class CaptureScreenPresentationTests: XCTestCase {
    func testChineseEmptyPresentationIsCameraFirstAndRuntimeNeutral() {
        let viewModel = CaptureFlowViewModel()

        let presentation = CaptureScreenPresentation(
            state: viewModel.state,
            selectedIntent: viewModel.selectedIntent,
            language: .chinese,
            connectedRuntimeName: "Kartz Mac"
        )

        XCTAssertEqual(presentation.title, "大师成片")
        XCTAssertEqual(presentation.connectedBadge, "已连接 · Kartz Mac")
        XCTAssertEqual(presentation.sceneTabs.map(\.title), ["自然", "人像", "产品", "社交"])
        XCTAssertEqual(presentation.primaryAction.title, "一键成片")
        XCTAssertEqual(presentation.primaryAction.systemImage, "sparkles")
        XCTAssertFalse(presentation.primaryAction.isEnabled)
        XCTAssertEqual(presentation.statusText, "拍照或选择一张照片开始。")
        XCTAssertEqual(presentation.galleryTitle, "相册")
        XCTAssertEqual(presentation.cameraTitle, "拍照")
    }

    func testReadyPresentationEnablesSendActionAndNamesSelectedScene() throws {
        let viewModel = CaptureFlowViewModel()
        viewModel.selectedIntent = .portraitPolish
        try viewModel.prepareImage(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "portrait.jpg",
            width: 640,
            height: 480,
            maxUploadMB: 30
        )

        let presentation = CaptureScreenPresentation(
            state: viewModel.state,
            selectedIntent: viewModel.selectedIntent,
            language: .english,
            connectedRuntimeName: "Kartz Mac"
        )

        XCTAssertEqual(presentation.title, "Master Shot")
        XCTAssertEqual(presentation.connectedBadge, "Connected · Kartz Mac")
        XCTAssertEqual(presentation.sceneTabs.first(where: { $0.intent == .portraitPolish })?.title, "Portrait")
        XCTAssertEqual(presentation.primaryAction.title, "Send to Local Agent")
        XCTAssertTrue(presentation.primaryAction.isEnabled)
        XCTAssertEqual(presentation.statusText, "portrait.jpg is ready for Portrait.")
    }

    func testCompletedPresentationPromotesReviewAction() throws {
        let status = try completedStatus()

        let presentation = CaptureScreenPresentation(
            state: .completed(taskID: status.taskID),
            selectedIntent: .naturalEnhance,
            language: .chinese,
            connectedRuntimeName: "Kartz Mac"
        )

        XCTAssertEqual(presentation.primaryAction.title, "查看成片")
        XCTAssertEqual(presentation.primaryAction.systemImage, "rectangle.on.rectangle")
        XCTAssertTrue(presentation.primaryAction.isEnabled)
        XCTAssertEqual(presentation.statusText, "已生成可对比的成片。")
    }

    private func completedStatus() throws -> TaskStatusResponse {
        let data = """
        {"task_id":"task_123","status":"completed","progress":1.0,"message":"Done.","variants":[{"id":"variant_1","label":"Natural","asset_id":"asset_result_1","download_url":"/mobile/v1/assets/asset_result_1/download"}]}
        """.data(using: .utf8)!

        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }
}
