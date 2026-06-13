import Foundation

#if os(iOS) && canImport(UIKit)
import UIKit
#elseif os(macOS) && canImport(AppKit)
import AppKit
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

public protocol ClipboardCourierWriting: Sendable {
    @MainActor func writeString(_ value: String)
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

public struct SystemClipboardCourierWriter: ClipboardCourierWriting {
    public init() {}

    @MainActor public func writeString(_ value: String) {
        #if os(iOS) && canImport(UIKit)
        UIPasteboard.general.string = value
        #elseif os(macOS) && canImport(AppKit)
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(value, forType: .string)
        #endif
    }
}
