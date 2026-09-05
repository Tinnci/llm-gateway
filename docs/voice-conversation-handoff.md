# 多轮语音交接

更新：2026-09-05。任务优先级以各仓库 issues 为准。

## 运行职责

Gateway 在最终语音处理后，根据 dialogue frame 和现有提问标点规则生成
continue_conversation。conversation_continuation trace 记录请求意图。
卫星负责采集、播放及反馈；显示代理投影生命周期事件。

目标设备核实为 HA 2026.6.3、Wyoming Satellite 1.4.1。配对续听实现位于
相邻 phosh-ha-status/home-assistant/wyoming-continuation/ 和
satellite/wyoming-satellite-v1.4.1-continuation.patch。

HA 等待 pipeline 结束和成功 Played 后，以原 conversation ID 启动下一轮 ASR。
HA 基类本来就读取 _conversation_id；此前“字段未使用”的结论应予纠正。
卫星收到 Transcribe 后重开窗口，播放失败发送 Error。静音、停止和错误清除
自动续听请求。具体安装、兼容性及回滚说明由相邻仓库维护。

集成启动直接加载本地 runtime、历史和 fallback 路由。首次配置继续验证凭据，
运行请求继续处理认证和网络错误。模型目录请求超时属于 provider 可用性问题，
与本地诊断是否可以加载分开处理。

## 面板

保留概览、最近运行、规则测试、统一设置四个入口，默认打开最近运行。
列表按语义结果区分回答、澄清、失败、取消，选中详情独立缓存；刷新显示时间。
设置保留统一入口，配置 API 复用集成配置。重绘期间保留输入，提交卫星配置
时先读取输入再显示忙碌状态，失败提示保留供排查。

粗查询和详细查询参见 [API](voice-harness-api.md)。现有兼容接口仍保留；删除
接口前核实外部调用者。已删除没有运行时消费者的虚拟化阈值及对应常量测试。

## 验证边界

前端使用 tsgo、Bun 构建和少量状态行为测试。续听测试分别检查补丁方法和
伪音频卫星流程。卫星模拟中的第二次 Transcribe 由脚本发送，不能证明真实
HA 自动追问或实际声学体验。部署加载检查也只证明服务成功启动。

本次使用代码与文本证据。音频测量由用户另行授权。

2026-09-05 部署目标为 192.168.3.120。配对运行时备份在
/home/user/homeassistant/backups/codex/voice-review-20260905.bDjINl，
首次 Gateway 备份在同目录下 llm_gateway-20260905.ifInAC/component。
Wyoming 安装器备份为 wyoming-20260905-170300.DCOHJD。
服务加载与 API 可用性单独核对；真实模型回复和声学测试使用各自的运行证据。

## 后续仍需完成

1. 实测同一 conversation ID 的二轮输入、playback-end-to-listening 延迟和开头丢字。
2. 测量初次静默、追问静默、播放器失败和取消；空文本与真正静默需 ASR/VAD 证据。
3. 处理跨轮乱序：复用已有请求身份，明确 callback 与 ASR polling 的优先级。
   Wyoming 的 Played 缺少轮次身份，当前实现不能完整排除迟到事件。
4. 显示活动态仍有 TTL，长请求可能提前过期；后续用结束事件管理活动态，
   过期表示遥测未知。原生页面变更仍需目标设备检查。
5. 大面板仍使用完整 innerHTML 重绘。后续按完整表单或详情职责迁入 Lit，
   支持跨标签草稿、焦点保留和列表翻页，而不是按行数拆分助手函数。

保持权限、高风险动作确认、停止/取消、备份与恢复。普通逻辑问题使用类型及
针对性测试解决，不增加新的 hash、冻结 contract 或形式化 gate。
