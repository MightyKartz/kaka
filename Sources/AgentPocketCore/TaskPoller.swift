import Foundation

public struct TaskPoller: Sendable {
    public let intervalNanoseconds: UInt64

    public init(intervalNanoseconds: UInt64 = 2_000_000_000) {
        self.intervalNanoseconds = intervalNanoseconds
    }

    public func pollUntilTerminal(
        fetch: @escaping () async throws -> TaskStatusResponse
    ) async throws -> TaskStatusResponse {
        while true {
            let status = try await fetch()
            if status.isTerminal {
                return status
            }
            if intervalNanoseconds > 0 {
                try await Task.sleep(nanoseconds: intervalNanoseconds)
            }
        }
    }
}
