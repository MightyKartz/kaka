# Pocket Agent 开发进度日志

倒序追加。每条 ≤10 行:日期、轨道/里程碑、做了什么、验证方式、遗留问题。章程见 `docs/KAKA-DEVELOPMENT-CHARTER-2026-06-13.md`。

---

## 2026-06-14 · Local Agent Lens · Inbox action feedback empty failure copy

- 修复 Inbox action feedback 失败横幅空白文案:空/仅空白错误会回落到本地化 review/retry 文案。
- 保留非空失败消息、失败图标和可 dismiss 行为,不改提交、队列、Recall、runtime 或 `/mobile/v1` 合约。
- 新增 TDD 覆盖 `testBlankFailureMessageFallsBackToLocalizedReviewCopy`;红测确认旧横幅直接显示空白字符串。
- QA receipt:`docs/qa-receipts/inbox-action-feedback-empty-failure-copy-20260614/`,含红绿 focused Swift、完整 Swift 与 `git diff --check` 结果。
- 验证:`swift test --filter InboxActionFeedbackPresentationTests` 5 passed; `swift test` 464 passed; `git diff --check`。
- 遗留:本轮为 presentation-copy 防御切片,未跑模拟器截图、真机硬件路径或 runtime/mock bridge pytest。

---

## 2026-06-14 · Local Agent Lens · Inbox result source app copy

- 优化 Inbox 提交完成结果横幅来源展示:保留有用 source app provenance,如 `Paste from Safari`、`系统分享来自 Photos`。
- 结果横幅继续避免 Files 导入重复显示 `Files from Files`,保持 Local Agent Lens 来源名和 Context Snapshot 文案不变。
- 新增 TDD 覆盖 `testSourceAppProvenanceShowsWhenItAddsContext`;红测确认旧横幅只显示 `Source: Paste`。
- QA receipt:`docs/qa-receipts/inbox-result-source-app-copy-20260614/`,含 focused/full Swift 测试与 `git diff --check` 日志。
- 验证:`swift test --filter InboxResultPresentationTests` 3 passed; `swift test` 463 passed; `git diff --check`。
- 遗留:本轮为 presentation-copy 单测切片,未跑模拟器截图、真机硬件路径或 runtime/mock bridge pytest。

---

## 2026-06-14 · Local Agent Lens · Inbox result source guard fix

- 修复 PR #19 验证阻塞:更新 `ios/tests/test_inbox_result_review_provenance_source.py`,不再把 Context Snapshot 结果横幅文案硬绑在 `InboxView.swift`。
- Source guard 现在确认 `InboxView` 使用 `InboxResultPresentation`,Recall 仍传 `sourceInboxItemID`,Context Snapshot 文案归属 presentation 文件。
- QA receipt:`docs/qa-receipts/inbox-result-source-copy-20260614/`,新增 focused source guard、完整 Python 套件与刷新后的 Swift 测试日志。
- 验证:`ios/tests/test_inbox_result_review_provenance_source.py` 1 passed; full pytest 653 passed; `swift test --filter InboxResultPresentationTests` 2 passed; `swift test` 462 passed。
- 遗留:本轮为 CI/source-guard 修复,未跑模拟器截图或真机硬件路径。

---

## 2026-06-14 · Local Agent Lens · Inbox result source copy

- 优化 Inbox 提交完成结果横幅来源展示:Local Agent Lens 的 `agent_scanner`、`document_scanner`、`video_capture` 不再显示 raw source surface。
- 新增 `InboxResultPresentation` 与 focused TDD 覆盖;红测确认旧横幅文案会显示 `Source: agent_scanner` 等内部来源名。
- QA receipt:`docs/qa-receipts/inbox-result-source-copy-20260614/`,含 focused/full Swift 测试与 `git diff --check` 日志。
- 验证:`swift test --filter InboxResultPresentationTests` 2 passed; `swift test` 462 passed; `git diff --check`。
- 遗留:本轮为 presentation-copy 单测切片,未跑模拟器截图、真机硬件路径或 runtime/mock bridge pytest。

---

## 2026-06-14 · Local Agent Lens · Inbox Files source dedupe copy

- 优化 Inbox pending item `Review Details` 来源展示:Files 导入不再显示重复的 `Files from Files`,改为 `Files`。
- 新增 TDD 覆盖现有 `InboxPendingItemReviewPresentationTests`;红测确认旧来源行重复。
- QA receipt:`docs/qa-receipts/inbox-files-source-dedupe-copy-20260614/`,含 focused/full Swift 测试与 `git diff --check` 日志。
- 验证:`swift test --filter InboxPendingItemReviewPresentationTests` 6 passed; `swift test` 460 passed; `git diff --check`。
- 遗留:本轮为 presentation-copy 单测切片,未跑模拟器截图或真机硬件路径。

---

## 2026-06-14 · Local Agent Lens · Context Snapshot courier source copy

- 优化 Context Snapshot 预览的 Source 行:显式 `paste` 显示为 Paste,`file_picker`/`document_picker` 显示为 Files,与 Inbox Review 来源命名对齐。
- 新增 TDD 覆盖 `testPreviewRowsUseInboxFacingCourierSourceNames`;红测确认 Files 来源仍显示内部式来源名。
- QA receipt:`docs/qa-receipts/context-snapshot-courier-source-copy-20260614/`,含 focused/full Swift 测试与 `git diff --check` 日志。
- 验证:`swift test --filter ContextSnapshotViewModelTests` 16 passed; `swift test` 460 passed; `git diff --check`。
- 遗留:本轮为 presentation-copy 单测切片,未跑模拟器截图或真机硬件路径。

---

## 2026-06-14 · Local Agent Lens · Context Snapshot source preview copy

- 优化 Context Snapshot 预览的 Source 行:Local Agent Lens 的 `agent_scanner`、`document_scanner`、`video_capture` 显示为 Scanner、Document Scan、Video。
- 新增 TDD 覆盖 `testPreviewRowsUseUserFacingLocalAgentLensSources`;清理 SwiftPM `.build` 后红测确认旧预览未包含用户可读来源名。
- QA receipt:`docs/qa-receipts/context-snapshot-lens-source-copy-20260614/`,含 focused/full Swift 测试与 `git diff --check` 日志。
- 验证:`swift test --filter ContextSnapshotViewModelTests` 15 passed; `swift test` 459 passed; `git diff --check`。
- 遗留:本轮为 presentation-copy 单测切片,未跑模拟器截图或真机硬件路径。

---

## 2026-06-14 · Local Agent Lens · Inbox source review copy

- 优化 Inbox pending item `Review Details` 来源展示:Local Agent Lens 的 `agent_scanner`、`document_scanner`、`video_capture` 不再显示 raw source surface。
- 新增 TDD 覆盖英文/中文来源名:Scanner/扫描、Document Scan/文档扫描、Video/视频。
- QA receipt:`docs/qa-receipts/lens-source-review-copy-20260614/`,含 focused/full Swift 测试与 `git diff --check` 日志。
- 验证:`swift test --filter InboxPendingItemReviewPresentationTests` 6 passed; `swift test` 458 passed; `git diff --check`。
- 遗留:本轮为 presentation-copy 单测切片,未跑模拟器截图或真机硬件路径。

---

## 2026-06-14 · Local Agent Lens · Scanner payment URL actions

- 收紧 Agent Scanner 本地动作策略:支付/结账类 HTTPS 链接仍保留 Ask Agent、Copy、Save to Inbox 的可见审阅路径,但不提供 Open 动作。
- 新增 TDD 覆盖 `testPaymentLikeHTTPSURLCanBeReviewedWithoutOpenAction`;红测先确认旧策略会把 HTTPS 支付链接降级成文本动作。
- QA receipt:`docs/qa-receipts/scanner-payment-url-actions-20260614/`,含 focused/full Swift 测试与 `git diff --check` 日志。
- 验证:`swift test --filter AgentScanActionPolicyTests` 7 passed; `swift test` 457 passed; `git diff --check`。
- 遗留:本轮为本地策略切片,未跑真实相机扫码/模拟器 UI;支付链接启发式范围需 Conversation B 重点复核。

---

## 2026-06-14 · UI/UX QA Second Pass · Quiet Lens polish

- 用 XcodeBuildMCP 在 iPhone 17 Pro Max(iOS 26.5)做主流程 QA,用 iPhone 17e(iOS 26.5)做小屏替代复核;iPhone 16 / 16 Plus 未安装,iPhone 16e 在刷新后不可 build/run。
- 一对一修复:Video Intake/Voice 空内容时禁用主按钮改为中性 inactive 状态,避免看起来像可点击 mint CTA;Activity 默认 `Runtime task` 在中文 UI 中显示为 `运行时任务`。
- 新增 `TaskInboxPresentation` 与 focused tests,保留 runtime/user 提供的具体英文标题不被误翻译;QA receipt:`docs/qa-receipts/pocket-agent-ui-ux-qa-second-pass-20260614/`。
- 验证:`swift test` 456 passed; `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime-kit:mock_bridge python3 -m pytest -p no:cacheprovider runtime-kit/tests mock_bridge/tests photo-pack/tests ios/tests -q` 653 passed; `git diff --check`; XcodeBuildMCP `build_run_sim -skipMacroValidation` succeeded on iPhone 17 Pro Max。
- 遗留:Simulator 仍不能验证真实扫码、VisionKit 文档扫描、麦克风录音、相机视频录制和 Dynamic Island 真机表现;需 iPhone 16 Plus 真机补硬件路径 QA。

---

## 2026-06-14 · UI/UX QA · Local Agent Lens polish

- 用 XcodeBuildMCP 在 iPhone 17 Pro Max(iOS 26.5)和 iPhone 16e(iOS 26.1)做 Local Agent Lens / Quiet Lens 系统化 Simulator QA;iPhone 16 / 16 Plus 模拟器未安装。
- 一对一修复:Hub 首屏 tab bar 遮挡、Voice 暗色导航标题、Scanner Simulator/中文状态、Video Intake 暗色禁用控件对比度、相机权限中文 Pocket Agent 文案。
- 新增测试覆盖 Scanner copy、Voice dark navigation chrome、dark control contrast、Capture initial layout policy;QA receipt:`docs/qa-receipts/pocket-agent-ui-ux-qa-20260614/`。
- 验证:`swift test` 453 passed; `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime-kit:mock_bridge python3 -m pytest -p no:cacheprovider runtime-kit/tests mock_bridge/tests photo-pack/tests ios/tests -q` 653 passed; `git diff --check`; XcodeBuildMCP `build_run_sim` succeeded on iPhone 17 Pro Max。
- 遗留:Simulator 不能验证真实扫码、VisionKit 文档扫描、麦克风录音、相机录制视频和 Dynamic Island 真机表现;iPhone 16e 首次手动保存凭证曾失败一次、重试成功,需真机回归关注。

---

## 2026-06-14 · Product Rename · Pocket Agent

- 项目用户可见名称正式改为 **Pocket Agent**;同步 README/中文 README 链接、PRODUCT、AGENTS、开发章程、Mobile Bridge API、setup/privacy、Runtime Kit/host package 文案、mock bridge QA 文案和 iOS display/permission strings。
- 保留兼容标识:`AgentPocket` 模块/target、`KakaInboxItem`、`KakaShareExtension` 路径、`group.dev.kartz.Kaka`、`kaka_mobile_runtime_kit`、旧 host adapter 路径和 legacy pairing error 输入。
- GitHub About 已更新为:`Pocket Agent: local-first iPhone front end for user-owned agent runtimes / 本地优先的 iPhone 本地智能体入口`;仓库 slug 未改。
- 验证:`swift test` 447 passed; `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime-kit:mock_bridge python3 -m pytest -p no:cacheprovider runtime-kit/tests mock_bridge/tests photo-pack/tests ios/tests -q` 653 passed; `git diff --check`; XcodeBuildMCP `build_sim -skipMacroValidation` succeeded on iPhone 17 / iOS 26.5。
- 遗留:若后续要改 repo slug、bundle id、App Group、target/path/type names,需要单独迁移计划和兼容策略。

---

## 2026-06-13 · QA · Simulator UI/UX sweep

- 用 XcodeBuildMCP 在 iPhone 16e fresh install 和 iPhone 17 connected runtime 两个模拟器上跑系统化 UI/UX QA。
- 覆盖:first pairing、connected Lens Hub、Scanner、Document Scan、Video Intake、Voice、Inbox、Recall、Activity、connected runtime sheet。
- QA receipt:`docs/qa-receipts/simulator-ui-ux-20260613-185716/`,含 10 张截图、构建日志和设计 review findings。
- 主要发现:Hub 底部 tile 被 tab bar 轻微遮挡、Scanner 缺少明显关闭、Voice/Video/Activity 有中文环境英文残留、连接 sheet 文案仍偏照片场景。
- 验证:XcodeBuildMCP `build_run_sim` 在 iPhone 16e/iPhone 17 均成功;本轮未改代码。
- 遗留:真机 iPhone 16 Plus 仍需补 Scanner、Document Scan、Video、Share Extension、Action Button、Dynamic Island 硬件/系统能力 QA。

## 2026-06-13 · Simulator UI/UX QA · 一对一修复闭环

- 基于 `docs/qa-receipts/simulator-ui-ux-20260613-185716/` 的 8 条问题逐项修复:Hub 底部遮挡、Scanner 关闭入口、Voice/Video 中文文案、Activity `Completed.`、Recall 浅色空状态、连接页照片专用文案和隐私提示弱化。
- Hub 紧凑高度布局改为更短预览、更密 Lens tiles,并在 Hub 与拍照控制区之间加空白缓冲,避免 iPhone 17 浮动 Tab bar 遮挡入口或透出下一区文字。
- Scanner sheet 增加明确 Close;Video Intake/Voice sheet 增加中文 presentation;Activity 卡片本地化常见状态消息;连接页改为 “接收手机动作 / 打开 Lens / 输入与密钥边界”。
- QA 证据:`docs/qa-receipts/simulator-ui-ux-fixes-20260613-192854/`,含一对一修复表和 7 张 iPhone 17 Simulator 截图。
- 验证:`swift test --filter ConnectScreenCopyTests`; `swift test --filter ConnectionStateTests`; `swift test --filter VoiceCapturePresentationTests`; `swift test --filter LocalAgentLensPresentationTests`; `swift test` 447 passed; `git diff --check`; XcodeBuildMCP `build_run_sim -skipMacroValidation` succeeded。
- 遗留:Simulator 无法验证真实摄像头扫码、VisionKit 文档扫描、麦克风录音和相机录制视频;仍需 iPhone 16 Plus 真机补硬件路径 QA。

## 2026-06-13 · Docs · GitHub 介绍与英文 README 更新

- 更新 GitHub 仓库 About 描述为中英双语短介绍:`Local-first iPhone front end for user-owned agent runtimes / 本地优先的 iPhone 智能体入口`。
- 更新 `README.md`,把当前主线改为 Local Agent Lens,覆盖 Scan、Document、Video、Record、Inbox、Activity、App Intents、Live Activity/Dynamic Island 等现状。
- README 英文版顶部仅保留中文版链接 `[简体中文](README.zh-CN.md)`,中文版 README 继续反向链接英文版。
- 验证:`git diff --check`; `gh repo view MightyKartz/kaka --json description`。
- 遗留:本次仅更新公开介绍/README 文档,未改代码。

## 2026-06-13 · M1 Local Agent Lens · Quiet Lens UI/UX 落地

- 按 `docs/superpowers/plans/2026-06-13-kaka-local-agent-lens.md` 实现 Local Agent Lens Hub、Scanner 动作策略、Document Scan 到 Inbox、Video Intake、Inbox/Activity 浅色审核面和前台 App Intent/Action Button handoff。
- Mobile Bridge/Core 增加 `video` 通用 intake 与 Lens source surfaces; mock bridge 同步支持 video asset intake。
- Live Activity / Dynamic Island 投影增加 phone-safe `progress` 和短 `message`,WidgetKit 仅渲染安全字段。
- QA 证据:`docs/qa-receipts/local-agent-lens-20260613/`,含 iPhone 17 已配对模拟器 Hub/Scanner/Video/Document/Inbox/Activity 截图、iPhone 16e fresh-install smoke 和 XcodeBuildMCP 日志。
- 验证:`swift test` 447 passed; `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime-kit:mock_bridge python3 -m pytest -p no:cacheprovider runtime-kit/tests mock_bridge/tests photo-pack/tests ios/tests -q` 653 passed; XcodeBuildMCP `build_run_sim` succeeded。
- 遗留:模拟器无法真实捕获摄像头/文档;需在 iPhone 16 Plus 真机上补真实 Scanner/Document/Video intake QA。

## 2026-06-13 · M0 Governance · Agent 入口文档

- 新增根目录 `AGENTS.md`,作为 Codex/Claude/多 agent 进入 Kaka 仓库的第一入口。
- 文档指向开发章程、进度日志、Mobile Bridge API、产品方向,并摘要当前 Local Agent Lens 主线。
- 固化硬确认线、默认允许动作、开发纪律、验证命令和重要路径,避免后续 agent 先读到旧 P 阶段文档后跑偏。
- 验证:文档为纯 Markdown,无需运行代码测试。
- 遗留:后续章程或主线变化时同步更新 `AGENTS.md`。

---

## 2026-06-13 · M0 Governance · 开发章程与进度入口

- 参考 Flow 的 Delivery Charter / PROGRESS 结构,为 Kaka 建立当前开发章程与单一进度入口。
- 章程把近期主线收敛为本地 Wi-Fi/LAN 的 Local Agent Lens,暂缓云端 relay、公网远程、服务器 Hermes 和 RoomPlan。
- 明确硬确认线:真实花钱/云端部署/破坏性数据操作/Host Extension 真实分发/模型路由变更/真机敏感操作。
- 明确默认允许:本地可撤销、不花钱的代码、测试、文档、mock/runtime-kit smoke 和用户授权下的 dev app 真机安装。
- 验证:人工对照 `README.zh-CN.md`、`PRODUCT.md`、`docs/development-history.md`、Host Extension 文档和 Flow 参考文档。
- 遗留:后续每个实现切片完成后必须倒序追加本文件。

---

## 2026-06-13 · Product Direction · Local Agent Lens 方向收敛

- 产品问题重新定义为:用户装好 Hermes/OpenClaw 后不知道能做什么,Kaka 应先提供手机原生动作入口。
- 当前主线:扫码后的下一步动作、文档扫描到 Inbox、录音转写/总结、短视频理解、Action Button/Shortcuts 前台入口、Live Activity/Dynamic Island 状态层。
- 计划文档:`docs/superpowers/plans/2026-06-13-kaka-local-agent-lens.md`。
- 边界:不做云端、不做公网远程、不引入默认 VPN/额外第三方软件、不做 RoomPlan 首期。
- 验证:基于 Apple 官方 WWDC26/App Intents/VisionKit/ActivityKit 文档调研和现有 Kaka 代码结构检查。
- 遗留:该计划位于 `docs/superpowers/`,当前被 `.gitignore` 忽略;需要提交时需另行决定是否 force-add 或迁移到非忽略路径。

---

## 2026-06-13 · M1 Connection QA · 本地 Hermes LAN 连接结论

- 真机 iPhone 16 Plus 与本地 Hermes/Mobile Bridge 已按 LAN/Bonjour 路径验证过连接与运行。
- 曾出现“本机运行时离线 / 重连失败”,根因是 iPhone 未连接同一 Wi-Fi;USB 连接不代表 app 能访问 Mac LAN endpoint。
- 产品结论:当前默认只承诺同一 Wi-Fi/LAN 的本地连接;户外/异地远程访问暂缓,不作为首期主线。
- 已实施的方向:已保存配对但运行时离线时,UI 应提示启动 Mac 上的 Hermes/OpenClaw/runtime-kit,并提供重新扫码/同网恢复路径。
- 验证:本地 `/mobile/v1/health`、Bonjour、真机手动测试和用户反馈。
- 遗留:后续 M1 仍需持续记录真机 QA receipt,尤其是 Wi-Fi off、IP 变化、Bonjour 修复、重扫二维码路径。

---

## 2026-06-13 · Host Extension · 外部材料仍阻塞

- Runtime Kit 已有 Hermes/OpenClaw Host Extension 合约、readiness、starter-kit、install-package、blueprint 等 repo-owned 材料。
- 普通用户目标路径仍是 host-native Hermes Plugin / OpenClaw Skill,不是 Codex plugin/skill 或手写 runtime-kit 命令。
- P3.7 external install drill 仍依赖真实 host-owned package materials:package ref、host UI entrypoint、signed package、adapter command、drill receipts、conformance/evidence refs。
- 当前结论:材料缺失时不再追加 repository-only installer wrapper;改做独立产品切片,即 Local Agent Lens。
- 验证:对照 `docs/kaka-host-extension-external-materials.md`、`docs/kaka-host-extension-install-experience-spec.md`、`docs/development-history.md`。
- 遗留:一旦 Hermes/OpenClaw 提供真实材料,先跑 `host-extension-material-intake`,再跑 `host-extension-readiness`,通过后才写/执行 P3.7。

---

## 2026-06-12 · UI/UX · 当前视觉系统完成首轮统一

- 已基于 product-design、design-taste-frontend、app-ui-implementer、ui-ux-pro-max 等分析完成首轮 SwiftUI 视觉统一。
- 新增/调整连接、Capture、Inbox、Recall、Activity、结果页等界面风格,并生成多轮真机截图 receipt。
- 相关证据在 `docs/qa-receipts/product-design-audit-20260612/`、`docs/qa-receipts/ui-ux-implementation-20260612/`、`docs/qa-receipts/ui-ux-pro-max-20260612/`。
- 产品结论:UI/UX 不应停留在“连接工具”,下一轮应围绕“拍、扫、录、传、看进度”的 Local Agent Lens 体验继续统一。
- 验证:真机/截图 QA、Swift 测试、用户手动运行反馈。
- 遗留:Local Agent Lens 新入口落地后需要再做一次 9:16 多界面图与真机视觉 QA。
