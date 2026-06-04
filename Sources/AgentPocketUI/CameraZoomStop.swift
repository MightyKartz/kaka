import Foundation

public enum CameraZoomStop: Double, CaseIterable, Identifiable, Sendable {
    case ultraWide = 0.5
    case wide = 1.0
    case telephoto2 = 2.0
    case telephoto5 = 5.0

    public var id: Double { rawValue }

    public var title: String {
        switch self {
        case .ultraWide:
            return "0.5"
        case .wide:
            return "1x"
        case .telephoto2:
            return "2"
        case .telephoto5:
            return "5"
        }
    }

    public var zoomFactor: Double { rawValue }
}

