import AgentPocketCore
import Foundation

@MainActor
public final class CaptureFlowViewModel: ObservableObject {
    public enum State: Equatable, Sendable {
        case empty
        case loadingPhoto
        case ready(fileName: String, intentTitle: String)
        case uploading
        case startingTask
        case submitted(taskID: String)
        case running(taskID: String, progress: Double, message: String?)
        case completed(taskID: String)
        case failed(message: String)
    }

    @Published public var selectedIntent: EditIntent
    @Published public var selectedCameraMode: SmartCameraMode
    @Published public private(set) var state: State
    @Published public private(set) var preparedUpload: PreparedImageUpload?
    @Published public private(set) var originalPreviewAsset: DownloadedAsset?
    @Published public private(set) var completedStatus: TaskStatusResponse?
    private let photoSubmitter: any PhotoEditSubmitting
    private let visionSubmitter: any VisionSubmitting
    private let imageIntakeSubmitter: any ImageIntakeSubmitting

    public init(
        selectedIntent: EditIntent = .naturalEnhance,
        selectedCameraMode: SmartCameraMode = .masterShot,
        state: State = .empty,
        submitter: any PhotoEditSubmitting = MobileBridgePhotoEditSubmitter(),
        visionSubmitter: any VisionSubmitting = MobileBridgeVisionSubmitter(),
        imageIntakeSubmitter: any ImageIntakeSubmitting = MobileBridgeImageIntakeSubmitter()
    ) {
        self.selectedIntent = selectedIntent
        self.selectedCameraMode = selectedCameraMode
        self.state = state
        self.photoSubmitter = submitter
        self.visionSubmitter = visionSubmitter
        self.imageIntakeSubmitter = imageIntakeSubmitter
    }

    public func prepareImage(
        data: Data,
        mimeType: String,
        fileName: String,
        width: Int,
        height: Int,
        maxUploadMB: Int
    ) throws {
        do {
            let policy = ImageUploadPolicy(maxUploadMB: maxUploadMB)
            let upload = try policy.prepare(
                data: data,
                mimeType: mimeType,
                fileName: fileName,
                width: width,
                height: height,
                localCreationTime: nil
            )
            preparedUpload = upload
            originalPreviewAsset = DownloadedAsset(data: upload.data, mimeType: upload.mimeType)
            completedStatus = nil
            state = .ready(fileName: fileName, intentTitle: selectedIntent.displayTitle)
        } catch ImageUploadPolicy.ValidationError.unsupportedMimeType {
            state = .failed(message: "This image format is not supported.")
            throw ImageUploadPolicy.ValidationError.unsupportedMimeType
        } catch ImageUploadPolicy.ValidationError.exceedsMaxUploadSize {
            state = .failed(message: "This image is larger than the runtime allows.")
            throw ImageUploadPolicy.ValidationError.exceedsMaxUploadSize
        } catch {
            state = .failed(message: "This image could not be prepared.")
            throw error
        }
    }

    public func prepareSelectedImage(
        data: Data,
        sourceMimeType: String,
        fileName: String,
        maxUploadMB: Int
    ) throws {
        do {
            let upload = try ImagePreprocessor().prepareForUpload(
                data: data,
                sourceMimeType: sourceMimeType,
                originalFileName: fileName,
                maxUploadMB: maxUploadMB
            )
            preparedUpload = upload
            originalPreviewAsset = DownloadedAsset(data: upload.data, mimeType: upload.mimeType)
            completedStatus = nil
            state = .ready(fileName: upload.fileName, intentTitle: selectedIntent.displayTitle)
        } catch ImageUploadPolicy.ValidationError.unsupportedMimeType {
            state = .failed(message: "This image format is not supported.")
            throw ImageUploadPolicy.ValidationError.unsupportedMimeType
        } catch ImageUploadPolicy.ValidationError.exceedsMaxUploadSize {
            state = .failed(message: "This image is larger than the runtime allows.")
            throw ImageUploadPolicy.ValidationError.exceedsMaxUploadSize
        } catch ImagePreprocessor.PreprocessError.cannotDecodeImage {
            state = .failed(message: "This image could not be read.")
            throw ImagePreprocessor.PreprocessError.cannotDecodeImage
        } catch {
            state = .failed(message: "This image could not be prepared.")
            throw error
        }
    }

    public func markLoadingSelectedPhoto() {
        preparedUpload = nil
        originalPreviewAsset = nil
        completedStatus = nil
        state = .loadingPhoto
    }

    public func prepareCapturedPhoto(
        data: Data,
        maxUploadMB: Int
    ) throws {
        try prepareSelectedImage(
            data: data,
            sourceMimeType: "image/jpeg",
            fileName: "camera.jpg",
            maxUploadMB: maxUploadMB
        )
    }

    public func buildTaskRequest(assetID: String, profileID: String) -> PhotoEditTaskRequest {
        PhotoEditTaskRequest(
            profileID: profileID,
            assetID: assetID,
            intent: selectedIntent,
            returnVariants: 3
        )
    }

    public func markUploading() {
        state = .uploading
    }

    public func markStartingTask() {
        state = .startingTask
    }

    public func markSubmitted(taskID: String) {
        state = .submitted(taskID: taskID)
    }

    public func markFailed(_ message: String) {
        state = .failed(message: message)
    }

    public func markCompleted(_ status: TaskStatusResponse) {
        completedStatus = status
        if status.resultType != "image_intake" {
            preparedUpload = nil
        }
        state = .completed(taskID: status.taskID)
    }

    public func resetForNextCapture() {
        selectedIntent = .naturalEnhance
        preparedUpload = nil
        originalPreviewAsset = nil
        completedStatus = nil
        state = .empty
    }

    public func submitPreparedImage(connection: StoredConnection?) async {
        guard let connection else {
            state = .failed(message: "Connect to your local agent before sending a photo.")
            return
        }
        guard let preparedUpload else {
            state = .failed(message: "Choose a photo before sending it to your local agent.")
            return
        }

        do {
            let terminalStatus: TaskStatusResponse
            if selectedCameraMode == .masterShot {
                terminalStatus = try await photoSubmitter.submit(
                    upload: preparedUpload,
                    intent: selectedIntent,
                    connection: connection
                ) { [weak self] progress in
                    await self?.apply(progress)
                }
            } else {
                terminalStatus = try await visionSubmitter.submit(
                    upload: preparedUpload,
                    mode: selectedCameraMode,
                    connection: connection
                ) { [weak self] progress in
                    await self?.apply(progress)
                }
            }
            completedStatus = terminalStatus
            if terminalStatus.status == "completed" {
                state = .completed(taskID: terminalStatus.taskID)
            } else {
                state = .failed(message: failureMessage(for: terminalStatus))
            }
        } catch MobileBridgeHTTPClient.ClientError.httpStatus(401, _) {
            state = .failed(message: "The local agent token was rejected. Change runtime and pair again.")
        } catch ConnectionCheckError.missingPhotoEdit {
            state = .failed(message: "This local agent runtime is missing the Photo Pack.")
        } catch ConnectionCheckError.missingVision {
            state = .failed(message: "This local agent runtime is missing Vision tasks.")
        } catch let error as URLError where error.isLikelyOffline {
            state = .failed(message: "Your local agent is offline. Check the network and try again.")
        } catch {
            state = .failed(message: selectedCameraMode == .masterShot ? "Could not submit photo edit." : "Could not submit vision task.")
        }
    }

    public func submitImageIntake(connection: StoredConnection?) async {
        guard let connection else {
            state = .failed(message: "Connect to your local agent before sending a photo.")
            return
        }
        guard let preparedUpload else {
            state = .failed(message: "Choose a photo before sending it to your local agent.")
            return
        }

        do {
            let terminalStatus = try await imageIntakeSubmitter.submit(
                upload: preparedUpload,
                connection: connection
            ) { [weak self] progress in
                await self?.apply(progress)
            }
            completedStatus = terminalStatus
            if terminalStatus.status == "completed" {
                state = .completed(taskID: terminalStatus.taskID)
            } else {
                state = .failed(message: failureMessage(for: terminalStatus))
            }
        } catch MobileBridgeHTTPClient.ClientError.httpStatus(401, _) {
            state = .failed(message: "The local agent token was rejected. Change runtime and pair again.")
        } catch ConnectionCheckError.missingVision {
            state = .failed(message: "This local agent runtime is missing Vision tasks.")
        } catch let error as URLError where error.isLikelyOffline {
            state = .failed(message: "Your local agent is offline. Check the network and try again.")
        } catch {
            state = .failed(message: "Could not inspect image.")
        }
    }

    private func apply(_ progress: PhotoEditSubmissionProgress) {
        switch progress {
        case .uploading:
            state = .uploading
        case .startingTask:
            state = .startingTask
        case .submitted(let taskID):
            state = .submitted(taskID: taskID)
        case .running(let taskID, let progress, let message):
            state = .running(taskID: taskID, progress: progress, message: message)
        }
    }

    private func failureMessage(for status: TaskStatusResponse) -> String {
        if let message = status.message, message.isEmpty == false {
            return message
        }

        switch status.failureCode {
        case "provider_failed", "provider_rejected_image":
            return "The photo provider failed. Check local agent provider credentials or logs."
        case "vision_failed":
            return "The vision provider failed. Check local agent provider credentials or logs."
        case "image_intake_failed":
            return "The image intake provider failed. Check local agent provider credentials or logs."
        default:
            if status.resultType == "vision" {
                return "Vision task did not complete."
            }
            if status.resultType == "image_intake" {
                return "Image intake did not complete."
            }
            return "Photo edit did not complete."
        }
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
