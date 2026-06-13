import AgentPocketCore
import Foundation

public struct AgentScanResult: Equatable, Identifiable, Sendable {
    public let rawValue: String

    public init(rawValue: String) {
        self.rawValue = rawValue.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    public var id: String { rawValue }

    public var url: URL? {
        guard let value = URL(string: rawValue),
              let scheme = value.scheme?.lowercased(),
              ["http", "https"].contains(scheme) else {
            return nil
        }
        return value
    }

    public var looksLikeKakaPairingPayload: Bool {
        rawValue.contains(#""pairing_code""#) && rawValue.contains(#""endpoint""#)
    }

    public var isPaymentLikeDeepLink: Bool {
        let lowercased = rawValue.lowercased()
        return lowercased.hasPrefix("alipays://")
            || lowercased.hasPrefix("weixin://")
            || lowercased.hasPrefix("wechat://")
            || lowercased.contains("pay")
    }
}

public struct AgentScanAction: Equatable, Sendable {
    public enum Kind: Hashable, Sendable {
        case connectLocalRuntime
        case summarizeURL
        case openURL
        case saveToInbox
        case askAgentAboutText
        case copy
    }

    public let kind: Kind
    public let title: String
    public let systemImageName: String

    public init(kind: Kind, title: String, systemImageName: String) {
        self.kind = kind
        self.title = title
        self.systemImageName = systemImageName
    }
}

public enum AgentScanInboxDraftBuilder {
    public static func item(for result: AgentScanResult) -> KakaInboxItem {
        if let url = result.url {
            return KakaInboxItem(
                kind: .url,
                sourceSurface: AgentLensSourceSurface.agentScanner.rawValue,
                note: "Summarize this scanned link and suggest the next action.",
                url: url.absoluteString,
                route: .universalIntake
            )
        }

        return KakaInboxItem(
            kind: .text,
            sourceSurface: AgentLensSourceSurface.agentScanner.rawValue,
            note: "Analyze this scanned text and suggest the next action.",
            text: result.rawValue,
            route: .universalIntake
        )
    }
}
