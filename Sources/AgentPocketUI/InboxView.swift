import AgentPocketCore
import SwiftUI

public struct InboxView: View {
    @StateObject private var viewModel: InboxViewModel
    @StateObject private var contextSnapshotViewModel: ContextSnapshotViewModel
    private let activeConnection: () -> StoredConnection?
    private let language: AppLanguage

    @MainActor public init(
        viewModel: InboxViewModel,
        contextSnapshotViewModel: ContextSnapshotViewModel = ContextSnapshotViewModel(),
        activeConnection: @escaping () -> StoredConnection?
    ) {
        _viewModel = StateObject(wrappedValue: viewModel)
        _contextSnapshotViewModel = StateObject(wrappedValue: contextSnapshotViewModel)
        self.activeConnection = activeConnection
        self.language = AppLanguage.resolved(storedValue: nil)
    }

    public var body: some View {
        ZStack {
            Color(red: 0.045, green: 0.052, blue: 0.052)
                .ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 12) {
                    if let status = viewModel.completedStatus {
                        resultBanner(status)
                    }

                    if viewModel.items.isEmpty {
                        emptyState
                    } else {
                        if showsContextSnapshotPreview {
                            ContextSnapshotPreviewView(viewModel: contextSnapshotViewModel)
                                .padding(14)
                                .background(.black.opacity(0.24), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                                        .stroke(.white.opacity(0.10), lineWidth: 1)
                                )
                        }

                        ForEach(viewModel.items) { item in
                            inboxRow(item)
                        }
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 16)
                .frame(maxWidth: 720)
                .frame(maxWidth: .infinity, alignment: .center)
            }
        }
        .navigationTitle("Inbox")
        .task {
            try? viewModel.reload()
        }
    }

    private var emptyState: some View {
        VStack(alignment: .center, spacing: 10) {
            Image(systemName: "tray")
                .font(.system(size: 30, weight: .semibold))
                .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                .frame(width: 54, height: 54)
            Text(language == .chinese ? "暂时没有待处理项目" : "No Pending Items")
                .font(.headline)
                .foregroundStyle(.white.opacity(0.92))
        }
        .frame(maxWidth: .infinity, minHeight: 220)
        .background(.black.opacity(0.24), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(.white.opacity(0.10), lineWidth: 1)
        )
    }

    private func inboxRow(_ item: KakaInboxItem) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: iconName(for: item))
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                    .frame(width: 30, height: 30)
                    .background(.white.opacity(0.08), in: Circle())
                    .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: 4) {
                    Text(title(for: item))
                        .font(.headline)
                        .foregroundStyle(.white)
                        .lineLimit(2)

                    Text(subtitle(for: item))
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.68))
                        .lineLimit(3)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer(minLength: 8)
            }

            HStack(spacing: 10) {
                Button {
                    let selectedContextSnapshot = contextSnapshotViewModel.selectedSnapshotForSubmission
                    Task {
                        await viewModel.submit(
                            item,
                            connection: activeConnection(),
                            contextSnapshot: selectedContextSnapshot
                        )
                        contextSnapshotViewModel.resetPerTaskConsent()
                    }
                } label: {
                    Label(language == .chinese ? "发送" : "Send", systemImage: "paperplane.fill")
                        .font(.callout.weight(.semibold))
                        .frame(minHeight: 38)
                        .padding(.horizontal, 12)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.black)
                .background(Color(red: 0.55, green: 0.96, blue: 0.89), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .disabled(isSubmitting || viewModel.canSubmit(item) == false)
                .opacity(isSubmitting || viewModel.canSubmit(item) == false ? 0.54 : 1)

                if item.route == .imageIntake {
                    Text("image-intake")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.64))
                }

                Spacer()
            }
        }
        .padding(14)
        .background(.black.opacity(0.24), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(.white.opacity(0.10), lineWidth: 1)
        )
    }

    private func resultBanner(_ status: TaskStatusResponse) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                Text(resultTitle(status))
                    .font(.headline)
                    .foregroundStyle(.white)
                Spacer()
                Button {
                    viewModel.dismissResult()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 13, weight: .bold))
                        .frame(width: 30, height: 30)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.white.opacity(0.78))
                .accessibilityLabel(language == .chinese ? "关闭" : "Close")
            }

            if let summary = resultSummary(status) {
                Text(summary)
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.74))
                    .lineLimit(4)
                    .fixedSize(horizontal: false, vertical: true)
            }

            RecallView(
                sourceTaskID: status.taskID,
                initialSummary: resultSummary(status) ?? resultTitle(status),
                isFramed: false,
                activeConnection: activeConnection
            )
        }
        .padding(14)
        .background(Color(red: 0.10, green: 0.20, blue: 0.18).opacity(0.92), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(Color(red: 0.55, green: 0.96, blue: 0.89).opacity(0.24), lineWidth: 1)
        )
    }

    private var isSubmitting: Bool {
        if case .submitting = viewModel.state {
            return true
        }
        return false
    }

    private var showsContextSnapshotPreview: Bool {
        viewModel.items.contains { $0.route == .universalIntake }
    }

    private func iconName(for item: KakaInboxItem) -> String {
        switch item.kind {
        case .text:
            return "text.alignleft"
        case .url:
            return "link"
        case .image, .screenshot:
            return "photo"
        case .pdf:
            return "doc.richtext"
        }
    }

    private func title(for item: KakaInboxItem) -> String {
        switch item.kind {
        case .text:
            return language == .chinese ? "共享文本" : "Shared Text"
        case .url:
            return language == .chinese ? "共享链接" : "Shared Link"
        case .image:
            return language == .chinese ? "共享图片" : "Shared Image"
        case .screenshot:
            return language == .chinese ? "共享截图" : "Shared Screenshot"
        case .pdf:
            return language == .chinese ? "共享 PDF" : "Shared PDF"
        }
    }

    private func subtitle(for item: KakaInboxItem) -> String {
        item.url
            ?? item.text
            ?? item.fileName
            ?? item.sourceApp
            ?? formattedDate(item.receivedAt)
    }

    private func resultTitle(_ status: TaskStatusResponse) -> String {
        status.intake?.title
            ?? status.imageIntake?.title
            ?? (language == .chinese ? "已完成" : "Completed")
    }

    private func resultSummary(_ status: TaskStatusResponse) -> String? {
        status.intake?.summary
            ?? status.imageIntake?.summary
            ?? status.message
    }

    private func formattedDate(_ date: Date) -> String {
        date.formatted(date: .abbreviated, time: .shortened)
    }
}
