#if os(iOS)
import AVFoundation
import SwiftUI
import UIKit

public struct CameraCaptureView: UIViewControllerRepresentable {
    private let onCapture: @MainActor (Data) -> Void
    private let onCancel: @MainActor () -> Void
    private let onFailure: @MainActor (String) -> Void

    public static var isCameraAvailable: Bool {
        CameraCaptureDevice.preferredBackCamera() != nil
    }

    public init(
        onCapture: @escaping @MainActor (Data) -> Void,
        onCancel: @escaping @MainActor () -> Void,
        onFailure: @escaping @MainActor (String) -> Void
    ) {
        self.onCapture = onCapture
        self.onCancel = onCancel
        self.onFailure = onFailure
    }

    public func makeUIViewController(context: Context) -> CameraCaptureViewController {
        CameraCaptureViewController(
            onCapture: onCapture,
            onCancel: onCancel,
            onFailure: onFailure
        )
    }

    public func updateUIViewController(_ uiViewController: CameraCaptureViewController, context: Context) {}
}

public final class CameraCaptureViewController: UIViewController, @preconcurrency AVCapturePhotoCaptureDelegate {
    private let onCapture: @MainActor (Data) -> Void
    private let onCancel: @MainActor () -> Void
    private let onFailure: @MainActor (String) -> Void
    private let session = AVCaptureSession()
    private let photoOutput = AVCapturePhotoOutput()
    private var previewLayer: AVCaptureVideoPreviewLayer?
    private var captureDevice: AVCaptureDevice?
    private var isCapturing = false

    private lazy var closeButton: UIButton = {
        let button = UIButton(type: .system)
        button.translatesAutoresizingMaskIntoConstraints = false
        button.tintColor = .white
        button.backgroundColor = UIColor.black.withAlphaComponent(0.38)
        button.layer.cornerRadius = 22
        button.setImage(UIImage(systemName: "xmark"), for: .normal)
        button.accessibilityIdentifier = "customCameraCloseButton"
        button.addTarget(self, action: #selector(cancelCapture), for: .touchUpInside)
        return button
    }()

    private lazy var shutterButton: UIButton = {
        let button = UIButton(type: .custom)
        button.translatesAutoresizingMaskIntoConstraints = false
        button.backgroundColor = UIColor.white.withAlphaComponent(0.24)
        button.layer.cornerRadius = 38
        button.layer.borderColor = UIColor.white.cgColor
        button.layer.borderWidth = 5
        button.accessibilityIdentifier = "customCameraShutterButton"
        button.addTarget(self, action: #selector(capturePhoto), for: .touchUpInside)
        return button
    }()

    public init(
        onCapture: @escaping @MainActor (Data) -> Void,
        onCancel: @escaping @MainActor () -> Void,
        onFailure: @escaping @MainActor (String) -> Void
    ) {
        self.onCapture = onCapture
        self.onCancel = onCancel
        self.onFailure = onFailure
        super.init(nibName: nil, bundle: nil)
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    public override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        configurePreview()
        configureControls()
        configureSession()
    }

    public override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        previewLayer?.frame = view.bounds
    }

    public override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        if session.isRunning {
            session.stopRunning()
        }
    }

    private func configurePreview() {
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.videoGravity = .resizeAspectFill
        previewLayer.frame = view.bounds
        view.layer.addSublayer(previewLayer)
        self.previewLayer = previewLayer
    }

    private func configureControls() {
        view.addSubview(closeButton)
        view.addSubview(shutterButton)

        NSLayoutConstraint.activate([
            closeButton.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 20),
            closeButton.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 12),
            closeButton.widthAnchor.constraint(equalToConstant: 44),
            closeButton.heightAnchor.constraint(equalToConstant: 44),

            shutterButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            shutterButton.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -30),
            shutterButton.widthAnchor.constraint(equalToConstant: 76),
            shutterButton.heightAnchor.constraint(equalToConstant: 76)
        ])
    }

    private func configureSession() {
        session.beginConfiguration()
        session.sessionPreset = .photo

        guard
            let camera = CameraCaptureDevice.preferredBackCamera(),
            let input = try? AVCaptureDeviceInput(device: camera),
            session.canAddInput(input)
        else {
            session.commitConfiguration()
            reportFailure("Camera input is not available.")
            return
        }
        captureDevice = camera
        session.addInput(input)

        guard session.canAddOutput(photoOutput) else {
            session.commitConfiguration()
            reportFailure("Camera output is not available.")
            return
        }
        session.addOutput(photoOutput)
        session.commitConfiguration()
        session.startRunning()
    }

    @objc private func cancelCapture() {
        Task { @MainActor in
            onCancel()
        }
    }

    @objc private func capturePhoto() {
        guard isCapturing == false else {
            return
        }
        isCapturing = true
        shutterButton.isEnabled = false
        shutterButton.alpha = 0.58

        let settings: AVCapturePhotoSettings
        if photoOutput.availablePhotoCodecTypes.contains(.jpeg) {
            settings = AVCapturePhotoSettings(format: [AVVideoCodecKey: AVVideoCodecType.jpeg])
        } else {
            settings = AVCapturePhotoSettings()
        }
        photoOutput.capturePhoto(with: settings, delegate: self)
    }

    public func photoOutput(
        _ output: AVCapturePhotoOutput,
        didFinishProcessingPhoto photo: AVCapturePhoto,
        error: Error?
    ) {
        isCapturing = false
        shutterButton.isEnabled = true
        shutterButton.alpha = 1

        if error != nil {
            reportFailure("This camera photo could not be loaded.")
            return
        }

        guard let data = photo.fileDataRepresentation() else {
            reportFailure("This camera photo could not be prepared.")
            return
        }

        Task { @MainActor in
            onCapture(data)
        }
    }

    private func reportFailure(_ message: String) {
        Task { @MainActor in
            onFailure(message)
        }
    }
}

public struct EmbeddedCameraPreviewView: UIViewControllerRepresentable {
    private let captureRequestID: Int
    private let zoomFactor: Double
    private let onCapture: @MainActor (Data) -> Void
    private let onFailure: @MainActor (String) -> Void

    public init(
        captureRequestID: Int,
        zoomFactor: Double,
        onCapture: @escaping @MainActor (Data) -> Void,
        onFailure: @escaping @MainActor (String) -> Void
    ) {
        self.captureRequestID = captureRequestID
        self.zoomFactor = zoomFactor
        self.onCapture = onCapture
        self.onFailure = onFailure
    }

    public func makeUIViewController(context: Context) -> EmbeddedCameraPreviewViewController {
        EmbeddedCameraPreviewViewController(
            onCapture: onCapture,
            onFailure: onFailure
        )
    }

    public func updateUIViewController(_ uiViewController: EmbeddedCameraPreviewViewController, context: Context) {
        uiViewController.setZoomFactor(zoomFactor)
        uiViewController.captureIfNeeded(requestID: captureRequestID)
    }

    public static func dismantleUIViewController(
        _ uiViewController: EmbeddedCameraPreviewViewController,
        coordinator: ()
    ) {
        uiViewController.stopSession()
    }
}

public final class EmbeddedCameraPreviewViewController: UIViewController, @preconcurrency AVCapturePhotoCaptureDelegate {
    private let onCapture: @MainActor (Data) -> Void
    private let onFailure: @MainActor (String) -> Void
    private let session = AVCaptureSession()
    private let photoOutput = AVCapturePhotoOutput()
    private var previewLayer: AVCaptureVideoPreviewLayer?
    private var captureDevice: AVCaptureDevice?
    private var pendingZoomFactor = 1.0
    private var isCapturing = false
    private var isConfigured = false
    private var isActive = false
    private var lastCaptureRequestID = 0

    public init(
        onCapture: @escaping @MainActor (Data) -> Void,
        onFailure: @escaping @MainActor (String) -> Void
    ) {
        self.onCapture = onCapture
        self.onFailure = onFailure
        super.init(nibName: nil, bundle: nil)
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    public override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        configurePreview()
        configureSession()
    }

    public override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        isActive = true
        startSession()
    }

    public override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        previewLayer?.frame = view.bounds
    }

    public override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        isActive = false
        stopSession()
    }

    public func captureIfNeeded(requestID: Int) {
        guard requestID != lastCaptureRequestID else {
            return
        }
        lastCaptureRequestID = requestID
        capturePhoto()
    }

    public func setZoomFactor(_ factor: Double) {
        pendingZoomFactor = factor
        applyZoomFactor(factor)
    }

    public func stopSession() {
        isActive = false
        if session.isRunning {
            session.stopRunning()
        }
    }

    private func startSession() {
        guard isConfigured, session.isRunning == false else {
            return
        }
        session.startRunning()
    }

    private func configurePreview() {
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.videoGravity = .resizeAspectFill
        previewLayer.frame = view.bounds
        view.layer.addSublayer(previewLayer)
        self.previewLayer = previewLayer
    }

    private func configureSession() {
        session.beginConfiguration()
        session.sessionPreset = .photo

        guard
            let camera = CameraCaptureDevice.preferredBackCamera(),
            let input = try? AVCaptureDeviceInput(device: camera),
            session.canAddInput(input)
        else {
            session.commitConfiguration()
            reportFailure("Camera input is not available.")
            return
        }
        captureDevice = camera
        session.addInput(input)

        guard session.canAddOutput(photoOutput) else {
            session.commitConfiguration()
            reportFailure("Camera output is not available.")
            return
        }
        session.addOutput(photoOutput)
        session.commitConfiguration()
        isConfigured = true
        applyZoomFactor(pendingZoomFactor)
    }

    private func applyZoomFactor(_ factor: Double) {
        guard let captureDevice else {
            return
        }

        let clampedFactor = min(
            max(factor, captureDevice.minAvailableVideoZoomFactor),
            captureDevice.maxAvailableVideoZoomFactor
        )

        do {
            try captureDevice.lockForConfiguration()
            captureDevice.videoZoomFactor = clampedFactor
            captureDevice.unlockForConfiguration()
        } catch {
            reportFailure("Camera zoom is not available.")
        }
    }

    private func capturePhoto() {
        guard isConfigured else {
            reportFailure("Camera output is not available.")
            return
        }
        guard isCapturing == false else {
            return
        }
        isCapturing = true

        let settings: AVCapturePhotoSettings
        if photoOutput.availablePhotoCodecTypes.contains(.jpeg) {
            settings = AVCapturePhotoSettings(format: [AVVideoCodecKey: AVVideoCodecType.jpeg])
        } else {
            settings = AVCapturePhotoSettings()
        }
        photoOutput.capturePhoto(with: settings, delegate: self)
    }

    public func photoOutput(
        _ output: AVCapturePhotoOutput,
        didFinishProcessingPhoto photo: AVCapturePhoto,
        error: Error?
    ) {
        isCapturing = false

        guard isActive else {
            return
        }

        if error != nil {
            reportFailure("This camera photo could not be loaded.")
            return
        }

        guard let data = photo.fileDataRepresentation() else {
            reportFailure("This camera photo could not be prepared.")
            return
        }

        Task { @MainActor in
            onCapture(data)
        }
    }

    private func reportFailure(_ message: String) {
        Task { @MainActor in
            onFailure(message)
        }
    }
}

private enum CameraCaptureDevice {
    static func preferredBackCamera() -> AVCaptureDevice? {
        let deviceTypes: [AVCaptureDevice.DeviceType] = [
            .builtInTripleCamera,
            .builtInDualWideCamera,
            .builtInDualCamera,
            .builtInWideAngleCamera
        ]
        let discovery = AVCaptureDevice.DiscoverySession(
            deviceTypes: deviceTypes,
            mediaType: .video,
            position: .back
        )
        return discovery.devices.first
            ?? AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back)
            ?? AVCaptureDevice.default(for: .video)
    }
}
#endif
