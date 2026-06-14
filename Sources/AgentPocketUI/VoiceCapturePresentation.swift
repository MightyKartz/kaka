import AgentPocketCore
import Foundation

public struct VoiceCapturePresentation: Equatable, Sendable {
    public let navigationTitle: String
    public let transcriptAccessibilityLabel: String
    public let submitTitle: String
    public let submitSystemImage: String
    public let language: AppLanguage
    public let prefersDarkNavigationChrome: Bool

    public init(
        navigationTitle: String,
        transcriptAccessibilityLabel: String,
        submitTitle: String,
        submitSystemImage: String,
        language: AppLanguage = .english,
        prefersDarkNavigationChrome: Bool = true
    ) {
        self.navigationTitle = navigationTitle
        self.transcriptAccessibilityLabel = transcriptAccessibilityLabel
        self.submitTitle = submitTitle
        self.submitSystemImage = submitSystemImage
        self.language = language
        self.prefersDarkNavigationChrome = prefersDarkNavigationChrome
    }

    public static let defaultDraft = VoiceCapturePresentation(
        navigationTitle: "Voice Draft",
        transcriptAccessibilityLabel: "Voice transcript",
        submitTitle: "Send",
        submitSystemImage: "paperplane.fill"
    )

    public static func inboxDraft(language: AppLanguage) -> VoiceCapturePresentation {
        switch language {
        case .chinese:
            return VoiceCapturePresentation(
                navigationTitle: "语音草稿",
                transcriptAccessibilityLabel: "语音草稿转写",
                submitTitle: "保存草稿",
                submitSystemImage: "tray.and.arrow.down.fill",
                language: .chinese
            )
        case .english:
            return VoiceCapturePresentation(
                navigationTitle: "Voice Draft",
                transcriptAccessibilityLabel: "Voice draft transcript",
                submitTitle: "Save Draft",
                submitSystemImage: "tray.and.arrow.down.fill",
                language: .english
            )
        }
    }

    public static func inboxInstruction(
        hasExistingInstruction: Bool,
        language: AppLanguage
    ) -> VoiceCapturePresentation {
        switch language {
        case .chinese:
            return VoiceCapturePresentation(
                navigationTitle: hasExistingInstruction ? "编辑指令" : "语音指令",
                transcriptAccessibilityLabel: "语音指令转写",
                submitTitle: "保存指令",
                submitSystemImage: "checkmark.circle.fill",
                language: .chinese
            )
        case .english:
            return VoiceCapturePresentation(
                navigationTitle: hasExistingInstruction ? "Edit Instruction" : "Voice Instruction",
                transcriptAccessibilityLabel: "Voice instruction transcript",
                submitTitle: "Save Instruction",
                submitSystemImage: "checkmark.circle.fill",
                language: .english
            )
        }
    }
}
