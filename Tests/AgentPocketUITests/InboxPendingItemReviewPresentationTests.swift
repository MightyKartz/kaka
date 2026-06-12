import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

final class InboxPendingItemReviewPresentationTests: XCTestCase {
    func testURLItemShowsSourceTypeContentInstructionAndIncludedContext() {
        let item = KakaInboxItem(
            kind: .url,
            sourceApp: "Safari",
            sourceSurface: "paste",
            note: "Summarize first.",
            locale: "en-US",
            preferredProfileID: "work",
            url: "https://example.com/article",
            route: .universalIntake
        )

        let presentation = InboxPendingItemReviewPresentation(
            item: item,
            contextIncluded: true,
            language: .english
        )

        XCTAssertEqual(presentation.title, "Review Details")
        XCTAssertEqual(presentation.actionTitle(isExpanded: false), "Review Details")
        XCTAssertEqual(presentation.actionTitle(isExpanded: true), "Hide Details")
        XCTAssertEqual(presentation.rows.map(\.id), [
            "source",
            "type",
            "content",
            "instruction",
            "context",
            "route",
            "locale",
            "profile"
        ])
        XCTAssertEqual(presentation.value(for: "source"), "Paste from Safari")
        XCTAssertEqual(presentation.value(for: "type"), "Link")
        XCTAssertEqual(presentation.value(for: "content"), "https://example.com/article")
        XCTAssertEqual(presentation.value(for: "instruction"), "Summarize first.")
        XCTAssertEqual(presentation.value(for: "context"), "Selected for this task")
        XCTAssertEqual(presentation.value(for: "route"), "Universal Intake")
        XCTAssertEqual(presentation.value(for: "locale"), "en-US")
        XCTAssertEqual(presentation.value(for: "profile"), "work")
    }

    func testFileItemShowsFileNameAndMimeTypeWithoutLeakingRelativePath() {
        let item = KakaInboxItem(
            kind: .pdf,
            sourceApp: "Files",
            sourceSurface: "file_picker",
            fileName: "brief.pdf",
            mimeType: "application/pdf",
            relativeFilePath: "SharedPayloads/private-secret-folder/hidden-original.pdf",
            route: .universalIntake
        )

        let presentation = InboxPendingItemReviewPresentation(
            item: item,
            contextIncluded: false,
            language: .english
        )

        XCTAssertEqual(presentation.value(for: "source"), "Files from Files")
        XCTAssertEqual(presentation.value(for: "type"), "PDF")
        XCTAssertEqual(presentation.value(for: "file"), "brief.pdf")
        XCTAssertEqual(presentation.value(for: "mime_type"), "application/pdf")
        XCTAssertEqual(presentation.value(for: "local_payload"), "Copied into Kaka Inbox")
        XCTAssertEqual(presentation.value(for: "context"), "Not selected for this task")
        let joinedValues = presentation.rows.map(\.value).joined(separator: "\n")
        XCTAssertFalse(joinedValues.contains("SharedPayloads"))
        XCTAssertFalse(joinedValues.contains("private-secret-folder"))
        XCTAssertFalse(joinedValues.contains("hidden-original.pdf"))
    }

    func testLongTextIsTrimmedAndBounded() {
        let text = String(repeating: "Launch notes ", count: 20)
        let item = KakaInboxItem(
            kind: .text,
            sourceSurface: "voice",
            text: "  \(text)  ",
            route: .universalIntake
        )

        let presentation = InboxPendingItemReviewPresentation(
            item: item,
            contextIncluded: false,
            language: .english
        )

        let content = presentation.value(for: "content")
        XCTAssertNotNil(content)
        XCTAssertLessThanOrEqual(content?.count ?? 0, 123)
        XCTAssertTrue(content?.hasSuffix("...") == true)
        XCTAssertFalse(content?.hasPrefix(" ") == true)
    }

    func testChinesePresentationIsLocalized() {
        let item = KakaInboxItem(
            kind: .screenshot,
            sourceApp: "Photos",
            sourceSurface: "share_extension",
            fileName: "screen.png",
            mimeType: "image/png",
            route: .imageIntake
        )

        let presentation = InboxPendingItemReviewPresentation(
            item: item,
            contextIncluded: true,
            language: .chinese
        )

        XCTAssertEqual(presentation.title, "查看详情")
        XCTAssertEqual(presentation.actionTitle(isExpanded: false), "查看详情")
        XCTAssertEqual(presentation.actionTitle(isExpanded: true), "收起详情")
        XCTAssertEqual(presentation.value(for: "source"), "系统分享来自 Photos")
        XCTAssertEqual(presentation.value(for: "type"), "截图")
        XCTAssertEqual(presentation.value(for: "context"), "图片任务不会随本次发送")
        XCTAssertEqual(presentation.value(for: "route"), "图片处理")
    }

    func testImageIntakeNoteIsNotShownAsInstruction() {
        let item = KakaInboxItem(
            kind: .image,
            note: "Do not show as universal instruction.",
            fileName: "image.jpg",
            route: .imageIntake
        )

        let presentation = InboxPendingItemReviewPresentation(
            item: item,
            contextIncluded: false,
            language: .english
        )

        XCTAssertNil(presentation.value(for: "instruction"))
    }
}

private extension InboxPendingItemReviewPresentation {
    func value(for rowID: String) -> String? {
        rows.first { $0.id == rowID }?.value
    }
}
