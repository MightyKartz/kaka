import Foundation

public struct DocumentScanDraft: Equatable, Sendable {
    public static let defaultInstruction = "Summarize this scanned document, extract key fields, risks, and next actions."

    public let fileName: String
    public let pageCount: Int

    public init(fileName: String, pageCount: Int) {
        self.fileName = fileName
        self.pageCount = pageCount
    }
}
