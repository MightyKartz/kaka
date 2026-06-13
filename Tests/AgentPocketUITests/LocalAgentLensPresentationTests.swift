import XCTest
@testable import AgentPocketUI

final class LocalAgentLensPresentationTests: XCTestCase {
    func testConnectedLensShowsPhoneFirstActions() {
        let presentation = LocalAgentLensPresentation(isConnected: true, language: .english)

        XCTAssertEqual(
            presentation.actions.map(\.id),
            ["agent_scanner", "document_scan", "video_intake", "voice_recorder", "inbox", "tasks"]
        )
        XCTAssertFalse(presentation.actions.contains { $0.isEnabled == false })
        XCTAssertEqual(presentation.connectionTitle, "Local Agent Connected")
    }

    func testDisconnectedLensKeepsActionsVisibleButExplainsLocalRuntime() {
        let presentation = LocalAgentLensPresentation(isConnected: false, language: .english)

        XCTAssertEqual(presentation.connectionTitle, "Local Agent Offline")
        XCTAssertEqual(presentation.connectionHint, "Connect to your local agent on Wi-Fi before sending.")
        XCTAssertTrue(presentation.actions.contains { $0.id == "agent_scanner" && $0.isEnabled })
        XCTAssertTrue(presentation.actions.contains { $0.id == "document_scan" && $0.isEnabled })
        XCTAssertTrue(presentation.actions.contains { $0.id == "video_intake" && $0.isEnabled })
    }
}
