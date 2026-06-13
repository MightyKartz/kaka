import SwiftUI

public struct LocalAgentLensView: View {
    public let presentation: LocalAgentLensPresentation
    public let onSelect: (String) -> Void

    public init(
        presentation: LocalAgentLensPresentation,
        onSelect: @escaping (String) -> Void
    ) {
        self.presentation = presentation
        self.onSelect = onSelect
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            connectionPill

            LazyVGrid(
                columns: [
                    GridItem(.flexible(minimum: 132), spacing: 10),
                    GridItem(.flexible(minimum: 132), spacing: 10)
                ],
                spacing: 10
            ) {
                ForEach(presentation.actions) { action in
                    Button {
                        onSelect(action.id)
                    } label: {
                        LocalAgentLensActionTile(action: action)
                    }
                    .buttonStyle(.plain)
                    .disabled(action.isEnabled == false)
                    .accessibilityIdentifier("localAgentLensAction-\(action.id)")
                }
            }
        }
        .padding(12)
        .background(AgentPocketDesignTokens.darkPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous)
                .stroke(AgentPocketDesignTokens.darkStroke, lineWidth: 1)
        )
    }

    private var connectionPill: some View {
        HStack(spacing: 10) {
            Circle()
                .fill(AgentPocketDesignTokens.statusSuccess)
                .frame(width: 9, height: 9)
                .shadow(color: AgentPocketDesignTokens.statusSuccess.opacity(0.45), radius: 8)
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 2) {
                Text(presentation.connectionTitle)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.95))
                    .lineLimit(1)
                    .minimumScaleFactor(0.82)

                Text(presentation.connectionHint)
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.62))
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 6)

            Image(systemName: "wifi")
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(AgentPocketDesignTokens.accent)
                .frame(width: 32, height: 32)
                .background(AgentPocketDesignTokens.darkSecondaryFill, in: Circle())
                .accessibilityHidden(true)
        }
        .padding(12)
        .background(AgentPocketDesignTokens.darkSecondaryFill, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
    }
}

private struct LocalAgentLensActionTile: View {
    let action: LocalAgentLensAction

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Image(systemName: action.systemImageName)
                .font(.system(size: 24, weight: .semibold))
                .foregroundStyle(AgentPocketDesignTokens.accent)
                .frame(width: 32, height: 32)

            VStack(alignment: .leading, spacing: 3) {
                Text(action.title)
                    .font(.callout.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.94))
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)

                Text(action.subtitle)
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.58))
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, minHeight: 106, alignment: .leading)
        .padding(12)
        .background(
            LinearGradient(
                colors: [
                    Color.white.opacity(0.10),
                    Color.white.opacity(0.06)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
        )
        .overlay(
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                .stroke(Color.white.opacity(0.08), lineWidth: 1)
        )
    }
}
