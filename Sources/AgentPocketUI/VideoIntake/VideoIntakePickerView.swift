import AgentPocketCore
import SwiftUI

public struct VideoIntakePickerView: View {
    public let payloadDirectory: URL
    public let onDraft: (KakaInboxItem) -> Void
    public let onCancel: () -> Void

    public init(
        payloadDirectory: URL,
        onDraft: @escaping (KakaInboxItem) -> Void,
        onCancel: @escaping () -> Void
    ) {
        self.payloadDirectory = payloadDirectory
        self.onDraft = onDraft
        self.onCancel = onCancel
    }

    public var body: some View {
        #if os(iOS) && canImport(PhotosUI) && canImport(AVKit) && canImport(UIKit)
        VideoIntakePickerContent(
            payloadDirectory: payloadDirectory,
            onDraft: onDraft,
            onCancel: onCancel
        )
        #else
        ContentUnavailableView(
            "Video Intake Unavailable",
            systemImage: "video",
            description: Text("Open Pocket Agent on iPhone to choose or record a short video.")
        )
        #endif
    }
}

#if os(iOS) && canImport(PhotosUI) && canImport(AVKit) && canImport(UIKit)
import AVKit
import PhotosUI
import UniformTypeIdentifiers
import UIKit

private struct VideoIntakePickerContent: View {
    let payloadDirectory: URL
    let onDraft: (KakaInboxItem) -> Void
    let onCancel: () -> Void

    @State private var selectedVideo: PhotosPickerItem?
    @State private var sourceURL: URL?
    @State private var fileName = "video.mov"
    @State private var mimeType = "video/quicktime"
    @State private var prompt = ""
    @State private var errorMessage: String?
    @State private var isLoading = false
    @State private var isShowingCamera = false

    var body: some View {
        NavigationStack {
            ZStack {
                AgentPocketDesignTokens.darkBackground
                    .ignoresSafeArea()

                ScrollView(showsIndicators: false) {
                    VStack(alignment: .leading, spacing: 14) {
                        preview
                        sourceCard
                        promptEditor
                        sendButton
                        Text(copy.limitText)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.48))
                            .frame(maxWidth: .infinity, alignment: .center)
                    }
                    .padding(16)
                    .frame(maxWidth: 620)
                    .frame(maxWidth: .infinity)
                }
            }
            .navigationTitle(copy.navigationTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(copy.closeTitle, action: onCancel)
                }
            }
            .onChange(of: selectedVideo) { _, item in
                Task { await loadSelectedVideo(item) }
            }
            .sheet(isPresented: $isShowingCamera) {
                VideoCameraRecorderView { url in
                    receiveVideo(url: url, suggestedFileName: url.lastPathComponent, mimeType: "video/quicktime")
                    isShowingCamera = false
                } onCancel: {
                    isShowingCamera = false
                }
            }
        }
    }

    @ViewBuilder
    private var preview: some View {
        if let sourceURL {
            VideoPlayer(player: AVPlayer(url: sourceURL))
                .frame(height: 250)
                .clipShape(RoundedRectangle(cornerRadius: AgentPocketDesignTokens.mediaRadius, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: AgentPocketDesignTokens.mediaRadius, style: .continuous)
                        .stroke(Color.white.opacity(0.12), lineWidth: 1)
                )
        } else {
            VStack(spacing: 16) {
                Image(systemName: "video.badge.plus")
                    .font(.system(size: 36, weight: .semibold))
                    .foregroundStyle(AgentPocketDesignTokens.accent)
                Text(copy.emptyPrompt)
                    .font(.callout)
                    .foregroundStyle(.white.opacity(0.72))
                    .multilineTextAlignment(.center)
                    .lineLimit(3)
            }
            .frame(maxWidth: .infinity, minHeight: 250)
            .background(AgentPocketDesignTokens.darkPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.mediaRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: AgentPocketDesignTokens.mediaRadius, style: .continuous)
                    .stroke(AgentPocketDesignTokens.darkStroke, lineWidth: 1)
            )
        }
    }

    private var sourceCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                Image(systemName: "plus.rectangle.on.folder")
                    .foregroundStyle(AgentPocketDesignTokens.accent)
                    .frame(width: 28, height: 28)
                VStack(alignment: .leading, spacing: 2) {
                    Text(fileName)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.white)
                        .lineLimit(1)
                        .minimumScaleFactor(0.78)
                    Text(sourceURL == nil ? copy.noSelection : copy.readyForReview(mimeType: mimeType))
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.58))
                        .lineLimit(2)
                }
                Spacer()
                if sourceURL != nil {
                    Image(systemName: "checkmark")
                        .foregroundStyle(AgentPocketDesignTokens.accent)
                }
            }

            HStack(spacing: 10) {
                PhotosPicker(selection: $selectedVideo, matching: .videos) {
                    Label(copy.chooseVideoTitle, systemImage: "photo.on.rectangle")
                        .font(.callout.weight(.semibold))
                        .frame(minHeight: 38)
                        .padding(.horizontal, 12)
                }
                .buttonStyle(AgentPocketDarkSecondaryButtonStyle())

                Button {
                    isShowingCamera = true
                } label: {
                    Label(copy.recordTitle, systemImage: "video")
                        .font(.callout.weight(.semibold))
                        .frame(minHeight: 38)
                        .padding(.horizontal, 12)
                }
                .buttonStyle(AgentPocketDarkSecondaryButtonStyle())
                .disabled(UIImagePickerController.isSourceTypeAvailable(.camera) == false)
            }

            if isLoading {
                ProgressView(copy.preparingTitle)
                    .tint(AgentPocketDesignTokens.accent)
            }

            if let errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundStyle(Color(red: 1.0, green: 0.58, blue: 0.48))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(12)
        .background(AgentPocketDesignTokens.darkPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                .stroke(AgentPocketDesignTokens.darkStroke, lineWidth: 1)
        )
    }

    private var promptEditor: some View {
        TextField(copy.promptPlaceholder, text: $prompt, axis: .vertical)
            .lineLimit(3, reservesSpace: true)
            .font(.callout)
            .padding(12)
            .foregroundStyle(.white)
            .background(AgentPocketDesignTokens.darkPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                    .stroke(AgentPocketDesignTokens.darkStroke, lineWidth: 1)
            )
    }

    private var sendButton: some View {
        Button {
            makeDraft()
        } label: {
            Label(copy.sendTitle, systemImage: "paperplane.fill")
                .font(.callout.weight(.semibold))
                .frame(maxWidth: .infinity, minHeight: 46)
        }
        .buttonStyle(AgentPocketDarkPrimaryButtonStyle())
        .disabled(sourceURL == nil || isLoading)
        .opacity(sourceURL == nil || isLoading ? 0.54 : 1)
    }

    private func loadSelectedVideo(_ item: PhotosPickerItem?) async {
        guard let item else {
            return
        }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            guard let data = try await item.loadTransferable(type: Data.self) else {
                errorMessage = copy.couldNotRead
                return
            }
            let type = item.supportedContentTypes.first(where: { $0.conforms(to: .movie) })
                ?? item.supportedContentTypes.first
                ?? .quickTimeMovie
            let ext = type.preferredFilenameExtension ?? "mov"
            let temporaryURL = FileManager.default.temporaryDirectory
                .appendingPathComponent("\(UUID().uuidString).\(ext)")
            try data.write(to: temporaryURL, options: .atomic)
            receiveVideo(
                url: temporaryURL,
                suggestedFileName: "video_\(Date().formatted(.iso8601.year().month().day().time(includingFractionalSeconds: false))).\(ext)",
                mimeType: type.preferredMIMEType ?? "video/quicktime"
            )
        } catch {
            errorMessage = copy.couldNotPrepare
        }
    }

    private func receiveVideo(url: URL, suggestedFileName: String, mimeType: String) {
        sourceURL = url
        fileName = suggestedFileName.isEmpty ? url.lastPathComponent : suggestedFileName
        self.mimeType = mimeType
        errorMessage = nil
    }

    private func makeDraft() {
        guard let sourceURL else {
            return
        }
        do {
            let item = try VideoInboxBuilder(payloadDirectory: payloadDirectory).makeInboxItem(
                sourceURL: sourceURL,
                fileName: fileName,
                mimeType: mimeType
            )
            let trimmedPrompt = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
            if trimmedPrompt.isEmpty {
                onDraft(item)
            } else {
                onDraft(
                    KakaInboxItem(
                        id: item.id,
                        kind: item.kind,
                        receivedAt: item.receivedAt,
                        sourceApp: item.sourceApp,
                        sourceSurface: item.sourceSurface,
                        note: trimmedPrompt,
                        locale: item.locale,
                        preferredProfileID: item.preferredProfileID,
                        text: item.text,
                        url: item.url,
                        fileName: item.fileName,
                        mimeType: item.mimeType,
                        relativeFilePath: item.relativeFilePath,
                        route: item.route
                    )
                )
            }
        } catch VideoIntakePolicy.ValidationError.exceedsFirstReleaseLimit {
            errorMessage = copy.tooLarge
        } catch {
            errorMessage = copy.couldNotCreateDraft
        }
    }

    private var copy: VideoIntakeCopy {
        VideoIntakeCopy(language: AppLanguage.resolved(storedValue: nil))
    }
}

private struct VideoIntakeCopy {
    let language: AppLanguage

    var navigationTitle: String {
        language == .chinese ? "视频" : "Video"
    }

    var closeTitle: String {
        language == .chinese ? "关闭" : "Close"
    }

    var emptyPrompt: String {
        language == .chinese
            ? "选择或录制一段短视频，审核后再发送给本机智能体。"
            : "Choose or record a short video before sending it to your local agent."
    }

    var noSelection: String {
        language == .chinese ? "尚未选择视频" : "No video selected"
    }

    var chooseVideoTitle: String {
        language == .chinese ? "选择视频" : "Choose Video"
    }

    var recordTitle: String {
        language == .chinese ? "录制" : "Record"
    }

    var preparingTitle: String {
        language == .chinese ? "正在准备视频" : "Preparing video"
    }

    var promptPlaceholder: String {
        language == .chinese ? "添加说明（可选）" : "Add a prompt (optional)"
    }

    var sendTitle: String {
        language == .chinese ? "发送给本机智能体" : "Send to Local Agent"
    }

    var limitText: String {
        language == .chinese ? "最大 100 MB" : "Max 100 MB"
    }

    var couldNotRead: String {
        language == .chinese ? "无法读取这个视频。" : "Could not read that video."
    }

    var couldNotPrepare: String {
        language == .chinese ? "无法准备这个视频。" : "Could not prepare that video."
    }

    var tooLarge: String {
        language == .chinese ? "请选择 100 MB 以下的视频。" : "Choose a video under 100 MB for this first release."
    }

    var couldNotCreateDraft: String {
        language == .chinese ? "无法创建视频收件箱草稿。" : "Could not create a video Inbox draft."
    }

    func readyForReview(mimeType: String) -> String {
        language == .chinese ? "\(mimeType) 已准备好进入收件箱审核" : "\(mimeType) ready for Inbox review"
    }
}

private struct VideoCameraRecorderView: UIViewControllerRepresentable {
    let onVideo: (URL) -> Void
    let onCancel: () -> Void

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.mediaTypes = [UTType.movie.identifier]
        picker.videoMaximumDuration = 90
        picker.videoQuality = .typeMedium
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onVideo: onVideo, onCancel: onCancel)
    }

    final class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let onVideo: (URL) -> Void
        let onCancel: () -> Void

        init(onVideo: @escaping (URL) -> Void, onCancel: @escaping () -> Void) {
            self.onVideo = onVideo
            self.onCancel = onCancel
        }

        func imagePickerController(
            _ picker: UIImagePickerController,
            didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]
        ) {
            let url = info[.mediaURL] as? URL
            picker.dismiss(animated: true) {
                if let url {
                    self.onVideo(url)
                } else {
                    self.onCancel()
                }
            }
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            picker.dismiss(animated: true) {
                self.onCancel()
            }
        }
    }
}
#endif
