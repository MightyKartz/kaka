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
        ZStack {
            AgentPocketDesignTokens.lightCanvas
                .ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 12) {
                    HStack(spacing: 10) {
                        Image(systemName: "list.bullet.rectangle")
                            .font(.system(size: 18, weight: .semibold))
                            .foregroundStyle(AgentPocketDesignTokens.accentStrong)
                            .frame(width: 32, height: 32)
                            .background(AgentPocketDesignTokens.accent.opacity(0.18), in: Circle())
                            .accessibilityHidden(true)

                        Text(language == .chinese ? "活动" : "Activity")
                            .font(.headline)
                            .foregroundStyle(AgentPocketDesignTokens.ink)

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
                        .buttonStyle(AgentPocketLightIconButtonStyle())
                        .accessibilityLabel(language == .chinese ? "刷新活动" : "Refresh activity")
                    }

                    content
                }
                .padding(14)
                .frame(maxWidth: 720)
                .frame(maxWidth: .infinity, alignment: .top)
            }
        }
        .task {
            await viewModel.load(connection: activeConnection())
        }
        .navigationTitle(language == .chinese ? "活动" : "Activity")
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .loading:
            ProgressView()
                .tint(AgentPocketDesignTokens.accent)
        case .failed(let message):
            Label(message, systemImage: "exclamationmark.triangle.fill")
                .font(.footnote.weight(.semibold))
                .foregroundStyle(Color(red: 1.0, green: 0.55, blue: 0.45))
        case .idle, .loaded, .submitting:
            if viewModel.tasks.isEmpty {
                Text(language == .chinese ? "没有正在进行的活动" : "No active activity")
                    .font(.footnote)
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    .frame(maxWidth: .infinity, minHeight: 180)
                    .background(AgentPocketDesignTokens.lightPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                            .stroke(AgentPocketDesignTokens.lightBorder, lineWidth: 1)
                    )
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
                Text(TaskInboxPresentation.taskTitle(task.title, language: language))
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(AgentPocketDesignTokens.ink)
                    .lineLimit(2)
                Spacer()
                Text(TaskInboxPresentation.statusTitle(task.status.rawValue, language: language))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
            }

            ProgressView(value: min(max(task.progress, 0), 1))
                .tint(task.requiresUserAction ? Color.orange : AgentPocketDesignTokens.accentStrong)

            if let message = task.message, message.isEmpty == false {
                Text(TaskInboxPresentation.taskMessage(message, language: language))
                    .font(.footnote)
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack(spacing: 8) {
                if task.requiresUserAction {
                    Button {
                        Task {
                            await viewModel.approve(taskID: task.id, connection: activeConnection())
                        }
                    } label: {
                        Label(language == .chinese ? "批准" : "Approve", systemImage: "checkmark")
                            .font(.caption.weight(.bold))
                            .frame(minHeight: 30)
                            .padding(.horizontal, 10)
                    }
                    .buttonStyle(AgentPocketLightPrimaryButtonStyle())
                }

                if task.isTerminal == false {
                    Button {
                        Task {
                            await viewModel.cancel(taskID: task.id, connection: activeConnection())
                        }
                    } label: {
                        Label(language == .chinese ? "取消" : "Cancel", systemImage: "xmark")
                            .font(.caption.weight(.bold))
                            .frame(minHeight: 30)
                            .padding(.horizontal, 10)
                    }
                    .buttonStyle(AgentPocketLightSecondaryButtonStyle())
                }
            }
        }
        .padding(10)
        .background(AgentPocketDesignTokens.lightPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                .stroke(AgentPocketDesignTokens.lightBorder, lineWidth: 1)
        )
    }

    private var language: AppLanguage {
        AppLanguage.resolved(storedValue: nil)
    }

}
