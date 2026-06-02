import AgentPocketCore
import AgentPocketUI
import SwiftUI

struct AppTaskProgressView: View {
    let status: TaskStatusResponse

    var body: some View {
        AgentPocketUI.TaskProgressView(status: status)
    }
}
