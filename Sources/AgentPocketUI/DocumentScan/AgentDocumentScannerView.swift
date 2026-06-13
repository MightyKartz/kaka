#if os(iOS) && canImport(VisionKit)
import SwiftUI
import UIKit
import VisionKit

public struct AgentDocumentScannerView: UIViewControllerRepresentable {
    public let onPDF: (Data) -> Void
    public let onCancel: () -> Void

    public init(onPDF: @escaping (Data) -> Void, onCancel: @escaping () -> Void) {
        self.onPDF = onPDF
        self.onCancel = onCancel
    }

    public func makeUIViewController(context: Context) -> VNDocumentCameraViewController {
        let controller = VNDocumentCameraViewController()
        controller.delegate = context.coordinator
        return controller
    }

    public func updateUIViewController(_ uiViewController: VNDocumentCameraViewController, context: Context) {}

    public func makeCoordinator() -> Coordinator {
        Coordinator(onPDF: onPDF, onCancel: onCancel)
    }

    public final class Coordinator: NSObject, VNDocumentCameraViewControllerDelegate {
        let onPDF: (Data) -> Void
        let onCancel: () -> Void

        init(onPDF: @escaping (Data) -> Void, onCancel: @escaping () -> Void) {
            self.onPDF = onPDF
            self.onCancel = onCancel
        }

        public func documentCameraViewController(
            _ controller: VNDocumentCameraViewController,
            didFinishWith scan: VNDocumentCameraScan
        ) {
            let bounds = CGRect(x: 0, y: 0, width: 612, height: 792)
            let renderer = UIGraphicsPDFRenderer(bounds: bounds)
            let data = renderer.pdfData { context in
                for index in 0..<scan.pageCount {
                    context.beginPage()
                    scan.imageOfPage(at: index).draw(in: bounds)
                }
            }
            controller.dismiss(animated: true)
            onPDF(data)
        }

        public func documentCameraViewControllerDidCancel(_ controller: VNDocumentCameraViewController) {
            controller.dismiss(animated: true)
            onCancel()
        }
    }
}
#endif
