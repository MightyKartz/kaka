import AgentPocketCore
@preconcurrency import Foundation

public struct DiscoveredRuntime: Identifiable, Equatable, Sendable {
    public let displayName: String
    public let endpoint: AgentEndpoint
    public let pairingPayload: String?

    public var id: String {
        endpoint.baseURL.absoluteString
    }

    public init(displayName: String, endpoint: AgentEndpoint, pairingPayload: String?) {
        self.displayName = displayName
        self.endpoint = endpoint
        self.pairingPayload = pairingPayload
    }
}

@MainActor
public protocol RuntimeDiscovering {
    func discover(timeout: TimeInterval) async throws -> [DiscoveredRuntime]
}

public enum RuntimeDiscoveryError: Error, Equatable, Sendable {
    case searchFailed
}

public final class BonjourRuntimeDiscoverer: NSObject, RuntimeDiscovering {
    private var activeSession: BonjourDiscoverySession?

    public override init() {}

    public func discover(timeout: TimeInterval = 2.5) async throws -> [DiscoveredRuntime] {
        try await withCheckedThrowingContinuation { continuation in
            let session = BonjourDiscoverySession { [weak self] result in
                self?.activeSession = nil
                continuation.resume(with: result)
            }
            activeSession = session
            session.start(timeout: timeout)
        }
    }
}

private final class BonjourDiscoverySession: NSObject, @unchecked Sendable, NetServiceBrowserDelegate, NetServiceDelegate {
    private let browser = NetServiceBrowser()
    private var services: [NetService] = []
    private var runtimes: [DiscoveredRuntime] = []
    private var timer: Timer?
    private var didFinish = false
    private let onFinish: (Result<[DiscoveredRuntime], Error>) -> Void

    init(onFinish: @escaping (Result<[DiscoveredRuntime], Error>) -> Void) {
        self.onFinish = onFinish
    }

    func start(timeout: TimeInterval) {
        browser.delegate = self
        browser.searchForServices(ofType: "_agent-pocket._tcp.", inDomain: "local.")
        timer = Timer.scheduledTimer(withTimeInterval: timeout, repeats: false) { [weak self] _ in
            self?.finish()
        }
    }

    func netServiceBrowser(_ browser: NetServiceBrowser, didFind service: NetService, moreComing: Bool) {
        services.append(service)
        service.delegate = self
        service.resolve(withTimeout: 1.2)
    }

    func netServiceBrowser(_ browser: NetServiceBrowser, didNotSearch errorDict: [String: NSNumber]) {
        finish(error: RuntimeDiscoveryError.searchFailed)
    }

    func netServiceBrowserDidStopSearch(_ browser: NetServiceBrowser) {
        finish()
    }

    func netServiceDidResolveAddress(_ sender: NetService) {
        guard let runtime = makeRuntime(from: sender), runtimes.contains(runtime) == false else {
            return
        }
        runtimes.append(runtime)
    }

    private func finish(error: Error? = nil) {
        guard didFinish == false else {
            return
        }
        didFinish = true
        timer?.invalidate()
        browser.stop()
        browser.delegate = nil
        services.forEach {
            $0.stop()
            $0.delegate = nil
        }
        if let error {
            onFinish(.failure(error))
        } else {
            onFinish(.success(runtimes))
        }
    }

    private func makeRuntime(from service: NetService) -> DiscoveredRuntime? {
        let txt = textRecord(from: service)
        let displayName = txt["display_name"] ?? service.name
        let endpointString: String
        if let endpoint = txt["endpoint"] {
            endpointString = endpoint
        } else {
            guard let host = txt["host"] ?? service.hostName?.trimmingCharacters(in: CharacterSet(charactersIn: ".")),
                  service.port > 0 else {
                return nil
            }
            let scheme = txt["scheme"] ?? "http"
            endpointString = "\(scheme)://\(host):\(service.port)"
        }

        guard let endpoint = try? AgentEndpoint(
            rawURL: endpointString,
            runtime: txt["runtime"] ?? "hermes",
            displayName: displayName
        ) else {
            return nil
        }

        let pairingPayload = txt["pairing_payload"] ?? makePairingPayload(
            endpoint: endpoint.baseURL.absoluteString,
            displayName: displayName,
            txt: txt
        )
        return DiscoveredRuntime(
            displayName: displayName,
            endpoint: endpoint,
            pairingPayload: pairingPayload
        )
    }

    private func textRecord(from service: NetService) -> [String: String] {
        guard let data = service.txtRecordData() else {
            return [:]
        }
        let rawRecord = NetService.dictionary(fromTXTRecord: data)
        return rawRecord.reduce(into: [String: String]()) { result, item in
            result[item.key] = String(data: item.value, encoding: .utf8)
        }
    }

    private func makePairingPayload(
        endpoint: String,
        displayName: String,
        txt: [String: String]
    ) -> String? {
        guard let pairingCode = txt["pairing_code"] else {
            return nil
        }
        let payload: [String: Any] = [
            "version": 1,
            "endpoint": endpoint,
            "runtime": txt["runtime"] ?? "hermes",
            "display_name": displayName,
            "pairing_code": pairingCode,
            "expires_at": txt["expires_at"] ?? ISO8601DateFormatter().string(from: Date().addingTimeInterval(300)),
        ].merging(optionalPairingTLSFields(from: txt)) { current, _ in current }
        guard let data = try? JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys]) else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }

    private func optionalPairingTLSFields(from txt: [String: String]) -> [String: Any] {
        var fields: [String: Any] = [:]
        if let fingerprint = txt["tls_public_key_sha256"],
           MobileBridgeTrustPolicy.normalizePublicKeySHA256(fingerprint) != nil {
            fields["tls_public_key_sha256"] = fingerprint
        }
        if let required = txt["trusted_local_tls_required"] {
            fields["trusted_local_tls_required"] = required == "true" || required == "1"
        }
        if let label = txt["tls_certificate_label"],
           label.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false {
            fields["tls_certificate_label"] = label
        }
        return fields
    }
}
