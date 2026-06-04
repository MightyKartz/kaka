import AgentPocketCore
import SwiftUI
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

public struct VisionResultView: View {
    private let status: TaskStatusResponse
    private let originalAsset: DownloadedAsset?

    public init(
        status: TaskStatusResponse,
        originalAsset: DownloadedAsset? = nil
    ) {
        self.status = status
        self.originalAsset = originalAsset
    }

    public var body: some View {
        let language = AppLanguage.resolved(storedValue: nil)
        let vision = status.vision

        ZStack {
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
                VStack(alignment: .leading, spacing: 16) {
                    VisionSourceImage(asset: originalAsset)

                    VStack(alignment: .leading, spacing: 12) {
                        HStack(alignment: .top, spacing: 10) {
                            Image(systemName: systemImage(for: vision?.mode))
                                .font(.system(size: 22, weight: .bold))
                                .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                                .frame(width: 34, height: 34)
                                .background(.white.opacity(0.08), in: Circle())
                                .accessibilityHidden(true)

                            VStack(alignment: .leading, spacing: 5) {
                                Text(vision?.title ?? fallbackTitle(language: language))
                                    .font(.title3.weight(.bold))
                                    .foregroundStyle(.white)
                                    .fixedSize(horizontal: false, vertical: true)

                                if let confidenceText = confidenceText(vision?.confidence, language: language) {
                                    Text(confidenceText)
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.white.opacity(0.62))
                                }
                            }
                        }

                        Text(vision?.summary ?? fallbackSummary(language: language))
                            .font(.body)
                            .foregroundStyle(.white.opacity(0.82))
                            .lineSpacing(3)
                            .fixedSize(horizontal: false, vertical: true)

                        if let text = vision?.text, text.isEmpty == false {
                            Text(text)
                                .font(.callout)
                                .foregroundStyle(.white.opacity(0.72))
                                .lineSpacing(3)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .padding(16)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(.white.opacity(0.10), lineWidth: 1)
                    )

                    if let sections = vision?.sections, sections.isEmpty == false {
                        VStack(alignment: .leading, spacing: 12) {
                            ForEach(Array(sections.enumerated()), id: \.offset) { _, section in
                                VisionResultSectionView(section: section, language: language)
                            }
                        }
                    } else if let items = vision?.items, items.isEmpty == false {
                        VStack(alignment: .leading, spacing: 10) {
                            Text(language == .chinese ? "关键结果" : "Key Results")
                                .font(.headline.weight(.bold))
                                .foregroundStyle(.white)

                            ForEach(Array(items.enumerated()), id: \.offset) { _, item in
                                VisionResultItemRow(item: item, language: language)
                            }
                        }
                    }
                }
                .padding(.horizontal, 14)
                .padding(.top, 12)
                .padding(.bottom, 28)
                .frame(maxWidth: 620)
                .frame(maxWidth: .infinity)
            }
        }
        .navigationTitle(language == .chinese ? "智能结果" : "Vision Result")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
    }

    private func systemImage(for mode: String?) -> String {
        switch mode {
        case "scan":
            return "doc.text.viewfinder"
        case "translate":
            return "translate"
        case "food":
            return "fork.knife"
        case "identify":
            return "viewfinder.circle"
        default:
            return "sparkles"
        }
    }

    private func fallbackTitle(language: AppLanguage) -> String {
        language == .chinese ? "智能结果" : "Vision Result"
    }

    private func fallbackSummary(language: AppLanguage) -> String {
        language == .chinese ? "本机智能体已完成视觉任务。" : "The local agent completed the vision task."
    }

    private func confidenceText(_ confidence: Double?, language: AppLanguage) -> String? {
        guard let confidence else {
            return nil
        }
        let percent = Int((confidence * 100).rounded())
        return language == .chinese ? "置信度 \(percent)%" : "Confidence \(percent)%"
    }
}

private struct VisionSourceImage: View {
    let asset: DownloadedAsset?

    var body: some View {
        ZStack {
            if let image = previewImage {
                image
                    .resizable()
                    .scaledToFit()
                    .frame(maxWidth: .infinity)
                    .accessibilityHidden(true)
            } else {
                LinearGradient(
                    colors: [
                        Color(red: 0.22, green: 0.27, blue: 0.28),
                        Color(red: 0.10, green: 0.13, blue: 0.13)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                Image(systemName: "photo")
                    .font(.system(size: 30, weight: .medium))
                    .foregroundStyle(.white.opacity(0.52))
                    .accessibilityHidden(true)
            }
        }
        .frame(maxWidth: .infinity)
        .frame(minHeight: 180)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(.white.opacity(0.12), lineWidth: 1)
        )
    }

    private var previewImage: Image? {
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

private struct VisionResultSectionView: View {
    let section: TaskStatusResponse.VisionSection
    let language: AppLanguage

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: systemImage)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                    .accessibilityHidden(true)

                Text(section.title)
                    .font(.headline.weight(.bold))
                    .foregroundStyle(.white)
                    .fixedSize(horizontal: false, vertical: true)
            }

            ForEach(Array(section.items.enumerated()), id: \.offset) { _, item in
                VisionResultItemRow(item: item, language: language)
            }
        }
    }

    private var systemImage: String {
        switch section.kind {
        case "nutrition":
            return "chart.bar.xaxis"
        case "ocr":
            return "text.viewfinder"
        case "codes":
            return "qrcode.viewfinder"
        case "candidates":
            return "list.bullet.rectangle"
        case "assumptions":
            return "info.circle"
        default:
            return "sparkles"
        }
    }
}

private struct VisionResultItemRow: View {
    let item: TaskStatusResponse.VisionItem
    let language: AppLanguage

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(item.title)
                    .font(.callout.weight(.bold))
                    .foregroundStyle(.white)
                    .fixedSize(horizontal: false, vertical: true)

                Spacer(minLength: 8)

                if let confidenceText = confidenceText {
                    Text(confidenceText)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(Color(red: 0.55, green: 0.96, blue: 0.89))
                }
            }

            if let value = item.value, value.isEmpty == false {
                Text(value)
                    .font(.body.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.84))
                    .fixedSize(horizontal: false, vertical: true)
            }

            if let subtitle = item.subtitle, subtitle.isEmpty == false {
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.58))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(.white.opacity(0.08), lineWidth: 1)
        )
    }

    private var confidenceText: String? {
        guard let confidence = item.confidence else {
            return nil
        }
        let percent = Int((confidence * 100).rounded())
        return language == .chinese ? "\(percent)%" : "\(percent)%"
    }
}
