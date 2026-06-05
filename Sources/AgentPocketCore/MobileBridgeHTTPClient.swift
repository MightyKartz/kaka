import Foundation

public struct MobileBridgeHTTPClient {
    public enum ClientError: Error, Equatable {
        case invalidResponse
        case httpStatus(Int, BridgeErrorResponse?)
    }

    private let endpoint: AgentEndpoint
    private let token: String
    private let session: URLSession

    public init(endpoint: AgentEndpoint, token: String, session: URLSession = .shared) {
        self.endpoint = endpoint
        self.token = token
        self.session = session
    }

    public func fetchHealth() async throws -> HealthResponse {
        let request = MobileBridgeClient.makeRequest(
            endpoint: endpoint,
            path: "/mobile/v1/health"
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(HealthResponse.self, from: data)
    }

    public func fetchCapabilities() async throws -> CapabilitiesResponse {
        let request = MobileBridgeClient.makeRequest(
            endpoint: endpoint,
            path: "/mobile/v1/capabilities",
            token: token
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(CapabilitiesResponse.self, from: data)
    }

    public func exchangePairingCode(
        pairingCode: String,
        deviceName: String,
        devicePublicID: String
    ) async throws -> PairingExchangeResponse {
        let request = try MobileBridgeClient.makePairingExchangeRequest(
            endpoint: endpoint,
            pairingCode: pairingCode,
            deviceName: deviceName,
            devicePublicID: devicePublicID
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(PairingExchangeResponse.self, from: data)
    }

    public func fetchDevelopmentPairingPayload() async throws -> String {
        let request = MobileBridgeClient.makeRequest(
            endpoint: endpoint,
            path: "/mobile/v1/pairing/dev"
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        guard let payload = String(data: data, encoding: .utf8) else {
            throw ClientError.invalidResponse
        }
        return payload
    }

    public func uploadAsset(_ upload: PreparedImageUpload) async throws -> AssetUploadResponse {
        try await uploadAsset(upload.asPreparedAssetUpload)
    }

    public func uploadAsset(_ upload: PreparedAssetUpload) async throws -> AssetUploadResponse {
        let request = try MobileBridgeClient.makeAssetUploadRequest(
            endpoint: endpoint,
            token: token,
            upload: upload
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(AssetUploadResponse.self, from: data)
    }

    public func startPhotoEditTask(_ task: PhotoEditTaskRequest) async throws -> PhotoEditTaskCreateResponse {
        let request = try MobileBridgeClient.makePhotoEditTaskRequest(
            endpoint: endpoint,
            token: token,
            task: task
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(PhotoEditTaskCreateResponse.self, from: data)
    }

    public func startVisionTask(_ task: VisionTaskRequest) async throws -> VisionTaskCreateResponse {
        let request = try MobileBridgeClient.makeVisionTaskRequest(
            endpoint: endpoint,
            token: token,
            task: task
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(VisionTaskCreateResponse.self, from: data)
    }

    public func startImageIntakeTask(_ task: ImageIntakeTaskRequest) async throws -> VisionTaskCreateResponse {
        let request = try MobileBridgeClient.makeImageIntakeTaskRequest(
            endpoint: endpoint,
            token: token,
            task: task
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(VisionTaskCreateResponse.self, from: data)
    }

    public func startUniversalIntakeTask(_ task: UniversalIntakeTaskRequest) async throws -> VisionTaskCreateResponse {
        let request = try MobileBridgeClient.makeUniversalIntakeTaskRequest(
            endpoint: endpoint,
            token: token,
            task: task
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(VisionTaskCreateResponse.self, from: data)
    }

    public func submitRecallAction(_ action: RecallActionRequest) async throws -> RecallActionResponse {
        let request = try MobileBridgeClient.makeRecallActionRequest(
            endpoint: endpoint,
            token: token,
            action: action
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(RecallActionResponse.self, from: data)
    }

    public func fetchRecallItems() async throws -> [RecallItem] {
        let request = MobileBridgeClient.makeRecallItemsRequest(
            endpoint: endpoint,
            token: token
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(RecallItemsResponse.self, from: data).items
    }

    public func deleteRecallItem(itemID: String) async throws -> RecallDeleteResponse {
        let request = MobileBridgeClient.makeDeleteRecallItemRequest(
            endpoint: endpoint,
            token: token,
            itemID: itemID
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(RecallDeleteResponse.self, from: data)
    }

    public func fetchTaskStatus(taskID: String) async throws -> TaskStatusResponse {
        let request = MobileBridgeClient.makeTaskStatusRequest(
            endpoint: endpoint,
            token: token,
            taskID: taskID
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }

    public func fetchRuntimeTasks() async throws -> [RuntimeTaskSummary] {
        let request = MobileBridgeClient.makeRuntimeTasksRequest(
            endpoint: endpoint,
            token: token
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(RuntimeTaskListResponse.self, from: data).tasks
    }

    public func cancelRuntimeTask(taskID: String) async throws -> RuntimeTaskActionResponse {
        let request = MobileBridgeClient.makeRuntimeTaskCancelRequest(
            endpoint: endpoint,
            token: token,
            taskID: taskID
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(RuntimeTaskActionResponse.self, from: data)
    }

    public func approveRuntimeTask(
        taskID: String,
        approval: RuntimeTaskApprovalRequest
    ) async throws -> RuntimeTaskActionResponse {
        let request = try MobileBridgeClient.makeRuntimeTaskApprovalRequest(
            endpoint: endpoint,
            token: token,
            taskID: taskID,
            approval: approval
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        return try JSONDecoder.mobileBridge.decode(RuntimeTaskActionResponse.self, from: data)
    }

    public func downloadAsset(downloadURL: String) async throws -> DownloadedAsset {
        let request = MobileBridgeClient.makeAssetDownloadRequest(
            endpoint: endpoint,
            token: token,
            downloadURL: downloadURL
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        let mimeType = (response as? HTTPURLResponse)?.value(forHTTPHeaderField: "Content-Type") ?? "application/octet-stream"
        return DownloadedAsset(data: data, mimeType: mimeType)
    }

    public func fetchTaskEvents(eventsURL: String) async throws -> [TaskEvent] {
        let request = MobileBridgeClient.makeTaskEventsRequest(
            endpoint: endpoint,
            token: token,
            eventsURL: eventsURL
        )
        let (data, response) = try await session.data(for: request)
        try validate(response: response, data: data)
        guard let text = String(data: data, encoding: .utf8) else {
            throw TaskEventParser.ParseError.invalidData
        }
        return try TaskEventParser.parse(text)
    }

    private func validate(response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else {
            throw ClientError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            let bridgeError = try? JSONDecoder.mobileBridge.decode(BridgeErrorResponse.self, from: data)
            throw ClientError.httpStatus(http.statusCode, bridgeError)
        }
    }
}
