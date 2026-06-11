import AgentPocketCore
import Foundation

public protocol UniversalIntakeSubmitting: Sendable {
    func submit(
        item: KakaInboxItem,
        connection: StoredConnection,
        contextSnapshot: ContextSnapshotPayload?,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse
}

public extension UniversalIntakeSubmitting {
    func submit(
        item: KakaInboxItem,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        try await submit(
            item: item,
            connection: connection,
            contextSnapshot: nil,
            progress: progress
        )
    }
}

public struct MobileBridgeUniversalIntakeSubmitter: UniversalIntakeSubmitting {
    private let session: URLSession?
    private let poller: TaskPoller
    private let documentLoader: any InboxDocumentPayloadLoading

    public init(
        session: URLSession? = nil,
        poller: TaskPoller = TaskPoller(),
        documentLoader: any InboxDocumentPayloadLoading = FileInboxDocumentPayloadLoader()
    ) {
        self.session = session
        self.poller = poller
        self.documentLoader = documentLoader
    }

    public func submit(
        item: KakaInboxItem,
        connection: StoredConnection,
        contextSnapshot: ContextSnapshotPayload?,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        let client = MobileBridgeHTTPClient(
            connection: connection,
            session: session
        )
        let capabilities = try await client.fetchCapabilities()
        let profileID = try intakeProfileID(for: item, from: capabilities)
        let submittedContextSnapshot = capabilities.tasks.intake?.supportsContextSnapshot == true
            ? contextSnapshot
            : nil
        let assetID: String?

        if item.kind == .pdf {
            await progress(.uploading)
            let upload = try documentLoader.preparedUpload(for: item)
            let uploaded = try await client.uploadAsset(upload)
            assetID = uploaded.assetID
        } else {
            assetID = nil
        }

        await progress(.startingTask)
        let created = try await client.startUniversalIntakeTask(
            UniversalIntakeTaskRequest(
                kind: item.kind,
                assetID: assetID,
                text: item.text,
                url: item.url,
                note: item.note,
                locale: item.locale ?? AppLanguage.resolved(storedValue: nil).rawValue,
                preferredProfileID: profileID,
                sourceApp: item.sourceApp,
                receivedAt: item.receivedAt,
                source: IntakeSource(surface: item.sourceSurface, hostApp: item.sourceApp),
                contextSnapshot: submittedContextSnapshot,
                userInstruction: item.note
            )
        )

        await progress(.submitted(taskID: created.taskID))
        return try await poller.pollUntilTerminal {
            try await client.fetchTaskStatus(taskID: created.taskID)
        }
    }

    private func intakeProfileID(for item: KakaInboxItem, from capabilities: CapabilitiesResponse) throws -> String {
        guard let intake = capabilities.tasks.intake,
              intake.acceptedTypes.contains(item.kind) else {
            throw ConnectionCheckError.missingIntake
        }
        if let preferred = item.preferredProfileID,
           capabilities.profiles.contains(where: { $0.id == preferred }) {
            return preferred
        }
        guard let profile = capabilities.profiles.first(where: { $0.capabilities.contains("intake") }) else {
            throw ConnectionCheckError.missingIntake
        }
        return profile.id
    }
}
