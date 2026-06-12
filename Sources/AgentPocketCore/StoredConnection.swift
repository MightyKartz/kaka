import Foundation
import Security

public struct StoredConnection: Equatable, Sendable {
    public let endpoint: AgentEndpoint
    public let displayName: String
    public let runtime: String
    public let runtimeVersion: String
    public let mobileToken: String
    public let tokenExpiresAt: String?
    public let tlsPublicKeySHA256: String?

    public var trustPolicy: MobileBridgeTrustPolicy {
        MobileBridgeTrustPolicy.policy(
            for: endpoint,
            tlsPublicKeySHA256: tlsPublicKeySHA256
        )
    }

    public init(
        endpoint: AgentEndpoint,
        displayName: String,
        runtime: String,
        runtimeVersion: String,
        mobileToken: String,
        tokenExpiresAt: String?,
        tlsPublicKeySHA256: String? = nil
    ) {
        self.endpoint = endpoint
        self.displayName = displayName
        self.runtime = runtime
        self.runtimeVersion = runtimeVersion
        self.mobileToken = mobileToken
        self.tokenExpiresAt = tokenExpiresAt
        self.tlsPublicKeySHA256 = MobileBridgeTrustPolicy.normalizePublicKeySHA256(tlsPublicKeySHA256)
    }

    public static func == (lhs: StoredConnection, rhs: StoredConnection) -> Bool {
        lhs.endpoint.baseURL == rhs.endpoint.baseURL
            && lhs.displayName == rhs.displayName
            && lhs.runtime == rhs.runtime
            && lhs.runtimeVersion == rhs.runtimeVersion
            && lhs.mobileToken == rhs.mobileToken
            && lhs.tokenExpiresAt == rhs.tokenExpiresAt
            && lhs.tlsPublicKeySHA256 == rhs.tlsPublicKeySHA256
    }
}

extension StoredConnection: Codable {
    private enum CodingKeys: String, CodingKey {
        case endpoint
        case displayName = "display_name"
        case runtime
        case runtimeVersion = "runtime_version"
        case mobileToken = "mobile_token"
        case tokenExpiresAt = "token_expires_at"
        case tlsPublicKeySHA256 = "tls_public_key_sha256"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let endpointURL = try container.decode(String.self, forKey: .endpoint)
        endpoint = try AgentEndpoint(rawURL: endpointURL)
        displayName = try container.decode(String.self, forKey: .displayName)
        runtime = try container.decode(String.self, forKey: .runtime)
        runtimeVersion = try container.decode(String.self, forKey: .runtimeVersion)
        mobileToken = try container.decode(String.self, forKey: .mobileToken)
        tokenExpiresAt = try container.decodeIfPresent(String.self, forKey: .tokenExpiresAt)
        tlsPublicKeySHA256 = MobileBridgeTrustPolicy.normalizePublicKeySHA256(
            try container.decodeIfPresent(String.self, forKey: .tlsPublicKeySHA256)
        )
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(endpoint.baseURL.absoluteString, forKey: .endpoint)
        try container.encode(displayName, forKey: .displayName)
        try container.encode(runtime, forKey: .runtime)
        try container.encode(runtimeVersion, forKey: .runtimeVersion)
        try container.encode(mobileToken, forKey: .mobileToken)
        try container.encodeIfPresent(tokenExpiresAt, forKey: .tokenExpiresAt)
        try container.encodeIfPresent(tlsPublicKeySHA256, forKey: .tlsPublicKeySHA256)
    }
}

public protocol ConnectionStoring {
    func load() throws -> StoredConnection?
    func save(_ connection: StoredConnection) throws
    func clear() throws
}

public final class KeychainConnectionStore: ConnectionStoring {
    public enum StoreError: Error, Equatable {
        case unexpectedStatus(OSStatus)
        case invalidPayload
    }

    private let service: String
    private let account: String
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    public init(
        service: String = "com.kaka.AgentPocket.connection",
        account: String = "default"
    ) {
        self.service = service
        self.account = account
        self.encoder = .mobileBridge
        self.decoder = .mobileBridge
    }

    public func load() throws -> StoredConnection? {
        var query = baseQuery()
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound {
            return nil
        }
        guard status == errSecSuccess else {
            throw StoreError.unexpectedStatus(status)
        }
        guard let data = result as? Data else {
            throw StoreError.invalidPayload
        }
        return try decoder.decode(StoredConnection.self, from: data)
    }

    public func save(_ connection: StoredConnection) throws {
        let data = try encoder.encode(connection)
        try clear()

        var query = baseQuery()
        query[kSecValueData as String] = data
        query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly

        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw StoreError.unexpectedStatus(status)
        }
    }

    public func clear() throws {
        let status = SecItemDelete(baseQuery() as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw StoreError.unexpectedStatus(status)
        }
    }

    private func baseQuery() -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }
}
