# Kaka 开发章程(Delivery Charter)

日期: 2026-06-13
负责人: Kartz / Codex
状态: 中文当前版。本章程是后续所有开发线程(人工、Codex、多 agent goal 续跑、真机 QA)的第一入口。
范围: 确认产品边界、开发纪律、交付里程碑、协作轨道、验证方式,以及与既有 P 阶段文档和 Host Extension 材料的关系。

---

## 0. 这份章程解决什么问题

Kaka 已经从单一拍照/修图原型演进成 iPhone 本地智能体入口:连接 Hermes、OpenClaw 或兼容 Mobile Bridge 的本机运行时,由手机负责采集、预览、语音、收件箱、确认和状态展示,由运行时负责模型、工具、记忆、任务和保留策略。

当前风险不是功能不够多,而是方向容易分散:

- 一条线想做远程访问、云端 relay、服务器 Hermes。
- 一条线想做 Hermes/OpenClaw 插件、Skill、Host Extension 安装。
- 一条线想做手机原生能力:扫码、文档扫描、短视频理解、录音总结、Action Button、Live Activity、Dynamic Island。
- 既有 `docs/` 和 `docs/superpowers/plans/` 已有大量阶段计划,后续继续新增零散计划会让开发入口变模糊。

本章程把 Kaka 的近期开发重新定义为:

> Kaka 先做本地局域网内的手机感知入口(Local Agent Lens),解决用户装好 Hermes/OpenClaw 后不知道能做什么的问题;云端和公网远程访问暂不作为当前阶段目标。

自本章程生效起:

- `docs/PROGRESS.md` 是后续进度、决策、QA 结果的默认追加入口。
- 旧的 P 阶段计划、UI 审计、Host Extension 文档保留为历史上下文和合约材料,不再作为“下一步自动授权来源”。
- `继续开发` / `按计划推进` / goal continuation 的默认语义是:按本章程当前里程碑推进下一个未完成、可验证的产品切片。

## 1. 产品不变量

1. **本地优先**:默认路径是 iPhone 与 Mac/本机运行时在同一可信 Wi-Fi/LAN 内连接,通过 QR、Bonjour、Mobile Bridge `/mobile/v1` 通信。
2. **手机是感知与确认面**:iPhone 负责相机、文档扫描、扫码、视频、麦克风、分享、粘贴、Files、Context Snapshot、Inbox、Recall 控制、任务进度和用户确认。
3. **运行时是思考与执行面**:Hermes/OpenClaw/sidecar 负责 provider key、模型路由、工具执行、任务状态、Recall、持久化和保留策略。
4. **先可见,再提交**:Share、Paste、Files、Voice、Scanner、Document、Video 进入运行时前必须有可见草稿、预览或确认。不得静默上传。
5. **Recall 显式**:记住、用一次、遗忘必须由用户看见并触发。不得自动写入长期记忆。
6. **安装路径 host-native**:普通用户未来应安装 Hermes Plugin 或 OpenClaw Skill/sidecar,在宿主 UI 中启用 Kaka Mobile Bridge,再扫码或 Bonjour 配对。Codex skill/plugin 只能是 host-team 开发自动化,不是普通用户安装面。
7. **Dynamic Island 使用公开 ActivityKit**:Kaka 可以做 Live Activities / Dynamic Island compact、minimal、expanded 状态,但不能声称复制或依赖 Apple 私有 Siri UI。

## 2. 当前非目标

以下方向需要另行重新开章程或明确用户批准,不作为当前阶段自动推进内容:

- 云端 relay、公网远程访问、服务器版 Hermes/OpenClaw、Tailscale/VPN 作为默认用户路径。
- RoomPlan/ARKit 空间扫描首期实现。
- 后台持续录音、被动截图、后台剪贴板轮询、后台位置/运动/日历采集。
- 自动打开未知/支付类二维码链接。
- 手机端保存 provider API key、模型 routing、private host API、运行时 secrets。
- 另做一个公开 Codex 插件/Skill 安装路径来替代 Hermes/OpenClaw host-native package。

## 3. 硬确认线(必须等待用户人工确认)

1. **真实花钱或真实 provider 调用**:任何会产生 provider 费用、云服务费用、短信/推送计费、GPU/ECS/OSS/模型 API 成本的动作。
2. **云端/公网/生产部署**:阿里云、Cloudflare、VPS、公网域名、production deploy、App Store/TestFlight 发布、推送到远程生产服务。
3. **破坏性数据操作**:删除用户设备上的 app、删除运行时 store、清理 Recall、删除非本任务创建的文件、迁移或重写数据库/SQLite 结构。
4. **Host Extension 真实分发**:安装、签名、发布、更新、卸载 Hermes Plugin / OpenClaw Skill/sidecar,或执行真实 host-private adapter command。
5. **模型/供应商路由变更**:改变默认模型、provider mapping、fallback chain、API key 来源、Hermes/OpenClaw profile 持久配置。
6. **真机敏感操作**:删除真机上已有 app、覆盖非 dev bundle、访问隐私权限以外的设备数据。重新安装当前 dev app 可在用户明确连接真机并要求测试时执行。

## 4. 默认允许(不需要额外确认)

满足“本地、可撤销、不花钱、不触发真实外部副作用”的动作默认允许:

- 在当前 feature 分支写代码、写测试、重构、修 bug。
- 更新 README、API 文档、隐私文档、章程、进度日志、QA receipt。
- 运行 `swift test`、pytest、plist lint、Xcode 本地 build、模拟器测试。
- 启动本地 mock bridge / runtime-kit / Hermes LAN bridge 做本机验证,只要不改写用户 profile secrets。
- 在用户已连接并要求真机测试时安装/启动当前 Kaka dev app。
- 创建小粒度计划文档,但需要在 `docs/PROGRESS.md` 登记目的和结果;长期方向优先写入本章程或进度日志。

## 5. 产出纪律

1. **进度统一倒序追加**:`docs/PROGRESS.md` 记录后续产品决策、实施切片、验证命令、遗留问题。每条控制在 10 行以内。
2. **计划必须可执行**:计划文档要写清文件、测试、命令、验收。纯愿景文档不能作为完成定义。
3. **每个切片必须改变真实用户路径**:避免只新增 readiness / projection / evidence 层而不改变用户能做什么。Host Extension 材料除外,但必须对应真实 host-owned package 输入。
4. **边界测试是资产**:连接、Recall、Inbox、App Intent、Live Activity、Runtime Kit secret-safety、Host Extension no-side-effect 测试不得为赶进度随意删除。
5. **UI/UX 必须真机看过**:涉及手机界面、相机、扫描、语音、Dynamic Island、Share Extension、Action Button 的改动,完成前必须安排模拟器或真机截图/QA receipt。
6. **不要让普通用户写命令**:面向普通用户的路径不能要求粘贴 `runtime-kit` 长命令、导出环境变量、写 adapter 代码或安装 Codex skill/plugin。

## 6. 当前交付里程碑

### M0:章程与进度入口统一(当前)

目标:让后续开发线程有一个稳定入口,避免继续在分散计划文档里迷路。

范围:

1. 新增本章程。
2. 新增 `docs/PROGRESS.md`。
3. 在进度日志记录当前 Local Agent Lens 决策、真机/连接 QA 背景、Host Extension 阻塞状态。

验收:

- `docs/KAKA-DEVELOPMENT-CHARTER-2026-06-13.md` 存在。
- `docs/PROGRESS.md` 存在并有当前倒序记录。
- 后续任务可引用本章程作为第一入口。

### M1:本地连接与首扫体验稳固

目标:用户安装 Kaka 和本机 Hermes/OpenClaw 后,知道如何连接、断线后知道如何恢复,同一 Wi-Fi/LAN 下能稳定配对和重新连接。

范围:

1. QR / Bonjour / saved connection / saved offline 状态继续硬化。
2. 首次配对与已保存连接离线的文案统一成“启动 Mac 上的本机运行时 / 同一 Wi-Fi / 重新扫码”。
3. Runtime Kit 启动、LAN host、Bonjour、Hermes profile env 映射保持可测试。
4. 真机 iPhone 16 Plus 继续作为主 QA 设备。

验收:

- `swift test` 通过。
- Runtime Kit pytest 通过。
- `runtime-kit start --provider hermes --lan --bonjour --runtime-store-path ...` 可被 iPhone 扫码或发现。
- `docs/qa-receipts/` 有真机连接 receipt。

### M2:Local Agent Lens P0

目标:解决“装好智能体不知道干什么”的第一公里。Kaka 打开后直接给用户手机动作,而不是空聊天框。

范围:

1. Agent Scanner:扫码/文字扫描后展示下一步动作,包括 URL 总结、打开、复制、保存到 Inbox、Kaka pairing QR 连接。
2. Agent Document Scan:VisionKit 文档扫描生成 PDF Inbox 草稿,用户可见后再发送给本地运行时。
3. Agent Recorder:继续强化录音转写、总结、行动项、Inbox 草稿。
4. Action Button / Shortcuts:前台 handoff 到 Scan、Document、Video、Record、Inbox、Tasks。
5. Local Agent Lens Hub:Capture 页或根入口展示“拍、扫、录、传、看进度”。

验收:

- Scanner 不自动打开未知链接或支付链接。
- Document scan 不静默上传,只创建可见 Inbox 草稿。
- Action Button/Shortcuts 不后台提交、不写 Recall、不改运行时设置。
- 真机 QA 覆盖 Scan、Document、Record、Inbox Send。

### M3:短视频理解与状态层

目标:让 Kaka 能处理短视频任务,并用 Live Activities / Dynamic Island 展示本地智能体状态。

范围:

1. `UniversalIntakeKind.video` 和 mock bridge/runtime-kit 通用 intake 支持短视频资产。
2. 视频首期限制短文件,进入可见 Inbox 草稿后再上传。
3. Runtime task Live Activity 增加 phone-safe progress/message。
4. Dynamic Island compact/minimal/expanded 显示“扫描中 / 分析中 / 等待确认 / 已完成 / 离线”等状态。

验收:

- 视频 intake 测试覆盖 capability、asset upload、task status。
- Dynamic Island 不泄漏 provider endpoint、token、文件路径、隐藏 prompt、raw logs。
- 真机 QA 记录 compact 和 expanded 状态。

### M4:Host Extension 外部材料恢复

目标:当 Hermes/OpenClaw 提供真实 host-owned package materials 后,恢复 P3.7 外部安装演练。

触发条件:

- host package ref
- host UI entry point
- disabled-by-default evidence
- extension-internal adapter command location
- install/update/uninstall/pairing drill receipts
- P3.2 conformance ref
- P3.4 evidence manifest ref
- release notes

执行顺序:

1. 用 `host-extension-material-intake` 审查材料。
2. 重新跑 `host-extension-readiness`。
3. 只有 readiness 通过后才写/执行 P3.7 external install drill。

禁止:

- 在材料缺失时继续添加 repository-only installer wrapper。
- 把 Codex plugin/skill 变成普通用户安装路径。

### M5:云端/远程连接(暂缓)

目标:只在用户重新明确选择后讨论。

当前默认结论:

- 不做云端。
- 不做公网远程。
- 不引入额外 VPN/第三方软件作为默认路径。
- 如果未来恢复,必须重新评估成本、备案、App Store、隐私、安全、账号和运维。

## 7. 多 agent 轨道分工

| 轨道 | 范围 | 主要目录 | 依赖 |
| --- | --- | --- | --- |
| A:iOS Local Agent Lens | Scanner、Document、Video、Voice、Hub、Action Button、Dynamic Island | `Sources/AgentPocketUI/`、`ios/`、`Tests/AgentPocketUITests/` | M1 连接稳定 |
| B:Mobile Bridge/Runtime Kit | `/mobile/v1` 合约、mock bridge、runtime-kit、Hermes/OpenClaw provider adapters | `Sources/AgentPocketCore/`、`mock_bridge/`、`runtime-kit/`、`Tests/AgentPocketCoreTests/` | A 的 intake 合约 |
| C:Host Extension | Hermes Plugin/OpenClaw Skill 材料审查、readiness、external install drill | `runtime-kit/packaging/`、`docs/kaka-host-extension-*` | 真实 host-owned 材料 |
| D:UI/UX 与 QA | 视觉统一、真机截图、m1-device checklist、Live Activity/Dynamic Island QA | `Sources/AgentPocketUI/`、`docs/qa-receipts/` | A/B |
| E:治理与文档 | 章程、PROGRESS、README、privacy、API docs、release notes | `docs/`、`README*.md` | 全部轨道 |

协作规则:

1. 同时活跃的实现轨道不超过 3 个。
2. `Sources/AgentPocketCore` 合约变更先写测试,再接 UI/runtime。
3. Host Extension 与 Local Agent Lens 不要混在一个切片里。
4. 每个切片收尾必须更新 `docs/PROGRESS.md`。

## 8. 验证命令

Swift 变更后:

```bash
swift test
```

Runtime Kit / mock bridge / photo-pack / iOS source guard 变更后:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=runtime-kit:mock_bridge \
python3 -m pytest -p no:cacheprovider runtime-kit/tests mock_bridge/tests photo-pack/tests ios/tests -q
```

iOS app build:

```bash
xcodebuild -project ios/AgentPocket.xcodeproj \
  -scheme AgentPocket \
  -destination 'generic/platform=iOS' \
  -skipMacroValidation build
```

iPhone 16 Plus dev install,仅在用户明确要求真机测试时运行:

```bash
xcodebuild -project ios/AgentPocket.xcodeproj \
  -scheme AgentPocket \
  -destination 'id=00008140-000835003EEB001C' \
  -derivedDataPath ios/build-device \
  -skipMacroValidation build

xcrun devicectl device install app \
  --device 00008140-000835003EEB001C \
  ios/build-device/Build/Products/Debug-iphoneos/AgentPocket.app
```

本地 Hermes LAN bridge smoke:

```bash
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --repo-root . \
  --runtime hermes \
  --lan \
  --bonjour \
  --runtime-store-path ~/.kaka/mobile-runtime.sqlite3
```

## 9. 与既有文档的关系

- `README.md` / `README.zh-CN.md`:当前项目摘要和开发入口。
- `PRODUCT.md`:产品定位、用户、边界、设计原则。
- `docs/mobile-bridge-api.md`:手机与运行时契约的事实源。
- `docs/development-history.md`:历史 P 阶段叙事和已完成切片。
- `docs/pocket-agents-direction.md`:Pocket Agents 产品方向背景。
- `docs/kaka-host-extension-*.md`:Host Extension 外部材料、安装体验、plugin/skill 产品化边界。
- `docs/superpowers/plans/*.md`:可执行实施计划,当前被 `.gitignore` 忽略,可作为本地工作材料。
- `docs/qa-receipts/`:真机、UI、runtime smoke 的证据材料。
- `docs/PROGRESS.md`:本章程生效后的默认进度入口。

若旧文档与本章程冲突,以本章程为准。若 Mobile Bridge API 文档与本章程冲突,先更新/审查 API 文档,因为它是手机与运行时合约事实源。

## 10. 下一步默认动作

没有新指令时,按以下顺序推进:

1. 执行 `docs/superpowers/plans/2026-06-13-kaka-local-agent-lens.md` 的 P0a/P0b/P0c 切片。
2. 每个切片完成后更新 `docs/PROGRESS.md`。
3. 涉及 UI、相机、扫描、语音、Live Activity 的切片必须做真机或模拟器 QA。
4. 只有用户重新明确选择云端/远程/Host Extension 外部材料路径时,才切换出 Local Agent Lens 主线。
