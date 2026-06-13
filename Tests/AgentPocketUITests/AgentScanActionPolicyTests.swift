import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

final class AgentScanActionPolicyTests: XCTestCase {
    func testKakaPairingQRPrefersConnectAction() {
        let result = AgentScanResult(rawValue: #"{"v":1,"endpoint":"http://192.168.1.10:8765","pairing_code":"abc"}"#)

        XCTAssertEqual(
            AgentScanActionPolicy.actions(for: result).map(\.kind),
            [.connectLocalRuntime, .copy]
        )
    }

    func testHTTPURLOffersSafeNextActionsWithoutAutoOpening() {
        let result = AgentScanResult(rawValue: "https://example.com/product?id=42")

        XCTAssertEqual(
            AgentScanActionPolicy.actions(for: result).map(\.kind),
            [.summarizeURL, .openURL, .copy, .saveToInbox]
        )
    }

    func testUnknownCodeCanBeCopiedAndSentAsText() {
        let result = AgentScanResult(rawValue: "SN-AX9-2026")

        XCTAssertEqual(
            AgentScanActionPolicy.actions(for: result).map(\.kind),
            [.askAgentAboutText, .copy]
        )
    }

    func testPaymentLikeURLDoesNotAutoOpen() {
        let result = AgentScanResult(rawValue: "alipays://platformapi/startapp?appId=20000067")

        XCTAssertTrue(AgentScanActionPolicy.actions(for: result).contains { $0.kind == .copy })
        XCTAssertFalse(AgentScanActionPolicy.actions(for: result).contains { $0.kind == .openURL })
    }

    func testURLScanBuildsInboxDraftWithScannerSourceSurface() {
        let item = AgentScanInboxDraftBuilder.item(for: AgentScanResult(rawValue: "https://example.com"))

        XCTAssertEqual(item.kind, .url)
        XCTAssertEqual(item.url, "https://example.com")
        XCTAssertEqual(item.sourceSurface, "agent_scanner")
        XCTAssertEqual(item.route, .universalIntake)
    }

    func testTextScanBuildsInboxDraftWithInstruction() {
        let item = AgentScanInboxDraftBuilder.item(for: AgentScanResult(rawValue: "SN-AX9-2026"))

        XCTAssertEqual(item.kind, .text)
        XCTAssertEqual(item.text, "SN-AX9-2026")
        XCTAssertEqual(item.sourceSurface, "agent_scanner")
        XCTAssertEqual(item.note, "Analyze this scanned text and suggest the next action.")
    }
}
