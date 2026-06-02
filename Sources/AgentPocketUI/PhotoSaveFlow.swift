import AgentPocketCore
import Foundation

public final class PhotoSaveFlow: ObservableObject {
    public enum State: Equatable, Sendable {
        case idle
        case requestingPermission
        case saving
        case saved
        case permissionDenied
        case failed(message: String)
    }

    public enum Permission: Equatable, Sendable {
        case authorized
        case denied
        case limited
    }

    public enum RecoveryDestination: Equatable, Sendable {
        case appSettings
    }

    @Published public private(set) var state: State = .idle

    public init() {}

    public var recoveryActionTitle: String? {
        switch state {
        case .permissionDenied:
            return "Open Settings"
        case .failed:
            return "Try Again"
        default:
            return nil
        }
    }

    public var recoveryDestination: RecoveryDestination? {
        switch state {
        case .permissionDenied:
            return .appSettings
        default:
            return nil
        }
    }

    public var isBusy: Bool {
        state.isBusy
    }

    public func beginSave() {
        state = .requestingPermission
    }

    public func handlePermission(_ permission: Permission) {
        switch permission {
        case .authorized, .limited:
            state = .saving
        case .denied:
            state = .permissionDenied
        }
    }

    public func markSaved() {
        state = .saved
    }

    public func markFailed(_ message: String) {
        state = .failed(message: message)
    }

    @MainActor
    public func save(_ asset: DownloadedAsset, using saver: PhotoLibrarySaving) async {
        beginSave()
        do {
            let result = try await saver.save(asset)
            switch result {
            case .saved:
                state = .saving
                markSaved()
            case .permissionDenied:
                state = .permissionDenied
            }
        } catch {
            state = .failed(message: "The image could not be saved.")
        }
    }
}

public extension PhotoSaveFlow.State {
    var isBusy: Bool {
        switch self {
        case .requestingPermission, .saving:
            return true
        default:
            return false
        }
    }
}
