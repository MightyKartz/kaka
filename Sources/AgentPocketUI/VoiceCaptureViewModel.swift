import Foundation

public protocol VoiceTranscribing: Sendable {
    func transcribe() async throws -> String
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
    @Published public var editableTranscript: String

    private let transcriber: (any VoiceTranscribing)?

    public init(
        transcriber: (any VoiceTranscribing)? = nil,
        initialTranscript: String = ""
    ) {
        self.transcriber = transcriber
        self.editableTranscript = initialTranscript
        self.state = initialTranscript.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? .idle : .ready
    }

    public var transcript: String {
        editableTranscript.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    public var canSubmit: Bool {
        state == .ready && transcript.isEmpty == false
    }

    public func beginRecording() {
        editableTranscript = ""
        state = .recording
    }

    public func beginTranscribing() {
        state = .transcribing
    }

    public func markTranscriptReady(_ transcript: String) {
        editableTranscript = transcript
        state = .ready
    }

    public func transcribeDraft() async {
        guard let transcriber else {
            state = .failed("Voice transcription is not configured.")
            return
        }

        state = .transcribing
        do {
            markTranscriptReady(try await transcriber.transcribe())
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    public func reset() {
        editableTranscript = ""
        state = .idle
    }

    public func cancel() {
        reset()
    }
}
