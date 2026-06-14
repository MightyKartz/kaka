import SwiftUI

enum AgentPocketDesignTokens {
    static let accent = Color(red: 0.55, green: 0.96, blue: 0.89)
    static let accentStrong = Color(red: 0.32, green: 0.82, blue: 0.73)
    static let ink = Color(red: 0.05, green: 0.09, blue: 0.10)
    static let inkMuted = Color(red: 0.28, green: 0.36, blue: 0.38)
    static let statusSuccess = Color(red: 0.11, green: 0.78, blue: 0.53)
    static let statusBusy = Color(red: 0.25, green: 0.54, blue: 0.94)
    static let statusDanger = Color(red: 0.92, green: 0.27, blue: 0.22)
    static let statusNeutral = Color(red: 0.41, green: 0.48, blue: 0.50)
    static let lightSurface = Color.white.opacity(0.86)
    static let lightSurfaceSubtle = Color.white.opacity(0.66)
    static let lightStroke = Color.white.opacity(0.68)
    static let lightCanvas = Color(red: 0.975, green: 0.972, blue: 0.955)
    static let lightPanel = Color.white
    static let lightPanelSubtle = Color(red: 0.96, green: 0.965, blue: 0.955)
    static let lightBorder = Color.black.opacity(0.08)
    static let lightShadow = Color(red: 0.13, green: 0.20, blue: 0.22).opacity(0.10)
    static let darkBackground = Color(red: 0.045, green: 0.052, blue: 0.052)
    static let darkPanel = Color.black.opacity(0.26)
    static let darkPanelStrong = Color.black.opacity(0.42)
    static let darkStroke = Color.white.opacity(0.10)
    static let darkSecondaryFill = Color.white.opacity(0.08)

    static let controlRadius: CGFloat = 8
    static let panelRadius: CGFloat = 12
    static let mediaRadius: CGFloat = 8
}

enum AgentPocketDarkControlContrast {
    static let disabledPrimaryBackgroundOpacity = 0.66
    static let disabledPrimaryLabelOpacity = 0.76
}

struct AgentPocketDarkPrimaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(AgentPocketDesignTokens.ink.opacity(isEnabled ? 1.0 : AgentPocketDarkControlContrast.disabledPrimaryLabelOpacity))
            .background(
                AgentPocketDesignTokens.accent.opacity(isEnabled ? (configuration.isPressed ? 0.86 : 1.0) : AgentPocketDarkControlContrast.disabledPrimaryBackgroundOpacity),
                in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
            )
            .scaleEffect(configuration.isPressed && isEnabled ? 0.98 : 1.0)
            .animation(.easeOut(duration: 0.14), value: configuration.isPressed)
    }
}

struct AgentPocketDarkSecondaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(.white.opacity(isEnabled ? 0.86 : 0.42))
            .background(
                Color.white.opacity(configuration.isPressed && isEnabled ? 0.14 : 0.08),
                in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
            )
            .overlay {
                RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                    .stroke(Color.white.opacity(configuration.isPressed && isEnabled ? 0.18 : 0.08), lineWidth: 1)
            }
            .scaleEffect(configuration.isPressed && isEnabled ? 0.98 : 1.0)
            .animation(.easeOut(duration: 0.14), value: configuration.isPressed)
    }
}

struct AgentPocketDarkIconButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(.white.opacity(isEnabled ? 0.82 : 0.38))
            .background(
                Color.white.opacity(configuration.isPressed && isEnabled ? 0.14 : 0.0),
                in: Circle()
            )
            .scaleEffect(configuration.isPressed && isEnabled ? 0.94 : 1.0)
            .animation(.easeOut(duration: 0.14), value: configuration.isPressed)
    }
}

struct AgentPocketLightPrimaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(AgentPocketDesignTokens.ink)
            .background(
                AgentPocketDesignTokens.accent.opacity(isEnabled ? (configuration.isPressed ? 0.72 : 0.92) : 0.34),
                in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
            )
            .overlay {
                RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                    .stroke(AgentPocketDesignTokens.accentStrong.opacity(0.22), lineWidth: 1)
            }
            .scaleEffect(configuration.isPressed && isEnabled ? 0.98 : 1.0)
            .animation(.easeOut(duration: 0.14), value: configuration.isPressed)
    }
}

struct AgentPocketLightSecondaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(AgentPocketDesignTokens.ink.opacity(isEnabled ? 0.82 : 0.38))
            .background(
                AgentPocketDesignTokens.lightPanelSubtle.opacity(configuration.isPressed && isEnabled ? 1.0 : 0.78),
                in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
            )
            .overlay {
                RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                    .stroke(AgentPocketDesignTokens.lightBorder, lineWidth: 1)
            }
            .scaleEffect(configuration.isPressed && isEnabled ? 0.98 : 1.0)
            .animation(.easeOut(duration: 0.14), value: configuration.isPressed)
    }
}

struct AgentPocketLightIconButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(AgentPocketDesignTokens.ink.opacity(isEnabled ? 0.72 : 0.32))
            .background(
                AgentPocketDesignTokens.lightPanelSubtle.opacity(configuration.isPressed && isEnabled ? 1.0 : 0.0),
                in: Circle()
            )
            .scaleEffect(configuration.isPressed && isEnabled ? 0.94 : 1.0)
            .animation(.easeOut(duration: 0.14), value: configuration.isPressed)
    }
}
