import Foundation

public struct AgentEndpoint: Equatable, Sendable {
    public enum ValidationError: Error, Equatable {
        case invalidURL
        case missingScheme
        case unsupportedScheme
        case remoteEndpointRequiresHTTPS
    }

    public let baseURL: URL
    public let displayName: String
    public let runtime: String?
    public let isTrustedLocalDevelopmentEndpoint: Bool

    public init(rawURL: String, runtime: String? = nil, displayName: String? = nil) throws {
        let trimmed = rawURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed), let host = url.host, !host.isEmpty else {
            throw ValidationError.invalidURL
        }
        guard let scheme = url.scheme?.lowercased(), !scheme.isEmpty else {
            throw ValidationError.missingScheme
        }

        let isLocal = Self.isLocalDevelopmentHost(host)
        switch scheme {
        case "https":
            break
        case "http":
            guard isLocal else {
                throw ValidationError.remoteEndpointRequiresHTTPS
            }
        default:
            throw ValidationError.unsupportedScheme
        }

        self.baseURL = url
        self.displayName = displayName ?? host
        self.runtime = runtime
        self.isTrustedLocalDevelopmentEndpoint = isLocal && scheme == "http"
    }

    private static func isLocalDevelopmentHost(_ host: String) -> Bool {
        let normalized = host.trimmingCharacters(in: CharacterSet(charactersIn: "[]")).lowercased()
        return normalized == "localhost"
            || normalized == "127.0.0.1"
            || normalized == "::1"
            || normalized.hasSuffix(".local")
            || isPrivateIPv4Address(normalized)
    }

    private static func isPrivateIPv4Address(_ host: String) -> Bool {
        let parts = host.split(separator: ".")
        guard parts.count == 4 else {
            return false
        }

        let octets = parts.compactMap { part -> Int? in
            guard let value = Int(part), (0...255).contains(value) else {
                return nil
            }
            return value
        }
        guard octets.count == 4 else {
            return false
        }

        switch (octets[0], octets[1]) {
        case (10, _), (192, 168), (169, 254):
            return true
        case (172, 16...31), (100, 64...127):
            return true
        default:
            return false
        }
    }
}
