import AgentPocketCore
import Foundation

public protocol ImageIntakeSubmitting: Sendable {
    func submit(
        upload: PreparedImageUpload,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse
}

public struct MobileBridgeImageIntakeSubmitter: ImageIntakeSubmitting {
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
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        let client = MobileBridgeHTTPClient(
            connection: connection,
            session: session
        )
        let capabilities = try await client.fetchCapabilities()
        let profileID = try intakeProfileID(from: capabilities)

        await progress(.uploading)
        let uploaded = try await client.uploadAsset(upload)

        await progress(.startingTask)
        let created = try await client.startImageIntakeTask(
            ImageIntakeTaskRequest(
                profileID: profileID,
                assetID: uploaded.assetID,
                locale: AppLanguage.resolved(storedValue: nil).rawValue
            )
        )

        await progress(.submitted(taskID: created.taskID))
        return try await poller.pollUntilTerminal {
            try await client.fetchTaskStatus(taskID: created.taskID)
        }
    }

    private func intakeProfileID(from capabilities: CapabilitiesResponse) throws -> String {
        guard let profile = capabilities.profiles.first(where: {
            $0.capabilities.contains("image_intake") || $0.capabilities.contains("vision")
        }) else {
            throw ConnectionCheckError.missingVision
        }
        return profile.id
    }
}
