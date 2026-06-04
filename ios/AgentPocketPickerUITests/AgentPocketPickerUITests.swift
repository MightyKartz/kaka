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
        handlePhotoLibraryAlertIfNeeded()

        chooseFirstVisiblePhoto(in: app)

        let readyStatus = app.staticTexts["selectedPhotoReadyStatus"]
        XCTAssertTrue(readyStatus.waitForExistence(timeout: 10))

        let sendToKaka = app.buttons["sendToKakaButton"]
        XCTAssertTrue(sendToKaka.waitForExistence(timeout: 2))
        XCTAssertTrue(sendToKaka.isEnabled)
    }

    private func chooseFirstVisiblePhoto(in app: XCUIApplication) {
        let firstCell = app.cells.element(boundBy: 0)
        if firstCell.waitForExistence(timeout: 5) {
            firstCell.tap()
            tapAddIfNeeded(in: app)
            return
        }

        let photoImages = app.images.matching(
            NSPredicate(format: "label != %@ AND identifier != %@", "camera.fill", "camera.fill")
        )
        let firstImage = photoImages.element(boundBy: 0)
        XCTAssertTrue(firstImage.waitForExistence(timeout: 5))
        firstImage.tap()
        tapAddIfNeeded(in: app)
    }

    private func tapAddIfNeeded(in app: XCUIApplication) {
        for label in ["Add", "Done", "Choose", "Select", "添加", "完成", "选择"] {
            let button = app.buttons[label]
            if button.waitForExistence(timeout: 1) {
                button.tap()
                return
            }
        }
    }

    private func handlePhotoLibraryAlertIfNeeded() {
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let alert = springboard.alerts.element(boundBy: 0)
        guard alert.waitForExistence(timeout: 2) else {
            return
        }

        for label in [
            "Allow Full Access",
            "Allow Access to All Photos",
            "Select Photos…",
            "Select Photos...",
            "Allow",
            "OK",
            "允许完全访问",
            "允许访问所有照片",
            "选择照片…",
            "选择照片",
            "好"
        ] {
            let button = alert.buttons[label]
            if button.exists {
                button.tap()
                return
            }
        }

        if alert.buttons.count > 0 {
            alert.buttons.element(boundBy: alert.buttons.count - 1).tap()
        }
    }
}
