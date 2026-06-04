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
                CaptureView(viewModel: captureViewModel, connectedRuntime: runtime) {
                    connectionViewModel.forgetSavedConnection()
                } activeConnection: {
                    connectionViewModel.activeConnection
                }
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
}
