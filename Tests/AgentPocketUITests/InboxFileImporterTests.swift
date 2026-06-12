import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

final class InboxFileImporterTests: XCTestCase {
    func testImportsPDFIntoSharedPayloadsAsPendingUniversalIntakeItem() throws {
        let directory = try temporaryDirectory()
        let source = directory.appendingPathComponent("source.pdf")
        try Data("%PDF-1.7 test".utf8).write(to: source)
        let importer = InboxFileImporter(
            containerURL: directory,
            uuidProvider: { UUID(uuidString: "00000000-0000-0000-0000-00000000f138")! }
        )

        let item = try importer.importFile(
            from: source,
            now: Date(timeIntervalSince1970: 1_800_000_000),
            locale: "en-US"
        )

        XCTAssertEqual(item.kind, .pdf)
        XCTAssertEqual(item.sourceApp, "Files")
        XCTAssertEqual(item.sourceSurface, "file_picker")
        XCTAssertEqual(item.fileName, "source.pdf")
        XCTAssertEqual(item.mimeType, "application/pdf")
        XCTAssertEqual(item.locale, "en-US")
        XCTAssertEqual(item.route, .universalIntake)
        XCTAssertEqual(
            item.relativeFilePath,
            "SharedPayloads/00000000-0000-0000-0000-00000000F138-source.pdf"
        )
        XCTAssertEqual(
            try Data(contentsOf: directory.appendingPathComponent(try XCTUnwrap(item.relativeFilePath))),
            Data("%PDF-1.7 test".utf8)
        )
    }

    func testImportsJPEGAsPendingImageIntakeItem() throws {
        let directory = try temporaryDirectory()
        let source = directory.appendingPathComponent("photo.jpg")
        try Data([0xff, 0xd8, 0xff, 0xd9]).write(to: source)
        let importer = InboxFileImporter(
            containerURL: directory,
            uuidProvider: { UUID(uuidString: "00000000-0000-0000-0000-00000000f139")! }
        )

        let item = try importer.importFile(
            from: source,
            now: Date(timeIntervalSince1970: 1_800_000_001),
            locale: "en-US"
        )

        XCTAssertEqual(item.kind, .image)
        XCTAssertEqual(item.sourceApp, "Files")
        XCTAssertEqual(item.sourceSurface, "file_picker")
        XCTAssertEqual(item.mimeType, "image/jpeg")
        XCTAssertEqual(item.route, .imageIntake)
        XCTAssertEqual(
            item.relativeFilePath,
            "SharedPayloads/00000000-0000-0000-0000-00000000F139-photo.jpg"
        )
    }

    func testRejectsUnsupportedTextFileWithoutCopyingPayload() throws {
        let directory = try temporaryDirectory()
        let source = directory.appendingPathComponent("notes.txt")
        try Data("not supported here".utf8).write(to: source)
        let importer = InboxFileImporter(containerURL: directory)

        XCTAssertThrowsError(try importer.importFile(from: source, now: Date(), locale: "en-US")) { error in
            XCTAssertEqual(error as? InboxFileImporter.ImportError, .unsupportedFileType)
        }
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.appendingPathComponent("SharedPayloads").path))
    }

    private func temporaryDirectory() throws -> URL {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("kaka-file-import-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }
}
