import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class InboxViewModelTests: XCTestCase {
    func testLoadsItemsFromStoreNewestFirst() throws {
        let older = KakaInboxItem(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!,
            kind: .url,
            receivedAt: Date(timeIntervalSince1970: 10),
            sourceApp: "Safari",
            url: "https://example.com"
        )
        let newer = KakaInboxItem(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000002")!,
            kind: .text,
            receivedAt: Date(timeIntervalSince1970: 20),
            sourceApp: "Notes",
            text: "Launch notes"
        )
        let viewModel = InboxViewModel(
            store: StubInboxStore(items: [older, newer]),
            submitter: StubUniversalIntakeSubmitter()
        )

        try viewModel.reload()

        XCTAssertEqual(viewModel.items.map(\.id), [newer.id, older.id])
        XCTAssertEqual(viewModel.state, .idle)
    }

    func testSubmitTextItemStoresTerminalResultAndRemovesItem() async throws {
        let item = KakaInboxItem(
            kind: .text,
            sourceApp: "Notes",
            text: "Buy milk and send launch review notes"
        )
        let store = StubInboxStore(items: [item])
        let submitter = StubUniversalIntakeSubmitter(status: try completedUniversalIntakeStatus(kind: .text))
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        await viewModel.submit(item, connection: try storedConnection())

        XCTAssertEqual(submitter.calls.map(\.item.id), [item.id])
        XCTAssertEqual(viewModel.completedStatus?.taskID, "task_intake_123")
        XCTAssertEqual(viewModel.completedStatus?.intake?.kind, .text)
        XCTAssertEqual(store.removedIDs, [item.id])
        XCTAssertEqual(viewModel.items, [])
        XCTAssertEqual(viewModel.state, .completed)
    }

    func testSubmitURLItemPassesSourceMetadataToUniversalSubmitter() async throws {
        let item = KakaInboxItem(
            kind: .url,
            locale: "en-US",
            preferredProfileID: "research-agent",
            url: "https://example.com/launch-review"
        )
        let submitter = StubUniversalIntakeSubmitter(status: try completedUniversalIntakeStatus(kind: .url))
        let viewModel = InboxViewModel(
            store: StubInboxStore(items: [item]),
            submitter: submitter
        )

        await viewModel.submit(item, connection: try storedConnection())

        XCTAssertEqual(submitter.calls.first?.item.kind, .url)
        XCTAssertEqual(submitter.calls.first?.item.locale, "en-US")
        XCTAssertEqual(submitter.calls.first?.item.preferredProfileID, "research-agent")
        XCTAssertEqual(viewModel.completedStatus?.intake?.kind, .url)
    }

    func testSharedImageRoutesToImageIntakePath() async throws {
        let item = KakaInboxItem(
            kind: .image,
            sourceApp: "Photos",
            fileName: "photo.jpg",
            mimeType: "image/jpeg",
            relativeFilePath: "SharedPayloads/photo.jpg"
        )
        let imageSubmitter = StubImageInboxSubmitter(status: try completedImageIntakeStatus())
        let universalSubmitter = StubUniversalIntakeSubmitter(status: try completedUniversalIntakeStatus(kind: .image))
        let viewModel = InboxViewModel(
            store: StubInboxStore(items: [item]),
            submitter: universalSubmitter,
            imageSubmitter: imageSubmitter
        )

        await viewModel.submit(item, connection: try storedConnection())

        XCTAssertEqual(imageSubmitter.calls.map(\.item.id), [item.id])
        XCTAssertTrue(universalSubmitter.calls.isEmpty)
        XCTAssertEqual(viewModel.completedStatus?.resultType, "image_intake")
        XCTAssertEqual(viewModel.completedStatus?.imageIntake?.suggestions.first?.skill, .photoEnhance)
    }

    func testPDFItemSubmitsThroughUniversalIntakePath() async throws {
        let item = KakaInboxItem(
            kind: .pdf,
            sourceApp: "Files",
            fileName: "brief.pdf",
            mimeType: "application/pdf",
            relativeFilePath: "SharedPayloads/brief.pdf"
        )
        let submitter = StubUniversalIntakeSubmitter(status: try completedUniversalIntakeStatus(kind: .pdf))
        let imageSubmitter = StubImageInboxSubmitter(status: try completedImageIntakeStatus())
        let store = StubInboxStore(items: [item])
        let viewModel = InboxViewModel(
            store: store,
            submitter: submitter,
            imageSubmitter: imageSubmitter
        )

        XCTAssertTrue(viewModel.canSubmit(item))

        await viewModel.submit(item, connection: try storedConnection())

        XCTAssertEqual(submitter.calls.map(\.item.id), [item.id])
        XCTAssertTrue(imageSubmitter.calls.isEmpty)
        XCTAssertEqual(store.removedIDs, [item.id])
        XCTAssertEqual(viewModel.completedStatus?.intake?.kind, .pdf)
        XCTAssertEqual(viewModel.state, .completed)
    }

    func testUniversalSubmitReceivesSelectedContextSnapshot() async throws {
        let item = KakaInboxItem(
            kind: .text,
            sourceApp: "Notes",
            text: "Buy milk and send launch review notes"
        )
        let snapshot = ContextSnapshotPayload(
            timestamp: "2026-06-05T09:30:00Z",
            timezone: "Asia/Shanghai",
            locale: "zh-Hans",
            sourceSurface: "share_extension"
        )
        let submitter = StubUniversalIntakeSubmitter(status: try completedUniversalIntakeStatus(kind: .text))
        let viewModel = InboxViewModel(
            store: StubInboxStore(items: [item]),
            submitter: submitter
        )

        await viewModel.submit(item, connection: try storedConnection(), contextSnapshot: snapshot)

        XCTAssertEqual(submitter.calls.first?.contextSnapshot, snapshot)
        XCTAssertEqual(viewModel.state, .completed)
    }

    func testFailedTerminalStatusDoesNotSetCompletedStatus() async throws {
        let item = KakaInboxItem(kind: .text, text: "Launch notes")
        let store = StubInboxStore(items: [item])
        let viewModel = InboxViewModel(
            store: store,
            submitter: StubUniversalIntakeSubmitter(status: try failedUniversalIntakeStatus())
        )

        await viewModel.submit(item, connection: try storedConnection())

        XCTAssertEqual(store.removedIDs, [])
        XCTAssertNil(viewModel.completedStatus)
        XCTAssertEqual(viewModel.state, .failed("Runtime rejected the item."))
    }

    func testSubmitWithoutConnectionKeepsItemAndFailsClearly() async throws {
        let item = KakaInboxItem(kind: .text, text: "Launch notes")
        let store = StubInboxStore(items: [item])
        let viewModel = InboxViewModel(
            store: store,
            submitter: StubUniversalIntakeSubmitter(status: try completedUniversalIntakeStatus(kind: .text))
        )

        await viewModel.submit(item, connection: nil)

        XCTAssertEqual(store.removedIDs, [])
        XCTAssertEqual(viewModel.state, .failed("Connect to your local agent before submitting inbox items."))
    }

    func testOversizedPDFSubmitFailureShowsRecoveryMessage() async throws {
        let item = KakaInboxItem(
            kind: .pdf,
            fileName: "large.pdf",
            mimeType: "application/pdf",
            relativeFilePath: "SharedPayloads/large.pdf"
        )
        let store = StubInboxStore(items: [item])
        let viewModel = InboxViewModel(
            store: store,
            submitter: ThrowingUniversalIntakeSubmitter(error: FileInboxDocumentPayloadLoader.LoadError.exceedsMaxUploadSize)
        )

        await viewModel.submit(item, connection: try storedConnection())

        XCTAssertEqual(store.removedIDs, [])
        XCTAssertEqual(viewModel.state, .failed("PDF is too large. Share a PDF under 25 MB."))
    }
}

private final class StubInboxStore: KakaInboxStoring, @unchecked Sendable {
    var items: [KakaInboxItem]
    var removedIDs: [UUID] = []
    var didClear = false

    init(items: [KakaInboxItem]) {
        self.items = items
    }

    func loadItems() throws -> [KakaInboxItem] {
        items
    }

    func addOrUpdate(_ item: KakaInboxItem) throws {
        items.removeAll { $0.id == item.id }
        items.append(item)
    }

    func append(_ item: KakaInboxItem) throws {
        try addOrUpdate(item)
    }

    func remove(id: UUID) throws {
        removedIDs.append(id)
        items.removeAll { $0.id == id }
    }

    func clear() throws {
        didClear = true
        items = []
    }
}

private final class StubUniversalIntakeSubmitter: UniversalIntakeSubmitting, @unchecked Sendable {
    struct Call {
        let item: KakaInboxItem
        let connection: StoredConnection
        let contextSnapshot: ContextSnapshotPayload?
    }

    let status: TaskStatusResponse
    private(set) var calls: [Call] = []

    init(status: TaskStatusResponse? = nil) {
        self.status = status ?? (try! completedUniversalIntakeStatus(kind: .text))
    }

    func submit(
        item: KakaInboxItem,
        connection: StoredConnection,
        contextSnapshot: ContextSnapshotPayload?,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        calls.append(Call(item: item, connection: connection, contextSnapshot: contextSnapshot))
        await progress(.startingTask)
        await progress(.submitted(taskID: status.taskID))
        return status
    }
}

private struct ThrowingUniversalIntakeSubmitter: UniversalIntakeSubmitting {
    let error: Error

    func submit(
        item: KakaInboxItem,
        connection: StoredConnection,
        contextSnapshot: ContextSnapshotPayload?,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        throw error
    }
}

private final class StubImageInboxSubmitter: ImageInboxSubmitting, @unchecked Sendable {
    struct Call {
        let item: KakaInboxItem
        let connection: StoredConnection
    }

    let status: TaskStatusResponse
    private(set) var calls: [Call] = []

    init(status: TaskStatusResponse) {
        self.status = status
    }

    func submit(
        item: KakaInboxItem,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        calls.append(Call(item: item, connection: connection))
        await progress(.uploading)
        await progress(.startingTask)
        await progress(.submitted(taskID: status.taskID))
        return status
    }
}

private func completedUniversalIntakeStatus(kind: UniversalIntakeKind) throws -> TaskStatusResponse {
    let data = """
    {
      "task_id":"task_intake_123",
      "status":"completed",
      "progress":1.0,
      "result_type":"intake",
      "intake":{
        "kind":"\(kind.rawValue)",
        "title":"Shared item ready",
        "summary":"Kaka received the shared item.",
        "suggestions":[
          {"id":"summarize","label":"Summarize","requires_confirmation":false,"is_available":true}
        ]
      }
    }
    """.data(using: .utf8)!
    return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
}

private func completedImageIntakeStatus() throws -> TaskStatusResponse {
    let data = """
    {
      "task_id":"task_image_intake_123",
      "status":"completed",
      "progress":1.0,
      "result_type":"image_intake",
      "image_intake":{
        "image_type":"photo",
        "title":"已看到照片",
        "summary":"我可以帮你优化这张照片。",
        "confidence":0.62,
        "suggestions":[
          {"skill":"photo_enhance","title":"大师级优化","reason":"适合自然增强。","confidence":0.62,"is_available":true}
        ]
      }
    }
    """.data(using: .utf8)!
    return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
}

private func failedUniversalIntakeStatus() throws -> TaskStatusResponse {
    let data = """
    {
      "task_id":"task_intake_failed",
      "status":"failed",
      "progress":1.0,
      "message":"Runtime rejected the item.",
      "result_type":"intake"
    }
    """.data(using: .utf8)!
    return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
}

private func storedConnection() throws -> StoredConnection {
    StoredConnection(
        endpoint: try AgentEndpoint(rawURL: "http://127.0.0.1:8765"),
        displayName: "Test Runtime",
        runtime: "hermes",
        runtimeVersion: "2026.5.16",
        mobileToken: "dev-mobile-token",
        tokenExpiresAt: nil
    )
}
