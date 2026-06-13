import XCTest
@testable import AgentPocketCore

final class AgentLensSourceSurfaceTests: XCTestCase {
    func testAgentLensSourceSurfacesUseStableBridgeValues() {
        XCTAssertEqual(AgentLensSourceSurface.agentScanner.rawValue, "agent_scanner")
        XCTAssertEqual(AgentLensSourceSurface.documentScanner.rawValue, "document_scanner")
        XCTAssertEqual(AgentLensSourceSurface.videoCapture.rawValue, "video_capture")
        XCTAssertEqual(AgentLensSourceSurface.actionButton.rawValue, "action_button")
        XCTAssertEqual(AgentLensSourceSurface.shortcut.rawValue, "shortcut")
    }
}
