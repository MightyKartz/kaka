import XCTest

final class AgentPocketPickerUITests: XCTestCase {
    override func setUp() {
        super.setUp()
        continueAfterFailure = false
    }

    func testChoosingSeededPhotoShowsReadySendAction() {
        let app = XCUIApplication()
        app.launchArguments = ["--agent-pocket-simulator-picker-ui-smoke"]
        app.launch()

        XCTAssertTrue(app.staticTexts["photosPickerUISmokeMarker"].waitForExistence(timeout: 5))

        let choosePhoto = app.buttons["choosePhotoButton"]
        XCTAssertTrue(choosePhoto.waitForExistence(timeout: 5))
        choosePhoto.tap()

        chooseFirstVisiblePhoto(in: app)

        let readyStatus = app.staticTexts["selectedPhotoReadyStatus"]
        XCTAssertTrue(readyStatus.waitForExistence(timeout: 10))

        let sendToLocalAgent = app.buttons["sendToLocalAgentButton"]
        XCTAssertTrue(sendToLocalAgent.waitForExistence(timeout: 2))
        XCTAssertTrue(sendToLocalAgent.isEnabled)
    }

    private func chooseFirstVisiblePhoto(in app: XCUIApplication) {
        let firstImage = app.images.element(boundBy: 0)
        if firstImage.waitForExistence(timeout: 5) {
            firstImage.tap()
            tapAddIfNeeded(in: app)
            return
        }

        let firstCell = app.cells.element(boundBy: 0)
        XCTAssertTrue(firstCell.waitForExistence(timeout: 5))
        firstCell.tap()
        tapAddIfNeeded(in: app)
    }

    private func tapAddIfNeeded(in app: XCUIApplication) {
        let addButton = app.buttons["Add"]
        if addButton.waitForExistence(timeout: 2) {
            addButton.tap()
        }
    }
}
