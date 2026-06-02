import AgentPocketCore
import XCTest
@testable import AgentPocketUI

final class PhotoSaveFlowTests: XCTestCase {
    func testSaveFlowStartsIdleAndRequestsPermissionOnlyWhenSaving() {
        let flow = PhotoSaveFlow()

        XCTAssertEqual(flow.state, .idle)

        flow.beginSave()

        XCTAssertEqual(flow.state, .requestingPermission)
    }

    func testDeniedPermissionShowsRecoveryPath() {
        let flow = PhotoSaveFlow()

        flow.handlePermission(.denied)

        XCTAssertEqual(flow.state, .permissionDenied)
        XCTAssertEqual(flow.recoveryActionTitle, "Open Settings")
        XCTAssertEqual(flow.recoveryDestination, .appSettings)
    }

    func testAuthorizedPermissionMovesToSavingThenSaved() {
        let flow = PhotoSaveFlow()

        flow.handlePermission(.authorized)
        XCTAssertEqual(flow.state, .saving)

        flow.markSaved()
        XCTAssertEqual(flow.state, .saved)
    }

    @MainActor
    func testSaveWithAuthorizedSaverEndsSaved() async {
        let flow = PhotoSaveFlow()
        let asset = DownloadedAsset(data: Data([1, 2, 3]), mimeType: "image/png")

        await flow.save(asset, using: FakePhotoLibrarySaver(result: .saved))

        XCTAssertEqual(flow.state, .saved)
    }

    @MainActor
    func testSaveWithDeniedSaverShowsRecovery() async {
        let flow = PhotoSaveFlow()
        let asset = DownloadedAsset(data: Data([1, 2, 3]), mimeType: "image/png")

        await flow.save(asset, using: FakePhotoLibrarySaver(result: .permissionDenied))

        XCTAssertEqual(flow.state, .permissionDenied)
        XCTAssertEqual(flow.recoveryActionTitle, "Open Settings")
    }

    @MainActor
    func testSaveWithFailingSaverShowsFailureMessage() async {
        let flow = PhotoSaveFlow()
        let asset = DownloadedAsset(data: Data([1, 2, 3]), mimeType: "image/png")

        await flow.save(asset, using: FakePhotoLibrarySaver(error: NSError(domain: "test", code: 1)))

        XCTAssertEqual(flow.state, .failed(message: "The image could not be saved."))
    }
}

private struct FakePhotoLibrarySaver: PhotoLibrarySaving {
    let result: PhotoSaveResult?
    let error: Error?

    init(result: PhotoSaveResult) {
        self.result = result
        self.error = nil
    }

    init(error: Error) {
        self.result = nil
        self.error = error
    }

    func save(_ asset: DownloadedAsset) async throws -> PhotoSaveResult {
        if let error {
            throw error
        }
        return result ?? .saved
    }
}
