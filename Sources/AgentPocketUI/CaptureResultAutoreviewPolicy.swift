import Foundation

public enum CaptureResultAutoreviewPolicy {
    public static func shouldOpenResult(
        taskID: String?,
        alreadyOpenedTaskID: String?,
        hasCompletedStatus: Bool
    ) -> Bool {
        guard hasCompletedStatus, let taskID, taskID.isEmpty == false else {
            return false
        }
        return taskID != alreadyOpenedTaskID
    }
}
