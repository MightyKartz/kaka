import Foundation

public enum CaptureConversationAutoreviewPolicy {
    public static func shouldOpenConversation(
        taskID: String?,
        alreadyOpenedTaskID: String?,
        hasImageIntake: Bool
    ) -> Bool {
        guard let taskID, hasImageIntake else {
            return false
        }
        return taskID != alreadyOpenedTaskID
    }
}
