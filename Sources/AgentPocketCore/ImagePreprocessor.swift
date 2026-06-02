import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

public struct ImagePreprocessor: Sendable {
    public enum OutputFormat: Equatable, Sendable {
        case jpeg(quality: CGFloat)
        case preserveOriginal
    }

    public enum PreprocessError: Error, Equatable {
        case cannotDecodeImage
        case cannotEncodeJPEG
    }

    public init() {}

    public func prepareForUpload(
        data: Data,
        sourceMimeType: String,
        originalFileName: String,
        maxUploadMB: Int,
        localCreationTime: String? = nil,
        outputFormat: OutputFormat = .jpeg(quality: 0.9),
        maxPixelDimension: Int = 4_096
    ) throws -> PreparedImageUpload {
        let image = try decodeImage(from: data, maxPixelDimension: maxPixelDimension)

        switch outputFormat {
        case .preserveOriginal:
            return try ImageUploadPolicy(maxUploadMB: maxUploadMB).prepare(
                data: data,
                mimeType: sourceMimeType,
                fileName: originalFileName,
                width: image.width,
                height: image.height,
                localCreationTime: localCreationTime
            )
        case .jpeg(let quality):
            let encoded = try encodeJPEG(image: image, quality: quality)
            return try ImageUploadPolicy(maxUploadMB: maxUploadMB).prepare(
                data: encoded,
                mimeType: "image/jpeg",
                fileName: jpegFileName(from: originalFileName),
                width: image.width,
                height: image.height,
                localCreationTime: localCreationTime
            )
        }
    }

    private func decodeImage(from data: Data, maxPixelDimension: Int) throws -> CGImage {
        guard let source = CGImageSourceCreateWithData(data as CFData, nil) else {
            throw PreprocessError.cannotDecodeImage
        }

        let options: [CFString: Any] = [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceShouldCacheImmediately: true,
            kCGImageSourceThumbnailMaxPixelSize: maxPixelDimension,
        ]

        guard let image = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary) else {
            throw PreprocessError.cannotDecodeImage
        }
        return image
    }

    private func encodeJPEG(image: CGImage, quality: CGFloat) throws -> Data {
        let output = NSMutableData()
        guard let destination = CGImageDestinationCreateWithData(
            output,
            UTType.jpeg.identifier as CFString,
            1,
            nil
        ) else {
            throw PreprocessError.cannotEncodeJPEG
        }

        let properties: [CFString: Any] = [
            kCGImageDestinationLossyCompressionQuality: min(max(quality, 0), 1),
        ]
        CGImageDestinationAddImage(destination, image, properties as CFDictionary)
        guard CGImageDestinationFinalize(destination) else {
            throw PreprocessError.cannotEncodeJPEG
        }
        return output as Data
    }

    private func jpegFileName(from originalFileName: String) -> String {
        let path = originalFileName as NSString
        let base = path.deletingPathExtension
        if base.isEmpty {
            return "photo.jpg"
        }
        return "\(base).jpg"
    }
}
