import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

final class InboxInstructionPresentationTests: XCTestCase {
    func testEnglishUniversalItemWithNoteShowsEditClearAndSubmitPreview() {
        let item = KakaInboxItem(
            kind: .url,
            note: "Summarize first.",
            url: "https://example.com",
            route: .universalIntake
        )

        let presentation = InboxInstructionPresentation(item: item, language: .english)

        XCTAssertTrue(presentation.hasInstruction)
        XCTAssertEqual(presentation.noteText, "Summarize first.")
        XCTAssertEqual(presentation.noteTitle, "Instruction")
        XCTAssertEqual(presentation.voiceActionTitle, "Edit Instruction")
        XCTAssertEqual(presentation.clearActionTitle, "Clear Instruction")
        XCTAssertEqual(presentation.submitPreviewText, "Send will include this instruction.")
    }

    func testChineseUniversalItemWithNoteShowsLocalizedPreview() {
        let item = KakaInboxItem(
            kind: .text,
            note: "先总结，再列行动项。",
            text: "Launch review",
            route: .universalIntake
        )

        let presentation = InboxInstructionPresentation(item: item, language: .chinese)

        XCTAssertTrue(presentation.hasInstruction)
        XCTAssertEqual(presentation.noteTitle, "指令")
        XCTAssertEqual(presentation.voiceActionTitle, "编辑指令")
        XCTAssertEqual(presentation.clearActionTitle, "清除指令")
        XCTAssertEqual(presentation.submitPreviewText, "发送时会附带这条指令。")
    }

    func testUniversalItemWithoutNoteShowsAddInstructionOnly() {
        let item = KakaInboxItem(kind: .url, url: "https://example.com", route: .universalIntake)

        let presentation = InboxInstructionPresentation(item: item, language: .english)

        XCTAssertFalse(presentation.hasInstruction)
        XCTAssertNil(presentation.noteText)
        XCTAssertNil(presentation.clearActionTitle)
        XCTAssertNil(presentation.submitPreviewText)
        XCTAssertEqual(presentation.voiceActionTitle, "Voice Instruction")
    }

    func testImageIntakeItemDoesNotExposeInstructionControls() {
        let item = KakaInboxItem(
            kind: .image,
            note: "Summarize this image.",
            fileName: "image.jpg",
            route: .imageIntake
        )

        let presentation = InboxInstructionPresentation(item: item, language: .english)

        XCTAssertFalse(presentation.isInstructionAvailable)
        XCTAssertFalse(presentation.hasInstruction)
        XCTAssertNil(presentation.noteText)
        XCTAssertNil(presentation.clearActionTitle)
        XCTAssertNil(presentation.submitPreviewText)
    }

    func testUniversalItemExposesDeterministicInstructionTemplates() {
        let item = KakaInboxItem(kind: .url, url: "https://example.com", route: .universalIntake)

        let presentation = InboxInstructionPresentation(item: item, language: .english)

        XCTAssertEqual(presentation.templates.map(\.id), ["summarize", "extract_actions", "translate", "ask_follow_up"])
        XCTAssertEqual(presentation.templates.map(\.title), ["Summarize", "Extract Actions", "Translate", "Ask Follow-up"])
        XCTAssertEqual(presentation.templates.map(\.instructionText), [
            "Summarize this item and highlight the key points.",
            "Extract action items, owners, and dates from this item.",
            "Translate the key points into my current language.",
            "Identify unanswered questions and suggest follow-up prompts."
        ])
    }

    func testChineseInstructionTemplatesAreLocalizedButStable() {
        let item = KakaInboxItem(kind: .text, text: "Launch notes", route: .universalIntake)

        let presentation = InboxInstructionPresentation(item: item, language: .chinese)

        XCTAssertEqual(presentation.templates.map(\.id), ["summarize", "extract_actions", "translate", "ask_follow_up"])
        XCTAssertEqual(presentation.templates.map(\.title), ["总结", "提取行动项", "翻译", "追问"])
        XCTAssertEqual(presentation.templates.first?.instructionText, "总结这个项目并突出关键要点。")
    }

    func testImageIntakeItemDoesNotExposeInstructionTemplates() {
        let item = KakaInboxItem(kind: .image, fileName: "image.jpg", route: .imageIntake)

        let presentation = InboxInstructionPresentation(item: item, language: .english)

        XCTAssertTrue(presentation.templates.isEmpty)
    }
}
