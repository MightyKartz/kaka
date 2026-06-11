import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class RecallActionViewModelTests: XCTestCase {
    func testRememberRequiresVisibleConfirmationBeforeSubmitting() async throws {
        let performer = StubRecallActionPerformer(response: .rememberedFixture())
        let viewModel = RecallActionViewModel(performer: performer)

        await viewModel.perform(
            .remember,
            sourceTaskID: "task_123",
            userVisibleSummary: "Remember that launch summaries should be in Chinese.",
            connection: try storedConnection()
        )

        XCTAssertEqual(performer.calls, [])
        guard case .confirming(let confirmation) = viewModel.state else {
            return XCTFail("Remember should enter visible confirmation before submission.")
        }
        XCTAssertEqual(confirmation.action, .remember)
        XCTAssertEqual(confirmation.userVisibleSummary, "Remember that launch summaries should be in Chinese.")

        await viewModel.confirmPendingAction(connection: try storedConnection())

        XCTAssertEqual(performer.calls.map(\.action), [.remember])
        XCTAssertEqual(performer.calls.map(\.sourceTaskID), ["task_123"])
        XCTAssertEqual(viewModel.state, .succeeded(.rememberedFixture()))
    }

    func testForgetRequiresVisibleConfirmationBeforeSubmitting() async throws {
        let inboxItemID = UUID(uuidString: "12345678-1234-1234-1234-1234567890AB")!
        let performer = StubRecallActionPerformer(response: .forgottenFixture())
        let viewModel = RecallActionViewModel(performer: performer)

        await viewModel.perform(
            .forget,
            sourceInboxItemID: inboxItemID,
            userVisibleSummary: "Forget the saved launch language preference.",
            connection: try storedConnection()
        )

        XCTAssertEqual(performer.calls, [])
        guard case .confirming(let confirmation) = viewModel.state else {
            return XCTFail("Forget should enter visible confirmation before submission.")
        }
        XCTAssertEqual(confirmation.action, .forget)
        XCTAssertEqual(confirmation.sourceInboxItemID, inboxItemID)

        await viewModel.confirmPendingAction(connection: try storedConnection())

        XCTAssertEqual(performer.calls.map(\.action), [.forget])
        XCTAssertEqual(performer.calls.map(\.sourceInboxItemID), [inboxItemID])
        XCTAssertEqual(viewModel.state, .succeeded(.forgottenFixture()))
    }

    func testUseOnceSubmitsImmediatelyWithoutConfirmationOrPersistence() async throws {
        let performer = StubRecallActionPerformer(response: .usedOnceFixture())
        let viewModel = RecallActionViewModel(performer: performer)

        await viewModel.perform(
            .useOnce,
            sourceTaskID: "task_123",
            userVisibleSummary: "Use this detail for the current answer only.",
            connection: try storedConnection()
        )

        XCTAssertEqual(performer.calls.map(\.action), [.useOnce])
        XCTAssertEqual(performer.calls.map(\.userVisibleSummary), ["Use this detail for the current answer only."])
        XCTAssertEqual(viewModel.state, .succeeded(.usedOnceFixture()))
        XCTAssertNil(performer.calls.first?.persistedItemID)
    }

    func testRecallActionSubmitsTaskAndInboxProvenanceTogether() async throws {
        let inboxItemID = UUID(uuidString: "12345678-1234-1234-1234-1234567890AB")!
        let performer = StubRecallActionPerformer(response: .usedOnceFixture())
        let viewModel = RecallActionViewModel(performer: performer)

        await viewModel.perform(
            .useOnce,
            sourceTaskID: "task_123",
            sourceInboxItemID: inboxItemID,
            userVisibleSummary: "Use this result provenance for the current answer.",
            connection: try storedConnection()
        )

        XCTAssertEqual(performer.calls.map(\.action), [.useOnce])
        XCTAssertEqual(performer.calls.map(\.sourceTaskID), ["task_123"])
        XCTAssertEqual(performer.calls.map(\.sourceInboxItemID), [inboxItemID])
    }

    func testCancelConfirmationDoesNotSubmitPendingRemember() async throws {
        let performer = StubRecallActionPerformer(response: .rememberedFixture())
        let viewModel = RecallActionViewModel(performer: performer)

        await viewModel.perform(
            .remember,
            sourceTaskID: "task_123",
            userVisibleSummary: "Remember this after I confirm it.",
            connection: try storedConnection()
        )
        viewModel.cancelConfirmation()

        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertTrue(performer.calls.isEmpty)
    }

    func testBlankSummaryFailsBeforeConfirmation() async throws {
        let performer = StubRecallActionPerformer(response: .rememberedFixture())
        let viewModel = RecallActionViewModel(performer: performer)

        await viewModel.perform(
            .remember,
            sourceTaskID: "task_123",
            userVisibleSummary: "   ",
            connection: try storedConnection()
        )

        XCTAssertEqual(viewModel.state, .failed(message: "Add a visible summary before using Recall."))
        XCTAssertTrue(performer.calls.isEmpty)
    }

    func testMissingConnectionFailsBeforeConfirmation() async {
        let performer = StubRecallActionPerformer(response: .rememberedFixture())
        let viewModel = RecallActionViewModel(performer: performer)

        await viewModel.perform(
            .forget,
            sourceTaskID: "task_123",
            userVisibleSummary: "Forget this item.",
            connection: nil
        )

        XCTAssertEqual(viewModel.state, .failed(message: "请先连接本机智能体。"))
        XCTAssertTrue(performer.calls.isEmpty)
    }

    private func storedConnection() throws -> StoredConnection {
        StoredConnection(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            displayName: "Hermes Mac",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "mobile_secret",
            tokenExpiresAt: nil
        )
    }
}

private final class StubRecallActionPerformer: RecallActionPerforming, @unchecked Sendable {
    private let response: RecallActionResponse
    private(set) var calls: [RecordedRecallAction] = []

    init(response: RecallActionResponse) {
        self.response = response
    }

    func submitRecallAction(
        _ request: RecallActionRequest,
        connection: StoredConnection
    ) async throws -> RecallActionResponse {
        calls.append(
            RecordedRecallAction(
                action: request.action,
                sourceTaskID: request.sourceTaskID,
                sourceInboxItemID: request.sourceInboxItemID,
                userVisibleSummary: request.userVisibleSummary,
                persistedItemID: response.item?.itemID
            )
        )
        return response
    }

    func fetchRecallItems(connection: StoredConnection) async throws -> [RecallItem] {
        []
    }

    func deleteRecallItem(itemID: String, connection: StoredConnection) async throws -> RecallDeleteResponse {
        RecallDeleteResponse(status: "forgotten", deletedItemIDs: [itemID])
    }
}

private struct RecordedRecallAction: Equatable {
    let action: RecallAction
    let sourceTaskID: String?
    let sourceInboxItemID: UUID?
    let userVisibleSummary: String
    let persistedItemID: String?
}

private extension RecallActionResponse {
    static func rememberedFixture() -> RecallActionResponse {
        RecallActionResponse(
            action: .remember,
            status: "remembered",
            item: RecallItem(
                itemID: "recall_0001",
                summary: "Remember that launch summaries should be in Chinese.",
                createdAt: "2026-06-05T09:30:00Z",
                provenance: RecallItem.Provenance(sourceTaskID: "task_123", sourceInboxItemID: nil)
            ),
            deletedItemIDs: []
        )
    }

    static func usedOnceFixture() -> RecallActionResponse {
        RecallActionResponse(
            action: .useOnce,
            status: "used_once",
            item: nil,
            deletedItemIDs: []
        )
    }

    static func forgottenFixture() -> RecallActionResponse {
        RecallActionResponse(
            action: .forget,
            status: "forgotten",
            item: nil,
            deletedItemIDs: ["recall_0001"]
        )
    }
}
