import XCTest
@testable import AgentPocketCore

final class ImageIntakeRequestTests: XCTestCase {
    func testImageIntakeTaskRequestBuildsJSONBody() throws {
        let request = ImageIntakeTaskRequest(
            profileID: "photo-agent",
            assetID: "asset_123",
            locale: "zh-Hans"
        )

        let data = try JSONEncoder.mobileBridge.encode(request)
        let body = String(data: data, encoding: .utf8)!

        XCTAssertTrue(body.contains("\"profile_id\":\"photo-agent\""))
        XCTAssertTrue(body.contains("\"asset_id\":\"asset_123\""))
        XCTAssertTrue(body.contains("\"locale\":\"zh-Hans\""))
    }

    func testTaskStatusDecodesImageIntakeResult() throws {
        let data = """
        {
          "task_id": "task_intake_1",
          "status": "completed",
          "progress": 1.0,
          "result_type": "image_intake",
          "image_intake": {
            "image_type": "text_screen",
            "title": "检测到文字",
            "summary": "画面中有大量可读文字。",
            "confidence": 0.82,
            "suggestions": [
              {
                "skill": "ocr",
                "title": "提取文字",
                "reason": "检测到多行文字。",
                "confidence": 0.84,
                "is_available": true
              }
            ]
          }
        }
        """.data(using: .utf8)!

        let status = try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)

        XCTAssertEqual(status.resultType, "image_intake")
        XCTAssertEqual(status.imageIntake?.imageType, "text_screen")
        XCTAssertEqual(status.imageIntake?.suggestions.first?.skill, .ocr)
        XCTAssertEqual(status.imageIntake?.suggestions.first?.isAvailable, true)
    }
}
