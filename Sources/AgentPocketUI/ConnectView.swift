import Foundation
import SwiftUI
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

public struct ConnectView: View {
    @ObservedObject private var viewModel: ConnectionViewModel
    @Environment(\.openURL) private var openURL
    @AppStorage("kaka.interfaceLanguage") private var languageRawValue = AppLanguage.chinese.rawValue
    @State private var showsManualEntry = false
    @State private var showsProjectSettings = false

    public init(viewModel: ConnectionViewModel = ConnectionViewModel()) {
        self.viewModel = viewModel
    }

    public var body: some View {
        let language = activeLanguage
        let copy = ConnectScreenCopy(
            state: viewModel.state,
            language: language,
            fallbackDeviceName: fallbackDeviceName(for: language)
        )
        let presentation = viewModel.state.presentation
        let isShowingDiscoveredRuntimes = viewModel.state == .idle && viewModel.discoveredRuntimes.isEmpty == false

        ScrollView {
            VStack(spacing: 12) {
                ConnectHeroCard(
                    copy: copy,
                    onlineTrustedTitle: heroOnlineTrustedTitle(
                        copy: copy,
                        language: language,
                        isShowingDiscoveredRuntimes: isShowingDiscoveredRuntimes
                    ),
                    trustBadgeTitles: heroTrustBadgeTitles(
                        copy: copy,
                        language: language,
                        isShowingDiscoveredRuntimes: isShowingDiscoveredRuntimes
                    ),
                    primaryButtonTitle: heroPrimaryButtonTitle(
                        copy: copy,
                        language: language,
                        isShowingDiscoveredRuntimes: isShowingDiscoveredRuntimes
                    ),
                    isBusy: presentation.isBusy,
                    primarySystemImage: primarySymbol(
                        for: viewModel.state,
                        isShowingDiscoveredRuntimes: isShowingDiscoveredRuntimes
                    ),
                    primaryAction: performPrimaryAction,
                    scanCodeAction: beginScanningFromHero
                )

                if presentation.isBusy && viewModel.state != .scanning {
                    ProgressView()
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .accessibilityLabel(copy.primaryButtonTitle)
                }

                if viewModel.state == .scanning {
                    PairingScannerCard(copy: copy) { pairingCode in
                        Task { @MainActor in
                            let deviceName = PairingDeviceInfo.name
                            let devicePublicID = PairingDeviceInfo.publicID
                            await viewModel.connectWithPairingPayload(
                                pairingCode,
                                deviceName: deviceName,
                                devicePublicID: devicePublicID
                            )
                        }
                    } manualAction: {
                        withAnimation(.easeOut(duration: 0.2)) {
                            showsManualEntry = true
                        }
                        viewModel.cancelScanning()
                    }
                }

                if viewModel.discoveredRuntimes.isEmpty == false {
                    DiscoveredRuntimeSection(viewModel: viewModel, copy: copy)
                }

                if presentation.showsManualEntry || showsManualEntry {
                    ManualEndpointSection(viewModel: viewModel, copy: copy)
                } else {
                    Button(copy.enterManuallyTitle) {
                        withAnimation(.easeOut(duration: 0.2)) {
                            showsManualEntry = true
                        }
                    }
                    .buttonStyle(.plain)
                    .font(.callout.weight(.medium))
                    .foregroundStyle(.secondary)
                    .frame(minHeight: 44)
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 12)
            .frame(maxWidth: 520)
        }
        .background(ConnectScreenBackground().ignoresSafeArea())
        .toolbar {
            Button {
                showsProjectSettings = true
            } label: {
                Image(systemName: "gearshape.fill")
            }
            .accessibilityLabel(copy.settingsTitle)
        }
        .sheet(isPresented: $showsProjectSettings) {
            ProjectSettingsSheet(language: languageBinding, copy: copy)
        }
        .navigationTitle("")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
    }

    private var activeLanguage: AppLanguage {
        AppLanguage(rawValue: languageRawValue) ?? .chinese
    }

    private var languageBinding: Binding<AppLanguage> {
        Binding {
            activeLanguage
        } set: { newValue in
            languageRawValue = newValue.rawValue
        }
    }

    private func fallbackDeviceName(for language: AppLanguage) -> String {
        switch language {
        case .chinese:
            return "我的电脑"
        case .english:
            return "Local Mac"
        }
    }

    private func heroOnlineTrustedTitle(
        copy: ConnectScreenCopy,
        language: AppLanguage,
        isShowingDiscoveredRuntimes: Bool
    ) -> String {
        guard isShowingDiscoveredRuntimes else {
            return copy.onlineTrustedTitle
        }

        switch language {
        case .chinese:
            return "已发现 · 待确认"
        case .english:
            return "Found · Confirm"
        }
    }

    private func heroTrustBadgeTitles(
        copy: ConnectScreenCopy,
        language: AppLanguage,
        isShowingDiscoveredRuntimes: Bool
    ) -> [String] {
        guard isShowingDiscoveredRuntimes else {
            return copy.trustBadgeTitles
        }

        switch language {
        case .chinese:
            return ["本地网络", "待确认"]
        case .english:
            return ["Local Network", "Confirm"]
        }
    }

    private func heroPrimaryButtonTitle(
        copy: ConnectScreenCopy,
        language: AppLanguage,
        isShowingDiscoveredRuntimes: Bool
    ) -> String {
        guard isShowingDiscoveredRuntimes else {
            return copy.primaryButtonTitle
        }

        switch language {
        case .chinese:
            return "重新搜索"
        case .english:
            return "Search Again"
        }
    }

    private func beginScanningFromHero() {
        if viewModel.state == .scanning {
            withAnimation(.easeOut(duration: 0.2)) {
                showsManualEntry = true
            }
            viewModel.cancelScanning()
        } else {
            viewModel.beginScanning()
        }
    }

    private func performPrimaryAction() {
        if let destination = viewModel.state.presentation.primaryRecoveryDestination {
            openRecoveryDestination(destination)
            return
        }

        switch viewModel.state {
        case .testing, .scanning, .discovering:
            break
        case .idle, .offline:
            Task {
                await viewModel.discoverLocalRuntimes(
                    autoPairSingleRuntime: false,
                    deviceName: PairingDeviceInfo.name,
                    devicePublicID: PairingDeviceInfo.publicID
                )
            }
        default:
            viewModel.beginScanning()
        }
    }

    private func performSecondaryAction() {
        switch viewModel.state {
        case .idle, .missingPhotoEdit:
            Task {
                await viewModel.discoverLocalRuntimes(
                    deviceName: PairingDeviceInfo.name,
                    devicePublicID: PairingDeviceInfo.publicID
                )
            }
        case .offline:
            viewModel.beginScanning()
        case .unauthorized, .invalidCertificate, .failed:
            withAnimation(.easeOut(duration: 0.2)) {
                showsManualEntry = true
            }
        case .localNetworkPermissionRequired:
            withAnimation(.easeOut(duration: 0.2)) {
                showsManualEntry = true
            }
        case .scanning:
            withAnimation(.easeOut(duration: 0.2)) {
                showsManualEntry = true
            }
            viewModel.cancelScanning()
        case .testing, .discovering, .connected:
            break
        }
    }

    private func primarySymbol(for state: ConnectionState, isShowingDiscoveredRuntimes: Bool) -> String {
        if isShowingDiscoveredRuntimes {
            return "arrow.clockwise"
        }

        switch state {
        case .connected:
            return "camera.viewfinder"
        case .idle:
            return "dot.radiowaves.left.and.right"
        case .testing:
            return "antenna.radiowaves.left.and.right"
        case .discovering:
            return "dot.radiowaves.left.and.right"
        case .offline:
            return "arrow.clockwise"
        case .missingPhotoEdit:
            return "book.pages"
        case .localNetworkPermissionRequired:
            return "gearshape"
        default:
            return "qrcode.viewfinder"
        }
    }

    private func secondarySymbol(for state: ConnectionState) -> String {
        switch state {
        case .idle:
            return "dot.radiowaves.left.and.right"
        case .offline:
            return "qrcode.viewfinder"
        case .unauthorized, .invalidCertificate, .failed:
            return "keyboard"
        case .localNetworkPermissionRequired:
            return "keyboard"
        case .missingPhotoEdit:
            return "arrow.clockwise"
        default:
            return "ellipsis"
        }
    }

    private func openRecoveryDestination(_ destination: ConnectionRecoveryDestination) {
        switch destination {
        case .appSettings:
            #if os(iOS)
            if let settingsURL = URL(string: UIApplication.openSettingsURLString) {
                openURL(settingsURL)
            }
            #endif
        }
    }
}

private struct ConnectScreenBackground: View {
    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.98, green: 0.99, blue: 0.99),
                    Color(red: 0.92, green: 0.95, blue: 0.96),
                    Color(red: 0.80, green: 0.86, blue: 0.88)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            Circle()
                .fill(Color.white.opacity(0.72))
                .frame(width: 280, height: 280)
                .blur(radius: 72)
                .offset(y: -220)

            Circle()
                .fill(Color(red: 0.56, green: 0.93, blue: 0.89).opacity(0.18))
                .frame(width: 320, height: 320)
                .blur(radius: 86)
                .offset(x: 120, y: -40)
        }
    }
}

private struct ConnectHeroCard: View {
    let copy: ConnectScreenCopy
    let onlineTrustedTitle: String
    let trustBadgeTitles: [String]
    let primaryButtonTitle: String
    let isBusy: Bool
    let primarySystemImage: String
    let primaryAction: () -> Void
    let scanCodeAction: () -> Void

    var body: some View {
        VStack(spacing: 14) {
            VStack(spacing: 6) {
                Text(copy.connectTitle)
                    .font(.title2.weight(.bold))
                    .foregroundStyle(Color(red: 0.06, green: 0.10, blue: 0.11))
                    .multilineTextAlignment(.center)
                    .accessibilityAddTraits(.isHeader)

                Text(copy.connectSubtitle)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .lineLimit(3)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(.top, 2)

            VStack(spacing: 12) {
                Image(systemName: "desktopcomputer")
                    .font(.system(size: 40, weight: .semibold))
                    .foregroundStyle(Color(red: 0.09, green: 0.15, blue: 0.16))
                    .frame(height: 48)
                    .accessibilityHidden(true)

                VStack(spacing: 8) {
                    Text(copy.deviceName)
                        .font(.title3.weight(.bold))
                        .foregroundStyle(.primary)
                        .lineLimit(1)
                        .minimumScaleFactor(0.82)

                    HStack(spacing: 7) {
                        Circle()
                            .fill(Color(red: 0.11, green: 0.78, blue: 0.53))
                            .frame(width: 8, height: 8)
                            .shadow(color: Color(red: 0.11, green: 0.78, blue: 0.53).opacity(0.24), radius: 5)

                        Text(onlineTrustedTitle)
                            .font(.footnote.weight(.semibold))
                            .foregroundStyle(Color(red: 0.06, green: 0.45, blue: 0.38))
                    }

                    TrustBadgeRow(labels: trustBadgeTitles)
                }

                Button(action: primaryAction) {
                    Label(primaryButtonTitle, systemImage: primarySystemImage)
                        .labelStyle(.titleAndIcon)
                        .font(.headline.weight(.bold))
                        .frame(maxWidth: .infinity, minHeight: 52)
                }
                .buttonStyle(MintProminentButtonStyle())
                .disabled(isBusy)
                .accessibilityIdentifier("connectLocalAgentButton")
            }
            .padding(18)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 28, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 28, style: .continuous)
                    .stroke(Color.white.opacity(0.66), lineWidth: 1)
            }
            .shadow(color: Color(red: 0.13, green: 0.20, blue: 0.22).opacity(0.12), radius: 28, y: 18)

            Button(action: scanCodeAction) {
                Text(copy.scanCodeTitle)
                    .font(.body.weight(.semibold))
                    .frame(maxWidth: .infinity, minHeight: 44)
            }
            .buttonStyle(.plain)
            .foregroundStyle(Color(red: 0.13, green: 0.20, blue: 0.21))
            .disabled(isBusy)

            HStack(alignment: .firstTextBaseline, spacing: 7) {
                Image(systemName: "lock.fill")
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(.secondary)

                Text(copy.privacyLine)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
            }
            .frame(maxWidth: .infinity)
            .padding(.bottom, 4)
        }
        .padding(.horizontal, 22)
        .padding(.vertical, 16)
    }
}

private struct PairingScannerCard: View {
    let copy: ConnectScreenCopy
    let onPairingCode: (String) -> Void
    let manualAction: () -> Void

    var body: some View {
        VStack(spacing: 14) {
            PairingScannerView(onCodeScanned: onPairingCode)

            Button(action: manualAction) {
                Label(copy.enterManuallyTitle, systemImage: "keyboard")
                    .frame(maxWidth: .infinity, minHeight: 48)
            }
            .buttonStyle(.bordered)
        }
        .padding(16)
        .background(AgentPocketColors.surfaceBackground, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .shadow(color: .black.opacity(0.06), radius: 18, y: 8)
    }
}

private struct ProjectSettingsSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Binding var language: AppLanguage
    let copy: ConnectScreenCopy

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    SettingsCard {
                        VStack(alignment: .leading, spacing: 12) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(copy.languageTitle)
                                    .font(.headline)

                                Text(copy.languageDescription)
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
                            }

                            Picker(copy.languageTitle, selection: $language) {
                                ForEach(AppLanguage.allCases) { option in
                                    Text(option.displayTitle).tag(option)
                                }
                            }
                            .pickerStyle(.segmented)
                        }
                    }

                    SettingsCard {
                        VStack(spacing: 0) {
                            SettingsRow(title: copy.runtimeTitle, detail: copy.runtimeDescription, value: copy.runtimeValue)
                            SettingsDivider()
                            SettingsRow(title: copy.privacyTitle, detail: copy.privacyDescription, value: copy.privacyValue)
                            SettingsDivider()
                            SettingsRow(title: copy.defaultSceneTitle, detail: copy.defaultSceneDescription, value: copy.defaultSceneValue)
                        }
                    }
                }
                .padding(20)
            }
            .background(ConnectScreenBackground().ignoresSafeArea())
            .navigationTitle(copy.settingsTitle)
            .toolbar {
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                }
                .accessibilityLabel("Close")
            }
        }
    }
}

private struct SettingsCard<Content: View>: View {
    @ViewBuilder let content: Content

    var body: some View {
        content
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(Color.white.opacity(0.68), lineWidth: 1)
            }
    }
}

private struct SettingsRow: View {
    let title: String
    let detail: String
    let value: String

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(.primary)

                Text(detail)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 8)

            Text(value)
                .font(.caption.weight(.bold))
                .foregroundStyle(Color(red: 0.05, green: 0.31, blue: 0.27))
                .padding(.horizontal, 10)
                .frame(minHeight: 30)
                .background(Color(red: 0.56, green: 0.93, blue: 0.89).opacity(0.46), in: Capsule())
        }
        .padding(.vertical, 8)
    }
}

private struct SettingsDivider: View {
    var body: some View {
        Rectangle()
            .fill(Color.primary.opacity(0.10))
            .frame(height: 1)
    }
}

private struct MintProminentButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(Color(red: 0.03, green: 0.15, blue: 0.13))
            .background(
                LinearGradient(
                    colors: [
                        Color(red: 0.72, green: 1.0, blue: 0.96),
                        Color(red: 0.56, green: 0.93, blue: 0.89)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                ),
                in: RoundedRectangle(cornerRadius: 18, style: .continuous)
            )
            .shadow(color: Color(red: 0.14, green: 0.72, blue: 0.67).opacity(configuration.isPressed ? 0.10 : 0.22), radius: 18, y: 10)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
    }
}

private struct TrustBadgeRow: View {
    let labels: [String]

    var body: some View {
        HStack(spacing: 8) {
            ForEach(labels, id: \.self) { label in
                Text(label)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 10)
                    .frame(minHeight: 30)
                    .background(AgentPocketColors.secondaryGroupedBackground, in: Capsule())
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(labels.joined(separator: ", "))
    }
}

@MainActor
private enum PairingDeviceInfo {
    static var name: String {
        #if os(iOS)
        UIDevice.current.name
        #elseif canImport(AppKit)
        Host.current().localizedName ?? "Agent Pocket Mac"
        #else
        "Agent Pocket"
        #endif
    }

    static var publicID: String {
        #if os(iOS)
        UIDevice.current.identifierForVendor?.uuidString ?? "agent-pocket-ios-device"
        #else
        name
            .lowercased()
            .replacingOccurrences(of: " ", with: "-")
        #endif
    }
}

private struct RuntimeMark: View {
    let state: ConnectionState

    var body: some View {
        ZStack {
            Circle()
                .fill(fill)
                .frame(width: 58, height: 58)

            Image(systemName: symbol)
                .font(.system(size: 24, weight: .semibold))
                .foregroundStyle(.white)
        }
        .accessibilityHidden(true)
    }

    private var fill: Color {
        switch state {
        case .connected:
            return Color.green
        case .unauthorized, .invalidCertificate, .missingPhotoEdit, .localNetworkPermissionRequired, .failed:
            return Color.red
        case .testing, .scanning, .discovering:
            return Color.blue
        default:
            return Color.black
        }
    }

    private var symbol: String {
        switch state {
        case .connected:
            return "checkmark"
        case .unauthorized, .invalidCertificate, .missingPhotoEdit, .localNetworkPermissionRequired, .failed:
            return "exclamationmark"
        default:
            return "iphone.radiowaves.left.and.right"
        }
    }
}

private struct ManualEndpointSection: View {
    @ObservedObject var viewModel: ConnectionViewModel
    let copy: ConnectScreenCopy

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(copy.manualTitle)
                .font(.title3.weight(.bold))
                .foregroundStyle(Color(red: 0.06, green: 0.10, blue: 0.11))

            VStack(spacing: 10) {
                ManualTextFieldShell(systemImage: "network") {
                    TextField(copy.endpointPlaceholder, text: $viewModel.endpointText)
                        .agentURLInputTraits()
                        .accessibilityLabel("Local agent endpoint")
                }

                ManualTextFieldShell(systemImage: "key.horizontal") {
                    SecureField(copy.tokenPlaceholder, text: $viewModel.tokenText)
                        .agentTokenInputTraits()
                        .accessibilityLabel("Mobile token")
                }
            }

            Button {
                Task {
                    await viewModel.connectManually()
                }
            } label: {
                Label(copy.testConnectionTitle, systemImage: "checkmark.shield")
                    .labelStyle(.titleAndIcon)
                    .font(.headline.weight(.bold))
                    .frame(maxWidth: .infinity, minHeight: 52)
            }
            .buttonStyle(MintProminentButtonStyle())
            .disabled(viewModel.state.presentation.isBusy)
        }
        .padding(18)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 28, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .stroke(Color.white.opacity(0.66), lineWidth: 1)
        }
        .shadow(color: Color(red: 0.13, green: 0.20, blue: 0.22).opacity(0.10), radius: 24, y: 14)
    }
}

private struct ManualTextFieldShell<Content: View>: View {
    let systemImage: String
    @ViewBuilder let content: Content

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: systemImage)
                .font(.callout.weight(.semibold))
                .foregroundStyle(Color(red: 0.08, green: 0.46, blue: 0.40).opacity(0.86))
                .frame(width: 22)
                .accessibilityHidden(true)

            content
                .font(.body.weight(.medium))
                .foregroundStyle(Color(red: 0.06, green: 0.10, blue: 0.11))
        }
        .padding(.horizontal, 14)
        .frame(minHeight: 48)
        .background(Color.white.opacity(0.58), in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(Color.white.opacity(0.78), lineWidth: 1)
        }
    }
}

private struct DiscoveredRuntimeSection: View {
    @ObservedObject var viewModel: ConnectionViewModel
    let copy: ConnectScreenCopy

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            VStack(alignment: .leading, spacing: 4) {
                Text(copy.nearbyRuntimeTitle)
                    .font(.title3.weight(.bold))
                    .foregroundStyle(Color(red: 0.06, green: 0.10, blue: 0.11))

                Text(copy.nearbyRuntimeDescription)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            ForEach(viewModel.discoveredRuntimes, id: \.id) { (runtime: DiscoveredRuntime) in
                Button {
                    Task { @MainActor in
                        let deviceName = PairingDeviceInfo.name
                        let devicePublicID = PairingDeviceInfo.publicID
                        await viewModel.connectDiscoveredRuntime(
                            runtime,
                            deviceName: deviceName,
                            devicePublicID: devicePublicID
                        )
                    }
                } label: {
                    HStack(spacing: 12) {
                        ZStack {
                            Circle()
                                .fill(Color.white.opacity(0.62))
                                .frame(width: 44, height: 44)

                            Image(systemName: "macbook.and.iphone")
                                .font(.title3.weight(.semibold))
                                .foregroundStyle(Color(red: 0.07, green: 0.45, blue: 0.39))
                        }

                        VStack(alignment: .leading, spacing: 3) {
                            Text(runtime.displayName)
                                .font(.body.weight(.semibold))
                                .foregroundStyle(Color(red: 0.06, green: 0.10, blue: 0.11))
                                .lineLimit(1)

                            HStack(spacing: 6) {
                                Circle()
                                    .fill(Color(red: 0.11, green: 0.78, blue: 0.53))
                                    .frame(width: 7, height: 7)

                                Text(endpointDetail(for: runtime))
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                        }

                        Spacer(minLength: 8)

                        Text(copy.connectRuntimeTitle)
                            .font(.caption.weight(.bold))
                            .foregroundStyle(Color(red: 0.03, green: 0.15, blue: 0.13))
                            .padding(.horizontal, 14)
                            .frame(minHeight: 34)
                            .background(
                                Color(red: 0.56, green: 0.93, blue: 0.89).opacity(0.82),
                                in: Capsule()
                            )
                    }
                    .padding(.horizontal, 14)
                    .frame(maxWidth: .infinity, minHeight: 68, alignment: .leading)
                    .background(Color.white.opacity(0.54), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
                    .overlay {
                        RoundedRectangle(cornerRadius: 20, style: .continuous)
                            .stroke(Color.white.opacity(0.76), lineWidth: 1)
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .disabled(viewModel.state.presentation.isBusy)
                .accessibilityElement(children: .ignore)
                .accessibilityLabel("\(runtime.displayName), \(endpointDetail(for: runtime))")
                .accessibilityHint(copy.nearbyRuntimeDescription)
                .accessibilityIdentifier("nearbyLocalAgentRuntimeCard")
            }
        }
        .padding(18)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 28, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .stroke(Color.white.opacity(0.66), lineWidth: 1)
        }
        .shadow(color: Color(red: 0.13, green: 0.20, blue: 0.22).opacity(0.10), radius: 24, y: 14)
        .accessibilityIdentifier("nearbyLocalAgentSection")
    }

    private func endpointDetail(for runtime: DiscoveredRuntime) -> String {
        let host = runtime.endpoint.baseURL.host ?? runtime.endpoint.displayName
        guard let runtimeName = runtime.endpoint.runtime.map(prettyRuntimeName) else {
            return host
        }

        if runtimeName.localizedCaseInsensitiveCompare(host) == .orderedSame {
            return host
        }
        return "\(runtimeName) · \(host)"
    }

    private func prettyRuntimeName(_ runtime: String) -> String {
        switch runtime.lowercased() {
        case "hermes":
            return "Hermes"
        case "openclaw":
            return "OpenClaw"
        default:
            return runtime
        }
    }
}

private enum AgentPocketColors {
    static var groupedBackground: Color {
        #if canImport(UIKit)
        Color(UIColor.systemGroupedBackground)
        #elseif canImport(AppKit)
        Color(NSColor.windowBackgroundColor)
        #else
        Color.gray.opacity(0.08)
        #endif
    }

    static var secondaryGroupedBackground: Color {
        #if canImport(UIKit)
        Color(UIColor.secondarySystemGroupedBackground)
        #elseif canImport(AppKit)
        Color(NSColor.controlBackgroundColor)
        #else
        Color.gray.opacity(0.12)
        #endif
    }

    static var surfaceBackground: Color {
        #if canImport(UIKit)
        Color(UIColor.systemBackground)
        #elseif canImport(AppKit)
        Color(NSColor.textBackgroundColor)
        #else
        Color.white
        #endif
    }
}

private extension View {
    @ViewBuilder
    func agentURLInputTraits() -> some View {
        #if os(iOS)
        self
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .keyboardType(.URL)
            .textContentType(.URL)
        #else
        self
        #endif
    }

    @ViewBuilder
    func agentTokenInputTraits() -> some View {
        #if os(iOS)
        self
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
        #else
        self
        #endif
    }
}
