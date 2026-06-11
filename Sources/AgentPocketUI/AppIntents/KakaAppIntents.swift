import AgentPocketCore
import Foundation

public enum KakaSystemSurface: String, CaseIterable, Codable, Equatable, Sendable {
    case inbox
    case tasks
    case reviewInboxItem
    case reviewRuntimeTask

    public var actionID: String {
        switch self {
        case .inbox:
            return "open_inbox"
        case .tasks:
            return "open_tasks"
        case .reviewInboxItem:
            return "review_inbox_item"
        case .reviewRuntimeTask:
            return "review_runtime_task"
        }
    }

    public var intentTitle: String {
        switch self {
        case .inbox:
            return "Open Inbox"
        case .tasks:
            return "Show Tasks"
        case .reviewInboxItem:
            return "Review Inbox Item"
        case .reviewRuntimeTask:
            return "Review Runtime Task"
        }
    }

    public var targetTab: AgentPocketRootTab {
        switch self {
        case .inbox, .reviewInboxItem:
            return .inbox
        case .tasks, .reviewRuntimeTask:
            return .tasks
        }
    }

    public var isActionButtonRecommended: Bool {
        switch self {
        case .inbox, .tasks:
            return true
        case .reviewInboxItem, .reviewRuntimeTask:
            return false
        }
    }
}

public struct KakaActionButtonShortcutMetadata: Codable, Equatable, Sendable {
    public let actionID: String
    public let shortTitle: String
    public let systemImageName: String
    public let targetSurface: KakaSystemSurface

    public init(
        actionID: String,
        shortTitle: String,
        systemImageName: String,
        targetSurface: KakaSystemSurface
    ) {
        self.actionID = actionID
        self.shortTitle = shortTitle
        self.systemImageName = systemImageName
        self.targetSurface = targetSurface
    }
}

public enum KakaAppIntentCatalog {
    public static let safeActionIDs = KakaSystemSurface.allCases.map(\.actionID)
    public static let requiresForegroundConfirmation = true
    public static let allowsBackgroundSubmission = false
    public static let allowsProviderConfiguration = false
    public static let allowsHiddenCapture = false
    public static let destinationParameterTitle = "Destination"
    public static let taskIDParameterTitle = "Task ID"
    public static let taskActionParameterTitle = "Task Action"
    public static let actionButtonRecommendedActionIDs = [
        KakaSystemSurface.inbox.actionID,
        KakaSystemSurface.tasks.actionID
    ]
    public static let actionButtonUsesForegroundHandoff = true
    public static let actionButtonAllowsBackgroundTaskMutation = false
    public static let actionButtonAllowsRecallMutation = false
    public static let actionButtonAllowsContextSnapshotCollection = false
    public static let actionButtonAllowsRuntimeSettingsChanges = false
    public static let actionButtonShortcuts = [
        KakaActionButtonShortcutMetadata(
            actionID: KakaSystemSurface.inbox.actionID,
            shortTitle: "Open Inbox",
            systemImageName: "tray.full",
            targetSurface: .inbox
        ),
        KakaActionButtonShortcutMetadata(
            actionID: KakaSystemSurface.tasks.actionID,
            shortTitle: "Show Tasks",
            systemImageName: "list.bullet.rectangle",
            targetSurface: .tasks
        )
    ]
}

public struct KakaAppIntentHandoff: Codable, Equatable, Sendable {
    public let surface: KakaSystemSurface
    public let itemID: String?
    public let taskID: String?
    public let createdAt: Date

    public init(
        surface: KakaSystemSurface,
        itemID: String? = nil,
        taskID: String? = nil,
        createdAt: Date = Date()
    ) {
        self.surface = surface
        self.itemID = itemID
        self.taskID = taskID
        self.createdAt = createdAt
    }
}

public struct KakaAppIntentHandoffStore: Sendable {
    public static let suiteName = FileKakaInboxStore.defaultAppGroupIdentifier
    private static let key = "dev.kartz.Kaka.pendingAppIntentHandoff"

    public init() {}

    public func save(_ handoff: KakaAppIntentHandoff) {
        guard let data = try? JSONEncoder().encode(handoff) else {
            return
        }
        userDefaults?.set(data, forKey: Self.key)
    }

    public func consumePendingHandoff() -> KakaAppIntentHandoff? {
        guard let defaults = userDefaults,
              let data = defaults.data(forKey: Self.key),
              let handoff = try? JSONDecoder().decode(KakaAppIntentHandoff.self, from: data) else {
            return nil
        }
        defaults.removeObject(forKey: Self.key)
        return handoff
    }

    private var userDefaults: UserDefaults? {
        UserDefaults(suiteName: Self.suiteName) ?? .standard
    }
}

#if canImport(AppIntents)
import AppIntents

@available(iOS 17.0, macOS 14.0, *)
public enum KakaSystemDestination: String, AppEnum {
    case inbox
    case tasks

    public static let typeDisplayRepresentation = TypeDisplayRepresentation(name: "Destination")
    public static let caseDisplayRepresentations: [Self: DisplayRepresentation] = [
        .inbox: "Inbox",
        .tasks: "Tasks"
    ]

    var surface: KakaSystemSurface {
        switch self {
        case .inbox:
            return .inbox
        case .tasks:
            return .tasks
        }
    }
}

@available(iOS 17.0, macOS 14.0, *)
public struct OpenKakaSurfaceIntent: AppIntent {
    public static let title: LocalizedStringResource = "Open Kaka"
    public static let description = IntentDescription("Open Kaka to a visible surface.")
    public static let openAppWhenRun = true

    @Parameter(title: "Destination")
    public var destination: KakaSystemDestination

    public init() {
        destination = .inbox
    }

    public init(destination: KakaSystemDestination) {
        self.destination = destination
    }

    public func perform() async throws -> some IntentResult {
        KakaAppIntentHandoffStore().save(
            KakaAppIntentHandoff(surface: destination.surface)
        )
        return .result()
    }
}

@available(iOS 17.0, macOS 14.0, *)
public struct ReviewKakaInboxItemIntent: AppIntent {
    public static let title: LocalizedStringResource = "Review Inbox Item"
    public static let description = IntentDescription("Open Kaka to review a visible inbox item.")
    public static let openAppWhenRun = true

    @Parameter(title: "Inbox Item ID")
    public var itemID: String

    public init() {
        itemID = ""
    }

    public init(itemID: String) {
        self.itemID = itemID
    }

    public func perform() async throws -> some IntentResult {
        KakaAppIntentHandoffStore().save(
            KakaAppIntentHandoff(
                surface: .reviewInboxItem,
                itemID: itemID.isEmpty ? nil : itemID
            )
        )
        return .result()
    }
}

@available(iOS 17.0, macOS 14.0, *)
public struct ReviewKakaRuntimeTaskIntent: AppIntent {
    public static let title: LocalizedStringResource = "Review Runtime Task"
    public static let description = IntentDescription("Open Kaka to review a visible runtime task.")
    public static let openAppWhenRun = true

    @Parameter(title: "Task ID")
    public var taskID: String

    public init() {
        taskID = ""
    }

    public init(taskID: String) {
        self.taskID = taskID
    }

    public func perform() async throws -> some IntentResult {
        KakaAppIntentHandoffStore().save(
            KakaAppIntentHandoff(
                surface: .reviewRuntimeTask,
                taskID: taskID.isEmpty ? nil : taskID
            )
        )
        return .result()
    }
}

@available(iOS 17.0, macOS 14.0, *)
public struct AgentPocketUIAppShortcuts: AppShortcutsProvider {
    public static let shortcutTileColor: ShortcutTileColor = .teal

    public static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: OpenKakaSurfaceIntent(destination: .inbox),
            phrases: [
                "Open inbox in \(.applicationName)",
                "Review inbox in \(.applicationName)",
                "Use \(.applicationName) to review inbox"
            ],
            shortTitle: "Open Inbox",
            systemImageName: "tray.full"
        )
        AppShortcut(
            intent: OpenKakaSurfaceIntent(destination: .tasks),
            phrases: [
                "Show tasks in \(.applicationName)",
                "Review tasks in \(.applicationName)",
                "Use \(.applicationName) to review tasks"
            ],
            shortTitle: "Show Tasks",
            systemImageName: "list.bullet.rectangle"
        )
    }
}

@available(iOS 17.0, macOS 14.0, *)
public struct AgentPocketUIAppIntentsPackage: AppIntentsPackage {}
#endif
