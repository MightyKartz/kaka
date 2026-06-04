import XCTest
@testable import AgentPocketCore

final class EditIntentTests: XCTestCase {
    func testPhaseOneIntentsUseStableBridgeStyleValues() {
        XCTAssertEqual(
            EditIntent.allCases.map(\.rawValue),
            ["natural_enhance", "portrait_polish", "product_shot", "social_cover"]
        )
    }

    func testIntentDisplayTitlesAreStable() {
        XCTAssertEqual(EditIntent.naturalEnhance.displayTitle, "Natural Enhance")
        XCTAssertEqual(EditIntent.portraitPolish.displayTitle, "Portrait Polish")
        XCTAssertEqual(EditIntent.productShot.displayTitle, "Product Shot")
        XCTAssertEqual(EditIntent.socialCover.displayTitle, "Social Cover")
    }

    func testScenePackTitlesMatchMasterShotCaptureChips() {
        XCTAssertEqual(
            EditIntent.allCases.map(\.sceneTitle),
            ["Natural", "Portrait", "Product", "Social"]
        )
    }

    func testMasterShotCompositionBadgePreservesOriginalFrame() {
        XCTAssertEqual(EditIntent.masterShotCompositionBadge, "Original")
    }

    func testDefaultInstructionsPreservePhotoSafetyBoundaries() {
        XCTAssertTrue(EditIntent.naturalEnhance.defaultInstruction.contains("Keep it realistic"))
        XCTAssertTrue(EditIntent.portraitPolish.defaultInstruction.contains("Do not change identity"))
        XCTAssertTrue(EditIntent.productShot.defaultInstruction.contains("Keep the product accurate"))
        XCTAssertTrue(EditIntent.socialCover.defaultInstruction.contains("original framing"))
    }
}
