import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class CaptureScreenPresentationTests: XCTestCase {
    func testChineseEmptyPresentationIsCameraFirstAndRuntimeNeutral() {
        let viewModel = CaptureFlowViewModel()

        let presentation = CaptureScreenPresentation(
            state: viewModel.state,
            selectedCameraMode: viewModel.selectedCameraMode,
            selectedIntent: viewModel.selectedIntent,
            language: .chinese,
            connectedRuntimeName: "Kartz Mac"
        )

        XCTAssertEqual(presentation.title, "智能相机")
        XCTAssertEqual(presentation.connectedBadge, "已连接 · Kartz Mac")
        XCTAssertTrue(presentation.modeTabs.isEmpty)
        XCTAssertEqual(presentation.primaryAction.title, "拍摄")
        XCTAssertEqual(presentation.primaryAction.systemImage, "camera.fill")
        XCTAssertTrue(presentation.primaryAction.isEnabled)
        XCTAssertEqual(presentation.statusText, "拍一张照片，让 Kaka 判断可以做什么。")
        XCTAssertEqual(presentation.galleryTitle, "相册")
        XCTAssertEqual(presentation.cameraTitle, "拍照")
    }

    func testChineseConnectedBadgeHidesRawIPAddressOnCaptureScreen() {
        let presentation = CaptureScreenPresentation(
            state: .empty,
            selectedCameraMode: .masterShot,
            selectedIntent: .naturalEnhance,
            language: .chinese,
            connectedRuntimeName: "192.168.1.107"
        )

        XCTAssertEqual(presentation.connectedBadge, "已连接 · 本机智能体")
    }

    func testDisconnectedCaptureBadgeDoesNotClaimRuntimeIsConnected() {
        let presentation = CaptureScreenPresentation(
            state: .empty,
            selectedCameraMode: .masterShot,
            selectedIntent: .naturalEnhance,
            language: .chinese,
            connectedRuntimeName: nil
        )

        XCTAssertEqual(presentation.connectedBadge, "未连接 · 本机智能体")
    }

    func testReadyPresentationEnablesSendActionForKaka() throws {
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
            selectedCameraMode: .masterShot,
            selectedIntent: viewModel.selectedIntent,
            language: .english,
            connectedRuntimeName: "Kartz Mac"
        )

        XCTAssertEqual(presentation.title, "Smart Camera")
        XCTAssertEqual(presentation.connectedBadge, "Connected · Kartz Mac")
        XCTAssertEqual(presentation.primaryAction.title, "Send to Kaka")
        XCTAssertEqual(presentation.primaryAction.systemImage, "paperplane.fill")
        XCTAssertTrue(presentation.primaryAction.isEnabled)
        XCTAssertEqual(presentation.statusText, "The photo is ready. Kaka will decide what it can do first.")
    }

    func testReadyPresentationPromptsSendToKaka() throws {
        let presentation = CaptureScreenPresentation(
            state: .ready(fileName: "camera.jpg", intentTitle: "Natural Enhance"),
            selectedCameraMode: .masterShot,
            selectedIntent: .naturalEnhance,
            language: .chinese,
            connectedRuntimeName: "Kartz Mac",
            hasPreparedUpload: true
        )

        XCTAssertEqual(presentation.primaryAction.title, "发送给 Kaka")
        XCTAssertEqual(presentation.primaryAction.systemImage, "paperplane.fill")
        XCTAssertEqual(presentation.statusText, "照片已准备好，Kaka 会先判断适合做什么。")
    }

    func testCompletedPresentationUsesImageUnderstandingCopy() throws {
        let status = try completedStatus()

        let presentation = CaptureScreenPresentation(
            state: .completed(taskID: status.taskID),
            selectedCameraMode: .masterShot,
            selectedIntent: .naturalEnhance,
            language: .chinese,
            connectedRuntimeName: "Kartz Mac"
        )

        XCTAssertEqual(presentation.primaryAction.title, "查看结果")
        XCTAssertEqual(presentation.primaryAction.systemImage, "rectangle.on.rectangle")
        XCTAssertTrue(presentation.primaryAction.isEnabled)
        XCTAssertEqual(presentation.statusText, "已完成图片理解，正在打开对话。")
    }

    func testCompletedPresentationIsModeNeutral() throws {
        let presentation = CaptureScreenPresentation(
            state: .completed(taskID: "task_vision_123"),
            selectedCameraMode: .identify,
            selectedIntent: .naturalEnhance,
            language: .chinese,
            connectedRuntimeName: "Kartz Mac"
        )

        XCTAssertEqual(presentation.primaryAction.title, "查看结果")
        XCTAssertEqual(presentation.primaryAction.systemImage, "rectangle.on.rectangle")
        XCTAssertEqual(presentation.statusText, "已完成图片理解，正在打开对话。")
    }

    func testProcessingPresentationShowsBlockingProgress() {
        let presentation = CaptureScreenPresentation(
            state: .running(taskID: "task_123", progress: 0.42, message: nil),
            selectedCameraMode: .masterShot,
            selectedIntent: .naturalEnhance,
            language: .chinese,
            connectedRuntimeName: "Kartz Mac"
        )

        XCTAssertTrue(presentation.isProcessing)
        XCTAssertEqual(presentation.primaryAction.title, "处理中")
    }

    func testChineseCameraFailureMessageIsLocalized() {
        let presentation = CaptureScreenPresentation(
            state: .failed(message: "Camera access is disabled. Allow camera access in Settings or choose a photo from the library."),
            selectedCameraMode: .masterShot,
            selectedIntent: .naturalEnhance,
            language: .chinese,
            connectedRuntimeName: "Kartz Mac"
        )

        XCTAssertEqual(presentation.statusText, "相机权限未开启。请在系统设置中允许相机访问，或从相册选择照片。")
        XCTAssertFalse(presentation.statusText.localizedCaseInsensitiveContains("Camera"))
        XCTAssertFalse(presentation.statusText.localizedCaseInsensitiveContains("Settings"))
    }

    func testReadyPresentationIgnoresLegacyCameraMode() throws {
        let presentation = CaptureScreenPresentation(
            state: .ready(fileName: "receipt.jpg", intentTitle: "Natural Enhance"),
            selectedCameraMode: .scan,
            selectedIntent: .naturalEnhance,
            language: .chinese,
            connectedRuntimeName: "Kartz Mac"
        )

        XCTAssertTrue(presentation.modeTabs.isEmpty)
        XCTAssertEqual(presentation.primaryAction.title, "发送给 Kaka")
        XCTAssertEqual(presentation.primaryAction.systemImage, "paperplane.fill")
        XCTAssertEqual(presentation.statusText, "照片已准备好，Kaka 会先判断适合做什么。")
    }

    func testChineseUnavailableSmartCameraModeMessageIsLocalized() {
        let presentation = CaptureScreenPresentation(
            state: .failed(message: SmartCameraMode.unavailableFailureMessage),
            selectedCameraMode: .identify,
            selectedIntent: .naturalEnhance,
            language: .chinese,
            connectedRuntimeName: "Kartz Mac"
        )

        XCTAssertEqual(presentation.statusText, "此智能相机模式的智能体任务协议尚未接入。照片已保留，可切回成片继续处理。")
    }

    private func completedStatus() throws -> TaskStatusResponse {
        let data = """
        {"task_id":"task_123","status":"completed","progress":1.0,"message":"Done.","variants":[{"id":"variant_1","label":"Natural","asset_id":"asset_result_1","download_url":"/mobile/v1/assets/asset_result_1/download"}]}
        """.data(using: .utf8)!

        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }
}
