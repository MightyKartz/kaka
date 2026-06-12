import AgentPocketUI
import AppIntents

@available(iOS 17.0, *)
struct AgentPocketAppIntentsPackage: AppIntentsPackage {
    static var includedPackages: [any AppIntentsPackage.Type] {
        [AgentPocketUIAppIntentsPackage.self]
    }
}
