import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

final class VideoInboxBuilderTests: XCTestCase {
    func testBuildsVideoInboxItemWithVisibleInstruction() throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let sourceURL = directory.appendingPathComponent("clip.mov")
        try Data("movie".utf8).write(to: sourceURL)

        let item = try VideoInboxBuilder(payloadDirectory: directory).makeInboxItem(
            sourceURL: sourceURL,
            fileName: "clip.mov",
            mimeType: "video/quicktime",
            receivedAt: Date(timeIntervalSince1970: 2)
        )

        XCTAssertEqual(item.kind, .video)
        XCTAssertEqual(item.mimeType, "video/quicktime")
        XCTAssertEqual(item.fileName, "clip.mov")
        XCTAssertEqual(item.sourceSurface, "video_capture")
        XCTAssertEqual(item.note, "Summarize this short video, identify the key moments, and suggest next actions.")
        XCTAssertEqual(item.route, .universalIntake)
        XCTAssertTrue(item.relativeFilePath?.hasPrefix("SharedPayloads/") == true)
    }

    func testRejectsVideoOverFirstReleaseLimit() throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let sourceURL = directory.appendingPathComponent("large.mov")
        FileManager.default.createFile(atPath: sourceURL.path, contents: Data())
        let handle = try FileHandle(forWritingTo: sourceURL)
        try handle.truncate(atOffset: UInt64(VideoIntakePolicy.firstReleaseMaxBytes + 1))
        try handle.close()

        XCTAssertThrowsError(
            try VideoInboxBuilder(payloadDirectory: directory).makeInboxItem(
                sourceURL: sourceURL,
                fileName: "large.mov",
                mimeType: "video/quicktime"
            )
        ) { error in
            XCTAssertEqual(error as? VideoIntakePolicy.ValidationError, .exceedsFirstReleaseLimit)
        }
    }
}
