import XCTest
@testable import AgentPocketCore

final class VoiceIntakeTests: XCTestCase {
    func testVoiceFollowUpDraftEncodesTranscriptAndSourceIDs() throws {
        let draft = VoiceFollowUpDraft(
            transcript: "提取图片里的文字",
            sourceTaskID: "task_intake_123",
            sourceInboxItemID: UUID(uuidString: "00000000-0000-0000-0000-000000000456")
        )

        let data = try JSONEncoder.mobileBridge.encode(draft)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])

        XCTAssertEqual(object["transcript"] as? String, "提取图片里的文字")
        XCTAssertEqual(object["source_task_id"] as? String, "task_intake_123")
        XCTAssertEqual(object["source_inbox_item_id"] as? String, "00000000-0000-0000-0000-000000000456")
    }
}
