import AgentPocketCore
import Foundation
import UniformTypeIdentifiers
import UIKit

@MainActor
final class ShareViewController: UIViewController {
    private let appGroupID = "group.dev.kartz.Kaka"

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        Task { @MainActor in
            await captureFirstSupportedItem()
        }
    }

    private func captureFirstSupportedItem() async {
        guard
            let extensionItems = extensionContext?.inputItems as? [NSExtensionItem],
            let provider = firstSupportedProvider(in: extensionItems),
            let containerURL = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: appGroupID)
        else {
            finish()
            return
        }

        do {
            let item = try await makeInboxItem(from: provider, containerURL: containerURL)
            try FileKakaInboxStore(directoryURL: containerURL).append(item)
        } catch {
            // Share Extension capture must fail closed: no hidden upload and no background retry.
        }
        finish()
    }

    private func firstSupportedProvider(in extensionItems: [NSExtensionItem]) -> NSItemProvider? {
        extensionItems
            .lazy
            .compactMap(\.attachments)
            .flatMap { $0 }
            .first(where: isSupportedProvider)
    }

    private func isSupportedProvider(_ provider: NSItemProvider) -> Bool {
        provider.hasItemConformingToTypeIdentifier(UTType.url.identifier)
            || provider.hasItemConformingToTypeIdentifier(UTType.plainText.identifier)
            || provider.hasItemConformingToTypeIdentifier(UTType.image.identifier)
            || provider.hasItemConformingToTypeIdentifier(UTType.pdf.identifier)
    }

    private func finish() {
        extensionContext?.completeRequest(returningItems: [], completionHandler: nil)
    }

    private func makeInboxItem(from provider: NSItemProvider, containerURL: URL) async throws -> KakaInboxItem {
        if provider.hasItemConformingToTypeIdentifier(UTType.pdf.identifier) {
            let copied = try await copyFilePayload(
                from: provider,
                typeIdentifier: UTType.pdf.identifier,
                fallbackExtension: "pdf",
                containerURL: containerURL
            )
            return KakaInboxItem(
                kind: .pdf,
                source: IntakeSource(surface: "share_extension", hostApp: nil),
                fileName: copied.fileName,
                mimeType: "application/pdf",
                relativeFilePath: copied.relativePath
            )
        }

        if provider.hasItemConformingToTypeIdentifier(UTType.image.identifier) {
            let copied = try await copyFilePayload(
                from: provider,
                typeIdentifier: UTType.image.identifier,
                fallbackExtension: "jpg",
                containerURL: containerURL
            )
            return KakaInboxItem(
                kind: .image,
                source: IntakeSource(surface: "share_extension", hostApp: nil),
                fileName: copied.fileName,
                mimeType: copied.mimeType,
                relativeFilePath: copied.relativePath
            )
        }

        if provider.hasItemConformingToTypeIdentifier(UTType.url.identifier) {
            let url = try await provider.loadSharedURL(forTypeIdentifier: UTType.url.identifier)
            guard let url, url.isFileURL == false else {
                throw CocoaError(.fileReadUnsupportedScheme)
            }
            return KakaInboxItem(
                kind: .url,
                source: IntakeSource(surface: "share_extension", hostApp: nil),
                url: url.absoluteString
            )
        }

        if provider.hasItemConformingToTypeIdentifier(UTType.plainText.identifier) {
            let text = try await provider.loadSharedString(forTypeIdentifier: UTType.plainText.identifier)
            guard let text, text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false else {
                throw CocoaError(.fileReadUnknown)
            }
            return KakaInboxItem(
                kind: .text,
                source: IntakeSource(surface: "share_extension", hostApp: nil),
                text: text
            )
        }

        throw CocoaError(.fileReadUnsupportedScheme)
    }

    private func copyFilePayload(
        from provider: NSItemProvider,
        typeIdentifier: String,
        fallbackExtension: String,
        containerURL: URL
    ) async throws -> CopiedPayload {
        try await provider.copySharedFile(
            forTypeIdentifier: typeIdentifier,
            fallbackExtension: fallbackExtension,
            containerURL: containerURL
        )
    }
}

private struct CopiedPayload: Sendable {
    let fileName: String
    let mimeType: String
    let relativePath: String
}

private extension NSItemProvider {
    @MainActor
    func loadSharedString(forTypeIdentifier typeIdentifier: String) async throws -> String? {
        try await withCheckedThrowingContinuation { continuation in
            loadItem(forTypeIdentifier: typeIdentifier, options: nil) { value, error in
                if let error {
                    continuation.resume(throwing: error)
                } else {
                    continuation.resume(returning: value as? String)
                }
            }
        }
    }

    @MainActor
    func loadSharedURL(forTypeIdentifier typeIdentifier: String) async throws -> URL? {
        try await withCheckedThrowingContinuation { continuation in
            loadItem(forTypeIdentifier: typeIdentifier, options: nil) { value, error in
                if let error {
                    continuation.resume(throwing: error)
                } else if let url = value as? URL {
                    continuation.resume(returning: url)
                } else if let string = value as? String {
                    continuation.resume(returning: URL(string: string))
                } else {
                    continuation.resume(returning: nil)
                }
            }
        }
    }

    @MainActor
    func copySharedFile(
        forTypeIdentifier typeIdentifier: String,
        fallbackExtension: String,
        containerURL: URL
    ) async throws -> CopiedPayload {
        let typeIdentifiers = registeredTypeIdentifiers
        return try await withCheckedThrowingContinuation { continuation in
            loadFileRepresentation(forTypeIdentifier: typeIdentifier) { url, error in
                do {
                    if let error {
                        throw error
                    }
                    guard let sourceURL = url else {
                        throw CocoaError(.fileReadUnknown)
                    }

                    let inboxDirectory = containerURL.appendingPathComponent("SharedPayloads", isDirectory: true)
                    try FileManager.default.createDirectory(at: inboxDirectory, withIntermediateDirectories: true)

                    let originalName = sourceURL.lastPathComponent.isEmpty ? "shared.\(fallbackExtension)" : sourceURL.lastPathComponent
                    let storedName = "\(UUID().uuidString)-\(originalName)"
                    let destination = inboxDirectory.appendingPathComponent(storedName)
                    try FileManager.default.copyItem(at: sourceURL, to: destination)

                    continuation.resume(
                        returning: CopiedPayload(
                            fileName: originalName,
                            mimeType: typeIdentifiers.first ?? typeIdentifier,
                            relativePath: "SharedPayloads/\(storedName)"
                        )
                    )
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }
}
