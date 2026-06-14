import XCTest
@testable import AgentPocketUI

final class DarkControlContrastTests: XCTestCase {
    func testDisabledPrimaryControlsRemainReadableOnDarkSheets() {
        XCTAssertGreaterThanOrEqual(AgentPocketDarkControlContrast.disabledPrimaryBackgroundOpacity, 0.62)
        XCTAssertGreaterThanOrEqual(AgentPocketDarkControlContrast.disabledPrimaryLabelOpacity, 0.72)
    }
}
