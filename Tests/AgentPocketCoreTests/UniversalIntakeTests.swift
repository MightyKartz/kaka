import XCTest
@testable import AgentPocketCore

final class UniversalIntakeTests: XCTestCase {
    func testUniversalIntakeKindsUseStableBridgeRawValues() {
        XCTAssertEqual(UniversalIntakeKind.text.rawValue, "text")
        XCTAssertEqual(UniversalIntakeKind.url.rawValue, "url")
        XCTAssertEqual(UniversalIntakeKind.image.rawValue, "image")
        XCTAssertEqual(UniversalIntakeKind.screenshot.rawValue, "screenshot")
        XCTAssertEqual(UniversalIntakeKind.pdf.rawValue, "pdf")
    }

    func testUniversalIntakeRequestEncodesURLPayloadWithSnakeCaseMetadata() throws {
        let request = UniversalIntakeTaskRequest(
            kind: .url,
            url: "https://example.com/article",
            note: "Summarize this.",
            locale: "zh-Hans",
            preferredProfileID: "photo-agent",
            sourceApp: "Safari",
            receivedAt: Date(timeIntervalSince1970: 1_800_000_000)
        )

        let data = try JSONEncoder.mobileBridge.encode(request)
        let body = String(data: data, encoding: .utf8)!

        XCTAssertTrue(body.contains("\"kind\":\"url\""))
        XCTAssertTrue(body.contains("\"url\":\"https://example.com/article\""))
        XCTAssertTrue(body.contains("\"note\":\"Summarize this.\""))
        XCTAssertTrue(body.contains("\"locale\":\"zh-Hans\""))
        XCTAssertTrue(body.contains("\"preferred_profile_id\":\"photo-agent\""))
        XCTAssertTrue(body.contains("\"source_app\":\"Safari\""))
        XCTAssertTrue(body.contains("\"received_at\":\"2027-01-15T08:00:00Z\""))
    }

    func testUniversalIntakeRequestEncodesImageAndPDFPayloads() throws {
        let image = UniversalIntakeTaskRequest(
            kind: .image,
            assetID: "asset_image_1",
            sourceApp: "Photos"
        )
        let pdf = UniversalIntakeTaskRequest(
            kind: .pdf,
            assetID: "asset_pdf_1",
            sourceApp: "Files"
        )

        let imageBody = String(data: try JSONEncoder.mobileBridge.encode(image), encoding: .utf8)!
        let pdfBody = String(data: try JSONEncoder.mobileBridge.encode(pdf), encoding: .utf8)!

        XCTAssertTrue(imageBody.contains("\"kind\":\"image\""))
        XCTAssertTrue(imageBody.contains("\"asset_id\":\"asset_image_1\""))
        XCTAssertTrue(imageBody.contains("\"source_app\":\"Photos\""))
        XCTAssertTrue(pdfBody.contains("\"kind\":\"pdf\""))
        XCTAssertTrue(pdfBody.contains("\"asset_id\":\"asset_pdf_1\""))
        XCTAssertTrue(pdfBody.contains("\"source_app\":\"Files\""))
    }

    func testTaskStatusDecodesUniversalIntakeResult() throws {
        let data = """
        {
          "task_id":"task_intake_url_1",
          "status":"completed",
          "progress":1.0,
          "result_type":"intake",
          "intake":{
            "kind":"url",
            "title":"Article ready",
            "summary":"The runtime summarized the shared URL.",
            "suggestions":[
              {"id":"summarize","label":"Summarize","requires_confirmation":false,"is_available":true},
              {"id":"remember","label":"Remember","requires_confirmation":true,"is_available":true}
            ]
          }
        }
        """.data(using: .utf8)!

        let status = try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)

        XCTAssertEqual(status.resultType, "intake")
        XCTAssertEqual(status.intake?.kind, .url)
        XCTAssertEqual(status.intake?.title, "Article ready")
        XCTAssertEqual(status.intake?.suggestions.map(\.id), ["summarize", "remember"])
        XCTAssertEqual(status.intake?.suggestions.last?.requiresConfirmation, true)
    }

    func testCapabilitiesDecodeImageIntakeAndUniversalIntakeAcceptedTypes() throws {
        let data = """
        {
          "profiles":[{"id":"photo-agent","display_name":"Photo Agent","capabilities":["photo_edit","vision","image_intake","intake"]}],
          "tasks":{
            "photo_edit":{"max_upload_mb":30,"accepted_mime_types":["image/jpeg"],"styles":["natural_enhance"],"provider":"recipe_local","renderer":"local_parametric","supports_sse":true,"return_variants_max":3},
            "vision":{"max_upload_mb":30,"accepted_mime_types":["image/jpeg"],"modes":["scan"],"provider":"fixture_vision","supports_sse":true},
            "image_intake":{"max_upload_mb":30,"accepted_mime_types":["image/jpeg"],"provider":"heuristic_image_intake","supports_sse":true},
            "intake":{"accepted_types":["text","url","image","screenshot","pdf"],"supports_sse":true}
          },
          "retention":{"input_assets_days":7,"output_assets_days":30,"task_history_days":30}
        }
        """.data(using: .utf8)!

        let capabilities = try JSONDecoder.mobileBridge.decode(CapabilitiesResponse.self, from: data)

        XCTAssertEqual(capabilities.tasks.photoEdit.provider, "recipe_local")
        XCTAssertEqual(capabilities.tasks.vision?.provider, "fixture_vision")
        XCTAssertEqual(capabilities.tasks.imageIntake?.provider, "heuristic_image_intake")
        XCTAssertEqual(capabilities.tasks.intake?.acceptedTypes, [.text, .url, .image, .screenshot, .pdf])
        XCTAssertEqual(capabilities.tasks.intake?.supportsSSE, true)
    }
}
