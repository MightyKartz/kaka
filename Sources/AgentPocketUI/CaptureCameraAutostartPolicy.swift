import Foundation

public enum CaptureCameraAutostartPolicy {
    public static func shouldOpenCamera(
        connectedRuntime: ConnectedRuntime?,
        captureState: CaptureFlowViewModel.State,
        hasAutoOpenedCamera: Bool,
        isCameraAvailable: Bool
    ) -> Bool {
        _ = connectedRuntime
        _ = captureState
        _ = hasAutoOpenedCamera
        _ = isCameraAvailable
        return false
    }
}
