import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

final class KakaSkillRouterTests: XCTestCase {
    func testChineseTextRoutesToOCR() {
        XCTAssertEqual(KakaSkillRouter.route("把里面的文字提取出来"), .ocr)
    }

    func testChineseTextRoutesToTranslate() {
        XCTAssertEqual(KakaSkillRouter.route("翻译成中文"), .translateText)
    }

    func testChineseTextRoutesToPhotoEnhance() {
        XCTAssertEqual(KakaSkillRouter.route("修得高级一点"), .photoEnhance)
    }

    func testUnknownTextFallsBackToPhotoEnhance() {
        XCTAssertEqual(KakaSkillRouter.route("帮我处理一下"), .photoEnhance)
    }
}
