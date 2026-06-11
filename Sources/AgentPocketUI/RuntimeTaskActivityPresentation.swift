import AgentPocketCore
import Foundation

@MainActor
public protocol RuntimeTaskActivityCoordinating: AnyObject {
    func sync(tasks: [RuntimeTaskSummary]) async
}

@MainActor
public final class NoopRuntimeTaskActivityCoordinator: RuntimeTaskActivityCoordinating {
    public init() {}

    public func sync(tasks: [RuntimeTaskSummary]) async {}
}

@MainActor
public final class RuntimeTaskActivitySyncPlanner {
    public struct Plan: Equatable, Sendable {
        public let activeSnapshots: [RuntimeTaskActivitySnapshot]
        public let endedTaskIDs: [String]
    }

    private var activeTaskIDs: Set<String> = []

    public init() {}

    public func seedActiveTaskIDs(_ taskIDs: [String]) {
        activeTaskIDs.formUnion(taskIDs)
    }

    public func plan(tasks: [RuntimeTaskSummary]) -> Plan {
        let snapshots = tasks.map(RuntimeTaskActivitySnapshot.init(task:))
        let activeSnapshots = snapshots.filter { $0.isTerminal == false }
        let nextActiveTaskIDs = Set(activeSnapshots.map(\.taskID))
        let terminalTaskIDs = Set(snapshots.filter(\.isTerminal).map(\.taskID))
        let disappearedTaskIDs = activeTaskIDs.subtracting(nextActiveTaskIDs).subtracting(terminalTaskIDs)
        activeTaskIDs = nextActiveTaskIDs

        return Plan(
            activeSnapshots: activeSnapshots,
            endedTaskIDs: Array(terminalTaskIDs.union(disappearedTaskIDs)).sorted()
        )
    }
}

#if os(iOS) && canImport(ActivityKit)
@preconcurrency import ActivityKit

@MainActor
public final class ActivityKitRuntimeTaskActivityCoordinator: RuntimeTaskActivityCoordinating {
    private let planner = RuntimeTaskActivitySyncPlanner()

    public init() {}

    public func sync(tasks: [RuntimeTaskSummary]) async {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else {
            return
        }

        planner.seedActiveTaskIDs(existingActivityTaskIDs())
        let plan = planner.plan(tasks: tasks)
        for taskID in plan.endedTaskIDs {
            await endActivity(taskID: taskID)
        }
        for snapshot in plan.activeSnapshots {
            await upsertActivity(snapshot: snapshot)
        }
    }

    private func upsertActivity(snapshot: RuntimeTaskActivitySnapshot) async {
        if let activity = activity(taskID: snapshot.taskID) {
            let content = ActivityContent(
                state: RuntimeTaskActivityAttributes.ContentState(snapshot: snapshot),
                staleDate: nil
            )
            await activity.update(content)
            return
        }

        do {
            _ = try Activity.request(
                attributes: RuntimeTaskActivityAttributes(snapshot: snapshot),
                content: ActivityContent(
                    state: RuntimeTaskActivityAttributes.ContentState(snapshot: snapshot),
                    staleDate: nil
                )
            )
        } catch {
            return
        }
    }

    private func endActivity(taskID: String) async {
        guard let activity = activity(taskID: taskID) else {
            return
        }
        await activity.end(nil, dismissalPolicy: .immediate)
    }

    private func activity(taskID: String) -> Activity<RuntimeTaskActivityAttributes>? {
        Activity<RuntimeTaskActivityAttributes>.activities.first { activity in
            activity.attributes.taskID == taskID
        }
    }

    private func existingActivityTaskIDs() -> [String] {
        Activity<RuntimeTaskActivityAttributes>.activities.map { activity in
            activity.attributes.taskID
        }
    }
}
#else
public typealias ActivityKitRuntimeTaskActivityCoordinator = NoopRuntimeTaskActivityCoordinator
#endif
