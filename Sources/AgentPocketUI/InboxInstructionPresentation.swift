import AgentPocketCore
import Foundation

public enum InboxInstructionTemplate: String, CaseIterable, Identifiable, Sendable {
    case summarize
    case extractActions
    case translate
    case askFollowUp

    public var id: String {
        switch self {
        case .summarize:
            return "summarize"
        case .extractActions:
            return "extract_actions"
        case .translate:
            return "translate"
        case .askFollowUp:
            return "ask_follow_up"
        }
    }

    public func presentation(language: AppLanguage) -> InboxInstructionTemplatePresentation {
        switch (self, language) {
        case (.summarize, .english):
            return InboxInstructionTemplatePresentation(template: self, title: "Summarize", systemImage: "text.alignleft", instructionText: instructionText(language: language))
        case (.extractActions, .english):
            return InboxInstructionTemplatePresentation(template: self, title: "Extract Actions", systemImage: "checklist", instructionText: instructionText(language: language))
        case (.translate, .english):
            return InboxInstructionTemplatePresentation(template: self, title: "Translate", systemImage: "character.book.closed", instructionText: instructionText(language: language))
        case (.askFollowUp, .english):
            return InboxInstructionTemplatePresentation(template: self, title: "Ask Follow-up", systemImage: "questionmark.bubble", instructionText: instructionText(language: language))
        case (.summarize, .chinese):
            return InboxInstructionTemplatePresentation(template: self, title: "总结", systemImage: "text.alignleft", instructionText: instructionText(language: language))
        case (.extractActions, .chinese):
            return InboxInstructionTemplatePresentation(template: self, title: "提取行动项", systemImage: "checklist", instructionText: instructionText(language: language))
        case (.translate, .chinese):
            return InboxInstructionTemplatePresentation(template: self, title: "翻译", systemImage: "character.book.closed", instructionText: instructionText(language: language))
        case (.askFollowUp, .chinese):
            return InboxInstructionTemplatePresentation(template: self, title: "追问", systemImage: "questionmark.bubble", instructionText: instructionText(language: language))
        }
    }

    public func instructionText(language: AppLanguage) -> String {
        switch (self, language) {
        case (.summarize, .english):
            return "Summarize this item and highlight the key points."
        case (.extractActions, .english):
            return "Extract action items, owners, and dates from this item."
        case (.translate, .english):
            return "Translate the key points into my current language."
        case (.askFollowUp, .english):
            return "Identify unanswered questions and suggest follow-up prompts."
        case (.summarize, .chinese):
            return "总结这个项目并突出关键要点。"
        case (.extractActions, .chinese):
            return "提取行动项、负责人和日期。"
        case (.translate, .chinese):
            return "把关键内容翻译成我当前使用的语言。"
        case (.askFollowUp, .chinese):
            return "找出未回答的问题，并建议后续追问。"
        }
    }
}

public struct InboxInstructionTemplatePresentation: Equatable, Identifiable, Sendable {
    public let template: InboxInstructionTemplate
    public let title: String
    public let systemImage: String
    public let instructionText: String

    public var id: String { template.id }
}

public struct InboxInstructionPresentation: Equatable, Sendable {
    public let isInstructionAvailable: Bool
    public let hasInstruction: Bool
    public let noteTitle: String?
    public let noteText: String?
    public let voiceActionTitle: String?
    public let clearActionTitle: String?
    public let submitPreviewText: String?
    public let templates: [InboxInstructionTemplatePresentation]

    public init(item: KakaInboxItem, language: AppLanguage) {
        isInstructionAvailable = item.route == .universalIntake
        let trimmedNote = item.note?.trimmingCharacters(in: .whitespacesAndNewlines)
        let visibleNote = trimmedNote?.isEmpty == false ? trimmedNote : nil
        hasInstruction = isInstructionAvailable && visibleNote != nil
        noteText = hasInstruction ? visibleNote : nil

        guard isInstructionAvailable else {
            noteTitle = nil
            voiceActionTitle = nil
            clearActionTitle = nil
            submitPreviewText = nil
            templates = []
            return
        }

        templates = InboxInstructionTemplate.allCases.map { $0.presentation(language: language) }

        switch language {
        case .chinese:
            noteTitle = hasInstruction ? "指令" : nil
            voiceActionTitle = hasInstruction ? "编辑指令" : "语音指令"
            clearActionTitle = hasInstruction ? "清除指令" : nil
            submitPreviewText = hasInstruction ? "发送时会附带这条指令。" : nil
        case .english:
            noteTitle = hasInstruction ? "Instruction" : nil
            voiceActionTitle = hasInstruction ? "Edit Instruction" : "Voice Instruction"
            clearActionTitle = hasInstruction ? "Clear Instruction" : nil
            submitPreviewText = hasInstruction ? "Send will include this instruction." : nil
        }
    }
}
