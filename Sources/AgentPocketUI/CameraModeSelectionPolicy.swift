import CoreGraphics
import Foundation

public enum CameraModeSelectionPolicy {
    private static let threshold: CGFloat = 34

    public static func resolvedMode(
        current: SmartCameraMode,
        translation: CGFloat,
        predictedEndTranslation: CGFloat
    ) -> SmartCameraMode {
        let effectiveTranslation = abs(predictedEndTranslation) > abs(translation)
            ? predictedEndTranslation
            : translation
        guard abs(effectiveTranslation) >= threshold else {
            return current
        }

        let direction = effectiveTranslation < 0 ? 1 : -1
        let modes = SmartCameraMode.allCases.filter(\.isSelectable)
        guard let currentIndex = modes.firstIndex(of: current) else {
            return current
        }

        let nextIndex = min(max(currentIndex + direction, modes.startIndex), modes.index(before: modes.endIndex))
        return modes[nextIndex]
    }

    public static func clampedDragOffset(
        _ translation: CGFloat,
        itemWidth: CGFloat
    ) -> CGFloat {
        let limit = max(1, itemWidth * 0.95)
        return min(max(translation, -limit), limit)
    }

    public static func interactiveDragOffset(
        current: SmartCameraMode,
        translation: CGFloat,
        itemWidth: CGFloat
    ) -> CGFloat {
        let modes = SmartCameraMode.allCases.filter(\.isSelectable)
        guard let currentIndex = modes.firstIndex(of: current) else {
            return translation
        }

        let firstIndex = modes.startIndex
        let lastIndex = modes.index(before: modes.endIndex)
        let leadingLimit = CGFloat(currentIndex - firstIndex) * itemWidth
        let trailingLimit = -CGFloat(lastIndex - currentIndex) * itemWidth

        if translation > leadingLimit {
            return leadingLimit + rubberBand(translation - leadingLimit, itemWidth: itemWidth)
        }
        if translation < trailingLimit {
            return trailingLimit + rubberBand(translation - trailingLimit, itemWidth: itemWidth)
        }
        return translation
    }

    public static func visibleTriplet(current: SmartCameraMode) -> [SmartCameraMode?] {
        let modes = SmartCameraMode.allCases.filter(\.isSelectable)
        guard let currentIndex = modes.firstIndex(of: current) else {
            return [nil, current, nil]
        }

        let previous: SmartCameraMode? = currentIndex > modes.startIndex
            ? modes[modes.index(before: currentIndex)]
            : nil
        let nextIndex = modes.index(after: currentIndex)
        let next: SmartCameraMode? = nextIndex < modes.endIndex ? modes[nextIndex] : nil
        return [previous, current, next]
    }

    private static func rubberBand(_ overscroll: CGFloat, itemWidth: CGFloat) -> CGFloat {
        let limit = max(1, itemWidth * 0.42)
        let damped = min(abs(overscroll) * 0.32, limit)
        return overscroll < 0 ? -damped : damped
    }
}
