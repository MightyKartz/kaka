import XCTest
@testable import AgentPocketCore

final class MobileBridgeClientTests: XCTestCase {
    func testRequestUsesBearerTokenWhenProvided() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")

        let request = MobileBridgeClient.makeRequest(
            endpoint: endpoint,
            path: "/mobile/v1/capabilities",
            token: "abc123"
        )

        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
        XCTAssertEqual(request.url?.absoluteString, "https://hermes.example.com/mobile/v1/capabilities")
    }

    func testDecodesHealthResponse() throws {
        let data = """
        {"ok":true,"runtime":"hermes","runtime_version":"2026.5.16","bridge_version":"0.1.0"}
        """.data(using: .utf8)!

        let response = try JSONDecoder.mobileBridge.decode(HealthResponse.self, from: data)

        XCTAssertTrue(response.ok)
        XCTAssertEqual(response.runtime, "hermes")
        XCTAssertEqual(response.runtimeVersion, "2026.5.16")
        XCTAssertEqual(response.bridgeVersion, "0.1.0")
    }

    func testDecodesCapabilitiesResponse() throws {
        let data = """
        {
          "profiles": [{"id":"photo-agent","display_name":"Photo Agent","capabilities":["photo_edit"]}],
          "tasks": {"photo_edit": {"max_upload_mb":30,"accepted_mime_types":["image/jpeg"],"styles":["natural_enhance"],"provider":"recipe_local","renderer":"local_parametric","variant_labels":["Master","Social"],"variant_ids":["variant_clean_pro","variant_social_pop"],"crop_aspects":["original","4:5","1:1"],"supports_crop_candidates":true,"supports_upscale_policy":true,"supports_sse":true,"return_variants_max":3}},
          "retention": {"input_assets_days":7,"output_assets_days":30,"task_history_days":30}
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder.mobileBridge.decode(CapabilitiesResponse.self, from: data)

        XCTAssertEqual(response.profiles.first?.id, "photo-agent")
        XCTAssertEqual(response.tasks.photoEdit.maxUploadMB, 30)
        XCTAssertEqual(response.tasks.photoEdit.provider, "recipe_local")
        XCTAssertEqual(response.tasks.photoEdit.renderer, "local_parametric")
        XCTAssertEqual(response.tasks.photoEdit.variantLabels, ["Master", "Social"])
        XCTAssertEqual(response.tasks.photoEdit.variantIDs, ["variant_clean_pro", "variant_social_pop"])
        XCTAssertEqual(response.tasks.photoEdit.cropAspects, ["original", "4:5", "1:1"])
        XCTAssertTrue(response.tasks.photoEdit.supportsCropCandidates)
        XCTAssertTrue(response.tasks.photoEdit.supportsUpscalePolicy)
        XCTAssertTrue(response.tasks.photoEdit.supportsSSE)
        XCTAssertEqual(response.retention.outputAssetsDays, 30)
    }

    func testDecodesBridgeErrorResponse() throws {
        let data = """
        {"error":{"code":"unauthorized","message":"The mobile token is missing or invalid.","recoverable":true}}
        """.data(using: .utf8)!

        let response = try JSONDecoder.mobileBridge.decode(BridgeErrorResponse.self, from: data)

        XCTAssertEqual(response.error.code, "unauthorized")
        XCTAssertTrue(response.error.recoverable)
    }

    func testDecodesPairingExchangeResponse() throws {
        let data = """
        {"endpoint_id":"endpoint_01JHERMES","display_name":"Kartz MacBook Hermes","runtime":"hermes","runtime_version":"2026.5.16","mobile_token":"mobile_secret_value","token_expires_at":null}
        """.data(using: .utf8)!

        let response = try JSONDecoder.mobileBridge.decode(PairingExchangeResponse.self, from: data)

        XCTAssertEqual(response.endpointID, "endpoint_01JHERMES")
        XCTAssertEqual(response.displayName, "Kartz MacBook Hermes")
        XCTAssertEqual(response.mobileToken, "mobile_secret_value")
        XCTAssertNil(response.tokenExpiresAt)
    }

    func testDecodesCompletedTaskStatusResponse() throws {
        let data = """
        {"task_id":"task_01JPHOTO","status":"completed","progress":1.0,"message":"Completed.","variants":[{"id":"variant_natural","label":"Natural","asset_id":"asset_result","download_url":"/mobile/v1/assets/asset_result/download"}],"explanation":"Balanced exposure."}
        """.data(using: .utf8)!

        let response = try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)

        XCTAssertEqual(response.taskID, "task_01JPHOTO")
        XCTAssertEqual(response.status, "completed")
        XCTAssertEqual(response.variants?.first?.assetID, "asset_result")
        XCTAssertEqual(response.variants?.first?.downloadURL, "/mobile/v1/assets/asset_result/download")
    }

    func testDecodesCompletedTaskStatusResponseWithLocalRecipeMetadata() throws {
        let data = """
        {
          "task_id": "task_01JPHOTO",
          "status": "completed",
          "progress": 1.0,
          "message": "Completed.",
          "variants": [
            {"id":"variant_clean_pro","label":"Master","asset_id":"asset_master","download_url":"/mobile/v1/assets/asset_master/download","recommended_for":"save"},
            {"id":"variant_social_pop","label":"Social","asset_id":"asset_social","download_url":"/mobile/v1/assets/asset_social/download","recommended_for":"share"}
          ],
          "renderer": "local_parametric",
          "composition": {
            "selected_aspect_ratio": "4:5",
            "crop": {"x": 0.2, "y": 0.0, "width": 0.6, "height": 1.0}
          },
          "qa": {
            "master_difference_score": 0.18,
            "social_difference_score": 0.31
          },
          "recipe_summary": "Balanced exposure and reframed to 4:5.",
          "share_caption": "Shot polished locally with Kaka."
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)

        XCTAssertEqual(response.renderer, "local_parametric")
        XCTAssertEqual(response.composition?.selectedAspectRatio, "4:5")
        XCTAssertEqual(response.composition?.crop?.x, 0.2)
        XCTAssertEqual(response.composition?.crop?.width, 0.6)
        XCTAssertEqual(response.variants?.map(\.recommendedFor), ["save", "share"])
        XCTAssertEqual(response.qa?.masterDifferenceScore, 0.18)
        XCTAssertEqual(response.qa?.socialDifferenceScore, 0.31)
        XCTAssertEqual(response.recipeSummary, "Balanced exposure and reframed to 4:5.")
        XCTAssertEqual(response.shareCaption, "Shot polished locally with Kaka.")
    }
}
