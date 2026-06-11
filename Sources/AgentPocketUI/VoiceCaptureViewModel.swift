import Foundation

public protocol VoiceTranscribing: Sendable {
    func transcribe() async throws -> String
}

public protocol VoiceRecordingTranscribing: Sendable {
    func startRecording() async throws
    func stopAndTranscribe() async throws -> String
    func cancelRecording() async
}

private struct LegacyVoiceRecordingTranscriber: VoiceRecordingTranscribing {
    let transcriber: any VoiceTranscribing

    func startRecording() async throws {}

    func stopAndTranscribe() async throws -> String {
        try await transcriber.transcribe()
    }

    func cancelRecording() async {}
}

public enum VoiceCaptureState: Equatable, Sendable {
    case idle
    case recording
    case transcribing
    case ready
    case failed(String)
}

@MainActor
public final class VoiceCaptureViewModel: ObservableObject {
    @Published public private(set) var state: VoiceCaptureState
    @Published public var editableTranscript: String {
        didSet {
            updateStateForManualTranscriptChange()
        }
    }

    private let transcriber: (any VoiceRecordingTranscribing)?

    public init(
        transcriber: (any VoiceRecordingTranscribing)? = nil,
        initialTranscript: String = ""
    ) {
        self.transcriber = transcriber
        self.editableTranscript = initialTranscript
        self.state = initialTranscript.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? .idle : .ready
    }

    public convenience init(
        transcriber: any VoiceTranscribing,
        initialTranscript: String = ""
    ) {
        self.init(
            transcriber: LegacyVoiceRecordingTranscriber(transcriber: transcriber),
            initialTranscript: initialTranscript
        )
    }

    public var transcript: String {
        editableTranscript.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    public var canSubmit: Bool {
        state == .ready && transcript.isEmpty == false
    }

    public var canRecord: Bool {
        switch state {
        case .idle, .ready, .failed:
            return true
        case .recording, .transcribing:
            return false
        }
    }

    public func beginRecording() {
        editableTranscript = ""
        state = .recording
    }

    public func beginTranscribing() {
        state = .transcribing
    }

    public func startRecording() async {
        guard let transcriber else {
            editableTranscript = ""
            state = .failed("Voice transcription is not configured.")
            return
        }

        editableTranscript = ""
        state = .recording
        do {
            try await transcriber.startRecording()
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    public func markTranscriptReady(_ transcript: String) {
        editableTranscript = transcript
        state = .ready
    }

    public func stopRecordingAndTranscribe() async {
        guard let transcriber else {
            state = .failed("Voice transcription is not configured.")
            return
        }

        state = .transcribing
        do {
            markTranscriptReady(try await transcriber.stopAndTranscribe())
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    public func transcribeDraft() async {
        await stopRecordingAndTranscribe()
    }

    public func reset() {
        editableTranscript = ""
        state = .idle
    }

    public func cancelRecording() async {
        await transcriber?.cancelRecording()
        reset()
    }

    public func cancel() {
        reset()
    }

    private func updateStateForManualTranscriptChange() {
        switch state {
        case .idle, .ready, .failed:
            state = transcript.isEmpty ? .idle : .ready
        case .recording, .transcribing:
            break
        }
    }
}

public extension VoiceCaptureState {
    var statusText: String {
        switch self {
        case .idle:
            return "Ready for push-to-talk"
        case .recording:
            return "Recording"
        case .transcribing:
            return "Transcribing"
        case .ready:
            return "Review transcript"
        case .failed(let message):
            return message
        }
    }
}
