import AgentPocketCore
import AgentPocketUI
import SwiftUI

struct AppEditIntentPickerView: View {
    @State private var selection: EditIntent = .naturalEnhance

    var body: some View {
        AgentPocketUI.EditIntentPickerView(selection: $selection)
    }
}
