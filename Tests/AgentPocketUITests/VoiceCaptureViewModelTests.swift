import XCTest
@testable import AgentPocketUI

@MainActor
final class VoiceCaptureViewModelTests: XCTestCase {
    func testPushToTalkPublishesEditableTranscriptAfterStop() async {
        let transcriber = StubVoiceRecordingTranscriber(transcript: " 提取图片里的文字 ")
        let viewModel = VoiceCaptureViewModel(transcriber: transcriber)

        await viewModel.startRecording()

        XCTAssertEqual(viewModel.state, .recording)
        let startedEvents = await transcriber.events()
        XCTAssertEqual(startedEvents, ["start"])
        XCTAssertFalse(viewModel.canSubmit)
        XCTAssertFalse(viewModel.canRecord)

        await viewModel.stopRecordingAndTranscribe()

        XCTAssertEqual(viewModel.state, .ready)
        XCTAssertEqual(viewModel.transcript, "提取图片里的文字")
        let finishedEvents = await transcriber.events()
        XCTAssertEqual(finishedEvents, ["start", "stop"])
        XCTAssertTrue(viewModel.canSubmit)
        XCTAssertTrue(viewModel.canRecord)
    }

    func testPushToTalkFailureKeepsTranscriptEditableForRetry() async {
        let transcriber = StubVoiceRecordingTranscriber(error: VoiceCaptureTestError.denied)
        let viewModel = VoiceCaptureViewModel(transcriber: transcriber, initialTranscript: "旧文字")

        await viewModel.startRecording()
        await viewModel.stopRecordingAndTranscribe()

        XCTAssertEqual(viewModel.state, .failed("Microphone access was denied."))
        XCTAssertEqual(viewModel.editableTranscript, "")
        XCTAssertFalse(viewModel.canSubmit)
        XCTAssertTrue(viewModel.canRecord)
    }

    func testCancelStopsActiveRecordingAndReturnsIdle() async {
        let transcriber = StubVoiceRecordingTranscriber(transcript: "不会发送")
        let viewModel = VoiceCaptureViewModel(transcriber: transcriber)

        await viewModel.startRecording()
        await viewModel.cancelRecording()

        XCTAssertEqual(viewModel.state, .idle)
        let events = await transcriber.events()
        XCTAssertEqual(events, ["start", "cancel"])
        XCTAssertEqual(viewModel.transcript, "")
        XCTAssertTrue(viewModel.canRecord)
    }

    func testVoiceCaptureStateDescriptionsAreUserVisible() {
        XCTAssertEqual(VoiceCaptureState.idle.statusText, "Ready for push-to-talk")
        XCTAssertEqual(VoiceCaptureState.recording.statusText, "Recording")
        XCTAssertEqual(VoiceCaptureState.transcribing.statusText, "Transcribing")
        XCTAssertEqual(VoiceCaptureState.ready.statusText, "Review transcript")
        XCTAssertEqual(VoiceCaptureState.failed("No speech was detected.").statusText, "No speech was detected.")
    }

    func testTranscriptMustBeNonEmptyBeforeSubmit() {
        let viewModel = VoiceCaptureViewModel()

        viewModel.markTranscriptReady("   \n  ")

        XCTAssertEqual(viewModel.state, .ready)
        XCTAssertFalse(viewModel.canSubmit)

        viewModel.editableTranscript = "  提取文字  "

        XCTAssertTrue(viewModel.canSubmit)
        XCTAssertEqual(viewModel.transcript, "提取文字")
    }

    func testManualTypingMakesIdleDraftReadyToSubmit() {
        let viewModel = VoiceCaptureViewModel()

        viewModel.editableTranscript = "  Summarize this receipt  "

        XCTAssertEqual(viewModel.state, .ready)
        XCTAssertTrue(viewModel.canSubmit)
        XCTAssertEqual(viewModel.transcript, "Summarize this receipt")
    }

    func testLegacyVoiceTranscriberAdapterPublishesTranscript() async {
        let transcriber = StubLegacyVoiceTranscriber(transcript: " Legacy transcript ")
        let viewModel = VoiceCaptureViewModel(transcriber: transcriber)

        await viewModel.startRecording()
        await viewModel.stopRecordingAndTranscribe()

        XCTAssertEqual(viewModel.state, .ready)
        XCTAssertEqual(viewModel.transcript, "Legacy transcript")
        XCTAssertTrue(viewModel.canSubmit)
    }

    func testLegacyDraftMethodsRemainAvailable() async {
        let transcriber = StubLegacyVoiceTranscriber(transcript: " Legacy draft ")
        let viewModel = VoiceCaptureViewModel(transcriber: transcriber)

        viewModel.beginRecording()
        XCTAssertEqual(viewModel.state, .recording)

        viewModel.beginTranscribing()
        XCTAssertEqual(viewModel.state, .transcribing)

        await viewModel.transcribeDraft()

        XCTAssertEqual(viewModel.state, .ready)
        XCTAssertEqual(viewModel.transcript, "Legacy draft")
        XCTAssertTrue(viewModel.canSubmit)
    }

    func testResetClearsTranscriptAndReturnsIdle() {
        let viewModel = VoiceCaptureViewModel()
        viewModel.markTranscriptReady("翻译这张图片")

        viewModel.reset()

        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertEqual(viewModel.transcript, "")
        XCTAssertEqual(viewModel.editableTranscript, "")
        XCTAssertFalse(viewModel.canSubmit)
    }
}

private enum VoiceCaptureTestError: LocalizedError {
    case denied

    var errorDescription: String? {
        "Microphone access was denied."
    }
}

private actor StubVoiceRecordingTranscriber: VoiceRecordingTranscribing {
    private let transcript: String
    private let error: Error?
    private var recordedEvents: [String] = []

    init(transcript: String = "", error: Error? = nil) {
        self.transcript = transcript
        self.error = error
    }

    func startRecording() async throws {
        recordedEvents.append("start")
    }

    func stopAndTranscribe() async throws -> String {
        recordedEvents.append("stop")
        if let error {
            throw error
        }
        return transcript
    }

    func cancelRecording() async {
        recordedEvents.append("cancel")
    }

    func events() -> [String] {
        recordedEvents
    }
}

private actor StubLegacyVoiceTranscriber: VoiceTranscribing {
    private let transcript: String

    init(transcript: String) {
        self.transcript = transcript
    }

    func transcribe() async throws -> String {
        transcript
    }
}
