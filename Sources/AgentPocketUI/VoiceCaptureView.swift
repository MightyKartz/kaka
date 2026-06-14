import SwiftUI

public struct VoiceCaptureView: View {
    @ObservedObject private var viewModel: VoiceCaptureViewModel
    private let presentation: VoiceCapturePresentation
    private let onCancel: () -> Void
    private let onSend: (String) -> Void

    public init(
        viewModel: VoiceCaptureViewModel,
        presentation: VoiceCapturePresentation = .defaultDraft,
        onCancel: @escaping () -> Void,
        onSend: @escaping (String) -> Void
    ) {
        self.viewModel = viewModel
        self.presentation = presentation
        self.onCancel = onCancel
        self.onSend = onSend
    }

    public var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                HStack(spacing: 10) {
                    Image(systemName: stateIconName)
                        .font(.system(size: 18, weight: .semibold))
                        .frame(width: 28, height: 28)
                        .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                        .accessibilityHidden(true)

                    Text(localizedStatusText)
                        .font(.headline)
                        .foregroundStyle(.white)
                        .lineLimit(1)
                        .minimumScaleFactor(0.82)

                    Spacer()
                }

                TextEditor(text: $viewModel.editableTranscript)
                    .font(.body)
                    .scrollContentBackground(.hidden)
                    .padding(10)
                    .frame(minHeight: 180)
                    .background(Color.white.opacity(0.10), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(Color.white.opacity(0.12), lineWidth: 1)
                    )
                    .disabled(viewModel.state == .recording || viewModel.state == .transcribing)
                    .accessibilityLabel(presentation.transcriptAccessibilityLabel)

                HStack(spacing: 12) {
                    Button {
                        Task {
                            await viewModel.cancelRecording()
                            onCancel()
                        }
                    } label: {
                        Label(cancelTitle, systemImage: "xmark")
                            .font(.callout.weight(.semibold))
                            .frame(minHeight: 40)
                            .padding(.horizontal, 10)
                    }
                    .buttonStyle(AgentPocketDarkSecondaryButtonStyle())

                    Spacer()

                    Button {
                        Task {
                            await toggleRecording()
                        }
                    } label: {
                        Label(recordButtonTitle, systemImage: recordButtonIconName)
                            .font(.callout.weight(.semibold))
                            .frame(minHeight: 40)
                            .padding(.horizontal, 10)
                    }
                    .buttonStyle(AgentPocketDarkSecondaryButtonStyle())
                    .disabled(viewModel.state == .transcribing)

                    Button {
                        onSend(viewModel.transcript)
                    } label: {
                        Label(presentation.submitTitle, systemImage: presentation.submitSystemImage)
                            .font(.callout.weight(.semibold))
                            .lineLimit(1)
                            .minimumScaleFactor(0.72)
                            .frame(minHeight: 40)
                            .padding(.horizontal, 10)
                    }
                    .buttonStyle(AgentPocketDarkPrimaryButtonStyle())
                    .disabled(viewModel.canSubmit == false)
                }
            }
            .padding(16)
            .background(Color(red: 0.035, green: 0.045, blue: 0.045))
            .foregroundStyle(.white)
            .navigationTitle(presentation.navigationTitle)
            .modifier(VoiceCaptureNavigationChrome(isDark: presentation.prefersDarkNavigationChrome))
            .tint(.white)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(cancelTitle) {
                        Task {
                            await viewModel.cancelRecording()
                            onCancel()
                        }
                    }
                }
            }
        }
    }

    private var stateIconName: String {
        switch viewModel.state {
        case .idle:
            return "mic"
        case .recording:
            return "waveform"
        case .transcribing:
            return "text.magnifyingglass"
        case .ready:
            return "text.bubble"
        case .failed:
            return "exclamationmark.triangle"
        }
    }

    private var recordButtonTitle: String {
        switch (presentation.language, viewModel.state == .recording) {
        case (.chinese, true):
            return "停止"
        case (.chinese, false):
            return "录音"
        case (.english, true):
            return "Stop"
        case (.english, false):
            return "Record"
        }
    }

    private var recordButtonIconName: String {
        viewModel.state == .recording ? "stop.fill" : "mic.fill"
    }

    private var cancelTitle: String {
        presentation.language == .chinese ? "取消" : "Cancel"
    }

    private var localizedStatusText: String {
        guard presentation.language == .chinese else {
            return viewModel.state.statusText
        }

        switch viewModel.state {
        case .idle:
            return "准备录音"
        case .recording:
            return "正在录音"
        case .transcribing:
            return "正在转写"
        case .ready:
            return "请审核转写"
        case .failed(let message):
            return message
        }
    }

    private func toggleRecording() async {
        if viewModel.state == .recording {
            await viewModel.stopRecordingAndTranscribe()
        } else {
            await viewModel.startRecording()
        }
    }
}

private struct VoiceCaptureNavigationChrome: ViewModifier {
    let isDark: Bool

    func body(content: Content) -> some View {
        #if os(iOS)
        content
            .toolbarColorScheme(isDark ? .dark : .light, for: .navigationBar)
            .toolbarBackground(AgentPocketDesignTokens.darkBackground, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
        #else
        content
        #endif
    }
}
