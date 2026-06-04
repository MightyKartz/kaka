import XCTest
@testable import AgentPocketUI

final class CameraModeSelectionPolicyTests: XCTestCase {
    func testLeftSwipeMovesToNextAdjacentModeWithoutSkipping() {
        let next = CameraModeSelectionPolicy.resolvedMode(
            current: .masterShot,
            translation: -160,
            predictedEndTranslation: -420
        )

        XCTAssertEqual(next, .scan)
    }

    func testSequentialLeftSwipesCanReachEveryMode() {
        var mode = SmartCameraMode.masterShot

        mode = CameraModeSelectionPolicy.resolvedMode(current: mode, translation: -80, predictedEndTranslation: -120)
        XCTAssertEqual(mode, .scan)

        mode = CameraModeSelectionPolicy.resolvedMode(current: mode, translation: -80, predictedEndTranslation: -120)
        XCTAssertEqual(mode, .identify)

        mode = CameraModeSelectionPolicy.resolvedMode(current: mode, translation: -80, predictedEndTranslation: -120)
        XCTAssertEqual(mode, .translate)

        mode = CameraModeSelectionPolicy.resolvedMode(current: mode, translation: -80, predictedEndTranslation: -120)
        XCTAssertEqual(mode, .food)
    }

    func testRightSwipeMovesToPreviousAdjacentMode() {
        let next = CameraModeSelectionPolicy.resolvedMode(
            current: .translate,
            translation: 96,
            predictedEndTranslation: 180
        )

        XCTAssertEqual(next, .identify)
    }

    func testSmallDragKeepsCurrentMode() {
        let next = CameraModeSelectionPolicy.resolvedMode(
            current: .identify,
            translation: -12,
            predictedEndTranslation: -24
        )

        XCTAssertEqual(next, .identify)
    }

    func testDragOffsetIsClampedForRubberBandFeel() {
        XCTAssertEqual(CameraModeSelectionPolicy.clampedDragOffset(300, itemWidth: 120), 114)
        XCTAssertEqual(CameraModeSelectionPolicy.clampedDragOffset(-300, itemWidth: 120), -114)
        XCTAssertEqual(CameraModeSelectionPolicy.clampedDragOffset(48, itemWidth: 120), 48)
    }

    func testInteractiveDragOffsetTracksValidDirectionOneToOne() {
        XCTAssertEqual(
            CameraModeSelectionPolicy.interactiveDragOffset(
                current: .identify,
                translation: -72,
                itemWidth: 120
            ),
            -72
        )
        XCTAssertEqual(
            CameraModeSelectionPolicy.interactiveDragOffset(
                current: .identify,
                translation: 64,
                itemWidth: 120
            ),
            64
        )
    }

    func testInteractiveDragOffsetTracksAcrossMultipleAvailableModes() {
        XCTAssertEqual(
            CameraModeSelectionPolicy.interactiveDragOffset(
                current: .masterShot,
                translation: -240,
                itemWidth: 120
            ),
            -240
        )
        XCTAssertEqual(
            CameraModeSelectionPolicy.interactiveDragOffset(
                current: .food,
                translation: 240,
                itemWidth: 120
            ),
            240
        )
    }

    func testInteractiveDragOffsetOnlyRubberBandsPastEdges() {
        XCTAssertEqual(
            CameraModeSelectionPolicy.interactiveDragOffset(
                current: .masterShot,
                translation: 100,
                itemWidth: 120
            ),
            32,
            accuracy: 0.001
        )
        XCTAssertEqual(
            CameraModeSelectionPolicy.interactiveDragOffset(
                current: .food,
                translation: -100,
                itemWidth: 120
            ),
            -32,
            accuracy: 0.001
        )
    }

    func testVisibleTripletUsesEmptySlotAtStart() {
        XCTAssertEqual(
            CameraModeSelectionPolicy.visibleTriplet(current: SmartCameraMode.masterShot),
            [nil, .masterShot, .scan] as [SmartCameraMode?]
        )
    }

    func testVisibleTripletShowsPreviousCurrentAndNextForMiddleMode() {
        XCTAssertEqual(
            CameraModeSelectionPolicy.visibleTriplet(current: SmartCameraMode.identify),
            [.scan, .identify, .translate] as [SmartCameraMode?]
        )
    }

    func testVisibleTripletUsesEmptySlotAtEnd() {
        XCTAssertEqual(
            CameraModeSelectionPolicy.visibleTriplet(current: SmartCameraMode.food),
            [.translate, .food, nil] as [SmartCameraMode?]
        )
    }
}
