import AgentPocketCore
import Foundation

public struct ResultScreenPresentation: Equatable, Sendable {
    public struct Action: Equatable, Sendable {
        public let title: String
        public let systemImage: String
        public let isEnabled: Bool
    }

    public struct VariantTab: Equatable, Identifiable, Sendable {
        public let id: String
        public let title: String
        public let isSelected: Bool
    }

    public let title: String
    public let beforeLabel: String
    public let afterLabel: String
    public let afterDetail: String
    public let comparisonAccessibilityLabel: String
    public let variantTabs: [VariantTab]
    public let downloadAction: Action
    public let saveAction: Action
    public let shareAction: Action
    public let statusMessage: String?

    public init(
        comparison: ResultGalleryViewModel.ComparisonPresentation,
        variants: [TaskStatusResponse.Variant],
        selectedVariantID: String?,
        state: ResultGalleryViewModel.State,
        saveState: PhotoSaveFlow.State,
        language: AppLanguage,
        canShare: Bool
    ) {
        title = language == .chinese ? "成片结果" : "Master Result"
        beforeLabel = language == .chinese ? "原图" : comparison.beforeLabel
        afterLabel = Self.localizedVariantTitle(comparison.afterLabel, language: language)
        afterDetail = Self.localizedAfterDetail(comparison.afterDetail, language: language)
        comparisonAccessibilityLabel = language == .chinese ? "原图与成片前后对比" : "Before and after comparison"
        variantTabs = variants.map { variant in
            VariantTab(
                id: variant.id,
                title: Self.localizedVariantTitle(variant.label, language: language),
                isSelected: variant.id == selectedVariantID
            )
        }
        downloadAction = Self.downloadAction(state: state, comparison: comparison, language: language)
        saveAction = Self.saveAction(saveState: saveState, isDownloaded: comparison.isDownloaded, language: language)
        shareAction = Action(
            title: language == .chinese ? "分享" : "Share",
            systemImage: "square.and.arrow.up",
            isEnabled: canShare && comparison.isDownloaded
        )
        statusMessage = Self.statusMessage(resultState: state, saveState: saveState, language: language)
    }

    private static func downloadAction(
        state: ResultGalleryViewModel.State,
        comparison: ResultGalleryViewModel.ComparisonPresentation,
        language: AppLanguage
    ) -> Action {
        switch state {
        case .downloading:
            return Action(
                title: language == .chinese ? "下载中" : "Downloading",
                systemImage: "arrow.down.circle",
                isEnabled: false
            )
        case .downloaded:
            return Action(
                title: language == .chinese ? "已下载" : "Downloaded",
                systemImage: "checkmark.circle.fill",
                isEnabled: false
            )
        case .ready, .failed:
            return Action(
                title: language == .chinese ? "下载成片" : "Download",
                systemImage: "arrow.down.circle",
                isEnabled: comparison.isDownloaded == false
            )
        }
    }

    private static func saveAction(
        saveState: PhotoSaveFlow.State,
        isDownloaded: Bool,
        language: AppLanguage
    ) -> Action {
        switch saveState {
        case .requestingPermission:
            return Action(title: language == .chinese ? "授权中" : "Requesting", systemImage: "square.and.arrow.down", isEnabled: false)
        case .saving:
            return Action(title: language == .chinese ? "保存中" : "Saving", systemImage: "square.and.arrow.down", isEnabled: false)
        case .saved:
            return Action(title: language == .chinese ? "已保存" : "Saved", systemImage: "checkmark.circle.fill", isEnabled: false)
        case .idle, .permissionDenied, .failed:
            return Action(title: language == .chinese ? "保存" : "Save", systemImage: "square.and.arrow.down", isEnabled: isDownloaded && saveState.isBusy == false)
        }
    }

    private static func localizedAfterDetail(_ detail: String, language: AppLanguage) -> String {
        guard language == .chinese else {
            return detail
        }
        let localizedDetail = detail
            .replacingOccurrences(of: "Master", with: "大师")
            .replacingOccurrences(of: "Social", with: "社交")
        if detail.hasPrefix("Save-ready ") {
            return localizedDetail.replacingOccurrences(of: "Save-ready ", with: "保存版 ")
        }
        if detail.hasPrefix("Share-ready ") {
            return localizedDetail.replacingOccurrences(of: "Share-ready ", with: "分享版 ")
        }
        if detail.hasSuffix(" result") {
            return localizedDetail.replacingOccurrences(of: " result", with: " 成片")
        }
        return localizedDetail
    }

    private static func localizedVariantTitle(_ title: String, language: AppLanguage) -> String {
        guard language == .chinese else {
            return title
        }

        switch title.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
        case "master":
            return "大师"
        case "social":
            return "社交"
        default:
            return title
        }
    }

    private static func statusMessage(
        resultState: ResultGalleryViewModel.State,
        saveState: PhotoSaveFlow.State,
        language: AppLanguage
    ) -> String? {
        switch resultState {
        case .failed(let message):
            return message
        case .ready, .downloading, .downloaded:
            break
        }

        switch saveState {
        case .permissionDenied:
            return language == .chinese ? "请在设置中允许相册权限后保存。" : "Allow photo library access in Settings to save this result."
        case .failed(let message):
            return message
        case .idle, .requestingPermission, .saving, .saved:
            return nil
        }
    }
}
