import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

final class DocumentScanInboxBuilderTests: XCTestCase {
    func testBuildsPDFInboxItemForScannedDocument() throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)

        let builder = DocumentScanInboxBuilder(payloadDirectory: directory)
        let item = try builder.makeInboxItem(
            pdfData: Data("pdf".utf8),
            fileName: "scan.pdf",
            receivedAt: Date(timeIntervalSince1970: 1)
        )

        XCTAssertEqual(item.kind, .pdf)
        XCTAssertEqual(item.mimeType, "application/pdf")
        XCTAssertEqual(item.fileName, "scan.pdf")
        XCTAssertEqual(item.sourceSurface, "document_scanner")
        XCTAssertEqual(item.note, "Summarize this scanned document, extract key fields, risks, and next actions.")
        XCTAssertEqual(item.route, .universalIntake)
        XCTAssertTrue(item.relativeFilePath?.hasPrefix("SharedPayloads/") == true)
    }
}
