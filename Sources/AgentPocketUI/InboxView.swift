import AgentPocketCore
import SwiftUI

public struct InboxView: View {
    private enum VoiceCaptureMode: Identifiable {
        case draft
        case instruction(KakaInboxItem)

        var id: String {
            switch self {
            case .draft:
                return "draft"
            case .instruction(let item):
                return "instruction-\(item.id.uuidString)"
            }
        }
    }

    @StateObject private var viewModel: InboxViewModel
    @StateObject private var contextSnapshotViewModel: ContextSnapshotViewModel
    @StateObject private var voiceCaptureViewModel: VoiceCaptureViewModel
    @State private var voiceCaptureMode: VoiceCaptureMode?
    @State private var isFileImporterPresented = false
    @State private var pendingDiscardItem: KakaInboxItem?
    @State private var expandedReviewItemIDs: Set<UUID> = []
    private let clipboardReader: any ClipboardCourierReading
    private let activeConnection: () -> StoredConnection?
    private let language: AppLanguage

    @MainActor public init(
        viewModel: InboxViewModel,
        contextSnapshotViewModel: ContextSnapshotViewModel = ContextSnapshotViewModel(),
        voiceTranscriber: (any VoiceRecordingTranscribing)? = VoiceTranscriberFactory.makeDefault(),
        clipboardReader: any ClipboardCourierReading = SystemClipboardCourierReader(),
        activeConnection: @escaping () -> StoredConnection?
    ) {
        _viewModel = StateObject(wrappedValue: viewModel)
        _contextSnapshotViewModel = StateObject(wrappedValue: contextSnapshotViewModel)
        _voiceCaptureViewModel = StateObject(wrappedValue: VoiceCaptureViewModel(transcriber: voiceTranscriber))
        self.clipboardReader = clipboardReader
        self.activeConnection = activeConnection
        self.language = AppLanguage.resolved(storedValue: nil)
    }

    public var body: some View {
        ZStack {
            AgentPocketDesignTokens.lightCanvas
                .ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 12) {
                    if let status = viewModel.completedStatus {
                        resultBanner(status, context: viewModel.completedSubmissionContext)
                    }

                    if let feedback = InboxActionFeedbackPresentation(
                        state: viewModel.state,
                        progressText: viewModel.progressText,
                        language: language
                    ) {
                        feedbackBanner(feedback)
                    }

                    inboxActions

                    if viewModel.items.isEmpty {
                        emptyState
                    } else {
                        if showsContextSnapshotPreview {
                            ContextSnapshotPreviewView(viewModel: contextSnapshotViewModel)
                                .padding(14)
                                .background(AgentPocketDesignTokens.lightPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
                                .overlay(
                                    RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                                        .stroke(AgentPocketDesignTokens.lightBorder, lineWidth: 1)
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
        .navigationTitle(language == .chinese ? "收件箱" : "Inbox")
        .sheet(item: $voiceCaptureMode) { mode in
            VoiceCaptureView(
                viewModel: voiceCaptureViewModel,
                presentation: voiceCapturePresentation(for: mode),
                onCancel: {
                    voiceCaptureMode = nil
                    voiceCaptureViewModel.reset()
                },
                onSend: { transcript in
                    if saveVoiceCapture(transcript, mode: mode) != nil {
                        voiceCaptureViewModel.reset()
                        voiceCaptureMode = nil
                    }
                }
            )
            .presentationDetents([.medium, .large])
        }
        .fileImporter(
            isPresented: $isFileImporterPresented,
            allowedContentTypes: InboxFileImporter.supportedContentTypes,
            allowsMultipleSelection: false
        ) { result in
            if case .success(let urls) = result,
               let url = urls.first {
                _ = viewModel.importFile(from: url)
            }
        }
        .confirmationDialog(
            discardConfirmationTitle,
            isPresented: discardConfirmationBinding,
            titleVisibility: .visible
        ) {
            if let item = pendingDiscardItem {
                Button(language == .chinese ? "丢弃" : "Discard", role: .destructive) {
                    guard isSubmitting == false,
                          viewModel.items.contains(where: { $0.id == item.id }) else {
                        pendingDiscardItem = nil
                        return
                    }
                    _ = viewModel.discardPendingItem(id: item.id)
                    pendingDiscardItem = nil
                }
            }
            Button(language == .chinese ? "取消" : "Cancel", role: .cancel) {
                pendingDiscardItem = nil
            }
        } message: {
            Text(discardConfirmationMessage)
        }
        .task {
            try? viewModel.reload()
        }
    }

    private var inboxActions: some View {
        HStack(spacing: 10) {
            Button {
                voiceCaptureViewModel.reset()
                voiceCaptureMode = .draft
            } label: {
                Label(language == .chinese ? "语音草稿" : "Voice Draft", systemImage: "mic.fill")
                    .font(.callout.weight(.semibold))
                    .frame(minHeight: 38)
                    .padding(.horizontal, 12)
            }
            .buttonStyle(AgentPocketLightPrimaryButtonStyle())
            .accessibilityHint(language == .chinese ? "录音并转写为收件箱草稿。" : "Record and transcribe a pending inbox draft.")

            Button {
                _ = viewModel.importClipboard(reader: clipboardReader)
            } label: {
                Label(language == .chinese ? "粘贴" : "Paste", systemImage: "doc.on.clipboard")
                    .font(.callout.weight(.semibold))
                    .frame(minHeight: 38)
                    .padding(.horizontal, 12)
            }
            .buttonStyle(AgentPocketLightSecondaryButtonStyle())
            .disabled(isSubmitting)
            .opacity(isSubmitting ? 0.54 : 1)
            .accessibilityHint(language == .chinese ? "从剪贴板导入文本或链接为待发送项目。" : "Import clipboard text or a link as a pending inbox item.")

            Button {
                isFileImporterPresented = true
            } label: {
                Label(language == .chinese ? "文件" : "Files", systemImage: "folder")
                    .font(.callout.weight(.semibold))
                    .frame(minHeight: 38)
                    .padding(.horizontal, 12)
            }
            .buttonStyle(AgentPocketLightSecondaryButtonStyle())
            .disabled(isSubmitting)
            .opacity(isSubmitting ? 0.54 : 1)
            .accessibilityHint(language == .chinese ? "从文件导入 PDF 或图片为待发送项目。" : "Import a PDF or image as a pending inbox item.")

            Spacer()
        }
    }

    private var emptyState: some View {
        VStack(alignment: .center, spacing: 10) {
            Image(systemName: "tray")
                .font(.system(size: 30, weight: .semibold))
                .foregroundStyle(AgentPocketDesignTokens.accent)
                .frame(width: 54, height: 54)
            Text(language == .chinese ? "暂时没有待处理项目" : "No Pending Items")
                .font(.headline)
                .foregroundStyle(AgentPocketDesignTokens.ink)
        }
        .frame(maxWidth: .infinity, minHeight: 220)
        .background(AgentPocketDesignTokens.lightPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                .stroke(AgentPocketDesignTokens.lightBorder, lineWidth: 1)
        )
    }

    private func inboxRow(_ item: KakaInboxItem) -> some View {
        let instructionPresentation = InboxInstructionPresentation(item: item, language: language)
        let reviewPresentation = InboxPendingItemReviewPresentation(
            item: item,
            contextIncluded: item.route == .universalIntake && contextSnapshotViewModel.includeContext,
            language: language
        )
        let isReviewExpanded = expandedReviewItemIDs.contains(item.id)

        return VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: iconName(for: item))
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(AgentPocketDesignTokens.accent)
                    .frame(width: 30, height: 30)
                    .background(AgentPocketDesignTokens.accent.opacity(0.20), in: Circle())
                    .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: 4) {
                    Text(title(for: item))
                        .font(.headline)
                        .foregroundStyle(AgentPocketDesignTokens.ink)
                        .lineLimit(2)

                    Text(subtitle(for: item))
                        .font(.subheadline)
                        .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                        .lineLimit(3)
                        .fixedSize(horizontal: false, vertical: true)

                    if let noteTitle = instructionPresentation.noteTitle,
                       let noteText = instructionPresentation.noteText {
                        VStack(alignment: .leading, spacing: 3) {
                            Text(noteTitle)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(AgentPocketDesignTokens.accent.opacity(0.88))
                            Text(noteText)
                                .font(.caption)
                                .foregroundStyle(AgentPocketDesignTokens.accent.opacity(0.86))
                                .lineLimit(2)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }

                Spacer(minLength: 8)
            }

            if let submitPreviewText = instructionPresentation.submitPreviewText {
                Text(submitPreviewText)
                    .font(.caption.weight(.medium))
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if instructionPresentation.templates.isEmpty == false {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(instructionPresentation.templates) { template in
                            Button {
                                _ = viewModel.applyInstructionTemplate(template.template, for: item.id, language: language)
                            } label: {
                                Label(template.title, systemImage: template.systemImage)
                                    .font(.caption.weight(.semibold))
                                    .frame(minHeight: 32)
                                    .padding(.horizontal, 10)
                            }
                            .buttonStyle(AgentPocketLightSecondaryButtonStyle())
                            .disabled(isSubmitting)
                            .opacity(isSubmitting ? 0.54 : 1)
                        }
                    }
                }
                .accessibilityLabel(language == .chinese ? "常用指令模板" : "Instruction templates")
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    if let voiceActionTitle = instructionPresentation.voiceActionTitle {
                        Button {
                            beginVoiceInstruction(for: item)
                        } label: {
                            Label(voiceActionTitle, systemImage: "mic.badge.plus")
                                .font(.callout.weight(.semibold))
                                .lineLimit(1)
                                .frame(minHeight: 38)
                                .padding(.horizontal, 12)
                        }
                        .buttonStyle(AgentPocketLightSecondaryButtonStyle())
                        .disabled(isSubmitting)
                        .opacity(isSubmitting ? 0.54 : 1)
                        .accessibilityHint(language == .chinese ? "为此收件箱项目添加或编辑语音指令。" : "Add or edit the voice instruction for this inbox item.")
                    }

                    if let clearActionTitle = instructionPresentation.clearActionTitle {
                        Button {
                            _ = viewModel.clearVoiceInstruction(for: item.id)
                        } label: {
                            Label(clearActionTitle, systemImage: "xmark.circle")
                                .font(.callout.weight(.semibold))
                                .lineLimit(1)
                                .frame(minHeight: 38)
                                .padding(.horizontal, 12)
                        }
                        .buttonStyle(AgentPocketLightSecondaryButtonStyle())
                        .disabled(isSubmitting)
                        .opacity(isSubmitting ? 0.54 : 1)
                        .accessibilityHint(language == .chinese ? "清除这条发送指令。" : "Clear the instruction before sending.")
                    }

                    Button {
                        toggleReviewDetails(for: item.id)
                    } label: {
                        Label(reviewPresentation.actionTitle(isExpanded: isReviewExpanded), systemImage: "info.circle")
                            .font(.callout.weight(.semibold))
                            .lineLimit(1)
                            .frame(minHeight: 38)
                            .padding(.horizontal, 12)
                    }
                    .buttonStyle(AgentPocketLightSecondaryButtonStyle())
                    .disabled(isSubmitting)
                    .opacity(isSubmitting ? 0.54 : 1)
                    .accessibilityHint(language == .chinese ? "查看这个待发送项目的本地详情。" : "Review local details for this pending item.")

                    Button {
                        pendingDiscardItem = item
                    } label: {
                        Label(language == .chinese ? "丢弃" : "Discard", systemImage: "trash")
                            .font(.callout.weight(.semibold))
                            .lineLimit(1)
                            .frame(minHeight: 38)
                            .padding(.horizontal, 12)
                    }
                    .buttonStyle(AgentPocketLightSecondaryButtonStyle())
                    .disabled(isSubmitting)
                    .opacity(isSubmitting ? 0.54 : 1)
                    .accessibilityHint(language == .chinese ? "从本地收件箱移除这个待发送项目。" : "Remove this pending item from the local inbox.")

                    if item.route == .imageIntake {
                        Text("image-intake")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    }
                }
            }

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
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, minHeight: 42)
            }
            .buttonStyle(AgentPocketLightPrimaryButtonStyle())
            .disabled(isSendDisabled(for: item))
            .opacity(isSendDisabled(for: item) ? 0.54 : 1)

            if isReviewExpanded {
                reviewDetails(reviewPresentation)
            }
        }
        .padding(14)
        .background(AgentPocketDesignTokens.lightPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                .stroke(AgentPocketDesignTokens.lightBorder, lineWidth: 1)
        )
    }

    private func reviewDetails(_ presentation: InboxPendingItemReviewPresentation) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(presentation.title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(AgentPocketDesignTokens.ink)

            VStack(alignment: .leading, spacing: 7) {
                ForEach(presentation.rows) { row in
                    HStack(alignment: .top, spacing: 8) {
                        Image(systemName: row.systemImage)
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(AgentPocketDesignTokens.accent.opacity(0.86))
                            .frame(width: 16, height: 16)
                            .accessibilityHidden(true)

                        Text(row.label)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                            .frame(width: 98, alignment: .leading)

                        Text(row.value)
                            .font(.caption)
                            .foregroundStyle(AgentPocketDesignTokens.ink)
                            .lineLimit(3)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        }
        .padding(.top, 2)
        .accessibilityElement(children: .contain)
    }

    private func toggleReviewDetails(for itemID: UUID) {
        if expandedReviewItemIDs.contains(itemID) {
            expandedReviewItemIDs.remove(itemID)
        } else {
            expandedReviewItemIDs.insert(itemID)
        }
    }

    private func feedbackBanner(_ presentation: InboxActionFeedbackPresentation) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: presentation.systemImage)
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(presentation.isFailure ? Color(red: 1.0, green: 0.74, blue: 0.38) : AgentPocketDesignTokens.accent)
                .frame(width: 28, height: 28)
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 4) {
                Text(presentation.title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(AgentPocketDesignTokens.ink)
                Text(presentation.message)
                    .font(.caption)
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 8)

            if presentation.canDismiss {
                Button {
                    viewModel.dismissFailure()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .bold))
                        .frame(width: 28, height: 28)
                }
                .buttonStyle(AgentPocketLightIconButtonStyle())
                .accessibilityLabel(language == .chinese ? "关闭" : "Close")
            }
        }
        .padding(12)
        .background(AgentPocketDesignTokens.lightPanel, in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                .stroke(presentation.isFailure ? Color(red: 1.0, green: 0.74, blue: 0.38).opacity(0.26) : AgentPocketDesignTokens.accent.opacity(0.20), lineWidth: 1)
        )
    }

    private func resultBanner(_ status: TaskStatusResponse, context: InboxSubmissionContext?) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(AgentPocketDesignTokens.accent)
                Text(resultTitle(status))
                    .font(.headline)
                    .foregroundStyle(AgentPocketDesignTokens.ink)
                Spacer()
                Button {
                    viewModel.dismissResult()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 13, weight: .bold))
                        .frame(width: 30, height: 30)
                }
                .buttonStyle(AgentPocketLightIconButtonStyle())
                .accessibilityLabel(language == .chinese ? "关闭" : "Close")
            }

            if let summary = resultSummary(status) {
                Text(summary)
                    .font(.subheadline)
                    .foregroundStyle(AgentPocketDesignTokens.inkMuted)
                    .lineLimit(4)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if let context {
                VStack(alignment: .leading, spacing: 4) {
                    Label(resultSourceText(context), systemImage: "link")
                    Label(resultContextText(context), systemImage: context.contextSelected ? "location.circle.fill" : "location.slash")
                }
                .font(.caption.weight(.medium))
                .foregroundStyle(AgentPocketDesignTokens.inkMuted)
            }

            RecallView(
                sourceTaskID: status.taskID,
                sourceInboxItemID: context?.sourceInboxItemID,
                initialSummary: resultSummary(status) ?? resultTitle(status),
                isFramed: false,
                activeConnection: activeConnection
            )
        }
        .padding(14)
        .background(Color(red: 0.90, green: 0.98, blue: 0.95), in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous)
                .stroke(AgentPocketDesignTokens.accent.opacity(0.24), lineWidth: 1)
        )
    }

    private var isSubmitting: Bool {
        if case .submitting = viewModel.state {
            return true
        }
        return false
    }

    private var discardConfirmationBinding: Binding<Bool> {
        Binding(
            get: { pendingDiscardItem != nil },
            set: { isPresented in
                if isPresented == false {
                    pendingDiscardItem = nil
                }
            }
        )
    }

    private var discardConfirmationTitle: String {
        language == .chinese ? "丢弃这个项目？" : "Discard This Item?"
    }

    private var discardConfirmationMessage: String {
        language == .chinese
            ? "这只会移除 Kaka 本地收件箱中的待发送项目。已经发送的任务和 Recall 不会改变。"
            : "This removes only the pending local Inbox item. Sent tasks and Recall stay unchanged."
    }

    private var isContextSnapshotPreparingForSubmission: Bool {
        contextSnapshotViewModel.includeContext && contextSnapshotViewModel.isContextSnapshotPreparing
    }

    private func isSendDisabled(for item: KakaInboxItem) -> Bool {
        isSubmitting
            || item.route == .universalIntake && isContextSnapshotPreparingForSubmission
            || viewModel.canSubmit(item) == false
    }

    private var showsContextSnapshotPreview: Bool {
        viewModel.items.contains { $0.route == .universalIntake }
    }

    private func beginVoiceInstruction(for item: KakaInboxItem) {
        if let note = item.note,
           note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false {
            voiceCaptureViewModel.markTranscriptReady(note)
        } else {
            voiceCaptureViewModel.reset()
        }
        voiceCaptureMode = .instruction(item)
    }

    private func voiceCapturePresentation(for mode: VoiceCaptureMode) -> VoiceCapturePresentation {
        switch mode {
        case .draft:
            return .inboxDraft(language: language)
        case .instruction(let item):
            let trimmedInstruction = item.note?.trimmingCharacters(in: .whitespacesAndNewlines)
            return .inboxInstruction(
                hasExistingInstruction: trimmedInstruction?.isEmpty == false,
                language: language
            )
        }
    }

    private func saveVoiceCapture(_ transcript: String, mode: VoiceCaptureMode) -> KakaInboxItem? {
        switch mode {
        case .draft:
            return viewModel.appendVoiceTranscript(transcript)
        case .instruction(let item):
            return viewModel.updateVoiceInstruction(transcript, for: item.id)
        }
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
        case .video:
            return "video"
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
        case .video:
            return language == .chinese ? "共享视频" : "Shared Video"
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

    private func resultSourceText(_ context: InboxSubmissionContext) -> String {
        let source = context.sourceSurface ?? context.sourceApp ?? context.kind.rawValue
        if language == .chinese {
            return "来源：\(localizedSource(source))"
        }
        return "Source: \(localizedSource(source))"
    }

    private func resultContextText(_ context: InboxSubmissionContext) -> String {
        if context.contextSelected {
            return language == .chinese
                ? "已选择 Context Snapshot；支持的运行时会随本次任务接收。"
                : "Context Snapshot selected; supported runtimes receive it with this task."
        }
        return language == .chinese
            ? "本次任务未选择 Context Snapshot。"
            : "No Context Snapshot selected for this task."
    }

    private func localizedSource(_ source: String) -> String {
        switch source {
        case "paste":
            return language == .chinese ? "粘贴" : "Paste"
        case "voice":
            return language == .chinese ? "语音" : "Voice"
        case "share_extension":
            return language == .chinese ? "系统分享" : "Share Extension"
        case "file_picker", "document_picker":
            return language == .chinese ? "文件" : "Files"
        default:
            return source
        }
    }

    private func formattedDate(_ date: Date) -> String {
        date.formatted(date: .abbreviated, time: .shortened)
    }
}
