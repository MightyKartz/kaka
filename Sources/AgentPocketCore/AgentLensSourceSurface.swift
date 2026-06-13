import Foundation

public enum AgentLensSourceSurface: String, Codable, CaseIterable, Sendable {
    case agentScanner = "agent_scanner"
    case documentScanner = "document_scanner"
    case videoCapture = "video_capture"
    case actionButton = "action_button"
    case shortcut = "shortcut"
}
