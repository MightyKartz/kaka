import Foundation

public struct VideoIntakeDraft: Equatable, Sendable {
    public static let defaultInstruction = "Summarize this short video, identify the key moments, and suggest next actions."

    public let fileName: String
    public let mimeType: String

    public init(fileName: String, mimeType: String) {
        self.fileName = fileName
        self.mimeType = mimeType
    }
}
