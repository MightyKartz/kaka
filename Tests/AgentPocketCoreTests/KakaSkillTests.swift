import XCTest
@testable import AgentPocketCore

final class KakaSkillTests: XCTestCase {
    func testSkillIDsExposeStableRawValues() {
        XCTAssertEqual(KakaSkillID.photoEnhance.rawValue, "photo_enhance")
        XCTAssertEqual(KakaSkillID.ocr.rawValue, "ocr")
        XCTAssertEqual(KakaSkillID.translateText.rawValue, "translate_text")
        XCTAssertEqual(KakaSkillID.identifySubject.rawValue, "identify_subject")
        XCTAssertEqual(KakaSkillID.nutritionEstimate.rawValue, "nutrition_estimate")
    }

    func testVisionBackedSkillsMapToVisionTaskKind() {
        XCTAssertNil(KakaSkillID.photoEnhance.visionTaskKind)
        XCTAssertEqual(KakaSkillID.ocr.visionTaskKind, .scan)
        XCTAssertEqual(KakaSkillID.translateText.visionTaskKind, .translate)
        XCTAssertEqual(KakaSkillID.identifySubject.visionTaskKind, .identify)
        XCTAssertEqual(KakaSkillID.nutritionEstimate.visionTaskKind, .food)
    }
}
