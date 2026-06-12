# M1 真机 iPhone + 真实 Claude 运行时 QA 清单

本清单用于 M1 验收。服务端冒烟可不依赖手机；真机步骤需要 iPhone 与 Mac 在同一局域网，并且 Claude API key 只保留在 Mac/运行时环境中。

## 0. 服务端冒烟

- [ ] Fake provider 冒烟可通过：

```bash
PYTHONPATH=mock_bridge:runtime-kit:photo-pack python3 -m agent_pocket_mock_bridge.qa smoke-real-provider --fake
```

预期结果：命令返回 0，JSON 中 `ok` 为 `true`，`mode` 为 `fake`，步骤包含 `health`、`capabilities`、`asset_upload`、`image_intake_*`、`universal_intake_*`、`recall_remember`、`recall_forget`，所有 step 的 `status` 都是 `passed`。

- [ ] Real provider 冒烟可手动通过：

```bash
export ANTHROPIC_API_KEY=<your-anthropic-api-key>
PYTHONPATH=mock_bridge:runtime-kit:photo-pack python3 -m agent_pocket_mock_bridge.qa smoke-real-provider --real
```

预期结果：命令返回 0，JSON 中 `ok` 为 `true`，`provider` 为 `anthropic`，不输出 API key 值。若未设置 `ANTHROPIC_API_KEY`，命令返回 2，并输出 `missing_anthropic_api_key`。

## 1. 启动真实运行时

- [ ] 在 Mac 上启动 Runtime Kit：

```bash
export ANTHROPIC_API_KEY=<your-anthropic-api-key>
PYTHONPATH=runtime-kit:mock_bridge python3 -m kaka_mobile_runtime_kit start \
  --lan \
  --bonjour \
  --bonjour-host "$(ipconfig getifaddr en0)" \
  --runtime-store-path "$HOME/.kaka/kaka-runtime.sqlite3" \
  --provider anthropic \
  --runtime hermes
```

预期结果：终端输出 pairing page，bridge 监听 `0.0.0.0:8765`，Bonjour 已开启；输出中只出现 `ANTHROPIC_API_KEY` 这个环境变量名，不出现 key 值。

## 2. 扫码或 Bonjour 配对

- [ ] iPhone 打开 Kaka，进入连接流程。
- [ ] 优先使用 Bonjour 发现 Mac runtime；若发现失败，打开 Mac 终端输出的 pairing page 并扫码。

预期结果：iPhone 显示 Mac runtime 卡片或 QR 配对页；确认后连接成功，后续请求使用 `/mobile/v1`，不会要求在 iPhone 输入 Claude API key。

## 3. 拍照 Image Intake

- [ ] 在 Kaka 内拍照或从相册选择一张图片并发送给运行时。

预期结果：任务进入进行中状态，然后完成；结果显示图片摘要和建议技能，建议中至少包含可执行的图像相关入口，例如 OCR、识别、翻译、食物估计或照片增强。

## 4. 分享到收件箱

- [ ] 从系统 Share Sheet 分享一段文本或网页 URL 到 Kaka Inbox。
- [ ] 在 Kaka 中检查待发送项并发送到运行时。

预期结果：Inbox 中出现来源、标题或摘要；发送后 universal intake 任务完成，并返回摘要与建议操作，不把内容自动写入 Recall，除非用户明确选择 Remember。

## 5. 粘贴到收件箱

- [ ] 复制一段文本，使用 Kaka 的粘贴入口创建 Inbox item。
- [ ] 发送到运行时。

预期结果：粘贴内容可预览；发送后返回 text intake 摘要和建议操作；没有剪贴板后台自动读取行为。

## 6. 语音追问

- [ ] 在一个已完成的 intake 或 image intake 结果页发起语音追问。
- [ ] 说出一个针对当前结果的简短问题并提交。

预期结果：语音内容转成用户可见文本后发送；运行时返回与当前任务相关的回答；没有要求 iPhone 持有 Claude API key。

## 7. Recall 记住与遗忘

- [ ] 对一个用户确认过的结果点击 Remember。

预期结果：Recall action 返回 remembered，列表或搜索能找到该条用户可见摘要。

- [ ] 对同一条内容执行 Forget 或删除。

预期结果：Recall action 返回 forgotten；再次搜索同样关键词时，该条内容不再出现。

## 8. 断线重连

- [ ] 保持 iPhone 不退出 Kaka，停止 Mac 上的 Runtime Kit 进程。
- [ ] 在 iPhone 上触发一次刷新或新任务。

预期结果：iPhone 显示连接失败或需要重连的状态，不丢失本地待处理内容。

- [ ] 重新运行第 1 步启动命令。
- [ ] 在 iPhone 上重新连接或等待已保存连接恢复。

预期结果：连接恢复后可以继续提交新任务；SQLite 路径不变时，运行时侧 Recall/任务历史按当前实现保留。

## 9. 收尾记录

- [ ] 保存服务端 smoke JSON 输出。
- [ ] 记录 iPhone 型号、iOS 版本、Mac 局域网 IP、Runtime Kit 命令、PR/commit SHA。
- [ ] 确认日志、截图、QA JSON、SQLite、iPhone UI 中没有真实 `ANTHROPIC_API_KEY` 值。

