import AgentPocketCore
import SwiftUI

public struct RecallBrowseView: View {
    @StateObject private var viewModel: RecallBrowseViewModel
    @State private var hasLoaded = false

    private let activeConnection: () -> StoredConnection?

    public init(
        viewModel: RecallBrowseViewModel = RecallBrowseViewModel(),
        activeConnection: @escaping () -> StoredConnection?
    ) {
        _viewModel = StateObject(wrappedValue: viewModel)
        self.activeConnection = activeConnection
    }

    public var body: some View {
        List {
            stateSection

            if viewModel.items.isEmpty, isLoading == false {
                emptySection
            } else {
                Section {
                    ForEach(viewModel.items, id: \.itemID) { item in
                        itemRow(item, matchReason: matchReason(for: item))
                            .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
                            .listRowBackground(Color.clear)
                            .listRowSeparator(.hidden)
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    Task {
                                        await viewModel.delete(itemID: item.itemID, connection: activeConnection())
                                    }
                                } label: {
                                    Label(language == .chinese ? "删除" : "Delete", systemImage: "trash")
                                }
                            }
                    }
                }
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(AgentPocketDesignTokens.lightCanvas.ignoresSafeArea())
        .tint(AgentPocketDesignTokens.accent)
        .navigationTitle(language == .chinese ? "记忆" : "Recall")
        .searchable(text: $viewModel.query, prompt: language == .chinese ? "搜索记忆" : "Search Recall")
        .onSubmit(of: .search) {
            Task {
                await viewModel.search(query: viewModel.query, connection: activeConnection())
            }
        }
        .refreshable {
            await viewModel.load(connection: activeConnection())
        }
        .overlay {
            if isLoading, viewModel.items.isEmpty {
                ProgressView()
            }
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    Task {
                        await viewModel.export(connection: activeConnection())
                    }
                } label: {
                    Label(language == .chinese ? "导出" : "Export", systemImage: "square.and.arrow.up")
                }
                .disabled(isBusy)
            }
        }
        .task {
            guard hasLoaded == false else {
                return
            }
            hasLoaded = true
            await viewModel.load(connection: activeConnection())
        }
    }

    private var language: AppLanguage {
        AppLanguage.resolved(storedValue: nil)
    }

    @ViewBuilder
    private var stateSection: some View {
        switch viewModel.state {
        case .failed(let message):
            Section {
                Label(message, systemImage: "exclamationmark.triangle.fill")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.red)
                    .recallStateRow()
            }
            .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
        case .exported(let export):
            Section {
                Label(exportedMessage(count: export.items.count), systemImage: "checkmark.circle.fill")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(AgentPocketDesignTokens.accentStrong)
                    .recallStateRow()
            }
            .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
        case .deleting:
            Section {
                Label(language == .chinese ? "正在删除记忆" : "Deleting Recall item", systemImage: "trash")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    .recallStateRow()
            }
            .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
        case .exporting:
            Section {
                HStack(spacing: 10) {
                    ProgressView()
                        .tint(AgentPocketDesignTokens.accent)
                    Text(language == .chinese ? "正在导出记忆" : "Exporting Recall")
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                }
                .recallStateRow()
            }
            .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
        case .idle, .loading, .loaded:
            EmptyView()
        }
    }

    private var emptySection: some View {
        Section {
            VStack(alignment: .center, spacing: 10) {
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 30, weight: .semibold))
                    .foregroundStyle(AgentPocketDesignTokens.accent)
                    .frame(width: 54, height: 54)

                Text(language == .chinese ? "还没有记忆" : "No Recall Items")
                    .font(.headline)
                    .foregroundStyle(AgentPocketDesignTokens.ink)

                Text(language == .chinese ? "完成任务后保存的要点会出现在这里，之后可以搜索或导出。" : "Search or refresh after saving Recall items from completed tasks.")
                    .font(.footnote)
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, minHeight: 220)
            .background(AgentPocketDesignTokens.lightPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                    .stroke(AgentPocketDesignTokens.lightBorder, lineWidth: 1)
            )
        }
        .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
        .listRowBackground(Color.clear)
        .listRowSeparator(.hidden)
    }

    private func itemRow(_ item: RecallItem, matchReason: String?) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(item.summary)
                .font(.body.weight(.semibold))
                .foregroundStyle(AgentPocketDesignTokens.ink)
                .lineLimit(4)
                .textSelection(.enabled)

            VStack(alignment: .leading, spacing: 4) {
                Label(item.createdAt, systemImage: "calendar")
                Label(provenanceText(item.provenance), systemImage: "link")
                if let matchReason, matchReason.isEmpty == false {
                    Label(matchReason, systemImage: "sparkle.magnifyingglass")
                }
            }
            .font(.caption)
            .foregroundStyle(AgentPocketDesignTokens.inkMuted)
            .lineLimit(2)
        }
        .padding(14)
        .background(AgentPocketDesignTokens.lightPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                .stroke(AgentPocketDesignTokens.lightBorder, lineWidth: 1)
        )
    }

    private var isLoading: Bool {
        if case .loading = viewModel.state {
            return true
        }
        return false
    }

    private var isBusy: Bool {
        switch viewModel.state {
        case .loading, .deleting, .exporting:
            return true
        case .idle, .loaded, .exported, .failed:
            return false
        }
    }

    private func provenanceText(_ provenance: RecallItem.Provenance) -> String {
        var parts: [String] = []
        if let sourceTaskID = provenance.sourceTaskID, sourceTaskID.isEmpty == false {
            parts.append(language == .chinese ? "任务 \(sourceTaskID)" : "Task \(sourceTaskID)")
        }
        if let sourceInboxItemID = provenance.sourceInboxItemID {
            parts.append(language == .chinese ? "收件箱 \(sourceInboxItemID.uuidString)" : "Inbox \(sourceInboxItemID.uuidString)")
        }
        return parts.isEmpty ? (language == .chinese ? "没有来源" : "No provenance") : parts.joined(separator: " / ")
    }

    private func exportedMessage(count: Int) -> String {
        switch language {
        case .chinese:
            return "已导出 \(count) 条记忆"
        case .english:
            return "Exported \(count) Recall items"
        }
    }

    private func matchReason(for item: RecallItem) -> String? {
        viewModel.lastSearchMatches.first { $0.item.itemID == item.itemID }?.matchReason
    }
}

private extension View {
    func recallStateRow() -> some View {
        self
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(AgentPocketDesignTokens.lightPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                    .stroke(AgentPocketDesignTokens.lightBorder, lineWidth: 1)
            )
    }
}
