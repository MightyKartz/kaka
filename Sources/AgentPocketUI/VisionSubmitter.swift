import AgentPocketCore
import Foundation

public protocol VisionSubmitting: Sendable {
    func submit(
        upload: PreparedImageUpload,
        mode: SmartCameraMode,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse
}

public struct MobileBridgeVisionSubmitter: VisionSubmitting {
    private let session: URLSession
    private let poller: TaskPoller

    public init(
        session: URLSession = .shared,
        poller: TaskPoller = TaskPoller()
    ) {
        self.session = session
        self.poller = poller
    }

    public func submit(
        upload: PreparedImageUpload,
        mode: SmartCameraMode,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        guard let kind = mode.visionTaskKind else {
            throw ConnectionCheckError.missingVision
        }

        let client = MobileBridgeHTTPClient(
            endpoint: connection.endpoint,
            token: connection.mobileToken,
            session: session
        )
        let capabilities = try await client.fetchCapabilities()
        let profileID = try visionProfileID(from: capabilities, mode: kind)

        await progress(.uploading)
        let uploaded = try await client.uploadAsset(upload)

        await progress(.startingTask)
        let created = try await client.startVisionTask(
            VisionTaskRequest(
                profileID: profileID,
                assetID: uploaded.assetID,
                mode: kind,
                locale: AppLanguage.resolved(storedValue: nil).rawValue
            )
        )

        await progress(.submitted(taskID: created.taskID))
        if capabilities.tasks.vision?.supportsSSE == true, let eventsURL = created.eventsURL {
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

    private func visionProfileID(from capabilities: CapabilitiesResponse, mode: VisionTaskKind) throws -> String {
        guard let vision = capabilities.tasks.vision,
              vision.modes.contains(mode.rawValue),
              let profile = capabilities.profiles.first(where: { $0.capabilities.contains("vision") }) else {
            throw ConnectionCheckError.missingVision
        }
        return profile.id
    }
}
