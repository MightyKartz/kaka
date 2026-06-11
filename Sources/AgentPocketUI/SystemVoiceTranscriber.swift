import Foundation

#if os(iOS) && canImport(AVFoundation) && canImport(Speech)
import AVFoundation
import Speech

public enum VoiceTranscriptionError: LocalizedError, Equatable, Sendable {
    case microphoneDenied
    case speechDenied
    case recognizerUnavailable
    case notRecording
    case recordingFailed
    case emptyTranscript
    case transcriptionTimedOut

    public var errorDescription: String? {
        switch self {
        case .microphoneDenied:
            return "Microphone access was denied."
        case .speechDenied:
            return "Speech recognition access was denied."
        case .recognizerUnavailable:
            return "Speech recognition is not available for the current locale."
        case .notRecording:
            return "No active voice recording was found."
        case .recordingFailed:
            return "Voice recording could not start."
        case .emptyTranscript:
            return "No speech was detected."
        case .transcriptionTimedOut:
            return "Speech transcription timed out."
        }
    }
}

public final class SystemVoiceTranscriber: NSObject, VoiceRecordingTranscribing, @unchecked Sendable {
    private let locale: Locale
    private let fileManager: FileManager
    private let recordingURLProvider: @Sendable () -> URL
    private let transcriptionTimeoutNanoseconds: UInt64
    private var recorder: AVAudioRecorder?
    private var recordingURL: URL?
    private var recognitionTask: SFSpeechRecognitionTask?

    public init(
        locale: Locale = .current,
        fileManager: FileManager = .default,
        transcriptionTimeoutNanoseconds: UInt64 = 30_000_000_000,
        recordingURLProvider: @escaping @Sendable () -> URL = {
            FileManager.default.temporaryDirectory
                .appendingPathComponent("kaka-voice-\(UUID().uuidString)")
                .appendingPathExtension("m4a")
        }
    ) {
        self.locale = locale
        self.fileManager = fileManager
        self.transcriptionTimeoutNanoseconds = transcriptionTimeoutNanoseconds
        self.recordingURLProvider = recordingURLProvider
    }

    public func startRecording() async throws {
        try await requestPermissions()

        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .spokenAudio, options: [.duckOthers, .defaultToSpeaker])
        try session.setActive(true)

        let url = recordingURLProvider()
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44_100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        let recorder = try AVAudioRecorder(url: url, settings: settings)
        recorder.prepareToRecord()
        guard recorder.record() else {
            try? fileManager.removeItem(at: url)
            try? session.setActive(false, options: .notifyOthersOnDeactivation)
            throw VoiceTranscriptionError.recordingFailed
        }
        self.recorder = recorder
        self.recordingURL = url
    }

    public func stopAndTranscribe() async throws -> String {
        guard let recorder, let recordingURL else {
            throw VoiceTranscriptionError.notRecording
        }

        recorder.stop()
        self.recorder = nil
        self.recordingURL = nil

        defer {
            try? fileManager.removeItem(at: recordingURL)
            try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        }

        guard let recognizer = SFSpeechRecognizer(locale: locale), recognizer.isAvailable else {
            throw VoiceTranscriptionError.recognizerUnavailable
        }
        guard recognizer.supportsOnDeviceRecognition else {
            throw VoiceTranscriptionError.recognizerUnavailable
        }

        let request = SFSpeechURLRecognitionRequest(url: recordingURL)
        request.shouldReportPartialResults = false
        request.requiresOnDeviceRecognition = true

        let transcript = try await recognize(request: request, recognizer: recognizer)

        let trimmed = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.isEmpty == false else {
            throw VoiceTranscriptionError.emptyTranscript
        }
        return trimmed
    }

    public func cancelRecording() async {
        recorder?.stop()
        recorder = nil
        recognitionTask?.cancel()
        recognitionTask = nil
        if let recordingURL {
            try? fileManager.removeItem(at: recordingURL)
        }
        recordingURL = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    private func requestPermissions() async throws {
        let micGranted = await withCheckedContinuation { continuation in
            AVAudioSession.sharedInstance().requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }
        guard micGranted else {
            throw VoiceTranscriptionError.microphoneDenied
        }

        let speechStatus = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status)
            }
        }
        guard speechStatus == .authorized else {
            throw VoiceTranscriptionError.speechDenied
        }
    }

    private func recognize(
        request: SFSpeechURLRecognitionRequest,
        recognizer: SFSpeechRecognizer
    ) async throws -> String {
        try await withTaskCancellationHandler {
            try await recognizeUntilFinal(request: request, recognizer: recognizer)
        } onCancel: {
            Task {
                cancelRecognitionTask()
            }
        }
    }

    private func recognizeUntilFinal(
        request: SFSpeechURLRecognitionRequest,
        recognizer: SFSpeechRecognizer
    ) async throws -> String {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<String, Error>) in
            let box = RecognitionContinuationBox(continuation)
            let timeoutNanoseconds = min(transcriptionTimeoutNanoseconds, UInt64(Int.max))
            let timeout = DispatchWorkItem { [weak self] in
                self?.cancelRecognitionTask()
                _ = box.resume(.failure(VoiceTranscriptionError.transcriptionTimedOut))
            }

            recognitionTask = recognizer.recognitionTask(with: request) { [weak self] result, error in
                if let error {
                    timeout.cancel()
                    self?.cancelRecognitionTask()
                    _ = box.resume(.failure(error))
                    return
                }
                guard let result, result.isFinal else {
                    return
                }
                timeout.cancel()
                self?.cancelRecognitionTask()
                _ = box.resume(.success(result.bestTranscription.formattedString))
            }
            DispatchQueue.global().asyncAfter(
                deadline: .now() + .nanoseconds(Int(timeoutNanoseconds)),
                execute: timeout
            )
        }
    }

    private func cancelRecognitionTask() {
        recognitionTask?.cancel()
        recognitionTask = nil
    }
}

private final class RecognitionContinuationBox: @unchecked Sendable {
    private let lock = NSLock()
    private var continuation: CheckedContinuation<String, Error>?

    init(_ continuation: CheckedContinuation<String, Error>) {
        self.continuation = continuation
    }

    func resume(_ result: Result<String, Error>) -> Bool {
        lock.lock()
        defer {
            lock.unlock()
        }

        guard let continuation else {
            return false
        }
        self.continuation = nil

        switch result {
        case .success(let transcript):
            continuation.resume(returning: transcript)
        case .failure(let error):
            continuation.resume(throwing: error)
        }
        return true
    }
}

public enum VoiceTranscriberFactory {
    public static func makeDefault() -> (any VoiceRecordingTranscribing)? {
        SystemVoiceTranscriber()
    }
}
#else
public enum VoiceTranscriberFactory {
    public static func makeDefault() -> (any VoiceRecordingTranscribing)? {
        nil
    }
}
#endif
