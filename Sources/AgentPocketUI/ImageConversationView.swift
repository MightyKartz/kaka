import AgentPocketCore
import SwiftUI
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

public struct ImageConversationView: View {
    @StateObject private var viewModel: ImageConversationViewModel
    private let activeConnection: () -> StoredConnection?
    private let language: AppLanguage

    public init(
        intakeStatus: TaskStatusResponse,
        originalAsset: DownloadedAsset?,
        preparedUpload: PreparedImageUpload,
        activeConnection: @escaping () -> StoredConnection?,
        skillExecutor: any ImageSkillExecuting = MobileBridgeImageSkillSubmitter()
    ) {
        _viewModel = StateObject(wrappedValue: ImageConversationViewModel(
            intakeStatus: intakeStatus,
            originalAsset: originalAsset,
            preparedUpload: preparedUpload,
            skillExecutor: skillExecutor
        ))
        self.activeConnection = activeConnection
        self.language = AppLanguage.resolved(storedValue: nil)
    }

    public var body: some View {
        ZStack {
            Color(red: 0.035, green: 0.045, blue: 0.045)
                .ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 16) {
                    sourceImage
                    suggestionStrip
                    messageList
                }
                .padding(.horizontal, 16)
                .padding(.top, 16)
                .padding(.bottom, 96)
                .frame(maxWidth: 720)
                .frame(maxWidth: .infinity)
            }
        }
        .safeAreaInset(edge: .bottom) {
            promptComposer
        }
        .navigationTitle("Kaka")
    }

    private var sourceImage: some View {
        ConversationSourceImage(asset: viewModel.originalAsset)
            .frame(height: 260)
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(.white.opacity(0.12), lineWidth: 1)
            )
    }

    private var suggestionStrip: some View {
        LazyVGrid(
            columns: [GridItem(.adaptive(minimum: 106, maximum: 180), spacing: 10)],
            alignment: .leading,
            spacing: 10
        ) {
            ForEach(viewModel.suggestions) { suggestion in
                KakaSkillSuggestionView(suggestion: suggestion) {
                    Task {
                        await viewModel.executeSuggestion(suggestion, connection: activeConnection())
                    }
                }
                .disabled(viewModel.isExecuting)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding(.vertical, 2)
    }

    private var messageList: some View {
        VStack(alignment: .leading, spacing: 10) {
            ForEach(viewModel.messages) { message in
                messageBubble(message)
            }
        }
    }

    private func messageBubble(_ message: KakaImageMessage) -> some View {
        HStack {
            if message.role == .user {
                Spacer(minLength: 42)
            }
            VStack(alignment: .leading, spacing: 6) {
                Text(message.text)
                    .font(.body)
                    .foregroundStyle(.white.opacity(0.9))
                    .multilineTextAlignment(.leading)
                if let result = message.result {
                    ConversationResultDetails(
                        status: result,
                        originalAsset: viewModel.originalAsset,
                        activeConnection: activeConnection,
                        language: language
                    )
                }
            }
            .padding(12)
            .background(messageBackground(message), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(.white.opacity(0.08), lineWidth: 1)
            )
            if message.role != .user {
                Spacer(minLength: 42)
            }
        }
    }

    private func messageBackground(_ message: KakaImageMessage) -> Color {
        switch message.role {
        case .assistant, .result:
            return Color.white.opacity(0.08)
        case .user:
            return Color(red: 0.15, green: 0.34, blue: 0.32).opacity(0.82)
        }
    }

    private var promptComposer: some View {
        HStack(spacing: 10) {
            TextField(promptPlaceholder, text: $viewModel.prompt)
                .textFieldStyle(.plain)
                .font(.body)
                .foregroundStyle(.white)
                .padding(.horizontal, 12)
                .frame(minHeight: 44)
                .background(.white.opacity(0.10), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(.white.opacity(0.10), lineWidth: 1)
                )

            Button {
                viewModel.reportVoiceUnavailable()
            } label: {
                Image(systemName: "mic.fill")
                    .font(.system(size: 17, weight: .semibold))
                    .frame(width: 44, height: 44)
            }
            .buttonStyle(.plain)
            .foregroundStyle(.white.opacity(0.72))
            .accessibilityLabel(language == .chinese ? "语音输入" : "Voice input")
            .accessibilityHint(voiceHint)

            Button {
                Task {
                    await viewModel.submitPrompt(connection: activeConnection())
                }
            } label: {
                Image(systemName: "paperplane.fill")
                    .font(.system(size: 17, weight: .semibold))
                    .frame(width: 44, height: 44)
                    .background(Color(red: 0.55, green: 0.96, blue: 0.89), in: Circle())
                    .foregroundStyle(.black)
            }
            .buttonStyle(.plain)
            .disabled(viewModel.isExecuting || canSubmitPrompt == false)
            .opacity(canSubmitPrompt ? 1 : 0.46)
            .accessibilityLabel(language == .chinese ? "发送" : "Send")
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color(red: 0.035, green: 0.045, blue: 0.045))
        .overlay(alignment: .top) {
            Rectangle()
                .fill(.white.opacity(0.08))
                .frame(height: 1)
        }
    }

    private var canSubmitPrompt: Bool {
        viewModel.prompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
    }

    private var promptPlaceholder: String {
        language == .chinese ? "告诉 Kaka 你想怎么处理这张图片" : "Tell Kaka what to do with this image"
    }

    private var voiceHint: String {
        language == .chinese ? "语音输入将在下一阶段接入。" : "Voice input will be connected in the next phase."
    }
}

private struct ConversationResultDetails: View {
    let status: TaskStatusResponse
    let originalAsset: DownloadedAsset?
    let activeConnection: () -> StoredConnection?
    let language: AppLanguage

    private var presentation: ImageConversationResultPresentation {
        ImageConversationResultPresentation(status: status, language: language)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Divider()
                .overlay(.white.opacity(0.12))

            HStack(alignment: .top, spacing: 8) {
                Image(systemName: presentation.systemImage)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                    .frame(width: 24, height: 24)
                    .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: 3) {
                    Text(presentation.title)
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(.white)

                    if let subtitle = presentation.subtitle {
                        Text(subtitle)
                            .font(.caption.weight(.medium))
                            .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                    }
                }
            }

            if let bodyText = presentation.bodyText {
                Text(bodyText)
                    .font(.callout)
                    .foregroundStyle(.white.opacity(0.78))
                    .lineSpacing(3)
                    .lineLimit(8)
                    .fixedSize(horizontal: false, vertical: true)
            }

            ForEach(Array(presentation.detailRows.enumerated()), id: \.offset) { _, row in
                VStack(alignment: .leading, spacing: 2) {
                    Text(row.title)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.62))
                    Text(row.value)
                        .font(.callout.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.86))
                        .lineLimit(3)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            if let actionTitle = presentation.actionTitle {
                NavigationLink {
                    destination
                } label: {
                    Label(actionTitle, systemImage: "arrow.forward.circle.fill")
                        .font(.callout.weight(.semibold))
                        .foregroundStyle(.black)
                        .frame(maxWidth: .infinity, minHeight: 42)
                        .background(Color(red: 0.55, green: 0.96, blue: 0.89), in: Capsule())
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("conversationResultActionButton")
            }
        }
    }

    @ViewBuilder
    private var destination: some View {
        if status.variants?.isEmpty == false {
            ResultGalleryView(
                status: status,
                activeConnection: activeConnection,
                initialOriginalAsset: originalAsset
            )
        } else if status.vision != nil {
            VisionResultView(
                status: status,
                originalAsset: originalAsset
            )
        } else {
            Text(presentation.title)
        }
    }
}

private struct ConversationSourceImage: View {
    let asset: DownloadedAsset?

    var body: some View {
        ZStack {
            if let image = renderedImage {
                image
                    .resizable()
                    .scaledToFill()
                    .accessibilityHidden(true)
            } else {
                LinearGradient(
                    colors: [
                        Color(red: 0.20, green: 0.27, blue: 0.27),
                        Color(red: 0.07, green: 0.09, blue: 0.09)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                Image(systemName: "photo")
                    .font(.system(size: 34, weight: .medium))
                    .foregroundStyle(.white.opacity(0.42))
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var renderedImage: Image? {
        guard let asset else {
            return nil
        }
        #if canImport(UIKit)
        guard let image = UIImage(data: asset.data) else {
            return nil
        }
        return Image(uiImage: image)
        #elseif canImport(AppKit)
        guard let image = NSImage(data: asset.data) else {
            return nil
        }
        return Image(nsImage: image)
        #else
        return nil
        #endif
    }
}
