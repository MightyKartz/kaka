import AgentPocketCore
import SwiftUI

public struct KakaSkillSuggestionView: View {
    public let suggestion: KakaSkillSuggestion
    public let action: () -> Void

    public init(suggestion: KakaSkillSuggestion, action: @escaping () -> Void) {
        self.suggestion = suggestion
        self.action = action
    }

    public var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Image(systemName: suggestion.skill.systemImage)
                    .font(.system(size: 15, weight: .semibold))
                    .frame(width: 24, height: 24)
                    .background(iconBackground, in: Circle())
                Text(suggestion.title)
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .foregroundStyle(foreground)
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(background, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(border, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel(suggestion.title)
        .accessibilityHint(suggestion.reason)
    }

    private var foreground: Color {
        suggestion.isAvailable ? .white : .white.opacity(0.42)
    }

    private var background: Color {
        suggestion.isAvailable ? Color.white.opacity(0.12) : Color.white.opacity(0.06)
    }

    private var border: Color {
        suggestion.isAvailable ? Color(red: 0.55, green: 0.96, blue: 0.89).opacity(0.36) : .white.opacity(0.08)
    }

    private var iconBackground: Color {
        suggestion.isAvailable ? Color(red: 0.55, green: 0.96, blue: 0.89).opacity(0.22) : .white.opacity(0.08)
    }
}

private extension KakaSkillID {
    var systemImage: String {
        switch self {
        case .photoEnhance:
            return "sparkles"
        case .ocr:
            return "doc.text.viewfinder"
        case .translateText:
            return "translate"
        case .identifySubject:
            return "viewfinder.circle"
        case .nutritionEstimate:
            return "fork.knife"
        }
    }
}
