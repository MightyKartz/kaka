import Foundation

public struct PairingPayload: Equatable, Sendable {
    public enum ValidationError: Error, Equatable {
        case unsupportedVersion
        case expired
        case missingRequiredTLSPublicKeyFingerprint
        case malformedRequiredTLSPublicKeyFingerprint
        case trustedLocalTLSRequiresHTTPSEndpoint
    }

    public let version: Int
    public let endpoint: AgentEndpoint
    public let runtime: String
    public let displayName: String
    public let pairingCode: String
    public let expiresAt: Date
    public let tlsPublicKeySHA256: String?
    public let trustedLocalTLSRequired: Bool
    public let tlsCertificateLabel: String?

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

        let endpoint = try AgentEndpoint(
            rawURL: decoded.endpoint,
            runtime: decoded.runtime,
            displayName: decoded.displayName
        )
        let trustedLocalTLSRequired = decoded.trustedLocalTLSRequired ?? false
        let tlsPublicKeySHA256 = MobileBridgeTrustPolicy.normalizePublicKeySHA256(decoded.tlsPublicKeySHA256)
        if trustedLocalTLSRequired {
            guard endpoint.baseURL.scheme?.lowercased() == "https" else {
                throw ValidationError.trustedLocalTLSRequiresHTTPSEndpoint
            }
            guard let rawFingerprint = decoded.tlsPublicKeySHA256?.trimmingCharacters(in: .whitespacesAndNewlines),
                  rawFingerprint.isEmpty == false else {
                throw ValidationError.missingRequiredTLSPublicKeyFingerprint
            }
            guard tlsPublicKeySHA256 != nil else {
                throw ValidationError.malformedRequiredTLSPublicKeyFingerprint
            }
        }

        self.version = decoded.version
        self.endpoint = endpoint
        self.runtime = decoded.runtime
        self.displayName = decoded.displayName
        self.pairingCode = decoded.pairingCode
        self.expiresAt = decoded.expiresAt
        self.tlsPublicKeySHA256 = tlsPublicKeySHA256
        self.trustedLocalTLSRequired = trustedLocalTLSRequired
        self.tlsCertificateLabel = decoded.tlsCertificateLabel?.trimmingCharacters(in: .whitespacesAndNewlines).nilIfEmpty
    }
}

private struct PairingPayloadDTO: Decodable {
    let version: Int
    let endpoint: String
    let runtime: String
    let displayName: String
    let pairingCode: String
    let expiresAt: Date
    let tlsPublicKeySHA256: String?
    let trustedLocalTLSRequired: Bool?
    let tlsCertificateLabel: String?

    private enum CodingKeys: String, CodingKey {
        case version
        case endpoint
        case runtime
        case displayName = "display_name"
        case pairingCode = "pairing_code"
        case expiresAt = "expires_at"
        case tlsPublicKeySHA256 = "tls_public_key_sha256"
        case trustedLocalTLSRequired = "trusted_local_tls_required"
        case tlsCertificateLabel = "tls_certificate_label"
    }
}

private extension String {
    var nilIfEmpty: String? {
        isEmpty ? nil : self
    }
}
