import XCTest

@MainActor
final class AgentPocketPickerUITests: XCTestCase {
    override func setUp() {
        super.setUp()
        continueAfterFailure = false
    }

    func testPhotosPickerSurfaceShowsChoosePhotoAction() {
        let app = XCUIApplication()
        app.launchArguments = ["--agent-pocket-simulator-picker-ui-smoke"]
        app.launch()

        XCTAssertTrue(app.staticTexts["photosPickerUISmokeMarker"].waitForExistence(timeout: 5))

        let choosePhoto = app.buttons["choosePhotoButton"]
        XCTAssertTrue(choosePhoto.waitForExistence(timeout: 5))
        XCTAssertTrue(choosePhoto.isEnabled)
    }

    func testSeededPhotoShowsReadySendAction() {
        let app = XCUIApplication()
        app.launchArguments = ["--agent-pocket-simulator-capture-ready-smoke"]
        app.launch()

        let readyStatus = app.staticTexts["selectedPhotoReadyStatus"]
        XCTAssertTrue(readyStatus.waitForExistence(timeout: 10))

        let sendToKaka = app.buttons["sendToKakaButton"]
        XCTAssertTrue(sendToKaka.waitForExistence(timeout: 2))
        XCTAssertTrue(sendToKaka.isEnabled)
    }
}
