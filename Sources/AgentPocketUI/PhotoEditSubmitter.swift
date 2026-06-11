import AgentPocketCore
import Foundation

public enum PhotoEditSubmissionProgress: Equatable, Sendable {
    case uploading
    case startingTask
    case submitted(taskID: String)
    case running(taskID: String, progress: Double, message: String?)
}

public protocol PhotoEditSubmitting: Sendable {
    func submit(
        upload: PreparedImageUpload,
        intent: EditIntent,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse
}

public struct MobileBridgePhotoEditSubmitter: PhotoEditSubmitting {
    private let session: URLSession?
    private let poller: TaskPoller

    public init(
        session: URLSession? = nil,
        poller: TaskPoller = TaskPoller()
    ) {
        self.session = session
        self.poller = poller
    }

    public func submit(
        upload: PreparedImageUpload,
        intent: EditIntent,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        let client = MobileBridgeHTTPClient(
            connection: connection,
            session: session
        )
        let capabilities = try await client.fetchCapabilities()
        let profileID = try photoEditProfileID(from: capabilities)
        let returnVariants = min(3, capabilities.tasks.photoEdit.returnVariantsMax)

        await progress(.uploading)
        let uploaded = try await client.uploadAsset(upload)

        await progress(.startingTask)
        let created = try await client.startPhotoEditTask(
            PhotoEditTaskRequest(
                profileID: profileID,
                assetID: uploaded.assetID,
                intent: intent,
                returnVariants: returnVariants
            )
        )

        await progress(.submitted(taskID: created.taskID))
        if capabilities.tasks.photoEdit.supportsSSE, let eventsURL = created.eventsURL {
            do {
                let events = try await client.fetchTaskEvents(eventsURL: eventsURL)
                for event in events {
                    if case .progress(let value, let message) = event {
                        await progress(.running(taskID: created.taskID, progress: value, message: message))
                    }
                }
            } catch {
                _ = TaskProgressTransport.fallback(after: .disconnected)
            }
        }
        return try await poller.pollUntilTerminal {
            try await client.fetchTaskStatus(taskID: created.taskID)
        }
    }

    private func photoEditProfileID(from capabilities: CapabilitiesResponse) throws -> String {
        guard let profile = capabilities.profiles.first(where: { $0.capabilities.contains("photo_edit") }) else {
            throw ConnectionCheckError.missingPhotoEdit
        }
        return profile.id
    }
}
