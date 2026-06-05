import SwiftUI

public struct VoiceCaptureView: View {
    @ObservedObject private var viewModel: VoiceCaptureViewModel
    private let onCancel: () -> Void
    private let onSend: (String) -> Void

    public init(
        viewModel: VoiceCaptureViewModel,
        onCancel: @escaping () -> Void,
        onSend: @escaping (String) -> Void
    ) {
        self.viewModel = viewModel
        self.onCancel = onCancel
        self.onSend = onSend
    }

    public var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
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
                    .accessibilityLabel("Voice transcript")

                HStack(spacing: 12) {
                    Button("Cancel") {
                        viewModel.cancel()
                        onCancel()
                    }
                    .buttonStyle(.bordered)

                    Spacer()

                    Button("Send") {
                        onSend(viewModel.transcript)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(viewModel.canSubmit == false)
                }
            }
            .padding(16)
            .background(Color(red: 0.035, green: 0.045, blue: 0.045))
            .foregroundStyle(.white)
            .navigationTitle("Voice Draft")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        viewModel.cancel()
                        onCancel()
                    }
                }
            }
            .onAppear {
                if viewModel.state == .idle {
                    viewModel.markTranscriptReady("")
                }
            }
        }
    }
}
