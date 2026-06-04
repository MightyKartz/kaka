import Foundation

public enum MobileBridgeClient {
    public static func makeRequest(endpoint: AgentEndpoint, path: String, token: String? = nil) -> URLRequest {
        let trimmedBase = endpoint.baseURL.absoluteString.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let trimmedPath = path.hasPrefix("/") ? String(path.dropFirst()) : path
        let url = URL(string: "\(trimmedBase)/\(trimmedPath)")!

        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let token, !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    public static func makeAssetUploadRequest(
        endpoint: AgentEndpoint,
        token: String,
        upload: PreparedImageUpload,
        boundary: String = "Boundary-\(UUID().uuidString)"
    ) throws -> URLRequest {
        var request = makeRequest(endpoint: endpoint, path: "/mobile/v1/assets", token: token)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let metadataData = try JSONEncoder.mobileBridge.encode(upload.metadata)
        let metadata = String(data: metadataData, encoding: .utf8) ?? "{}"
        request.httpBody = MultipartFormData.build(
            boundary: boundary,
            fields: ["metadata": metadata],
            fileFieldName: "file",
            fileName: upload.fileName,
            mimeType: upload.mimeType,
            fileData: upload.data
        )
        return request
    }

    public static func makePairingExchangeRequest(
        endpoint: AgentEndpoint,
        pairingCode: String,
        deviceName: String,
        devicePublicID: String
    ) throws -> URLRequest {
        var request = makeRequest(endpoint: endpoint, path: "/mobile/v1/pairing/exchange")
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder.mobileBridge.encode(
            PairingExchangeRequest(
                pairingCode: pairingCode,
                deviceName: deviceName,
                devicePublicID: devicePublicID
            )
        )
        return request
    }

    public static func makePhotoEditTaskRequest(
        endpoint: AgentEndpoint,
        token: String,
        task: PhotoEditTaskRequest
    ) throws -> URLRequest {
        var request = makeRequest(endpoint: endpoint, path: "/mobile/v1/tasks/photo-edit", token: token)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder.mobileBridge.encode(task)
        return request
    }

    public static func makeVisionTaskRequest(
        endpoint: AgentEndpoint,
        token: String,
        task: VisionTaskRequest
    ) throws -> URLRequest {
        var request = makeRequest(endpoint: endpoint, path: "/mobile/v1/tasks/vision", token: token)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder.mobileBridge.encode(task)
        return request
    }

    public static func makeImageIntakeTaskRequest(
        endpoint: AgentEndpoint,
        token: String,
        task: ImageIntakeTaskRequest
    ) throws -> URLRequest {
        var request = makeRequest(endpoint: endpoint, path: "/mobile/v1/tasks/image-intake", token: token)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder.mobileBridge.encode(task)
        return request
    }

    public static func makeTaskStatusRequest(
        endpoint: AgentEndpoint,
        token: String,
        taskID: String
    ) -> URLRequest {
        var request = makeRequest(endpoint: endpoint, path: "/mobile/v1/tasks/\(taskID)", token: token)
        request.httpMethod = "GET"
        return request
    }

    public static func makeAssetDownloadRequest(
        endpoint: AgentEndpoint,
        token: String,
        downloadURL: String
    ) -> URLRequest {
        var request = makeRequest(endpoint: endpoint, path: downloadURL, token: token)
        request.httpMethod = "GET"
        return request
    }

    public static func makeTaskEventsRequest(
        endpoint: AgentEndpoint,
        token: String,
        eventsURL: String
    ) -> URLRequest {
        var request = makeRequest(endpoint: endpoint, path: eventsURL, token: token)
        request.httpMethod = "GET"
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        return request
    }
}
