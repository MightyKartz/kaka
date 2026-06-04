import Foundation

public enum TaskEvent: Equatable, Sendable {
    case progress(progress: Double, message: String?)
    case completed(variantCount: Int)
}

public enum TaskEventParser {
    public enum ParseError: Error, Equatable {
        case invalidData
    }

    public static func parse(_ text: String) throws -> [TaskEvent] {
        let blocks = text.components(separatedBy: "\n\n")
        var events: [TaskEvent] = []

        for block in blocks {
            let lines = block
                .split(separator: "\n", omittingEmptySubsequences: false)
                .map(String.init)
            guard !lines.isEmpty else { continue }

            var eventName: String?
            var dataLines: [String] = []

            for line in lines {
                if line.hasPrefix("event:") {
                    eventName = line.removing(prefix: "event:").trimmingCharacters(in: .whitespaces)
                } else if line.hasPrefix("data:") {
                    dataLines.append(line.removing(prefix: "data:").trimmingCharacters(in: .whitespaces))
                }
            }

            guard let eventName, !dataLines.isEmpty else { continue }
            let data = Data(dataLines.joined(separator: "\n").utf8)

            switch eventName {
            case "task.progress":
                let payload = try decode(ProgressPayload.self, from: data)
                events.append(.progress(progress: payload.progress, message: payload.message))
            case "task.completed":
                let payload = try decode(CompletedPayload.self, from: data)
                events.append(.completed(variantCount: payload.variantCount))
            default:
                continue
            }
        }

        return events
    }

    private static func decode<T: Decodable>(_ type: T.Type, from data: Data) throws -> T {
        do {
            return try JSONDecoder.mobileBridge.decode(type, from: data)
        } catch {
            throw ParseError.invalidData
        }
    }
}

private struct ProgressPayload: Decodable {
    let progress: Double
    let message: String?
}

private struct CompletedPayload: Decodable {
    let variantCount: Int

    private enum CodingKeys: String, CodingKey {
        case variantCount = "variant_count"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        variantCount = try container.decodeIfPresent(Int.self, forKey: .variantCount) ?? 0
    }
}

public enum TaskProgressTransport: Equatable, Sendable {
    case polling
    case serverSentEvents

    public enum Failure: Equatable, Sendable {
        case parseFailure
        case disconnected
    }

    public static func preferred(supportsSSE: Bool) -> TaskProgressTransport {
        supportsSSE ? .serverSentEvents : .polling
    }

    public static func fallback(after failure: Failure) -> TaskProgressTransport {
        switch failure {
        case .parseFailure, .disconnected:
            return .polling
        }
    }
}

private extension String {
    func removing(prefix: String) -> String {
        guard hasPrefix(prefix) else { return self }
        return String(dropFirst(prefix.count))
    }
}
