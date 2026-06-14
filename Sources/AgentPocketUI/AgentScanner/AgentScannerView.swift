import SwiftUI

public struct AgentScannerCopy: Equatable, Sendable {
    public let language: AppLanguage

    public init(language: AppLanguage) {
        self.language = language
    }

    public var title: String {
        language == .chinese ? "扫码" : "Scan"
    }

    public var instruction: String {
        language == .chinese
            ? "点按二维码、条码、链接或可见文本，再选择下一步。"
            : "Tap a QR code, barcode, link, or visible text to choose the next action."
    }

    public var closeTitle: String {
        language == .chinese ? "关闭" : "Close"
    }

    public var closeAccessibilityLabel: String {
        language == .chinese ? "关闭扫码" : "Close scanner"
    }

    public var unavailableTitle: String {
        language == .chinese ? "扫码不可用" : "Scanner Unavailable"
    }

    public var unavailableDescription: String {
        language == .chinese
            ? "请在 iPhone 上打开 Pocket Agent 扫码；模拟器无法使用相机扫码。"
            : "Open Pocket Agent on iPhone to scan codes and text. The simulator cannot use the camera scanner."
    }
}

public struct AgentScannerView: View {
    public let onResult: (AgentScanResult) -> Void
    public let onCancel: () -> Void

    public init(
        onResult: @escaping (AgentScanResult) -> Void,
        onCancel: @escaping () -> Void = {}
    ) {
        self.onResult = onResult
        self.onCancel = onCancel
    }

    public var body: some View {
        let copy = AgentScannerCopy(language: AppLanguage.resolved(storedValue: nil))
        #if os(iOS) && canImport(VisionKit)
        if DataScannerViewController.isSupported && DataScannerViewController.isAvailable {
            ZStack(alignment: .bottom) {
                AgentDataScannerRepresentable(onResult: onResult)
                    .ignoresSafeArea()

                VStack(spacing: 10) {
                    Text(copy.title)
                        .font(.headline.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.92))
                    Text(copy.instruction)
                        .font(.footnote)
                        .foregroundStyle(.white.opacity(0.72))
                        .multilineTextAlignment(.center)
                        .lineLimit(2)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(.black.opacity(0.56), in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
                .padding(.horizontal, 18)
                .padding(.bottom, 18)
            }
            .overlay(alignment: .topLeading) {
                Button(action: onCancel) {
                    Label(copy.closeTitle, systemImage: "xmark")
                        .font(.callout.weight(.semibold))
                        .labelStyle(.titleAndIcon)
                        .padding(.horizontal, 12)
                        .frame(minHeight: 38)
                }
                .buttonStyle(AgentPocketDarkSecondaryButtonStyle())
                .accessibilityLabel(copy.closeAccessibilityLabel)
                .padding(.leading, 18)
                .padding(.top, 18)
            }
            .background(.black)
        } else {
            AgentScannerUnavailableView(copy: copy, onCancel: onCancel)
        }
        #else
        ContentUnavailableView(
            copy.unavailableTitle,
            systemImage: "qrcode.viewfinder",
            description: Text(copy.unavailableDescription)
        )
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button(copy.closeTitle, action: onCancel)
            }
        }
        #endif
    }
}

#if os(iOS) && canImport(VisionKit)
import VisionKit

private struct AgentScannerUnavailableView: View {
    let copy: AgentScannerCopy
    let onCancel: () -> Void

    var body: some View {
        NavigationStack {
            ContentUnavailableView(
                copy.unavailableTitle,
                systemImage: "qrcode.viewfinder",
                description: Text(copy.unavailableDescription)
            )
            .navigationTitle(copy.title)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(copy.closeTitle, action: onCancel)
                }
            }
        }
    }
}

private struct AgentDataScannerRepresentable: UIViewControllerRepresentable {
    let onResult: (AgentScanResult) -> Void

    func makeUIViewController(context: Context) -> DataScannerViewController {
        let scanner = DataScannerViewController(
            recognizedDataTypes: [.text(), .barcode()],
            qualityLevel: .balanced,
            recognizesMultipleItems: false,
            isHighFrameRateTrackingEnabled: false,
            isPinchToZoomEnabled: true,
            isGuidanceEnabled: true,
            isHighlightingEnabled: true
        )
        scanner.delegate = context.coordinator
        try? scanner.startScanning()
        return scanner
    }

    func updateUIViewController(_ uiViewController: DataScannerViewController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onResult: onResult)
    }

    final class Coordinator: NSObject, DataScannerViewControllerDelegate {
        let onResult: (AgentScanResult) -> Void

        init(onResult: @escaping (AgentScanResult) -> Void) {
            self.onResult = onResult
        }

        func dataScanner(
            _ dataScanner: DataScannerViewController,
            didTapOn item: RecognizedItem
        ) {
            switch item {
            case .text(let text):
                onResult(AgentScanResult(rawValue: text.transcript))
            case .barcode(let barcode):
                onResult(AgentScanResult(rawValue: barcode.payloadStringValue ?? ""))
            @unknown default:
                break
            }
        }
    }
}
#endif
