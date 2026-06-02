import AgentPocketCore
import Foundation
import SwiftUI
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

public struct ResultGalleryView: View {
    @StateObject private var viewModel: ResultGalleryViewModel
    @StateObject private var saveFlow = PhotoSaveFlow()
    @AppStorage("kaka.interfaceLanguage") private var languageRawValue = AppLanguage.chinese.rawValue
    @State private var comparisonPosition = 0.5
    @State private var shareURL: URL?
    @Environment(\.openURL) private var openURL
    private let activeConnection: () -> StoredConnection?
    private let photoSaver: (any PhotoLibrarySaving)?

    public init(
        status: TaskStatusResponse,
        activeConnection: @escaping () -> StoredConnection? = { nil },
        downloader: any ResultAssetDownloading = MobileBridgeResultAssetDownloader(),
        initialOriginalAsset: DownloadedAsset? = nil,
        initialDownloadedAssets: [String: DownloadedAsset] = [:],
        photoSaver: (any PhotoLibrarySaving)? = ResultGalleryView.defaultPhotoSaver()
    ) {
        self._viewModel = StateObject(
            wrappedValue: ResultGalleryViewModel(
                status: status,
                downloader: downloader,
                initialOriginalAsset: initialOriginalAsset,
                initialDownloadedAssets: initialDownloadedAssets
            )
        )
        self.activeConnection = activeConnection
        self.photoSaver = photoSaver
    }

    public var body: some View {
        let presentation = presentation
        return ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.025, green: 0.034, blue: 0.038),
                    Color(red: 0.055, green: 0.071, blue: 0.075),
                    Color.black
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(spacing: 14) {
                    beforeAfterComparison(presentation)
                    variantTabs(presentation)
                    recipePanel(presentation)
                    actionPanel(presentation)
                }
                .padding(.horizontal, 14)
                .padding(.top, 12)
                .padding(.bottom, 20)
                .frame(maxWidth: 620)
                .frame(maxWidth: .infinity)
            }
        }
        .navigationTitle(presentation.title)
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
        .toolbar {
            ToolbarItem(placement: .automatic) {
                Button {
                } label: {
                    Image(systemName: "ellipsis")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(.white.opacity(0.86))
                }
                .buttonStyle(.plain)
                .accessibilityLabel(language == .chinese ? "更多" : "More")
            }
        }
        .task {
            await downloadSelectedVariantIfNeeded()
            refreshShareURL()
        }
    }

    private var language: AppLanguage {
        AppLanguage(rawValue: languageRawValue) ?? .chinese
    }

    private var presentation: ResultScreenPresentation {
        ResultScreenPresentation(
            comparison: viewModel.comparisonPresentation,
            variants: viewModel.variants,
            selectedVariantID: viewModel.selectedVariantID,
            recipe: viewModel.recipePresentation,
            explanation: viewModel.explanation,
            state: viewModel.state,
            saveState: saveFlow.state,
            language: language,
            canShare: shareURL != nil
        )
    }

    private func beforeAfterComparison(_ presentation: ResultScreenPresentation) -> some View {
        GeometryReader { geometry in
            let width = geometry.size.width
            let x = width * comparisonPosition

            ZStack(alignment: .trailing) {
                ResultImageLayer(
                    title: presentation.beforeLabel,
                    detail: language == .chinese ? "Source" : "Source photo",
                    symbol: "photo",
                    asset: viewModel.originalPreviewAsset,
                    fallbackColor: Color(red: 0.18, green: 0.23, blue: 0.24)
                )

                ResultImageLayer(
                    title: presentation.afterLabel,
                    detail: presentation.afterDetail,
                    symbol: viewModel.downloadedAssetForSelectedVariant == nil ? "wand.and.stars" : "checkmark.seal.fill",
                    asset: viewModel.downloadedAssetForSelectedVariant,
                    fallbackColor: Color(red: 0.36, green: 0.48, blue: 0.50)
                )
                .frame(width: max(0, width * (1 - comparisonPosition)), alignment: .trailing)
                .clipped()

                VStack {
                    HStack {
                        ResultPillLabel(title: presentation.beforeLabel)
                        Spacer()
                        ResultPillLabel(title: presentation.afterLabel)
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity)
                    Spacer()
                }

                Rectangle()
                    .fill(.white.opacity(0.88))
                    .frame(width: 2)
                    .position(x: x, y: geometry.size.height / 2)

                Circle()
                    .fill(.white)
                    .frame(width: 42, height: 42)
                    .overlay(
                        Image(systemName: "chevron.left.chevron.right")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(.black.opacity(0.72))
                    )
                    .position(x: x, y: geometry.size.height / 2)
                    .shadow(color: .black.opacity(0.25), radius: 10, y: 3)
            }
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { value in
                        comparisonPosition = min(0.92, max(0.08, value.location.x / max(width, 1)))
                    }
            )
        }
        .frame(height: comparisonHeight)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(.white.opacity(0.12), lineWidth: 1)
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel(presentation.comparisonAccessibilityLabel)
    }

    private func variantTabs(_ presentation: ResultScreenPresentation) -> some View {
        HStack(spacing: 6) {
            ForEach(presentation.variantTabs) { tab in
                Button {
                    Task {
                        await selectVariant(tab.id)
                    }
                } label: {
                    Text(tab.title)
                        .font(.callout.weight(.semibold))
                        .foregroundStyle(tab.isSelected ? Color(red: 0.55, green: 0.96, blue: 0.89) : .white.opacity(0.76))
                        .frame(maxWidth: .infinity, minHeight: 48)
                        .background(tab.isSelected ? .white.opacity(0.08) : .clear, in: Capsule())
                }
                .buttonStyle(.plain)
            }
        }
        .padding(6)
        .background(.white.opacity(0.07), in: Capsule())
    }

    private func recipePanel(_ presentation: ResultScreenPresentation) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(presentation.recipeTitle)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.white)

            if presentation.recipeChips.isEmpty == false {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 86), spacing: 8)], alignment: .leading, spacing: 8) {
                    ForEach(presentation.recipeChips, id: \.self) { chip in
                        Text(chip)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white)
                            .frame(maxWidth: .infinity, minHeight: 34)
                            .padding(.horizontal, 10)
                            .background(.white.opacity(0.08), in: Capsule())
                    }
                }
            }

            if let note = presentation.recipeNote {
                Text(note)
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.64))
                    .lineLimit(2)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.white.opacity(0.055), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(.white.opacity(0.08), lineWidth: 1)
        )
    }

    private var comparisonHeight: CGFloat {
        #if os(iOS)
        min(500, max(340, UIScreen.main.bounds.height * 0.43))
        #else
        500
        #endif
    }

    private func actionPanel(_ presentation: ResultScreenPresentation) -> some View {
        VStack(spacing: 12) {
            if shouldShowDownloadAction(presentation) {
                Button {
                    Task {
                        await downloadSelectedVariant()
                    }
                } label: {
                    ResultActionLabel(action: presentation.downloadAction, isProminent: false)
                }
                .buttonStyle(.plain)
                .disabled(presentation.downloadAction.isEnabled == false || viewModel.selectedVariant == nil)
            }

            HStack(spacing: 12) {
                Button {
                    saveSelectedVariant()
                } label: {
                    ResultActionLabel(action: presentation.saveAction, isProminent: false)
                }
                .buttonStyle(.plain)
                .disabled(presentation.saveAction.isEnabled == false)

                shareButton(presentation)
            }

            sharePlatformRow(presentation)

            if let statusMessage = presentation.statusMessage {
                Text(statusMessage)
                    .font(.callout)
                    .foregroundStyle(Color(red: 1.0, green: 0.48, blue: 0.42))
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            if saveFlow.state == .permissionDenied {
                Button(saveFlow.recoveryActionTitle ?? (language == .chinese ? "打开设置" : "Open Settings")) {
                    openRecoveryDestination(saveFlow.recoveryDestination)
                }
                .font(.callout.weight(.semibold))
                .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                .frame(maxWidth: .infinity, minHeight: 42)
            }
        }
    }

    private func shouldShowDownloadAction(_ presentation: ResultScreenPresentation) -> Bool {
        presentation.downloadAction.isEnabled || viewModel.downloadedAssetForSelectedVariant == nil
    }

    @ViewBuilder
    private func shareButton(_ presentation: ResultScreenPresentation) -> some View {
        if let shareURL {
            if let caption = viewModel.shareCaptionForSelectedVariant {
                ShareLink(item: shareURL, message: Text(caption)) {
                    ResultActionLabel(action: presentation.shareAction, isProminent: true)
                }
                .buttonStyle(.plain)
            } else {
                ShareLink(item: shareURL) {
                    ResultActionLabel(action: presentation.shareAction, isProminent: true)
                }
                .buttonStyle(.plain)
            }
        } else {
            Button {
            } label: {
                ResultActionLabel(action: presentation.shareAction, isProminent: true)
            }
            .buttonStyle(.plain)
            .disabled(true)
        }
    }

    private func sharePlatformRow(_ presentation: ResultScreenPresentation) -> some View {
        HStack(spacing: 8) {
            ForEach(presentation.sharePlatformTitles, id: \.self) { title in
                sharePlatformControl(title)
            }
        }
    }

    @ViewBuilder
    private func sharePlatformControl(_ title: String) -> some View {
        if let shareURL {
            if let caption = viewModel.shareCaptionForSelectedVariant {
                ShareLink(item: shareURL, message: Text(caption)) {
                    ResultPlatformLabel(title: title, isEnabled: true)
                }
                .buttonStyle(.plain)
            } else {
                ShareLink(item: shareURL) {
                    ResultPlatformLabel(title: title, isEnabled: true)
                }
                .buttonStyle(.plain)
            }
        } else {
            Button {
            } label: {
                ResultPlatformLabel(title: title, isEnabled: false)
            }
            .buttonStyle(.plain)
            .disabled(true)
        }
    }

    @MainActor
    private func downloadSelectedVariant() async {
        await viewModel.downloadSelectedVariant(connection: activeConnection())
        refreshShareURL()
    }

    @MainActor
    private func downloadSelectedVariantIfNeeded() async {
        await viewModel.downloadSelectedVariantIfNeeded(connection: activeConnection())
    }

    @MainActor
    private func selectVariant(_ id: String) async {
        await viewModel.selectVariantAndDownloadIfNeeded(id: id, connection: activeConnection())
        refreshShareURL()
    }

    private func refreshShareURL() {
        guard let variant = viewModel.selectedVariant,
              let asset = viewModel.downloadedAssetForSelectedVariant else {
            shareURL = nil
            return
        }
        shareURL = try? ResultShareFile.write(asset: asset, variantID: variant.id)
    }

    private func saveSelectedVariant() {
        guard let selectedVariant = viewModel.selectedVariant else {
            saveFlow.markFailed("Select a variant before saving.")
            return
        }
        guard let asset = viewModel.downloadedAsset(for: selectedVariant.id) else {
            saveFlow.markFailed("Download this variant before saving.")
            return
        }
        guard let photoSaver else {
            saveFlow.markFailed("Photo saving is only available on iPhone.")
            return
        }

        Task {
            await saveFlow.save(asset, using: photoSaver)
        }
    }

    private func openRecoveryDestination(_ destination: PhotoSaveFlow.RecoveryDestination?) {
        switch destination {
        case .appSettings:
            if let settingsURL {
                openURL(settingsURL)
            }
        case nil:
            break
        }
    }

    private var settingsURL: URL? {
        #if canImport(UIKit)
        URL(string: UIApplication.openSettingsURLString)
        #else
        nil
        #endif
    }

    public static func defaultPhotoSaver() -> (any PhotoLibrarySaving)? {
        #if os(iOS)
        IOSPhotoLibrarySaver()
        #else
        nil
        #endif
    }
}

private struct ResultImageLayer: View {
    let title: String
    let detail: String
    let symbol: String
    let asset: DownloadedAsset?
    let fallbackColor: Color

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            if let image = previewImage {
                image
                    .resizable()
                    .scaledToFill()
                    .accessibilityHidden(true)
            } else {
                LinearGradient(
                    colors: [fallbackColor.opacity(0.92), fallbackColor.opacity(0.52), .black.opacity(0.72)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )

                VStack(spacing: 10) {
                    Image(systemName: symbol)
                        .font(.system(size: 34, weight: .semibold))
                        .foregroundStyle(.white.opacity(0.8))
                        .accessibilityHidden(true)

                    Text(title)
                        .font(.headline.weight(.semibold))
                        .foregroundStyle(.white)

                    Text(detail)
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.68))
                        .multilineTextAlignment(.center)
                }
                .padding(16)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .clipped()
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

private struct ResultPillLabel: View {
    let title: String

    var body: some View {
        Text(title)
            .font(.caption.weight(.semibold))
            .foregroundStyle(.white)
            .lineLimit(1)
            .minimumScaleFactor(0.86)
            .padding(.horizontal, 10)
            .frame(height: 30)
            .background(.black.opacity(0.44), in: Capsule())
            .fixedSize(horizontal: true, vertical: false)
    }
}

private struct ResultActionLabel: View {
    let action: ResultScreenPresentation.Action
    let isProminent: Bool

    var body: some View {
        Label(action.title, systemImage: action.systemImage)
            .font(.callout.weight(.semibold))
            .foregroundStyle(isProminent ? .black : .white)
            .frame(maxWidth: .infinity, minHeight: 52)
            .background(backgroundStyle, in: Capsule())
            .overlay(Capsule().stroke(.white.opacity(isProminent ? 0 : 0.1), lineWidth: 1))
            .opacity(action.isEnabled ? 1 : 0.48)
    }

    private var backgroundStyle: Color {
        if isProminent {
            return Color(red: 0.55, green: 0.96, blue: 0.89)
        }
        return Color.white.opacity(0.09)
    }
}

private struct ResultPlatformLabel: View {
    let title: String
    let isEnabled: Bool

    var body: some View {
        Text(title)
            .font(.caption.weight(.semibold))
            .foregroundStyle(.white)
            .lineLimit(1)
            .minimumScaleFactor(0.72)
            .frame(maxWidth: .infinity, minHeight: 40)
            .background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(.white.opacity(0.08), lineWidth: 1)
            )
            .opacity(isEnabled ? 1 : 0.42)
    }
}

private enum ResultShareFile {
    static func write(asset: DownloadedAsset, variantID: String) throws -> URL {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("AgentPocketShares", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)

        let fileURL = directory.appendingPathComponent(
            "\(safeFileName(from: variantID)).\(fileExtension(for: asset.mimeType))"
        )
        try asset.data.write(to: fileURL, options: .atomic)
        return fileURL
    }

    private static func safeFileName(from value: String) -> String {
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-_"))
        let scalars = value.unicodeScalars.map { scalar in
            allowed.contains(scalar) ? Character(scalar) : "_"
        }
        let name = String(scalars)
        return name.isEmpty ? "agent-pocket-result" : name
    }

    private static func fileExtension(for mimeType: String) -> String {
        switch mimeType.lowercased() {
        case "image/jpeg":
            return "jpg"
        case "image/heic":
            return "heic"
        case "image/png":
            return "png"
        default:
            return "bin"
        }
    }
}
