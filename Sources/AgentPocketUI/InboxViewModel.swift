import AgentPocketCore
import Foundation

public protocol ImageInboxSubmitting: Sendable {
    func submit(
        item: KakaInboxItem,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse
}

public struct MobileBridgeImageInboxSubmitter: ImageInboxSubmitting {
    private let loader: any InboxImagePayloadLoading
    private let submitter: any ImageIntakeSubmitting

    public init(
        loader: any InboxImagePayloadLoading = FileInboxImagePayloadLoader(),
        submitter: any ImageIntakeSubmitting = MobileBridgeImageIntakeSubmitter()
    ) {
        self.loader = loader
        self.submitter = submitter
    }

    public func submit(
        item: KakaInboxItem,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        let upload = try loader.preparedUpload(for: item)
        return try await submitter.submit(
            upload: upload,
            connection: connection,
            progress: progress
        )
    }
}

public struct UnavailableImageInboxSubmitter: ImageInboxSubmitting {
    public init() {}

    public func submit(
        item: KakaInboxItem,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        throw URLError(.unsupportedURL)
    }
}

@MainActor
public final class InboxViewModel: ObservableObject {
    public enum State: Equatable, Sendable {
        case idle
        case loading
        case submitting
        case completed
        case failed(String)
    }

    @Published public private(set) var items: [KakaInboxItem] = []
    @Published public private(set) var state: State = .idle
    @Published public private(set) var completedStatus: TaskStatusResponse?
    @Published public private(set) var progressText: String?

    private let store: any KakaInboxStoring
    private let submitter: any UniversalIntakeSubmitting
    private let imageSubmitter: any ImageInboxSubmitting

    public init(
        store: any KakaInboxStoring,
        submitter: any UniversalIntakeSubmitting = MobileBridgeUniversalIntakeSubmitter(),
        imageSubmitter: any ImageInboxSubmitting = MobileBridgeImageInboxSubmitter()
    ) {
        self.store = store
        self.submitter = submitter
        self.imageSubmitter = imageSubmitter
    }

    public func reload() throws {
        state = .loading
        items = try store.loadItems().sorted {
            if $0.receivedAt == $1.receivedAt {
                return $0.id.uuidString > $1.id.uuidString
            }
            return $0.receivedAt > $1.receivedAt
        }
        state = .idle
    }

    public func submit(
        _ item: KakaInboxItem,
        connection: StoredConnection?,
        contextSnapshot: ContextSnapshotPayload? = nil
    ) async {
        guard canSubmit(item) else {
            completedStatus = nil
            state = .failed("PDF inbox submission will be available after document skills are connected.")
            return
        }
        guard let connection else {
            completedStatus = nil
            state = .failed("Connect to your local agent before submitting inbox items.")
            return
        }

        do {
            state = .submitting
            progressText = nil
            completedStatus = nil
            let status: TaskStatusResponse
            if item.route == .imageIntake {
                status = try await imageSubmitter.submit(item: item, connection: connection, progress: updateProgress)
            } else {
                status = try await submitter.submit(
                    item: item,
                    connection: connection,
                    contextSnapshot: contextSnapshot,
                    progress: updateProgress
                )
            }
            guard status.status == "completed" else {
                completedStatus = nil
                state = .failed(status.message ?? "The intake task did not complete.")
                return
            }
            completedStatus = status
            try store.remove(id: item.id)
            try reload()
            state = .completed
        } catch {
            completedStatus = nil
            state = .failed(Self.failureMessage(for: error))
        }
    }

    public func canSubmit(_ item: KakaInboxItem) -> Bool {
        switch item.kind {
        case .text, .url, .image, .screenshot, .pdf:
            return true
        }
    }

    public func dismissResult() {
        completedStatus = nil
        progressText = nil
        if case .completed = state {
            state = .idle
        }
    }

    private func updateProgress(_ progress: PhotoEditSubmissionProgress) async {
        switch progress {
        case .uploading:
            progressText = "Uploading"
        case .startingTask:
            progressText = "Starting"
        case .submitted(let taskID):
            progressText = "Submitted \(taskID)"
        case .running(_, let progress, let message):
            let percent = Int((progress * 100).rounded())
            progressText = message ?? "Running \(percent)%"
        }
    }

    private static func failureMessage(for error: Error) -> String {
        if let clientError = error as? MobileBridgeHTTPClient.ClientError,
           case .httpStatus(let code, _) = clientError,
           code == 401 {
            return "The local agent token was rejected. Change runtime and pair again."
        }
        if let connectionError = error as? ConnectionCheckError {
            switch connectionError {
            case .missingPhotoEdit:
                return "This local agent runtime is missing the Photo Pack."
            case .missingVision:
                return "This local agent runtime is missing Vision tasks."
            case .missingIntake:
                return "This local agent runtime is missing inbox intake."
            }
        }
        if let urlError = error as? URLError,
           [.cannotConnectToHost, .networkConnectionLost, .notConnectedToInternet, .timedOut].contains(urlError.code) {
            return "Your local agent is offline. Check the network and try again."
        }
        if let loaderError = error as? FileInboxDocumentPayloadLoader.LoadError {
            switch loaderError {
            case .exceedsMaxUploadSize:
                return "PDF is too large. Share a PDF under 25 MB."
            case .missingRelativePath, .unsafeRelativePath:
                return "The shared PDF file is no longer available. Share it to Kaka again."
            case .unsupportedKind, .unsupportedMimeType:
                return "This inbox item is not a supported PDF."
            }
        }
        return "Could not submit inbox item."
    }
}
