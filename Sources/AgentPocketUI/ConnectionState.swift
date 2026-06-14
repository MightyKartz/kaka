import Foundation

public struct ConnectedRuntime: Equatable, Sendable {
    public let displayName: String
    public let runtime: String
    public let runtimeVersion: String

    public init(displayName: String, runtime: String, runtimeVersion: String) {
        self.displayName = displayName
        self.runtime = runtime
        self.runtimeVersion = runtimeVersion
    }
}

public enum ConnectionState: Equatable, Sendable {
    case idle
    case scanning
    case discovering
    case testing
    case restoringSavedConnection(displayName: String)
    case connected(ConnectedRuntime)
    case unauthorized
    case offline
    case savedConnectionOffline(displayName: String)
    case invalidCertificate
    case missingPhotoEdit
    case localNetworkPermissionRequired
    case failed(message: String)

    public var presentation: ConnectionPresentation {
        switch self {
        case .idle:
            return ConnectionPresentation(
                title: "Connect Your Local Runtime",
                message: "Scan the pairing QR on your Mac once. Pocket Agent will reconnect automatically after that.",
                primaryActionTitle: "Scan Pairing QR",
                secondaryActionTitle: "Find Nearby Runtime",
                isBusy: false,
                showsManualEntry: false
            )
        case .scanning:
            return ConnectionPresentation(
                title: "Scan Pairing QR",
                message: "Point the camera at the pairing code shown by your local agent.",
                primaryActionTitle: "Scanning...",
                secondaryActionTitle: "Enter Manually",
                isBusy: true,
                showsManualEntry: false
            )
        case .discovering:
            return ConnectionPresentation(
                title: "Finding Local Agent",
                message: "Looking for private runtimes on your local network.",
                primaryActionTitle: "Finding...",
                secondaryActionTitle: nil,
                isBusy: true,
                showsManualEntry: false
            )
        case .testing:
            return ConnectionPresentation(
                title: "Testing Connection",
                message: "Checking health and mobile capabilities.",
                primaryActionTitle: "Testing...",
                secondaryActionTitle: nil,
                isBusy: true,
                showsManualEntry: false
            )
        case .restoringSavedConnection(let displayName):
            return ConnectionPresentation(
                title: "Restoring Saved Runtime",
                message: "Checking \(displayName) with your saved pairing.",
                primaryActionTitle: "Checking...",
                secondaryActionTitle: nil,
                isBusy: true,
                showsManualEntry: false
            )
        case .connected(let runtime):
            return ConnectionPresentation(
                title: "Connected",
                message: "\(runtime.displayName) is ready for phone actions.",
                primaryActionTitle: "Open Lens",
                secondaryActionTitle: "Change Runtime",
                isBusy: false,
                showsManualEntry: false,
                trustBadges: ["Local Network", "Trusted"]
            )
        case .unauthorized:
            return ConnectionPresentation(
                title: "Token Not Accepted",
                message: "Create a new mobile pairing code in your local agent, then try again.",
                primaryActionTitle: "Scan New QR",
                secondaryActionTitle: "Enter Token",
                isBusy: false,
                showsManualEntry: true
            )
        case .offline:
            return ConnectionPresentation(
                title: "Runtime Offline",
                message: "Make sure your local agent is running and reachable from this iPhone.",
                primaryActionTitle: "Discover Local Runtime",
                secondaryActionTitle: "Scan Pairing QR",
                isBusy: false,
                showsManualEntry: false
            )
        case .savedConnectionOffline(let displayName):
            return ConnectionPresentation(
                title: "Start Runtime on Mac",
                message: "\(displayName) is still paired. Start the runtime on your Mac, then reconnect here.",
                primaryActionTitle: "I've Started It, Reconnect",
                secondaryActionTitle: "Scan New QR",
                isBusy: false,
                showsManualEntry: false,
                trustBadges: ["Saved Pairing", "Mac Action Needed"]
            )
        case .invalidCertificate:
            return ConnectionPresentation(
                title: "Certificate Problem",
                message: "Use a trusted HTTPS certificate or local developer mode.",
                primaryActionTitle: "Retry",
                secondaryActionTitle: "Change Endpoint",
                isBusy: false,
                showsManualEntry: true
            )
        case .missingPhotoEdit:
            return ConnectionPresentation(
                title: "Photo Pack Missing",
                message: "This runtime is reachable, but the Photo Pack is not installed.",
                primaryActionTitle: "Open Setup Guide",
                secondaryActionTitle: "Check Again",
                isBusy: false,
                showsManualEntry: false
            )
        case .localNetworkPermissionRequired:
            return ConnectionPresentation(
                title: "Local Network Access Needed",
                message: "Allow Pocket Agent to find your local agent on the local network.",
                primaryActionTitle: "Open Settings",
                secondaryActionTitle: "Enter Endpoint",
                isBusy: false,
                showsManualEntry: false,
                primaryRecoveryDestination: .appSettings
            )
        case .failed(let message):
            return ConnectionPresentation(
                title: "Connection Failed",
                message: message,
                primaryActionTitle: "Try Again",
                secondaryActionTitle: "Change Endpoint",
                isBusy: false,
                showsManualEntry: true
            )
        }
    }
}

public enum ConnectionRecoveryDestination: Equatable, Sendable {
    case appSettings
}

public struct ConnectionPresentation: Equatable, Sendable {
    public let title: String
    public let message: String
    public let primaryActionTitle: String
    public let secondaryActionTitle: String?
    public let isBusy: Bool
    public let showsManualEntry: Bool
    public let trustBadges: [String]

    public let primaryRecoveryDestination: ConnectionRecoveryDestination?

    public init(
        title: String,
        message: String,
        primaryActionTitle: String,
        secondaryActionTitle: String?,
        isBusy: Bool,
        showsManualEntry: Bool,
        trustBadges: [String] = [],
        primaryRecoveryDestination: ConnectionRecoveryDestination? = nil
    ) {
        self.title = title
        self.message = message
        self.primaryActionTitle = primaryActionTitle
        self.secondaryActionTitle = secondaryActionTitle
        self.isBusy = isBusy
        self.showsManualEntry = showsManualEntry
        self.trustBadges = trustBadges
        self.primaryRecoveryDestination = primaryRecoveryDestination
    }
}
