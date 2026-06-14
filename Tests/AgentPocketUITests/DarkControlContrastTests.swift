import XCTest
@testable import AgentPocketUI

final class DarkControlContrastTests: XCTestCase {
    func testDisabledPrimaryControlsReadAsInactiveOnDarkSheets() {
        XCTAssertLessThanOrEqual(AgentPocketDarkControlContrast.disabledPrimaryNeutralFillOpacity, 0.16)
        XCTAssertGreaterThanOrEqual(AgentPocketDarkControlContrast.disabledPrimaryLabelOpacity, 0.48)
        XCTAssertLessThanOrEqual(AgentPocketDarkControlContrast.disabledPrimaryLabelOpacity, 0.68)
    }
}
