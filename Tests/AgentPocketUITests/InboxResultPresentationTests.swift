import XCTest
@testable import AgentPocketCore
@testable import AgentPocketUI

final class InboxResultPresentationTests: XCTestCase {
    func testLocalAgentLensSourcesUseUserFacingNames() throws {
        let status = try completedIntakeStatus()
        let englishCases: [(AgentLensSourceSurface, UniversalIntakeKind, String)] = [
            (.agentScanner, .text, "Source: Scanner"),
            (.documentScanner, .pdf, "Source: Document Scan"),
            (.videoCapture, .video, "Source: Video")
        ]
        let chineseCases: [(AgentLensSourceSurface, UniversalIntakeKind, String)] = [
            (.agentScanner, .text, "来源：扫描"),
            (.documentScanner, .pdf, "来源：文档扫描"),
            (.videoCapture, .video, "来源：视频")
        ]

        for (surface, kind, expectedSourceText) in englishCases {
            let presentation = InboxResultPresentation(
                status: status,
                context: context(sourceSurface: surface.rawValue, kind: kind),
                language: .english
            )

            XCTAssertEqual(presentation.sourceText, expectedSourceText)
        }

        for (surface, kind, expectedSourceText) in chineseCases {
            let presentation = InboxResultPresentation(
                status: status,
                context: context(sourceSurface: surface.rawValue, kind: kind),
                language: .chinese
            )

            XCTAssertEqual(presentation.sourceText, expectedSourceText)
        }
    }

    func testContextSelectionCopyStaysLocalized() throws {
        let status = try completedIntakeStatus()

        let selected = InboxResultPresentation(
            status: status,
            context: context(sourceSurface: "paste", kind: .text, contextSelected: true),
            language: .english
        )
        let omitted = InboxResultPresentation(
            status: status,
            context: context(sourceSurface: "paste", kind: .text, contextSelected: false),
            language: .chinese
        )

        XCTAssertEqual(selected.contextText, "Context Snapshot selected; supported runtimes receive it with this task.")
        XCTAssertEqual(omitted.contextText, "本次任务未选择 Context Snapshot。")
    }

    func testSourceAppProvenanceShowsWhenItAddsContext() throws {
        let status = try completedIntakeStatus()

        let pasted = InboxResultPresentation(
            status: status,
            context: context(sourceApp: "Safari", sourceSurface: "paste", kind: .url),
            language: .english
        )
        let fileImport = InboxResultPresentation(
            status: status,
            context: context(sourceApp: "Files", sourceSurface: "file_picker", kind: .pdf),
            language: .english
        )
        let sharedChinese = InboxResultPresentation(
            status: status,
            context: context(sourceApp: "Photos", sourceSurface: "share_extension", kind: .image),
            language: .chinese
        )

        XCTAssertEqual(pasted.sourceText, "Source: Paste from Safari")
        XCTAssertEqual(fileImport.sourceText, "Source: Files")
        XCTAssertEqual(sharedChinese.sourceText, "来源：系统分享来自 Photos")
    }

    private func context(
        sourceApp: String? = nil,
        sourceSurface: String?,
        kind: UniversalIntakeKind,
        contextSelected: Bool = true
    ) -> InboxSubmissionContext {
        InboxSubmissionContext(
            sourceInboxItemID: UUID(uuidString: "A6830000-0000-4000-9000-000000000001")!,
            sourceApp: sourceApp,
            sourceSurface: sourceSurface,
            kind: kind,
            contextSelected: contextSelected
        )
    }

    private func completedIntakeStatus() throws -> TaskStatusResponse {
        let data = """
        {
          "task_id": "task_intake_123",
          "status": "completed",
          "progress": 1.0,
          "message": "Done.",
          "intake": {
            "kind": "text",
            "title": "Saved",
            "summary": "Runtime accepted the item.",
            "suggestions": []
          }
        }
        """.data(using: .utf8)!

        return try JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }
}
