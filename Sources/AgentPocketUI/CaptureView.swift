import AgentPocketCore
import SwiftUI
#if os(iOS)
import AVFoundation
import PhotosUI
import UniformTypeIdentifiers
#endif
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

public struct CaptureView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @StateObject private var viewModel: CaptureFlowViewModel
    private let connectedRuntime: ConnectedRuntime?
    private let onChangeRuntime: (() -> Void)?
    private let activeConnection: () -> StoredConnection?
    @State private var isModeSelectorExpanded = false
    @State private var modeSelectorCollapseTask: Task<Void, Never>?
    @State private var modeDragTranslation: CGFloat = 0
    @State private var isShowingCompletedResult = false
    @State private var isShowingImageConversation = false
    @State private var autoOpenedResultTaskID: String?
    @State private var autoOpenedConversationTaskID: String?
    #if os(iOS)
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var embeddedCaptureRequestID = 0
    @State private var cameraAuthorizationStatus = AVCaptureDevice.authorizationStatus(for: .video)
    @State private var selectedZoomStop: CameraZoomStop = .wide
    #endif

    public init(
        connectedRuntime: ConnectedRuntime? = nil,
        onChangeRuntime: (() -> Void)? = nil,
        activeConnection: @escaping () -> StoredConnection? = { nil }
    ) {
        _viewModel = StateObject(wrappedValue: CaptureFlowViewModel())
        self.connectedRuntime = connectedRuntime
        self.onChangeRuntime = onChangeRuntime
        self.activeConnection = activeConnection
    }

    @MainActor
    public init(
        viewModel: CaptureFlowViewModel,
        connectedRuntime: ConnectedRuntime? = nil,
        onChangeRuntime: (() -> Void)? = nil,
        activeConnection: @escaping () -> StoredConnection? = { nil }
    ) {
        _viewModel = StateObject(wrappedValue: viewModel)
        self.connectedRuntime = connectedRuntime
        self.onChangeRuntime = onChangeRuntime
        self.activeConnection = activeConnection
    }

    public var body: some View {
        let presentation = presentation
        return GeometryReader { geometry in
            ZStack {
                captureBackground()

                ScrollView(showsIndicators: false) {
                    VStack(spacing: 14) {
                        captureHeader(presentation)
                        capturePreview(presentation)
                            .frame(height: previewHeight(for: geometry.size))
                        captureControls(presentation)
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 18)
                    .padding(.bottom, 18)
                    .frame(maxWidth: 620)
                    .frame(maxWidth: .infinity)
                }

                if presentation.isProcessing {
                    CaptureProcessingOverlay(statusText: presentation.statusText)
                        .transition(.opacity)
                }
            }
        }
        .animation(.easeInOut(duration: 0.18), value: presentation.isProcessing)
        .navigationTitle(presentation.title)
        .navigationDestination(isPresented: $isShowingCompletedResult) {
            if let completedStatus = viewModel.completedStatus {
                if completedStatus.vision != nil {
                    VisionResultView(
                        status: completedStatus,
                        originalAsset: viewModel.originalPreviewAsset
                    )
                } else {
                    resultGalleryView(status: completedStatus)
                }
            }
        }
        .navigationDestination(isPresented: $isShowingImageConversation) {
            if let completedStatus = viewModel.completedStatus,
               completedStatus.imageIntake != nil,
               let preparedUpload = viewModel.preparedUpload {
                ImageConversationView(
                    intakeStatus: completedStatus,
                    originalAsset: viewModel.originalPreviewAsset,
                    preparedUpload: preparedUpload,
                    activeConnection: activeConnection
                )
            }
        }
        .onChange(of: viewModel.completedStatus?.taskID) { _, taskID in
            autoOpenImageConversationIfNeeded(taskID: taskID)
            autoOpenCompletedResultIfNeeded(taskID: taskID)
        }
        .onChange(of: isShowingCompletedResult) { oldValue, isPresented in
            guard oldValue, isPresented == false else {
                return
            }
            resetForNextCapture()
        }
        .onChange(of: isShowingImageConversation) { oldValue, isPresented in
            guard oldValue, isPresented == false else {
                return
            }
            resetForNextCapture()
        }
        .onDisappear {
            modeSelectorCollapseTask?.cancel()
        }
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await prepareInlineCameraPreviewIfNeeded()
        }
        .onChange(of: selectedPhoto) { _, item in
            Task {
                await loadSelectedPhoto(item)
            }
        }
        #endif
    }

    private var language: AppLanguage {
        AppLanguage.resolved(storedValue: nil)
    }

    private var presentation: CaptureScreenPresentation {
        CaptureScreenPresentation(
            state: viewModel.state,
            selectedCameraMode: viewModel.selectedCameraMode,
            selectedIntent: viewModel.selectedIntent,
            language: language,
            connectedRuntimeName: connectedRuntime?.displayName,
            hasPreparedUpload: viewModel.preparedUpload != nil
        )
    }

    private func previewHeight(for size: CGSize) -> CGFloat {
        let contentWidth = min(size.width - 32, 588)
        return min(contentWidth * 4.0 / 3.0, size.height * 0.62)
    }

    @ViewBuilder
    private func captureBackground() -> some View {
        #if os(iOS)
        if shouldShowInlineCameraPreview {
            EmbeddedCameraPreviewView(
                captureRequestID: embeddedCaptureRequestID,
                zoomFactor: selectedZoomStop.zoomFactor,
                onCapture: handleEmbeddedCameraCapture,
                onFailure: { message in
                    viewModel.markFailed(message)
                }
            )
            .ignoresSafeArea()
            .allowsHitTesting(false)
            .accessibilityHidden(true)

            LinearGradient(
                colors: [
                    .black.opacity(0.44),
                    .black.opacity(0.10),
                    .black.opacity(0.66)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
            .allowsHitTesting(false)
        } else {
            fallbackCaptureBackground()
        }
        #else
        fallbackCaptureBackground()
        #endif
    }

    private func fallbackCaptureBackground() -> some View {
        LinearGradient(
            colors: [
                Color(red: 0.055, green: 0.066, blue: 0.066),
                Color(red: 0.11, green: 0.145, blue: 0.145),
                Color(red: 0.045, green: 0.05, blue: 0.05)
            ],
            startPoint: .top,
            endPoint: .bottom
        )
        .ignoresSafeArea()
    }

    private func captureHeader(_ presentation: CaptureScreenPresentation) -> some View {
        HStack(spacing: 10) {
            if let onChangeRuntime {
                Button {
                    onChangeRuntime()
                } label: {
                    Image(systemName: "gearshape.fill")
                        .font(.system(size: 17, weight: .semibold))
                        .frame(width: 40, height: 40)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.white.opacity(0.9))
                .accessibilityIdentifier("changeRuntimeButton")
                .accessibilityLabel(language == .chinese ? "更换本机智能体" : "Change Local Agent")
            } else {
                Image(systemName: "gearshape.fill")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.42))
                    .frame(width: 40, height: 40)
                    .accessibilityHidden(true)
            }

            CaptureAIConnectionIndicator(accessibilityLabel: presentation.connectedBadge)

            Spacer(minLength: 8)

            galleryHeaderControl(presentation)
        }
    }

    private func capturePreview(_ presentation: CaptureScreenPresentation) -> some View {
        ZStack {
            capturePreviewContent()
                .overlay {
                    LinearGradient(
                        colors: [.black.opacity(0.18), .clear, .black.opacity(0.34)],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                    .allowsHitTesting(false)
                }
                .overlay(alignment: .center) {
                    CaptureGridOverlay()
                }
                .overlay(alignment: .bottom) {
                    zoomStopBar(presentation)
                        .padding(.bottom, 14)
                }

            CaptureCornerGuides()
                .padding(16)
                .allowsHitTesting(false)
        }
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(.white.opacity(0.14), lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.28), radius: 24, y: 12)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(presentation.statusText)
    }

    @ViewBuilder
    private func capturePreviewContent() -> some View {
        #if os(iOS)
        if shouldShowInlineCameraPreview {
            Color.clear
        } else {
            CapturePreviewImage(asset: viewModel.originalPreviewAsset)
        }
        #else
        CapturePreviewImage(asset: viewModel.originalPreviewAsset)
        #endif
    }

    #if os(iOS)
    private var shouldShowInlineCameraPreview: Bool {
        viewModel.originalPreviewAsset == nil
            && CameraCaptureView.isCameraAvailable
            && cameraAuthorizationStatus == .authorized
    }
    #endif

    private func zoomStopBar(_ presentation: CaptureScreenPresentation) -> some View {
        HStack(spacing: 8) {
            ForEach(presentation.zoomStops) { stop in
                Button {
                    selectZoomStop(stop)
                } label: {
                    Text(stop.title)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(isSelectedZoomStop(stop) ? Color(red: 0.55, green: 0.96, blue: 0.89) : .white)
                        .frame(width: 34, height: 34)
                        .background(isSelectedZoomStop(stop) ? .black.opacity(0.48) : .black.opacity(0.34), in: Circle())
                        .overlay(
                            Circle()
                                .stroke(isSelectedZoomStop(stop) ? Color(red: 0.55, green: 0.96, blue: 0.89) : .clear, lineWidth: 1)
                        )
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("cameraZoom-\(stop.title)")
                .accessibilityLabel(stop.title)
            }
        }
    }

    private func isSelectedZoomStop(_ stop: CameraZoomStop) -> Bool {
        #if os(iOS)
        return stop == selectedZoomStop
        #else
        return stop == .wide
        #endif
    }

    private func selectZoomStop(_ stop: CameraZoomStop) {
        #if os(iOS)
        withAnimation(.easeInOut(duration: 0.18)) {
            selectedZoomStop = stop
        }
        #endif
    }

    private func captureControls(_ presentation: CaptureScreenPresentation) -> some View {
        VStack(spacing: 14) {
            captureStatus(presentation)

            HStack(alignment: .center, spacing: 20) {
                primaryActionControl(presentation)
            }
            .frame(maxWidth: .infinity)
        }
        .padding(.horizontal, 12)
        .padding(.top, 12)
        .padding(.bottom, 16)
        .background(.black.opacity(0.28), in: RoundedRectangle(cornerRadius: 24, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .stroke(.white.opacity(0.12), lineWidth: 1)
        )
    }

    @ViewBuilder
    private func cameraModeWheel(_ presentation: CaptureScreenPresentation) -> some View {
        CaptureModeCarousel(
            tabs: presentation.modeTabs.filter(\.isEnabled),
            selectedMode: viewModel.selectedCameraMode,
            isExpanded: isModeSelectorExpanded || abs(modeDragTranslation) > 0.5,
            dragOffset: modeDragTranslation,
            onSelect: { mode in
                selectCameraMode(mode, collapseAfterSelection: true)
            }
        )
        .simultaneousGesture(modeDragGesture)
        .onTapGesture {
            showModeSelector()
            collapseModeSelectorSoon()
        }
        .transition(.opacity)
        .accessibilityIdentifier("cameraModeWheel")
    }

    @ViewBuilder
    private func captureStatus(_ presentation: CaptureScreenPresentation) -> some View {
        if shouldDisplayCaptureStatus {
            VStack(alignment: .center, spacing: 8) {
                switch viewModel.state {
                case .empty:
                    Text(presentation.statusText)
                        .font(.callout)
                        .foregroundStyle(.white.opacity(0.72))
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: .infinity, alignment: .center)
                case .loadingPhoto:
                    ProgressView(presentation.statusText)
                        .tint(Color(red: 0.55, green: 0.96, blue: 0.89))
                case .ready:
                    Label(presentation.statusText, systemImage: "checkmark.circle.fill")
                        .font(.callout.weight(.medium))
                        .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                        .accessibilityIdentifier("selectedPhotoReadyStatus")
                case .uploading:
                    ProgressView(presentation.statusText)
                        .tint(Color(red: 0.55, green: 0.96, blue: 0.89))
                case .startingTask:
                    ProgressView(presentation.statusText)
                        .tint(Color(red: 0.55, green: 0.96, blue: 0.89))
                case .submitted:
                    ProgressView(presentation.statusText)
                        .tint(Color(red: 0.55, green: 0.96, blue: 0.89))
                case .running(let taskID, let progress, let message):
                    VStack(alignment: .leading, spacing: 6) {
                        ProgressView(value: progress) {
                            Text(message ?? presentation.statusText)
                        }
                        .tint(Color(red: 0.55, green: 0.96, blue: 0.89))

                        Text(taskID)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.58))
                    }
                case .completed:
                    Label(presentation.statusText, systemImage: "checkmark.circle.fill")
                        .font(.callout.weight(.medium))
                        .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                case .failed:
                    Label(presentation.statusText, systemImage: "exclamationmark.triangle.fill")
                        .font(.callout.weight(.medium))
                        .foregroundStyle(Color(red: 1.0, green: 0.45, blue: 0.40))
                }
            }
            .frame(maxWidth: .infinity, minHeight: 44, alignment: .center)
            .transition(.opacity.combined(with: .move(edge: .top)))
        }
    }

    private var shouldDisplayCaptureStatus: Bool {
        switch viewModel.state {
        case .empty:
            return true
        case .loadingPhoto, .ready, .uploading, .startingTask, .submitted, .running, .completed, .failed:
            return true
        }
    }

    private func selectCameraMode(_ mode: SmartCameraMode, collapseAfterSelection: Bool = false) {
        guard mode.isSelectable else {
            return
        }
        withAnimation(modeSelectionAnimation) {
            viewModel.selectedCameraMode = mode
            modeDragTranslation = 0
        }
        if collapseAfterSelection {
            collapseModeSelectorSoon()
        }
    }

    private var modeDragGesture: some Gesture {
        DragGesture(minimumDistance: 0, coordinateSpace: .local)
            .onChanged { value in
                updateModeDrag(value)
            }
            .onEnded { gesture in
                switchCameraMode(after: gesture)
            }
    }

    private func updateModeDrag(_ value: DragGesture.Value) {
        showModeSelector()
        var transaction = Transaction(animation: nil)
        transaction.disablesAnimations = true
        withTransaction(transaction) {
            modeDragTranslation = value.translation.width
        }
    }

    private func switchCameraMode(after gesture: DragGesture.Value) {
        let nextMode = CameraModeSelectionPolicy.resolvedMode(
            current: viewModel.selectedCameraMode,
            translation: gesture.translation.width,
            predictedEndTranslation: gesture.predictedEndTranslation.width
        )
        guard nextMode != viewModel.selectedCameraMode else {
            withAnimation(modeSelectionAnimation) {
                modeDragTranslation = 0
            }
            collapseModeSelectorSoon()
            return
        }
        withAnimation(modeSelectionAnimation) {
            viewModel.selectedCameraMode = nextMode
            modeDragTranslation = 0
        }
        collapseModeSelectorSoon()
    }

    private func showModeSelector() {
        modeSelectorCollapseTask?.cancel()
        guard isModeSelectorExpanded == false else {
            return
        }
        withAnimation(modeSelectionAnimation) {
            isModeSelectorExpanded = true
        }
    }

    private func collapseModeSelectorSoon() {
        modeSelectorCollapseTask?.cancel()
        modeSelectorCollapseTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 900_000_000)
            withAnimation(modeSelectionAnimation) {
                isModeSelectorExpanded = false
            }
        }
    }

    @MainActor
    private func resetForNextCapture() {
        modeSelectorCollapseTask?.cancel()
        withAnimation(modeSelectionAnimation) {
            isModeSelectorExpanded = false
        }
        #if os(iOS)
        embeddedCaptureRequestID = 0
        selectedPhoto = nil
        #endif
        autoOpenedResultTaskID = nil
        autoOpenedConversationTaskID = nil
        viewModel.resetForNextCapture()
    }

    private var unavailableModeAccessibilityHint: String {
        language == .chinese ? "此模式即将开放。" : "This mode is coming soon."
    }

    private var modeSelectionAccessibilityHint: String {
        language == .chinese ? "选择此相机模式。" : "Selects this camera mode."
    }

    private var modeSelectionAnimation: Animation {
        reduceMotion
            ? .linear(duration: 0.01)
            : .interactiveSpring(response: 0.34, dampingFraction: 0.82, blendDuration: 0.08)
    }

    private func cameraControl(_ presentation: CaptureScreenPresentation) -> some View {
        #if os(iOS)
        Button {
            Task {
                await openCamera()
            }
        } label: {
            CaptureSideControl(title: presentation.cameraTitle, systemImage: "camera")
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("capturePhotoButton")
        .accessibilityHint(cameraAccessibilityHint)
        #else
        Button {
        } label: {
            CaptureSideControl(title: presentation.cameraTitle, systemImage: "camera")
        }
        .buttonStyle(.plain)
        .disabled(true)
        .accessibilityHint(language == .chinese ? "相机拍摄可在 iPhone 上使用。" : "Camera capture is available on iPhone.")
        #endif
    }

    @ViewBuilder
    private func galleryHeaderControl(_ presentation: CaptureScreenPresentation) -> some View {
        #if os(iOS)
        PhotosPicker(selection: $selectedPhoto, matching: .images) {
            Image(systemName: "photo.on.rectangle")
                .font(.system(size: 17, weight: .semibold))
                .frame(width: 40, height: 40)
                .background(.white.opacity(0.12), in: Circle())
                .overlay(Circle().stroke(.white.opacity(0.14), lineWidth: 1))
        }
        .buttonStyle(.plain)
        .foregroundStyle(.white.opacity(0.92))
        .accessibilityIdentifier("choosePhotoButton")
        .accessibilityLabel(presentation.galleryTitle)
        .accessibilityHint(language == .chinese ? "从照片图库中选择一张图片。" : "Selects an image from your photo library.")
        #else
        Button {
        } label: {
            Image(systemName: "photo.on.rectangle")
                .font(.system(size: 17, weight: .semibold))
                .frame(width: 40, height: 40)
                .background(.white.opacity(0.08), in: Circle())
        }
        .buttonStyle(.plain)
        .foregroundStyle(.white.opacity(0.42))
        .disabled(true)
        .accessibilityLabel(presentation.galleryTitle)
        #endif
    }

    @ViewBuilder
    private func primaryActionControl(_ presentation: CaptureScreenPresentation) -> some View {
        let actionMode = primaryActionMode
        if actionMode == .reviewCompletedResult {
            Button {
                isShowingCompletedResult = viewModel.completedStatus != nil
            } label: {
                CapturePrimaryActionButton(presentation: presentation)
            }
            .buttonStyle(.plain)
            .disabled(viewModel.completedStatus == nil)
            .accessibilityIdentifier("reviewResultsButton")
        } else {
            Button {
                Task {
                    await performPrimaryAction(mode: actionMode)
                }
            } label: {
                CapturePrimaryActionButton(presentation: presentation)
            }
            .buttonStyle(.plain)
            .disabled(actionMode == .disabled || presentation.primaryAction.isEnabled == false)
            .accessibilityIdentifier(primaryActionAccessibilityIdentifier(for: actionMode))
        }
    }

    private func galleryControl(_ presentation: CaptureScreenPresentation) -> some View {
        #if os(iOS)
        PhotosPicker(selection: $selectedPhoto, matching: .images) {
            CaptureSideControl(title: presentation.galleryTitle, systemImage: "photo.on.rectangle")
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("choosePhotoButton")
        .accessibilityHint(language == .chinese ? "从照片图库中选择一张图片。" : "Selects an image from your photo library.")
        #else
        Button {
        } label: {
            CaptureSideControl(title: presentation.galleryTitle, systemImage: "photo.on.rectangle")
        }
        .buttonStyle(.plain)
        .disabled(true)
        #endif
    }

    private var primaryActionMode: CapturePrimaryActionMode {
        CapturePrimaryActionPolicy.mode(
            captureState: viewModel.state,
            hasPreparedUpload: viewModel.preparedUpload != nil,
            hasCompletedStatus: viewModel.completedStatus != nil
        )
    }

    private var completedStatusForReview: TaskStatusResponse? {
        if case .completed = viewModel.state {
            return viewModel.completedStatus
        }
        return nil
    }

    @MainActor
    private func autoOpenCompletedResultIfNeeded(taskID: String?) {
        guard viewModel.completedStatus?.imageIntake == nil else {
            return
        }
        guard CaptureResultAutoreviewPolicy.shouldOpenResult(
            taskID: taskID,
            alreadyOpenedTaskID: autoOpenedResultTaskID,
            hasCompletedStatus: viewModel.completedStatus != nil
        ) else {
            return
        }
        autoOpenedResultTaskID = taskID
        isShowingCompletedResult = true
    }

    @MainActor
    private func autoOpenImageConversationIfNeeded(taskID: String?) {
        guard CaptureConversationAutoreviewPolicy.shouldOpenConversation(
            taskID: taskID,
            alreadyOpenedTaskID: autoOpenedConversationTaskID,
            hasImageIntake: viewModel.completedStatus?.imageIntake != nil
        ) else {
            return
        }
        autoOpenedConversationTaskID = taskID
        isShowingImageConversation = true
    }

    @MainActor
    private func performPrimaryAction(mode: CapturePrimaryActionMode) async {
        switch mode {
        case .openCamera:
            #if os(iOS)
            await openCamera()
            #else
            viewModel.markFailed("Camera is not available on this device. Choose a photo from the library instead.")
            #endif
        case .submitPreparedPhoto:
            await viewModel.submitImageIntake(connection: activeConnection())
        case .reviewCompletedResult:
            isShowingCompletedResult = viewModel.completedStatus != nil
        case .disabled:
            break
        }
    }

    private func primaryActionAccessibilityIdentifier(for mode: CapturePrimaryActionMode) -> String {
        switch mode {
        case .openCamera:
            return "capturePhotoButton"
        case .submitPreparedPhoto:
            return "sendToKakaButton"
        case .reviewCompletedResult:
            return "reviewResultsButton"
        case .disabled:
            return "primaryActionButtonDisabled"
        }
    }

    private func resultGalleryView(status: TaskStatusResponse) -> some View {
        ResultGalleryView(
            status: status,
            activeConnection: activeConnection,
            initialOriginalAsset: viewModel.originalPreviewAsset
        )
    }

    @MainActor
    private func autoSubmitPreparedPhotoIfNeeded(source: CapturePreparedPhotoSource) {
        guard CaptureAutosubmitPolicy.shouldSubmitPreparedPhoto(
            source: source,
            hasPreparedUpload: viewModel.preparedUpload != nil,
            hasActiveConnection: activeConnection() != nil,
            allowsAutosubmit: viewModel.selectedCameraMode.isSelectable
        ) else {
            return
        }

        Task {
            await viewModel.submitImageIntake(connection: activeConnection())
        }
    }

    #if os(iOS)
    private var cameraAccessibilityHint: String {
        if CameraCaptureView.isCameraAvailable {
            return language == .chinese
                ? "直接拍摄当前取景画面。"
                : "Captures the current live camera frame."
        }
        return language == .chinese
            ? "这台设备没有可用相机。请从相册选择照片。"
            : "Camera is not available on this device. Choose a photo from the library instead."
    }

    @MainActor
    private func openCamera() async {
        await captureInlineCameraPhoto()
    }

    @MainActor
    private func prepareInlineCameraPreviewIfNeeded() async {
        guard CameraCaptureView.isCameraAvailable else {
            return
        }
        let status = AVCaptureDevice.authorizationStatus(for: .video)
        cameraAuthorizationStatus = status
        guard status == .notDetermined else {
            return
        }
        let granted = await requestCameraAccess()
        cameraAuthorizationStatus = granted ? .authorized : .denied
        if granted == false {
            viewModel.markFailed("Camera access is disabled. Allow camera access in Settings or choose a photo from the library.")
        }
    }

    @MainActor
    private func captureInlineCameraPhoto() async {
        guard CameraCaptureView.isCameraAvailable else {
            viewModel.markFailed("Camera is not available on this device. Choose a photo from the library instead.")
            return
        }

        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            cameraAuthorizationStatus = .authorized
            embeddedCaptureRequestID += 1
        case .notDetermined:
            if await requestCameraAccess() {
                cameraAuthorizationStatus = .authorized
                embeddedCaptureRequestID += 1
            } else {
                cameraAuthorizationStatus = .denied
                viewModel.markFailed("Camera access is disabled. Allow camera access in Settings or choose a photo from the library.")
            }
        case .denied, .restricted:
            cameraAuthorizationStatus = AVCaptureDevice.authorizationStatus(for: .video)
            viewModel.markFailed("Camera access is disabled. Allow camera access in Settings or choose a photo from the library.")
        @unknown default:
            viewModel.markFailed("Camera is not available on this device. Choose a photo from the library instead.")
        }
    }

    @MainActor
    private func handleEmbeddedCameraCapture(_ data: Data) {
        do {
            try viewModel.prepareCapturedPhoto(data: data, maxUploadMB: 30)
            autoSubmitPreparedPhotoIfNeeded(source: .camera)
        } catch {
            if case .failed = viewModel.state {
                return
            }
            viewModel.markFailed("This camera photo could not be prepared.")
        }
    }

    private func requestCameraAccess() async -> Bool {
        await withCheckedContinuation { continuation in
            AVCaptureDevice.requestAccess(for: .video) { granted in
                continuation.resume(returning: granted)
            }
        }
    }

    @MainActor
    private func loadSelectedPhoto(_ item: PhotosPickerItem?) async {
        guard let item else {
            return
        }
        viewModel.markLoadingSelectedPhoto()
        defer {
            selectedPhoto = nil
        }
        do {
            guard let data = try await item.loadTransferable(type: Data.self) else {
                viewModel.markFailed("This photo could not be loaded.")
                return
            }
            let contentType = item.supportedContentTypes.first ?? UTType.jpeg
            try viewModel.prepareSelectedImage(
                data: data,
                sourceMimeType: contentType.preferredMIMEType ?? "image/jpeg",
                fileName: "library.\(contentType.preferredFilenameExtension ?? "jpg")",
                maxUploadMB: 30
            )
        } catch {
            if case .failed = viewModel.state {
                return
            }
            viewModel.markFailed("This photo could not be loaded.")
        }
    }
    #endif
}

private struct CapturePreviewImage: View {
    let asset: DownloadedAsset?

    var body: some View {
        ZStack {
            if let image = previewImage {
                image
                    .resizable()
                    .scaledToFill()
                    .accessibilityHidden(true)
            } else {
                LinearGradient(
                    colors: [
                        Color(red: 0.38, green: 0.45, blue: 0.47),
                        Color(red: 0.16, green: 0.22, blue: 0.22),
                        Color(red: 0.07, green: 0.09, blue: 0.09)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )

                Image(systemName: "viewfinder")
                    .font(.system(size: 34, weight: .medium))
                    .foregroundStyle(.white.opacity(0.5))
                    .accessibilityHidden(true)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var previewImage: Image? {
        guard let asset else {
            return nil
        }
        #if canImport(UIKit)
        guard let uiImage = UIImage(data: asset.data) else {
            return nil
        }
        return Image(uiImage: uiImage)
        #elseif canImport(AppKit)
        guard let nsImage = NSImage(data: asset.data) else {
            return nil
        }
        return Image(nsImage: nsImage)
        #else
        return nil
        #endif
    }
}

private struct CaptureGridOverlay: View {
    var body: some View {
        GeometryReader { geometry in
            Path { path in
                let width = geometry.size.width
                let height = geometry.size.height
                path.move(to: CGPoint(x: width / 3, y: 0))
                path.addLine(to: CGPoint(x: width / 3, y: height))
                path.move(to: CGPoint(x: width * 2 / 3, y: 0))
                path.addLine(to: CGPoint(x: width * 2 / 3, y: height))
                path.move(to: CGPoint(x: 0, y: height / 3))
                path.addLine(to: CGPoint(x: width, y: height / 3))
                path.move(to: CGPoint(x: 0, y: height * 2 / 3))
                path.addLine(to: CGPoint(x: width, y: height * 2 / 3))
            }
            .stroke(.white.opacity(0.22), lineWidth: 0.8)
        }
        .allowsHitTesting(false)
    }
}

private struct CaptureCornerGuides: View {
    var body: some View {
        GeometryReader { geometry in
            Path { path in
                let width = geometry.size.width
                let height = geometry.size.height
                let length = min(width, height) * 0.08

                path.move(to: CGPoint(x: 0, y: length))
                path.addLine(to: CGPoint(x: 0, y: 0))
                path.addLine(to: CGPoint(x: length, y: 0))

                path.move(to: CGPoint(x: width - length, y: 0))
                path.addLine(to: CGPoint(x: width, y: 0))
                path.addLine(to: CGPoint(x: width, y: length))

                path.move(to: CGPoint(x: width, y: height - length))
                path.addLine(to: CGPoint(x: width, y: height))
                path.addLine(to: CGPoint(x: width - length, y: height))

                path.move(to: CGPoint(x: length, y: height))
                path.addLine(to: CGPoint(x: 0, y: height))
                path.addLine(to: CGPoint(x: 0, y: height - length))
            }
            .stroke(.white.opacity(0.82), style: StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
        }
    }
}

private struct CaptureSideControl: View {
    let title: String
    let systemImage: String

    var body: some View {
        VStack(spacing: 7) {
            Image(systemName: systemImage)
                .font(.system(size: 22, weight: .semibold))
                .foregroundStyle(.white)
                .frame(width: 58, height: 58)
                .background(.white.opacity(0.12), in: Circle())
                .overlay(Circle().stroke(.white.opacity(0.18), lineWidth: 1))
                .accessibilityHidden(true)

            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white.opacity(0.9))
                .lineLimit(1)
                .minimumScaleFactor(0.76)
        }
        .frame(width: 76)
        .contentShape(Rectangle())
    }
}

private struct CaptureAIConnectionIndicator: View {
    let accessibilityLabel: String

    var body: some View {
        HStack(spacing: 5) {
            Circle()
                .fill(Color(red: 0.38, green: 0.86, blue: 0.54))
                .frame(width: 6, height: 6)
                .accessibilityHidden(true)

            Text("AI")
                .font(.caption.weight(.bold))
                .foregroundStyle(.white.opacity(0.92))
                .lineLimit(1)
        }
        .padding(.horizontal, 10)
        .frame(height: 32)
        .background(.black.opacity(0.24), in: Capsule())
        .overlay(Capsule().stroke(.white.opacity(0.10), lineWidth: 1))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(accessibilityLabel)
    }
}

private struct CaptureModeCarousel: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let tabs: [CaptureScreenPresentation.ModeTab]
    let selectedMode: SmartCameraMode
    let isExpanded: Bool
    let dragOffset: CGFloat
    let onSelect: (SmartCameraMode) -> Void

    var body: some View {
        GeometryReader { geometry in
            let slotWidth = max(86, (geometry.size.width - 24) / 3)
            let spacing: CGFloat = 10
            let itemStride = slotWidth + spacing
            let selectedIndex = tabs.firstIndex { $0.mode == selectedMode } ?? 0
            let activeDragOffset = CameraModeSelectionPolicy.interactiveDragOffset(
                current: selectedMode,
                translation: dragOffset,
                itemWidth: itemStride
            )
            let stripOffset = stripOffset(
                selectedIndex: selectedIndex,
                activeDragOffset: activeDragOffset,
                slotWidth: slotWidth,
                itemStride: itemStride,
                containerWidth: geometry.size.width
            )
            HStack(spacing: spacing) {
                ForEach(Array(tabs.enumerated()), id: \.element.mode) { index, tab in
                    let focusAmount = focusAmount(
                        forIndex: index,
                        stripOffset: stripOffset,
                        slotWidth: slotWidth,
                        itemStride: itemStride,
                        containerWidth: geometry.size.width
                    )

                    Button {
                        onSelect(tab.mode)
                    } label: {
                        CaptureModeWheelItem(tab: tab, focusAmount: focusAmount)
                            .frame(width: slotWidth, height: 44)
                    }
                    .buttonStyle(.plain)
                    .allowsHitTesting(tab.mode != selectedMode)
                    .accessibilityIdentifier("cameraMode-\(tab.mode.rawValue)")
                    .zIndex(Double(focusAmount))
                }
            }
            .offset(x: stripOffset)
            .animation(modeChangeAnimation, value: selectedMode)
            .animation(expansionAnimation, value: isExpanded)
            .frame(height: geometry.size.height, alignment: .center)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .frame(height: 56)
        .padding(6)
        .background(.black.opacity(isExpanded ? 0.30 : 0.0), in: Capsule())
        .overlay(
            Capsule()
                .stroke(.white.opacity(isExpanded ? 0.12 : 0.0), lineWidth: 1)
        )
        .clipShape(Capsule())
        .contentShape(Capsule())
    }

    private var modeChangeAnimation: Animation? {
        reduceMotion
            ? .linear(duration: 0.01)
            : .interactiveSpring(response: 0.34, dampingFraction: 0.82, blendDuration: 0.08)
    }

    private var expansionAnimation: Animation? {
        reduceMotion ? .linear(duration: 0.01) : .easeInOut(duration: 0.12)
    }

    private func stripOffset(
        selectedIndex: Int,
        activeDragOffset: CGFloat,
        slotWidth: CGFloat,
        itemStride: CGFloat,
        containerWidth: CGFloat
    ) -> CGFloat {
        let selectedCenter = CGFloat(selectedIndex) * itemStride + slotWidth / 2
        return containerWidth / 2 - selectedCenter + activeDragOffset
    }

    private func focusAmount(
        forIndex index: Int,
        stripOffset: CGFloat,
        slotWidth: CGFloat,
        itemStride: CGFloat,
        containerWidth: CGFloat
    ) -> CGFloat {
        let itemCenter = stripOffset + CGFloat(index) * itemStride + slotWidth / 2
        let distanceFromCenter = abs(itemCenter - containerWidth / 2)
        return max(0, min(1, 1 - distanceFromCenter / max(itemStride, 1)))
    }
}

private struct CaptureSelectedModePill: View {
    let tab: CaptureScreenPresentation.ModeTab

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: tab.systemImage)
                .font(.system(size: 15, weight: .bold))
                .accessibilityHidden(true)

            Text(tab.title)
                .font(.callout.weight(.bold))
                .lineLimit(1)
                .minimumScaleFactor(0.76)

            Image(systemName: "chevron.left.chevron.right")
                .font(.system(size: 11, weight: .bold))
                .accessibilityHidden(true)
        }
        .foregroundStyle(.black)
        .padding(.horizontal, 18)
        .frame(minWidth: 132, minHeight: 50)
        .background(Color(red: 0.55, green: 0.96, blue: 0.89), in: Capsule())
        .overlay(Capsule().stroke(.white.opacity(0.36), lineWidth: 1))
        .contentShape(Capsule())
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isButton)
        .accessibilityAddTraits(.isSelected)
    }
}

private struct CaptureModeWheelItem: View {
    let tab: CaptureScreenPresentation.ModeTab
    let focusAmount: CGFloat

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: tab.systemImage)
                .font(.system(size: 13 + 2 * boundedFocusAmount, weight: .semibold))
                .accessibilityHidden(true)

            Text(tab.title)
                .font(.callout.weight(.semibold))
                .lineLimit(1)
                .minimumScaleFactor(0.72)

            if tab.isEnabled == false {
                Image(systemName: "lock.fill")
                    .font(.system(size: 9, weight: .bold))
                    .accessibilityHidden(true)
            }
        }
        .foregroundStyle(foregroundStyle)
        .padding(.horizontal, 13)
        .frame(minWidth: 92, minHeight: 42)
        .background {
            Capsule()
                .fill(baseBackgroundStyle)

            Capsule()
                .fill(selectedBackgroundStyle)
        }
        .overlay(
            Capsule()
                .stroke(strokeStyle, lineWidth: 1)
        )
        .scaleEffect(0.88 + 0.14 * boundedFocusAmount)
        .opacity(itemOpacity)
        .contentShape(Capsule())
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isButton)
        .accessibilityAddTraits(tab.isSelected ? .isSelected : [])
    }

    private var foregroundStyle: Color {
        if tab.isEnabled == false {
            return .white.opacity(0.5)
        }
        let whiteComponent = 1 - Double(boundedFocusAmount) * 0.94
        return Color(white: whiteComponent).opacity(0.9 + Double(boundedFocusAmount) * 0.1)
    }

    private var baseBackgroundStyle: Color {
        if tab.isEnabled == false {
            return .white.opacity(0.035)
        }
        return .white.opacity(0.07 + Double(boundedFocusAmount) * 0.03)
    }

    private var selectedBackgroundStyle: Color {
        Color(red: 0.55, green: 0.96, blue: 0.89)
            .opacity(tab.isEnabled ? Double(boundedFocusAmount) : 0)
    }

    private var strokeStyle: Color {
        if tab.isEnabled == false {
            return .white.opacity(0.05)
        }
        return .white.opacity(0.10 + Double(boundedFocusAmount) * 0.24)
    }

    private var itemOpacity: Double {
        if tab.isEnabled == false {
            return 0.42
        }
        return 0.46 + Double(boundedFocusAmount) * 0.54
    }

    private var boundedFocusAmount: CGFloat {
        min(max(focusAmount, 0), 1)
    }
}

private struct CapturePrimaryActionButton: View {
    let presentation: CaptureScreenPresentation

    var body: some View {
        VStack(spacing: 8) {
            ZStack {
                Circle()
                    .fill(Color(red: 0.55, green: 0.96, blue: 0.89))
                    .frame(width: 82, height: 82)
                    .overlay(Circle().stroke(.white.opacity(0.38), lineWidth: 5))

                Image(systemName: presentation.primaryAction.systemImage)
                    .font(.system(size: 24, weight: .bold))
                    .foregroundStyle(.black)
                    .accessibilityHidden(true)
            }
            .opacity(presentation.primaryAction.isEnabled ? 1 : 0.58)

            Text(presentation.primaryAction.title)
                .font(.caption.weight(.bold))
                .foregroundStyle(.white)
                .lineLimit(1)
                .minimumScaleFactor(0.64)
        }
        .frame(width: 122)
    }
}

private struct CaptureProcessingOverlay: View {
    let statusText: String

    var body: some View {
        ZStack {
            Color.black.opacity(0.48)
                .ignoresSafeArea()

            VStack(spacing: 14) {
                ProgressView()
                    .tint(Color(red: 0.55, green: 0.96, blue: 0.89))
                    .scaleEffect(1.15)

                Text(statusText)
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                    .multilineTextAlignment(.center)
                    .lineLimit(3)
                    .minimumScaleFactor(0.78)
            }
            .padding(.horizontal, 22)
            .padding(.vertical, 20)
            .frame(maxWidth: 300)
            .background(.black.opacity(0.66), in: RoundedRectangle(cornerRadius: 18, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(.white.opacity(0.12), lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.26), radius: 22, y: 10)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(statusText)
    }
}
