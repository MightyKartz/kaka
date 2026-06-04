import Foundation

public enum CapturePreparedPhotoSource: Equatable, Sendable {
    case camera
    case photoLibrary
}

public enum CaptureAutosubmitPolicy {
    public static func shouldSubmitPreparedPhoto(
        source: CapturePreparedPhotoSource,
        hasPreparedUpload: Bool,
        hasActiveConnection: Bool,
        allowsAutosubmit: Bool = true
    ) -> Bool {
        source == .camera && hasPreparedUpload && hasActiveConnection && allowsAutosubmit
    }
}
