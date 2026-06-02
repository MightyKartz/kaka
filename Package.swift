// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "AgentPocket",
    platforms: [
        .iOS(.v17),
        .macOS(.v14)
    ],
    products: [
        .library(name: "AgentPocketCore", targets: ["AgentPocketCore"]),
        .library(name: "AgentPocketUI", targets: ["AgentPocketUI"]),
        .executable(name: "AgentPocketApp", targets: ["AgentPocketApp"])
    ],
    targets: [
        .target(name: "AgentPocketCore"),
        .target(
            name: "AgentPocketUI",
            dependencies: ["AgentPocketCore"]
        ),
        .executableTarget(
            name: "AgentPocketApp",
            dependencies: ["AgentPocketUI"],
            path: "ios/AgentPocket",
            exclude: ["Info.plist"]
        ),
        .testTarget(
            name: "AgentPocketCoreTests",
            dependencies: ["AgentPocketCore"]
        ),
        .testTarget(
            name: "AgentPocketUITests",
            dependencies: ["AgentPocketUI"]
        )
    ]
)
