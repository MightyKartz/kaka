import AgentPocketCore
import SwiftUI

public struct RecallView: View {
    @StateObject private var viewModel: RecallActionViewModel
    @State private var summaryText: String

    private let sourceTaskID: String?
    private let sourceInboxItemID: UUID?
    private let activeConnection: () -> StoredConnection?
    private let isFramed: Bool

    public init(
        viewModel: RecallActionViewModel = RecallActionViewModel(),
        sourceTaskID: String? = nil,
        sourceInboxItemID: UUID? = nil,
        initialSummary: String = "",
        isFramed: Bool = true,
        activeConnection: @escaping () -> StoredConnection?
    ) {
        _viewModel = StateObject(wrappedValue: viewModel)
        _summaryText = State(initialValue: initialSummary)
        self.sourceTaskID = sourceTaskID
        self.sourceInboxItemID = sourceInboxItemID
        self.activeConnection = activeConnection
        self.isFramed = isFramed
    }

    public var body: some View {
        if isFramed {
            content
                .padding(14)
                .background(.black.opacity(0.24), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(.white.opacity(0.10), lineWidth: 1)
                )
        } else {
            content
        }
    }

    private var content: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                    .frame(width: 32, height: 32)
                    .background(.white.opacity(0.08), in: Circle())
                    .accessibilityHidden(true)

                Text("Recall")
                    .font(.headline)
                    .foregroundStyle(.white)

                Spacer()
            }

            TextField("Visible summary", text: $summaryText, axis: .vertical)
                .textFieldStyle(.plain)
                .font(.callout)
                .foregroundStyle(.white)
                .lineLimit(2...4)
                .padding(10)
                .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(.white.opacity(0.10), lineWidth: 1)
                )

            HStack(spacing: 8) {
                actionButton(title: "Remember", systemImage: "bookmark.fill", action: .remember)
                actionButton(title: "Use once", systemImage: "bolt.fill", action: .useOnce)
                actionButton(title: "Forget", systemImage: "trash.fill", action: .forget)
            }

            stateContent
        }
    }

    private func actionButton(title: String, systemImage: String, action: RecallAction) -> some View {
        Button {
            Task {
                await viewModel.perform(
                    action,
                    sourceTaskID: sourceTaskID,
                    sourceInboxItemID: sourceInboxItemID,
                    userVisibleSummary: summaryText,
                    connection: activeConnection()
                )
            }
        } label: {
            Label(title, systemImage: systemImage)
                .font(.caption.weight(.semibold))
                .lineLimit(1)
                .frame(maxWidth: .infinity, minHeight: 34)
        }
        .buttonStyle(.plain)
        .foregroundStyle(action == .forget ? .white : .black)
        .background(actionBackground(action), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .disabled(summaryText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        .opacity(summaryText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? 0.52 : 1)
    }

    @ViewBuilder
    private var stateContent: some View {
        switch viewModel.state {
        case .idle:
            EmptyView()
        case .confirming(let confirmation):
            VStack(alignment: .leading, spacing: 10) {
                Text(confirmation.action == .forget ? "Confirm forget" : "Confirm remember")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.white)
                Text(confirmation.userVisibleSummary)
                    .font(.footnote)
                    .foregroundStyle(.white.opacity(0.72))
                    .fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 8) {
                    Button {
                        Task {
                            await viewModel.confirmPendingAction(connection: activeConnection())
                        }
                    } label: {
                        Label("Confirm", systemImage: "checkmark")
                            .font(.caption.weight(.bold))
                            .frame(minHeight: 32)
                            .padding(.horizontal, 10)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.black)
                    .background(Color(red: 0.55, green: 0.96, blue: 0.89), in: RoundedRectangle(cornerRadius: 8, style: .continuous))

                    Button {
                        viewModel.cancelConfirmation()
                    } label: {
                        Label("Cancel", systemImage: "xmark")
                            .font(.caption.weight(.bold))
                            .frame(minHeight: 32)
                            .padding(.horizontal, 10)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.white.opacity(0.82))
                    .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
            }
            .padding(10)
            .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        case .submitting:
            ProgressView()
                .tint(Color(red: 0.55, green: 0.96, blue: 0.89))
                .frame(maxWidth: .infinity, alignment: .leading)
        case .succeeded(let response):
            Label(response.status, systemImage: "checkmark.circle.fill")
                .font(.footnote.weight(.semibold))
                .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
        case .failed(let message):
            Label(message, systemImage: "exclamationmark.triangle.fill")
                .font(.footnote.weight(.semibold))
                .foregroundStyle(Color(red: 1.0, green: 0.55, blue: 0.45))
        }
    }

    private func actionBackground(_ action: RecallAction) -> Color {
        switch action {
        case .remember:
            return Color(red: 0.55, green: 0.96, blue: 0.89)
        case .useOnce:
            return Color(red: 0.85, green: 0.76, blue: 1.0)
        case .forget:
            return Color(red: 0.72, green: 0.18, blue: 0.18)
        }
    }
}
