import Foundation

public enum AgentScanActionPolicy {
    public static func actions(for result: AgentScanResult) -> [AgentScanAction] {
        if result.looksLikeKakaPairingPayload {
            return [
                AgentScanAction(kind: .connectLocalRuntime, title: "Connect Local Runtime", systemImageName: "qrcode.viewfinder"),
                AgentScanAction(kind: .copy, title: "Copy", systemImageName: "doc.on.doc")
            ]
        }

        if result.url != nil {
            let actions = [
                AgentScanAction(kind: .summarizeURL, title: "Ask Agent", systemImageName: "sparkles"),
                AgentScanAction(kind: .openURL, title: "Open", systemImageName: "safari"),
                AgentScanAction(kind: .copy, title: "Copy", systemImageName: "doc.on.doc"),
                AgentScanAction(kind: .saveToInbox, title: "Save", systemImageName: "tray.and.arrow.down")
            ]
            return result.isPaymentLikeWebURL ? actions.filter { $0.kind != .openURL } : actions
        }

        return [
            AgentScanAction(kind: .askAgentAboutText, title: "Ask Agent", systemImageName: "text.viewfinder"),
            AgentScanAction(kind: .copy, title: "Copy", systemImageName: "doc.on.doc")
        ]
    }
}
