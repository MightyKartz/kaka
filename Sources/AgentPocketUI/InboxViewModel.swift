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

public struct InboxSubmissionContext: Equatable, Sendable {
    public let sourceInboxItemID: UUID
    public let sourceApp: String?
    public let sourceSurface: String?
    public let kind: UniversalIntakeKind
    public let contextSelected: Bool

    public init(
        sourceInboxItemID: UUID,
        sourceApp: String?,
        sourceSurface: String?,
        kind: UniversalIntakeKind,
        contextSelected: Bool
    ) {
        self.sourceInboxItemID = sourceInboxItemID
        self.sourceApp = sourceApp
        self.sourceSurface = sourceSurface
        self.kind = kind
        self.contextSelected = contextSelected
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
    @Published public private(set) var completedSubmissionContext: InboxSubmissionContext?
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

    @discardableResult
    public func appendVoiceTranscript(
        _ transcript: String,
        receivedAt: Date = Date(),
        locale: String = Locale.current.identifier
    ) -> KakaInboxItem? {
        let text = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
        guard text.isEmpty == false else {
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .failed("Voice transcript is empty. Record or type a request first.")
            return nil
        }

        let item = KakaInboxItem(
            kind: .text,
            receivedAt: receivedAt,
            sourceApp: "Kaka Voice",
            sourceSurface: "voice",
            locale: locale,
            text: text,
            route: .universalIntake
        )

        do {
            try store.append(item)
            try reload()
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .idle
            return item
        } catch {
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .failed("Could not save voice draft.")
            return nil
        }
    }

    @discardableResult
    public func importClipboard(
        reader: any ClipboardCourierReading = SystemClipboardCourierReader(),
        now: Date = Date(),
        locale: String = Locale.current.identifier
    ) -> KakaInboxItem? {
        let text = reader.readContent().string?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard text.isEmpty == false else {
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .failed("Clipboard is empty. Copy text or a link, then tap Paste.")
            return nil
        }

        let item: KakaInboxItem
        if let url = Self.httpURLString(from: text) {
            item = KakaInboxItem(
                kind: .url,
                receivedAt: now,
                sourceApp: "Clipboard",
                sourceSurface: "paste",
                locale: locale,
                url: url,
                route: .universalIntake
            )
        } else {
            item = KakaInboxItem(
                kind: .text,
                receivedAt: now,
                sourceApp: "Clipboard",
                sourceSurface: "paste",
                locale: locale,
                text: text,
                route: .universalIntake
            )
        }

        do {
            try store.append(item)
            try reload()
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .idle
            return item
        } catch {
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .failed("Could not save pasted item.")
            return nil
        }
    }

    @discardableResult
    public func importFile(
        from url: URL,
        importer: any InboxFileImporting = InboxFileImporter(),
        now: Date = Date(),
        locale: String = Locale.current.identifier
    ) -> KakaInboxItem? {
        do {
            let item = try importer.importFile(from: url, now: now, locale: locale)
            try store.append(item)
            try reload()
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .idle
            return item
        } catch {
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .failed("Could not import that file. Choose a supported PDF or image.")
            return nil
        }
    }

    @discardableResult
    public func discardPendingItem(id: UUID) -> Bool {
        do {
            try store.remove(id: id)
            try reload()
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .idle
            return true
        } catch {
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .failed("Could not discard that inbox item. Try again.")
            return false
        }
    }

    @discardableResult
    public func updateVoiceInstruction(_ instruction: String, for itemID: UUID) -> KakaInboxItem? {
        let note = instruction.trimmingCharacters(in: .whitespacesAndNewlines)
        guard note.isEmpty == false else {
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .failed("Voice instruction is empty. Record or type an instruction first.")
            return nil
        }

        do {
            let existingItems = try store.loadItems()
            guard let existing = existingItems.first(where: { $0.id == itemID })
                ?? items.first(where: { $0.id == itemID }) else {
                completedStatus = nil
                completedSubmissionContext = nil
                progressText = nil
                state = .failed("Inbox item is no longer available.")
                return nil
            }

            let updated = KakaInboxItem(
                id: existing.id,
                kind: existing.kind,
                receivedAt: existing.receivedAt,
                sourceApp: existing.sourceApp,
                sourceSurface: existing.sourceSurface,
                note: note,
                locale: existing.locale,
                preferredProfileID: existing.preferredProfileID,
                text: existing.text,
                url: existing.url,
                fileName: existing.fileName,
                mimeType: existing.mimeType,
                relativeFilePath: existing.relativeFilePath,
                route: existing.route
            )
            try store.addOrUpdate(updated)
            try reload()
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .idle
            return updated
        } catch {
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .failed("Could not save voice instruction.")
            return nil
        }
    }

    @discardableResult
    public func applyInstructionTemplate(
        _ template: InboxInstructionTemplate,
        for itemID: UUID,
        language: AppLanguage = AppLanguage.resolved(storedValue: nil)
    ) -> KakaInboxItem? {
        updateVoiceInstruction(template.instructionText(language: language), for: itemID)
    }

    @discardableResult
    public func clearVoiceInstruction(for itemID: UUID) -> KakaInboxItem? {
        do {
            let existingItems = try store.loadItems()
            guard let existing = existingItems.first(where: { $0.id == itemID })
                ?? items.first(where: { $0.id == itemID }) else {
                completedStatus = nil
                completedSubmissionContext = nil
                progressText = nil
                state = .failed("Inbox item is no longer available.")
                return nil
            }

            let updated = KakaInboxItem(
                id: existing.id,
                kind: existing.kind,
                receivedAt: existing.receivedAt,
                sourceApp: existing.sourceApp,
                sourceSurface: existing.sourceSurface,
                note: nil,
                locale: existing.locale,
                preferredProfileID: existing.preferredProfileID,
                text: existing.text,
                url: existing.url,
                fileName: existing.fileName,
                mimeType: existing.mimeType,
                relativeFilePath: existing.relativeFilePath,
                route: existing.route
            )
            try store.addOrUpdate(updated)
            try reload()
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .idle
            return updated
        } catch {
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .failed("Could not clear voice instruction.")
            return nil
        }
    }

    public func submit(
        _ item: KakaInboxItem,
        connection: StoredConnection?,
        contextSnapshot: ContextSnapshotPayload? = nil
    ) async {
        guard canSubmit(item) else {
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .failed("PDF inbox submission will be available after document skills are connected.")
            return
        }
        guard let connection else {
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .failed("Connect to your local agent before submitting inbox items.")
            return
        }

        do {
            state = .submitting
            progressText = nil
            completedStatus = nil
            completedSubmissionContext = nil
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
                completedSubmissionContext = nil
                progressText = nil
                state = .failed(status.message ?? "The intake task did not complete.")
                return
            }
            completedStatus = status
            completedSubmissionContext = InboxSubmissionContext(
                sourceInboxItemID: item.id,
                sourceApp: item.sourceApp,
                sourceSurface: item.sourceSurface,
                kind: item.kind,
                contextSelected: contextSnapshot != nil
            )
            try store.remove(id: item.id)
            try reload()
            state = .completed
        } catch {
            completedStatus = nil
            completedSubmissionContext = nil
            progressText = nil
            state = .failed(Self.failureMessage(for: error))
        }
    }

    public func canSubmit(_ item: KakaInboxItem) -> Bool {
        switch item.kind {
        case .text, .url, .image, .screenshot, .pdf, .video:
            return true
        }
    }

    public func dismissResult() {
        completedStatus = nil
        completedSubmissionContext = nil
        progressText = nil
        if case .completed = state {
            state = .idle
        }
    }

    public func dismissFailure() {
        progressText = nil
        if case .failed = state {
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

    private static func httpURLString(from text: String) -> String? {
        guard let url = URL(string: text),
              let scheme = url.scheme?.lowercased(),
              (scheme == "http" || scheme == "https"),
              let host = url.host,
              host.isEmpty == false
        else {
            return nil
        }
        return text
    }
}
