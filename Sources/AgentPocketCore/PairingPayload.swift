import Foundation

public struct PairingPayload: Equatable, Sendable {
    public enum ValidationError: Error, Equatable {
        case unsupportedVersion
        case expired
    }

    public let version: Int
    public let endpoint: AgentEndpoint
    public let runtime: String
    public let displayName: String
    public let pairingCode: String
    public let expiresAt: Date

    public init(jsonString: String, now: Date = Date()) throws {
        let data = Data(jsonString.utf8)
        let decoder = JSONDecoder.mobileBridge
        decoder.dateDecodingStrategy = .iso8601
        let decoded = try decoder.decode(PairingPayloadDTO.self, from: data)

        guard decoded.version == 1 else {
            throw ValidationError.unsupportedVersion
        }
        guard decoded.expiresAt > now else {
            throw ValidationError.expired
        }

        self.version = decoded.version
        self.endpoint = try AgentEndpoint(
            rawURL: decoded.endpoint,
            runtime: decoded.runtime,
            displayName: decoded.displayName
        )
        self.runtime = decoded.runtime
        self.displayName = decoded.displayName
        self.pairingCode = decoded.pairingCode
        self.expiresAt = decoded.expiresAt
    }
}

private struct PairingPayloadDTO: Decodable {
    let version: Int
    let endpoint: String
    let runtime: String
    let displayName: String
    let pairingCode: String
    let expiresAt: Date

    private enum CodingKeys: String, CodingKey {
        case version
        case endpoint
        case runtime
        case displayName = "display_name"
        case pairingCode = "pairing_code"
        case expiresAt = "expires_at"
    }
}
