import AgentPocketCore
import Foundation

public struct MobileBridgeImageSkillSubmitter: ImageSkillExecuting {
    private let session: URLSession
    private let poller: TaskPoller

    public init(
        session: URLSession = .shared,
        poller: TaskPoller = TaskPoller()
    ) {
        self.session = session
        self.poller = poller
    }

    public func execute(
        skill: KakaSkillID,
        userInstruction: String?,
        upload: PreparedImageUpload,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        let client = MobileBridgeHTTPClient(
            endpoint: connection.endpoint,
            token: connection.mobileToken,
            session: session
        )
        let capabilities = try await client.fetchCapabilities()

        await progress(.uploading)
        let uploaded = try await client.uploadAsset(upload)

        await progress(.startingTask)
        switch skill {
        case .photoEnhance:
            let profileID = try photoEditProfileID(from: capabilities)
            let created = try await client.startPhotoEditTask(
                PhotoEditTaskRequest(
                    profileID: profileID,
                    assetID: uploaded.assetID,
                    intent: .naturalEnhance,
                    instruction: cleanedInstruction(userInstruction),
                    returnVariants: min(3, capabilities.tasks.photoEdit.returnVariantsMax)
                )
            )
            await progress(.submitted(taskID: created.taskID))
            return try await poller.pollUntilTerminal {
                try await client.fetchTaskStatus(taskID: created.taskID)
            }
        case .ocr, .translateText, .identifySubject, .nutritionEstimate:
            let kind = try visionTaskKind(for: skill)
            let profileID = try visionProfileID(from: capabilities, mode: kind)
            let created = try await client.startVisionTask(
                VisionTaskRequest(
                    profileID: profileID,
                    assetID: uploaded.assetID,
                    mode: kind,
                    instruction: cleanedInstruction(userInstruction),
                    locale: AppLanguage.resolved(storedValue: nil).rawValue
                )
            )
            await progress(.submitted(taskID: created.taskID))
            return try await poller.pollUntilTerminal {
                try await client.fetchTaskStatus(taskID: created.taskID)
            }
        }
    }

    private func cleanedInstruction(_ value: String?) -> String? {
        let trimmed = (value ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    private func visionTaskKind(for skill: KakaSkillID) throws -> VisionTaskKind {
        guard let kind = skill.visionTaskKind else {
            throw ConnectionCheckError.missingVision
        }
        return kind
    }

    private func photoEditProfileID(from capabilities: CapabilitiesResponse) throws -> String {
        guard let profile = capabilities.profiles.first(where: { $0.capabilities.contains("photo_edit") }) else {
            throw ConnectionCheckError.missingPhotoEdit
        }
        return profile.id
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
