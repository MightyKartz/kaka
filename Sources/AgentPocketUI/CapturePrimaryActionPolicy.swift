import Foundation

public enum CapturePrimaryActionMode: Equatable, Sendable {
    case openCamera
    case submitPreparedPhoto
    case reviewCompletedResult
    case disabled
}

public enum CapturePrimaryActionPolicy {
    public static func mode(
        captureState: CaptureFlowViewModel.State,
        hasPreparedUpload: Bool,
        hasCompletedStatus: Bool
    ) -> CapturePrimaryActionMode {
        switch captureState {
        case .empty:
            return .openCamera
        case .ready:
            return hasPreparedUpload ? .submitPreparedPhoto : .disabled
        case .failed:
            return hasPreparedUpload ? .submitPreparedPhoto : .openCamera
        case .completed:
            return hasCompletedStatus ? .reviewCompletedResult : .disabled
        case .loadingPhoto, .uploading, .startingTask, .submitted, .running:
            return .disabled
        }
    }
}
