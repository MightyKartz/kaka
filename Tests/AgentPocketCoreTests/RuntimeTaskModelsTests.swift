import XCTest
@testable import AgentPocketCore

final class RuntimeTaskModelsTests: XCTestCase {
    func testRuntimeTaskIdentifiesWaitingForApproval() {
        let task = RuntimeTaskSummary(
            id: "task_approval_1",
            title: "Remember article",
            status: .waitingForApproval,
            progress: 0.5,
            message: "Approve Recall write"
        )

        XCTAssertTrue(task.requiresUserAction)
        XCTAssertFalse(task.isTerminal)
    }

    func testRuntimeTaskListDecodesSnakeCaseStatusAndDefaults() throws {
        let data = """
        {
          "tasks": [
            {
              "id": "task_approval_1",
              "title": "Remember article",
              "status": "waiting_for_approval",
              "progress": 0.5,
              "message": "Approve Recall write"
            }
          ]
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder.mobileBridge.decode(RuntimeTaskListResponse.self, from: data)

        XCTAssertEqual(response.tasks.first?.status, .waitingForApproval)
        XCTAssertEqual(response.tasks.first?.message, "Approve Recall write")
    }

    func testBuildsRuntimeTaskCancelAndApprovalRequests() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")

        let cancel = MobileBridgeClient.makeRuntimeTaskCancelRequest(
            endpoint: endpoint,
            token: "abc123",
            taskID: "task_approval_1"
        )
        let approval = try MobileBridgeClient.makeRuntimeTaskApprovalRequest(
            endpoint: endpoint,
            token: "abc123",
            taskID: "task_approval_1",
            approval: RuntimeTaskApprovalRequest(action: .approve, note: "Looks good.")
        )
        let body = String(data: approval.httpBody ?? Data(), encoding: .utf8) ?? ""

        XCTAssertEqual(cancel.httpMethod, "POST")
        XCTAssertEqual(cancel.url?.path, "/mobile/v1/tasks/task_approval_1/cancel")
        XCTAssertEqual(cancel.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
        XCTAssertEqual(approval.httpMethod, "POST")
        XCTAssertEqual(approval.url?.path, "/mobile/v1/tasks/task_approval_1/approval")
        XCTAssertTrue(body.contains("\"action\":\"approve\""))
        XCTAssertTrue(body.contains("\"note\":\"Looks good.\""))
    }
}
