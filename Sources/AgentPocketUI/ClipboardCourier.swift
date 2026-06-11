import Foundation

#if os(iOS) && canImport(UIKit)
import UIKit
#endif

public struct ClipboardCourierContent: Equatable, Sendable {
    public let string: String?

    public init(string: String? = nil) {
        self.string = string
    }
}

public protocol ClipboardCourierReading: Sendable {
    @MainActor func readContent() -> ClipboardCourierContent
}

public struct SystemClipboardCourierReader: ClipboardCourierReading {
    public init() {}

    @MainActor public func readContent() -> ClipboardCourierContent {
        #if os(iOS) && canImport(UIKit)
        return ClipboardCourierContent(string: UIPasteboard.general.string)
        #else
        return ClipboardCourierContent()
        #endif
    }
}
