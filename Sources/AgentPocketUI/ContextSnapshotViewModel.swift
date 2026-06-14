import AgentPocketCore
import Foundation

public struct ContextSnapshotPreviewRow: Equatable, Identifiable, Sendable {
    public var id: String { label }
    public let label: String
    public let value: String

    public init(label: String, value: String) {
        self.label = label
        self.value = value
    }
}

@MainActor
public final class ContextSnapshotViewModel: ObservableObject {
    @Published public var includeContext: Bool
    @Published public private(set) var snapshotPreview: ContextSnapshotPayload?
    @Published public private(set) var permissionMessage: String?
    @Published public private(set) var isContextSnapshotPreparing = false

    private let collector: any ContextSnapshotCollecting
    private var collectionGeneration = 0

    public init(
        includeContext: Bool = false,
        collector: any ContextSnapshotCollecting = PermissionedContextSnapshotCollector(sourceSurface: "share_extension")
    ) {
        self.includeContext = includeContext
        self.collector = collector
    }

    public var selectedSnapshotForSubmission: ContextSnapshotPayload? {
        includeContext ? snapshotPreview : nil
    }

    public var previewRows: [ContextSnapshotPreviewRow] {
        guard let snapshot = snapshotPreview else { return [] }
        return [
            Self.row("Time", snapshot.timestamp),
            Self.row("Timezone", snapshot.timezone),
            Self.row("Locale", snapshot.locale),
            Self.row("Source", snapshot.sourceSurface, formatter: Self.sourceDisplayValue),
            Self.row("Network", snapshot.network, formatter: Self.networkDisplayValue),
            Self.row("Battery", snapshot.battery, formatter: Self.batteryDisplayValue),
            Self.row("Motion", snapshot.motion, formatter: Self.motionDisplayValue),
            Self.row("Location", snapshot.locationLabel, formatter: Self.locationDisplayValue),
            Self.row("Precision", snapshot.locationPrecision, formatter: Self.precisionDisplayValue),
            Self.row("Calendar", snapshot.calendarAvailability, formatter: Self.calendarDisplayValue)
        ].compactMap { $0 }
    }

    public func resetPerTaskConsent() {
        collectionGeneration += 1
        includeContext = false
        snapshotPreview = nil
        permissionMessage = nil
        isContextSnapshotPreparing = false
    }

    public func refresh() async {
        await collect()
    }

    public func refreshForInclusionIfNeeded() async {
        guard includeContext, snapshotPreview == nil else { return }
        await collect()
    }

    public func collect() async {
        collectionGeneration += 1
        let generation = collectionGeneration
        isContextSnapshotPreparing = true
        do {
            let snapshot = try await collector.collectContextSnapshot()
            guard generation == collectionGeneration else { return }
            snapshotPreview = snapshot
            permissionMessage = nil
            isContextSnapshotPreparing = false
        } catch let error as ContextSnapshotCollectionError {
            guard generation == collectionGeneration else { return }
            snapshotPreview = nil
            permissionMessage = error.message
            isContextSnapshotPreparing = false
        } catch {
            guard generation == collectionGeneration else { return }
            snapshotPreview = nil
            permissionMessage = "Context is unavailable."
            isContextSnapshotPreparing = false
        }
    }
}

private extension ContextSnapshotViewModel {
    static func row(
        _ label: String,
        _ value: String?,
        formatter: ((String) -> String)? = nil
    ) -> ContextSnapshotPreviewRow? {
        guard let value, !value.isEmpty else { return nil }
        return ContextSnapshotPreviewRow(label: label, value: formatter?(value) ?? value)
    }

    static func sourceDisplayValue(_ value: String) -> String {
        switch value {
        case "share_extension":
            return "Share Extension"
        case "voice":
            return "Voice"
        case "inbox":
            return "Inbox"
        case AgentLensSourceSurface.agentScanner.rawValue:
            return "Scanner"
        case AgentLensSourceSurface.documentScanner.rawValue:
            return "Document Scan"
        case AgentLensSourceSurface.videoCapture.rawValue:
            return "Video"
        default:
            return prettified(value)
        }
    }

    static func networkDisplayValue(_ value: String) -> String {
        switch value {
        case "wifi":
            return "Wi-Fi"
        case "cellular":
            return "Cellular"
        case "offline":
            return "Offline"
        case "constrained":
            return "Limited network"
        case "unknown":
            return "Unknown"
        case "unavailable":
            return "Unavailable"
        default:
            return prettified(value)
        }
    }

    static func batteryDisplayValue(_ value: String) -> String {
        let chargingPrefix = "charging_"
        let percentSuffix = "_percent"
        if value.hasPrefix(chargingPrefix), value.hasSuffix(percentSuffix) {
            let start = value.index(value.startIndex, offsetBy: chargingPrefix.count)
            let end = value.index(value.endIndex, offsetBy: -percentSuffix.count)
            let percent = value[start..<end]
            if percent.allSatisfy(\.isNumber) {
                return "Charging, \(percent)%"
            }
        }

        switch value {
        case "critical":
            return "Critical"
        case "low":
            return "Low"
        case "normal":
            return "Normal"
        case "full":
            return "Full"
        case "charging":
            return "Charging"
        case "unknown":
            return "Unknown"
        case "unavailable":
            return "Unavailable"
        default:
            return prettified(value)
        }
    }

    static func permissionDisplayValue(_ value: String) -> String {
        switch value {
        case "available":
            return "Available"
        case "permission_denied":
            return "Permission denied"
        case "not_requested":
            return "Not requested for this task"
        case "unavailable":
            return "Unavailable"
        default:
            return prettified(value)
        }
    }

    static func motionDisplayValue(_ value: String) -> String {
        switch value {
        case "stationary":
            return "Stationary"
        case "walking":
            return "Walking"
        case "running":
            return "Running"
        case "driving":
            return "Driving"
        default:
            return permissionDisplayValue(value)
        }
    }

    static func locationDisplayValue(_ value: String) -> String {
        switch value {
        case "available":
            return "Allowed for this task"
        case "permission_denied":
            return "Permission denied"
        case "not_requested":
            return "Not requested for this task"
        case "unavailable":
            return "Unavailable"
        default:
            return prettified(value)
        }
    }

    static func precisionDisplayValue(_ value: String) -> String {
        switch value {
        case "precise":
            return "Precise"
        case "coarse":
            return "Approximate"
        case "none":
            return "Not included"
        case "unknown":
            return "Unknown"
        case "unavailable":
            return "Unavailable"
        default:
            return prettified(value)
        }
    }

    static func calendarDisplayValue(_ value: String) -> String {
        switch value {
        case "free":
            return "Free for the next 30 minutes"
        case "busy":
            return "Busy now"
        case "busy_soon":
            return "Busy in the next 30 minutes"
        case "available":
            return "Available"
        case "write_only":
            return "Write-only access"
        case "permission_denied":
            return "Permission denied"
        case "not_requested":
            return "Not requested for this task"
        case "unavailable":
            return "Unavailable"
        default:
            return prettified(value)
        }
    }

    static func prettified(_ value: String) -> String {
        value
            .split(separator: "_")
            .map { word in
                guard let first = word.first else { return "" }
                return String(first).uppercased() + String(word.dropFirst())
            }
            .joined(separator: " ")
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
