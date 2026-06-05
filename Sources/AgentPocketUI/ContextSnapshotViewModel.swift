import AgentPocketCore
import Foundation

@MainActor
public final class ContextSnapshotViewModel: ObservableObject {
    @Published public var includeContext: Bool
    @Published public private(set) var snapshotPreview: ContextSnapshotPayload?
    @Published public private(set) var permissionMessage: String?

    private let collector: any ContextSnapshotCollecting

    public init(
        includeContext: Bool = false,
        collector: any ContextSnapshotCollecting = MinimalContextSnapshotCollector(sourceSurface: "share_extension")
    ) {
        self.includeContext = includeContext
        self.collector = collector
    }

    public var selectedSnapshotForSubmission: ContextSnapshotPayload? {
        includeContext ? snapshotPreview : nil
    }

    public func resetPerTaskConsent() {
        includeContext = false
    }

    public func refresh() async {
        await collect()
    }

    public func collect() async {
        do {
            snapshotPreview = try await collector.collectContextSnapshot()
            permissionMessage = nil
        } catch let error as ContextSnapshotCollectionError {
            snapshotPreview = nil
            permissionMessage = error.message
        } catch {
            snapshotPreview = nil
            permissionMessage = "Context is unavailable."
        }
    }
}

private extension ContextSnapshotCollectionError {
    var message: String {
        switch self {
        case .permissionDenied(let message), .unavailable(let message):
            return message
        }
    }
}
