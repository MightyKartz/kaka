import Foundation
import XCTest
@testable import AgentPocketCore

final class MobileBridgeHTTPIntegrationTests: XCTestCase {
    private var serverProcess: Process?
    private var nextPort = 18_976

    override func tearDown() {
        if let serverProcess, serverProcess.isRunning {
            serverProcess.terminate()
            serverProcess.waitUntilExit()
        }
        serverProcess = nil
        super.tearDown()
    }

    func testURLSessionClientCompletesPhotoEditLifecycleAgainstLocalMockBridge() async throws {
        let port = nextAvailablePort()
        try startMockBridge(port: port)
        try await waitForHealth(port: port)

        let client = MobileBridgeHTTPClient(
            endpoint: try AgentEndpoint(rawURL: "http://127.0.0.1:\(port)"),
            token: "dev-mobile-token",
            session: URLSession(configuration: .ephemeral)
        )
        let upload = try ImageUploadPolicy(maxUploadMB: 30).prepare(
            data: Data("source-image".utf8),
            mimeType: "image/jpeg",
            fileName: "photo.jpg",
            width: 100,
            height: 100,
            localCreationTime: nil
        )

        let uploaded = try await client.uploadAsset(upload)
        let created = try await client.startPhotoEditTask(
            PhotoEditTaskRequest(
                profileID: "photo-agent",
                assetID: uploaded.assetID,
                intent: .naturalEnhance,
                instruction: "Keep it realistic.",
                returnVariants: 1
            )
        )
        let status = try await client.fetchTaskStatus(taskID: created.taskID)
        let variant = try XCTUnwrap(status.variants?.first)
        let downloaded = try await client.downloadAsset(downloadURL: variant.downloadURL)

        XCTAssertEqual(created.status, "queued")
        XCTAssertEqual(status.status, "completed")
        XCTAssertEqual(downloaded.mimeType, "image/png")
        XCTAssertTrue(downloaded.data.starts(with: [0x89, 0x50, 0x4E, 0x47]))
    }

    func testURLSessionClientCompletesVisionLifecycleAgainstLocalMockBridge() async throws {
        let port = nextAvailablePort()
        try startMockBridge(port: port)
        try await waitForHealth(port: port)

        let client = MobileBridgeHTTPClient(
            endpoint: try AgentEndpoint(rawURL: "http://127.0.0.1:\(port)"),
            token: "dev-mobile-token",
            session: URLSession(configuration: .ephemeral)
        )
        let upload = try ImageUploadPolicy(maxUploadMB: 30).prepare(
            data: Data("source-image".utf8),
            mimeType: "image/jpeg",
            fileName: "photo.jpg",
            width: 100,
            height: 100,
            localCreationTime: nil
        )

        let uploaded = try await client.uploadAsset(upload)
        let created = try await client.startVisionTask(
            VisionTaskRequest(
                profileID: "photo-agent",
                assetID: uploaded.assetID,
                mode: .identify,
                instruction: "Identify the visible object.",
                locale: "zh-Hans"
            )
        )
        let status = try await client.fetchTaskStatus(taskID: created.taskID)

        XCTAssertEqual(created.status, "queued")
        XCTAssertEqual(status.status, "completed")
        XCTAssertEqual(status.resultType, "vision")
        XCTAssertEqual(status.vision?.mode, "identify")
        XCTAssertEqual(status.vision?.title, "识别结果")
        XCTAssertEqual(status.vision?.items.first?.title, "主要物体")
    }

    func testURLSessionClientExchangesPairingCodeThenFetchesCapabilities() async throws {
        let port = nextAvailablePort()
        try startMockBridge(port: port)
        try await waitForHealth(port: port)

        let client = MobileBridgeHTTPClient(
            endpoint: try AgentEndpoint(rawURL: "http://127.0.0.1:\(port)"),
            token: "",
            session: URLSession(configuration: .ephemeral)
        )

        let exchange = try await client.exchangePairingCode(
            pairingCode: "pair_dev",
            deviceName: "Simulator",
            devicePublicID: "device_simulator"
        )
        let pairedClient = MobileBridgeHTTPClient(
            endpoint: try AgentEndpoint(rawURL: "http://127.0.0.1:\(port)"),
            token: exchange.mobileToken,
            session: URLSession(configuration: .ephemeral)
        )
        let capabilities = try await pairedClient.fetchCapabilities()

        XCTAssertEqual(exchange.mobileToken, "dev-mobile-token")
        XCTAssertEqual(capabilities.tasks.photoEdit.returnVariantsMax, 3)
    }

    private func startMockBridge(port: Int) throws {
        let root = packageRoot()
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = [
            "-m",
            "agent_pocket_mock_bridge.server",
            "--host",
            "127.0.0.1",
            "--port",
            String(port),
        ]
        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONPATH"] = [
            root.appendingPathComponent("runtime-kit").path,
            root.appendingPathComponent("mock_bridge").path,
        ].joined(separator: ":")
        process.environment = environment
        process.standardOutput = Pipe()
        process.standardError = Pipe()
        try process.run()
        serverProcess = process
    }

    private func nextAvailablePort() -> Int {
        nextPort += 1
        return nextPort
    }

    private func waitForHealth(port: Int) async throws {
        let deadline = Date().addingTimeInterval(5)
        let url = URL(string: "http://127.0.0.1:\(port)/mobile/v1/health")!
        var lastError: Error?

        while Date() < deadline {
            do {
                let (data, response) = try await URLSession.shared.data(from: url)
                if (response as? HTTPURLResponse)?.statusCode == 200,
                   String(data: data, encoding: .utf8)?.contains("\"runtime\": \"hermes\"") == true {
                    return
                }
            } catch {
                lastError = error
            }
            try await Task.sleep(nanoseconds: 100_000_000)
        }

        throw lastError ?? URLError(.cannotConnectToHost)
    }

    private func packageRoot() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }
}
