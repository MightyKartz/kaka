import Foundation

public protocol VoiceReplySpeaking: Sendable {
    func speak(_ text: String) async
    func stop() async
}

#if canImport(AVFoundation)
import AVFoundation

public final class SystemVoiceReplySpeaker: NSObject, VoiceReplySpeaking, @unchecked Sendable {
    private let synthesizer = AVSpeechSynthesizer()

    public override init() {
        super.init()
    }

    public func speak(_ text: String) async {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.isEmpty == false else {
            return
        }

        await stop()

        let utterance = AVSpeechUtterance(string: trimmed)
        utterance.voice = AVSpeechSynthesisVoice(language: Locale.current.identifier)
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        synthesizer.speak(utterance)
    }

    public func stop() async {
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
    }
}

public enum VoiceReplySpeakerFactory {
    public static func makeDefault() -> any VoiceReplySpeaking {
        SystemVoiceReplySpeaker()
    }
}
#else
public struct SilentVoiceReplySpeaker: VoiceReplySpeaking {
    public init() {}
    public func speak(_ text: String) async {}
    public func stop() async {}
}

public enum VoiceReplySpeakerFactory {
    public static func makeDefault() -> any VoiceReplySpeaking {
        SilentVoiceReplySpeaker()
    }
}
#endif
