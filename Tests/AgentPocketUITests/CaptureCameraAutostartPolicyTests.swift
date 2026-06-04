import XCTest
@testable import AgentPocketUI

final class CaptureCameraAutostartPolicyTests: XCTestCase {
    func testDoesNotOpenCameraForConnectedEmptyCaptureOnAppLaunch() {
        XCTAssertFalse(
            CaptureCameraAutostartPolicy.shouldOpenCamera(
                connectedRuntime: connectedRuntime(),
                captureState: .empty,
                hasAutoOpenedCamera: false,
                isCameraAvailable: true
            )
        )
    }

    func testDoesNotOpenCameraWithoutConnectedRuntime() {
        XCTAssertFalse(
            CaptureCameraAutostartPolicy.shouldOpenCamera(
                connectedRuntime: nil,
                captureState: .empty,
                hasAutoOpenedCamera: false,
                isCameraAvailable: true
            )
        )
    }

    func testDoesNotReopenCameraAfterFirstAutomaticPresentation() {
        XCTAssertFalse(
            CaptureCameraAutostartPolicy.shouldOpenCamera(
                connectedRuntime: connectedRuntime(),
                captureState: .empty,
                hasAutoOpenedCamera: true,
                isCameraAvailable: true
            )
        )
    }

    func testDoesNotOpenCameraWhenPhotoIsAlreadyPrepared() {
        XCTAssertFalse(
            CaptureCameraAutostartPolicy.shouldOpenCamera(
                connectedRuntime: connectedRuntime(),
                captureState: .ready(fileName: "camera.jpg", intentTitle: "Natural"),
                hasAutoOpenedCamera: false,
                isCameraAvailable: true
            )
        )
    }

    func testDoesNotOpenCameraWhenDeviceHasNoCamera() {
        XCTAssertFalse(
            CaptureCameraAutostartPolicy.shouldOpenCamera(
                connectedRuntime: connectedRuntime(),
                captureState: .empty,
                hasAutoOpenedCamera: false,
                isCameraAvailable: false
            )
        )
    }

    private func connectedRuntime() -> ConnectedRuntime {
        ConnectedRuntime(
            displayName: "Kartz Mac",
            runtime: "hermes",
            runtimeVersion: "dev"
        )
    }
}
