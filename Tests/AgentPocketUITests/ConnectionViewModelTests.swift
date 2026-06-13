import XCTest
import AgentPocketCore
@testable import AgentPocketUI

@MainActor
final class ConnectionViewModelTests: XCTestCase {
    func testStartsInIdleStateWithEmptyManualFields() {
        let viewModel = ConnectionViewModel()

        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertEqual(viewModel.endpointText, "")
        XCTAssertEqual(viewModel.tokenText, "")
    }

    func testBeginScanningSwitchesToScanningState() {
        let viewModel = ConnectionViewModel()

        viewModel.beginScanning()

        XCTAssertEqual(viewModel.state, .scanning)
    }

    func testCancelScanningReturnsToIdle() {
        let viewModel = ConnectionViewModel()
        viewModel.beginScanning()

        viewModel.cancelScanning()

        XCTAssertEqual(viewModel.state, .idle)
    }

    func testManualEndpointValidationRejectsHTTPRemoteURL() {
        let viewModel = ConnectionViewModel()
        viewModel.endpointText = "http://example.com"
        viewModel.tokenText = "token"

        viewModel.validateManualEntry()

        XCTAssertEqual(viewModel.state, .failed(message: "Remote endpoints must use HTTPS."))
    }

    func testManualEndpointValidationStartsTestingForHTTPSURL() {
        let viewModel = ConnectionViewModel()
        viewModel.endpointText = "https://hermes.example.com"
        viewModel.tokenText = "token"

        viewModel.validateManualEntry()

        XCTAssertEqual(viewModel.state, .testing)
    }

    func testManualConnectionChecksBridgeAndMarksConnected() async {
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Hermes Mac",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let viewModel = ConnectionViewModel(connectionChecker: checker)
        viewModel.endpointText = "https://hermes.example.com"
        viewModel.tokenText = " token "

        await viewModel.connectManually()

        XCTAssertEqual(
            viewModel.state,
            .connected(
                ConnectedRuntime(
                    displayName: "Hermes Mac",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            )
        )
        XCTAssertEqual(checker.calls.map(\.endpoint.baseURL.absoluteString), ["https://hermes.example.com"])
        XCTAssertEqual(checker.calls.map(\.token), ["token"])
    }

    func testManualConnectionSavesVerifiedCredential() async {
        let store = StubConnectionStore()
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Hermes Mac",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let viewModel = ConnectionViewModel(connectionChecker: checker, connectionStore: store)
        viewModel.endpointText = "https://hermes.example.com"
        viewModel.tokenText = " token "

        await viewModel.connectManually()

        XCTAssertEqual(store.savedConnections.map(\.endpoint.baseURL.absoluteString), ["https://hermes.example.com"])
        XCTAssertEqual(store.savedConnections.map(\.mobileToken), ["token"])
        XCTAssertEqual(store.savedConnections.map(\.displayName), ["Hermes Mac"])
        XCTAssertEqual(viewModel.activeConnection?.mobileToken, "token")
    }

    func testManualConnectionMapsUnauthorizedBridgeResponse() async {
        let viewModel = ConnectionViewModel(
            connectionChecker: StubConnectionChecker(error: MobileBridgeHTTPClient.ClientError.httpStatus(401, nil))
        )
        viewModel.endpointText = "https://hermes.example.com"
        viewModel.tokenText = "bad-token"

        await viewModel.connectManually()

        XCTAssertEqual(viewModel.state, .unauthorized)
    }

    func testManualConnectionMapsCertificateFailure() async {
        let viewModel = ConnectionViewModel(
            connectionChecker: StubConnectionChecker(error: URLError(.serverCertificateUntrusted))
        )
        viewModel.endpointText = "https://hermes.example.com"
        viewModel.tokenText = "token"

        await viewModel.connectManually()

        XCTAssertEqual(viewModel.state, .invalidCertificate)
    }

    func testManualConnectionMapsMissingPhotoEditCapability() async {
        let viewModel = ConnectionViewModel(
            connectionChecker: StubConnectionChecker(error: ConnectionCheckError.missingPhotoEdit)
        )
        viewModel.endpointText = "https://hermes.example.com"
        viewModel.tokenText = "token"

        await viewModel.connectManually()

        XCTAssertEqual(viewModel.state, .missingPhotoEdit)
    }

    func testPairingPayloadExchangeMarksConnectedAfterCapabilityCheck() async throws {
        let now = ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let viewModel = ConnectionViewModel(connectionChecker: checker, pairingExchanger: exchanger)

        await viewModel.connectWithPairingPayload(
            """
            {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z"}
            """,
            now: now,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(
            viewModel.state,
            .connected(
                ConnectedRuntime(
                    displayName: "Kartz MacBook Hermes",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            )
        )
        XCTAssertEqual(exchanger.calls.map(\.pairingCode), ["pair_123"])
        XCTAssertEqual(exchanger.calls.map(\.deviceName), ["Kartz iPhone"])
        XCTAssertEqual(checker.calls.map(\.token), ["mobile_secret"])
    }

    func testPairingPayloadExchangeSavesMobileCredential() async throws {
        let now = ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
        let store = StubConnectionStore()
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: "2026-06-01T00:00:00Z"
            )
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger,
            connectionStore: store
        )

        await viewModel.connectWithPairingPayload(
            """
            {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z"}
            """,
            now: now,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(store.savedConnections.count, 1)
        XCTAssertEqual(store.savedConnections[0].endpoint.baseURL.absoluteString, "https://macbook-pro.local:8765")
        XCTAssertEqual(store.savedConnections[0].mobileToken, "mobile_secret")
        XCTAssertEqual(store.savedConnections[0].tokenExpiresAt, "2026-06-01T00:00:00Z")
    }

    func testPairingPayloadCarriesTLSPinThroughExchangeCheckAndSave() async throws {
        let now = ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
        let pin = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        let store = StubConnectionStore()
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger,
            connectionStore: store
        )

        await viewModel.connectWithPairingPayload(
            """
            {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z","tls_public_key_sha256":"\(pin)","trusted_local_tls_required":true}
            """,
            now: now,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(exchanger.calls.map(\.trustPolicy), [.pinnedPublicKeySHA256(pin)])
        XCTAssertEqual(checker.calls.map(\.trustPolicy), [.pinnedPublicKeySHA256(pin)])
        XCTAssertEqual(store.savedConnections.map(\.tlsPublicKeySHA256), [pin])
    }

    func testRequiredLocalTLSPayloadWithoutPinMapsInvalidCertificateBeforeExchange() async {
        let now = ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let viewModel = ConnectionViewModel(pairingExchanger: exchanger)

        await viewModel.connectWithPairingPayload(
            """
            {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z","trusted_local_tls_required":true}
            """,
            now: now,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(viewModel.state, .invalidCertificate)
        XCTAssertTrue(exchanger.calls.isEmpty)
    }

    func testExpiredPairingPayloadFailsBeforeExchange() async {
        let now = ISO8601DateFormatter().date(from: "2026-05-30T16:31:00Z")!
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: StubConnectionChecker(error: ConnectionCheckError.missingPhotoEdit),
            pairingExchanger: exchanger
        )

        await viewModel.connectWithPairingPayload(
            """
            {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z"}
            """,
            now: now,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(viewModel.state, .failed(message: "Pairing code expired."))
        XCTAssertTrue(exchanger.calls.isEmpty)
    }

    func testPairingAlreadyUsedMapsToRecoverableFailure() async {
        let now = ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
        let viewModel = ConnectionViewModel(
            connectionChecker: StubConnectionChecker(error: ConnectionCheckError.missingPhotoEdit),
            pairingExchanger: StubPairingExchanger(
                error: MobileBridgeHTTPClient.ClientError.httpStatus(
                    409,
                    BridgeErrorResponse(
                        error: BridgeErrorResponse.BridgeError(
                            code: "pairing_already_used",
                            message: "Pairing code has already been used.",
                            recoverable: true
                        )
                    )
                )
            )
        )

        await viewModel.connectWithPairingPayload(
            """
            {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z"}
            """,
            now: now,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(viewModel.state, .failed(message: "Pairing code already used. Scan a new QR code."))
    }

    func testPairingPayloadExchangeMapsCertificateFailure() async {
        let now = ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
        let viewModel = ConnectionViewModel(
            pairingExchanger: StubPairingExchanger(error: URLError(.secureConnectionFailed))
        )

        await viewModel.connectWithPairingPayload(
            """
            {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z"}
            """,
            now: now,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(viewModel.state, .invalidCertificate)
    }

    func testLocalDiscoveryPublishesFoundRuntimes() async throws {
        let endpoint = try AgentEndpoint(rawURL: "http://macbook-pro.local:8765")
        let runtime = DiscoveredRuntime(
            displayName: "Kartz MacBook Hermes",
            endpoint: endpoint,
            pairingPayload: nil
        )
        let viewModel = ConnectionViewModel(
            runtimeDiscoverer: StubRuntimeDiscoverer(result: [runtime])
        )

        await viewModel.discoverLocalRuntimes(autoPairSingleRuntime: false)

        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertEqual(viewModel.discoveredRuntimes, [runtime])
    }

    func testLocalDiscoverySingleRuntimeRequiresUserConfirmationByDefault() async throws {
        let endpoint = try AgentEndpoint(rawURL: "http://macbook-pro.local:8765")
        let runtime = DiscoveredRuntime(
            displayName: "Kartz MacBook Hermes",
            endpoint: endpoint,
            pairingPayload: """
            {"version":1,"endpoint":"http://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2099-05-30T16:30:00Z"}
            """
        )
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger,
            runtimeDiscoverer: StubRuntimeDiscoverer(result: [runtime])
        )

        await viewModel.discoverLocalRuntimes()

        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertEqual(viewModel.discoveredRuntimes, [runtime])
        XCTAssertTrue(exchanger.calls.isEmpty)
        XCTAssertTrue(checker.calls.isEmpty)
    }

    func testLocalDiscoveryAutoPairsSingleRuntimeWithPairingPayloadWhenRequested() async throws {
        let endpoint = try AgentEndpoint(rawURL: "http://macbook-pro.local:8765")
        let runtime = DiscoveredRuntime(
            displayName: "Kartz MacBook Hermes",
            endpoint: endpoint,
            pairingPayload: """
            {"version":1,"endpoint":"http://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2099-05-30T16:30:00Z"}
            """
        )
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger,
            runtimeDiscoverer: StubRuntimeDiscoverer(result: [runtime])
        )

        await viewModel.discoverLocalRuntimes(autoPairSingleRuntime: true)

        XCTAssertEqual(
            viewModel.state,
            .connected(
                ConnectedRuntime(
                    displayName: "Kartz MacBook Hermes",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            )
        )
        XCTAssertEqual(exchanger.calls.map(\.pairingCode), ["pair_123"])
        XCTAssertEqual(checker.calls.map(\.token), ["mobile_secret"])
        XCTAssertEqual(viewModel.discoveredRuntimes, [])
    }

    func testLocalDiscoveryAutoPairsSingleRuntimeWithoutPayloadUsingDevelopmentRefresh() async throws {
        let endpoint = try AgentEndpoint(rawURL: "http://macbook-pro.local:8765")
        let runtime = DiscoveredRuntime(
            displayName: "Kartz MacBook Hermes",
            endpoint: endpoint,
            pairingPayload: nil
        )
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let refresher = StubPairingPayloadRefresher(
            payload: """
            {"version":1,"endpoint":"http://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_dev_0004","expires_at":"2099-05-30T16:30:00Z"}
            """
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger,
            runtimeDiscoverer: StubRuntimeDiscoverer(result: [runtime]),
            pairingPayloadRefresher: refresher
        )

        await viewModel.discoverLocalRuntimes(
            autoPairSingleRuntime: true,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(
            viewModel.state,
            .connected(
                ConnectedRuntime(
                    displayName: "Kartz MacBook Hermes",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            )
        )
        XCTAssertEqual(refresher.calls.map(\.baseURL.absoluteString), ["http://macbook-pro.local:8765"])
        XCTAssertEqual(exchanger.calls.map(\.pairingCode), ["pair_dev_0004"])
        XCTAssertEqual(checker.calls.map(\.token), ["mobile_secret"])
        XCTAssertEqual(viewModel.discoveredRuntimes, [])
    }

    func testLocalDiscoveryRefreshesAlreadyUsedPairingCodeFromEndpoint() async throws {
        let endpoint = try AgentEndpoint(rawURL: "http://macbook-pro.local:8765")
        let runtime = DiscoveredRuntime(
            displayName: "Kartz MacBook Hermes",
            endpoint: endpoint,
            pairingPayload: """
            {"version":1,"endpoint":"http://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_dev","expires_at":"2099-05-30T16:30:00Z"}
            """
        )
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            sequence: [
                .failure(
                    MobileBridgeHTTPClient.ClientError.httpStatus(
                        409,
                        BridgeErrorResponse(
                            error: BridgeErrorResponse.BridgeError(
                                code: "pairing_already_used",
                                message: "Pairing code has already been used.",
                                recoverable: true
                            )
                        )
                    )
                ),
                .success(
                    PairingExchangeResponse(
                        endpointID: "endpoint_123",
                        displayName: "Kartz MacBook Hermes",
                        runtime: "hermes",
                        runtimeVersion: "2026.5.16",
                        mobileToken: "mobile_secret",
                        tokenExpiresAt: nil
                    )
                ),
            ]
        )
        let refresher = StubPairingPayloadRefresher(
            payload: """
            {"version":1,"endpoint":"http://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_dev_0002","expires_at":"2099-05-30T16:30:00Z"}
            """
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger,
            runtimeDiscoverer: StubRuntimeDiscoverer(result: [runtime]),
            pairingPayloadRefresher: refresher
        )

        await viewModel.discoverLocalRuntimes(
            autoPairSingleRuntime: true,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(
            viewModel.state,
            .connected(
                ConnectedRuntime(
                    displayName: "Kartz MacBook Hermes",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            )
        )
        XCTAssertEqual(refresher.calls.map(\.baseURL.absoluteString), ["http://macbook-pro.local:8765"])
        XCTAssertEqual(exchanger.calls.map(\.pairingCode), ["pair_dev", "pair_dev_0002"])
        XCTAssertEqual(checker.calls.map(\.token), ["mobile_secret"])
    }

    func testLocalDiscoveryWithMultipleRuntimesRequiresUserChoice() async throws {
        let first = DiscoveredRuntime(
            displayName: "Desk Hermes",
            endpoint: try AgentEndpoint(rawURL: "http://desk.local:8765"),
            pairingPayload: """
            {"version":1,"endpoint":"http://desk.local:8765","runtime":"hermes","display_name":"Desk Hermes","pairing_code":"pair_desk","expires_at":"2099-05-30T16:30:00Z"}
            """
        )
        let second = DiscoveredRuntime(
            displayName: "Studio Hermes",
            endpoint: try AgentEndpoint(rawURL: "http://studio.local:8765"),
            pairingPayload: """
            {"version":1,"endpoint":"http://studio.local:8765","runtime":"hermes","display_name":"Studio Hermes","pairing_code":"pair_studio","expires_at":"2099-05-30T16:30:00Z"}
            """
        )
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Desk Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Desk Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger,
            runtimeDiscoverer: StubRuntimeDiscoverer(result: [first, second])
        )

        await viewModel.discoverLocalRuntimes()

        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertEqual(viewModel.discoveredRuntimes, [first, second])
        XCTAssertTrue(exchanger.calls.isEmpty)
        XCTAssertTrue(checker.calls.isEmpty)
    }

    func testLocalDiscoveryWithoutResultsFailsRecoverably() async {
        let viewModel = ConnectionViewModel(
            runtimeDiscoverer: StubRuntimeDiscoverer(result: [])
        )

        await viewModel.discoverLocalRuntimes()

        XCTAssertEqual(
            viewModel.state,
            .failed(message: "No local agent runtime found. Scan a pairing QR or enter an endpoint.")
        )
    }

    func testLocalDiscoverySearchFailureAsksForLocalNetworkPermission() async {
        let viewModel = ConnectionViewModel(
            runtimeDiscoverer: StubRuntimeDiscoverer(error: RuntimeDiscoveryError.searchFailed)
        )

        await viewModel.discoverLocalRuntimes()

        XCTAssertEqual(
            viewModel.state,
            .localNetworkPermissionRequired
        )
    }

    func testRestoreSavedConnectionWithoutSavedConnectionDoesNotDiscoverNearby() async throws {
        let discoveredRuntime = DiscoveredRuntime(
            displayName: "Kartz MacBook Hermes",
            endpoint: try AgentEndpoint(rawURL: "http://macbook-pro.local:8765"),
            pairingPayload: nil
        )
        let discoverer = StubRuntimeDiscoverer(result: [discoveredRuntime])
        let viewModel = ConnectionViewModel(
            runtimeDiscoverer: discoverer,
            connectionStore: StubConnectionStore()
        )

        await viewModel.restoreSavedConnection()

        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertEqual(viewModel.discoveredRuntimes, [])
        XCTAssertTrue(discoverer.calls.isEmpty)
    }

    func testLaunchBootstrapRequiresFirstPairingWhenNoSavedConnection() async {
        let discoverer = StubRuntimeDiscoverer(result: [])
        let viewModel = ConnectionViewModel(
            runtimeDiscoverer: discoverer,
            connectionStore: StubConnectionStore()
        )

        let outcome = await viewModel.bootstrapConnectionForLaunch()

        XCTAssertEqual(outcome, .needsFirstPairing)
        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertEqual(viewModel.discoveredRuntimes, [])
        XCTAssertTrue(discoverer.calls.isEmpty)
    }

    func testLaunchBootstrapDoesNotAutoPairNearbyRuntimeWithoutSavedConnection() async throws {
        let endpoint = try AgentEndpoint(rawURL: "http://macbook-pro.local:8765")
        let runtime = DiscoveredRuntime(
            displayName: "Kartz MacBook Hermes",
            endpoint: endpoint,
            pairingPayload: """
            {"version":1,"endpoint":"http://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2099-05-30T16:30:00Z"}
            """
        )
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger,
            runtimeDiscoverer: StubRuntimeDiscoverer(result: [runtime]),
            connectionStore: StubConnectionStore()
        )

        let outcome = await viewModel.bootstrapConnectionForLaunch(
            timeout: 0.1
        )

        XCTAssertEqual(outcome, .needsFirstPairing)
        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertEqual(viewModel.discoveredRuntimes, [])
        XCTAssertTrue(exchanger.calls.isEmpty)
        XCTAssertTrue(checker.calls.isEmpty)
    }

    func testManualDiscoveryCanStillAutoPairSingleRuntimeWhenExplicitlyRequested() async throws {
        let endpoint = try AgentEndpoint(rawURL: "http://macbook-pro.local:8765")
        let runtime = DiscoveredRuntime(
            displayName: "Kartz MacBook Hermes",
            endpoint: endpoint,
            pairingPayload: """
            {"version":1,"endpoint":"http://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2099-05-30T16:30:00Z"}
            """
        )
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger,
            runtimeDiscoverer: StubRuntimeDiscoverer(result: [runtime]),
            connectionStore: StubConnectionStore()
        )

        await viewModel.discoverLocalRuntimes(
            autoPairSingleRuntime: true,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(
            viewModel.state,
            .connected(
                ConnectedRuntime(
                    displayName: "Kartz MacBook Hermes",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            )
        )
        XCTAssertEqual(exchanger.calls.map(\.pairingCode), ["pair_123"])
        XCTAssertEqual(checker.calls.map(\.token), ["mobile_secret"])
    }

    func testManualDiscoveryKeepsMultipleNearbyRuntimesForUserChoice() async throws {
        let first = DiscoveredRuntime(
            displayName: "Desk Hermes",
            endpoint: try AgentEndpoint(rawURL: "http://desk.local:8765"),
            pairingPayload: """
            {"version":1,"endpoint":"http://desk.local:8765","runtime":"hermes","display_name":"Desk Hermes","pairing_code":"pair_desk","expires_at":"2099-05-30T16:30:00Z"}
            """
        )
        let second = DiscoveredRuntime(
            displayName: "Studio Hermes",
            endpoint: try AgentEndpoint(rawURL: "http://studio.local:8765"),
            pairingPayload: """
            {"version":1,"endpoint":"http://studio.local:8765","runtime":"hermes","display_name":"Studio Hermes","pairing_code":"pair_studio","expires_at":"2099-05-30T16:30:00Z"}
            """
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Desk Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let viewModel = ConnectionViewModel(
            pairingExchanger: exchanger,
            runtimeDiscoverer: StubRuntimeDiscoverer(result: [first, second]),
            connectionStore: StubConnectionStore()
        )

        await viewModel.discoverLocalRuntimes(autoPairSingleRuntime: false)

        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertEqual(viewModel.discoveredRuntimes, [first, second])
        XCTAssertTrue(exchanger.calls.isEmpty)
    }

    func testLaunchProximityDiscoveryPrefersSavedConnectionOverBonjourSearch() async throws {
        let savedConnection = StoredConnection(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            displayName: "Saved Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "stored_secret",
            tokenExpiresAt: nil
        )
        let discoverer = StubRuntimeDiscoverer(result: [])
        let viewModel = ConnectionViewModel(
            connectionChecker: StubConnectionChecker(
                result: ConnectedRuntime(
                    displayName: "Saved Hermes",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            ),
            runtimeDiscoverer: discoverer,
            connectionStore: StubConnectionStore(savedConnection: savedConnection)
        )

        await viewModel.restoreSavedConnectionOrDiscoverNearby()

        XCTAssertEqual(
            viewModel.state,
            .connected(
                ConnectedRuntime(
                    displayName: "Saved Hermes",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            )
        )
        XCTAssertTrue(discoverer.calls.isEmpty)
    }

    func testLaunchProximityDiscoveryDoesNotInterruptExistingConnection() async {
        let runtime = ConnectedRuntime(
            displayName: "Saved Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16"
        )
        let checker = StubConnectionChecker(result: runtime)
        let discoverer = StubRuntimeDiscoverer(result: [])
        let viewModel = ConnectionViewModel(
            state: .connected(runtime),
            connectionChecker: checker,
            runtimeDiscoverer: discoverer,
            connectionStore: StubConnectionStore()
        )

        await viewModel.restoreSavedConnectionOrDiscoverNearby()

        XCTAssertEqual(viewModel.state, .connected(runtime))
        XCTAssertTrue(checker.calls.isEmpty)
        XCTAssertTrue(discoverer.calls.isEmpty)
    }

    func testLaunchBootstrapRepairsOfflineSavedConnectionFromSingleNearbyRuntimeUsingSavedToken() async throws {
        let savedConnection = StoredConnection(
            endpoint: try AgentEndpoint(rawURL: "https://old-hermes.example.com"),
            displayName: "Kartz MacBook Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "stored_secret",
            tokenExpiresAt: nil
        )
        let nearbyRuntime = DiscoveredRuntime(
            displayName: "Kartz MacBook Hermes",
            endpoint: try AgentEndpoint(rawURL: "http://macbook-pro.local:8765"),
            pairingPayload: """
            {"version":1,"endpoint":"http://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_repair","expires_at":"2099-05-30T16:30:00Z"}
            """
        )
        let checker = StubConnectionChecker(
            sequence: [
                .failure(URLError(.cannotConnectToHost)),
                .success(
                    ConnectedRuntime(
                        displayName: "Kartz MacBook Hermes",
                        runtime: "hermes",
                        runtimeVersion: "2026.5.16"
                    )
                ),
            ]
        )
        let exchanger = StubPairingExchanger(error: TestStoreError.clearFailed)
        let store = StubConnectionStore(savedConnection: savedConnection)
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger,
            runtimeDiscoverer: StubRuntimeDiscoverer(result: [nearbyRuntime]),
            connectionStore: store
        )

        let outcome = await viewModel.bootstrapConnectionForLaunch()

        XCTAssertEqual(outcome, .connected)
        XCTAssertEqual(
            viewModel.state,
            .connected(
                ConnectedRuntime(
                    displayName: "Kartz MacBook Hermes",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            )
        )
        XCTAssertTrue(exchanger.calls.isEmpty)
        XCTAssertEqual(checker.calls.map(\.endpoint.baseURL.absoluteString), [
            "https://old-hermes.example.com",
            "http://macbook-pro.local:8765",
        ])
        XCTAssertEqual(checker.calls.map(\.token), ["stored_secret", "stored_secret"])
        XCTAssertEqual(store.savedConnections.map(\.mobileToken), ["stored_secret"])
        XCTAssertEqual(store.savedConnections.map(\.endpoint.baseURL.absoluteString), ["http://macbook-pro.local:8765"])
    }

    func testLaunchBootstrapPreservesSavedOfflineStateWhenSavedConnectionAndNoNearbyRuntime() async throws {
        let savedConnection = StoredConnection(
            endpoint: try AgentEndpoint(rawURL: "https://old-hermes.example.com"),
            displayName: "Kartz MacBook Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "stored_secret",
            tokenExpiresAt: nil
        )
        let discoverer = StubRuntimeDiscoverer(result: [])
        let viewModel = ConnectionViewModel(
            connectionChecker: StubConnectionChecker(error: URLError(.cannotConnectToHost)),
            runtimeDiscoverer: discoverer,
            connectionStore: StubConnectionStore(savedConnection: savedConnection)
        )

        let outcome = await viewModel.bootstrapConnectionForLaunch()

        XCTAssertEqual(outcome, .savedConnectionOffline)
        XCTAssertEqual(viewModel.state, .savedConnectionOffline(displayName: "Kartz MacBook Hermes"))
        XCTAssertEqual(discoverer.calls, [1.8])
    }

    func testConnectDiscoveredRuntimeUsesPairingPayload() async throws {
        let now = ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
        let endpoint = try AgentEndpoint(rawURL: "http://macbook-pro.local:8765")
        let runtime = DiscoveredRuntime(
            displayName: "Kartz MacBook Hermes",
            endpoint: endpoint,
            pairingPayload: """
            {"version":1,"endpoint":"http://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_123","expires_at":"2026-05-30T16:30:00Z"}
            """
        )
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger
        )

        await viewModel.connectDiscoveredRuntime(
            runtime,
            now: now,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(
            viewModel.state,
            .connected(
                ConnectedRuntime(
                    displayName: "Kartz MacBook Hermes",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            )
        )
        XCTAssertEqual(exchanger.calls.map(\.pairingCode), ["pair_123"])
        XCTAssertEqual(checker.calls.map(\.token), ["mobile_secret"])
    }

    func testConnectDiscoveredRuntimeWithoutPayloadFetchesDevelopmentPairingPayload() async throws {
        let now = ISO8601DateFormatter().date(from: "2026-05-30T16:29:00Z")!
        let endpoint = try AgentEndpoint(rawURL: "http://macbook-pro.local:8765")
        let runtime = DiscoveredRuntime(
            displayName: "Kartz MacBook Hermes",
            endpoint: endpoint,
            pairingPayload: nil
        )
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_123",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let refresher = StubPairingPayloadRefresher(
            payload: """
            {"version":1,"endpoint":"http://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_dev_0003","expires_at":"2026-05-30T16:30:00Z"}
            """
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger,
            pairingPayloadRefresher: refresher
        )

        await viewModel.connectDiscoveredRuntime(
            runtime,
            now: now,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(
            viewModel.state,
            .connected(
                ConnectedRuntime(
                    displayName: "Kartz MacBook Hermes",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            )
        )
        XCTAssertEqual(refresher.calls.map(\.baseURL.absoluteString), ["http://macbook-pro.local:8765"])
        XCTAssertEqual(exchanger.calls.map(\.pairingCode), ["pair_dev_0003"])
        XCTAssertEqual(checker.calls.map(\.token), ["mobile_secret"])
    }

    func testDiscoveredRuntimeWithoutPayloadUsesGenericPairingRefresh() async throws {
        let now = ISO8601DateFormatter().date(from: "2026-06-05T08:00:00Z")!
        let endpoint = try AgentEndpoint(rawURL: "https://macbook-pro.local:8765")
        let runtime = DiscoveredRuntime(
            displayName: "Kartz MacBook Hermes",
            endpoint: endpoint,
            pairingPayload: nil
        )
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let exchanger = StubPairingExchanger(
            result: PairingExchangeResponse(
                endpointID: "endpoint_hermes",
                displayName: "Kartz MacBook Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16",
                mobileToken: "mobile_secret",
                tokenExpiresAt: nil
            )
        )
        let refresher = StubPairingPayloadRefresher(
            payload: """
            {"version":1,"endpoint":"https://macbook-pro.local:8765","runtime":"hermes","display_name":"Kartz MacBook Hermes","pairing_code":"pair_prod","expires_at":"2026-06-05T08:02:00Z"}
            """
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            pairingExchanger: exchanger,
            pairingPayloadRefresher: refresher
        )

        await viewModel.connectDiscoveredRuntime(
            runtime,
            now: now,
            deviceName: "Kartz iPhone",
            devicePublicID: "device_abc"
        )

        XCTAssertEqual(
            viewModel.state,
            .connected(
                ConnectedRuntime(
                    displayName: "Kartz MacBook Hermes",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            )
        )
        XCTAssertEqual(refresher.calls.map(\.baseURL.absoluteString), ["https://macbook-pro.local:8765"])
        XCTAssertEqual(exchanger.calls.map(\.pairingCode), ["pair_prod"])
        XCTAssertEqual(checker.calls.map(\.token), ["mobile_secret"])
    }

    func testRestoreSavedConnectionChecksCapabilitiesAndMarksConnected() async throws {
        let endpoint = try AgentEndpoint(rawURL: "https://hermes.example.com")
        let savedConnection = StoredConnection(
            endpoint: endpoint,
            displayName: "Saved Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "stored_secret",
            tokenExpiresAt: nil
        )
        let store = StubConnectionStore(savedConnection: savedConnection)
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Saved Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let viewModel = ConnectionViewModel(connectionChecker: checker, connectionStore: store)

        await viewModel.restoreSavedConnection()

        XCTAssertEqual(
            viewModel.state,
            .connected(
                ConnectedRuntime(
                    displayName: "Saved Hermes",
                    runtime: "hermes",
                    runtimeVersion: "2026.5.16"
                )
            )
        )
        XCTAssertEqual(checker.calls.map(\.token), ["stored_secret"])
        XCTAssertEqual(viewModel.activeConnection, savedConnection)
    }

    func testRestoreSavedConnectionUsesStoredTLSPinTrustPolicy() async throws {
        let pin = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        let savedConnection = StoredConnection(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            displayName: "Saved Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "stored_secret",
            tokenExpiresAt: nil,
            tlsPublicKeySHA256: pin
        )
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Saved Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let viewModel = ConnectionViewModel(
            connectionChecker: checker,
            connectionStore: StubConnectionStore(savedConnection: savedConnection)
        )

        await viewModel.restoreSavedConnection()

        XCTAssertEqual(checker.calls.map(\.trustPolicy), [.pinnedPublicKeySHA256(pin)])
    }

    func testRestoreSavedConnectionClearsRevokedToken() async throws {
        let savedConnection = StoredConnection(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            displayName: "Saved Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "revoked_secret",
            tokenExpiresAt: nil
        )
        let store = StubConnectionStore(savedConnection: savedConnection)
        let viewModel = ConnectionViewModel(
            connectionChecker: StubConnectionChecker(error: MobileBridgeHTTPClient.ClientError.httpStatus(401, nil)),
            connectionStore: store
        )

        await viewModel.restoreSavedConnection()

        XCTAssertEqual(viewModel.state, .unauthorized)
        XCTAssertEqual(store.clearCallCount, 1)
        XCTAssertNil(viewModel.activeConnection)
    }

    func testRestoreSavedConnectionMapsCertificateFailureWithoutClearingCredential() async throws {
        let savedConnection = StoredConnection(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            displayName: "Saved Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "stored_secret",
            tokenExpiresAt: nil
        )
        let store = StubConnectionStore(savedConnection: savedConnection)
        let viewModel = ConnectionViewModel(
            connectionChecker: StubConnectionChecker(error: URLError(.serverCertificateHasUnknownRoot)),
            connectionStore: store
        )

        await viewModel.restoreSavedConnection()

        XCTAssertEqual(viewModel.state, .invalidCertificate)
        XCTAssertEqual(store.clearCallCount, 0)
        XCTAssertNil(viewModel.activeConnection)
    }

    func testForgetSavedConnectionClearsStoreAndReturnsToIdle() async throws {
        let savedConnection = StoredConnection(
            endpoint: try AgentEndpoint(rawURL: "https://hermes.example.com"),
            displayName: "Saved Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16",
            mobileToken: "stored_secret",
            tokenExpiresAt: nil
        )
        let store = StubConnectionStore(savedConnection: savedConnection)
        let checker = StubConnectionChecker(
            result: ConnectedRuntime(
                displayName: "Saved Hermes",
                runtime: "hermes",
                runtimeVersion: "2026.5.16"
            )
        )
        let viewModel = ConnectionViewModel(connectionChecker: checker, connectionStore: store)

        await viewModel.restoreSavedConnection()
        viewModel.forgetSavedConnection()

        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertNil(viewModel.activeConnection)
        XCTAssertEqual(store.clearCallCount, 1)
    }

    func testForgetSavedConnectionFailureShowsRecoverableMessage() throws {
        let store = StubConnectionStore(clearError: TestStoreError.clearFailed)
        let viewModel = ConnectionViewModel(connectionStore: store)

        viewModel.forgetSavedConnection()

        XCTAssertEqual(viewModel.state, .failed(message: "Could not forget local agent connection."))
    }
}

private final class StubConnectionChecker: ConnectionChecking {
    struct Call: Equatable {
        let endpoint: AgentEndpoint
        let token: String
        let trustPolicy: MobileBridgeTrustPolicy
    }

    private(set) var calls: [Call] = []
    private var sequence: [Result<ConnectedRuntime, Error>]

    init(result: ConnectedRuntime) {
        self.sequence = [.success(result)]
    }

    init(error: Error) {
        self.sequence = [.failure(error)]
    }

    init(sequence: [Result<ConnectedRuntime, Error>]) {
        self.sequence = sequence
    }

    func check(
        endpoint: AgentEndpoint,
        token: String,
        trustPolicy: MobileBridgeTrustPolicy
    ) async throws -> ConnectedRuntime {
        calls.append(Call(endpoint: endpoint, token: token, trustPolicy: trustPolicy))
        let next = sequence.count > 1 ? sequence.removeFirst() : sequence[0]
        switch next {
        case .success(let runtime):
            return runtime
        case .failure(let error):
            throw error
        }
    }
}

private final class StubPairingExchanger: PairingExchanging {
    struct Call: Equatable {
        let endpoint: AgentEndpoint
        let pairingCode: String
        let deviceName: String
        let devicePublicID: String
        let trustPolicy: MobileBridgeTrustPolicy
    }

    private(set) var calls: [Call] = []
    private var sequence: [Result<PairingExchangeResponse, Error>]

    init(result: PairingExchangeResponse) {
        self.sequence = [.success(result)]
    }

    init(error: Error) {
        self.sequence = [.failure(error)]
    }

    init(sequence: [Result<PairingExchangeResponse, Error>]) {
        self.sequence = sequence
    }

    func exchange(
        endpoint: AgentEndpoint,
        pairingCode: String,
        deviceName: String,
        devicePublicID: String,
        trustPolicy: MobileBridgeTrustPolicy
    ) async throws -> PairingExchangeResponse {
        calls.append(
            Call(
                endpoint: endpoint,
                pairingCode: pairingCode,
                deviceName: deviceName,
                devicePublicID: devicePublicID,
                trustPolicy: trustPolicy
            )
        )
        let next = sequence.count > 1 ? sequence.removeFirst() : sequence[0]
        switch next {
        case .success(let response):
            return response
        case .failure(let error):
            throw error
        }
    }
}

private final class StubPairingPayloadRefresher: PairingPayloadRefreshing {
    private(set) var calls: [AgentEndpoint] = []
    private let payload: String

    init(payload: String) {
        self.payload = payload
    }

    func refreshPairingPayload(endpoint: AgentEndpoint) async throws -> String {
        calls.append(endpoint)
        return payload
    }
}

private final class StubRuntimeDiscoverer: RuntimeDiscovering {
    private(set) var calls: [TimeInterval] = []
    let result: [DiscoveredRuntime]?
    let error: Error?

    init(result: [DiscoveredRuntime]) {
        self.result = result
        self.error = nil
    }

    init(error: Error) {
        self.result = nil
        self.error = error
    }

    func discover(timeout: TimeInterval) async throws -> [DiscoveredRuntime] {
        calls.append(timeout)
        if let error {
            throw error
        }
        guard let result else {
            return []
        }
        return result
    }
}

private final class StubConnectionStore: ConnectionStoring {
    private var savedConnection: StoredConnection?
    private(set) var savedConnections: [StoredConnection] = []
    private(set) var clearCallCount = 0
    private let clearError: Error?

    init(savedConnection: StoredConnection? = nil, clearError: Error? = nil) {
        self.savedConnection = savedConnection
        self.clearError = clearError
    }

    func load() throws -> StoredConnection? {
        savedConnection
    }

    func save(_ connection: StoredConnection) throws {
        savedConnection = connection
        savedConnections.append(connection)
    }

    func clear() throws {
        if let clearError {
            throw clearError
        }
        savedConnection = nil
        clearCallCount += 1
    }
}

private enum TestStoreError: Error {
    case clearFailed
}
