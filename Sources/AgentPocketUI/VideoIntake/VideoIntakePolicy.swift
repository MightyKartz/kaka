import Foundation

public enum VideoIntakePolicy {
    public static let firstReleaseMaxBytes = 100 * 1_024 * 1_024

    public enum ValidationError: Error, Equatable {
        case exceedsFirstReleaseLimit
    }

    public static func validate(sourceURL: URL) throws {
        let values = try sourceURL.resourceValues(forKeys: [.fileSizeKey])
        let byteCount = values.fileSize ?? 0
        if byteCount > firstReleaseMaxBytes {
            throw ValidationError.exceedsFirstReleaseLimit
        }
    }
}
