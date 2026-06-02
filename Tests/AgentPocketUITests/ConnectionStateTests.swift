import XCTest
@testable import AgentPocketUI

final class ConnectionStateTests: XCTestCase {
    func testIdleStatePromotesLocalDiscoveryAsPrimaryAction() {
        let model = ConnectionState.idle.presentation

        XCTAssertEqual(model.title, "Connect My Local Agent")
        XCTAssertEqual(model.primaryActionTitle, "Discover Local Runtime")
        XCTAssertEqual(model.secondaryActionTitle, "Scan Pairing QR")
        XCTAssertFalse(model.isBusy)
        XCTAssertFalse(model.showsManualEntry)
    }

    func testConnectionPresentationUsesRuntimeNeutralAgentCopy() {
        let runtime = ConnectedRuntime(
            displayName: "OpenClaw Studio",
            runtime: "openclaw",
            runtimeVersion: "2026.6"
        )
        let presentations = [
            ConnectionState.idle.presentation,
            ConnectionState.scanning.presentation,
            ConnectionState.discovering.presentation,
            ConnectionState.testing.presentation,
            ConnectionState.connected(runtime).presentation,
            ConnectionState.unauthorized.presentation,
            ConnectionState.offline.presentation,
            ConnectionState.invalidCertificate.presentation,
            ConnectionState.missingPhotoEdit.presentation,
            ConnectionState.localNetworkPermissionRequired.presentation,
            ConnectionState.failed(message: "Could not connect to your local agent.").presentation
        ]

        for model in presentations {
            let copy = [
                model.title,
                model.message,
                model.primaryActionTitle,
                model.secondaryActionTitle ?? ""
            ].joined(separator: " ")

            XCTAssertFalse(copy.localizedCaseInsensitiveContains("Hermes"), copy)
        }
    }

    func testTestingStateDisablesActionsAndShowsProgress() {
        let model = ConnectionState.testing.presentation

        XCTAssertEqual(model.title, "Testing Connection")
        XCTAssertEqual(model.primaryActionTitle, "Testing...")
        XCTAssertTrue(model.isBusy)
        XCTAssertFalse(model.showsManualEntry)
    }

    func testDiscoveringStateDisablesActionsAndShowsProgress() {
        let model = ConnectionState.discovering.presentation

        XCTAssertEqual(model.title, "Finding Local Agent")
        XCTAssertEqual(model.primaryActionTitle, "Finding...")
        XCTAssertTrue(model.isBusy)
        XCTAssertFalse(model.showsManualEntry)
    }

    func testConnectedStateNamesRuntimeAndHidesManualEntry() {
        let runtime = ConnectedRuntime(
            displayName: "Kartz MacBook Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16"
        )

        let model = ConnectionState.connected(runtime).presentation

        XCTAssertEqual(model.title, "Connected")
        XCTAssertEqual(model.message, "Kartz MacBook Hermes is ready for photo edits.")
        XCTAssertEqual(model.primaryActionTitle, "Start Photo Edit")
        XCTAssertFalse(model.showsManualEntry)
    }

    func testConnectedStateShowsLocalTrustedBadges() {
        let runtime = ConnectedRuntime(
            displayName: "Kartz MacBook Hermes",
            runtime: "hermes",
            runtimeVersion: "2026.5.16"
        )

        let model = ConnectionState.connected(runtime).presentation

        XCTAssertEqual(model.trustBadges, ["Local Network", "Trusted"])
    }

    func testOfflineStatePromotesLocalDiscoveryRecovery() {
        let model = ConnectionState.offline.presentation

        XCTAssertEqual(model.title, "Runtime Offline")
        XCTAssertEqual(model.primaryActionTitle, "Discover Local Runtime")
        XCTAssertEqual(model.secondaryActionTitle, "Scan Pairing QR")
        XCTAssertFalse(model.showsManualEntry)
    }

    func testMissingPhotoEditStateHasRecoveryCopy() {
        let model = ConnectionState.missingPhotoEdit.presentation

        XCTAssertEqual(model.title, "Photo Pack Missing")
        XCTAssertEqual(model.primaryActionTitle, "Open Setup Guide")
        XCTAssertTrue(model.message.contains("Photo Pack"))
    }

    func testLocalNetworkPermissionStateOpensSettings() {
        let model = ConnectionState.localNetworkPermissionRequired.presentation

        XCTAssertEqual(model.title, "Local Network Access Needed")
        XCTAssertEqual(model.message, "Allow Agent Pocket to find your local agent on the local network.")
        XCTAssertEqual(model.primaryActionTitle, "Open Settings")
        XCTAssertEqual(model.primaryRecoveryDestination, .appSettings)
        XCTAssertEqual(model.secondaryActionTitle, "Enter Endpoint")
        XCTAssertFalse(model.showsManualEntry)
    }
}
