import AgentPocketCore
import Foundation

public struct VideoInboxBuilder {
    private let payloadDirectory: URL

    public init(payloadDirectory: URL) {
        self.payloadDirectory = payloadDirectory
    }

    public func makeInboxItem(
        sourceURL: URL,
        fileName: String,
        mimeType: String,
        receivedAt: Date = Date()
    ) throws -> KakaInboxItem {
        try VideoIntakePolicy.validate(sourceURL: sourceURL)

        let sharedDirectory = payloadDirectory.appendingPathComponent("SharedPayloads", isDirectory: true)
        try FileManager.default.createDirectory(at: sharedDirectory, withIntermediateDirectories: true)

        let safeFileName = (fileName as NSString).lastPathComponent
        let storedFileName = "\(UUID().uuidString)-\(safeFileName)"
        let destination = sharedDirectory.appendingPathComponent(storedFileName)
        if FileManager.default.fileExists(atPath: destination.path) {
            try FileManager.default.removeItem(at: destination)
        }
        try FileManager.default.copyItem(at: sourceURL, to: destination)

        return KakaInboxItem(
            kind: .video,
            receivedAt: receivedAt,
            sourceSurface: AgentLensSourceSurface.videoCapture.rawValue,
            note: VideoIntakeDraft.defaultInstruction,
            fileName: safeFileName,
            mimeType: mimeType,
            relativeFilePath: "SharedPayloads/\(storedFileName)",
            route: .universalIntake
        )
    }
}
