import XCTest
@testable import AgentPocketCore

final class PhotoEditTaskRequestTests: XCTestCase {
    func testDecodesAssetUploadResponse() throws {
        let data = """
        {"asset_id":"asset_123","mime_type":"image/jpeg","size_bytes":42,"sha256":"abc"}
        """.data(using: .utf8)!

        let response = try JSONDecoder.mobileBridge.decode(AssetUploadResponse.self, from: data)

        XCTAssertEqual(response.assetID, "asset_123")
        XCTAssertEqual(response.mimeType, "image/jpeg")
        XCTAssertEqual(response.sizeBytes, 42)
    }

    func testPhotoEditTaskRequestBuildsJSONBody() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")
        let task = PhotoEditTaskRequest(
            profileID: "photo-agent",
            assetID: "asset_123",
            intent: .portraitPolish,
            returnVariants: 3
        )

        let request = try MobileBridgeClient.makePhotoEditTaskRequest(
            endpoint: endpoint,
            token: "abc123",
            task: task
        )

        let body = String(data: request.httpBody ?? Data(), encoding: .utf8) ?? ""
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url?.absoluteString, "https://hermes.example.com/mobile/v1/tasks/photo-edit")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
        XCTAssertTrue(body.contains("\"profile_id\":\"photo-agent\""))
        XCTAssertTrue(body.contains("\"asset_id\":\"asset_123\""))
        XCTAssertTrue(body.contains("\"style\":\"portrait_polish\""))
        XCTAssertTrue(body.contains("\"return_variants\":3"))
        XCTAssertTrue(body.contains("Do not change identity"))
    }

    func testPhotoEditTaskRequestClampsReturnVariantsToSupportedRange() {
        let tooMany = PhotoEditTaskRequest(
            profileID: "photo-agent",
            assetID: "asset_123",
            intent: .naturalEnhance,
            returnVariants: 99
        )
        let none = PhotoEditTaskRequest(
            profileID: "photo-agent",
            assetID: "asset_123",
            intent: .naturalEnhance,
            returnVariants: 0
        )

        XCTAssertEqual(tooMany.returnVariants, 3)
        XCTAssertEqual(none.returnVariants, 1)
    }
}
