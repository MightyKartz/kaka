import XCTest
@testable import AgentPocketCore

final class KakaInboxStoreTests: XCTestCase {
    func testFileStoreLoadsEmptyForMissingFile() throws {
        let directory = temporaryInboxDirectory()
        let store = FileKakaInboxStore(directoryURL: directory)

        XCTAssertEqual(try store.loadItems(), [])
    }

    func testFileStoreAddsUpsertsRemovesAndClearsItems() throws {
        let directory = temporaryInboxDirectory()
        let store = FileKakaInboxStore(directoryURL: directory)
        let id = UUID(uuidString: "00000000-0000-0000-0000-000000000001")!
        let item = KakaInboxItem(
            id: id,
            kind: .url,
            receivedAt: Date(timeIntervalSince1970: 1_800_000_000),
            sourceApp: "Safari",
            note: "Summarize this",
            locale: "en-US",
            preferredProfileID: "photo-agent",
            url: "https://example.com"
        )
        let updated = KakaInboxItem(
            id: id,
            kind: .url,
            receivedAt: Date(timeIntervalSince1970: 1_800_000_001),
            sourceApp: "Safari",
            note: "Remember this",
            locale: "en-US",
            preferredProfileID: "photo-agent",
            url: "https://example.com/updated"
        )

        try store.addOrUpdate(item)
        XCTAssertEqual(try store.loadItems(), [item])

        try store.addOrUpdate(updated)
        XCTAssertEqual(try store.loadItems(), [updated])

        try store.remove(id: id)
        XCTAssertEqual(try store.loadItems(), [])

        try store.addOrUpdate(item)
        try store.clear()
        XCTAssertEqual(try store.loadItems(), [])
    }

    func testFileStoreTreatsCorruptJSONAsEmptyAndCanOverwrite() throws {
        let directory = temporaryInboxDirectory()
        let store = FileKakaInboxStore(directoryURL: directory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try Data("not json".utf8).write(to: directory.appendingPathComponent("kaka-inbox.json"))

        XCTAssertEqual(try store.loadItems(), [])

        let item = KakaInboxItem(
            kind: .text,
            receivedAt: Date(timeIntervalSince1970: 1_800_000_000),
            sourceApp: "Notes",
            text: "Launch notes"
        )
        try store.addOrUpdate(item)

        XCTAssertEqual(try store.loadItems(), [item])
    }

    func testSharedImageItemPersistsImageIntakeRouteMetadata() throws {
        let item = KakaInboxItem(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000002")!,
            kind: .image,
            receivedAt: Date(timeIntervalSince1970: 1_800_000_000),
            sourceApp: "Photos",
            fileName: "shared.jpg",
            mimeType: "image/jpeg",
            relativeFilePath: "SharedPayloads/shared.jpg"
        )

        let data = try JSONEncoder.mobileBridge.encode(item)
        let body = String(data: data, encoding: .utf8)!
        let decoded = try JSONDecoder.mobileBridge.decode(KakaInboxItem.self, from: data)

        XCTAssertEqual(item.route, .imageIntake)
        XCTAssertTrue(body.contains("\"route\":\"image_intake\""))
        XCTAssertTrue(body.contains("\"relative_file_path\":\"SharedPayloads/shared.jpg\""))
        XCTAssertEqual(decoded, item)
    }

    func testInboxItemPersistsSourceSurfaceFromLegacySourceObject() throws {
        let data = Data("""
        {
          "id": "00000000-0000-0000-0000-000000000003",
          "kind": "text",
          "received_at": "2027-01-15T08:00:00Z",
          "source": {
            "surface": "voice",
            "host_app": "Kaka Voice"
          },
          "text": "Summarize my last meeting notes."
        }
        """.utf8)

        let item = try JSONDecoder.mobileBridge.decode(KakaInboxItem.self, from: data)
        let encodedData = try JSONEncoder.mobileBridge.encode(item)
        let encodedObject = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encodedData) as? [String: Any]
        )

        XCTAssertEqual(item.sourceSurface, "voice")
        XCTAssertEqual(item.sourceApp, "Kaka Voice")
        XCTAssertEqual(encodedObject["source_surface"] as? String, "voice")
        XCTAssertNil(encodedObject["source"])
    }

    func testRemovingAndClearingItemsDeletesSharedPayloadFiles() throws {
        let directory = temporaryInboxDirectory()
        let store = FileKakaInboxStore(directoryURL: directory)
        let payloadDirectory = directory.appendingPathComponent("SharedPayloads", isDirectory: true)
        try FileManager.default.createDirectory(at: payloadDirectory, withIntermediateDirectories: true)
        let firstPayload = payloadDirectory.appendingPathComponent("first.jpg")
        let secondPayload = payloadDirectory.appendingPathComponent("second.pdf")
        try Data("first".utf8).write(to: firstPayload)
        try Data("second".utf8).write(to: secondPayload)

        let first = KakaInboxItem(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000101")!,
            kind: .image,
            relativeFilePath: "SharedPayloads/first.jpg"
        )
        let second = KakaInboxItem(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000102")!,
            kind: .pdf,
            relativeFilePath: "SharedPayloads/second.pdf"
        )

        try store.addOrUpdate(first)
        try store.addOrUpdate(second)
        try store.remove(id: first.id)

        XCTAssertFalse(FileManager.default.fileExists(atPath: firstPayload.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: secondPayload.path))

        try store.clear()

        XCTAssertFalse(FileManager.default.fileExists(atPath: secondPayload.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: payloadDirectory.path))
    }

    func testDefaultAppGroupIdentifierIsDevelopmentGroup() {
        XCTAssertEqual(FileKakaInboxStore.defaultAppGroupIdentifier, "group.dev.kartz.Kaka")
    }

    private func temporaryInboxDirectory() -> URL {
        FileManager.default.temporaryDirectory
            .appendingPathComponent("kaka-inbox-\(UUID().uuidString)", isDirectory: true)
    }
}
