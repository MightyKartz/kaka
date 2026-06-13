import AgentPocketCore
import Foundation

public struct DocumentScanInboxBuilder {
    private let payloadDirectory: URL

    public init(payloadDirectory: URL) {
        self.payloadDirectory = payloadDirectory
    }

    public func makeInboxItem(
        pdfData: Data,
        fileName: String,
        receivedAt: Date = Date()
    ) throws -> KakaInboxItem {
        let sharedDirectory = payloadDirectory.appendingPathComponent("SharedPayloads", isDirectory: true)
        try FileManager.default.createDirectory(at: sharedDirectory, withIntermediateDirectories: true)

        let safeFileName = (fileName as NSString).lastPathComponent
        let storedFileName = "\(UUID().uuidString)-\(safeFileName)"
        let storedURL = sharedDirectory.appendingPathComponent(storedFileName)
        try pdfData.write(to: storedURL, options: .atomic)

        return KakaInboxItem(
            kind: .pdf,
            receivedAt: receivedAt,
            sourceSurface: AgentLensSourceSurface.documentScanner.rawValue,
            note: DocumentScanDraft.defaultInstruction,
            fileName: safeFileName,
            mimeType: "application/pdf",
            relativeFilePath: "SharedPayloads/\(storedFileName)",
            route: .universalIntake
        )
    }
}
