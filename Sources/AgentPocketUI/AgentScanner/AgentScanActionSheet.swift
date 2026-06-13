import SwiftUI

public struct AgentScanActionSheet: View {
    public let result: AgentScanResult
    public let onAction: (AgentScanAction.Kind) -> Void

    public init(
        result: AgentScanResult,
        onAction: @escaping (AgentScanAction.Kind) -> Void
    ) {
        self.result = result
        self.onAction = onAction
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Capsule()
                .fill(Color.white.opacity(0.16))
                .frame(width: 44, height: 4)
                .frame(maxWidth: .infinity)
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 8) {
                Text("Scanned")
                    .font(.headline)
                    .foregroundStyle(.white)

                Text(result.rawValue)
                    .font(.callout)
                    .foregroundStyle(.white.opacity(0.76))
                    .lineLimit(5)
                    .textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true)
            }

            LazyVGrid(columns: [GridItem(.adaptive(minimum: 118), spacing: 10)], spacing: 10) {
                ForEach(AgentScanActionPolicy.actions(for: result), id: \.kind) { action in
                    Button {
                        onAction(action.kind)
                    } label: {
                        VStack(spacing: 8) {
                            Image(systemName: action.systemImageName)
                                .font(.system(size: 20, weight: .semibold))
                            Text(action.title)
                                .font(.caption.weight(.semibold))
                                .lineLimit(1)
                                .minimumScaleFactor(0.78)
                        }
                        .frame(maxWidth: .infinity, minHeight: 74)
                    }
                    .buttonStyle(AgentPocketDarkSecondaryButtonStyle())
                }
            }
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(AgentPocketDesignTokens.darkBackground)
        .presentationDetents([.height(310), .medium])
        .presentationDragIndicator(.hidden)
    }
}
