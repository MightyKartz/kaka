#if os(iOS)
import SwiftUI
import UIKit

public struct CameraCaptureView: UIViewControllerRepresentable {
    private let onCapture: @MainActor (Data) -> Void
    private let onCancel: @MainActor () -> Void
    private let onFailure: @MainActor (String) -> Void

    public static var isCameraAvailable: Bool {
        UIImagePickerController.isSourceTypeAvailable(.camera)
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

    public func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.delegate = context.coordinator
        picker.sourceType = .camera
        picker.cameraCaptureMode = .photo
        picker.allowsEditing = false
        return picker
    }

    public func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    public func makeCoordinator() -> Coordinator {
        Coordinator(parent: self)
    }

    public final class Coordinator: NSObject, UINavigationControllerDelegate, UIImagePickerControllerDelegate {
        private let parent: CameraCaptureView

        init(parent: CameraCaptureView) {
            self.parent = parent
        }

        public func imagePickerController(
            _ picker: UIImagePickerController,
            didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]
        ) {
            guard let image = info[.originalImage] as? UIImage else {
                reportFailure("This camera photo could not be loaded.")
                return
            }
            guard let data = image.jpegData(compressionQuality: 0.92) else {
                reportFailure("This camera photo could not be prepared.")
                return
            }

            Task { @MainActor in
                parent.onCapture(data)
            }
        }

        public func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            Task { @MainActor in
                parent.onCancel()
            }
        }

        private func reportFailure(_ message: String) {
            Task { @MainActor in
                parent.onFailure(message)
            }
        }
    }
}
#endif
