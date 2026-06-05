import Foundation

public struct ContextSnapshotPayload: Codable, Equatable, Sendable {
    public let timestamp: String
    public let timezone: String
    public let locale: String?
    public let sourceSurface: String?
    public let network: String?
    public let battery: String?
    public let motion: String?
    public let locationLabel: String?

    public init(
        timestamp: String,
        timezone: String,
        locale: String? = nil,
        sourceSurface: String? = nil,
        network: String? = nil,
        battery: String? = nil,
        motion: String? = nil,
        locationLabel: String? = nil
    ) {
        self.timestamp = timestamp
        self.timezone = timezone
        self.locale = locale
        self.sourceSurface = sourceSurface
        self.network = network
        self.battery = battery
        self.motion = motion
        self.locationLabel = locationLabel
    }

    private enum CodingKeys: String, CodingKey {
        case timestamp
        case timezone
        case locale
        case sourceSurface = "source_surface"
        case network
        case battery
        case motion
        case locationLabel = "location_label"
    }
}

public protocol ContextSnapshotCollecting: Sendable {
    func collectContextSnapshot() async throws -> ContextSnapshotPayload
}

public enum ContextSnapshotCollectionError: Error, Equatable, Sendable {
    case permissionDenied(String)
    case unavailable(String)
}

public struct MinimalContextSnapshotCollector: ContextSnapshotCollecting {
    private let sourceSurface: String
    private let localeProvider: @Sendable () -> String?
    private let dateProvider: @Sendable () -> Date
    private let timeZoneProvider: @Sendable () -> TimeZone

    public init(
        sourceSurface: String,
        localeProvider: @escaping @Sendable () -> String? = { Locale.current.identifier },
        dateProvider: @escaping @Sendable () -> Date = Date.init,
        timeZoneProvider: @escaping @Sendable () -> TimeZone = { .current }
    ) {
        self.sourceSurface = sourceSurface
        self.localeProvider = localeProvider
        self.dateProvider = dateProvider
        self.timeZoneProvider = timeZoneProvider
    }

    public func collectContextSnapshot() async throws -> ContextSnapshotPayload {
        ContextSnapshotPayload(
            timestamp: MobileBridgeDateCoding.encode(dateProvider()),
            timezone: timeZoneProvider().identifier,
            locale: localeProvider(),
            sourceSurface: sourceSurface
        )
    }
}
