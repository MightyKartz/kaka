import AgentPocketCore
import SwiftUI

public struct TaskProgressView: View {
    private let status: TaskStatusResponse

    public init(status: TaskStatusResponse) {
        self.status = status
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Image(systemName: symbol)
                .font(.system(size: 34, weight: .semibold))
                .foregroundStyle(tint)
                .accessibilityHidden(true)

            Text(title)
                .font(.title.bold())
                .accessibilityAddTraits(.isHeader)

            if let message = status.message {
                Text(message)
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .lineLimit(nil)
            }

            ProgressView(value: progress)
                .progressViewStyle(.linear)
                .accessibilityLabel("Photo edit progress")
                .accessibilityValue("\(Int(progress * 100)) percent")

            if !status.isTerminal {
                Button {
                } label: {
                    Label("Cancel", systemImage: "xmark.circle")
                        .frame(maxWidth: .infinity, minHeight: 48)
                }
                .buttonStyle(.bordered)
            }
        }
        .padding(22)
        .frame(maxWidth: 560, alignment: .leading)
        .navigationTitle("Progress")
    }

    private var progress: Double {
        min(max(status.progress ?? 0, 0), 1)
    }

    private var title: String {
        switch status.status {
        case "completed":
            return "Variants Ready"
        case "failed":
            return "Edit Failed"
        case "cancelled":
            return "Edit Cancelled"
        case "queued":
            return "Queued"
        default:
            return "Editing Photo"
        }
    }

    private var symbol: String {
        switch status.status {
        case "completed":
            return "checkmark.circle.fill"
        case "failed", "cancelled":
            return "exclamationmark.triangle.fill"
        default:
            return "wand.and.stars"
        }
    }

    private var tint: Color {
        switch status.status {
        case "completed":
            return .green
        case "failed", "cancelled":
            return .red
        default:
            return .blue
        }
    }
}
