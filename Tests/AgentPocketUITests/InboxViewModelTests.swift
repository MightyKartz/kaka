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

    func testSubmitTextItemStoresCompletedSubmissionContextForRecallProvenance() async throws {
        let item = KakaInboxItem(
            kind: .text,
            receivedAt: Date(timeIntervalSince1970: 70),
            sourceApp: "Clipboard",
            sourceSurface: "paste",
            text: "Summarize this copied note.",
            route: .universalIntake
        )
        let snapshot = ContextSnapshotPayload(
            timestamp: "2026-06-05T09:30:00Z",
            timezone: "Asia/Shanghai",
            locale: "zh-Hans",
            sourceSurface: "paste"
        )
        let store = StubInboxStore(items: [item])
        let submitter = StubUniversalIntakeSubmitter(status: try completedUniversalIntakeStatus(kind: .text))
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        await viewModel.submit(item, connection: try storedConnection(), contextSnapshot: snapshot)

        XCTAssertEqual(viewModel.completedSubmissionContext?.sourceInboxItemID, item.id)
        XCTAssertEqual(viewModel.completedSubmissionContext?.sourceApp, "Clipboard")
        XCTAssertEqual(viewModel.completedSubmissionContext?.sourceSurface, "paste")
        XCTAssertEqual(viewModel.completedSubmissionContext?.kind, .text)
        XCTAssertEqual(viewModel.completedSubmissionContext?.contextSelected, true)
        XCTAssertEqual(viewModel.completedStatus?.taskID, "task_intake_123")
    }

    func testFailedSubmitClearsCompletedSubmissionContext() async throws {
        let item = KakaInboxItem(kind: .text, text: "Draft", route: .universalIntake)
        let store = StubInboxStore(items: [item])
        let viewModel = InboxViewModel(
            store: store,
            submitter: ThrowingUniversalIntakeSubmitter(error: URLError(.cannotConnectToHost))
        )

        await viewModel.submit(item, connection: try storedConnection())

        XCTAssertNil(viewModel.completedSubmissionContext)
        XCTAssertNil(viewModel.completedStatus)
        guard case .failed = viewModel.state else {
            return XCTFail("Expected failed state.")
        }
    }

    func testDismissResultClearsCompletedSubmissionContext() async throws {
        let item = KakaInboxItem(
            kind: .text,
            sourceApp: "Kaka Voice",
            sourceSurface: "voice",
            text: "Draft",
            route: .universalIntake
        )
        let store = StubInboxStore(items: [item])
        let submitter = StubUniversalIntakeSubmitter(status: try completedUniversalIntakeStatus(kind: .text))
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        await viewModel.submit(item, connection: try storedConnection())
        XCTAssertEqual(viewModel.completedSubmissionContext?.sourceSurface, "voice")

        viewModel.dismissResult()

        XCTAssertNil(viewModel.completedSubmissionContext)
        XCTAssertNil(viewModel.completedStatus)
        XCTAssertEqual(viewModel.state, .idle)
    }

    func testDismissFailureClearsFailedStateWithoutChangingQueue() async throws {
        let item = KakaInboxItem(kind: .text, text: "Keep this")
        let store = StubInboxStore(items: [item])
        let viewModel = InboxViewModel(
            store: store,
            submitter: StubUniversalIntakeSubmitter()
        )
        try viewModel.reload()
        await viewModel.submit(item, connection: nil)

        viewModel.dismissFailure()

        XCTAssertEqual(viewModel.items.map(\.id), [item.id])
        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertNil(viewModel.completedStatus)
        XCTAssertNil(viewModel.completedSubmissionContext)
        XCTAssertNil(viewModel.progressText)
    }

    func testFailedTerminalStatusDoesNotSetCompletedStatus() async throws {
        let item = KakaInboxItem(kind: .text, text: "Launch notes")
        let store = StubInboxStore(items: [item])
        let viewModel = InboxViewModel(
            store: store,
            submitter: StubUniversalIntakeSubmitter(status: try failedUniversalIntakeStatus())
        )
        try viewModel.reload()

        await viewModel.submit(item, connection: try storedConnection())

        XCTAssertEqual(store.removedIDs, [])
        XCTAssertNil(viewModel.completedStatus)
        XCTAssertEqual(viewModel.state, .failed("Runtime rejected the item."))
    }

    func testFailedTerminalStatusClearsStaleProgressAndKeepsPendingItem() async throws {
        let item = KakaInboxItem(kind: .text, text: "Launch notes")
        let store = StubInboxStore(items: [item])
        let viewModel = InboxViewModel(
            store: store,
            submitter: StubUniversalIntakeSubmitter(status: try failedUniversalIntakeStatus())
        )
        try viewModel.reload()

        await viewModel.submit(item, connection: try storedConnection())

        XCTAssertEqual(viewModel.items.map(\.id), [item.id])
        XCTAssertNil(viewModel.progressText)
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

    func testSubmitFailureClearsStaleProgressAndKeepsPendingItem() async throws {
        let item = KakaInboxItem(kind: .text, text: "Retry later")
        let store = StubInboxStore(items: [item])
        let submitter = ProgressThenThrowingUniversalIntakeSubmitter(error: URLError(.timedOut))
        let viewModel = InboxViewModel(store: store, submitter: submitter)
        try viewModel.reload()

        await viewModel.submit(item, connection: try storedConnection())

        XCTAssertEqual(viewModel.items.map(\.id), [item.id])
        XCTAssertNil(viewModel.progressText)
        XCTAssertEqual(viewModel.state, .failed("Your local agent is offline. Check the network and try again."))
    }

    func testAppendVoiceTranscriptCreatesPendingTextItemWithoutSubmitting() throws {
        let store = StubInboxStore(items: [])
        let submitter = StubUniversalIntakeSubmitter()
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        let item = try XCTUnwrap(viewModel.appendVoiceTranscript(
            "  Summarize this receipt before I send it.  ",
            receivedAt: Date(timeIntervalSince1970: 1_800_000_010),
            locale: "en-US"
        ))

        XCTAssertEqual(item.kind, .text)
        XCTAssertEqual(item.text, "Summarize this receipt before I send it.")
        XCTAssertEqual(item.sourceApp, "Kaka Voice")
        XCTAssertEqual(item.sourceSurface, "voice")
        XCTAssertEqual(item.locale, "en-US")
        XCTAssertEqual(item.route, .universalIntake)
        XCTAssertEqual(viewModel.items.map(\.id), [item.id])
        XCTAssertTrue(submitter.calls.isEmpty)
        XCTAssertEqual(viewModel.state, .idle)
    }

    func testAppendVoiceTranscriptRejectsEmptyTranscriptWithoutSubmitting() {
        let store = StubInboxStore(items: [])
        let submitter = StubUniversalIntakeSubmitter()
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        let item = viewModel.appendVoiceTranscript("   \n  ")

        XCTAssertNil(item)
        XCTAssertTrue(store.items.isEmpty)
        XCTAssertTrue(submitter.calls.isEmpty)
        XCTAssertEqual(viewModel.state, .failed("Voice transcript is empty. Record or type a request first."))
    }

    func testAppendVoiceTranscriptReloadsNewestFirst() throws {
        let older = KakaInboxItem(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000010")!,
            kind: .text,
            receivedAt: Date(timeIntervalSince1970: 10),
            sourceApp: "Notes",
            text: "Older note"
        )
        let store = StubInboxStore(items: [older])
        let viewModel = InboxViewModel(store: store, submitter: StubUniversalIntakeSubmitter())

        let item = try XCTUnwrap(viewModel.appendVoiceTranscript(
            "New voice draft",
            receivedAt: Date(timeIntervalSince1970: 20),
            locale: "zh-Hans"
        ))

        XCTAssertEqual(viewModel.items.map(\.id), [item.id, older.id])
    }

    func testImportClipboardURLCreatesPendingPasteLinkWithoutSubmitting() throws {
        let store = StubInboxStore(items: [])
        let submitter = StubUniversalIntakeSubmitter()
        let reader = StubClipboardCourierReader(string: "  https://example.com/launch?ref=kaka  ")
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        let item = try XCTUnwrap(viewModel.importClipboard(
            reader: reader,
            now: Date(timeIntervalSince1970: 1_800_000_020),
            locale: "en-US"
        ))

        XCTAssertEqual(reader.readCount, 1)
        XCTAssertEqual(item.kind, .url)
        XCTAssertEqual(item.url, "https://example.com/launch?ref=kaka")
        XCTAssertNil(item.text)
        XCTAssertEqual(item.sourceApp, "Clipboard")
        XCTAssertEqual(item.sourceSurface, "paste")
        XCTAssertEqual(item.locale, "en-US")
        XCTAssertEqual(item.route, .universalIntake)
        XCTAssertEqual(item.receivedAt, Date(timeIntervalSince1970: 1_800_000_020))
        XCTAssertEqual(viewModel.items.map(\.id), [item.id])
        XCTAssertTrue(submitter.calls.isEmpty)
        XCTAssertEqual(viewModel.state, .idle)
    }

    func testImportClipboardTextCreatesPendingPasteTextWithoutSubmitting() throws {
        let store = StubInboxStore(items: [])
        let submitter = StubUniversalIntakeSubmitter()
        let reader = StubClipboardCourierReader(string: "  Rewrite this message in a calmer tone.  ")
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        let item = try XCTUnwrap(viewModel.importClipboard(
            reader: reader,
            now: Date(timeIntervalSince1970: 1_800_000_030),
            locale: "zh-Hans"
        ))

        XCTAssertEqual(reader.readCount, 1)
        XCTAssertEqual(item.kind, .text)
        XCTAssertEqual(item.text, "Rewrite this message in a calmer tone.")
        XCTAssertNil(item.url)
        XCTAssertEqual(item.sourceApp, "Clipboard")
        XCTAssertEqual(item.sourceSurface, "paste")
        XCTAssertEqual(item.locale, "zh-Hans")
        XCTAssertEqual(item.route, .universalIntake)
        XCTAssertEqual(viewModel.items.map(\.id), [item.id])
        XCTAssertTrue(submitter.calls.isEmpty)
        XCTAssertEqual(viewModel.state, .idle)
    }

    func testImportClipboardEmptyContentFailsWithoutReadingAgainOrSubmitting() {
        let store = StubInboxStore(items: [])
        let submitter = StubUniversalIntakeSubmitter()
        let reader = StubClipboardCourierReader(string: "   \n  ")
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        let item = viewModel.importClipboard(reader: reader)

        XCTAssertNil(item)
        XCTAssertEqual(reader.readCount, 1)
        XCTAssertTrue(store.items.isEmpty)
        XCTAssertTrue(submitter.calls.isEmpty)
        XCTAssertEqual(viewModel.state, .failed("Clipboard is empty. Copy text or a link, then tap Paste."))
    }

    func testImportFileAppendsPendingItemWithoutSubmitting() throws {
        let directory = try temporaryDirectory()
        let source = directory.appendingPathComponent("brief.pdf")
        try Data("%PDF".utf8).write(to: source)
        let store = StubInboxStore(items: [])
        let submitter = StubUniversalIntakeSubmitter()
        let importer = InboxFileImporter(
            containerURL: directory,
            uuidProvider: { UUID(uuidString: "00000000-0000-0000-0000-00000000f140")! }
        )
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        let item = try XCTUnwrap(viewModel.importFile(
            from: source,
            importer: importer,
            now: Date(timeIntervalSince1970: 1_800_000_002),
            locale: "en-US"
        ))

        XCTAssertEqual(item.sourceSurface, "file_picker")
        XCTAssertEqual(item.sourceApp, "Files")
        XCTAssertEqual(item.kind, .pdf)
        XCTAssertEqual(item.route, .universalIntake)
        XCTAssertEqual(viewModel.items.map(\.id), [item.id])
        XCTAssertNil(viewModel.completedStatus)
        XCTAssertNil(viewModel.completedSubmissionContext)
        XCTAssertTrue(submitter.calls.isEmpty)
        XCTAssertEqual(viewModel.state, .idle)
    }

    func testImportFileFailureDoesNotAppendOrSubmit() throws {
        let directory = try temporaryDirectory()
        let source = directory.appendingPathComponent("notes.txt")
        try Data("not supported here".utf8).write(to: source)
        let store = StubInboxStore(items: [])
        let submitter = StubUniversalIntakeSubmitter()
        let importer = InboxFileImporter(containerURL: directory)
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        let item = viewModel.importFile(from: source, importer: importer)

        XCTAssertNil(item)
        XCTAssertTrue(viewModel.items.isEmpty)
        XCTAssertTrue(store.items.isEmpty)
        XCTAssertTrue(submitter.calls.isEmpty)
        XCTAssertEqual(viewModel.state, .failed("Could not import that file. Choose a supported PDF or image."))
    }

    func testDiscardPendingItemRemovesItemWithoutSubmittingOrRecall() throws {
        let kept = KakaInboxItem(
            id: UUID(uuidString: "00000000-0000-0000-0000-00000000d139")!,
            kind: .text,
            receivedAt: Date(timeIntervalSince1970: 20),
            sourceApp: "Notes",
            text: "Keep me"
        )
        let discarded = KakaInboxItem(
            id: UUID(uuidString: "00000000-0000-0000-0000-00000000d140")!,
            kind: .pdf,
            receivedAt: Date(timeIntervalSince1970: 30),
            sourceApp: "Files",
            sourceSurface: "file_picker",
            fileName: "discard.pdf",
            mimeType: "application/pdf",
            relativeFilePath: "SharedPayloads/discard.pdf",
            route: .universalIntake
        )
        let store = StubInboxStore(items: [kept, discarded])
        let submitter = StubUniversalIntakeSubmitter()
        let viewModel = InboxViewModel(store: store, submitter: submitter)
        try viewModel.reload()

        let didDiscard = viewModel.discardPendingItem(id: discarded.id)

        XCTAssertTrue(didDiscard)
        XCTAssertEqual(store.removedIDs, [discarded.id])
        XCTAssertEqual(viewModel.items.map(\.id), [kept.id])
        XCTAssertNil(viewModel.completedStatus)
        XCTAssertNil(viewModel.completedSubmissionContext)
        XCTAssertNil(viewModel.progressText)
        XCTAssertTrue(submitter.calls.isEmpty)
        XCTAssertEqual(viewModel.state, .idle)
    }

    func testDiscardPendingItemFailureLeavesQueueAndReportsClearly() throws {
        let item = KakaInboxItem(kind: .text, text: "Keep me")
        let store = ThrowingRemoveInboxStore(items: [item])
        let viewModel = InboxViewModel(store: store, submitter: StubUniversalIntakeSubmitter())
        try viewModel.reload()

        let didDiscard = viewModel.discardPendingItem(id: item.id)

        XCTAssertFalse(didDiscard)
        XCTAssertEqual(viewModel.items.map(\.id), [item.id])
        XCTAssertEqual(viewModel.state, .failed("Could not discard that inbox item. Try again."))
    }

    func testUpdateVoiceInstructionAddsNoteWithoutSubmitting() throws {
        let item = KakaInboxItem(
            kind: .url,
            receivedAt: Date(timeIntervalSince1970: 20),
            sourceApp: "Safari",
            url: "https://example.com"
        )
        let store = StubInboxStore(items: [item])
        let submitter = StubUniversalIntakeSubmitter()
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        let updated = try XCTUnwrap(viewModel.updateVoiceInstruction(
            "  Summarize and extract action items  ",
            for: item.id
        ))

        XCTAssertEqual(updated.id, item.id)
        XCTAssertEqual(updated.note, "Summarize and extract action items")
        XCTAssertEqual(updated.url, item.url)
        XCTAssertEqual(viewModel.items.first?.note, "Summarize and extract action items")
        XCTAssertTrue(submitter.calls.isEmpty)
        XCTAssertEqual(viewModel.state, .idle)
    }

    func testUpdateVoiceInstructionRejectsEmptyInstructionWithoutChangingItem() {
        let item = KakaInboxItem(kind: .text, note: "Existing", text: "Launch notes")
        let store = StubInboxStore(items: [item])
        let viewModel = InboxViewModel(store: store, submitter: StubUniversalIntakeSubmitter())

        let updated = viewModel.updateVoiceInstruction("   \n  ", for: item.id)

        XCTAssertNil(updated)
        XCTAssertEqual(store.items.first?.note, "Existing")
        XCTAssertEqual(viewModel.state, .failed("Voice instruction is empty. Record or type an instruction first."))
    }

    func testUpdateVoiceInstructionFailsWhenInboxItemIsMissing() {
        let store = StubInboxStore(items: [])
        let viewModel = InboxViewModel(store: store, submitter: StubUniversalIntakeSubmitter())

        let updated = viewModel.updateVoiceInstruction("Summarize this.", for: UUID())

        XCTAssertNil(updated)
        XCTAssertEqual(viewModel.state, .failed("Inbox item is no longer available."))
    }

    func testClearVoiceInstructionRemovesNoteWithoutSubmitting() throws {
        let item = KakaInboxItem(
            kind: .url,
            receivedAt: Date(timeIntervalSince1970: 40),
            sourceApp: "Safari",
            note: "Summarize first.",
            url: "https://example.com"
        )
        let store = StubInboxStore(items: [item])
        let submitter = StubUniversalIntakeSubmitter()
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        let updated = try XCTUnwrap(viewModel.clearVoiceInstruction(for: item.id))

        XCTAssertEqual(updated.id, item.id)
        XCTAssertNil(updated.note)
        XCTAssertEqual(updated.url, item.url)
        XCTAssertNil(viewModel.items.first?.note)
        XCTAssertTrue(submitter.calls.isEmpty)
        XCTAssertEqual(viewModel.state, .idle)
    }

    func testClearVoiceInstructionFailsWhenInboxItemIsMissing() {
        let store = StubInboxStore(items: [])
        let viewModel = InboxViewModel(store: store, submitter: StubUniversalIntakeSubmitter())

        let updated = viewModel.clearVoiceInstruction(for: UUID())

        XCTAssertNil(updated)
        XCTAssertEqual(viewModel.state, .failed("Inbox item is no longer available."))
    }

    func testApplyInstructionTemplateSetsDeterministicNoteWithoutSubmitting() throws {
        let item = KakaInboxItem(
            kind: .url,
            receivedAt: Date(timeIntervalSince1970: 50),
            sourceApp: "Safari",
            note: "Old instruction",
            url: "https://example.com"
        )
        let store = StubInboxStore(items: [item])
        let submitter = StubUniversalIntakeSubmitter()
        let viewModel = InboxViewModel(store: store, submitter: submitter)

        let updated = try XCTUnwrap(viewModel.applyInstructionTemplate(.extractActions, for: item.id, language: .english))

        XCTAssertEqual(updated.id, item.id)
        XCTAssertEqual(updated.note, "Extract action items, owners, and dates from this item.")
        XCTAssertEqual(updated.url, item.url)
        XCTAssertEqual(viewModel.items.first?.note, "Extract action items, owners, and dates from this item.")
        XCTAssertTrue(submitter.calls.isEmpty)
        XCTAssertEqual(viewModel.state, .idle)
    }

    func testApplyInstructionTemplateUsesLocalizedInstructionText() throws {
        let item = KakaInboxItem(kind: .text, receivedAt: Date(timeIntervalSince1970: 60), text: "Launch notes")
        let viewModel = InboxViewModel(store: StubInboxStore(items: [item]), submitter: StubUniversalIntakeSubmitter())

        let updated = try XCTUnwrap(viewModel.applyInstructionTemplate(.summarize, for: item.id, language: .chinese))

        XCTAssertEqual(updated.note, "总结这个项目并突出关键要点。")
        XCTAssertEqual(viewModel.state, .idle)
    }
}

@MainActor
private final class StubClipboardCourierReader: ClipboardCourierReading, @unchecked Sendable {
    private let content: ClipboardCourierContent
    private(set) var readCount = 0

    init(string: String?) {
        self.content = ClipboardCourierContent(string: string)
    }

    func readContent() -> ClipboardCourierContent {
        readCount += 1
        return content
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

private final class ThrowingRemoveInboxStore: KakaInboxStoring, @unchecked Sendable {
    var items: [KakaInboxItem]

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
        throw CocoaError(.fileWriteUnknown)
    }

    func clear() throws {
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

private struct ProgressThenThrowingUniversalIntakeSubmitter: UniversalIntakeSubmitting {
    let error: Error

    func submit(
        item: KakaInboxItem,
        connection: StoredConnection,
        contextSnapshot: ContextSnapshotPayload?,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        await progress(.uploading)
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

private func temporaryDirectory() throws -> URL {
    let url = FileManager.default.temporaryDirectory
        .appendingPathComponent("InboxViewModelTests-\(UUID().uuidString)", isDirectory: true)
    try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
    return url
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
