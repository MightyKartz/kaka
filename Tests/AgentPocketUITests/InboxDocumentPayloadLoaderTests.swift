import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

final class InboxDocumentPayloadLoaderTests: XCTestCase {
    func testLoadsPDFPayloadAsGenericAssetUpload() throws {
        let directory = try temporaryDirectory()
        let payloadDirectory = directory.appendingPathComponent("SharedPayloads", isDirectory: true)
        try FileManager.default.createDirectory(at: payloadDirectory, withIntermediateDirectories: true)
        let fileURL = payloadDirectory.appendingPathComponent("brief.pdf")
        try Data("%PDF-1.7".utf8).write(to: fileURL)
        let item = KakaInboxItem(
            kind: .pdf,
            sourceApp: "Files",
            fileName: "brief.pdf",
            mimeType: "application/pdf",
            relativeFilePath: "SharedPayloads/brief.pdf"
        )
        let loader = FileInboxDocumentPayloadLoader(containerURL: directory, maxUploadMB: 25)

        let upload = try loader.preparedUpload(for: item)

        XCTAssertEqual(upload.data, Data("%PDF-1.7".utf8))
        XCTAssertEqual(upload.mimeType, "application/pdf")
        XCTAssertEqual(upload.fileName, "brief.pdf")
        XCTAssertEqual(upload.metadata.source, "share_extension")
        XCTAssertEqual(upload.metadata.originalFileName, "brief.pdf")
        XCTAssertEqual(upload.metadata.stripSensitiveMetadata, true)
        XCTAssertNil(upload.metadata.width)
    }

    func testPreparedPDFUploadUsesInboxSourceSurface() throws {
        let directory = try temporaryDirectory()
        let payloadDirectory = directory.appendingPathComponent("SharedPayloads", isDirectory: true)
        try FileManager.default.createDirectory(at: payloadDirectory, withIntermediateDirectories: true)
        let fileURL = payloadDirectory.appendingPathComponent("brief.pdf")
        try Data("%PDF".utf8).write(to: fileURL)
        let item = KakaInboxItem(
            kind: .pdf,
            sourceApp: "Files",
            sourceSurface: "file_picker",
            fileName: "brief.pdf",
            mimeType: "application/pdf",
            relativeFilePath: "SharedPayloads/brief.pdf",
            route: .universalIntake
        )
        let loader = FileInboxDocumentPayloadLoader(containerURL: directory, maxUploadMB: 25)

        let upload = try loader.preparedUpload(for: item)

        XCTAssertEqual(upload.metadata.source, "file_picker")
    }

    func testRejectsUnsafeRelativePayloadPaths() throws {
        let directory = try temporaryDirectory()
        let loader = FileInboxDocumentPayloadLoader(containerURL: directory, maxUploadMB: 25)
        let absolute = KakaInboxItem(
            kind: .pdf,
            fileName: "brief.pdf",
            mimeType: "application/pdf",
            relativeFilePath: "/tmp/brief.pdf"
        )
        let traversal = KakaInboxItem(
            kind: .pdf,
            fileName: "brief.pdf",
            mimeType: "application/pdf",
            relativeFilePath: "../brief.pdf"
        )

        XCTAssertThrowsError(try loader.preparedUpload(for: absolute))
        XCTAssertThrowsError(try loader.preparedUpload(for: traversal))
    }

    func testRejectsSymlinkPayloadsOutsideContainer() throws {
        let directory = try temporaryDirectory()
        let payloadDirectory = directory.appendingPathComponent("SharedPayloads", isDirectory: true)
        try FileManager.default.createDirectory(at: payloadDirectory, withIntermediateDirectories: true)
        let outsideDirectory = try temporaryDirectory()
        let outsideFile = outsideDirectory.appendingPathComponent("outside.pdf")
        try Data("%PDF-1.7".utf8).write(to: outsideFile)
        let symlinkURL = payloadDirectory.appendingPathComponent("linked.pdf")
        try FileManager.default.createSymbolicLink(at: symlinkURL, withDestinationURL: outsideFile)
        let item = KakaInboxItem(
            kind: .pdf,
            fileName: "linked.pdf",
            mimeType: "application/pdf",
            relativeFilePath: "SharedPayloads/linked.pdf"
        )
        let loader = FileInboxDocumentPayloadLoader(containerURL: directory, maxUploadMB: 25)

        XCTAssertThrowsError(try loader.preparedUpload(for: item))
    }

    func testRejectsOversizedPDFPayloads() throws {
        let directory = try temporaryDirectory()
        let payloadDirectory = directory.appendingPathComponent("SharedPayloads", isDirectory: true)
        try FileManager.default.createDirectory(at: payloadDirectory, withIntermediateDirectories: true)
        let fileURL = payloadDirectory.appendingPathComponent("large.pdf")
        try Data(repeating: 0x41, count: 1_048_577).write(to: fileURL)
        let item = KakaInboxItem(
            kind: .pdf,
            fileName: "large.pdf",
            mimeType: "application/pdf",
            relativeFilePath: "SharedPayloads/large.pdf"
        )
        let loader = FileInboxDocumentPayloadLoader(containerURL: directory, maxUploadMB: 1)

        XCTAssertThrowsError(try loader.preparedUpload(for: item))
    }

    private func temporaryDirectory() throws -> URL {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("InboxDocumentPayloadLoaderTests-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }
}
