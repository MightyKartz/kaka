import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
import XCTest
@testable import AgentPocketCore

final class ImagePreprocessorTests: XCTestCase {
    func testPreprocessorEncodesPNGToJPEGAndStripsSensitiveMetadataByDefault() throws {
        let source = try makeImageData(
            typeIdentifier: UTType.png.identifier,
            width: 2,
            height: 1,
            properties: [
                kCGImagePropertyExifDictionary as String: ["LensModel": "Private Lens"],
                kCGImagePropertyGPSDictionary as String: ["Latitude": 37.0, "Longitude": -122.0],
            ]
        )

        let upload = try ImagePreprocessor().prepareForUpload(
            data: source,
            sourceMimeType: "image/png",
            originalFileName: "original.png",
            maxUploadMB: 30
        )

        XCTAssertEqual(upload.mimeType, "image/jpeg")
        XCTAssertEqual(upload.fileName, "original.jpg")
        XCTAssertEqual(upload.metadata.width, 2)
        XCTAssertEqual(upload.metadata.height, 1)
        XCTAssertTrue(upload.metadata.stripSensitiveEXIF)
        XCTAssertTrue(upload.data.starts(with: [0xFF, 0xD8]))

        let outputProperties = try imageProperties(from: upload.data)
        let outputExif = outputProperties[kCGImagePropertyExifDictionary as String] as? [String: Any]
        XCTAssertNil(outputExif?["LensModel"])
        XCTAssertNil(outputProperties[kCGImagePropertyGPSDictionary as String])
    }

    func testPreprocessorCanPreserveOriginalPNGWhenRequested() throws {
        let source = try makeImageData(typeIdentifier: UTType.png.identifier, width: 3, height: 2)

        let upload = try ImagePreprocessor().prepareForUpload(
            data: source,
            sourceMimeType: "image/png",
            originalFileName: "diagram.png",
            maxUploadMB: 30,
            outputFormat: .preserveOriginal
        )

        XCTAssertEqual(upload.mimeType, "image/png")
        XCTAssertEqual(upload.fileName, "diagram.png")
        XCTAssertEqual(upload.metadata.width, 3)
        XCTAssertEqual(upload.metadata.height, 2)
        XCTAssertEqual(upload.data, source)
    }

    func testPreprocessorEncodesHEICSelectionToJPEGForIPhoneLibraryPhotos() throws {
        let source = try makeImageData(typeIdentifier: UTType.heic.identifier, width: 4, height: 3)

        let upload = try ImagePreprocessor().prepareForUpload(
            data: source,
            sourceMimeType: "image/heic",
            originalFileName: "iphone-library.heic",
            maxUploadMB: 30
        )

        XCTAssertEqual(upload.mimeType, "image/jpeg")
        XCTAssertEqual(upload.fileName, "iphone-library.jpg")
        XCTAssertEqual(upload.metadata.width, 4)
        XCTAssertEqual(upload.metadata.height, 3)
        XCTAssertTrue(upload.metadata.stripSensitiveEXIF)
        XCTAssertTrue(upload.data.starts(with: [0xFF, 0xD8]))
    }

    func testPreprocessorRejectsUndecodableImageData() {
        XCTAssertThrowsError(
            try ImagePreprocessor().prepareForUpload(
                data: Data("not image".utf8),
                sourceMimeType: "image/jpeg",
                originalFileName: "bad.jpg",
                maxUploadMB: 30
            )
        ) { error in
            XCTAssertEqual(error as? ImagePreprocessor.PreprocessError, .cannotDecodeImage)
        }
    }

    private func makeImageData(
        typeIdentifier: String,
        width: Int,
        height: Int,
        properties: [String: Any] = [:]
    ) throws -> Data {
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        guard let context = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: width * 4,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else {
            throw XCTSkip("Could not create test image context.")
        }
        context.setFillColor(CGColor(red: 0.2, green: 0.4, blue: 0.8, alpha: 1.0))
        context.fill(CGRect(x: 0, y: 0, width: width, height: height))
        guard let image = context.makeImage() else {
            throw XCTSkip("Could not create test image.")
        }

        let data = NSMutableData()
        guard let destination = CGImageDestinationCreateWithData(data, typeIdentifier as CFString, 1, nil) else {
            throw XCTSkip("Could not create image destination.")
        }
        CGImageDestinationAddImage(destination, image, properties as CFDictionary)
        guard CGImageDestinationFinalize(destination) else {
            throw XCTSkip("Could not finalize image.")
        }
        return data as Data
    }

    private func imageProperties(from data: Data) throws -> [String: Any] {
        guard let source = CGImageSourceCreateWithData(data as CFData, nil),
              let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [String: Any] else {
            throw XCTSkip("Could not read output image properties.")
        }
        return properties
    }
}
