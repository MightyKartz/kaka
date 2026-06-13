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
                Label(language == .chinese ? "共享上下文" : "Share Context", systemImage: "location.circle")
                    .font(.headline)
            }
            .tint(Color(red: 0.55, green: 0.96, blue: 0.89))

            if viewModel.includeContext && viewModel.isContextSnapshotPreparing {
                Label(language == .chinese ? "正在准备上下文" : "Preparing context", systemImage: "clock")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if !viewModel.previewRows.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(viewModel.previewRows) { row in
                        snapshotRow(row.label, row.value)
                    }
                }
                .font(.footnote)
            }

            if let permissionMessage = viewModel.permissionMessage {
                Text(permissionMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .onChange(of: viewModel.includeContext) { _, includeContext in
            guard includeContext else { return }
            Task {
                await viewModel.refreshForInclusionIfNeeded()
            }
        }
        .task {
            await viewModel.refreshForInclusionIfNeeded()
        }
    }

    private var language: AppLanguage {
        AppLanguage.resolved(storedValue: nil)
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
