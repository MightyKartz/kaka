import XCTest
@testable import AgentPocketUI

final class ConnectionReadinessPresentationTests: XCTestCase {
    func testExpiredPairingQRCodeUsesPhoneSideRefreshAndScanRecovery() {
        let presentation = ConnectionReadinessPresenter.presentation(for: .expiredPairingQRCode)

        XCTAssertEqual(presentation.recoveryOwner, .phone)
        XCTAssertEqual(presentation.recoveryAction, .scanRefreshedPairingQR)
        XCTAssertNil(presentation.compatibleConnectionState)
        XCTAssertEqual(presentation.primaryActionTitle, "Scan Refreshed QR")
        XCTAssertEqual(presentation.secondaryActionTitle, "Refresh QR on Host")
        XCTAssertVisibleCopy(presentation, contains: ["expired", "refreshed QR"])
    }

    func testRevokedSavedConnectionUsesUnauthorizedCompatibleCopyAndHostPairingRecovery() {
        let presentation = ConnectionReadinessPresenter.presentation(for: .revokedSavedConnection)
        let unauthorizedCopy = ConnectionState.unauthorized.presentation

        XCTAssertEqual(presentation.recoveryOwner, .hostRuntime)
        XCTAssertEqual(presentation.recoveryAction, .generateMobilePairingCode)
        XCTAssertEqual(presentation.compatibleConnectionState, .unauthorized)
        XCTAssertEqual(presentation.title, unauthorizedCopy.title)
        XCTAssertEqual(presentation.message, unauthorizedCopy.message)
        XCTAssertVisibleCopy(presentation, contains: ["new mobile pairing code"])
    }

    func testBridgeUnavailableUsesOfflineCompatibleCopyAndHostRuntimeRecovery() {
        let presentation = ConnectionReadinessPresenter.presentation(for: .bridgeUnavailable)
        let offlineCopy = ConnectionState.offline.presentation

        XCTAssertEqual(presentation.recoveryOwner, .hostRuntime)
        XCTAssertEqual(presentation.recoveryAction, .startMobileBridge)
        XCTAssertEqual(presentation.compatibleConnectionState, .offline)
        XCTAssertEqual(presentation.title, offlineCopy.title)
        XCTAssertEqual(presentation.message, offlineCopy.message)
        XCTAssertVisibleCopy(presentation, contains: ["Start Kaka Mobile Bridge"])
    }

    func testMissingBonjourHostOffersLocalNetworkAndManualEndpointFallback() {
        let presentation = ConnectionReadinessPresenter.presentation(for: .missingBonjourHost)

        XCTAssertEqual(presentation.recoveryOwner, .phone)
        XCTAssertEqual(presentation.recoveryAction, .useLocalNetworkOrManualEndpointFallback)
        XCTAssertNil(presentation.compatibleConnectionState)
        XCTAssertEqual(presentation.primaryActionTitle, "Scan Pairing QR")
        XCTAssertEqual(presentation.secondaryActionTitle, "Enter Endpoint")
        XCTAssertVisibleCopy(presentation, contains: ["Local Network", "Bonjour", "endpoint"])
    }

    func testPortConflictStaysHostOwnedAndDoesNotOfferPhoneSettings() {
        let presentation = ConnectionReadinessPresenter.presentation(for: .portConflict)

        XCTAssertEqual(presentation.recoveryOwner, .hostRuntime)
        XCTAssertEqual(presentation.recoveryAction, .repairHostPort)
        XCTAssertNil(presentation.compatibleConnectionState)
        XCTAssertVisibleCopy(presentation, contains: ["host", "port"])
        XCTAssertVisibleCopy(presentation, doesNotContain: ["Phone Settings", "iPhone Settings", "Mobile Bridge Settings"])
    }

    func testDisabledHostActionWaitsForRuntimeStateChange() {
        let presentation = ConnectionReadinessPresenter.presentation(for: .disabledHostAction)

        XCTAssertEqual(presentation.recoveryOwner, .hostRuntime)
        XCTAssertEqual(presentation.recoveryAction, .waitForRuntimeStateChange)
        XCTAssertNil(presentation.compatibleConnectionState)
        XCTAssertVisibleCopy(presentation, contains: ["unavailable", "runtime state changes"])
    }

    func testHostExtensionUnavailableUsesPhoneSafeHostOwnedRecovery() {
        let presentation = ConnectionReadinessPresenter.presentation(for: .hostExtensionUnavailable)

        XCTAssertEqual(presentation.recoveryOwner, .hostRuntime)
        XCTAssertEqual(presentation.recoveryAction, .checkHostExtension)
        XCTAssertNil(presentation.compatibleConnectionState)
        XCTAssertVisibleCopy(presentation, contains: ["Host Extension", "Kaka Mobile Bridge", "Mac"])
        XCTAssertVisibleCopy(presentation, doesNotContain: [
            "P3.1",
            "private host API",
            "Private Host Adapter",
            "Host API",
            "mock QA",
            "manual QA"
        ])
    }

    func testStateDerivedRecoveryMapsPhoneObservableStates() {
        XCTAssertEqual(
            ConnectionReadinessPresenter.presentation(for: ConnectionState.unauthorized)?.issue,
            .revokedSavedConnection
        )
        XCTAssertEqual(
            ConnectionReadinessPresenter.presentation(for: ConnectionState.offline)?.issue,
            .bridgeUnavailable
        )
        XCTAssertEqual(
            ConnectionReadinessPresenter.presentation(for: ConnectionState.localNetworkPermissionRequired)?.issue,
            .missingBonjourHost
        )
        XCTAssertEqual(
            ConnectionReadinessPresenter.presentation(for: ConnectionState.invalidCertificate)?.issue,
            .requiredTLSCertificateFailure
        )
    }

    func testKnownPairingFailureMessagesMapToRecoveryGuidance() {
        XCTAssertEqual(
            ConnectionReadinessPresenter.presentation(
                for: ConnectionState.failed(message: "Pairing code expired.")
            )?.issue,
            .expiredPairingQRCode
        )
        XCTAssertEqual(
            ConnectionReadinessPresenter.presentation(
                for: ConnectionState.failed(message: "Pairing code already used.")
            )?.issue,
            .pairingCodeAlreadyUsed
        )
    }

    func testStateDerivedRecoveryOmitsBusyAndConnectedStates() {
        let runtime = ConnectedRuntime(
            displayName: "Kaka Runtime",
            runtime: "hermes",
            runtimeVersion: "2026.6"
        )

        XCTAssertNil(ConnectionReadinessPresenter.presentation(for: ConnectionState.idle))
        XCTAssertNil(ConnectionReadinessPresenter.presentation(for: ConnectionState.scanning))
        XCTAssertNil(ConnectionReadinessPresenter.presentation(for: ConnectionState.discovering))
        XCTAssertNil(ConnectionReadinessPresenter.presentation(for: ConnectionState.testing))
        XCTAssertNil(ConnectionReadinessPresenter.presentation(for: ConnectionState.connected(runtime)))
    }

    func testRecoveryGuidanceDoesNotTurnHostOwnedActionsIntoPhoneControls() {
        let hostOwnedIssues: [ConnectionReadinessIssue] = [
            .revokedSavedConnection,
            .bridgeUnavailable,
            .portConflict,
            .disabledHostAction,
            .hostExtensionUnavailable
        ]

        for issue in hostOwnedIssues {
            let presentation = ConnectionReadinessPresenter.presentation(for: issue)
            XCTAssertNotEqual(presentation.primaryActionTitle, "Install")
            XCTAssertNotEqual(presentation.primaryActionTitle, "Update")
            XCTAssertNotEqual(presentation.primaryActionTitle, "Uninstall")
            XCTAssertVisibleCopy(presentation, doesNotContain: [
                "HERMES_KAKA_HOST_API",
                "OPENCLAW_KAKA_HOST_API",
                "--private-adapter-command",
                "host-adapter-run",
                "hermes-kaka-host-api",
                "openclaw-kaka-host-api",
                "private host API",
                "Private Host Adapter",
                "Host API",
                "P3.1",
                "mock QA",
                "manual QA",
                "sqlite",
                "private key",
                "bearer",
                "token="
            ])
        }
    }

    func testRecoveryOwnerLabelsAreShortAndPhoneSafe() {
        XCTAssertEqual(ConnectionReadinessPresenter.ownerLabel(for: .phone), "iPhone")
        XCTAssertEqual(ConnectionReadinessPresenter.ownerLabel(for: .hostRuntime), "Host")
    }

    func testPresentationsExposeNoSecretOrHostInternalFields() {
        let forbiddenFieldFragments = [
            "rawToken",
            "mobileToken",
            "sqlite",
            "runtimeStorePath",
            "providerEndpoint",
            "endpointSecret",
            "privateAPIPayload",
            "hostLogPath",
            "bearer"
        ].map { $0.lowercased() }
        let forbiddenVisibleFragments = [
            "mobile_secret",
            "bearer ",
            "/mobile/v1",
            "/tmp/kaka-runtime.sqlite3",
            "/var/log/kaka",
            "https://api.openai.com",
            "sk-",
            "private_api_payload"
        ]

        for issue in ConnectionReadinessIssue.allCases {
            let presentation = ConnectionReadinessPresenter.presentation(for: issue)
            let fieldLabels = Mirror(reflecting: presentation).children.compactMap(\.label)

            for label in fieldLabels {
                let lowercasedLabel = label.lowercased()
                for forbiddenFragment in forbiddenFieldFragments {
                    XCTAssertFalse(
                        lowercasedLabel.contains(forbiddenFragment),
                        "\(issue) exposes forbidden field label \(label)"
                    )
                }
            }

            XCTAssertVisibleCopy(presentation, doesNotContain: forbiddenVisibleFragments)
        }
    }
}

private extension ConnectionReadinessPresentationTests {
    func XCTAssertVisibleCopy(
        _ presentation: ConnectionReadinessPresentation,
        contains fragments: [String],
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let visibleCopy = presentation.visibleCopy.lowercased()
        for fragment in fragments {
            XCTAssertTrue(
                visibleCopy.contains(fragment.lowercased()),
                "Expected visible copy to contain \(fragment). Copy: \(presentation.visibleCopy)",
                file: file,
                line: line
            )
        }
    }

    func XCTAssertVisibleCopy(
        _ presentation: ConnectionReadinessPresentation,
        doesNotContain fragments: [String],
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let visibleCopy = presentation.visibleCopy.lowercased()
        for fragment in fragments {
            XCTAssertFalse(
                visibleCopy.contains(fragment.lowercased()),
                "Expected visible copy to omit \(fragment). Copy: \(presentation.visibleCopy)",
                file: file,
                line: line
            )
        }
    }
}
