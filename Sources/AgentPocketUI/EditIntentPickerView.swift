import AgentPocketCore
import SwiftUI

public struct EditIntentPickerView: View {
    @Binding private var selection: EditIntent

    public init(selection: Binding<EditIntent>) {
        self._selection = selection
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Scene Pack")
                .font(.headline)
                .accessibilityAddTraits(.isHeader)

            VStack(spacing: 10) {
                ForEach(EditIntent.allCases) { intent in
                    Button { selection = intent } label: {
                        EditIntentRow(intent: intent, isSelected: selection == intent)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(selection == intent ? .white : .primary)
                    .background(
                        selection == intent ? Color.blue : Color.gray.opacity(0.12),
                        in: RoundedRectangle(cornerRadius: 8)
                    )
                    .accessibilityHint(intent.defaultInstruction)
                }
            }
        }
    }
}

private struct EditIntentRow: View {
    let intent: EditIntent
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: symbol)
                .font(.system(size: 18, weight: .semibold))
                .frame(width: 28)
                .foregroundStyle(isSelected ? .white : .blue)
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 3) {
                Text(intent.sceneTitle)
                    .font(.body.weight(.semibold))
                Text(intent.summary)
                    .font(.caption)
                    .foregroundStyle(isSelected ? .white.opacity(0.85) : .secondary)
                    .lineLimit(nil)
            }

            Spacer(minLength: 8)

            if isSelected {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 18, weight: .semibold))
                    .accessibilityLabel("Selected")
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, minHeight: 56, alignment: .leading)
    }

    private var symbol: String {
        switch intent {
        case .naturalEnhance:
            return "wand.and.stars"
        case .portraitPolish:
            return "person.crop.circle"
        case .productShot:
            return "shippingbox"
        case .socialCover:
            return "rectangle.on.rectangle"
        }
    }
}
