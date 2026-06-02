import AgentPocketCore
import AgentPocketUI
import SwiftUI

struct AppResultGalleryView: View {
    let status: TaskStatusResponse

    var body: some View {
        AgentPocketUI.ResultGalleryView(status: status)
    }
}
