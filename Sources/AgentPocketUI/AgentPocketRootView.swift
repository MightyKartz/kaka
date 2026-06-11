import AgentPocketCore
import SwiftUI

public enum AgentPocketRootTab: Hashable, Sendable {
    case capture
    case inbox
    case recall
    case tasks
}

public struct AgentPocketRootView: View {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var connectionViewModel = ConnectionViewModel()
    @StateObject private var captureViewModel = CaptureFlowViewModel()
    @State private var hasBootstrappedConnection = false
    @State private var selectedTab: AgentPocketRootTab = .capture

    public init() {}

    public var body: some View {
        NavigationStack {
            switch connectionViewModel.state {
            case .connected(let runtime):
                connectedTabs(runtime: runtime)
            default:
                ConnectView(viewModel: connectionViewModel)
            }
        }
        .task {
            guard hasBootstrappedConnection == false else {
                return
            }
            hasBootstrappedConnection = true
            await connectionViewModel.restoreSavedConnectionOrDiscoverNearby()
            handlePendingAppIntentHandoff()
        }
        .onChange(of: scenePhase) { _, newPhase in
            guard newPhase == .active else {
                return
            }
            handlePendingAppIntentHandoff()
        }
    }

    private func connectedTabs(runtime: ConnectedRuntime) -> some View {
        TabView(selection: $selectedTab) {
            CaptureView(viewModel: captureViewModel, connectedRuntime: runtime) {
                connectionViewModel.forgetSavedConnection()
            } activeConnection: {
                connectionViewModel.activeConnection
            }
            .tabItem {
                Label("Capture", systemImage: "camera.viewfinder")
            }
            .tag(AgentPocketRootTab.capture)

            InboxView(viewModel: makeInboxViewModel()) {
                connectionViewModel.activeConnection
            }
            .tabItem {
                Label("Inbox", systemImage: "tray.full")
            }
            .tag(AgentPocketRootTab.inbox)

            RecallBrowseView {
                connectionViewModel.activeConnection
            }
            .tabItem {
                Label("Recall", systemImage: "brain.head.profile")
            }
            .tag(AgentPocketRootTab.recall)

            TaskInboxView {
                connectionViewModel.activeConnection
            }
            .tabItem {
                Label("Tasks", systemImage: "list.bullet.rectangle")
            }
            .tag(AgentPocketRootTab.tasks)
        }
    }

    private func handlePendingAppIntentHandoff() {
        guard let handoff = KakaAppIntentHandoffStore().consumePendingHandoff() else {
            return
        }
        selectedTab = handoff.surface.targetTab
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
}
