import XCTest
@testable import AgentPocketUI

final class AgentScannerPresentationTests: XCTestCase {
    func testScannerCopyIsLocalizedForChinese() {
        let copy = AgentScannerCopy(language: .chinese)

        XCTAssertEqual(copy.title, "扫码")
        XCTAssertEqual(copy.instruction, "点按二维码、条码、链接或可见文本，再选择下一步。")
        XCTAssertEqual(copy.closeTitle, "关闭")
        XCTAssertEqual(copy.closeAccessibilityLabel, "关闭扫码")
    }

    func testScannerUnavailableCopyExplainsSimulatorFallback() {
        let copy = AgentScannerCopy(language: .chinese)

        XCTAssertEqual(copy.unavailableTitle, "扫码不可用")
        XCTAssertEqual(copy.unavailableDescription, "请在 iPhone 上打开 Pocket Agent 扫码；模拟器无法使用相机扫码。")
    }
}
