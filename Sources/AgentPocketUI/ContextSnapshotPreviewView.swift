import AgentPocketCore
import SwiftUI

public struct ContextSnapshotPreviewView: View {
    @ObservedObject private var viewModel: ContextSnapshotViewModel

    public init(viewModel: ContextSnapshotViewModel) {
        self.viewModel = viewModel
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Toggle(isOn: $viewModel.includeContext) {
                Label("Context", systemImage: "location.circle")
                    .font(.headline)
            }
            .tint(Color(red: 0.55, green: 0.96, blue: 0.89))

            if let snapshot = viewModel.snapshotPreview {
                VStack(alignment: .leading, spacing: 8) {
                    snapshotRow("Time", snapshot.timestamp)
                    snapshotRow("Timezone", snapshot.timezone)
                    snapshotRow("Locale", snapshot.locale)
                    snapshotRow("Source", snapshot.sourceSurface)
                    snapshotRow("Network", snapshot.network)
                    snapshotRow("Battery", snapshot.battery)
                    snapshotRow("Motion", snapshot.motion)
                    snapshotRow("Location", snapshot.locationLabel)
                }
                .font(.footnote)
            }

            if let permissionMessage = viewModel.permissionMessage {
                Text(permissionMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .task {
            await viewModel.refresh()
        }
    }

    @ViewBuilder
    private func snapshotRow(_ label: String, _ value: String?) -> some View {
        if let value, !value.isEmpty {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(label)
                    .foregroundStyle(.secondary)
                    .frame(width: 72, alignment: .leading)
                Text(value)
                    .foregroundStyle(.primary)
                    .textSelection(.enabled)
            }
            .accessibilityElement(children: .combine)
        }
    }
}
