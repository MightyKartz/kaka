import XCTest
@testable import AgentPocketCore

final class AssetUploadTests: XCTestCase {
    func testImageUploadPreparationRejectsUnsupportedMimeType() {
        let policy = ImageUploadPolicy(maxUploadMB: 30)

        XCTAssertThrowsError(
            try policy.prepare(
                data: Data("not an image".utf8),
                mimeType: "text/plain",
                fileName: "note.txt",
                width: 10,
                height: 10,
                localCreationTime: "2026-05-30T12:00:00Z"
            )
        ) { error in
            XCTAssertEqual(error as? ImageUploadPolicy.ValidationError, .unsupportedMimeType)
        }
    }

    func testImageUploadPreparationRejectsOversizedData() {
        let policy = ImageUploadPolicy(maxUploadMB: 1)
        let tooLarge = Data(repeating: 0x41, count: 1_048_577)

        XCTAssertThrowsError(
            try policy.prepare(
                data: tooLarge,
                mimeType: "image/jpeg",
                fileName: "photo.jpg",
                width: 100,
                height: 100,
                localCreationTime: nil
            )
        ) { error in
            XCTAssertEqual(error as? ImageUploadPolicy.ValidationError, .exceedsMaxUploadSize)
        }
    }

    func testImageUploadPreparationMarksSensitiveExifAsStripped() throws {
        let policy = ImageUploadPolicy(maxUploadMB: 30)

        let upload = try policy.prepare(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "photo.jpg",
            width: 640,
            height: 480,
            localCreationTime: "2026-05-30T12:00:00Z"
        )

        XCTAssertEqual(upload.metadata.width, 640)
        XCTAssertEqual(upload.metadata.height, 480)
        XCTAssertTrue(upload.metadata.stripSensitiveEXIF)
        XCTAssertEqual(upload.mimeType, "image/jpeg")
    }

    func testAssetUploadRequestBuildsMultipartBody() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")
        let policy = ImageUploadPolicy(maxUploadMB: 30)
        let upload = try policy.prepare(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "photo.jpg",
            width: 640,
            height: 480,
            localCreationTime: "2026-05-30T12:00:00Z"
        )

        let request = try MobileBridgeClient.makeAssetUploadRequest(
            endpoint: endpoint,
            token: "abc123",
            upload: upload,
            boundary: "Boundary-Test"
        )

        let body = String(data: request.httpBody ?? Data(), encoding: .utf8) ?? ""
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url?.absoluteString, "https://hermes.example.com/mobile/v1/assets")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
        XCTAssertEqual(
            request.value(forHTTPHeaderField: "Content-Type"),
            "multipart/form-data; boundary=Boundary-Test"
        )
        XCTAssertTrue(body.contains("name=\"metadata\""))
        XCTAssertTrue(body.contains("\"width\":640"))
        XCTAssertTrue(body.contains("\"strip_sensitive_exif\":true"))
        XCTAssertTrue(body.contains("name=\"file\"; filename=\"photo.jpg\""))
        XCTAssertTrue(body.contains("Content-Type: image/jpeg"))
        XCTAssertTrue(body.contains("jpeg bytes"))
    }
}
