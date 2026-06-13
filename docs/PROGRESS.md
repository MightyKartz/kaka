# Kaka 开发进度日志

倒序追加。每条 ≤10 行:日期、轨道/里程碑、做了什么、验证方式、遗留问题。章程见 `docs/KAKA-DEVELOPMENT-CHARTER-2026-06-13.md`。

---

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
