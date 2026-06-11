import Foundation
import CryptoKit
import Security

public enum MobileBridgeTrustPolicy: Equatable, Sendable {
    case systemDefault
    case pinnedPublicKeySHA256(String)

    public static func policy(
        for endpoint: AgentEndpoint,
        tlsPublicKeySHA256: String?
    ) -> MobileBridgeTrustPolicy {
        guard endpoint.baseURL.scheme?.lowercased() == "https",
              let normalized = normalizePublicKeySHA256(tlsPublicKeySHA256) else {
            return .systemDefault
        }
        return .pinnedPublicKeySHA256(normalized)
    }

    public static func normalizePublicKeySHA256(_ value: String?) -> String? {
        guard let value else {
            return nil
        }
        let normalized = value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let hexCharacters = Set("0123456789abcdef")
        guard normalized.count == 64,
              normalized.allSatisfy({ hexCharacters.contains($0) }) else {
            return nil
        }
        return normalized
    }
}

public enum MobileBridgeURLSessionFactory {
    public static func makeSession(for policy: MobileBridgeTrustPolicy) -> URLSession {
        switch policy {
        case .systemDefault:
            return .shared
        case .pinnedPublicKeySHA256(let fingerprint):
            return URLSession(
                configuration: .ephemeral,
                delegate: MobileBridgePinnedTrustDelegate(pinnedPublicKeySHA256: fingerprint),
                delegateQueue: nil
            )
        }
    }
}

public final class MobileBridgePinnedTrustDelegate: NSObject, URLSessionDelegate {
    private let pinnedPublicKeySHA256: String

    public init(pinnedPublicKeySHA256: String) {
        self.pinnedPublicKeySHA256 = pinnedPublicKeySHA256
    }

    public func urlSession(
        _ session: URLSession,
        didReceive challenge: URLAuthenticationChallenge
    ) async -> (URLSession.AuthChallengeDisposition, URLCredential?) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let trust = challenge.protectionSpace.serverTrust else {
            return (.performDefaultHandling, nil)
        }

        guard Self.evaluateServerTrust(trust),
              let presentedSHA256 = Self.publicKeySHA256Hex(from: trust),
              Self.publicKeySHA256Matches(
                  presentedSHA256: presentedSHA256,
                  pinnedSHA256: pinnedPublicKeySHA256
              ) else {
            return (.cancelAuthenticationChallenge, nil)
        }

        return (.useCredential, URLCredential(trust: trust))
    }

    public static func publicKeySHA256Matches(
        presentedSHA256: String,
        pinnedSHA256: String
    ) -> Bool {
        guard let presented = MobileBridgeTrustPolicy.normalizePublicKeySHA256(presentedSHA256),
              let pinned = MobileBridgeTrustPolicy.normalizePublicKeySHA256(pinnedSHA256) else {
            return false
        }
        return presented == pinned
    }

    static func publicKeySHA256Hex(from trust: SecTrust) -> String? {
        guard let key = SecTrustCopyKey(trust),
              let keyData = SecKeyCopyExternalRepresentation(key, nil) as Data? else {
            return nil
        }
        return publicKeySHA256Hex(from: keyData)
    }

    static func publicKeySHA256Hex(from publicKeyData: Data) -> String {
        SHA256.hash(data: publicKeyData)
            .map { String(format: "%02x", $0) }
            .joined()
    }

    static func evaluateServerTrust(_ trust: SecTrust) -> Bool {
        var error: CFError?
        return SecTrustEvaluateWithError(trust, &error)
    }
}
