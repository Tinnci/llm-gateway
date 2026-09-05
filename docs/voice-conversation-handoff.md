# 多轮语音实现交接

日期：2026-09-05。本文件记录本次实现边界和后续建议；任务优先级以所属仓库的
GitHub issues/milestones 为准。先读本文件、关联实现和测试即可继续。

## 目标与约束

Alexa 唤醒后，用户说话、ASR 出文字、Gateway 执行、TTS 播放。模型需要澄清时，
播放完追问后自动打开同一会话的下一次命令输入，界面与声音提示依据实际运行状态。
正常无输入应安静结束；用户取消或重新唤醒应结束旧轮次的影响。

使用 bun/tsgo、uv/uvx。直接修改并做针对性测试。维持高风险动作确认、权限、
取消、超时、目标覆盖和发布边界的安全检查。普通类型和测试足以解决的问题，
直接采用这些机制。新增 hash、冻结 contract、baseline 或 gate 需要具体失败场景
及现有机制不足的证据。用户要求直接执行、使用文本证据；截图和子代理均在本轮范围外。
音频实测需要用户明确授权。

## 已完成的源代码改动

### Gateway

- `custom_components/llm_gateway/conversation.py`：最终语音清理、截断及输出修复之后，
  根据当前活动 dialogue frame 或最终语音的提问标点设置 `continue_conversation`。
  输出修复路径保守关闭续听。保留 `?`、`？`、`;` 的兼容行为。
- `conversation_continuation` trace stage 记录 `requested`、`awaiting_reply` 和
  `source=final_speech_and_dialogue`，表示请求意图。
- `tests/test_conversation.py`：覆盖截断掉尾部问题后关闭续听，以及天气/人物
  澄清 frame 请求续听。
- `policy.py`：搜索权限来自已提交 `RouteDecision.allowed_tools` 和缺失参数，
  首次强制搜索来自 `next_action=search`；删去重复的关键词决策。
  `grounding.py` 自行判断出处问题与搜索证据。
- 前端静态视图、诊断 tabs 和虚拟化常量使用既有类型/校验，移除运行时冻结；
  CI 移除重复版本任务，保留版本一致性与发布检查。对应架构文档已同步。

### 相邻仓库 phosh-ha-status

- `satellite/voice-event.py` 与 service：streaming-start → listening，stt-stop → stt，
  非空 transcript → thinking，空 transcript / `No text recognized` → no_input，
  detect → idle。发送状态元数据，转写内容只用于分类。其他错误保留原有错误音路径。
- `wake-display.sh` 只唤醒屏幕，由 streaming callback 发布聆听状态，消除它原先
  异步晚到的 listening 事件覆盖后续状态的问题。
- `snd-command-wrapper.sh` 在失败分支立即保存播放器退出码，返回真实失败；成功
  发布独立 `playback_finished`。
- `agent/voice_activity.py` 与翻译：idle/no_input/playback_finished 使用中性 idle
  动效；播放结束、打断分别描述播放事实；未知 phase 归为 idle。
- 安装器包含新回调；service 使用正常日志级别。详见该仓库
  `docs/voice-lifecycle.md`、`tests/test_wake_and_cue.py`、`tests/test_voice_activity.py`
  和 `tests/test_agent.py`。

## 真实能力边界

目前实现的是续听意图及本地事件投影。自动二轮输入仍需终端链路支持。
配置中的终端是 Wyoming Satellite 1.4.1；此前检查的 HA 开发依赖中 Wyoming
pipeline 事件路径没有完成消费 continuation 请求的闭环。部署版本需要再核实。

上游参考入口：

- https://github.com/rhasspy/wyoming-satellite （先看 1.4.1 tag 的 callback 实现）
- https://developers.home-assistant.io/docs/core/entity/assist-satellite/

此前上游调查指向 Linux Voice Assistant 作为新续听能力的候选终端。下一位代理应
核对其当前设备支持与接口，再决定迁移；已有回调只投影状态，无法补齐终端能力。
当前 streaming callback 是软件生命周期证据，麦克风和声学就绪需要实机测量。

本次没有新增或生成 earcon。既有 awake.wav 和错误反馈继续由卫星负责。
后续 ready cue 应在实际 capture 就绪后由卫星播放一次。

## 下一步建议，按依赖顺序执行

1. ~~核对终端能力~~（2026-09-05 完成）。结论：现有链路两侧都缺一环 ——
   HA 2026.6.3 的 wyoming 集成不转发 `INTENT_END`（含 `continue_conversation`/
   `conversation_id`）、`Played` 后不重跑管道；wyoming-satellite 1.4.1
   的 `WakeStreamingSatellite` 只能由本地唤醒词打开命令窗口，事件服务是单向的。
   上游 v1.4.1 已是最终版（项目由 Linux Voice Assistant 接任）。
   两个补丁已写好并经模拟验证（见下条），尚未部署：
   - `repos/phosh-ha-status/home-assistant/wyoming-continuation/`：HA 侧
     custom_components 覆盖 + 补丁 + 部署脚本（含 2026.6.x 版本门禁）。
   - `repos/phosh-ha-status/satellite/wyoming-satellite-v1.4.1-continuation.patch`：
     卫星在服务端发起 ASR 阶段（`Transcribe`）时重开命令窗口并触发 listening 提示。
   - `lab/voice-pipeline-smoke/reports/satellite-continuation-simulation-2026-09-05.md`：
     补丁版两轮闭环 PASS，未打补丁基线在窗口重开处 FAIL。
   迁移评估：Linux Voice Assistant（OHF-Voice）经 ESPHome 协议原生支持
   多轮（`--continue-conversation-delay`），支持 aarch64，但仍是 experimental；
   作为后续评估路线，不阻塞补丁路径。评估时保留 PipeWire/AEC、Alexa、
   暂停/停止、声音路由和回退安装方法。
   Gateway 负责意图，卫星负责音频生命周期，显示代理负责投影。
2. 部署并打通一条两轮路径（需按 AGENTS.md 的备份/部署规则执行；HA 侧脚本
   `apply-ha-wyoming-override.sh` 已含备份、版本门禁与回滚说明）。模拟已覆盖
   replayed → capture started → next transcript 的协议层；实测需获用户授权。
   重点关注 playback-end-to-listening 延迟、开头丢字、conversation ID 是否
   真正保留（Gateway trace 里 `continue_conversation` 与同一 dialogue frame）。
3. 处理乱序。当前 callback 缺少 turn/playback 关联，旧 ASR polling 可能覆盖新状态。
   补丁下续听窗口打开期间唤醒词检测被忽略（沿用既有运行期行为），"重新唤醒使
   旧轮次失效"需在此步一并处理。复用已有 conversation/request/turn ID，按轮次及
   生产者顺序接收事件。避免新增独立状态数据库或多套监听控制器。
4. 改善显示生命周期。`voice_activity.py` 仍有 6 秒默认 TTL，长时间 listening /
   thinking 可能先过期，idle callback 也可能很快覆盖 no_input。
   用结束事件关闭活动态，把过期解释为遥测未知；明确 callback 与 ASR polling
   的优先级。以中性短提示表达正常空输入。
5. 增强空输入证据。旧 error callback 只传普通文本，`No text recognized` 只能
   表示无可用文字。区分真正 silence、说话但识别为空、超时和 provider failure
   需要 VAD/ASR 结构化结果。初次静默安静结束；追问静默短暂提示后回到 idle。
   六秒 no-speech 窗口仅是待测初值，计时起点为 capture acknowledgement。
6. 有必要时用显式 reply mode 替代标点 fallback。先检查 HA/模型接口和所有结果
   返回路径，避免只覆盖当前 finalizer。成功输出修复后的续听策略也需单独决定。
7. 最后做完整场景测量：初次静默、追问静默、二轮成功、TTS/网络失败、取消、
   播放中重新唤醒。测 playback-end-to-listening、开头丢字、false VAD 和旧事件
   拒绝。原生界面交互变更沿用 phosh 目标设备 checklist。

## 最少阅读位置与验证

工作区 `/Users/driezy/Downloads/ha-voice-stack` 中各 `repos/*` 独立提交。
Gateway 从 `conversation.py` 的 `conversation_continuation` 搜索定位，沿
`dialogue_pending_key`、`_dialogue_frames` 阅读；Harness 结构看
`docs/harness-architecture.md`，查询接口看 `docs/voice-harness-api.md`。
相邻仓库从 `satellite/wyoming-satellite.service` 进入，然后看 callback、播放 wrapper、
`agent/voice_activity.py` 和显示代理的 ASR polling 调用点。

Gateway 针对性验证：

```sh
uv run pytest tests/test_conversation.py tests/test_policy.py -q
bun run typecheck
bun run build:panel
bun test
```

phosh 针对性验证（播放器测试使用替身）：

```sh
uv run pytest tests/test_wake_and_cue.py tests/test_voice_activity.py tests/test_install_target.py tests/test_agent.py -q
uvx ruff check agent satellite/voice-event.py tests
uvx ruff format --check agent satellite/voice-event.py tests
```

版本文件此次保持不变。此次提交是本地源码收尾，发布和目标设备验收单独进行。
本轮已验证：Gateway conversation/policy 80 项、grounding/router 16 项、前端 21 项、phosh 针对性测试
111 项通过；前端类型检查/构建、两仓库相关 lint/格式检查通过。
版本同步检查为 0.3.48，`uv lock --check` 通过。
HA 目标为 `192.168.3.120`，实际部署先读工作区 AGENTS.md 的备份/部署规则；
提交用 Tinnci GitHub 身份，结束后恢复 shisoratsu。凭据留在本机凭据配置中。
诊断使用现有分层 API，先取摘要再取单轮详情。延迟与计数使用低基数指标；
完整 transcript、Turn 和诊断 JSON 保持在受控诊断路径及其保留策略内。
