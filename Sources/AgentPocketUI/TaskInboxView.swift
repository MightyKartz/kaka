import AgentPocketCore
import SwiftUI

public struct TaskInboxView: View {
    @StateObject private var viewModel: TaskInboxViewModel
    private let activeConnection: () -> StoredConnection?

    public init(
        viewModel: TaskInboxViewModel = TaskInboxViewModel(),
        activeConnection: @escaping () -> StoredConnection?
    ) {
        _viewModel = StateObject(wrappedValue: viewModel)
        self.activeConnection = activeConnection
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                Image(systemName: "list.bullet.rectangle")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                    .frame(width: 32, height: 32)
                    .background(.white.opacity(0.08), in: Circle())
                    .accessibilityHidden(true)

                Text("Tasks")
                    .font(.headline)
                    .foregroundStyle(.white)

                Spacer()

                Button {
                    Task {
                        await viewModel.load(connection: activeConnection())
                    }
                } label: {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 14, weight: .bold))
                        .frame(width: 32, height: 32)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.white.opacity(0.82))
                .accessibilityLabel("Refresh tasks")
            }

            content
        }
        .padding(14)
        .background(.black.opacity(0.24), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(.white.opacity(0.10), lineWidth: 1)
        )
        .task {
            await viewModel.load(connection: activeConnection())
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .loading:
            ProgressView()
                .tint(Color(red: 0.55, green: 0.96, blue: 0.89))
        case .failed(let message):
            Label(message, systemImage: "exclamationmark.triangle.fill")
                .font(.footnote.weight(.semibold))
                .foregroundStyle(Color(red: 1.0, green: 0.55, blue: 0.45))
        case .idle, .loaded, .submitting:
            if viewModel.tasks.isEmpty {
                Text("No active tasks")
                    .font(.footnote)
                    .foregroundStyle(.white.opacity(0.66))
            } else {
                VStack(spacing: 8) {
                    ForEach(viewModel.tasks) { task in
                        taskRow(task)
                    }
                }
            }
        }
    }

    private func taskRow(_ task: RuntimeTaskSummary) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Text(task.title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.white)
                    .lineLimit(2)
                Spacer()
                Text(task.status.rawValue.replacingOccurrences(of: "_", with: " "))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.62))
            }

            ProgressView(value: min(max(task.progress, 0), 1))
                .tint(task.requiresUserAction ? Color(red: 0.85, green: 0.76, blue: 1.0) : Color(red: 0.55, green: 0.96, blue: 0.89))

            if let message = task.message, message.isEmpty == false {
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.white.opacity(0.68))
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack(spacing: 8) {
                if task.requiresUserAction {
                    Button {
                        Task {
                            await viewModel.approve(taskID: task.id, connection: activeConnection())
                        }
                    } label: {
                        Label("Approve", systemImage: "checkmark")
                            .font(.caption.weight(.bold))
                            .frame(minHeight: 30)
                            .padding(.horizontal, 10)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.black)
                    .background(Color(red: 0.55, green: 0.96, blue: 0.89), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                }

                if task.isTerminal == false {
                    Button {
                        Task {
                            await viewModel.cancel(taskID: task.id, connection: activeConnection())
                        }
                    } label: {
                        Label("Cancel", systemImage: "xmark")
                            .font(.caption.weight(.bold))
                            .frame(minHeight: 30)
                            .padding(.horizontal, 10)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.white.opacity(0.84))
                    .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
            }
        }
        .padding(10)
        .background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}
