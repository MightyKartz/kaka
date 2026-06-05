import Foundation

public protocol KakaInboxStoring: Sendable {
    func loadItems() throws -> [KakaInboxItem]
    func addOrUpdate(_ item: KakaInboxItem) throws
    func append(_ item: KakaInboxItem) throws
    func remove(id: UUID) throws
    func clear() throws
}

public final class FileKakaInboxStore: KakaInboxStoring, @unchecked Sendable {
    public static let defaultAppGroupIdentifier = "group.dev.kartz.Kaka"

    private let directoryURL: URL
    private let fileName: String
    private let fileManager: FileManager
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    public convenience init(
        appGroupIdentifier: String = FileKakaInboxStore.defaultAppGroupIdentifier,
        fileName: String = "kaka-inbox.json",
        fileManager: FileManager = .default
    ) {
        let directoryURL = fileManager.containerURL(forSecurityApplicationGroupIdentifier: appGroupIdentifier)
            ?? fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask)
                .first!
                .appendingPathComponent(appGroupIdentifier, isDirectory: true)
        self.init(directoryURL: directoryURL, fileName: fileName, fileManager: fileManager)
    }

    public init(
        directoryURL: URL,
        fileName: String = "kaka-inbox.json",
        fileManager: FileManager = .default
    ) {
        self.directoryURL = directoryURL
        self.fileName = fileName
        self.fileManager = fileManager
        encoder = JSONEncoder.mobileBridge
        decoder = JSONDecoder.mobileBridge
    }

    public func loadItems() throws -> [KakaInboxItem] {
        let url = inboxFileURL
        guard fileManager.fileExists(atPath: url.path) else {
            return []
        }

        do {
            let data = try Data(contentsOf: url)
            return try decoder.decode([KakaInboxItem].self, from: data)
        } catch {
            return []
        }
    }

    public func addOrUpdate(_ item: KakaInboxItem) throws {
        var items = try loadItems()
        items.removeAll { $0.id == item.id }
        items.append(item)
        try save(items)
    }

    public func append(_ item: KakaInboxItem) throws {
        try addOrUpdate(item)
    }

    public func remove(id: UUID) throws {
        let existing = try loadItems()
        for item in existing where item.id == id {
            try deletePayloadIfPresent(for: item)
        }
        let items = existing.filter { $0.id != id }
        try save(items)
    }

    public func clear() throws {
        for item in try loadItems() {
            try deletePayloadIfPresent(for: item)
        }
        let url = inboxFileURL
        if fileManager.fileExists(atPath: url.path) {
            try fileManager.removeItem(at: url)
        }
        let payloadDirectory = directoryURL.appendingPathComponent("SharedPayloads", isDirectory: true)
        if fileManager.fileExists(atPath: payloadDirectory.path) {
            try fileManager.removeItem(at: payloadDirectory)
        }
    }

    private var inboxFileURL: URL {
        directoryURL.appendingPathComponent(fileName)
    }

    private func save(_ items: [KakaInboxItem]) throws {
        try fileManager.createDirectory(at: directoryURL, withIntermediateDirectories: true)
        let sorted = items.sorted {
            if $0.receivedAt == $1.receivedAt {
                return $0.id.uuidString < $1.id.uuidString
            }
            return $0.receivedAt < $1.receivedAt
        }
        let data = try encoder.encode(sorted)
        try data.write(to: inboxFileURL, options: [.atomic])
    }

    private func deletePayloadIfPresent(for item: KakaInboxItem) throws {
        guard let url = payloadURL(for: item),
              fileManager.fileExists(atPath: url.path) else {
            return
        }
        try fileManager.removeItem(at: url)
    }

    private func payloadURL(for item: KakaInboxItem) -> URL? {
        guard let relativePath = item.relativeFilePath,
              relativePath.hasPrefix("/") == false,
              (relativePath as NSString).pathComponents.contains("..") == false else {
            return nil
        }
        let baseURL = directoryURL.standardizedFileURL
        let payloadURL = baseURL.appendingPathComponent(relativePath).standardizedFileURL
        let basePath = baseURL.path.hasSuffix("/") ? baseURL.path : "\(baseURL.path)/"
        guard payloadURL.path.hasPrefix(basePath) else {
            return nil
        }
        return payloadURL
    }
}
