import Foundation
#if canImport(CoreLocation)
import CoreLocation
#endif
#if canImport(CoreMotion)
import CoreMotion
#endif
#if canImport(EventKit)
import EventKit
#endif
#if canImport(Network)
import Network
#endif
#if os(iOS) && canImport(UIKit)
import UIKit
#endif

public struct ContextSnapshotPayload: Codable, Equatable, Sendable {
    public let timestamp: String
    public let timezone: String
    public let locale: String?
    public let sourceSurface: String?
    public let network: String?
    public let battery: String?
    public let motion: String?
    public let locationLabel: String?
    public let locationPrecision: String?
    public let calendarAvailability: String?

    public init(
        timestamp: String,
        timezone: String,
        locale: String? = nil,
        sourceSurface: String? = nil,
        network: String? = nil,
        battery: String? = nil,
        motion: String? = nil,
        locationLabel: String? = nil,
        locationPrecision: String? = nil,
        calendarAvailability: String? = nil
    ) {
        self.timestamp = timestamp
        self.timezone = timezone
        self.locale = locale
        self.sourceSurface = sourceSurface
        self.network = network
        self.battery = battery
        self.motion = motion
        self.locationLabel = locationLabel
        self.locationPrecision = locationPrecision
        self.calendarAvailability = calendarAvailability
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
        case locationPrecision = "location_precision"
        case calendarAvailability = "calendar_availability"
    }
}

public protocol ContextSnapshotCollecting: Sendable {
    func collectContextSnapshot() async throws -> ContextSnapshotPayload
}

public enum ContextSnapshotCollectionError: Error, Equatable, Sendable {
    case permissionDenied(String)
    case unavailable(String)
}

public struct ContextSnapshotFieldValues: Equatable, Sendable {
    public let network: String?
    public let battery: String?
    public let motion: String?
    public let locationLabel: String?
    public let locationPrecision: String?
    public let calendarAvailability: String?

    public init(
        network: String? = nil,
        battery: String? = nil,
        motion: String? = nil,
        locationLabel: String? = nil,
        locationPrecision: String? = nil,
        calendarAvailability: String? = nil
    ) {
        self.network = network
        self.battery = battery
        self.motion = motion
        self.locationLabel = locationLabel
        self.locationPrecision = locationPrecision
        self.calendarAvailability = calendarAvailability
    }
}

public protocol ContextSnapshotFieldCollecting: Sendable {
    func collectContextSnapshotFields() async -> ContextSnapshotFieldValues
}

public enum ContextSnapshotNetworkPathInterface: String, CaseIterable, Hashable, Sendable {
    case wifi
    case cellular
    case wired
    case loopback
    case other
}

public struct ContextSnapshotNetworkPathState: Equatable, Sendable {
    public let isSatisfied: Bool
    public let isConstrained: Bool
    public let interfaces: Set<ContextSnapshotNetworkPathInterface>

    public init(
        isSatisfied: Bool,
        isConstrained: Bool,
        interfaces: Set<ContextSnapshotNetworkPathInterface>
    ) {
        self.isSatisfied = isSatisfied
        self.isConstrained = isConstrained
        self.interfaces = interfaces
    }

    public var snapshotNetworkStatus: String {
        guard isSatisfied else { return "offline" }
        if isConstrained { return "constrained" }
        if interfaces.contains(.wifi) { return "wifi" }
        if interfaces.contains(.cellular) { return "cellular" }
        return "unknown"
    }
}

public protocol ContextSnapshotNetworkPathSampling: Sendable {
    func currentNetworkPathStatus() async -> String
}

public struct StaticContextSnapshotNetworkPathSampler: ContextSnapshotNetworkPathSampling {
    private let status: String

    public init(status: String) {
        self.status = status
    }

    public func currentNetworkPathStatus() async -> String {
        status
    }
}

public struct ContextSnapshotMotionActivityState: Equatable, Sendable {
    public let isStationary: Bool
    public let isWalking: Bool
    public let isRunning: Bool
    public let isAutomotive: Bool

    public init(
        isStationary: Bool = false,
        isWalking: Bool = false,
        isRunning: Bool = false,
        isAutomotive: Bool = false
    ) {
        self.isStationary = isStationary
        self.isWalking = isWalking
        self.isRunning = isRunning
        self.isAutomotive = isAutomotive
    }

    public var snapshotMotionStatus: String {
        if isAutomotive { return "driving" }
        if isRunning { return "running" }
        if isWalking { return "walking" }
        if isStationary { return "stationary" }
        return "unknown"
    }
}

public enum ContextSnapshotMotionActivityAuthorizationStatus: Equatable, Sendable {
    case authorized
    case denied
    case restricted
    case notDetermined
    case unavailable

    public var snapshotMotionStatus: String? {
        switch self {
        case .authorized:
            return nil
        case .notDetermined:
            return "not_requested"
        case .denied, .restricted:
            return "permission_denied"
        case .unavailable:
            return "unavailable"
        }
    }
}

public protocol ContextSnapshotMotionActivitySampling: Sendable {
    func currentMotionStatus() async -> String
}

public struct StaticContextSnapshotMotionActivitySampler: ContextSnapshotMotionActivitySampling {
    private let status: String

    public init(status: String) {
        self.status = status
    }

    public func currentMotionStatus() async -> String {
        status
    }
}

public struct OneShotContextSnapshotMotionActivitySampler: ContextSnapshotMotionActivitySampling {
    private let timeoutSeconds: TimeInterval

    public init(timeoutSeconds: TimeInterval = 0.6) {
        self.timeoutSeconds = timeoutSeconds
    }

    public func currentMotionStatus() async -> String {
        #if os(iOS) && canImport(CoreMotion)
        guard CMMotionActivityManager.isActivityAvailable() else {
            return "unavailable"
        }
        if let permissionStatus = Self.authorizationStatus().snapshotMotionStatus {
            return permissionStatus
        }
        return await withCheckedContinuation { continuation in
            let probe = OneShotMotionActivityProbe(continuation: continuation)
            probe.start(timeoutSeconds: timeoutSeconds)
        }
        #else
        return "unavailable"
        #endif
    }

    private static func authorizationStatus() -> ContextSnapshotMotionActivityAuthorizationStatus {
        #if os(iOS) && canImport(CoreMotion)
        switch CMMotionActivityManager.authorizationStatus() {
        case .authorized:
            return .authorized
        case .denied:
            return .denied
        case .restricted:
            return .restricted
        case .notDetermined:
            return .notDetermined
        @unknown default:
            return .unavailable
        }
        #else
        return .unavailable
        #endif
    }
}

#if os(iOS) && canImport(CoreMotion)
private final class OneShotMotionActivityProbe: @unchecked Sendable {
    private let lock = NSLock()
    private let manager = CMMotionActivityManager()
    private let operationQueue = OperationQueue()
    private let timeoutQueue = DispatchQueue(label: "kaka.context-snapshot.motion-timeout")
    private var didFinish = false
    private let continuation: CheckedContinuation<String, Never>

    init(continuation: CheckedContinuation<String, Never>) {
        self.continuation = continuation
        operationQueue.maxConcurrentOperationCount = 1
    }

    func start(timeoutSeconds: TimeInterval) {
        manager.startActivityUpdates(to: operationQueue) { activity in
            guard let activity else {
                self.finish("unavailable")
                return
            }
            self.finish(ContextSnapshotMotionActivityState(activity: activity).snapshotMotionStatus)
        }
        timeoutQueue.asyncAfter(deadline: .now() + timeoutSeconds) {
            self.finish("unavailable")
        }
    }

    private func finish(_ status: String) {
        lock.lock()
        guard !didFinish else {
            lock.unlock()
            return
        }
        didFinish = true
        lock.unlock()

        manager.stopActivityUpdates()
        operationQueue.cancelAllOperations()
        continuation.resume(returning: status)
    }
}

private extension ContextSnapshotMotionActivityState {
    init(activity: CMMotionActivity) {
        self.init(
            isStationary: activity.stationary,
            isWalking: activity.walking,
            isRunning: activity.running,
            isAutomotive: activity.automotive
        )
    }
}
#endif

public struct ContextSnapshotCalendarBusyInterval: Equatable, Sendable {
    public let start: Date
    public let end: Date

    public init(start: Date, end: Date) {
        self.start = start
        self.end = end
    }
}

public struct ContextSnapshotCalendarAvailabilityWindow: Equatable, Sendable {
    public let now: Date
    public let end: Date
    public let busyIntervals: [ContextSnapshotCalendarBusyInterval]

    public init(
        now: Date,
        end: Date,
        busyIntervals: [ContextSnapshotCalendarBusyInterval]
    ) {
        self.now = now
        self.end = end
        self.busyIntervals = busyIntervals
    }

    public var snapshotCalendarAvailability: String {
        let relevantIntervals = busyIntervals.filter { interval in
            interval.end > now && interval.start < end
        }
        if relevantIntervals.contains(where: { $0.start <= now && $0.end > now }) {
            return "busy"
        }
        if relevantIntervals.contains(where: { $0.start > now }) {
            return "busy_soon"
        }
        return "free"
    }
}

public enum ContextSnapshotCalendarAuthorizationStatus: Equatable, Sendable {
    case readable
    case writeOnly
    case denied
    case restricted
    case notDetermined
    case unavailable

    public var snapshotCalendarAvailability: String? {
        switch self {
        case .readable:
            return nil
        case .writeOnly:
            return "write_only"
        case .notDetermined:
            return "not_requested"
        case .denied, .restricted:
            return "permission_denied"
        case .unavailable:
            return "unavailable"
        }
    }
}

public protocol ContextSnapshotCalendarAvailabilitySampling: Sendable {
    func currentCalendarAvailability() async -> String
}

public struct StaticContextSnapshotCalendarAvailabilitySampler: ContextSnapshotCalendarAvailabilitySampling {
    private let status: String

    public init(status: String) {
        self.status = status
    }

    public func currentCalendarAvailability() async -> String {
        status
    }
}

public struct OneShotContextSnapshotCalendarAvailabilitySampler: ContextSnapshotCalendarAvailabilitySampling {
    private let dateProvider: @Sendable () -> Date
    private let windowSeconds: TimeInterval

    public init(
        dateProvider: @escaping @Sendable () -> Date = Date.init,
        windowSeconds: TimeInterval = 30 * 60
    ) {
        self.dateProvider = dateProvider
        self.windowSeconds = windowSeconds
    }

    public func currentCalendarAvailability() async -> String {
        #if canImport(EventKit)
        if let permissionStatus = Self.authorizationStatus().snapshotCalendarAvailability {
            return permissionStatus
        }
        let now = dateProvider()
        let end = now.addingTimeInterval(windowSeconds)
        let store = EKEventStore()
        let predicate = store.predicateForEvents(withStart: now, end: end, calendars: nil)
        let intervals = store.events(matching: predicate).compactMap { event -> ContextSnapshotCalendarBusyInterval? in
            guard let start = event.startDate, let end = event.endDate else {
                return nil
            }
            return ContextSnapshotCalendarBusyInterval(start: start, end: end)
        }
        return ContextSnapshotCalendarAvailabilityWindow(
            now: now,
            end: end,
            busyIntervals: intervals
        ).snapshotCalendarAvailability
        #else
        return "unavailable"
        #endif
    }

    private static func authorizationStatus() -> ContextSnapshotCalendarAuthorizationStatus {
        #if canImport(EventKit)
        switch EKEventStore.authorizationStatus(for: .event) {
        case .authorized, .fullAccess:
            return .readable
        case .writeOnly:
            return .writeOnly
        case .denied:
            return .denied
        case .restricted:
            return .restricted
        case .notDetermined:
            return .notDetermined
        @unknown default:
            return .unavailable
        }
        #else
        return .unavailable
        #endif
    }
}

public struct OneShotContextSnapshotNetworkPathSampler: ContextSnapshotNetworkPathSampling {
    private let timeoutSeconds: TimeInterval

    public init(timeoutSeconds: TimeInterval = 0.35) {
        self.timeoutSeconds = timeoutSeconds
    }

    public func currentNetworkPathStatus() async -> String {
        #if canImport(Network)
        await withCheckedContinuation { continuation in
            let probe = OneShotNetworkPathProbe(continuation: continuation)
            probe.start(timeoutSeconds: timeoutSeconds)
        }
        #else
        "unavailable"
        #endif
    }
}

#if canImport(Network)
private final class OneShotNetworkPathProbe: @unchecked Sendable {
    private let lock = NSLock()
    private var didFinish = false
    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "kaka.context-snapshot.network-path")
    private let continuation: CheckedContinuation<String, Never>

    init(continuation: CheckedContinuation<String, Never>) {
        self.continuation = continuation
    }

    func start(timeoutSeconds: TimeInterval) {
        monitor.pathUpdateHandler = { path in
            self.finish(ContextSnapshotNetworkPathState(path: path).snapshotNetworkStatus)
        }
        monitor.start(queue: queue)
        queue.asyncAfter(deadline: .now() + timeoutSeconds) {
            self.finish("unavailable")
        }
    }

    private func finish(_ status: String) {
        lock.lock()
        guard !didFinish else {
            lock.unlock()
            return
        }
        didFinish = true
        lock.unlock()

        monitor.cancel()
        monitor.pathUpdateHandler = nil
        continuation.resume(returning: status)
    }
}

private extension ContextSnapshotNetworkPathState {
    init(path: NWPath) {
        var interfaces: Set<ContextSnapshotNetworkPathInterface> = []
        if path.usesInterfaceType(.wifi) { interfaces.insert(.wifi) }
        if path.usesInterfaceType(.cellular) { interfaces.insert(.cellular) }
        if path.usesInterfaceType(.wiredEthernet) { interfaces.insert(.wired) }
        if path.usesInterfaceType(.loopback) { interfaces.insert(.loopback) }
        if path.usesInterfaceType(.other) { interfaces.insert(.other) }
        self.init(
            isSatisfied: path.status == .satisfied,
            isConstrained: path.isConstrained,
            interfaces: interfaces
        )
    }
}
#endif

public struct StaticContextSnapshotFieldCollector: ContextSnapshotFieldCollecting {
    private let values: ContextSnapshotFieldValues

    public init(values: ContextSnapshotFieldValues) {
        self.values = values
    }

    public func collectContextSnapshotFields() async -> ContextSnapshotFieldValues {
        values
    }
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

public struct PermissionedContextSnapshotCollector: ContextSnapshotCollecting {
    private let sourceSurface: String
    private let localeProvider: @Sendable () -> String?
    private let dateProvider: @Sendable () -> Date
    private let timeZoneProvider: @Sendable () -> TimeZone
    private let fieldCollector: any ContextSnapshotFieldCollecting

    public init(
        sourceSurface: String,
        localeProvider: @escaping @Sendable () -> String? = { Locale.current.identifier },
        dateProvider: @escaping @Sendable () -> Date = Date.init,
        timeZoneProvider: @escaping @Sendable () -> TimeZone = { .current },
        fieldCollector: any ContextSnapshotFieldCollecting = SystemContextSnapshotFieldCollector()
    ) {
        self.sourceSurface = sourceSurface
        self.localeProvider = localeProvider
        self.dateProvider = dateProvider
        self.timeZoneProvider = timeZoneProvider
        self.fieldCollector = fieldCollector
    }

    public func collectContextSnapshot() async throws -> ContextSnapshotPayload {
        let fields = await fieldCollector.collectContextSnapshotFields()
        return ContextSnapshotPayload(
            timestamp: MobileBridgeDateCoding.encode(dateProvider()),
            timezone: timeZoneProvider().identifier,
            locale: localeProvider(),
            sourceSurface: sourceSurface,
            network: fields.network,
            battery: fields.battery,
            motion: fields.motion,
            locationLabel: fields.locationLabel,
            locationPrecision: fields.locationPrecision,
            calendarAvailability: fields.calendarAvailability
        )
    }
}

public struct SystemContextSnapshotFieldCollector: ContextSnapshotFieldCollecting {
    private let networkPathSampler: any ContextSnapshotNetworkPathSampling
    private let motionActivitySampler: any ContextSnapshotMotionActivitySampling
    private let calendarAvailabilitySampler: any ContextSnapshotCalendarAvailabilitySampling

    public init(
        networkPathSampler: any ContextSnapshotNetworkPathSampling = OneShotContextSnapshotNetworkPathSampler(),
        motionActivitySampler: any ContextSnapshotMotionActivitySampling = OneShotContextSnapshotMotionActivitySampler(),
        calendarAvailabilitySampler: any ContextSnapshotCalendarAvailabilitySampling = OneShotContextSnapshotCalendarAvailabilitySampler()
    ) {
        self.networkPathSampler = networkPathSampler
        self.motionActivitySampler = motionActivitySampler
        self.calendarAvailabilitySampler = calendarAvailabilitySampler
    }

    public func collectContextSnapshotFields() async -> ContextSnapshotFieldValues {
        ContextSnapshotFieldValues(
            network: await networkPathSampler.currentNetworkPathStatus(),
            battery: await Self.batteryStatus(),
            motion: await motionActivitySampler.currentMotionStatus(),
            locationLabel: await Self.locationLabel(),
            locationPrecision: await Self.locationPrecision(),
            calendarAvailability: await calendarAvailabilitySampler.currentCalendarAvailability()
        )
    }

    private static func batteryStatus() async -> String {
        #if os(iOS) && canImport(UIKit)
        await MainActor.run {
            let device = UIDevice.current
            let previousMonitoringState = device.isBatteryMonitoringEnabled
            device.isBatteryMonitoringEnabled = true
            defer { device.isBatteryMonitoringEnabled = previousMonitoringState }
            let state: String
            switch device.batteryState {
            case .charging:
                if device.batteryLevel >= 0 {
                    let percent = Int((device.batteryLevel * 100).rounded())
                    return "charging_\(percent)_percent"
                }
                state = "charging"
            case .full:
                state = "full"
            case .unplugged:
                if device.batteryLevel >= 0 {
                    if device.batteryLevel <= 0.10 {
                        return "critical"
                    }
                    if device.batteryLevel <= 0.20 {
                        return "low"
                    }
                    return "normal"
                }
                state = "normal"
            case .unknown:
                state = "unknown"
            @unknown default:
                state = "unknown"
            }
            return state
        }
        #else
        return "unavailable"
        #endif
    }

    private static func locationLabel() async -> String {
        #if canImport(CoreLocation)
        await MainActor.run {
            switch CLLocationManager().authorizationStatus {
            case .authorizedAlways, .authorizedWhenInUse:
                return "available"
            case .denied, .restricted:
                return "permission_denied"
            case .notDetermined:
                return "not_requested"
            @unknown default:
                return "unavailable"
            }
        }
        #else
        return "unavailable"
        #endif
    }

    private static func locationPrecision() async -> String {
        #if os(iOS) && canImport(CoreLocation)
        await MainActor.run {
            switch CLLocationManager().authorizationStatus {
            case .authorizedAlways, .authorizedWhenInUse:
                let manager = CLLocationManager()
                switch manager.accuracyAuthorization {
                case .fullAccuracy:
                    return "precise"
                case .reducedAccuracy:
                    return "coarse"
                @unknown default:
                    return "unknown"
                }
            case .denied, .restricted, .notDetermined:
                return "none"
            @unknown default:
                return "unknown"
            }
        }
        #else
        return "unavailable"
        #endif
    }

}
