import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class ImageConversationViewModelTests: XCTestCase {
    func testStartsWithIntakeSummaryAndSuggestions() throws {
        let status = try completedImageIntakeStatus()
        let viewModel = ImageConversationViewModel(
            intakeStatus: status,
            originalAsset: DownloadedAsset(data: Data("image".utf8), mimeType: "image/jpeg"),
            preparedUpload: PreparedImageUpload.fixture()
        )

        XCTAssertEqual(viewModel.messages.first?.role, .assistant)
        XCTAssertEqual(viewModel.messages.first?.text, "我可以帮你优化这张照片。")
        XCTAssertEqual(
            viewModel.suggestions.map(\.skill),
            [.photoEnhance, .ocr, .identifySubject, .translateText, .nutritionEstimate]
        )
        XCTAssertTrue(viewModel.suggestions.allSatisfy(\.isAvailable))
    }

    func testSubmittingPromptRoutesAndExecutesSkill() async throws {
        let executor = StubImageSkillExecutor(status: try completedVisionStatus(mode: .scan))
        let viewModel = ImageConversationViewModel(
            intakeStatus: try completedImageIntakeStatus(),
            originalAsset: nil,
            preparedUpload: PreparedImageUpload.fixture(),
            skillExecutor: executor
        )

        viewModel.prompt = "提取文字"
        await viewModel.submitPrompt(connection: try storedConnection())

        XCTAssertEqual(executor.calls.map(\.skill), [.ocr])
        XCTAssertEqual(viewModel.messages.last?.role, .result)
        XCTAssertEqual(viewModel.messages.last?.result?.taskID, "task_vision_123")
    }

    func testPhotoResultPresentationReturnsActionableResultCardData() throws {
        let presentation = ImageConversationResultPresentation(
            status: try completedPhotoStatus(),
            language: .chinese
        )

        XCTAssertEqual(presentation.kind, .photo)
        XCTAssertEqual(presentation.title, "修图结果")
        XCTAssertEqual(presentation.subtitle, "已生成 2 个版本")
        XCTAssertEqual(presentation.bodyText, "自然增强完成。")
        XCTAssertEqual(presentation.detailRows.map(\.title), ["Master", "Social"])
        XCTAssertEqual(presentation.detailRows.map(\.value), ["适合查看细节", "适合分享"])
        XCTAssertEqual(presentation.actionTitle, "查看修图结果")
    }

    func testVisionResultPresentationIncludesReturnedTextAndItems() throws {
        let presentation = ImageConversationResultPresentation(
            status: try completedVisionStatusWithText(),
            language: .chinese
        )

        XCTAssertEqual(presentation.kind, .vision)
        XCTAssertEqual(presentation.title, "扫描结果")
        XCTAssertEqual(presentation.subtitle, "Vision · scan")
        XCTAssertEqual(presentation.bodyText, "NATIVE WOOD PULP\n100% 原生木浆")
        XCTAssertEqual(presentation.detailRows.first?.title, "文本 1")
        XCTAssertEqual(presentation.detailRows.first?.value, "NATIVE WOOD PULP")
        XCTAssertEqual(presentation.actionTitle, "查看完整结果")
    }

    func testSkillExecutorMapsOCRToVisionScan() async throws {
        let recording = SkillExecutorHTTPRecording()
        let executor = try makeHTTPExecutor(recording: recording)

        _ = try await executor.execute(
            skill: .ocr,
            userInstruction: "提取文字",
            upload: PreparedImageUpload.fixture(),
            connection: try storedConnection()
        ) { _ in }

        XCTAssertEqual(recording.startedVisionModes, ["scan"])
        XCTAssertEqual(recording.visionInstructions, ["提取文字"])
    }

    func testSkillExecutorMapsVisibleVisionSkillsToModes() async throws {
        let cases: [(KakaSkillID, String, VisionTaskKind)] = [
            (.translateText, "翻译文字", .translate),
            (.identifySubject, "识别主体", .identify),
            (.nutritionEstimate, "估算热量", .food),
        ]

        for (skill, instruction, expectedMode) in cases {
            let recording = SkillExecutorHTTPRecording()
            let executor = try makeHTTPExecutor(recording: recording)

            _ = try await executor.execute(
                skill: skill,
                userInstruction: instruction,
                upload: PreparedImageUpload.fixture(),
                connection: try storedConnection()
            ) { _ in }

            XCTAssertEqual(recording.startedVisionModes, [expectedMode.rawValue])
            XCTAssertEqual(recording.visionInstructions, [instruction])
        }
    }

    func testSkillExecutorMapsPhotoEnhanceToPhotoEdit() async throws {
        let recording = SkillExecutorHTTPRecording()
        let executor = try makeHTTPExecutor(recording: recording)

        _ = try await executor.execute(
            skill: .photoEnhance,
            userInstruction: "修得高级一点",
            upload: PreparedImageUpload.fixture(),
            connection: try storedConnection()
        ) { _ in }

        XCTAssertEqual(recording.startedPhotoEditIntents, ["natural_enhance"])
        XCTAssertEqual(recording.photoEditInstructions, ["修得高级一点"])
    }

    func testUnavailableSuggestionDoesNotExecuteAndShowsRecoveryMessage() async throws {
        let suggestion = KakaSkillSuggestion(
            skill: .nutritionEstimate,
            title: "估算热量",
            reason: "需要食物识别模型。",
            confidence: 0.2,
            isAvailable: false
        )
        let viewModel = ImageConversationViewModel(
            intakeStatus: try completedImageIntakeStatus(suggestions: [suggestion]),
            originalAsset: nil,
            preparedUpload: PreparedImageUpload.fixture()
        )

        await viewModel.executeSuggestion(suggestion, connection: try storedConnection())

        XCTAssertEqual(viewModel.messages.last?.text, "这个技能当前没有接入视觉模型。")
    }

    func testAvailableIdentifySuggestionExecutesInsteadOfShowingUnavailableCopy() async throws {
        let suggestion = KakaSkillSuggestion(
            skill: .identifySubject,
            title: "识别主体",
            reason: "判断画面中的主要物体。",
            confidence: 0.48,
            isAvailable: true
        )
        let executor = StubImageSkillExecutor(status: try completedVisionStatus(mode: .identify))
        let viewModel = ImageConversationViewModel(
            intakeStatus: try completedImageIntakeStatus(suggestions: [suggestion]),
            originalAsset: nil,
            preparedUpload: PreparedImageUpload.fixture(),
            skillExecutor: executor
        )

        await viewModel.executeSuggestion(suggestion, connection: try storedConnection())

        XCTAssertEqual(executor.calls.map(\.skill), [.identifySubject])
        XCTAssertEqual(viewModel.messages.last?.role, .result)
    }

    func testVoiceUnavailableFeedbackAppendsAssistantMessage() throws {
        let viewModel = ImageConversationViewModel(
            intakeStatus: try completedImageIntakeStatus(),
            originalAsset: nil,
            preparedUpload: PreparedImageUpload.fixture()
        )

        viewModel.reportVoiceUnavailable()

        XCTAssertEqual(viewModel.messages.last?.role, .assistant)
        XCTAssertEqual(viewModel.messages.last?.text, "语音输入还没有接入，请先用文字告诉 Kaka。")
    }

    private func completedImageIntakeStatus() throws -> TaskStatusResponse {
        let data = """
        {
          "task_id":"task_intake_123",
          "status":"completed",
          "progress":1.0,
          "result_type":"image_intake",
          "image_intake":{
            "image_type":"photo",
            "title":"已看到照片",
            "summary":"我可以帮你优化这张照片。",
            "confidence":0.62,
            "suggestions":[
              {"skill":"photo_enhance","title":"大师级优化","reason":"适合自然增强。","confidence":0.62,"is_available":true},
              {"skill":"ocr","title":"提取文字","reason":"如果你想读背景文字，也可以提取文字。","confidence":0.25,"is_available":true}
            ]
          }
        }
        """.data(using: .utf8)!
        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }

    private func completedImageIntakeStatus(suggestions: [KakaSkillSuggestion]) throws -> TaskStatusResponse {
        let suggestionJSON = suggestions.map { suggestion in
            """
            {
              "skill":"\(suggestion.skill.rawValue)",
              "title":"\(suggestion.title)",
              "reason":"\(suggestion.reason)",
              "confidence":\(suggestion.confidence ?? 0),
              "is_available":\(suggestion.isAvailable ? "true" : "false")
            }
            """
        }.joined(separator: ",")
        let data = """
        {
          "task_id":"task_intake_123",
          "status":"completed",
          "progress":1.0,
          "result_type":"image_intake",
          "image_intake":{
            "image_type":"photo",
            "title":"已看到照片",
            "summary":"我可以帮你优化这张照片。",
            "confidence":0.62,
            "suggestions":[\(suggestionJSON)]
          }
        }
        """.data(using: .utf8)!
        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }

    private func completedVisionStatus(mode: VisionTaskKind) throws -> TaskStatusResponse {
        let data = """
        {
          "task_id":"task_vision_123",
          "status":"completed",
          "progress":1.0,
          "result_type":"vision",
          "vision":{
            "mode":"\(mode.rawValue)",
            "title":"扫描结果",
            "summary":"识别到 2 行文字。",
            "items":[{"title":"文本 1","value":"NATIVE WOOD PULP"}]
          }
        }
        """.data(using: .utf8)!
        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }

    private func completedVisionStatusWithText() throws -> TaskStatusResponse {
        let data = """
        {
          "task_id":"task_vision_123",
          "status":"completed",
          "progress":1.0,
          "result_type":"vision",
          "vision":{
            "mode":"scan",
            "title":"扫描结果",
            "summary":"识别到 2 行文字。",
            "text":"NATIVE WOOD PULP\\n100% 原生木浆",
            "sections":[
              {
                "title":"文本",
                "kind":"ocr",
                "items":[
                  {"title":"文本 1","value":"NATIVE WOOD PULP","confidence":0.9},
                  {"title":"文本 2","value":"100% 原生木浆","confidence":0.88}
                ]
              }
            ],
            "items":[]
          }
        }
        """.data(using: .utf8)!
        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }

    private func completedPhotoStatus() throws -> TaskStatusResponse {
        let data = """
        {
          "task_id":"task_photo_123",
          "status":"completed",
          "progress":1.0,
          "variants":[
            {"id":"variant_clean_pro","label":"Master","asset_id":"asset_master","download_url":"/mobile/v1/assets/asset_master/download","recommended_for":"review"},
            {"id":"variant_social_pop","label":"Social","asset_id":"asset_social","download_url":"/mobile/v1/assets/asset_social/download","recommended_for":"share"}
          ],
          "explanation":"自然增强完成。"
        }
        """.data(using: .utf8)!
        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
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

    private func makeHTTPExecutor(recording: SkillExecutorHTTPRecording) throws -> MobileBridgeImageSkillSubmitter {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [ImageSkillMockURLProtocol.self]
        let session = URLSession(configuration: configuration)
        ImageSkillMockURLProtocol.requestHandler = { request in
            let path = request.url?.path ?? ""
            let body = request.httpBodyStreamData()
            return try recording.response(for: path, request: request, body: body)
        }
        return MobileBridgeImageSkillSubmitter(
            session: session,
            poller: TaskPoller(intervalNanoseconds: 0)
        )
    }
}

private extension PreparedImageUpload {
    static func fixture() -> PreparedImageUpload {
        PreparedImageUpload(
            data: Data("jpeg bytes".utf8),
            mimeType: "image/jpeg",
            fileName: "camera.jpg",
            metadata: ImageUploadMetadata(
                width: 640,
                height: 480,
                localCreationTime: nil,
                stripSensitiveEXIF: true
            )
        )
    }
}

private final class StubImageSkillExecutor: ImageSkillExecuting, @unchecked Sendable {
    struct Call: Equatable {
        let skill: KakaSkillID
        let instruction: String?
        let upload: PreparedImageUpload
        let connection: StoredConnection
    }

    private(set) var calls: [Call] = []
    private let status: TaskStatusResponse

    init(status: TaskStatusResponse) {
        self.status = status
    }

    func execute(
        skill: KakaSkillID,
        userInstruction: String?,
        upload: PreparedImageUpload,
        connection: StoredConnection,
        progress: @escaping @Sendable (PhotoEditSubmissionProgress) async -> Void
    ) async throws -> TaskStatusResponse {
        calls.append(Call(skill: skill, instruction: userInstruction, upload: upload, connection: connection))
        await progress(.submitted(taskID: status.taskID))
        return status
    }
}

private final class SkillExecutorHTTPRecording: @unchecked Sendable {
    private(set) var startedVisionModes: [String] = []
    private(set) var visionInstructions: [String] = []
    private(set) var startedPhotoEditIntents: [String] = []
    private(set) var photoEditInstructions: [String] = []

    func response(for path: String, request: URLRequest, body: Data) throws -> (HTTPURLResponse, Data) {
        switch (request.httpMethod, path) {
        case ("GET", "/mobile/v1/capabilities"):
            return ok(request, """
            {
              "profiles": [{"id":"photo-agent","display_name":"Photo Agent","capabilities":["photo_edit","vision","image_intake"]}],
              "tasks": {
                "photo_edit": {"max_upload_mb":30,"accepted_mime_types":["image/jpeg"],"styles":["natural_enhance"],"provider":"recipe_local","renderer":"local_parametric","variant_labels":["Master","Social"],"variant_ids":["variant_clean_pro","variant_social_pop"],"crop_aspects":["original"],"supports_crop_candidates":false,"supports_upscale_policy":true,"supports_sse":false,"return_variants_max":3},
                "vision": {"max_upload_mb":30,"accepted_mime_types":["image/jpeg"],"modes":["scan","identify","translate","food"],"provider":"fixture_vision","supports_sse":false}
              },
              "retention": {"input_assets_days":7,"output_assets_days":30,"task_history_days":30}
            }
            """)
        case ("POST", "/mobile/v1/assets"):
            return ok(request, """
            {"asset_id":"asset_123","mime_type":"image/jpeg","size_bytes":10,"sha256":"abc"}
            """)
        case ("POST", "/mobile/v1/tasks/vision"):
            let payload = try JSONSerialization.jsonObject(with: body) as? [String: Any]
            startedVisionModes.append(payload?["mode"] as? String ?? "")
            visionInstructions.append(payload?["instruction"] as? String ?? "")
            return ok(request, """
            {"task_id":"task_vision_123","status":"queued","events_url":"/mobile/v1/tasks/task_vision_123/events"}
            """)
        case ("POST", "/mobile/v1/tasks/photo-edit"):
            let payload = try JSONSerialization.jsonObject(with: body) as? [String: Any]
            startedPhotoEditIntents.append(payload?["style"] as? String ?? "")
            photoEditInstructions.append(payload?["instruction"] as? String ?? "")
            return ok(request, """
            {"task_id":"task_photo_123","status":"queued","events_url":"/mobile/v1/tasks/task_photo_123/events"}
            """)
        case ("GET", "/mobile/v1/tasks/task_vision_123"):
            return ok(request, """
            {"task_id":"task_vision_123","status":"completed","progress":1.0,"result_type":"vision","vision":{"mode":"scan","title":"扫描结果","summary":"识别到 2 行文字。","items":[]}}
            """)
        case ("GET", "/mobile/v1/tasks/task_photo_123"):
            return ok(request, """
            {"task_id":"task_photo_123","status":"completed","progress":1.0,"variants":[{"id":"variant_1","label":"Master","asset_id":"asset_result","download_url":"/mobile/v1/assets/asset_result/download"}],"explanation":"修图完成。"}
            """)
        default:
            throw URLError(.badServerResponse)
        }
    }

    private func ok(_ request: URLRequest, _ body: String) -> (HTTPURLResponse, Data) {
        (
            HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!,
            body.data(using: .utf8)!
        )
    }
}

private final class ImageSkillMockURLProtocol: URLProtocol {
    nonisolated(unsafe) static var requestHandler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    override class func canInit(with request: URLRequest) -> Bool {
        true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        guard let requestHandler = Self.requestHandler else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
            return
        }

        do {
            let (response, data) = try requestHandler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}

private extension URLRequest {
    func httpBodyStreamData() -> Data {
        if let httpBody {
            return httpBody
        }
        guard let stream = httpBodyStream else {
            return Data()
        }

        stream.open()
        defer { stream.close() }

        var data = Data()
        let bufferSize = 1_024
        let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: bufferSize)
        defer { buffer.deallocate() }

        while stream.hasBytesAvailable {
            let count = stream.read(buffer, maxLength: bufferSize)
            if count <= 0 {
                break
            }
            data.append(buffer, count: count)
        }
        return data
    }
}
