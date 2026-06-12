@testable import AgentPocketCore
@testable import AgentPocketUI
import XCTest

final class VoiceCapturePresentationTests: XCTestCase {
    func testEnglishInboxDraftPresentationSavesDraft() {
        let presentation = VoiceCapturePresentation.inboxDraft(language: .english)

        XCTAssertEqual(presentation.navigationTitle, "Voice Draft")
        XCTAssertEqual(presentation.transcriptAccessibilityLabel, "Voice draft transcript")
        XCTAssertEqual(presentation.submitTitle, "Save Draft")
        XCTAssertEqual(presentation.submitSystemImage, "tray.and.arrow.down.fill")
    }

    func testEnglishInboxInstructionPresentationSavesInstruction() {
        let newInstruction = VoiceCapturePresentation.inboxInstruction(
            hasExistingInstruction: false,
            language: .english
        )
        let editInstruction = VoiceCapturePresentation.inboxInstruction(
            hasExistingInstruction: true,
            language: .english
        )

        XCTAssertEqual(newInstruction.navigationTitle, "Voice Instruction")
        XCTAssertEqual(editInstruction.navigationTitle, "Edit Instruction")
        XCTAssertEqual(newInstruction.transcriptAccessibilityLabel, "Voice instruction transcript")
        XCTAssertEqual(newInstruction.submitTitle, "Save Instruction")
        XCTAssertEqual(newInstruction.submitSystemImage, "checkmark.circle.fill")
    }

    func testChineseInboxPresentationsAreLocalized() {
        let draft = VoiceCapturePresentation.inboxDraft(language: .chinese)
        let instruction = VoiceCapturePresentation.inboxInstruction(
            hasExistingInstruction: true,
            language: .chinese
        )

        XCTAssertEqual(draft.navigationTitle, "语音草稿")
        XCTAssertEqual(draft.transcriptAccessibilityLabel, "语音草稿转写")
        XCTAssertEqual(draft.submitTitle, "保存草稿")
        XCTAssertEqual(instruction.navigationTitle, "编辑指令")
        XCTAssertEqual(instruction.transcriptAccessibilityLabel, "语音指令转写")
        XCTAssertEqual(instruction.submitTitle, "保存指令")
    }
}
