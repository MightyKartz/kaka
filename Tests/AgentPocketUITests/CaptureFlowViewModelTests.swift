import XCTest
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
@testable import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class CaptureFlowViewModelTests: XCTestCase {
    func testStartsWithNaturalEnhanceIntentAndNoPreparedImage() {
        let viewModel = CaptureFlowViewModel()

        XCTAssertEqual(viewModel.selectedIntent.rawValue, "natural_enhance")
        XCTAssertEqual(viewModel.state, .empty)
    }

    func testPrepareImageMovesFlowToReadyState() throws {
        let viewModel = CaptureFlowViewModel()

        try viewModel.prepareImage(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "photo.jpg",
            width: 640,
            height: 480,
            maxUploadMB: 30
        )

        XCTAssertEqual(viewModel.state, .ready(fileName: "photo.jpg", intentTitle: "Natural Enhance"))
        XCTAssertEqual(viewModel.preparedUpload?.metadata.width, 640)
    }

    func testPrepareSelectedImagePreprocessesRealImageDataForUpload() throws {
        let source = try makeImageData(typeIdentifier: UTType.png.identifier, width: 2, height: 1)
        let viewModel = CaptureFlowViewModel()

        try viewModel.prepareSelectedImage(
            data: source,
            sourceMimeType: "image/png",
            fileName: "library.png",
            maxUploadMB: 30
        )

        XCTAssertEqual(viewModel.state, .ready(fileName: "library.jpg", intentTitle: "Natural Enhance"))
        XCTAssertEqual(viewModel.preparedUpload?.mimeType, "image/jpeg")
        XCTAssertEqual(viewModel.preparedUpload?.metadata.width, 2)
        XCTAssertTrue(viewModel.preparedUpload?.metadata.stripSensitiveEXIF == true)
    }

    func testPrepareSelectedHEICImageMovesFlowToSendableReadyState() throws {
        let source = try makeImageData(typeIdentifier: UTType.heic.identifier, width: 4, height: 3)
        let viewModel = CaptureFlowViewModel()

        try viewModel.prepareSelectedImage(
            data: source,
            sourceMimeType: "image/heic",
            fileName: "iphone-library.heic",
            maxUploadMB: 30
        )

        XCTAssertEqual(viewModel.state, .ready(fileName: "iphone-library.jpg", intentTitle: "Natural Enhance"))
        XCTAssertNotNil(viewModel.preparedUpload)
        XCTAssertEqual(viewModel.preparedUpload?.mimeType, "image/jpeg")
        XCTAssertEqual(viewModel.preparedUpload?.metadata.width, 4)
    }

    func testMarkLoadingSelectedPhotoShowsImmediateFeedbackAndClearsPreviousUpload() throws {
        let source = try makeImageData(typeIdentifier: UTType.png.identifier, width: 2, height: 1)
        let viewModel = CaptureFlowViewModel()
        try viewModel.prepareSelectedImage(
            data: source,
            sourceMimeType: "image/png",
            fileName: "library.png",
            maxUploadMB: 30
        )

        viewModel.markLoadingSelectedPhoto()

        XCTAssertEqual(viewModel.state, .loadingPhoto)
        XCTAssertNil(viewModel.preparedUpload)
        XCTAssertNil(viewModel.completedStatus)
    }

    func testPrepareCapturedPhotoPreprocessesCameraJPEGForUpload() throws {
        let source = try makeImageData(typeIdentifier: UTType.jpeg.identifier, width: 3, height: 2)
        let viewModel = CaptureFlowViewModel()

        try viewModel.prepareCapturedPhoto(
            data: source,
            maxUploadMB: 30
        )

        XCTAssertEqual(viewModel.state, .ready(fileName: "camera.jpg", intentTitle: "Natural Enhance"))
        XCTAssertEqual(viewModel.preparedUpload?.mimeType, "image/jpeg")
        XCTAssertEqual(viewModel.preparedUpload?.metadata.width, 3)
        XCTAssertTrue(viewModel.preparedUpload?.metadata.stripSensitiveEXIF == true)
    }

    func testBuildTaskRequestUsesSelectedIntentAndUploadedAssetID() {
        let viewModel = CaptureFlowViewModel()
        viewModel.selectedIntent = .socialCover

        let task = viewModel.buildTaskRequest(assetID: "asset_123", profileID: "photo-agent")

        XCTAssertEqual(task.assetID, "asset_123")
        XCTAssertEqual(task.style, "social_cover")
        XCTAssertTrue(task.instruction.contains("title-safe"))
        XCTAssertEqual(task.returnVariants, 3)
    }

    func testRejectedImageMovesFlowToFailedState() {
        let viewModel = CaptureFlowViewModel()

        XCTAssertThrowsError(
            try viewModel.prepareImage(
                data: Data("not image".utf8),
                mimeType: "text/plain",
                fileName: "note.txt",
                width: 10,
                height: 10,
                maxUploadMB: 30
            )
        )

        XCTAssertEqual(viewModel.state, .failed(message: "This image format is not supported."))
    }

    func testInvalidSelectedImageShowsReadableFailure() {
        let viewModel = CaptureFlowViewModel()

        XCTAssertThrowsError(
            try viewModel.prepareSelectedImage(
                data: Data("not image".utf8),
                sourceMimeType: "image/jpeg",
                fileName: "bad.jpg",
                maxUploadMB: 30
            )
        )

        XCTAssertEqual(viewModel.state, .failed(message: "This image could not be read."))
        XCTAssertNil(viewModel.preparedUpload)
    }

    func testOversizedSelectedImageShowsReadableFailure() throws {
        let source = try makeImageData(typeIdentifier: UTType.png.identifier, width: 8, height: 8)
        let viewModel = CaptureFlowViewModel()

        XCTAssertThrowsError(
            try viewModel.prepareSelectedImage(
                data: source,
                sourceMimeType: "image/png",
                fileName: "huge.png",
                maxUploadMB: 0
            )
        )

        XCTAssertEqual(viewModel.state, .failed(message: "This image is larger than the runtime allows."))
        XCTAssertNil(viewModel.preparedUpload)
    }

    func testSubmitPreparedImageUploadsStartsTaskAndStoresCompletedStatus() async throws {
        let submitter = StubPhotoEditSubmitter(status: try completedStatus())
        let viewModel = CaptureFlowViewModel(submitter: submitter)
        viewModel.selectedIntent = .portraitPolish
        try viewModel.prepareImage(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "portrait.jpg",
            width: 640,
            height: 480,
            maxUploadMB: 30
        )

        await viewModel.submitPreparedImage(connection: try storedConnection())

        XCTAssertEqual(submitter.calls.map(\.upload.fileName), ["portrait.jpg"])
        XCTAssertEqual(submitter.calls.map(\.intent.rawValue), ["portrait_polish"])
        XCTAssertEqual(submitter.calls.map(\.connection.mobileToken), ["mobile_secret"])
        XCTAssertEqual(submitter.progressEvents, [.uploading, .startingTask, .submitted(taskID: "task_123")])
        XCTAssertEqual(viewModel.state, .completed(taskID: "task_123"))
        XCTAssertEqual(viewModel.completedStatus?.variants?.first?.assetID, "asset_result_1")
    }

    func testSubmitPreparedImageKeepsOriginalPreviewForResultReview() async throws {
        let submitter = StubPhotoEditSubmitter(status: try completedStatus())
        let viewModel = CaptureFlowViewModel(submitter: submitter)
        let originalData = Data("jpeg bytes".utf8)
        try viewModel.prepareImage(
            data: originalData,
            mimeType: "image/jpeg",
            fileName: "portrait.jpg",
            width: 640,
            height: 480,
            maxUploadMB: 30
        )

        await viewModel.submitPreparedImage(connection: try storedConnection())

        XCTAssertEqual(viewModel.originalPreviewAsset, DownloadedAsset(data: originalData, mimeType: "image/jpeg"))
        XCTAssertEqual(viewModel.state, .completed(taskID: "task_123"))
    }

    func testMarkCompletedStoresStatusForImmediateReview() throws {
        let viewModel = CaptureFlowViewModel()
        let status = try completedStatus()

        viewModel.markCompleted(status)

        XCTAssertEqual(viewModel.state, .completed(taskID: "task_123"))
        XCTAssertEqual(viewModel.completedStatus?.variants?.first?.assetID, "asset_result_1")
        XCTAssertNil(viewModel.preparedUpload)
    }

    func testSubmitWithoutPreparedImageFailsClearly() async throws {
        let viewModel = CaptureFlowViewModel(submitter: StubPhotoEditSubmitter(status: try completedStatus()))

        await viewModel.submitPreparedImage(connection: try storedConnection())

        XCTAssertEqual(viewModel.state, .failed(message: "Choose a photo before sending it to your local agent."))
    }

    func testSubmitWithoutConnectionAsksToPairAgain() async throws {
        let viewModel = CaptureFlowViewModel(submitter: StubPhotoEditSubmitter(status: try completedStatus()))
        try viewModel.prepareImage(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "portrait.jpg",
            width: 640,
            height: 480,
            maxUploadMB: 30
        )

        await viewModel.submitPreparedImage(connection: nil)

        XCTAssertEqual(viewModel.state, .failed(message: "Connect to your local agent before sending a photo."))
    }

    func testSubmitFailureShowsRecoverableMessage() async throws {
        let viewModel = CaptureFlowViewModel(
            submitter: StubPhotoEditSubmitter(error: MobileBridgeHTTPClient.ClientError.httpStatus(401, nil))
        )
        try viewModel.prepareImage(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "portrait.jpg",
            width: 640,
            height: 480,
            maxUploadMB: 30
        )

        await viewModel.submitPreparedImage(connection: try storedConnection())

        XCTAssertEqual(viewModel.state, .failed(message: "The local agent token was rejected. Change runtime and pair again."))
    }

    func testProviderFailedTerminalStatusShowsRecoveryMessage() async throws {
        let viewModel = CaptureFlowViewModel(
            submitter: StubPhotoEditSubmitter(status: try failedProviderStatus())
        )
        try viewModel.prepareImage(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "portrait.jpg",
            width: 640,
            height: 480,
            maxUploadMB: 30
        )

        await viewModel.submitPreparedImage(connection: try storedConnection())

        XCTAssertEqual(
            viewModel.state,
            .failed(message: "The photo provider failed. Check local agent provider credentials or logs.")
        )
    }

    func testSubmitOfflineShowsRecoveryMessage() async throws {
        let viewModel = CaptureFlowViewModel(
            submitter: StubPhotoEditSubmitter(error: URLError(.cannotConnectToHost))
        )
        try viewModel.prepareImage(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "portrait.jpg",
            width: 640,
            height: 480,
            maxUploadMB: 30
        )

        await viewModel.submitPreparedImage(connection: try storedConnection())

        XCTAssertEqual(viewModel.state, .failed(message: "Your local agent is offline. Check the network and try again."))
    }

    func testSubmitMissingPhotoEditShowsRecoveryMessage() async throws {
        let viewModel = CaptureFlowViewModel(
            submitter: StubPhotoEditSubmitter(error: ConnectionCheckError.missingPhotoEdit)
        )
        try viewModel.prepareImage(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "portrait.jpg",
            width: 640,
            height: 480,
            maxUploadMB: 30
        )

        await viewModel.submitPreparedImage(connection: try storedConnection())

        XCTAssertEqual(viewModel.state, .failed(message: "This local agent runtime is missing the Photo Pack."))
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

    private func completedStatus() throws -> TaskStatusResponse {
        let data = """
        {"task_id":"task_123","status":"completed","progress":1.0,"message":"Done.","variants":[{"id":"variant_1","label":"Natural","asset_id":"asset_result_1","download_url":"/mobile/v1/assets/asset_result_1/download"}],"explanation":"Balanced exposure."}
        """.data(using: .utf8)!

        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }

    private func failedProviderStatus() throws -> TaskStatusResponse {
        let data = """
        {"task_id":"task_123","status":"failed","progress":1.0,"failure_code":"provider_failed"}
        """.data(using: .utf8)!

        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }

    private func makeImageData(typeIdentifier: String, width: Int, height: Int) throws -> Data {
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        guard let context = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: width * 4,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else {
            throw XCTSkip("Could not create test image context.")
        }
        context.setFillColor(CGColor(red: 0.2, green: 0.4, blue: 0.8, alpha: 1.0))
        context.fill(CGRect(x: 0, y: 0, width: width, height: height))
        guard let image = context.makeImage() else {
            throw XCTSkip("Could not create test image.")
        }

        let data = NSMutableData()
        guard let destination = CGImageDestinationCreateWithData(data, typeIdentifier as CFString, 1, nil) else {
            throw XCTSkip("Could not create image destination.")
        }
        CGImageDestinationAddImage(destination, image, [:] as CFDictionary)
        guard CGImageDestinationFinalize(destination) else {
            throw XCTSkip("Could not finalize image.")
        }
        return data as Data
    }
}

private final class StubPhotoEditSubmitter: PhotoEditSubmitting, @unchecked Sendable {
    struct Call: Equatable {
        let upload: PreparedImageUpload
        let intent: EditIntent
        let connection: StoredConnection
    }

    private(set) var calls: [Call] = []
    private(set) var progressEvents: [PhotoEditSubmissionProgress] = []
    private let status: TaskStatusResponse?
    private let error: Error?

    init(status: TaskStatusResponse) {
        self.status = status
        self.error = nil
    }

    init(error: Error) {
        self.status = nil
        self.error = error
    }

    func submit(
        upload: PreparedImageUpload,
        intent: EditIntent,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        calls.append(Call(upload: upload, intent: intent, connection: connection))
        await progress(.uploading)
        await progress(.startingTask)
        await progress(.submitted(taskID: "task_123"))
        progressEvents = [.uploading, .startingTask, .submitted(taskID: "task_123")]
        if let error {
            throw error
        }
        return status!
    }
}
