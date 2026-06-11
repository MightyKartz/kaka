import Foundation

public enum ConnectionReadinessIssue: String, CaseIterable, Equatable, Sendable {
    case expiredPairingQRCode
    case pairingCodeAlreadyUsed
    case revokedSavedConnection
    case bridgeUnavailable
    case missingBonjourHost
    case requiredTLSCertificateFailure
    case portConflict
    case disabledHostAction
    case hostExtensionUnavailable
}

public enum ConnectionRecoveryOwner: Equatable, Sendable {
    case phone
    case hostRuntime
}

public enum ConnectionRecoveryAction: String, Equatable, Sendable {
    case scanRefreshedPairingQR
    case generateMobilePairingCode
    case startMobileBridge
    case useLocalNetworkOrManualEndpointFallback
    case repairHostPort
    case waitForRuntimeStateChange
    case checkHostExtension
}

public struct ConnectionReadinessPresentation: Equatable, Sendable {
    public let issue: ConnectionReadinessIssue
    public let title: String
    public let message: String
    public let primaryActionTitle: String
    public let secondaryActionTitle: String?
    public let recoveryOwner: ConnectionRecoveryOwner
    public let recoveryAction: ConnectionRecoveryAction
    public let compatibleConnectionState: ConnectionState?

    public init(
        issue: ConnectionReadinessIssue,
        title: String,
        message: String,
        primaryActionTitle: String,
        secondaryActionTitle: String?,
        recoveryOwner: ConnectionRecoveryOwner,
        recoveryAction: ConnectionRecoveryAction,
        compatibleConnectionState: ConnectionState? = nil
    ) {
        self.issue = issue
        self.title = title
        self.message = message
        self.primaryActionTitle = primaryActionTitle
        self.secondaryActionTitle = secondaryActionTitle
        self.recoveryOwner = recoveryOwner
        self.recoveryAction = recoveryAction
        self.compatibleConnectionState = compatibleConnectionState
    }

    public var visibleCopy: String {
        [
            title,
            message,
            primaryActionTitle,
            secondaryActionTitle
        ].compactMap { $0 }
            .joined(separator: " ")
    }
}

public enum ConnectionReadinessPresenter {
    public static func presentation(
        for issue: ConnectionReadinessIssue
    ) -> ConnectionReadinessPresentation {
        switch issue {
        case .expiredPairingQRCode:
            return ConnectionReadinessPresentation(
                issue: issue,
                title: "Pairing QR Expired",
                message: "Scan the refreshed QR shown by your host runtime. If this iPhone still sees the expired code, refresh the QR on the host and scan again.",
                primaryActionTitle: "Scan Refreshed QR",
                secondaryActionTitle: "Refresh QR on Host",
                recoveryOwner: .phone,
                recoveryAction: .scanRefreshedPairingQR
            )
        case .pairingCodeAlreadyUsed:
            return ConnectionReadinessPresentation(
                issue: issue,
                title: "Pairing QR Already Used",
                message: "Generate a fresh mobile pairing code on the host, then scan the new QR from this iPhone.",
                primaryActionTitle: "Scan New QR",
                secondaryActionTitle: "Generate on Host",
                recoveryOwner: .hostRuntime,
                recoveryAction: .generateMobilePairingCode
            )
        case .revokedSavedConnection:
            let copy = ConnectionState.unauthorized.presentation
            return ConnectionReadinessPresentation(
                issue: issue,
                title: copy.title,
                message: copy.message,
                primaryActionTitle: "Show New Pairing Code on Host",
                secondaryActionTitle: "Scan New QR",
                recoveryOwner: .hostRuntime,
                recoveryAction: .generateMobilePairingCode,
                compatibleConnectionState: .unauthorized
            )
        case .bridgeUnavailable:
            let copy = ConnectionState.offline.presentation
            return ConnectionReadinessPresentation(
                issue: issue,
                title: copy.title,
                message: copy.message,
                primaryActionTitle: "Start Kaka Mobile Bridge",
                secondaryActionTitle: "Discover Local Runtime",
                recoveryOwner: .hostRuntime,
                recoveryAction: .startMobileBridge,
                compatibleConnectionState: .offline
            )
        case .missingBonjourHost:
            return ConnectionReadinessPresentation(
                issue: issue,
                title: "Local Agent Not Found",
                message: "Allow Local Network access and Bonjour discovery, or scan a pairing QR / enter endpoint fallback from the host.",
                primaryActionTitle: "Scan Pairing QR",
                secondaryActionTitle: "Enter Endpoint",
                recoveryOwner: .phone,
                recoveryAction: .useLocalNetworkOrManualEndpointFallback
            )
        case .requiredTLSCertificateFailure:
            let copy = ConnectionState.invalidCertificate.presentation
            return ConnectionReadinessPresentation(
                issue: issue,
                title: copy.title,
                message: copy.message,
                primaryActionTitle: "Retry Trusted Endpoint",
                secondaryActionTitle: "Change Endpoint",
                recoveryOwner: .phone,
                recoveryAction: .useLocalNetworkOrManualEndpointFallback,
                compatibleConnectionState: .invalidCertificate
            )
        case .portConflict:
            return ConnectionReadinessPresentation(
                issue: issue,
                title: "Host Port Needs Attention",
                message: "The host runtime owns port repair. Check the bridge port on the Mac and choose a free port before retrying from the phone.",
                primaryActionTitle: "Repair Host Port",
                secondaryActionTitle: "Try Again",
                recoveryOwner: .hostRuntime,
                recoveryAction: .repairHostPort
            )
        case .disabledHostAction:
            return ConnectionReadinessPresentation(
                issue: issue,
                title: "Host Action Unavailable",
                message: "This action is unavailable until runtime state changes on the host. Wait for setup, health, or required capabilities to finish, then retry.",
                primaryActionTitle: "Check Runtime State",
                secondaryActionTitle: "Try Again",
                recoveryOwner: .hostRuntime,
                recoveryAction: .waitForRuntimeStateChange
            )
        case .hostExtensionUnavailable:
            return ConnectionReadinessPresentation(
                issue: issue,
                title: "Host Extension Not Ready",
                message: "Open Kaka Mobile Bridge on the Mac and finish host setup, then retry from this iPhone.",
                primaryActionTitle: "Check on Mac",
                secondaryActionTitle: "Try Again",
                recoveryOwner: .hostRuntime,
                recoveryAction: .checkHostExtension
            )
        }
    }

    public static func presentation(
        for state: ConnectionState
    ) -> ConnectionReadinessPresentation? {
        switch state {
        case .unauthorized:
            return presentation(for: .revokedSavedConnection)
        case .offline:
            return presentation(for: .bridgeUnavailable)
        case .localNetworkPermissionRequired:
            return presentation(for: .missingBonjourHost)
        case .invalidCertificate:
            return presentation(for: .requiredTLSCertificateFailure)
        case .failed(let message):
            return presentation(forFailureMessage: message)
        case .idle, .scanning, .discovering, .testing, .connected, .missingPhotoEdit:
            return nil
        }
    }

    public static func ownerLabel(for owner: ConnectionRecoveryOwner) -> String {
        switch owner {
        case .phone:
            return "iPhone"
        case .hostRuntime:
            return "Host"
        }
    }

    private static func presentation(
        forFailureMessage message: String
    ) -> ConnectionReadinessPresentation? {
        let normalized = message.lowercased()

        if normalized.contains("expired") {
            return presentation(for: .expiredPairingQRCode)
        }
        if normalized.contains("already used") || normalized.contains("used pairing") {
            return presentation(for: .pairingCodeAlreadyUsed)
        }
        if normalized.contains("certificate") || normalized.contains("tls") {
            return presentation(for: .requiredTLSCertificateFailure)
        }
        return nil
    }
}
