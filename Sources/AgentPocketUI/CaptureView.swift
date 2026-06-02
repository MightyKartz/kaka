import AgentPocketCore
import SwiftUI
#if os(iOS)
import PhotosUI
import UniformTypeIdentifiers
#endif
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

public struct CaptureView: View {
    @StateObject private var viewModel: CaptureFlowViewModel
    @AppStorage("kaka.interfaceLanguage") private var languageRawValue = AppLanguage.chinese.rawValue
    private let connectedRuntime: ConnectedRuntime?
    private let onChangeRuntime: (() -> Void)?
    private let activeConnection: () -> StoredConnection?
    #if os(iOS)
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var isShowingCamera = false
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
            }
        }
        .navigationTitle(presentation.title)
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        .onChange(of: selectedPhoto) { _, item in
            Task {
                await loadSelectedPhoto(item)
            }
        }
        .sheet(isPresented: $isShowingCamera) {
            CameraCaptureView { data in
                isShowingCamera = false
                do {
                    try viewModel.prepareCapturedPhoto(data: data, maxUploadMB: 30)
                } catch {
                    if case .failed = viewModel.state {
                        return
                    }
                    viewModel.markFailed("This camera photo could not be prepared.")
                }
            } onCancel: {
                isShowingCamera = false
            } onFailure: { message in
                isShowingCamera = false
                viewModel.markFailed(message)
            }
            .ignoresSafeArea()
        }
        #endif
    }

    private var language: AppLanguage {
        AppLanguage(rawValue: languageRawValue) ?? .chinese
    }

    private var presentation: CaptureScreenPresentation {
        CaptureScreenPresentation(
            state: viewModel.state,
            selectedIntent: viewModel.selectedIntent,
            language: language,
            connectedRuntimeName: connectedRuntime?.displayName,
            hasPreparedUpload: viewModel.preparedUpload != nil
        )
    }

    private func previewHeight(for size: CGSize) -> CGFloat {
        let contentWidth = min(size.width - 32, 588)
        return min(contentWidth * 1.18, size.height * 0.48)
    }

    private func captureHeader(_ presentation: CaptureScreenPresentation) -> some View {
        HStack(spacing: 10) {
            Image(systemName: "bolt.fill")
                .font(.system(size: 17, weight: .semibold))
                .foregroundStyle(.white.opacity(0.9))
                .frame(width: 40, height: 40)
                .accessibilityHidden(true)

            Spacer(minLength: 8)

            VStack(spacing: 7) {
                Text(presentation.connectedBadge)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
                    .padding(.horizontal, 12)
                    .frame(height: 30)
                    .background(.white.opacity(0.16), in: Capsule())

                Text(presentation.title)
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white)
                    .accessibilityAddTraits(.isHeader)
            }

            Spacer(minLength: 8)

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
                .accessibilityLabel(language == .chinese ? "更换本机智能体" : "Change Local Agent")
            } else {
                Image(systemName: "gearshape.fill")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.42))
                    .frame(width: 40, height: 40)
                    .accessibilityHidden(true)
            }
        }
    }

    private func capturePreview(_ presentation: CaptureScreenPresentation) -> some View {
        ZStack {
            CapturePreviewImage(asset: viewModel.originalPreviewAsset)
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
                .overlay(alignment: .topTrailing) {
                    Text(presentation.frameBadge)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 10)
                        .frame(height: 30)
                        .background(.black.opacity(0.42), in: Capsule())
                        .padding(12)
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

    private func zoomStopBar(_ presentation: CaptureScreenPresentation) -> some View {
        HStack(spacing: 8) {
            ForEach(presentation.zoomStops, id: \.self) { stop in
                Text(stop)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(stop == "1x" ? Color(red: 0.55, green: 0.96, blue: 0.89) : .white)
                    .frame(width: 34, height: 34)
                    .background(stop == "1x" ? .black.opacity(0.48) : .black.opacity(0.34), in: Circle())
                    .overlay(
                        Circle()
                            .stroke(stop == "1x" ? Color(red: 0.55, green: 0.96, blue: 0.89) : .clear, lineWidth: 1)
                    )
            }
        }
    }

    private func captureControls(_ presentation: CaptureScreenPresentation) -> some View {
        VStack(spacing: 14) {
            sceneTabs(presentation)
            captureStatus(presentation)

            HStack(alignment: .center, spacing: 20) {
                cameraControl(presentation)
                primaryActionControl(presentation)
                galleryControl(presentation)
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

    private func sceneTabs(_ presentation: CaptureScreenPresentation) -> some View {
        HStack(spacing: 4) {
            ForEach(presentation.sceneTabs) { tab in
                Button {
                    viewModel.selectedIntent = tab.intent
                } label: {
                    Text(tab.title)
                        .font(.callout.weight(.semibold))
                        .foregroundStyle(tab.isSelected ? .black : .white)
                        .lineLimit(1)
                        .minimumScaleFactor(0.72)
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .padding(.horizontal, 8)
                        .background(
                            tab.isSelected ? Color(red: 0.55, green: 0.96, blue: 0.89) : Color.clear,
                            in: Capsule()
                        )
                }
                .buttonStyle(.plain)
                .accessibilityHint(tab.intent.defaultInstruction)
            }
        }
        .padding(6)
        .background(.white.opacity(0.09), in: Capsule())
    }

    private func captureStatus(_ presentation: CaptureScreenPresentation) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            switch viewModel.state {
            case .empty:
                Text(presentation.statusText)
                    .font(.callout)
                    .foregroundStyle(.white.opacity(0.72))
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
            case .failed(let message):
                Label(message, systemImage: "exclamationmark.triangle.fill")
                    .font(.callout.weight(.medium))
                    .foregroundStyle(Color(red: 1.0, green: 0.45, blue: 0.40))
            }
        }
        .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
    }

    private func cameraControl(_ presentation: CaptureScreenPresentation) -> some View {
        #if os(iOS)
        Button {
            openCamera()
        } label: {
            CaptureSideControl(title: presentation.cameraTitle, systemImage: "camera")
        }
        .buttonStyle(.plain)
        .accessibilityHint(cameraAccessibilityHint)
        #else
        Button {
        } label: {
            CaptureSideControl(title: presentation.cameraTitle, systemImage: "camera")
        }
        .buttonStyle(.plain)
        .disabled(true)
        .accessibilityHint("Camera capture is available on iPhone.")
        #endif
    }

    @ViewBuilder
    private func primaryActionControl(_ presentation: CaptureScreenPresentation) -> some View {
        if let completedStatus = completedStatusForReview {
            NavigationLink {
                ResultGalleryView(
                    status: completedStatus,
                    activeConnection: activeConnection,
                    initialOriginalAsset: viewModel.originalPreviewAsset
                )
            } label: {
                CapturePrimaryActionButton(presentation: presentation)
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier("reviewResultsButton")
        } else {
            Button {
                Task {
                    await viewModel.submitPreparedImage(connection: activeConnection())
                }
            } label: {
                CapturePrimaryActionButton(presentation: presentation)
            }
            .buttonStyle(.plain)
            .disabled(isSubmitDisabled || presentation.primaryAction.isEnabled == false)
            .accessibilityIdentifier("sendToLocalAgentButton")
        }
    }

    private func galleryControl(_ presentation: CaptureScreenPresentation) -> some View {
        #if os(iOS)
        PhotosPicker(selection: $selectedPhoto, matching: .images) {
            CaptureSideControl(title: presentation.galleryTitle, systemImage: "photo.on.rectangle")
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("choosePhotoButton")
        .accessibilityHint("Selects an image from your photo library.")
        #else
        Button {
        } label: {
            CaptureSideControl(title: presentation.galleryTitle, systemImage: "photo.on.rectangle")
        }
        .buttonStyle(.plain)
        .disabled(true)
        #endif
    }

    private var isSubmitDisabled: Bool {
        switch viewModel.state {
        case .ready, .failed, .completed:
            return viewModel.preparedUpload == nil
        case .empty, .loadingPhoto, .uploading, .startingTask, .submitted, .running:
            return true
        }
    }

    private var completedStatusForReview: TaskStatusResponse? {
        if case .completed = viewModel.state {
            return viewModel.completedStatus
        }
        return nil
    }

    #if os(iOS)
    private var cameraAccessibilityHint: String {
        if CameraCaptureView.isCameraAvailable {
            return "Opens the camera to capture a photo for your local agent."
        }
        return "Camera is not available on this device. Choose a photo from the library instead."
    }

    @MainActor
    private func openCamera() {
        guard CameraCaptureView.isCameraAvailable else {
            viewModel.markFailed("Camera is not available on this device. Choose a photo from the library instead.")
            return
        }
        isShowingCamera = true
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
