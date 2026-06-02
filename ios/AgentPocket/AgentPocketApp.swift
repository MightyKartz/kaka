import AgentPocketCore
import AgentPocketUI
import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

@main
struct AgentPocketApp: App {
    var body: some Scene {
        WindowGroup {
            #if DEBUG
            let processArguments = ProcessInfo.processInfo.arguments
            if let configuration = SimulatorSmokeConfiguration(processArguments: processArguments) {
                SimulatorSmokeView(configuration: configuration)
            } else if let configuration = SimulatorDiscoveryRefreshSmokeConfiguration(processArguments: processArguments) {
                SimulatorDiscoveryRefreshSmokeView(configuration: configuration)
            } else if SimulatorDiscoveryConfirmSmokeConfiguration(processArguments: processArguments) != nil {
                SimulatorDiscoveryConfirmSmokeView()
            } else if SimulatorConnectionFailedSmokeConfiguration(processArguments: processArguments) != nil {
                SimulatorConnectionFailedSmokeView()
            } else if SimulatorPhotosPickerUISmokeConfiguration(processArguments: processArguments) != nil {
                SimulatorPhotosPickerUISmokeView()
            } else if SimulatorCaptureReadySmokeConfiguration(processArguments: processArguments) != nil {
                SimulatorCaptureReadySmokeView()
            } else if SimulatorCaptureCompletedSmokeConfiguration(processArguments: processArguments) != nil {
                SimulatorCaptureCompletedSmokeView()
            } else if SimulatorResultGallerySmokeConfiguration(processArguments: processArguments) != nil {
                SimulatorResultGallerySmokeView()
            } else if SimulatorResultGalleryDownloadedSmokeConfiguration(processArguments: processArguments) != nil {
                SimulatorResultGalleryDownloadedSmokeView()
            } else if SimulatorShareSheetSmokeConfiguration(processArguments: processArguments) != nil {
                SimulatorShareSheetSmokeView()
            } else {
                AgentPocketRootView()
            }
            #else
            AgentPocketRootView()
            #endif
        }
    }
}

#if DEBUG
private struct SimulatorSmokeConfiguration: Equatable {
    let baseURL: String
    let token: String

    init?(processArguments: [String]) {
        guard processArguments.contains("--agent-pocket-simulator-smoke") else {
            return nil
        }
        baseURL = Self.value(after: "--agent-pocket-smoke-base-url", in: processArguments) ?? "http://127.0.0.1:8766"
        token = Self.value(after: "--agent-pocket-smoke-token", in: processArguments) ?? "dev-mobile-token"
    }

    private static func value(after flag: String, in arguments: [String]) -> String? {
        guard let index = arguments.firstIndex(of: flag), arguments.indices.contains(index + 1) else {
            return nil
        }
        return arguments[index + 1]
    }
}

private struct SimulatorCaptureReadySmokeConfiguration: Equatable {
    init?(processArguments: [String]) {
        guard processArguments.contains("--agent-pocket-simulator-capture-ready-smoke") else {
            return nil
        }
    }
}

private struct SimulatorCaptureCompletedSmokeConfiguration: Equatable {
    init?(processArguments: [String]) {
        guard processArguments.contains("--agent-pocket-simulator-capture-completed-smoke") else {
            return nil
        }
    }
}

private struct SimulatorDiscoveryRefreshSmokeConfiguration: Equatable {
    let baseURL: String

    init?(processArguments: [String]) {
        guard processArguments.contains("--agent-pocket-simulator-discovery-refresh-smoke") else {
            return nil
        }
        baseURL = Self.value(after: "--agent-pocket-smoke-base-url", in: processArguments) ?? "http://127.0.0.1:8767"
    }

    private static func value(after flag: String, in arguments: [String]) -> String? {
        guard let index = arguments.firstIndex(of: flag), arguments.indices.contains(index + 1) else {
            return nil
        }
        return arguments[index + 1]
    }
}

private struct SimulatorConnectionFailedSmokeConfiguration: Equatable {
    init?(processArguments: [String]) {
        guard processArguments.contains("--agent-pocket-simulator-connect-failed-smoke") else {
            return nil
        }
    }
}

private struct SimulatorDiscoveryConfirmSmokeConfiguration: Equatable {
    init?(processArguments: [String]) {
        guard processArguments.contains("--agent-pocket-simulator-discovery-confirm-smoke") else {
            return nil
        }
    }
}

private struct SimulatorResultGallerySmokeConfiguration: Equatable {
    init?(processArguments: [String]) {
        guard processArguments.contains("--agent-pocket-simulator-result-gallery-smoke") else {
            return nil
        }
    }
}

private struct SimulatorResultGalleryDownloadedSmokeConfiguration: Equatable {
    init?(processArguments: [String]) {
        guard processArguments.contains("--agent-pocket-simulator-result-gallery-downloaded-smoke") else {
            return nil
        }
    }
}

private struct SimulatorShareSheetSmokeConfiguration: Equatable {
    init?(processArguments: [String]) {
        guard processArguments.contains("--agent-pocket-simulator-share-sheet-smoke") else {
            return nil
        }
    }
}

private struct SimulatorPhotosPickerUISmokeConfiguration: Equatable {
    init?(processArguments: [String]) {
        guard processArguments.contains("--agent-pocket-simulator-picker-ui-smoke") else {
            return nil
        }
    }
}

private struct SimulatorDiscoveryRefreshSmokeView: View {
    let configuration: SimulatorDiscoveryRefreshSmokeConfiguration
    @StateObject private var viewModel: ConnectionViewModel
    @State private var didRun = false

    init(configuration: SimulatorDiscoveryRefreshSmokeConfiguration) {
        self.configuration = configuration
        _viewModel = StateObject(
            wrappedValue: ConnectionViewModel(
                runtimeDiscoverer: SimulatorNoPayloadRuntimeDiscoverer(baseURL: configuration.baseURL)
            )
        )
    }

    var body: some View {
        ConnectView(viewModel: viewModel)
            .task {
                await runDiscoveryRefreshIfNeeded()
            }
    }

    @MainActor
    private func runDiscoveryRefreshIfNeeded() async {
        guard didRun == false else {
            return
        }
        didRun = true
        await viewModel.discoverLocalRuntimes(
            timeout: 0.1,
            autoPairSingleRuntime: true,
            showsNoResultsFailure: true,
            deviceName: "Simulator iPhone",
            devicePublicID: "simulator-iphone"
        )
    }
}

private struct SimulatorNoPayloadRuntimeDiscoverer: RuntimeDiscovering {
    let baseURL: String

    func discover(timeout: TimeInterval) async throws -> [DiscoveredRuntime] {
        let endpoint = try AgentEndpoint(
            rawURL: baseURL,
            runtime: "hermes",
            displayName: "Agent Pocket Mock Agent"
        )
        return [
            DiscoveredRuntime(
                displayName: "Agent Pocket Mock Agent",
                endpoint: endpoint,
                pairingPayload: nil
            )
        ]
    }
}

private struct SimulatorConnectionFailedSmokeView: View {
    @StateObject private var viewModel = ConnectionViewModel(
        state: .failed(message: "No local agent runtime found. Scan a pairing QR or enter an endpoint.")
    )

    var body: some View {
        NavigationStack {
            ConnectView(viewModel: viewModel)
        }
        .task {
            writeReceipt()
        }
    }

    private func writeReceipt() {
        guard let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
            return
        }
        let copy = ConnectScreenCopy(
            state: viewModel.state,
            language: .chinese,
            fallbackDeviceName: "我的电脑"
        )
        let payload: [String: Any] = [
            "phase": "connect-failed-ui",
            "ok": copy.connectTitle == "连接失败" && copy.visibleCopy.localizedCaseInsensitiveContains("No local agent runtime found") == false,
            "state": "failed",
            "title": copy.connectTitle,
            "subtitle": copy.connectSubtitle,
            "manual_visible": viewModel.state.presentation.showsManualEntry,
            "manual_title": copy.manualTitle,
            "primary_action": copy.primaryButtonTitle,
            "brand_in_hero": false
        ]
        let receiptURL = documentsURL.appendingPathComponent("agent-pocket-connect-failed-smoke.json")
        if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: receiptURL, options: [.atomic])
        }
    }
}

private struct SimulatorDiscoveryConfirmSmokeView: View {
    @StateObject private var viewModel = Self.makeViewModel()

    var body: some View {
        NavigationStack {
            ConnectView(viewModel: viewModel)
        }
        .task {
            writeReceipt()
        }
    }

    @MainActor
    private static func makeViewModel() -> ConnectionViewModel {
        let endpoint = try! AgentEndpoint(
            rawURL: "http://kartz-macbook.local:8765",
            runtime: "hermes",
            displayName: "Kartz Mac Runtime"
        )
        return ConnectionViewModel(
            discoveredRuntimes: [
                DiscoveredRuntime(
                    displayName: "Kartz Mac Runtime",
                    endpoint: endpoint,
                    pairingPayload: """
                    {"version":1,"endpoint":"http://kartz-macbook.local:8765","runtime":"hermes","display_name":"Kartz Mac Runtime","pairing_code":"pair_smoke","expires_at":"2099-01-01T00:00:00Z"}
                    """
                )
            ]
        )
    }

    private func writeReceipt() {
        guard let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
            return
        }
        let copy = ConnectScreenCopy(
            state: viewModel.state,
            language: .chinese,
            fallbackDeviceName: "我的电脑"
        )
        let heroStatus = "已发现 · 待确认"
        let heroPrimaryAction = "重新搜索"
        let payload: [String: Any] = [
            "phase": "discovery-confirm-ui",
            "ok": viewModel.state == .idle
                && viewModel.discoveredRuntimes.count == 1
                && heroStatus == "已发现 · 待确认"
                && heroPrimaryAction == "重新搜索"
                && copy.trustBadgeTitles == ["本地网络", "待确认"],
            "state": "idle",
            "discovered_runtime_count": viewModel.discoveredRuntimes.count,
            "hero_status": heroStatus,
            "nearby_title": copy.nearbyRuntimeTitle,
            "nearby_description": copy.nearbyRuntimeDescription,
            "primary_action": heroPrimaryAction,
            "runtime_card_action": copy.connectRuntimeTitle,
            "scan_action": copy.scanCodeTitle,
            "trust_badges": copy.trustBadgeTitles
        ]
        let receiptURL = documentsURL.appendingPathComponent("agent-pocket-discovery-confirm-smoke.json")
        if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: receiptURL, options: [.atomic])
        }
    }
}

private struct SimulatorPhotosPickerUISmokeView: View {
    var body: some View {
        VStack(spacing: 0) {
            Text("Photos Picker UI Smoke")
                .font(.caption)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("photosPickerUISmokeMarker")

            CaptureView(
                connectedRuntime: SimulatorSmokeFixtures.runtime,
                activeConnection: { SimulatorSmokeFixtures.connection }
            )
        }
    }
}

private struct SimulatorCaptureReadySmokeView: View {
    @StateObject private var viewModel = CaptureFlowViewModel()

    var body: some View {
        CaptureView(
            viewModel: viewModel,
            connectedRuntime: SimulatorSmokeFixtures.runtime,
            activeConnection: { SimulatorSmokeFixtures.connection }
        )
        .task {
            await prepareReadyImageIfNeeded()
        }
    }

    @MainActor
    private func prepareReadyImageIfNeeded() async {
        guard viewModel.preparedUpload == nil else {
            return
        }
        viewModel.markLoadingSelectedPhoto()
        do {
            try viewModel.prepareSelectedImage(
                data: Self.fixturePNG,
                sourceMimeType: "image/png",
                fileName: "library.png",
                maxUploadMB: 30
            )
            writeReceipt(ok: true)
        } catch {
            viewModel.markFailed("Simulator capture-ready smoke could not prepare the fixture photo.")
            writeReceipt(ok: false)
        }
    }

    private func writeReceipt(ok: Bool) {
        guard let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
            return
        }
        let payload: [String: Any] = [
            "phase": "capture-ready",
            "ok": ok,
            "state": stateName,
            "file_name": readyFileName,
            "intent_title": viewModel.selectedIntent.displayTitle,
            "has_prepared_upload": viewModel.preparedUpload != nil,
            "prepared_file_name": viewModel.preparedUpload?.fileName ?? "",
            "prepared_mime_type": viewModel.preparedUpload?.mimeType ?? "",
            "prepared_size_bytes": viewModel.preparedUpload?.data.count ?? 0,
            "send_to_local_agent_enabled": isSendToLocalAgentEnabled,
            "send_to_hermes_enabled": isSendToHermesEnabled,
            "selection_source": "library_fixture",
            "preprocessing_path": "CaptureFlowViewModel.prepareSelectedImage",
            "primary_action": "Send to Local Agent",
            "ready_status_accessibility_identifier": "selectedPhotoReadyStatus",
            "send_button_accessibility_identifier": "sendToLocalAgentButton"
        ]
        let receiptURL = documentsURL.appendingPathComponent("agent-pocket-capture-ready-smoke.json")
        if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: receiptURL, options: [.atomic])
        }
    }

    private var stateName: String {
        switch viewModel.state {
        case .empty:
            return "empty"
        case .loadingPhoto:
            return "loadingPhoto"
        case .ready:
            return "ready"
        case .uploading:
            return "uploading"
        case .startingTask:
            return "startingTask"
        case .submitted:
            return "submitted"
        case .running:
            return "running"
        case .completed:
            return "completed"
        case .failed:
            return "failed"
        }
    }

    private var readyFileName: String {
        if case .ready(let fileName, _) = viewModel.state {
            return fileName
        }
        return ""
    }

    private var isSendToHermesEnabled: Bool {
        isSendToLocalAgentEnabled
    }

    private var isSendToLocalAgentEnabled: Bool {
        if case .ready = viewModel.state {
            return viewModel.preparedUpload != nil
        }
        return false
    }

    private static let fixturePNG = Data(base64Encoded: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")!
}

private struct SimulatorCaptureCompletedSmokeView: View {
    @StateObject private var viewModel = CaptureFlowViewModel()

    var body: some View {
        NavigationStack {
            CaptureView(
                viewModel: viewModel,
                connectedRuntime: SimulatorSmokeFixtures.runtime,
                activeConnection: { SimulatorSmokeFixtures.connection }
            )
        }
        .task {
            markCompletedIfNeeded()
        }
    }

    @MainActor
    private func markCompletedIfNeeded() {
        guard viewModel.completedStatus == nil else {
            return
        }
        viewModel.markCompleted(SimulatorResultGallerySmokeFixtures.completedStatus)
        writeReceipt()
    }

    @MainActor
    private func writeReceipt() {
        guard let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
            return
        }
        let variants = viewModel.completedStatus?.variants ?? []
        let payload: [String: Any] = [
            "phase": "capture-completed",
            "ok": isReviewResultsEnabled && variants.isEmpty == false,
            "state": stateName,
            "task_id": viewModel.completedStatus?.taskID ?? "",
            "variants_count": variants.count,
            "review_results_enabled": isReviewResultsEnabled,
            "review_results_primary": isReviewResultsEnabled,
            "send_to_local_agent_enabled": false,
            "send_to_hermes_enabled": false
        ]
        let receiptURL = documentsURL.appendingPathComponent("agent-pocket-capture-completed-smoke.json")
        if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: receiptURL, options: [.atomic])
        }
    }

    @MainActor
    private var stateName: String {
        switch viewModel.state {
        case .completed:
            return "completed"
        case .empty:
            return "empty"
        case .loadingPhoto:
            return "loadingPhoto"
        case .ready:
            return "ready"
        case .uploading:
            return "uploading"
        case .startingTask:
            return "startingTask"
        case .submitted:
            return "submitted"
        case .running:
            return "running"
        case .failed:
            return "failed"
        }
    }

    @MainActor
    private var isReviewResultsEnabled: Bool {
        if case .completed = viewModel.state {
            return viewModel.completedStatus != nil
        }
        return false
    }
}

private struct SimulatorResultGallerySmokeView: View {
    var body: some View {
        NavigationStack {
            ResultGalleryView(
                status: SimulatorResultGallerySmokeFixtures.completedStatus,
                activeConnection: { SimulatorSmokeFixtures.connection },
                downloader: SimulatorResultGallerySmokeDownloader(),
                initialOriginalAsset: SimulatorResultGallerySmokeFixtures.originalAsset,
                photoSaver: nil
            )
        }
        .task {
            writeReceipt()
        }
    }

    private func writeReceipt() {
        guard let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
            return
        }
        let variants = SimulatorResultGallerySmokeFixtures.completedStatus.variants ?? []
        let selectedVariant = variants.first
        let payload: [String: Any] = [
            "phase": "result-gallery",
            "ok": selectedVariant != nil,
            "state": selectedVariant == nil ? "failed" : "ready",
            "task_status": SimulatorResultGallerySmokeFixtures.completedStatus.status,
            "variants_count": variants.count,
            "selected_variant_id": selectedVariant?.id ?? "",
            "selected_asset_id": selectedVariant?.assetID ?? "",
            "has_explanation": (SimulatorResultGallerySmokeFixtures.completedStatus.explanation ?? "").isEmpty == false,
            "download_selected_enabled": selectedVariant != nil && SimulatorSmokeFixtures.connection != nil,
            "save_enabled": false,
            "share_enabled": false
        ]
        let receiptURL = documentsURL.appendingPathComponent("agent-pocket-result-gallery-smoke.json")
        if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: receiptURL, options: [.atomic])
        }
    }
}

private struct SimulatorResultGalleryDownloadedSmokeView: View {
    var body: some View {
        NavigationStack {
            ResultGalleryView(
                status: SimulatorResultGallerySmokeFixtures.completedStatus,
                activeConnection: { SimulatorSmokeFixtures.connection },
                downloader: SimulatorResultGallerySmokeDownloader(),
                initialOriginalAsset: SimulatorResultGallerySmokeFixtures.originalAsset,
                initialDownloadedAssets: [
                    "variant_clean_pro": SimulatorResultGallerySmokeFixtures.downloadedAsset
                ],
                photoSaver: nil
            )
        }
        .task {
            writeReceipt()
        }
    }

    private func writeReceipt() {
        guard let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
            return
        }
        let variants = SimulatorResultGallerySmokeFixtures.completedStatus.variants ?? []
        let selectedVariant = variants.first
        let downloadedAsset = SimulatorResultGallerySmokeFixtures.downloadedAsset
        let payload: [String: Any] = [
            "phase": "result-gallery-downloaded",
            "ok": selectedVariant != nil && downloadedAsset.data.isEmpty == false,
            "state": selectedVariant == nil ? "failed" : "downloaded",
            "task_status": SimulatorResultGallerySmokeFixtures.completedStatus.status,
            "variants_count": variants.count,
            "selected_variant_id": selectedVariant?.id ?? "",
            "selected_asset_id": selectedVariant?.assetID ?? "",
            "downloaded_asset_bytes": downloadedAsset.data.count,
            "downloaded_mime_type": downloadedAsset.mimeType,
            "recipe_summary": SimulatorResultGallerySmokeFixtures.completedStatus.recipeSummary ?? "",
            "share_caption": SimulatorResultGallerySmokeFixtures.completedStatus.shareCaption ?? "",
            "download_selected_enabled": false,
            "save_enabled": selectedVariant != nil && downloadedAsset.data.isEmpty == false,
            "share_enabled": selectedVariant != nil && downloadedAsset.data.isEmpty == false
        ]
        let receiptURL = documentsURL.appendingPathComponent("agent-pocket-result-gallery-downloaded-smoke.json")
        if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: receiptURL, options: [.atomic])
        }
    }
}

private struct SimulatorShareSheetSmokeView: View {
    @State private var sharePayload: SimulatorShareSheetPayload?

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "square.and.arrow.up")
                .font(.system(size: 42, weight: .semibold))
            Text("Share Sheet Smoke")
                .font(.title.bold())
            Text("Preparing selected Master image and generated caption.")
                .foregroundStyle(.secondary)
        }
        .padding()
        .task {
            guard sharePayload == nil else {
                return
            }
            do {
                let payload = try SimulatorShareSheetPayload.make()
                sharePayload = payload
                writeReceipt(payload: payload, presented: false)
            } catch {
                writeFailureReceipt(message: "Could not prepare share payload.")
            }
        }
        .sheet(item: $sharePayload) { payload in
            SimulatorShareSheetPresenter(payload: payload) {
                writeReceipt(payload: payload, presented: true)
            }
        }
    }

    private func writeReceipt(payload: SimulatorShareSheetPayload, presented: Bool) {
        guard let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
            return
        }
        let receiptURL = documentsURL.appendingPathComponent("agent-pocket-share-sheet-smoke.json")
        let receipt: [String: Any] = [
            "phase": "share-sheet-handoff",
            "ok": presented,
            "state": presented ? "presented" : "prepared",
            "selected_variant_id": payload.variantID,
            "selected_asset_id": payload.assetID,
            "downloaded_asset_bytes": payload.asset.data.count,
            "downloaded_mime_type": payload.asset.mimeType,
            "share_items_count": 2,
            "share_caption": payload.caption,
            "handoff_attempted": true,
            "share_sheet_presented": presented,
            "presenter": payload.presenterName
        ]
        if let data = try? JSONSerialization.data(withJSONObject: receipt, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: receiptURL, options: [.atomic])
        }
    }

    private func writeFailureReceipt(message: String) {
        guard let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
            return
        }
        let receiptURL = documentsURL.appendingPathComponent("agent-pocket-share-sheet-smoke.json")
        let receipt: [String: Any] = [
            "phase": "share-sheet-handoff",
            "ok": false,
            "state": "failed",
            "message": message,
            "handoff_attempted": false,
            "share_sheet_presented": false
        ]
        if let data = try? JSONSerialization.data(withJSONObject: receipt, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: receiptURL, options: [.atomic])
        }
    }
}

private struct SimulatorShareSheetPayload: Identifiable {
    let id: String
    let variantID: String
    let assetID: String
    let asset: DownloadedAsset
    let caption: String
    let fileURL: URL

    var presenterName: String {
        #if canImport(UIKit)
        "UIActivityViewController"
        #else
        "SwiftUI fallback"
        #endif
    }

    static func make() throws -> SimulatorShareSheetPayload {
        let status = SimulatorResultGallerySmokeFixtures.completedStatus
        guard let variant = status.variants?.first else {
            throw URLError(.badServerResponse)
        }
        let caption = status.shareCaption ?? ""
        let asset = SimulatorResultGallerySmokeFixtures.downloadedAsset
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("AgentPocketShareSheetSmoke", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let fileURL = directory.appendingPathComponent("\(variant.id).png")
        try asset.data.write(to: fileURL, options: .atomic)
        return SimulatorShareSheetPayload(
            id: variant.id,
            variantID: variant.id,
            assetID: variant.assetID,
            asset: asset,
            caption: caption,
            fileURL: fileURL
        )
    }
}

#if canImport(UIKit)
private struct SimulatorShareSheetPresenter: UIViewControllerRepresentable {
    let payload: SimulatorShareSheetPayload
    let onPresented: () -> Void

    func makeUIViewController(context: Context) -> UIActivityViewController {
        let controller = UIActivityViewController(
            activityItems: [payload.fileURL, payload.caption],
            applicationActivities: nil
        )
        DispatchQueue.main.async {
            onPresented()
        }
        return controller
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
#else
private struct SimulatorShareSheetPresenter: View {
    let payload: SimulatorShareSheetPayload
    let onPresented: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Text("Share Sheet Fallback")
                .font(.headline)
            Text(payload.caption)
                .font(.body)
        }
        .padding()
        .onAppear(perform: onPresented)
    }
}
#endif

private enum SimulatorResultGallerySmokeFixtures {
    static let completedStatus: TaskStatusResponse = {
        let data = """
        {"task_id":"task_simulator_result","status":"completed","progress":1.0,"message":"Done.","variants":[{"id":"variant_clean_pro","label":"Master","asset_id":"asset_1","download_url":"/mobile/v1/assets/asset_1/download"},{"id":"variant_social_pop","label":"Social","asset_id":"asset_2","download_url":"/mobile/v1/assets/asset_2/download"}],"explanation":"Balanced exposure and warmer highlights while preserving skin tone.","renderer":"local_parametric","composition":{"selected_aspect_ratio":"4:5","crop":{"x":0.2,"y":0.0,"width":0.6,"height":1.0}},"qa":{"master_difference_score":0.18,"social_difference_score":0.31},"recipe_summary":"Balanced exposure and reframed to 4:5.","share_caption":"Shot polished locally with Kaka."}
        """.data(using: .utf8)!
        return try! JSONDecoder.mobileBridge.decode(TaskStatusResponse.self, from: data)
    }()

    static let downloadedAsset = DownloadedAsset(data: fixturePNG, mimeType: "image/png")
    static let originalAsset = DownloadedAsset(data: originalFixturePNG, mimeType: "image/png")

    static let fixturePNG = Data(base64Encoded: "iVBORw0KGgoAAAANSUhEUgAAABAAAAAUCAIAAAALACogAAAALElEQVR4nGNsuneKmYGReMTCwMTIwEACYhnVwDCqgWH4amAkTQMTSarJ0QAAKukEARzpevsAAAAASUVORK5CYII=")!
    static let originalFixturePNG = Data(base64Encoded: "iVBORw0KGgoAAAANSUhEUgAAABAAAAAUCAIAAAALACogAAAAJUlEQVR4nGM0D8tkZmAkHrEwMDEyMJCAWEY1MIxqYBjVwEgvDQCU4QLWv0lV0wAAAABJRU5ErkJggg==")!
}

private struct SimulatorResultGallerySmokeDownloader: ResultAssetDownloading {
    func download(downloadURL: String, connection: StoredConnection) async throws -> DownloadedAsset {
        SimulatorResultGallerySmokeFixtures.downloadedAsset
    }
}

private enum SimulatorSmokeFixtures {
    static let runtime = ConnectedRuntime(
        displayName: "Agent Pocket Mock Agent",
        runtime: "hermes",
        runtimeVersion: "simulator"
    )

    static let connection: StoredConnection? = {
        guard let endpoint = try? AgentEndpoint(rawURL: "http://127.0.0.1:8766") else {
            return nil
        }
        return StoredConnection(
            endpoint: endpoint,
            displayName: "Agent Pocket Mock Agent",
            runtime: "hermes",
            runtimeVersion: "simulator",
            mobileToken: "dev-mobile-token",
            tokenExpiresAt: nil
        )
    }()
}

private struct SimulatorSmokeView: View {
    let configuration: SimulatorSmokeConfiguration
    @State private var status = "Starting simulator smoke test..."
    @State private var detail = ""
    @State private var didPass = false

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Image(systemName: didPass ? "checkmark.circle.fill" : "gearshape.2.fill")
                .font(.system(size: 56, weight: .semibold))
                .foregroundStyle(didPass ? .green : .blue)

            Text("Simulator Smoke")
                .font(.largeTitle.bold())

            Text(status)
                .font(.headline)

            Text(detail.isEmpty ? configuration.baseURL : detail)
                .font(.callout)
                .foregroundStyle(.secondary)
                .textSelection(.enabled)
        }
        .padding(28)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .task {
            await runSmokeTest()
        }
    }

    private func runSmokeTest() async {
        do {
            update("Checking local agent...", configuration.baseURL)
            let endpoint = try AgentEndpoint(rawURL: configuration.baseURL)
            let connection = StoredConnection(
                endpoint: endpoint,
                displayName: "Simulator Smoke Local Agent",
                runtime: "hermes",
                runtimeVersion: "simulator",
                mobileToken: configuration.token,
                tokenExpiresAt: nil
            )
            let client = MobileBridgeHTTPClient(endpoint: endpoint, token: configuration.token)
            _ = try await client.fetchHealth()
            let capabilities = try await client.fetchCapabilities()
            guard let profile = capabilities.profiles.first(where: { $0.capabilities.contains("photo_edit") }) else {
                throw SimulatorSmokeError.missingPhotoEdit
            }

            update("Preparing simulator image...", "Generating a fixture image inside the iOS app process.")
            let upload = try ImagePreprocessor().prepareForUpload(
                data: Self.fixturePNG,
                sourceMimeType: "image/png",
                originalFileName: "simulator-smoke.png",
                maxUploadMB: 30
            )

            update("Uploading image...", upload.fileName)
            let uploaded = try await client.uploadAsset(upload)

            update("Starting local agent photo edit...", uploaded.assetID)
            let created = try await client.startPhotoEditTask(
                PhotoEditTaskRequest(
                    profileID: profile.id,
                    assetID: uploaded.assetID,
                    intent: .naturalEnhance,
                    returnVariants: 1
                )
            )

            update("Waiting for result...", created.taskID)
            let terminalStatus = try await pollUntilTerminal(client: client, taskID: created.taskID)
            guard terminalStatus.status == "completed",
                  let downloadURL = terminalStatus.variants?.first?.downloadURL else {
                throw SimulatorSmokeError.taskDidNotComplete
            }

            update("Downloading edited result...", downloadURL)
            let downloaded = try await MobileBridgeResultAssetDownloader().download(
                downloadURL: downloadURL,
                connection: connection
            )
            guard downloaded.data.isEmpty == false else {
                throw SimulatorSmokeError.emptyDownload
            }

            await MainActor.run {
                didPass = true
                status = "Simulator photo flow passed."
                detail = "Downloaded \(downloaded.data.count) bytes with MIME type \(downloaded.mimeType)."
            }
        } catch {
            await MainActor.run {
                didPass = false
                status = "Simulator photo flow failed."
                detail = String(describing: error)
            }
        }
    }

    @MainActor
    private func update(_ status: String, _ detail: String) {
        didPass = false
        self.status = status
        self.detail = detail
    }

    private nonisolated func pollUntilTerminal(client: MobileBridgeHTTPClient, taskID: String) async throws -> TaskStatusResponse {
        while true {
            let status = try await client.fetchTaskStatus(taskID: taskID)
            if status.isTerminal {
                return status
            }
            try await Task.sleep(nanoseconds: 250_000_000)
        }
    }

    private static let fixturePNG = Data(base64Encoded: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")!
}

private enum SimulatorSmokeError: Error {
    case missingPhotoEdit
    case taskDidNotComplete
    case emptyDownload
}
#endif
