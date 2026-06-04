import AgentPocketCore
import Foundation

public enum ConnectionCheckError: Error, Equatable, Sendable {
    case missingPhotoEdit
    case missingVision
}

@MainActor
public protocol ConnectionChecking {
    func check(endpoint: AgentEndpoint, token: String) async throws -> ConnectedRuntime
}

@MainActor
public protocol PairingExchanging {
    func exchange(
        endpoint: AgentEndpoint,
        pairingCode: String,
        deviceName: String,
        devicePublicID: String
    ) async throws -> PairingExchangeResponse
}

public struct MobileBridgeConnectionChecker: ConnectionChecking {
    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    public func check(endpoint: AgentEndpoint, token: String) async throws -> ConnectedRuntime {
        let client = MobileBridgeHTTPClient(endpoint: endpoint, token: token, session: session)
        let health = try await client.fetchHealth()
        let capabilities = try await client.fetchCapabilities()

        guard capabilities.tasks.photoEdit.styles.isEmpty == false else {
            throw ConnectionCheckError.missingPhotoEdit
        }

        return ConnectedRuntime(
            displayName: endpoint.displayName,
            runtime: health.runtime,
            runtimeVersion: health.runtimeVersion
        )
    }
}

public struct MobileBridgePairingExchanger: PairingExchanging {
    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    public func exchange(
        endpoint: AgentEndpoint,
        pairingCode: String,
        deviceName: String,
        devicePublicID: String
    ) async throws -> PairingExchangeResponse {
        try await MobileBridgeHTTPClient(
            endpoint: endpoint,
            token: "",
            session: session
        ).exchangePairingCode(
            pairingCode: pairingCode,
            deviceName: deviceName,
            devicePublicID: devicePublicID
        )
    }
}

@MainActor
public protocol PairingPayloadRefreshing {
    func refreshPairingPayload(endpoint: AgentEndpoint) async throws -> String
}

public struct MobileBridgePairingPayloadRefresher: PairingPayloadRefreshing {
    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    public func refreshPairingPayload(endpoint: AgentEndpoint) async throws -> String {
        try await MobileBridgeHTTPClient(
            endpoint: endpoint,
            token: "",
            session: session
        ).fetchDevelopmentPairingPayload()
    }
}

@MainActor
public final class ConnectionViewModel: ObservableObject {
    @Published public var state: ConnectionState
    @Published public var endpointText: String
    @Published public var tokenText: String
    @Published public var discoveredRuntimes: [DiscoveredRuntime]
    @Published public private(set) var activeConnection: StoredConnection?
    private let connectionChecker: any ConnectionChecking
    private let pairingExchanger: any PairingExchanging
    private let runtimeDiscoverer: any RuntimeDiscovering
    private let pairingPayloadRefresher: any PairingPayloadRefreshing
    private let connectionStore: any ConnectionStoring

    public init(
        state: ConnectionState = .idle,
        endpointText: String = "",
        tokenText: String = "",
        discoveredRuntimes: [DiscoveredRuntime] = [],
        activeConnection: StoredConnection? = nil,
        connectionChecker: any ConnectionChecking = MobileBridgeConnectionChecker(),
        pairingExchanger: any PairingExchanging = MobileBridgePairingExchanger(),
        runtimeDiscoverer: any RuntimeDiscovering = BonjourRuntimeDiscoverer(),
        pairingPayloadRefresher: any PairingPayloadRefreshing = MobileBridgePairingPayloadRefresher(),
        connectionStore: any ConnectionStoring = KeychainConnectionStore()
    ) {
        self.state = state
        self.endpointText = endpointText
        self.tokenText = tokenText
        self.discoveredRuntimes = discoveredRuntimes
        self.activeConnection = activeConnection
        self.connectionChecker = connectionChecker
        self.pairingExchanger = pairingExchanger
        self.runtimeDiscoverer = runtimeDiscoverer
        self.pairingPayloadRefresher = pairingPayloadRefresher
        self.connectionStore = connectionStore
    }

    public func beginScanning() {
        state = .scanning
    }

    public func cancelScanning() {
        state = .idle
    }

    public func beginDiscovery() {
        state = .discovering
    }

    public func discoverLocalRuntimes(
        timeout: TimeInterval = 2.5,
        autoPairSingleRuntime: Bool = false,
        showsNoResultsFailure: Bool = true,
        fallbackStateWhenNoResults: ConnectionState? = nil,
        now: Date = Date(),
        deviceName: String = "Agent Pocket",
        devicePublicID: String = "agent-pocket-device"
    ) async {
        beginDiscovery()
        discoveredRuntimes = []
        let runtimes: [DiscoveredRuntime]
        do {
            runtimes = try await runtimeDiscoverer.discover(timeout: timeout)
        } catch RuntimeDiscoveryError.searchFailed {
            state = .localNetworkPermissionRequired
            return
        } catch {
            state = .failed(message: "Could not search the local network. Check Local Network permission and try again.")
            return
        }
        guard runtimes.isEmpty == false else {
            if let fallbackStateWhenNoResults {
                state = fallbackStateWhenNoResults
            } else {
                state = showsNoResultsFailure
                    ? .failed(message: "No local agent runtime found. Scan a pairing QR or enter an endpoint.")
                    : .idle
            }
            return
        }
        discoveredRuntimes = runtimes
        if autoPairSingleRuntime,
           runtimes.count == 1 {
            await connectDiscoveredRuntime(
                runtimes[0],
                now: now,
                deviceName: deviceName,
                devicePublicID: devicePublicID
            )
            return
        }
        state = .idle
    }

    public func connectDiscoveredRuntime(
        _ runtime: DiscoveredRuntime,
        now: Date = Date(),
        deviceName: String,
        devicePublicID: String
    ) async {
        let pairingPayload: String
        if let discoveredPayload = runtime.pairingPayload {
            pairingPayload = discoveredPayload
        } else {
            do {
                state = .testing
                pairingPayload = try await pairingPayloadRefresher.refreshPairingPayload(endpoint: runtime.endpoint)
            } catch {
                endpointText = runtime.endpoint.baseURL.absoluteString
                state = .failed(message: "Scan the pairing QR shown by your local agent to finish connecting.")
                return
            }
        }

        do {
            try await pairWithPayload(
                pairingPayload,
                now: now,
                deviceName: deviceName,
                devicePublicID: devicePublicID
            )
        } catch let error where Self.isPairingAlreadyUsed(error) {
            do {
                let refreshedPayload = try await pairingPayloadRefresher.refreshPairingPayload(endpoint: runtime.endpoint)
                try await pairWithPayload(
                    refreshedPayload,
                    now: now,
                    deviceName: deviceName,
                    devicePublicID: devicePublicID
                )
            } catch {
                mapPairingError(error)
            }
        } catch {
            mapPairingError(error)
        }
    }

    public func validateManualEntry() {
        let trimmedToken = tokenText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedToken.isEmpty else {
            state = .failed(message: "Enter the mobile token from your local agent.")
            return
        }

        do {
            _ = try AgentEndpoint(rawURL: endpointText)
            state = .testing
        } catch AgentEndpoint.ValidationError.remoteEndpointRequiresHTTPS {
            state = .failed(message: "Remote endpoints must use HTTPS.")
        } catch {
            state = .failed(message: "Enter a valid local agent endpoint.")
        }
    }

    public func connectManually() async {
        let trimmedToken = tokenText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedToken.isEmpty else {
            state = .failed(message: "Enter the mobile token from your local agent.")
            return
        }

        let endpoint: AgentEndpoint
        do {
            endpoint = try AgentEndpoint(rawURL: endpointText)
        } catch AgentEndpoint.ValidationError.remoteEndpointRequiresHTTPS {
            state = .failed(message: "Remote endpoints must use HTTPS.")
            return
        } catch {
            state = .failed(message: "Enter a valid local agent endpoint.")
            return
        }

        state = .testing
        do {
            let runtime = try await connectionChecker.check(endpoint: endpoint, token: trimmedToken)
            activeConnection = try saveConnection(
                endpoint: endpoint,
                token: trimmedToken,
                runtime: runtime,
                tokenExpiresAt: nil
            )
            markConnected(runtime)
        } catch ConnectionStoreError.saveFailed {
            state = .failed(message: "Could not save local agent credentials.")
        } catch ConnectionCheckError.missingPhotoEdit {
            state = .missingPhotoEdit
        } catch MobileBridgeHTTPClient.ClientError.httpStatus(401, _) {
            state = .unauthorized
        } catch let error as URLError where error.isLikelyCertificateProblem {
            state = .invalidCertificate
        } catch let error as URLError where error.isLikelyOffline {
            state = .offline
        } catch {
            state = .failed(message: "Could not connect to your local agent.")
        }
    }

    public func connectWithPairingPayload(
        _ jsonString: String,
        now: Date = Date(),
        deviceName: String,
        devicePublicID: String
    ) async {
        do {
            try await pairWithPayload(
                jsonString,
                now: now,
                deviceName: deviceName,
                devicePublicID: devicePublicID
            )
        } catch {
            mapPairingError(error)
        }
    }

    private func pairWithPayload(
        _ jsonString: String,
        now: Date,
        deviceName: String,
        devicePublicID: String
    ) async throws {
        let payload: PairingPayload
        do {
            payload = try PairingPayload(jsonString: jsonString, now: now)
        } catch PairingPayload.ValidationError.expired {
            throw PairingPayload.ValidationError.expired
        } catch PairingPayload.ValidationError.unsupportedVersion {
            throw PairingPayload.ValidationError.unsupportedVersion
        } catch AgentEndpoint.ValidationError.remoteEndpointRequiresHTTPS {
            throw AgentEndpoint.ValidationError.remoteEndpointRequiresHTTPS
        } catch {
            throw PairingFlowError.unreadablePayload
        }

        state = .testing
        let exchange = try await pairingExchanger.exchange(
            endpoint: payload.endpoint,
            pairingCode: payload.pairingCode,
            deviceName: deviceName,
            devicePublicID: devicePublicID
        )
        let runtime = try await connectionChecker.check(
            endpoint: payload.endpoint,
            token: exchange.mobileToken
        )
        activeConnection = try saveConnection(
            endpoint: payload.endpoint,
            token: exchange.mobileToken,
            runtime: runtime,
            tokenExpiresAt: exchange.tokenExpiresAt
        )
        markConnected(runtime)
    }

    private static func isPairingAlreadyUsed(_ error: Error) -> Bool {
        if case MobileBridgeHTTPClient.ClientError.httpStatus(409, let bridgeError) = error,
           bridgeError?.error.code == "pairing_already_used" {
            return true
        }
        return false
    }

    private func mapPairingError(_ error: Error) {
        switch error {
        case ConnectionStoreError.saveFailed:
            state = .failed(message: "Could not save local agent credentials.")
        case ConnectionCheckError.missingPhotoEdit:
            state = .missingPhotoEdit
        case PairingPayload.ValidationError.expired:
            state = .failed(message: "Pairing code expired.")
        case PairingPayload.ValidationError.unsupportedVersion:
            state = .failed(message: "Pairing QR is not supported by this app version.")
        case AgentEndpoint.ValidationError.remoteEndpointRequiresHTTPS:
            state = .failed(message: "Remote endpoints must use HTTPS.")
        case MobileBridgeHTTPClient.ClientError.httpStatus(409, let bridgeError)
            where bridgeError?.error.code == "pairing_already_used":
            state = .failed(message: "Pairing code already used. Scan a new QR code.")
        case MobileBridgeHTTPClient.ClientError.httpStatus(404, let bridgeError)
            where bridgeError?.error.code == "pairing_expired":
            state = .failed(message: "Pairing code expired.")
        case MobileBridgeHTTPClient.ClientError.httpStatus(401, _):
            state = .unauthorized
        case PairingFlowError.unreadablePayload:
            state = .failed(message: "Pairing QR could not be read.")
        default:
            if let urlError = error as? URLError, urlError.isLikelyCertificateProblem {
                state = .invalidCertificate
            } else if let urlError = error as? URLError, urlError.isLikelyOffline {
                state = .offline
            } else {
                state = .failed(message: "Could not pair with your local agent.")
            }
        }
    }

    public func restoreSavedConnection() async {
        _ = await restoreSavedConnectionIfAvailable()
    }

    public func restoreSavedConnectionOrDiscoverNearby(
        timeout: TimeInterval = 2.5,
        now: Date = Date(),
        deviceName: String = "Agent Pocket",
        devicePublicID: String = "agent-pocket-device"
    ) async {
        if case .connected = state {
            return
        }
        let restoreOutcome = await restoreSavedConnectionIfAvailable()
        switch restoreOutcome {
        case .noSavedConnection:
            await discoverLocalRuntimes(
                timeout: timeout,
                autoPairSingleRuntime: true,
                showsNoResultsFailure: false,
                now: now,
                deviceName: deviceName,
                devicePublicID: devicePublicID
            )
        case .savedConnectionOffline:
            await discoverLocalRuntimes(
                timeout: timeout,
                autoPairSingleRuntime: true,
                showsNoResultsFailure: false,
                fallbackStateWhenNoResults: .offline,
                now: now,
                deviceName: deviceName,
                devicePublicID: devicePublicID
            )
        case .attemptedSavedConnection:
            return
        }
    }

    private func restoreSavedConnectionIfAvailable() async -> RestoreSavedConnectionOutcome {
        let savedConnection: StoredConnection?
        do {
            savedConnection = try connectionStore.load()
        } catch {
            activeConnection = nil
            state = .idle
            return .noSavedConnection
        }
        guard let savedConnection else {
            activeConnection = nil
            state = .idle
            return .noSavedConnection
        }

        state = .testing
        do {
            let runtime = try await connectionChecker.check(
                endpoint: savedConnection.endpoint,
                token: savedConnection.mobileToken
            )
            activeConnection = savedConnection
            markConnected(runtime)
            return .attemptedSavedConnection
        } catch ConnectionCheckError.missingPhotoEdit {
            activeConnection = nil
            state = .missingPhotoEdit
            return .attemptedSavedConnection
        } catch MobileBridgeHTTPClient.ClientError.httpStatus(401, _) {
            try? connectionStore.clear()
            activeConnection = nil
            state = .unauthorized
            return .attemptedSavedConnection
        } catch let error as URLError where error.isLikelyCertificateProblem {
            activeConnection = nil
            state = .invalidCertificate
            return .attemptedSavedConnection
        } catch let error as URLError where error.isLikelyOffline {
            activeConnection = nil
            state = .offline
            return .savedConnectionOffline
        } catch {
            activeConnection = nil
            state = .failed(message: "Could not restore local agent connection.")
            return .attemptedSavedConnection
        }
    }

    public func forgetSavedConnection() {
        do {
            try connectionStore.clear()
            activeConnection = nil
            endpointText = ""
            tokenText = ""
            discoveredRuntimes = []
            state = .idle
        } catch {
            state = .failed(message: "Could not forget local agent connection.")
        }
    }

    public func markConnected(displayName: String, runtime: String, runtimeVersion: String) {
        markConnected(
            ConnectedRuntime(
                displayName: displayName,
                runtime: runtime,
                runtimeVersion: runtimeVersion
            )
        )
    }

    private func markConnected(_ runtime: ConnectedRuntime) {
        discoveredRuntimes = []
        state = .connected(runtime)
    }

    private func saveConnection(
        endpoint: AgentEndpoint,
        token: String,
        runtime: ConnectedRuntime,
        tokenExpiresAt: String?
    ) throws -> StoredConnection {
        do {
            let connection = StoredConnection(
                endpoint: endpoint,
                displayName: runtime.displayName,
                runtime: runtime.runtime,
                runtimeVersion: runtime.runtimeVersion,
                mobileToken: token,
                tokenExpiresAt: tokenExpiresAt
            )
            try connectionStore.save(connection)
            return connection
        } catch {
            throw ConnectionStoreError.saveFailed
        }
    }
}

private enum ConnectionStoreError: Error {
    case saveFailed
}

private enum RestoreSavedConnectionOutcome {
    case noSavedConnection
    case savedConnectionOffline
    case attemptedSavedConnection
}

private enum PairingFlowError: Error {
    case unreadablePayload
}

private extension URLError {
    var isLikelyCertificateProblem: Bool {
        switch code {
        case .serverCertificateUntrusted,
             .serverCertificateHasBadDate,
             .serverCertificateHasUnknownRoot,
             .serverCertificateNotYetValid,
             .secureConnectionFailed,
             .clientCertificateRejected,
             .clientCertificateRequired,
             .appTransportSecurityRequiresSecureConnection:
            return true
        default:
            return false
        }
    }

    var isLikelyOffline: Bool {
        switch code {
        case .cannotConnectToHost, .networkConnectionLost, .notConnectedToInternet, .timedOut:
            return true
        default:
            return false
        }
    }
}
