import SwiftUI

#if os(iOS) && canImport(AVFoundation) && canImport(UIKit)
@preconcurrency import AVFoundation
@preconcurrency import UIKit
#endif

public struct PairingScannerView: View {
    private let onCodeScanned: (String) -> Void

    public init(onCodeScanned: @escaping (String) -> Void) {
        self.onCodeScanned = onCodeScanned
    }

    public var body: some View {
        #if os(iOS) && canImport(AVFoundation) && canImport(UIKit)
        PairingScannerContent(onCodeScanned: onCodeScanned)
        #else
        ScannerUnavailableView(
            title: "Camera Unavailable",
            message: "QR scanning is available on iPhone. Use manual connection on this platform."
        )
        #endif
    }
}

#if os(iOS) && canImport(AVFoundation) && canImport(UIKit)
private struct PairingScannerContent: View {
    @State private var authorizationStatus = AVCaptureDevice.authorizationStatus(for: .video)
    @State private var setupError: String?
    let onCodeScanned: (String) -> Void

    var body: some View {
        Group {
            switch authorizationStatus {
            case .authorized:
                ZStack {
                    QRScannerRepresentable(
                        onCodeScanned: onCodeScanned,
                        onSetupFailed: { setupError = $0 }
                    )

                    RoundedRectangle(cornerRadius: 22)
                        .stroke(.white.opacity(0.88), lineWidth: 3)
                        .padding(42)

                    VStack {
                        Spacer()
                        Text("Center the local agent pairing QR in the frame")
                            .font(.callout.weight(.medium))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 10)
                            .background(.black.opacity(0.58), in: Capsule())
                            .padding(.bottom, 18)
                    }
                }
                .overlay {
                    if let setupError {
                        ScannerUnavailableView(title: "Scanner Error", message: setupError)
                    }
                }
            case .notDetermined:
                ScannerUnavailableView(
                    title: "Camera Permission",
                    message: "Allow camera access to scan the local agent pairing QR."
                )
                .task {
                    AVCaptureDevice.requestAccess(for: .video) { granted in
                        Task { @MainActor in
                            authorizationStatus = granted ? .authorized : .denied
                        }
                    }
                }
            case .denied, .restricted:
                ScannerUnavailableView(
                    title: "Camera Access Needed",
                    message: "Allow camera access in Settings, or connect manually."
                )
            @unknown default:
                ScannerUnavailableView(
                    title: "Camera Unavailable",
                    message: "This device cannot scan QR codes right now."
                )
            }
        }
        .frame(maxWidth: .infinity)
        .frame(height: 340)
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Pairing QR scanner")
    }
}

private struct QRScannerRepresentable: UIViewRepresentable {
    let onCodeScanned: (String) -> Void
    let onSetupFailed: (String) -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(onCodeScanned: onCodeScanned)
    }

    func makeUIView(context: Context) -> PreviewView {
        let view = PreviewView()
        view.videoPreviewLayer.videoGravity = .resizeAspectFill

        let session = AVCaptureSession()
        session.beginConfiguration()
        defer { session.commitConfiguration() }

        guard let device = AVCaptureDevice.default(for: .video) else {
            onSetupFailed("No camera is available for QR scanning.")
            return view
        }

        do {
            let input = try AVCaptureDeviceInput(device: device)
            guard session.canAddInput(input) else {
                onSetupFailed("Camera input is not available.")
                return view
            }
            session.addInput(input)
        } catch {
            onSetupFailed("Camera input could not be started.")
            return view
        }

        let output = AVCaptureMetadataOutput()
        guard session.canAddOutput(output) else {
            onSetupFailed("QR scanning output is not available.")
            return view
        }
        session.addOutput(output)
        output.setMetadataObjectsDelegate(context.coordinator, queue: DispatchQueue.main)
        output.metadataObjectTypes = [.qr]

        view.session = session
        context.coordinator.session = session
        context.coordinator.start()
        return view
    }

    func updateUIView(_ uiView: PreviewView, context: Context) {}

    static func dismantleUIView(_ uiView: PreviewView, coordinator: Coordinator) {
        coordinator.stop()
    }

    final class Coordinator: NSObject, AVCaptureMetadataOutputObjectsDelegate {
        private let onCodeScanned: (String) -> Void
        private let sessionQueue = DispatchQueue(label: "AgentPocket.QRScanner.session")
        private var didScan = false
        private var sessionBox: CaptureSessionBox?

        var session: AVCaptureSession? {
            get { sessionBox?.session }
            set { sessionBox = newValue.map(CaptureSessionBox.init) }
        }

        init(onCodeScanned: @escaping (String) -> Void) {
            self.onCodeScanned = onCodeScanned
        }

        func metadataOutput(
            _ output: AVCaptureMetadataOutput,
            didOutput metadataObjects: [AVMetadataObject],
            from connection: AVCaptureConnection
        ) {
            guard didScan == false,
                  let object = metadataObjects.compactMap({ $0 as? AVMetadataMachineReadableCodeObject }).first,
                  object.type == .qr,
                  let value = object.stringValue else {
                return
            }
            didScan = true
            stop()
            onCodeScanned(value)
        }

        func start() {
            guard let sessionBox else {
                return
            }
            sessionQueue.async {
                guard sessionBox.session.isRunning == false else {
                    return
                }
                sessionBox.session.startRunning()
            }
        }

        func stop() {
            guard let sessionBox else {
                return
            }
            sessionQueue.async {
                guard sessionBox.session.isRunning else {
                    return
                }
                sessionBox.session.stopRunning()
            }
        }
    }
}

private final class CaptureSessionBox: @unchecked Sendable {
    let session: AVCaptureSession

    init(session: AVCaptureSession) {
        self.session = session
    }
}

private final class PreviewView: UIView {
    override class var layerClass: AnyClass {
        AVCaptureVideoPreviewLayer.self
    }

    var videoPreviewLayer: AVCaptureVideoPreviewLayer {
        layer as! AVCaptureVideoPreviewLayer
    }

    var session: AVCaptureSession? {
        get { videoPreviewLayer.session }
        set { videoPreviewLayer.session = newValue }
    }
}
#endif

private struct ScannerUnavailableView: View {
    let title: String
    let message: String

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "qrcode.viewfinder")
                .font(.system(size: 34, weight: .semibold))
                .foregroundStyle(.secondary)

            Text(title)
                .font(.headline)

            Text(message)
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .lineLimit(nil)
        }
        .frame(maxWidth: .infinity, minHeight: 220)
        .padding(18)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 18))
    }
}
