import AgentPocketCore
import SwiftUI

public struct AgentPocketRootView: View {
    @StateObject private var connectionViewModel = ConnectionViewModel()
    @StateObject private var captureViewModel = CaptureFlowViewModel()
    @State private var hasBootstrappedConnection = false

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
        }
    }

    private func connectedTabs(runtime: ConnectedRuntime) -> some View {
        TabView {
            CaptureView(viewModel: captureViewModel, connectedRuntime: runtime) {
                connectionViewModel.forgetSavedConnection()
            } activeConnection: {
                connectionViewModel.activeConnection
            }
            .tabItem {
                Label("Capture", systemImage: "camera.viewfinder")
            }

            InboxView(viewModel: makeInboxViewModel()) {
                connectionViewModel.activeConnection
            }
            .tabItem {
                Label("Inbox", systemImage: "tray.full")
            }

            TaskInboxView {
                connectionViewModel.activeConnection
            }
            .tabItem {
                Label("Tasks", systemImage: "list.bullet.rectangle")
            }
        }
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
