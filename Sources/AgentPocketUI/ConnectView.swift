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
        let recoveryPresentation = ConnectionReadinessPresenter.presentation(for: viewModel.state)
        let isShowingDiscoveredRuntimes = shouldShowDiscoveredRuntimes

        ScrollView {
            VStack(spacing: 12) {
                if isShowingDiscoveredRuntimes {
                    DiscoveryHeroActions(
                        copy: copy,
                        scanButtonTitle: language == .chinese ? "扫描配对码" : "Scan Pairing QR",
                        isBusy: presentation.isBusy,
                        scanAction: beginScanningFromHero
                    )
                } else {
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
                        statusColor: heroStatusColor(isShowingDiscoveredRuntimes: isShowingDiscoveredRuntimes),
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
                        secondaryButtonTitle: heroSecondaryButtonTitle(
                            copy: copy,
                            language: language,
                            isShowingDiscoveredRuntimes: isShowingDiscoveredRuntimes
                        ),
                        secondarySystemImage: heroSecondarySymbol(isShowingDiscoveredRuntimes: isShowingDiscoveredRuntimes),
                        secondaryAction: {
                            performHeroSecondaryAction(isShowingDiscoveredRuntimes: isShowingDiscoveredRuntimes)
                        }
                    )
                }

                if presentation.isBusy && viewModel.state != .scanning {
                    ProgressView()
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .accessibilityLabel(copy.primaryButtonTitle)
                }

                if let recoveryPresentation {
                    ConnectionRecoveryGuidancePanel(presentation: recoveryPresentation, language: language)
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

                if isShowingDiscoveredRuntimes {
                    DiscoveredRuntimeSection(viewModel: viewModel, copy: copy)
                }

                if presentation.showsManualEntry || showsManualEntry {
                    ManualEndpointSection(viewModel: viewModel, copy: copy)
                } else if shouldShowStandaloneManualEntry {
                    ManualFallbackButton(title: copy.enterManuallyTitle) {
                        withAnimation(.easeOut(duration: 0.2)) {
                            showsManualEntry = true
                        }
                    }
                }

                ConnectionPrivacyLine(copy: copy)
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
            ProjectSettingsSheet(copy: copy)
        }
        .onChange(of: viewModel.state) { _, newState in
            resetManualEntryIfNeeded(for: newState)
        }
        .navigationTitle("")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
    }

    private var activeLanguage: AppLanguage {
        AppLanguage.resolved(storedValue: nil)
    }

    private var shouldShowDiscoveredRuntimes: Bool {
        guard viewModel.discoveredRuntimes.isEmpty == false else {
            return false
        }

        switch viewModel.state {
        case .idle, .savedConnectionOffline:
            return true
        case .connected, .discovering, .testing, .restoringSavedConnection, .scanning, .offline, .unauthorized, .invalidCertificate, .missingPhotoEdit, .localNetworkPermissionRequired, .failed:
            return false
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
        guard isShowingDiscoveredRuntimes == false else {
            switch language {
            case .chinese:
                return "扫描配对码"
            case .english:
                return "Scan Pairing QR"
            }
        }

        return copy.primaryButtonTitle
    }

    private func heroSecondaryButtonTitle(
        copy: ConnectScreenCopy,
        language: AppLanguage,
        isShowingDiscoveredRuntimes: Bool
    ) -> String {
        guard isShowingDiscoveredRuntimes == false else {
            return copy.enterManuallyTitle
        }

        switch viewModel.state {
        case .unauthorized:
            return language == .chinese ? "输入令牌" : "Enter Token"
        case .invalidCertificate, .failed, .localNetworkPermissionRequired:
            return copy.enterManuallyTitle
        case .connected:
            return language == .chinese ? "更换本机智能体" : "Change Local Agent"
        case .missingPhotoEdit:
            return language == .chinese ? "重新检查" : "Check Again"
        case .idle:
            return language == .chinese ? "查找附近运行时" : "Find Nearby Runtime"
        case .savedConnectionOffline:
            return language == .chinese ? "重新扫码" : "Scan New QR"
        case .offline:
            return copy.scanCodeTitle
        case .scanning:
            return copy.enterManuallyTitle
        case .testing, .discovering, .restoringSavedConnection:
            return copy.primaryButtonTitle
        }
    }

    private func heroStatusColor(isShowingDiscoveredRuntimes: Bool) -> Color {
        if isShowingDiscoveredRuntimes {
            return AgentPocketDesignTokens.accentStrong
        }

        switch viewModel.state {
        case .connected:
            return AgentPocketDesignTokens.statusSuccess
        case .discovering, .testing, .scanning, .restoringSavedConnection:
            return AgentPocketDesignTokens.statusBusy
        case .unauthorized, .offline, .savedConnectionOffline, .invalidCertificate, .missingPhotoEdit, .localNetworkPermissionRequired, .failed:
            return AgentPocketDesignTokens.statusDanger
        case .idle:
            return AgentPocketDesignTokens.statusNeutral
        }
    }

    private var shouldShowStandaloneManualEntry: Bool {
        switch viewModel.state {
        case .idle, .offline, .savedConnectionOffline, .unauthorized, .invalidCertificate, .localNetworkPermissionRequired, .failed:
            return true
        case .connected, .discovering, .testing, .restoringSavedConnection, .scanning, .missingPhotoEdit:
            return false
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

    private func performHeroSecondaryAction(isShowingDiscoveredRuntimes: Bool) {
        guard isShowingDiscoveredRuntimes == false else {
            withAnimation(.easeOut(duration: 0.2)) {
                showsManualEntry = true
            }
            return
        }

        performSecondaryAction()
    }

    private func performPrimaryAction() {
        if let destination = viewModel.state.presentation.primaryRecoveryDestination {
            openRecoveryDestination(destination)
            return
        }

        switch viewModel.state {
        case .testing, .scanning, .discovering, .restoringSavedConnection:
            break
        case .idle:
            viewModel.beginScanning()
        case .savedConnectionOffline:
            Task {
                await viewModel.restoreSavedConnectionOrDiscoverNearby(
                    deviceName: PairingDeviceInfo.name,
                    devicePublicID: PairingDeviceInfo.publicID
                )
            }
        case .offline:
            if let runtime = viewModel.discoveredRuntimes.first {
                Task { @MainActor in
                    await viewModel.connectDiscoveredRuntime(
                        runtime,
                        deviceName: PairingDeviceInfo.name,
                        devicePublicID: PairingDeviceInfo.publicID
                    )
                }
                return
            }
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
        case .idle:
            Task {
                await viewModel.discoverLocalRuntimes(
                    autoPairSingleRuntime: false,
                    deviceName: PairingDeviceInfo.name,
                    devicePublicID: PairingDeviceInfo.publicID
                )
            }
        case .savedConnectionOffline:
            viewModel.beginScanning()
        case .offline:
            viewModel.beginScanning()
        case .missingPhotoEdit:
            Task {
                await viewModel.discoverLocalRuntimes(
                    deviceName: PairingDeviceInfo.name,
                    devicePublicID: PairingDeviceInfo.publicID
                )
            }
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
        case .connected:
            viewModel.forgetSavedConnection()
        case .testing, .discovering, .restoringSavedConnection:
            break
        }
    }

    private func resetManualEntryIfNeeded(for state: ConnectionState) {
        switch state {
        case .connected, .idle, .discovering, .testing, .restoringSavedConnection:
            showsManualEntry = false
        case .scanning, .unauthorized, .offline, .savedConnectionOffline, .invalidCertificate, .missingPhotoEdit, .localNetworkPermissionRequired, .failed:
            break
        }
    }

    private func primarySymbol(for state: ConnectionState, isShowingDiscoveredRuntimes: Bool) -> String {
        if isShowingDiscoveredRuntimes {
            return "qrcode.viewfinder"
        }

        switch state {
        case .connected:
            return "camera.viewfinder"
        case .idle:
            return "qrcode.viewfinder"
        case .testing:
            return "antenna.radiowaves.left.and.right"
        case .discovering, .restoringSavedConnection:
            return "dot.radiowaves.left.and.right"
        case .offline, .savedConnectionOffline:
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
        case .offline, .savedConnectionOffline:
            return "qrcode.viewfinder"
        case .unauthorized, .invalidCertificate, .failed:
            return "keyboard"
        case .localNetworkPermissionRequired:
            return "keyboard"
        case .missingPhotoEdit:
            return "arrow.clockwise"
        case .connected:
            return "arrow.triangle.2.circlepath"
        default:
            return "ellipsis"
        }
    }

    private func heroSecondarySymbol(isShowingDiscoveredRuntimes: Bool) -> String {
        isShowingDiscoveredRuntimes ? "keyboard" : secondarySymbol(for: viewModel.state)
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
                    Color(red: 0.94, green: 0.97, blue: 0.96),
                    Color(red: 0.85, green: 0.91, blue: 0.91),
                    Color(red: 0.73, green: 0.82, blue: 0.83)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            LinearGradient(
                colors: [
                    Color.white.opacity(0.44),
                    AgentPocketDesignTokens.accent.opacity(0.18),
                    Color.clear
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        }
    }
}

private struct DiscoveryHeroActions: View {
    let copy: ConnectScreenCopy
    let scanButtonTitle: String
    let isBusy: Bool
    let scanAction: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            VStack(alignment: .leading, spacing: 7) {
                Text(copy.appName)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    .textCase(.uppercase)

                Text(copy.connectTitle)
                    .font(.title2.weight(.bold))
                    .foregroundStyle(AgentPocketDesignTokens.ink)
                    .multilineTextAlignment(.leading)
                    .accessibilityAddTraits(.isHeader)

                Text(copy.connectSubtitle)
                    .font(.subheadline)
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Button(action: scanAction) {
                Label(scanButtonTitle, systemImage: "qrcode.viewfinder")
                    .labelStyle(.titleAndIcon)
                    .font(.headline.weight(.bold))
                    .frame(maxWidth: .infinity, minHeight: 56)
            }
            .buttonStyle(MintProminentButtonStyle())
            .disabled(isBusy)
            .accessibilityIdentifier("connectScanPairingCodeButton")
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 2)
        .padding(.top, 4)
        .padding(.bottom, 2)
    }
}

private struct ConnectHeroCard: View {
    let copy: ConnectScreenCopy
    let onlineTrustedTitle: String
    let trustBadgeTitles: [String]
    let statusColor: Color
    let primaryButtonTitle: String
    let isBusy: Bool
    let primarySystemImage: String
    let primaryAction: () -> Void
    let secondaryButtonTitle: String
    let secondarySystemImage: String
    let secondaryAction: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 7) {
                Text(copy.appName)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    .textCase(.uppercase)

                Text(copy.connectTitle)
                    .font(.title2.weight(.bold))
                    .foregroundStyle(AgentPocketDesignTokens.ink)
                    .multilineTextAlignment(.leading)
                    .accessibilityAddTraits(.isHeader)

                Text(copy.connectSubtitle)
                    .font(.subheadline)
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)
            }

            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .center, spacing: 12) {
                    ZStack {
                        RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                            .fill(AgentPocketDesignTokens.ink)
                            .frame(width: 52, height: 52)

                        Image(systemName: "desktopcomputer")
                            .font(.system(size: 24, weight: .semibold))
                            .foregroundStyle(.white)
                            .accessibilityHidden(true)
                    }

                    VStack(alignment: .leading, spacing: 5) {
                        Text(copy.deviceName)
                            .font(.headline.weight(.bold))
                            .foregroundStyle(AgentPocketDesignTokens.ink)
                            .lineLimit(1)
                            .minimumScaleFactor(0.82)

                        HStack(spacing: 7) {
                            Circle()
                                .fill(statusColor)
                                .frame(width: 8, height: 8)

                            Text(onlineTrustedTitle)
                                .font(.footnote.weight(.semibold))
                                .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                                .lineLimit(2)
                        }
                    }
                }

                TrustBadgeRow(labels: trustBadgeTitles)

                Button(action: primaryAction) {
                    Label(primaryButtonTitle, systemImage: primarySystemImage)
                        .labelStyle(.titleAndIcon)
                        .font(.headline.weight(.bold))
                        .frame(maxWidth: .infinity, minHeight: 52)
                }
                .buttonStyle(MintProminentButtonStyle())
                .disabled(isBusy)
                .accessibilityIdentifier("connectLocalAgentButton")

                Button(action: secondaryAction) {
                    Label(secondaryButtonTitle, systemImage: secondarySystemImage)
                        .labelStyle(.titleAndIcon)
                        .font(.subheadline.weight(.bold))
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(ConnectSecondaryButtonStyle())
                .disabled(isBusy)
            }
            .padding(18)
            .background(AgentPocketDesignTokens.lightSurface, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous)
                    .stroke(AgentPocketDesignTokens.lightStroke, lineWidth: 1)
            }
            .shadow(color: AgentPocketDesignTokens.lightShadow, radius: 20, y: 10)
        }
        .padding(18)
    }
}

private struct ManualFallbackButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(title, systemImage: "keyboard")
                .labelStyle(.titleAndIcon)
                .font(.callout.weight(.bold))
                .frame(maxWidth: .infinity, minHeight: 46)
        }
        .buttonStyle(ConnectSecondaryButtonStyle())
    }
}

private struct ConnectionPrivacyLine: View {
    let copy: ConnectScreenCopy

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 7) {
            Image(systemName: "lock.fill")
                .font(.caption2.weight(.bold))
                .foregroundStyle(AgentPocketDesignTokens.inkMuted)

            Text(copy.privacyLine)
                .font(.caption)
                .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                .multilineTextAlignment(.leading)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 2)
    }
}

private struct ConnectionRecoveryGuidancePanel: View {
    let presentation: ConnectionReadinessPresentation
    let language: AppLanguage

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Text(ownerLabel)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.secondary.opacity(0.14), in: Capsule())

                Text(localizedTitle)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.primary)
                    .lineLimit(2)
            }

            Text(localizedMessage)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            HStack(spacing: 12) {
                Label(localizedPrimaryActionTitle, systemImage: "checkmark.circle")

                if let secondaryActionTitle = localizedSecondaryActionTitle {
                    Label(secondaryActionTitle, systemImage: "arrow.turn.up.right")
                }
            }
            .font(.caption.weight(.medium))
            .foregroundStyle(Color(red: 0.06, green: 0.45, blue: 0.38))
            .lineLimit(2)
            .minimumScaleFactor(0.86)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(AgentPocketDesignTokens.lightSurfaceSubtle, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous)
                .stroke(Color.white.opacity(0.58), lineWidth: 1)
        }
    }

    private var ownerLabel: String {
        guard language == .chinese else {
            return ConnectionReadinessPresenter.ownerLabel(for: presentation.recoveryOwner)
        }

        switch presentation.recoveryOwner {
        case .phone:
            return "iPhone"
        case .hostRuntime:
            return "Mac"
        }
    }

    private var localizedTitle: String {
        guard language == .chinese else {
            return presentation.title
        }

        switch presentation.issue {
        case .expiredPairingQRCode:
            return "配对码已过期"
        case .pairingCodeAlreadyUsed:
            return "配对码已使用"
        case .revokedSavedConnection:
            return "令牌未被接受"
        case .bridgeUnavailable:
            return "本机智能体离线"
        case .savedRuntimeUnavailable:
            return "Mac 端需要启动"
        case .missingBonjourHost:
            return "未找到本机智能体"
        case .requiredTLSCertificateFailure:
            return "证书需要处理"
        case .portConflict:
            return "Mac 端口需要处理"
        case .disabledHostAction:
            return "Mac 端操作暂不可用"
        case .hostExtensionUnavailable:
            return "Mac 扩展未准备好"
        }
    }

    private var localizedMessage: String {
        guard language == .chinese else {
            return presentation.message
        }

        switch presentation.issue {
        case .expiredPairingQRCode:
            return "请扫描 Mac 上刷新的配对二维码。如果 iPhone 仍看到旧码，先在 Mac 上刷新二维码。"
        case .pairingCodeAlreadyUsed:
            return "请在 Mac 上生成新的移动端配对码，然后用 iPhone 重新扫描。"
        case .revokedSavedConnection:
            return "当前移动端令牌不可用。请在 Mac 上生成新的配对码后重新连接。"
        case .bridgeUnavailable:
            return "请确认 Mac 上的 Kaka Mobile Bridge 正在运行，并且 iPhone 可访问。"
        case .savedRuntimeUnavailable:
            return "配对仍然有效，不需要先重新扫码。请在 Mac 上启动 Hermes/OpenClaw 或 runtime-kit，然后点“我已启动，重新连接”。"
        case .missingBonjourHost:
            return "请允许本地网络访问，或改用扫码/手动输入地址连接。"
        case .requiredTLSCertificateFailure:
            return "请使用可信 HTTPS 证书、Tailscale HTTPS，或切换到本地开发连接方式。"
        case .portConflict:
            return "请在 Mac 上检查 bridge 端口，换到可用端口后再从 iPhone 重试。"
        case .disabledHostAction:
            return "需要等待 Mac 端完成设置、健康检查或能力安装后再重试。"
        case .hostExtensionUnavailable:
            return "请在 Mac 上打开 Kaka Mobile Bridge 并完成主机设置。"
        }
    }

    private var localizedPrimaryActionTitle: String {
        guard language == .chinese else {
            return presentation.primaryActionTitle
        }

        switch presentation.recoveryAction {
        case .scanRefreshedPairingQR:
            return "扫描新二维码"
        case .generateMobilePairingCode:
            return "在 Mac 上生成"
        case .startMobileBridge:
            if presentation.issue == .savedRuntimeUnavailable {
                return "Mac 已启动后重连"
            }
            return "启动 Mobile Bridge"
        case .useLocalNetworkOrManualEndpointFallback:
            return "扫码或手动输入"
        case .repairHostPort:
            return "检查 Mac 端口"
        case .waitForRuntimeStateChange:
            return "检查运行状态"
        case .checkHostExtension:
            return "检查 Mac 设置"
        }
    }

    private var localizedSecondaryActionTitle: String? {
        guard let secondaryActionTitle = presentation.secondaryActionTitle else {
            return nil
        }
        guard language == .chinese else {
            return secondaryActionTitle
        }

        switch secondaryActionTitle {
        case "Refresh QR on Host":
            return "刷新 Mac 上的二维码"
        case "Scan New QR", "Scan Pairing QR":
            return "扫描二维码"
        case "Discover Local Runtime":
            return "重新发现"
        case "I've Started It, Reconnect":
            return "我已启动，重新连接"
        case "Enter Endpoint", "Change Endpoint":
            return "手动输入"
        case "Try Again":
            return "重试"
        default:
            return secondaryActionTitle
        }
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
        .background(AgentPocketColors.surfaceBackground, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous))
        .shadow(color: .black.opacity(0.06), radius: 18, y: 8)
    }
}

private struct ProjectSettingsSheet: View {
    @Environment(\.dismiss) private var dismiss
    let copy: ConnectScreenCopy

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
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
            .background(AgentPocketDesignTokens.lightSurface, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous)
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
                        AgentPocketDesignTokens.accent
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                ),
                in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
            )
            .shadow(color: Color(red: 0.14, green: 0.72, blue: 0.67).opacity(configuration.isPressed ? 0.10 : 0.22), radius: 18, y: 10)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
    }
}

private struct ConnectSecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(AgentPocketDesignTokens.ink)
            .background(
                Color.white.opacity(configuration.isPressed ? 0.58 : 0.72),
                in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
            )
            .overlay {
                RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                    .stroke(Color.white.opacity(0.82), lineWidth: 1)
            }
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
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    .padding(.horizontal, 10)
                    .frame(minHeight: 30)
                    .background(AgentPocketColors.secondaryGroupedBackground, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
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
        case .unauthorized, .offline, .savedConnectionOffline, .invalidCertificate, .missingPhotoEdit, .localNetworkPermissionRequired, .failed:
            return Color.red
        case .testing, .scanning, .discovering, .restoringSavedConnection:
            return Color.blue
        default:
            return Color.black
        }
    }

    private var symbol: String {
        switch state {
        case .connected:
            return "checkmark"
        case .unauthorized, .offline, .savedConnectionOffline, .invalidCertificate, .missingPhotoEdit, .localNetworkPermissionRequired, .failed:
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
                .foregroundStyle(AgentPocketDesignTokens.ink)

            VStack(spacing: 10) {
                ManualFieldGroup(title: copy.endpointFieldTitle) {
                    ManualTextFieldShell(systemImage: "network") {
                        TextField(
                            "",
                            text: $viewModel.endpointText,
                            prompt: Text(copy.endpointPlaceholder)
                                .foregroundStyle(AgentPocketDesignTokens.inkMuted.opacity(0.72))
                        )
                            .agentURLInputTraits()
                            .accessibilityLabel(copy.endpointFieldTitle)
                    }
                }

                ManualFieldGroup(title: copy.tokenFieldTitle) {
                    ManualTextFieldShell(systemImage: "key.horizontal") {
                        SecureField(
                            "",
                            text: $viewModel.tokenText,
                            prompt: Text(copy.tokenPlaceholder)
                                .foregroundStyle(AgentPocketDesignTokens.inkMuted.opacity(0.72))
                        )
                            .agentTokenInputTraits()
                            .accessibilityLabel(copy.tokenFieldTitle)
                    }
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
        .background(AgentPocketDesignTokens.lightSurface, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous)
                .stroke(Color.white.opacity(0.66), lineWidth: 1)
        }
        .shadow(color: Color(red: 0.13, green: 0.20, blue: 0.22).opacity(0.08), radius: 18, y: 10)
    }
}

private struct ManualFieldGroup<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption.weight(.bold))
                .foregroundStyle(AgentPocketDesignTokens.inkMuted)

            content
        }
    }
}

private struct ManualTextFieldShell<Content: View>: View {
    let systemImage: String
    @ViewBuilder let content: Content

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: systemImage)
                .font(.callout.weight(.semibold))
                .foregroundStyle(AgentPocketDesignTokens.accentStrong)
                .frame(width: 22)
                .accessibilityHidden(true)

            content
                .font(.body.weight(.medium))
                .foregroundStyle(AgentPocketDesignTokens.ink)
        }
        .padding(.horizontal, 14)
        .frame(minHeight: 48)
        .background(Color.white.opacity(0.70), in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
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
                    .foregroundStyle(AgentPocketDesignTokens.ink)

                Text(copy.nearbyRuntimeDescription)
                    .font(.footnote)
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
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
                                .foregroundStyle(AgentPocketDesignTokens.accentStrong)
                        }

                        VStack(alignment: .leading, spacing: 3) {
                            Text(runtime.displayName)
                                .font(.body.weight(.semibold))
                                .foregroundStyle(AgentPocketDesignTokens.ink)
                                .lineLimit(1)

                            HStack(spacing: 6) {
                                Circle()
                                    .fill(AgentPocketDesignTokens.statusSuccess)
                                    .frame(width: 7, height: 7)

                                Text(endpointDetail(for: runtime))
                                    .font(.footnote)
                                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
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
                                AgentPocketDesignTokens.accent.opacity(0.86),
                                in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                            )
                    }
                    .padding(.horizontal, 14)
                    .frame(maxWidth: .infinity, minHeight: 68, alignment: .leading)
                    .background(Color.white.opacity(0.64), in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous))
                    .overlay {
                        RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous)
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
        .background(AgentPocketDesignTokens.lightSurface, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.panelRadius, style: .continuous)
                .stroke(Color.white.opacity(0.66), lineWidth: 1)
        }
        .shadow(color: Color(red: 0.13, green: 0.20, blue: 0.22).opacity(0.08), radius: 18, y: 10)
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
