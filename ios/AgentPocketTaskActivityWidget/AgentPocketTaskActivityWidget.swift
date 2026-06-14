import AgentPocketCore
import ActivityKit
import SwiftUI
import WidgetKit

@main
struct AgentPocketTaskActivityWidgetBundle: WidgetBundle {
    var body: some Widget {
        RuntimeTaskActivityWidget()
    }
}

struct RuntimeTaskActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: RuntimeTaskActivityAttributes.self) { context in
            RuntimeTaskActivityLockScreenView(
                title: context.attributes.title,
                phase: context.state.phase,
                approvalNeeded: context.state.approvalNeeded,
                progress: context.state.progress,
                message: context.state.message
            )
        } dynamicIsland: { context in
                DynamicIsland {
                    DynamicIslandExpandedRegion(.leading) {
                        Text(context.state.phase.statusLabel)
                            .font(.caption)
                            .fontWeight(.semibold)
                            .lineLimit(1)
                    }
                    DynamicIslandExpandedRegion(.trailing) {
                        Text(context.state.approvalNeeded ? "Review" : "Active")
                            .font(.caption2)
                            .lineLimit(1)
                    }
                    DynamicIslandExpandedRegion(.bottom) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(context.attributes.title)
                                .font(.footnote.weight(.semibold))
                                .lineLimit(1)
                            if let message = context.state.message {
                                Text(message)
                                    .font(.caption2)
                                    .lineLimit(2)
                                    .minimumScaleFactor(0.82)
                            }
                            ProgressView(value: context.state.progress)
                                .tint(context.state.approvalNeeded ? .orange : .accentColor)
                        }
                    }
                } compactLeading: {
                Image(systemName: context.state.approvalNeeded ? "exclamationmark.circle.fill" : "clock")
            } compactTrailing: {
                Text(context.state.phase.shortLabel)
                    .font(.caption2)
                    .fontWeight(.semibold)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
            } minimal: {
                Image(systemName: context.state.approvalNeeded ? "exclamationmark.circle.fill" : "clock")
            }
            .keylineTint(context.state.approvalNeeded ? .orange : .accentColor)
        }
        .configurationDisplayName("Pocket Agent Task")
        .description("Shows phone-safe Pocket Agent task status.")
    }
}

private struct RuntimeTaskActivityLockScreenView: View {
    let title: String
    let phase: RuntimeTaskActivityPhase
    let approvalNeeded: Bool
    let progress: Double
    let message: String?

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: approvalNeeded ? "exclamationmark.circle.fill" : "clock")
                .font(.title3)
                .foregroundStyle(approvalNeeded ? .orange : .accentColor)
                .frame(width: 28, height: 28)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.headline)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)

                VStack(alignment: .leading, spacing: 3) {
                    Text(message ?? phase.statusLabel)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                    ProgressView(value: progress)
                        .tint(approvalNeeded ? .orange : .accentColor)
                }
            }

            Spacer(minLength: 8)

            if approvalNeeded {
                Text("Review")
                    .font(.caption2)
                    .fontWeight(.semibold)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(.orange.opacity(0.18)))
            }
        }
        .padding(16)
        .activityBackgroundTint(Color(.systemBackground))
        .activitySystemActionForegroundColor(.accentColor)
    }
}
