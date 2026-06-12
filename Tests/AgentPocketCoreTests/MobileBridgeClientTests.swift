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
          "profiles": [{"id":"photo-agent","display_name":"Photo Agent","capabilities":["photo_edit","vision"]}],
          "tasks": {
            "photo_edit": {"max_upload_mb":30,"accepted_mime_types":["image/jpeg"],"styles":["natural_enhance"],"provider":"recipe_local","renderer":"local_parametric","variant_labels":["Master","Social"],"variant_ids":["variant_clean_pro","variant_social_pop"],"crop_aspects":["original"],"supports_crop_candidates":false,"supports_upscale_policy":true,"supports_sse":true,"return_variants_max":2},
            "vision": {"max_upload_mb":30,"accepted_mime_types":["image/jpeg"],"modes":["scan","identify","translate","food"],"provider":"fixture_vision","supports_sse":true}
          },
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
        XCTAssertEqual(response.tasks.photoEdit.cropAspects, ["original"])
        XCTAssertFalse(response.tasks.photoEdit.supportsCropCandidates)
        XCTAssertTrue(response.tasks.photoEdit.supportsUpscalePolicy)
        XCTAssertTrue(response.tasks.photoEdit.supportsSSE)
        XCTAssertEqual(response.tasks.vision?.provider, "fixture_vision")
        XCTAssertEqual(response.tasks.vision?.modes, ["scan", "identify", "translate", "food"])
        XCTAssertTrue(response.tasks.vision?.supportsSSE == true)
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
            "selected_aspect_ratio": "original",
            "crop": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
          },
          "qa": {
            "master_difference_score": 0.18,
            "social_difference_score": 0.31
          },
          "recipe_summary": "Balanced exposure while preserving the original frame.",
          "share_caption": "Shot polished locally with Kaka."
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)

        XCTAssertEqual(response.renderer, "local_parametric")
        XCTAssertEqual(response.composition?.selectedAspectRatio, "original")
        XCTAssertEqual(response.composition?.crop?.x, 0.0)
        XCTAssertEqual(response.composition?.crop?.width, 1.0)
        XCTAssertEqual(response.variants?.map(\.recommendedFor), ["save", "share"])
        XCTAssertEqual(response.qa?.masterDifferenceScore, 0.18)
        XCTAssertEqual(response.qa?.socialDifferenceScore, 0.31)
        XCTAssertEqual(response.recipeSummary, "Balanced exposure while preserving the original frame.")
        XCTAssertEqual(response.shareCaption, "Shot polished locally with Kaka.")
    }

    func testBuildsVisionTaskRequest() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")
        let task = VisionTaskRequest(
            profileID: "photo-agent",
            assetID: "asset_123",
            mode: .identify,
            locale: "zh-Hans"
        )

        let request = try MobileBridgeClient.makeVisionTaskRequest(
            endpoint: endpoint,
            token: "abc123",
            task: task
        )
        let body = String(data: request.httpBody ?? Data(), encoding: .utf8) ?? ""

        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url?.absoluteString, "https://hermes.example.com/mobile/v1/tasks/vision")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
        XCTAssertTrue(body.contains("\"asset_id\":\"asset_123\""))
        XCTAssertTrue(body.contains("\"mode\":\"identify\""))
        XCTAssertTrue(body.contains("\"locale\":\"zh-Hans\""))
        XCTAssertTrue(body.contains("Identify the main visible objects"))
    }

    func testBuildsImageIntakeTaskRequest() throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")
        let task = ImageIntakeTaskRequest(
            profileID: "photo-agent",
            assetID: "asset_123",
            locale: "zh-Hans"
        )

        let request = try MobileBridgeClient.makeImageIntakeTaskRequest(
            endpoint: endpoint,
            token: "abc123",
            task: task
        )
        let body = String(data: request.httpBody ?? Data(), encoding: .utf8) ?? ""

        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url?.absoluteString, "https://hermes.example.com/mobile/v1/tasks/image-intake")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
        XCTAssertTrue(body.contains("\"profile_id\":\"photo-agent\""))
        XCTAssertTrue(body.contains("\"asset_id\":\"asset_123\""))
        XCTAssertTrue(body.contains("\"locale\":\"zh-Hans\""))
    }

    func testBuildsUniversalIntakeTaskRequest() throws {
        let endpoint = try AgentEndpoint(rawURL: "http://127.0.0.1:8765")
        let task = UniversalIntakeTaskRequest(
            kind: .text,
            text: "Launch notes",
            note: "Extract tasks",
            locale: "en-US",
            preferredProfileID: "photo-agent",
            sourceApp: "Notes"
        )

        let request = try MobileBridgeClient.makeUniversalIntakeTaskRequest(
            endpoint: endpoint,
            token: "mobile-token",
            task: task
        )
        let body = String(data: request.httpBody ?? Data(), encoding: .utf8) ?? ""

        XCTAssertEqual(request.url?.path, "/mobile/v1/tasks/intake")
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer mobile-token")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
        XCTAssertTrue(body.contains("\"kind\":\"text\""))
        XCTAssertTrue(body.contains("\"preferred_profile_id\":\"photo-agent\""))
        XCTAssertTrue(body.contains("\"source_app\":\"Notes\""))
    }

    func testDecodesVisionTaskStatusResponse() throws {
        let data = """
        {
          "task_id": "task_vision_1",
          "status": "completed",
          "progress": 1.0,
          "message": "Completed.",
          "result_type": "vision",
          "vision": {
            "mode": "food",
            "title": "食物估算",
            "summary": "画面中像是一份轻食，热量约 320-460 千卡。",
            "text": "可见食材：鸡蛋、蔬菜、面包。",
            "language": "zh-Hans",
            "confidence": 0.72,
            "sections": [
              {
                "title": "营养估算",
                "kind": "nutrition",
                "items": [
                  {"title":"蛋白质","value":"18-25 g","subtitle":"粗略估算","confidence":0.58}
                ]
              }
            ],
            "items": [
              {"title":"热量范围","value":"320-460 kcal","subtitle":"基于可见分量估算","confidence":0.62}
            ]
          }
        }
        """.data(using: .utf8)!

        let response = try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)

        XCTAssertEqual(response.resultType, "vision")
        XCTAssertEqual(response.vision?.mode, "food")
        XCTAssertEqual(response.vision?.title, "食物估算")
        XCTAssertEqual(response.vision?.items.first?.value, "320-460 kcal")
        XCTAssertEqual(response.vision?.sections.first?.kind, "nutrition")
        XCTAssertEqual(response.vision?.sections.first?.items.first?.title, "蛋白质")
        XCTAssertEqual(response.vision?.confidence, 0.72)
    }
}
