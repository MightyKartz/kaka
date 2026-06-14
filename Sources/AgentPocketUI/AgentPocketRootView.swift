import AgentPocketCore
import Foundation
import SwiftUI
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

public enum AgentPocketRootTab: Hashable, Sendable {
    case capture
    case inbox
    case recall
    case tasks

    var localizedTitle: String {
        let language = AppLanguage.resolved(storedValue: nil)
        switch (self, language) {
        case (.capture, .chinese):
            return "拍照"
        case (.capture, .english):
            return "Capture"
        case (.inbox, .chinese):
            return "收件箱"
        case (.inbox, .english):
            return "Inbox"
        case (.recall, .chinese):
            return "记忆"
        case (.recall, .english):
            return "Recall"
        case (.tasks, .chinese):
            return "活动"
        case (.tasks, .english):
            return "Activity"
        }
    }
}

public struct AgentPocketRootView: View {
    @Environment(\.openURL) private var openURL
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var connectionViewModel = ConnectionViewModel()
    @StateObject private var captureViewModel = CaptureFlowViewModel()
    @StateObject private var voiceCaptureViewModel = VoiceCaptureViewModel(transcriber: VoiceTranscriberFactory.makeDefault())
    @State private var hasBootstrappedConnection = false
    @State private var selectedTab: AgentPocketRootTab = .capture
    @State private var connectionSheet: ConnectionSheet?
    @State private var lensSheet: LocalAgentLensSheet?

    public init() {}

    public var body: some View {
        NavigationStack {
            rootTabs(runtime: connectedRuntime)
        }
        .sheet(item: $connectionSheet) { _ in
            NavigationStack {
                ConnectView(viewModel: connectionViewModel)
            }
        }
        .sheet(item: $lensSheet) { sheet in
            lensSheetView(sheet)
        }
        .task {
            guard hasBootstrappedConnection == false else {
                return
            }
            hasBootstrappedConnection = true
            let outcome = await connectionViewModel.bootstrapConnectionForLaunch()
            if outcome == .needsFirstPairing {
                connectionSheet = .firstPairing
            }
            handlePendingAppIntentHandoff()
        }
        .onChange(of: scenePhase) { _, newPhase in
            guard newPhase == .active else {
                return
            }
            handlePendingAppIntentHandoff()
        }
        .onChange(of: connectionViewModel.state) { _, newState in
            if case .connected = newState {
                connectionSheet = nil
            }
        }
    }

    private var connectedRuntime: ConnectedRuntime? {
        guard case .connected(let runtime) = connectionViewModel.state else {
            return nil
        }
        return runtime
    }

    private func rootTabs(runtime: ConnectedRuntime?) -> some View {
        TabView(selection: $selectedTab) {
            connectionAwareTab(runtime: runtime) {
                CaptureView(viewModel: captureViewModel, connectedRuntime: runtime) {
                    connectionSheet = .manageConnection
                } onLensAction: { actionID in
                    handleLocalAgentLensAction(actionID)
                } activeConnection: {
                    connectionViewModel.activeConnection
                }
            }
            .tabItem {
                Label(AgentPocketRootTab.capture.localizedTitle, systemImage: "camera.viewfinder")
            }
            .tag(AgentPocketRootTab.capture)

            connectionAwareTab(runtime: runtime) {
                InboxView(viewModel: makeInboxViewModel()) {
                    connectionViewModel.activeConnection
                }
            }
            .tabItem {
                Label(AgentPocketRootTab.inbox.localizedTitle, systemImage: "tray.full")
            }
            .tag(AgentPocketRootTab.inbox)

            connectionAwareTab(runtime: runtime) {
                RecallBrowseView {
                    connectionViewModel.activeConnection
                }
            }
            .tabItem {
                Label(AgentPocketRootTab.recall.localizedTitle, systemImage: "brain.head.profile")
            }
            .tag(AgentPocketRootTab.recall)

            connectionAwareTab(runtime: runtime) {
                TaskInboxView {
                    connectionViewModel.activeConnection
                }
            }
            .tabItem {
                Label(AgentPocketRootTab.tasks.localizedTitle, systemImage: "waveform.path.ecg.rectangle")
            }
            .tag(AgentPocketRootTab.tasks)
        }
    }

    @ViewBuilder
    private func connectionAwareTab<Content: View>(
        runtime: ConnectedRuntime?,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(spacing: 0) {
            if runtime == nil {
                RootConnectionBanner(
                    state: connectionViewModel.state,
                    primaryAction: rootConnectionPrimaryAction,
                    secondaryAction: rootConnectionSecondaryAction
                )
            }

            content()
        }
    }

    private func handlePendingAppIntentHandoff() {
        guard let handoff = KakaAppIntentHandoffStore().consumePendingHandoff() else {
            return
        }
        selectedTab = handoff.surface.targetTab
        presentLensSheet(for: handoff.surface)
    }

    @ViewBuilder
    private func lensSheetView(_ sheet: LocalAgentLensSheet) -> some View {
        switch sheet {
        case .agentScanner:
            AgentScannerView { result in
                lensSheet = .scanActions(result)
            } onCancel: {
                lensSheet = nil
            }
        case .scanActions(let result):
            AgentScanActionSheet(result: result) { action in
                handleScanAction(action, result: result)
            }
        case .documentScanner:
            #if os(iOS) && canImport(VisionKit)
            AgentDocumentScannerView { pdfData in
                appendDocumentScanDraft(pdfData)
            } onCancel: {
                lensSheet = nil
            }
            .ignoresSafeArea()
            #else
            ContentUnavailableView(
                "Document Scan Unavailable",
                systemImage: "doc.viewfinder",
                description: Text("Open Pocket Agent on iPhone to scan documents.")
            )
            #endif
        case .videoIntake:
            VideoIntakePickerView(
                payloadDirectory: inboxPayloadContainerURL(),
                onDraft: { item in
                    appendInboxDraft(item)
                },
                onCancel: {
                    lensSheet = nil
                }
            )
        case .voiceRecorder:
            VoiceCaptureView(
                viewModel: voiceCaptureViewModel,
                presentation: .inboxDraft(language: AppLanguage.resolved(storedValue: nil)),
                onCancel: {
                    voiceCaptureViewModel.reset()
                    lensSheet = nil
                },
                onSend: { transcript in
                    appendVoiceDraft(transcript)
                }
            )
            .presentationDetents([.medium, .large])
        }
    }

    private func handleLocalAgentLensAction(_ actionID: String) {
        switch actionID {
        case "agent_scanner":
            lensSheet = .agentScanner
        case "document_scan":
            lensSheet = .documentScanner
        case "video_intake":
            lensSheet = .videoIntake
        case "voice_recorder":
            voiceCaptureViewModel.reset()
            lensSheet = .voiceRecorder
        case "inbox":
            selectedTab = .inbox
        case "tasks":
            selectedTab = .tasks
        default:
            break
        }
    }

    private func presentLensSheet(for surface: KakaSystemSurface) {
        switch surface {
        case .agentScanner:
            lensSheet = .agentScanner
        case .documentScanner:
            lensSheet = .documentScanner
        case .videoCapture:
            lensSheet = .videoIntake
        case .voiceRecorder:
            voiceCaptureViewModel.reset()
            lensSheet = .voiceRecorder
        case .inbox, .tasks, .reviewInboxItem, .reviewRuntimeTask:
            break
        }
    }

    private func handleScanAction(_ action: AgentScanAction.Kind, result: AgentScanResult) {
        switch action {
        case .connectLocalRuntime:
            lensSheet = nil
            Task {
                await connectionViewModel.connectWithPairingPayload(
                    result.rawValue,
                    deviceName: rootPairingDeviceName,
                    devicePublicID: rootPairingDevicePublicID
                )
            }
        case .summarizeURL, .saveToInbox, .askAgentAboutText:
            appendInboxDraft(AgentScanInboxDraftBuilder.item(for: result))
        case .openURL:
            lensSheet = nil
            if let url = result.url {
                openURL(url)
            }
        case .copy:
            copyToPasteboard(result.rawValue)
            lensSheet = nil
        }
    }

    private func appendDocumentScanDraft(_ pdfData: Data) {
        let fileName = "scan-\(Self.fileSafeTimestamp()).pdf"
        do {
            let item = try DocumentScanInboxBuilder(payloadDirectory: inboxPayloadContainerURL())
                .makeInboxItem(pdfData: pdfData, fileName: fileName)
            appendInboxDraft(item)
        } catch {
            lensSheet = nil
        }
    }

    private func appendVoiceDraft(_ transcript: String) {
        let text = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
        guard text.isEmpty == false else {
            return
        }
        let item = KakaInboxItem(
            kind: .text,
            sourceApp: "Pocket Agent Voice",
            sourceSurface: "voice",
            locale: Locale.current.identifier,
            text: text,
            route: .universalIntake
        )
        appendInboxDraft(item)
        voiceCaptureViewModel.reset()
    }

    private func appendInboxDraft(_ item: KakaInboxItem) {
        do {
            try FileKakaInboxStore().append(item)
            selectedTab = .inbox
            lensSheet = nil
        } catch {
            lensSheet = nil
        }
    }

    private func inboxPayloadContainerURL() -> URL {
        FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: FileKakaInboxStore.defaultAppGroupIdentifier)
            ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)
                .first!
                .appendingPathComponent(FileKakaInboxStore.defaultAppGroupIdentifier, isDirectory: true)
    }

    private func copyToPasteboard(_ value: String) {
        SystemClipboardCourierWriter().writeString(value)
    }

    private var rootPairingDeviceName: String {
        #if os(iOS)
        UIDevice.current.name
        #elseif canImport(AppKit)
        Host.current().localizedName ?? "Pocket Agent Mac"
        #else
        "Pocket Agent"
        #endif
    }

    private var rootPairingDevicePublicID: String {
        #if os(iOS)
        UIDevice.current.identifierForVendor?.uuidString ?? "agent-pocket-ios-device"
        #else
        rootPairingDeviceName
            .lowercased()
            .replacingOccurrences(of: " ", with: "-")
        #endif
    }

    private static func fileSafeTimestamp() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd-HHmmss"
        return formatter.string(from: Date())
    }

    private func makeInboxViewModel() -> InboxViewModel {
        let store = FileKakaInboxStore()
        return InboxViewModel(
            store: store,
            imageSubmitter: MobileBridgeImageInboxSubmitter(
                loader: FileInboxImagePayloadLoader()
            )
        )
    }

    private func rootConnectionPrimaryAction() {
        switch connectionViewModel.state {
        case .savedConnectionOffline:
            Task {
                await connectionViewModel.restoreSavedConnectionOrDiscoverNearby()
            }
        default:
            connectionSheet = .manageConnection
        }
    }

    private func rootConnectionSecondaryAction() {
        connectionSheet = .firstPairing
        connectionViewModel.beginScanning()
    }
}

private enum ConnectionSheet: Identifiable {
    case firstPairing
    case manageConnection

    var id: String {
        switch self {
        case .firstPairing:
            return "firstPairing"
        case .manageConnection:
            return "manageConnection"
        }
    }
}

private enum LocalAgentLensSheet: Identifiable {
    case agentScanner
    case scanActions(AgentScanResult)
    case documentScanner
    case videoIntake
    case voiceRecorder

    var id: String {
        switch self {
        case .agentScanner:
            return "agentScanner"
        case .scanActions(let result):
            return "scanActions-\(result.id)"
        case .documentScanner:
            return "documentScanner"
        case .videoIntake:
            return "videoIntake"
        case .voiceRecorder:
            return "voiceRecorder"
        }
    }
}

private struct RootConnectionBanner: View {
    let state: ConnectionState
    let primaryAction: () -> Void
    let secondaryAction: () -> Void

    var body: some View {
        HStack(alignment: .center, spacing: 10) {
            statusIcon

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(.white)
                    .lineLimit(1)
                    .minimumScaleFactor(0.86)

                Text(message)
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.68))
                    .lineLimit(2)
            }

            Spacer(minLength: 8)

            if showsSecondaryAction {
                Button(action: secondaryAction) {
                    Label(secondaryButtonTitle, systemImage: "qrcode.viewfinder")
                        .labelStyle(.iconOnly)
                        .font(.caption.weight(.bold))
                        .frame(width: 38, height: 34)
                }
                .buttonStyle(AgentPocketDarkIconButtonStyle())
                .accessibilityLabel(secondaryButtonTitle)
            }

            Button(action: primaryAction) {
                Label(buttonTitle, systemImage: buttonSystemImage)
                    .labelStyle(.titleAndIcon)
                    .font(.caption.weight(.bold))
                    .frame(minHeight: 34)
                    .padding(.horizontal, 10)
            }
            .buttonStyle(AgentPocketDarkPrimaryButtonStyle())
            .accessibilityIdentifier("rootConnectRuntimeButton")
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(AgentPocketDesignTokens.darkBackground)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(AgentPocketDesignTokens.darkStroke)
                .frame(height: 1)
        }
    }

    @ViewBuilder
    private var statusIcon: some View {
        switch state {
        case .discovering, .testing, .scanning, .restoringSavedConnection:
            ProgressView()
                .tint(AgentPocketDesignTokens.accent)
                .frame(width: 30, height: 30)
                .accessibilityHidden(true)
        default:
            Image(systemName: "antenna.radiowaves.left.and.right.slash")
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(AgentPocketDesignTokens.accent)
                .frame(width: 30, height: 30)
                .background(AgentPocketDesignTokens.darkSecondaryFill, in: Circle())
                .accessibilityHidden(true)
        }
    }

    private var language: AppLanguage {
        AppLanguage.resolved(storedValue: nil)
    }

    private var title: String {
        switch (state, language) {
        case (.discovering, .chinese):
            return "正在发现本机智能体"
        case (.discovering, .english):
            return "Finding Local Agent"
        case (.restoringSavedConnection, .chinese):
            return "正在恢复已保存连接"
        case (.restoringSavedConnection, .english):
            return "Restoring Saved Runtime"
        case (.testing, .chinese):
            return "正在检查连接"
        case (.testing, .english):
            return "Checking Connection"
        case (.savedConnectionOffline, .chinese):
            return "Mac 端运行时未启动"
        case (.savedConnectionOffline, .english):
            return "Start Runtime on Mac"
        default:
            return language == .chinese ? "本机智能体未连接" : "Local Agent Not Connected"
        }
    }

    private var message: String {
        switch language {
        case .chinese:
            switch state {
            case .savedConnectionOffline(let displayName):
                return "\(displayName) 配对已保存。请先在 Mac 上启动运行时。"
            case .idle:
                return "首次连接需要扫描 Mac 上的配对二维码。"
            default:
                return "仍可查看收件箱和记忆；发送照片前需要连接。"
            }
        case .english:
            switch state {
            case .savedConnectionOffline(let displayName):
                return "\(displayName) is still paired. Start the runtime on your Mac first."
            case .idle:
                return "Scan the pairing QR on your Mac for first-time setup."
            default:
                return "You can still review Inbox and Recall. Connect before sending photos."
            }
        }
    }

    private var buttonTitle: String {
        switch (state, language) {
        case (.savedConnectionOffline, .chinese):
            return "已启动，重连"
        case (.savedConnectionOffline, .english):
            return "Reconnect"
        default:
            return language == .chinese ? "连接" : "Connect"
        }
    }

    private var buttonSystemImage: String {
        switch state {
        case .savedConnectionOffline:
            return "arrow.clockwise"
        default:
            return "dot.radiowaves.left.and.right"
        }
    }

    private var secondaryButtonTitle: String {
        language == .chinese ? "重新扫码" : "Scan New QR"
    }

    private var showsSecondaryAction: Bool {
        if case .savedConnectionOffline = state {
            return true
        }
        return false
    }
}
