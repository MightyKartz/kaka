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
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                Button(role: .destructive) {
                                    Task {
                                        await viewModel.delete(itemID: item.itemID, connection: activeConnection())
                                    }
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                    }
                }
            }
        }
        .listStyle(.plain)
        .navigationTitle("Recall")
        .searchable(text: $viewModel.query, prompt: "Search Recall")
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
                    Label("Export", systemImage: "square.and.arrow.up")
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

    @ViewBuilder
    private var stateSection: some View {
        switch viewModel.state {
        case .failed(let message):
            Section {
                Label(message, systemImage: "exclamationmark.triangle.fill")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.red)
            }
        case .exported(let export):
            Section {
                Label("Exported \(export.items.count) Recall items", systemImage: "checkmark.circle.fill")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.green)
            }
        case .deleting:
            Section {
                Label("Deleting Recall item", systemImage: "trash")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
        case .exporting:
            Section {
                HStack(spacing: 10) {
                    ProgressView()
                    Text("Exporting Recall")
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
            }
        case .idle, .loading, .loaded:
            EmptyView()
        }
    }

    private var emptySection: some View {
        Section {
            ContentUnavailableView(
                "No Recall Items",
                systemImage: "brain.head.profile",
                description: Text("Search or refresh after saving Recall items from completed tasks.")
            )
        }
    }

    private func itemRow(_ item: RecallItem, matchReason: String?) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(item.summary)
                .font(.body.weight(.semibold))
                .foregroundStyle(.primary)
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
            .foregroundStyle(.secondary)
            .lineLimit(2)
        }
        .padding(.vertical, 4)
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
            parts.append("Task \(sourceTaskID)")
        }
        if let sourceInboxItemID = provenance.sourceInboxItemID {
            parts.append("Inbox \(sourceInboxItemID.uuidString)")
        }
        return parts.isEmpty ? "No provenance" : parts.joined(separator: " / ")
    }

    private func matchReason(for item: RecallItem) -> String? {
        viewModel.lastSearchMatches.first { $0.item.itemID == item.itemID }?.matchReason
    }
}
