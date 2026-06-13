import SwiftUI

public struct AgentScannerView: View {
    public let onResult: (AgentScanResult) -> Void

    public init(onResult: @escaping (AgentScanResult) -> Void) {
        self.onResult = onResult
    }

    public var body: some View {
        #if os(iOS) && canImport(VisionKit)
        ZStack(alignment: .bottom) {
            AgentDataScannerRepresentable(onResult: onResult)
                .ignoresSafeArea()

            VStack(spacing: 10) {
                Text("Scan")
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.92))
                Text("Tap a QR code, barcode, link, or visible text to choose the next action.")
                    .font(.footnote)
                    .foregroundStyle(.white.opacity(0.68))
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(.black.opacity(0.48), in: RoundedRectangle(cornerRadius: AgentPocketDesignTokens.controlRadius, style: .continuous))
            .padding(.horizontal, 18)
            .padding(.bottom, 18)
        }
        .background(.black)
        #else
        ContentUnavailableView(
            "Scanner Unavailable",
            systemImage: "qrcode.viewfinder",
            description: Text("Open Kaka on iPhone to scan codes and text.")
        )
        #endif
    }
}

#if os(iOS) && canImport(VisionKit)
import VisionKit

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
