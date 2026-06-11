import AgentPocketCore
import Foundation
import UniformTypeIdentifiers

public protocol InboxFileImporting: Sendable {
    func importFile(from url: URL, now: Date, locale: String) throws -> KakaInboxItem
}

public struct InboxFileImporter: InboxFileImporting, @unchecked Sendable {
    public enum ImportError: Error, Equatable {
        case unsupportedFileType
        case unreadableFile
    }

    public static let supportedContentTypes: [UTType] = [.pdf, .image]

    private let containerURL: URL
    private let fileManager: FileManager
    private let uuidProvider: @Sendable () -> UUID

    public init(
        containerURL: URL,
        fileManager: FileManager = .default,
        uuidProvider: @escaping @Sendable () -> UUID = UUID.init
    ) {
        self.containerURL = containerURL
        self.fileManager = fileManager
        self.uuidProvider = uuidProvider
    }

    public init(
        appGroupIdentifier: String = FileKakaInboxStore.defaultAppGroupIdentifier,
        fileManager: FileManager = .default,
        uuidProvider: @escaping @Sendable () -> UUID = UUID.init
    ) {
        let directoryURL = fileManager.containerURL(forSecurityApplicationGroupIdentifier: appGroupIdentifier)
            ?? fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask)
                .first!
                .appendingPathComponent(appGroupIdentifier, isDirectory: true)
        self.init(containerURL: directoryURL, fileManager: fileManager, uuidProvider: uuidProvider)
    }

    public func importFile(
        from url: URL,
        now: Date = Date(),
        locale: String = Locale.current.identifier
    ) throws -> KakaInboxItem {
        let scoped = url.startAccessingSecurityScopedResource()
        defer {
            if scoped {
                url.stopAccessingSecurityScopedResource()
            }
        }

        guard fileManager.fileExists(atPath: url.path) else {
            throw ImportError.unreadableFile
        }

        let descriptor = try descriptor(for: url)
        let payloadDirectory = containerURL.appendingPathComponent("SharedPayloads", isDirectory: true)
        try fileManager.createDirectory(at: payloadDirectory, withIntermediateDirectories: true)

        let payloadName = "\(uuidProvider().uuidString)-\(sanitizedFileName(url.lastPathComponent))"
        let destination = payloadDirectory.appendingPathComponent(payloadName)
        if fileManager.fileExists(atPath: destination.path) {
            try fileManager.removeItem(at: destination)
        }
        try fileManager.copyItem(at: url, to: destination)

        return KakaInboxItem(
            kind: descriptor.kind,
            receivedAt: now,
            sourceApp: "Files",
            sourceSurface: "file_picker",
            locale: locale,
            fileName: url.lastPathComponent,
            mimeType: descriptor.mimeType,
            relativeFilePath: "SharedPayloads/\(payloadName)",
            route: descriptor.route
        )
    }

    private func descriptor(for url: URL) throws -> (kind: UniversalIntakeKind, mimeType: String, route: KakaInboxRoute) {
        let pathExtension = url.pathExtension.lowercased()
        if pathExtension == "pdf" {
            return (.pdf, "application/pdf", .universalIntake)
        }
        guard let type = UTType(filenameExtension: pathExtension),
              type.conforms(to: .image) else {
            throw ImportError.unsupportedFileType
        }
        return (.image, type.preferredMIMEType ?? "image/\(pathExtension)", .imageIntake)
    }

    private func sanitizedFileName(_ fileName: String) -> String {
        let lastPathComponent = (fileName as NSString).lastPathComponent
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: ".-_ "))
        let sanitizedScalars = lastPathComponent.unicodeScalars.map { scalar in
            allowed.contains(scalar) ? String(scalar) : "-"
        }
        let sanitized = sanitizedScalars.joined().trimmingCharacters(in: .whitespacesAndNewlines)
        return sanitized.isEmpty ? "imported-file" : sanitized
    }
}
