// @ts-check

/**
 * @typedef {"auto" | "fast" | "mid" | "deep"} RouteKind
 * @typedef {"local" | "ha_media_player" | "auto"} FirstResponsePlaybackAdapter
 * @typedef {{ fast: string, mid: string, deep: string }} TierTextMap
 * @typedef {{ fast: number, mid: number, deep: number }} TierNumberMap
 * @typedef {{ kind: RouteKind, model: string, max_tokens: number, timeout_s: number, async_deep_task: boolean }} RouteStatus
 * @typedef {{ enabled: boolean, adapter?: FirstResponsePlaybackAdapter, local_service?: string, tts_entity?: string, media_player_entity?: string }} FirstResponseAudioOptions
 * @typedef {{ service?: string, available?: boolean, preferred?: boolean }} LocalServiceCandidate
 * @typedef {{ entity_id?: string, state?: string, name?: string, usable?: boolean, preferred?: boolean }} AudioEntityCandidate
 * @typedef {{ enabled?: boolean, adapter?: FirstResponsePlaybackAdapter, configured?: Record<string, any>, route?: Record<string, any>, can_play?: boolean, services?: Record<string, boolean>, candidates?: { local_services?: LocalServiceCandidate[], tts?: AudioEntityCandidate[], media_player?: AudioEntityCandidate[] } }} FirstResponseAudioStatus
 * @typedef {{ quiet_hours?: { start_hour?: number, end_hour?: number, current_local_hour?: number, active?: boolean } }} FeedbackPolicyStatus
 * @typedef {{ routing_mode: RouteKind, models: TierTextMap, max_tokens: TierNumberMap, timeouts: TierNumberMap, first_response_audio?: FirstResponseAudioOptions }} HarnessOptions
 * @typedef {{ enabled: boolean, include_raw_messages: boolean, max_runs: number, retention_hours: number }} TraceOptions
 * @typedef {{ provider?: string, model?: string, status?: string, latency_ms?: number, error?: string, retryable?: boolean, iteration?: number }} ProviderAttempt
 * @typedef {{ name?: string, base_url?: string, models?: Partial<TierTextMap>, has_api_key?: boolean, soft_timeouts?: Partial<TierNumberMap>, max_tokens?: Partial<TierNumberMap> }} ProviderProfile
 * @typedef {{ primary?: ProviderProfile, fallbacks?: ProviderProfile[], fallback_enabled?: boolean, config_error?: string }} ProviderStatus
 * @typedef {{ provider?: string, route?: string, failures?: number, cooldown_remaining_s?: number, last_error?: string }} ProviderHealth
 * @typedef {{ latest_display?: Record<string, any> | null, display_events?: Array<Record<string, any>>, earcon_events?: Array<Record<string, any>> }} FeedbackStatus
 * @typedef {{ entry_id: string, title: string, state: string, base_url?: string, options: HarnessOptions, routes: RouteStatus[], trace: TraceOptions, traces?: { records?: Array<Record<string, any>>, storage?: Record<string, any> }, voice_runs?: Array<Record<string, any>>, feedback?: FeedbackStatus, feedback_policy?: FeedbackPolicyStatus, first_response_audio?: FirstResponseAudioStatus, memory?: any, search?: { providers?: string[] }, model_providers?: ProviderStatus, provider_health?: ProviderHealth[] }} HarnessEntry
 * @typedef {{ routing_modes: RouteKind[], max_tokens: { min: number, max: number }, timeouts: { min: number, max: number }, trace_max_runs: { min: number, max: number }, trace_retention_hours: { min: number, max: number }, first_response_playback_adapters?: FirstResponsePlaybackAdapter[] }} EditableSchema
 * @typedef {{ id: string, risk?: string, title?: string, title_i18n?: Record<string, string>, spoken?: string, spoken_i18n?: Record<string, string>, rules?: string[] }} PromptPolicy
 * @typedef {{ id: string, name?: string, name_i18n?: Record<string, string>, user?: string, user_i18n?: Record<string, string>, response?: string, response_i18n?: Record<string, string>, expected?: Record<string, unknown>, expected_i18n?: Record<string, Record<string, unknown>> }} SampleScenario
 * @typedef {{ path?: string, url?: string, duration_ms?: number, lufs?: number, peak_dbfs?: number, purpose?: string, purpose_i18n?: Record<string, string>, semantic_state?: string, priority?: number, can_play_while_listening?: boolean, quiet_hours_behavior?: string, trace_event_name?: string }} EarconFile
 * @typedef {{ pack?: string, sample_rate?: number, target_lufs?: number, true_peak_dbfs?: number, files?: Record<string, EarconFile> }} EarconPack
 * @typedef {{ entity_id: string, state: string, available: boolean, name?: string, unit?: string, attributes?: Record<string, unknown> }} SatelliteEntityState
 * @typedef {{ states?: Record<string, SatelliteEntityState>, services?: Record<string, boolean> }} SatelliteStatus
 * @typedef {{ entries: HarnessEntry[], editable: EditableSchema, satellite?: SatelliteStatus, earcons?: EarconPack, prompt_policies?: PromptPolicy[], sample_scenarios?: SampleScenario[] }} HarnessStatus
 * @typedef {{ entry_id: string, options: { routing_mode: RouteKind, models: TierTextMap, max_tokens: TierNumberMap, timeouts: TierNumberMap, trace: TraceOptions, first_response_audio?: FirstResponseAudioOptions } }} OptionsUpdateRequest
 * @typedef {{ user: string, response: string, expected: string }} ScenarioDraft
 */

const TABS = [
  ["runs", "tab.runs", "mdi:play-circle-outline"],
  ["settings", "tab.settings", "mdi:tune-variant"],
  ["satellite", "tab.satellite", "mdi:microphone-settings"],
  ["policies", "tab.policies", "mdi:shield-check-outline"],
  ["scenarios", "tab.scenarios", "mdi:clipboard-text-search-outline"],
  ["search", "tab.search", "mdi:web"],
  ["memory", "tab.memory", "mdi:database-eye-outline"],
  ["earcons", "tab.earcons", "mdi:music-note-outline"],
  ["regression", "tab.regression", "mdi:chart-timeline-variant"],
];

const DEFAULT_EXPECTED = {
  must_search: false,
  spoken_response: {
    max_sentences: 2,
    must_not_mention: ["entity_id"],
  },
};

/** @type {EditableSchema} */
const DEFAULT_EDITABLE = {
  routing_modes: ["auto", "fast", "mid", "deep"],
  max_tokens: { min: 1, max: 16384 },
  timeouts: { min: 5, max: 300 },
  trace_max_runs: { min: 1, max: 200 },
  trace_retention_hours: { min: 1, max: 168 },
  first_response_playback_adapters: ["local", "ha_media_player", "auto"],
};

const I18N = {
  en: {
    "app.title": "Voice Harness",
    "aria.views": "Voice Harness views",
    "common.refresh": "Refresh",
    "common.save": "Save",
    "common.saved": "Saved",
    "common.enabled": "Enabled",
    "common.disabled": "Disabled",
    "tab.runs": "Runs",
    "tab.settings": "Settings",
    "tab.satellite": "Satellite",
    "tab.policies": "Prompt Policies",
    "tab.scenarios": "Scenarios",
    "tab.search": "Search Lab",
    "tab.memory": "Memory Lab",
    "tab.earcons": "Earcons",
    "tab.regression": "Regression",
    "status.loading": "Reading integration status",
    "status.waiting": "Waiting for Home Assistant",
    "status.no_entries": "No LLM Gateway config entries loaded yet",
    "status.entries": "{count} config entries loaded",
    "runs.empty": "No configured LLM Gateway entries.",
    "runs.trace_disabled": "Diagnostic traces are disabled",
    "runs.trace_empty": "No recorded runs yet.",
    "runs.trace_enabled": "Traces on",
    "runs.live": "Recent live runs",
    "runs.live_empty": "No live run snapshots yet.",
    "runs.live_status": "Live status",
    "runs.no_live_status": "No live display status yet.",
    "runs.earcons": "Earcons",
    "runs.no_earcons": "No earcon events.",
    "runs.display_status": "Display status",
    "runs.no_display_status": "No display status events.",
    "runs.privacy": "Privacy",
    "runs.actions_available": "Actions",
    "runs.raw_enabled": "raw compressed",
    "runs.raw_disabled": "summary only",
    "runs.retention": "{count} runs · {hours}h",
    "runs.user": "User",
    "runs.assistant": "Assistant",
    "runs.tools": "{count} tool events",
    "runs.provider": "Provider",
    "runs.provider_attempts": "Provider attempts",
    "runs.detail": "Run detail",
    "runs.input": "Input",
    "runs.route": "Route",
    "runs.first_response": "First response",
    "runs.first_response_audio": "First response audio",
    "runs.final_speech": "Final speech",
    "runs.debug_flags": "Debug flags",
    "runs.search": "Search",
    "runs.deep_model": "Deep model",
    "runs.deep_verifier": "Deep verifier",
    "runs.high_risk": "High risk",
    "runs.final_modified": "Final modified",
    "runs.polluted_evidence": "Polluted evidence",
    "runs.verifier_mode": "Verifier mode",
    "runs.critical_path": "Critical path",
    "runs.no_critical_path": "No timeline spans recorded.",
    "runs.blocking": "Blocking",
    "runs.non_blocking": "Non-blocking",
    "runs.first_response_detail": "First response decision",
    "runs.search_debug": "Search debug",
    "runs.no_search_debug": "No search debug data.",
    "runs.search_gate": "Search gate",
    "runs.inventory": "Inventory / static context",
    "runs.inventory_scope": "Scope",
    "runs.inventory_execution": "Execution",
    "runs.inventory_entities": "Exposed entities",
    "runs.weather_path": "Weather / local context",
    "runs.tool_iterations": "Tool calls by iteration",
    "runs.no_tool_iterations": "No tool iteration data.",
    "runs.duplicate_suppressions": "Duplicate tool suppressions",
    "runs.no_duplicate_suppressions": "No duplicate tool suppressions.",
    "runs.active_stage": "Active stage",
    "runs.running_duration": "Running duration",
    "runs.completion": "Completion",
    "runs.search_gate_reason": "Gate",
    "runs.search_queries": "Queries",
    "runs.search_providers": "Providers",
    "runs.search_results": "Results",
    "runs.actions": "Actions / HA state",
    "runs.no_actions": "No HA action tool calls.",
    "runs.timing": "Timing",
    "runs.reason": "Reason",
    "runs.within_target": "within target",
    "runs.missed_target": "missed target",
    "runs.timeout": "timeout",
    "runs.cache_hit": "cache hit",
    "runs.polluted_result": "polluted result",
    "runs.unintended_state_change": "unintended state change",
    "runs.errors": "Errors",
    "runs.no_errors": "No recorded errors.",
    "runs.tool_events": "Tool events",
    "runs.no_tools": "No tool events.",
    "runs.evidence": "Evidence",
    "runs.no_evidence": "No typed evidence.",
    "runs.grounding": "Grounding verifier",
    "runs.grounding_candidates": "Evidence candidates",
    "runs.grounding_canonical": "Canonical answers",
    "runs.grounding_repairs": "Repairs",
    "runs.timeline": "Timeline",
    "runs.raw_payload": "Raw compressed payload",
    "runs.no_raw": "Raw payload was not stored for this run.",
    "runs.storage": "{records} records · {bytes} compressed bytes",
    "runs.no_conversation": "No conversation id",
    "entry.base_url_missing": "Base URL not configured",
    "settings.empty": "No editable config entries.",
    "settings.title": "Editable runtime settings",
    "settings.description": "These fields update runtime-safe options. Secrets, base URL, HA LLM API exposure and the system prompt use Home Assistant options flow for admin validation and redaction.",
    "settings.routing": "Routing",
    "settings.routing_mode": "Routing mode",
    "settings.models": "Models",
    "settings.budgets": "Budgets",
    "settings.traces": "Diagnostic traces",
    "settings.first_response_audio": "First response audio",
    "settings.first_response_audio_enabled": "Play first response audio",
    "settings.first_response_adapter": "Playback adapter",
    "settings.first_response_local_service": "Local display-agent service",
    "settings.first_response_local_service_hint": "Preferred: rest_command.kukui_voice_feedback. Leave empty for auto-detection.",
    "settings.first_response_tts_entity": "HA fallback TTS entity",
    "settings.first_response_media_player": "HA fallback media_player",
    "settings.audio_route": "Active route",
    "settings.audio_candidates": "Candidates",
    "settings.local_adapter_missing": "Local playback adapter missing. Add a display-agent service before expecting tablet-speaker audio.",
    "settings.ha_fallback_notice": "HA media_player fallback is explicit; it is not tablet-local playback.",
    "settings.model": "{tier} model",
    "settings.max_tokens": "{tier} max tokens",
    "settings.timeout": "{tier} timeout",
    "settings.diagnostic_traces": "Enable diagnostic traces",
    "settings.include_raw": "Store compressed raw messages",
    "settings.max_runs": "Maximum diagnostic runs",
    "settings.retention_hours": "Diagnostic retention hours",
    "settings.saved": "Settings saved.",
    "satellite.title": "Satellite and voice controls",
    "satellite.description": "These controls use HA entities and the typed local apply API exposed by the display agent. Applying wake or mic changes restarts the local satellite path.",
    "satellite.pause": "Pause voice",
    "satellite.resume": "Resume voice",
    "satellite.save_minutes": "Save minutes",
    "satellite.save_config": "Save config",
    "satellite.apply_config": "Apply config",
    "satellite.minutes": "Pause minutes",
    "satellite.config": "Wake and audio tuning",
    "satellite.wake_threshold": "Wake threshold",
    "satellite.wake_trigger_level": "Trigger level",
    "satellite.wake_refractory_seconds": "Refractory seconds",
    "satellite.mic_volume_multiplier": "Mic gain",
    "satellite.tts_volume_day": "Day TTS volume",
    "satellite.tts_volume_night": "Night TTS volume",
    "satellite.fallback_clip_volume": "Local clip volume",
    "satellite.voice_config": "Applied voice config",
    "satellite.asr_metrics": "ASR metrics",
    "satellite.unavailable": "HA satellite entities are not available.",
    "satellite.voice_pipeline": "Voice pipeline",
    "satellite.voice_paused": "Voice paused",
    "satellite.display_awake": "Display awake",
    "satellite.pause_requested": "Pause request switch",
    "satellite.pause_minutes": "Pause minutes",
    "satellite.ambient_light": "Ambient light",
    "satellite.screen_brightness": "Screen brightness",
    "satellite.missing": "missing",
    "satellite.service_unavailable": "Required HA service is not available.",
    "policies.empty": "No prompt policies.",
    "scenario.user": "User input",
    "scenario.response": "Assistant response",
    "scenario.expected": "Expected JSON",
    "scenario.run": "Run scenario",
    "search.gating": "Search gating",
    "search.no_providers": "No search provider key exposed",
    "search.evaluate": "Evaluate gating",
    "providers.title": "Model providers",
    "providers.primary": "Primary",
    "providers.fallbacks": "{count} fallback providers",
    "providers.none": "No fallback provider profiles",
    "providers.config_error": "Provider config error: {message}",
    "providers.health": "Provider health",
    "providers.health_empty": "No provider penalties active",
    "providers.cooldown": "{seconds}s cooldown",
    "memory.turns": "{count} turns",
    "memory.user": "User",
    "memory.assistant": "Assistant",
    "memory.empty": "No active memory sessions.",
    "earcon.no_pack": "No earcon pack",
    "earcon.meta": "{sampleRate} Hz · target {targetLufs} LUFS · peak limit {peakDbfs} dBFS",
    "earcon.play": "Play {name}",
    "earcon.peak": "{peak} dBFS peak",
    "earcon.empty": "No rendered earcons.",
    "regression.run": "Run",
    "route.timeout": "{seconds}s timeout",
    "route.tokens": "{count} tokens",
    "result.empty": "No run result yet.",
    "result.passed": "Passed",
    "result.failed": "Failed",
    "result.meta": "Route: {route} · Search: {search}",
    "search.allowed": "allowed",
    "search.blocked": "blocked",
    "mode.auto": "Auto",
    "mode.fast": "Fast",
    "mode.mid": "Mid",
    "mode.deep": "Deep",
    "adapter.local": "Local display-agent",
    "adapter.ha_media_player": "HA media_player fallback",
    "adapter.auto": "Local, then fallback",
    "tier.fast": "Fast",
    "tier.mid": "Mid",
    "tier.deep": "Deep",
    "risk.low": "Low",
    "risk.medium": "Medium",
    "risk.high": "High",
    "trace.status.complete": "Complete",
    "trace.status.queued": "Queued",
    "trace.status.error": "Error",
    "trace.status.unknown": "Unknown",
    "grounding.status.not_required": "Not required",
    "grounding.status.no_answer": "No answer",
    "grounding.status.no_evidence": "No evidence",
    "grounding.status.ok": "Grounded",
    "grounding.status.repaired": "Repaired",
    "grounding.status.unsupported": "Unsupported",
    "grounding.status.verifier_error": "Verifier error",
    "verifier.blocking": "blocking",
    "verifier.audit_only": "audit only",
    "verifier.disabled": "disabled",
    "evidence.quote_origin": "quote origin",
    "evidence.term_explanation_source": "term explanation",
    "evidence.commentary_source": "commentary",
    "evidence.polluted_related_item": "related item",
    "rule.max_one_sentence": "One sentence",
    "rule.no_tool_details": "No tool details",
    "rule.no_entity_id": "No entity ids",
    "rule.answer_first": "Answer first",
    "rule.no_long_list": "No long lists",
    "rule.no_url": "No URLs",
    "rule.one_question": "One question",
    "rule.no_action_before_clarity": "Clarify before action",
    "rule.must_confirm": "Must confirm",
    "rule.name_target": "Name target",
    "rule.no_action_before_confirmation": "No action before confirmation",
    "rule.external_facts_only": "External facts only",
    "rule.cite_in_panel": "Cite in panel",
    "rule.short_tts": "Short TTS",
    "rule.local_clip_preferred": "Prefer local clip",
    "rule.do_not_repeat": "Do not repeat",
    "rule.do_not_extend_dialog": "Do not extend dialog",
    "rule.stop_when_final_tts_starts": "Stop when final TTS starts",
    "rule.actionable_repair": "Actionable repair",
    "rule.no_blame": "No blame",
    "rule.one_next_step": "One next step",
    "rule.non_blocking_voice": "Non-blocking voice",
    "rule.no_direct_ha_action": "No direct HA action",
    "error.invalid_expected_json": "Expected JSON is not valid.",
    "policy.low_risk_success.title": "Low-risk success",
    "policy.low_risk_success.spoken": "Done.",
    "policy.state_query.title": "State query",
    "policy.state_query.spoken": "Answer the conclusion first without long explanation.",
    "policy.clarification.title": "Minimal clarification",
    "policy.clarification.spoken": "Ask only one minimal clarification question.",
    "policy.high_risk_confirmation.title": "High-risk confirmation",
    "policy.high_risk_confirmation.spoken": "Do you want to operate {target}? Please confirm.",
    "policy.search_summary.title": "Search summary",
    "policy.search_summary.spoken": "Say the conclusion first; put sources and long lists on screen.",
    "policy.error_repair.title": "Error repair",
    "policy.error_repair.spoken": "Give the next step instead of only saying you did not understand.",
    "policy.deep_task.title": "Deep task",
    "policy.deep_task.spoken": "I will keep analyzing and send the result to Home Assistant notifications.",
    "sample.fast-light.name": "Basic light control",
    "sample.mid-search.name": "Fresh information query",
    "sample.risk-confirmation.name": "High-risk action confirmation",
    "earcon.clarification.purpose": "The assistant needs one missing detail before acting.",
    "earcon.confirmation.purpose": "High-risk action needs explicit user confirmation.",
    "earcon.deep_task.purpose": "Long reasoning has been handed off to a background task.",
    "earcon.failure.purpose": "Request failed or the assistant cannot continue safely.",
    "earcon.listening_end.purpose": "Speech capture ended and the assistant is processing.",
    "earcon.listening_start.purpose": "Microphone is open and the user can speak.",
    "earcon.processing_loop.purpose": "Quiet loop for slow provider waits after the soft latency threshold.",
    "earcon.provider_fallback.purpose": "Primary model provider was slow or failed; the request is moving to a fallback provider.",
    "earcon.search.purpose": "Web search is being used for current external information.",
    "earcon.success.purpose": "Low-risk command completed.",
    "earcon.wake.purpose": "Wake word accepted; assistant is entering the voice path.",
  },
  "zh-Hans": {
    "app.title": "语音测试台",
    "aria.views": "语音测试台视图",
    "common.refresh": "刷新",
    "common.save": "保存",
    "common.saved": "已保存",
    "common.enabled": "已启用",
    "common.disabled": "未启用",
    "tab.runs": "运行记录",
    "tab.settings": "配置",
    "tab.satellite": "卫星端",
    "tab.policies": "提示策略",
    "tab.scenarios": "场景测试",
    "tab.search": "搜索实验室",
    "tab.memory": "记忆实验室",
    "tab.earcons": "提示音",
    "tab.regression": "回归测试",
    "status.loading": "正在读取集成状态",
    "status.waiting": "等待 Home Assistant",
    "status.no_entries": "尚未加载 LLM Gateway 配置项",
    "status.entries": "已加载 {count} 个配置项",
    "runs.empty": "没有已配置的 LLM Gateway 条目。",
    "runs.trace_disabled": "诊断记录未开启",
    "runs.trace_empty": "还没有运行记录。",
    "runs.trace_enabled": "诊断记录已开启",
    "runs.live": "最近实时运行",
    "runs.live_empty": "还没有实时运行快照。",
    "runs.live_status": "实时状态",
    "runs.no_live_status": "还没有锁屏/悬浮状态。",
    "runs.earcons": "提示音事件",
    "runs.no_earcons": "没有提示音事件。",
    "runs.display_status": "显示状态",
    "runs.no_display_status": "没有显示状态事件。",
    "runs.privacy": "隐私",
    "runs.actions_available": "动作",
    "runs.raw_enabled": "原始内容已压缩",
    "runs.raw_disabled": "仅摘要",
    "runs.retention": "{count} 条 · {hours} 小时",
    "runs.user": "用户",
    "runs.assistant": "助手",
    "runs.tools": "{count} 个工具事件",
    "runs.provider": "模型 provider",
    "runs.provider_attempts": "Provider 尝试",
    "runs.detail": "运行详情",
    "runs.input": "输入",
    "runs.route": "路由",
    "runs.first_response": "首反馈",
    "runs.first_response_audio": "首反馈音频",
    "runs.final_speech": "最终语音",
    "runs.debug_flags": "调试标记",
    "runs.search": "搜索",
    "runs.deep_model": "深模型",
    "runs.deep_verifier": "Deep 校验",
    "runs.high_risk": "高风险",
    "runs.final_modified": "最终被改写",
    "runs.polluted_evidence": "污染证据",
    "runs.verifier_mode": "校验模式",
    "runs.critical_path": "关键路径",
    "runs.no_critical_path": "没有记录时间线 span。",
    "runs.blocking": "阻塞",
    "runs.non_blocking": "非阻塞",
    "runs.first_response_detail": "首反馈决策",
    "runs.search_debug": "搜索调试",
    "runs.no_search_debug": "没有搜索调试数据。",
    "runs.search_gate": "搜索门控",
    "runs.inventory": "设备清单 / 静态上下文",
    "runs.inventory_scope": "范围",
    "runs.inventory_execution": "执行",
    "runs.inventory_entities": "已暴露实体",
    "runs.weather_path": "天气 / 本地上下文",
    "runs.tool_iterations": "按轮次的工具调用",
    "runs.no_tool_iterations": "没有工具轮次数据。",
    "runs.duplicate_suppressions": "重复工具抑制",
    "runs.no_duplicate_suppressions": "没有重复工具抑制。",
    "runs.active_stage": "活跃阶段",
    "runs.running_duration": "运行时长",
    "runs.completion": "完成状态",
    "runs.search_gate_reason": "搜索门控",
    "runs.search_queries": "查询",
    "runs.search_providers": "Provider",
    "runs.search_results": "结果",
    "runs.actions": "动作 / HA 状态",
    "runs.no_actions": "没有 HA 动作工具调用。",
    "runs.timing": "时间",
    "runs.reason": "原因",
    "runs.within_target": "目标内",
    "runs.missed_target": "超出目标",
    "runs.timeout": "超时",
    "runs.cache_hit": "命中缓存",
    "runs.polluted_result": "污染结果",
    "runs.unintended_state_change": "非预期状态变化",
    "runs.errors": "错误",
    "runs.no_errors": "没有记录到错误。",
    "runs.tool_events": "工具事件",
    "runs.no_tools": "没有工具事件。",
    "runs.evidence": "证据",
    "runs.no_evidence": "没有 typed evidence。",
    "runs.grounding": "证据校验",
    "runs.grounding_candidates": "证据候选",
    "runs.grounding_canonical": "标准答案",
    "runs.grounding_repairs": "修正",
    "runs.timeline": "时间线",
    "runs.raw_payload": "压缩原始 payload",
    "runs.no_raw": "本次运行未保存原始 payload。",
    "runs.storage": "{records} 条记录 · {bytes} 压缩字节",
    "runs.no_conversation": "无会话 id",
    "entry.base_url_missing": "未配置 Base URL",
    "settings.empty": "没有可编辑的配置项。",
    "settings.title": "可编辑运行配置",
    "settings.description": "这些字段只更新运行期安全选项。密钥、Base URL、HA LLM API 暴露范围和系统提示词使用 Home Assistant options flow 做管理员校验和脱敏。",
    "settings.routing": "路由",
    "settings.routing_mode": "路由模式",
    "settings.models": "模型",
    "settings.budgets": "预算",
    "settings.traces": "诊断记录",
    "settings.first_response_audio": "首反馈音频",
    "settings.first_response_audio_enabled": "播放首反馈音频",
    "settings.first_response_adapter": "播放 adapter",
    "settings.first_response_local_service": "本地 display-agent 服务",
    "settings.first_response_local_service_hint": "推荐：rest_command.kukui_voice_feedback。留空则自动检测。",
    "settings.first_response_tts_entity": "HA fallback TTS 实体",
    "settings.first_response_media_player": "HA fallback media_player",
    "settings.audio_route": "当前播放路由",
    "settings.audio_candidates": "候选项",
    "settings.local_adapter_missing": "缺少本地播放 adapter。需要先接 display-agent 服务，平板本机扬声器才会出声。",
    "settings.ha_fallback_notice": "HA media_player 只是显式 fallback，不是平板本机播放。",
    "settings.model": "{tier} 模型",
    "settings.max_tokens": "{tier} 最大令牌",
    "settings.timeout": "{tier} 超时",
    "settings.diagnostic_traces": "启用诊断记录",
    "settings.include_raw": "保存压缩原始消息",
    "settings.max_runs": "最多诊断运行数",
    "settings.retention_hours": "诊断保留小时数",
    "settings.saved": "配置已保存。",
    "satellite.title": "卫星端与语音控制",
    "satellite.description": "这些控件使用 HA 实体和 display-agent 暴露的 typed apply API。应用唤醒或麦克风改动会重启本地 satellite 链路。",
    "satellite.pause": "暂停语音",
    "satellite.resume": "恢复语音",
    "satellite.save_minutes": "保存分钟数",
    "satellite.save_config": "保存配置",
    "satellite.apply_config": "应用配置",
    "satellite.minutes": "暂停分钟数",
    "satellite.config": "唤醒和音频调校",
    "satellite.wake_threshold": "唤醒阈值",
    "satellite.wake_trigger_level": "连续命中",
    "satellite.wake_refractory_seconds": "冷却秒数",
    "satellite.mic_volume_multiplier": "麦克风增益",
    "satellite.tts_volume_day": "白天播报音量",
    "satellite.tts_volume_night": "夜间播报音量",
    "satellite.fallback_clip_volume": "本地片段音量",
    "satellite.voice_config": "已应用语音配置",
    "satellite.asr_metrics": "ASR 指标",
    "satellite.unavailable": "HA 卫星端实体不可用。",
    "satellite.voice_pipeline": "语音管线",
    "satellite.voice_paused": "语音暂停",
    "satellite.display_awake": "屏幕唤醒",
    "satellite.pause_requested": "暂停请求开关",
    "satellite.pause_minutes": "暂停分钟数",
    "satellite.ambient_light": "环境光",
    "satellite.screen_brightness": "屏幕亮度",
    "satellite.missing": "缺失",
    "satellite.service_unavailable": "所需 HA 服务不可用。",
    "policies.empty": "没有提示策略。",
    "scenario.user": "用户输入",
    "scenario.response": "助手回复",
    "scenario.expected": "期望 JSON",
    "scenario.run": "运行场景",
    "search.gating": "搜索门控",
    "search.no_providers": "未暴露搜索 provider key",
    "search.evaluate": "评估门控",
    "providers.title": "模型 provider",
    "providers.primary": "主 provider",
    "providers.fallbacks": "{count} 个备用 provider",
    "providers.none": "未配置备用 provider profiles",
    "providers.config_error": "Provider 配置错误：{message}",
    "providers.health": "Provider 健康",
    "providers.health_empty": "当前没有 provider 冷却惩罚",
    "providers.cooldown": "冷却 {seconds}s",
    "memory.turns": "{count} 轮",
    "memory.user": "用户",
    "memory.assistant": "助手",
    "memory.empty": "没有活跃记忆会话。",
    "earcon.no_pack": "没有提示音包",
    "earcon.meta": "{sampleRate} Hz · 目标 {targetLufs} LUFS · 峰值上限 {peakDbfs} dBFS",
    "earcon.play": "播放 {name}",
    "earcon.peak": "{peak} dBFS 峰值",
    "earcon.empty": "没有已渲染的提示音。",
    "regression.run": "运行",
    "route.timeout": "{seconds}s 超时",
    "route.tokens": "{count} 个令牌",
    "result.empty": "还没有运行结果。",
    "result.passed": "通过",
    "result.failed": "失败",
    "result.meta": "路由：{route} · 搜索：{search}",
    "search.allowed": "允许",
    "search.blocked": "阻止",
    "mode.auto": "自动",
    "mode.fast": "快速",
    "mode.mid": "均衡",
    "mode.deep": "深度",
    "adapter.local": "本地 display-agent",
    "adapter.ha_media_player": "HA media_player fallback",
    "adapter.auto": "本地优先，失败再 fallback",
    "tier.fast": "快速",
    "tier.mid": "均衡",
    "tier.deep": "深度",
    "risk.low": "低",
    "risk.medium": "中",
    "risk.high": "高",
    "trace.status.complete": "完成",
    "trace.status.queued": "排队",
    "trace.status.error": "错误",
    "trace.status.unknown": "未知",
    "grounding.status.not_required": "不需要",
    "grounding.status.no_answer": "无答案",
    "grounding.status.no_evidence": "缺少证据",
    "grounding.status.ok": "已校验",
    "grounding.status.repaired": "已修正",
    "grounding.status.unsupported": "未被证据支持",
    "grounding.status.verifier_error": "校验器错误",
    "verifier.blocking": "阻塞",
    "verifier.audit_only": "旁路审计",
    "verifier.disabled": "未启用",
    "evidence.quote_origin": "出处证据",
    "evidence.term_explanation_source": "词义解释来源",
    "evidence.commentary_source": "注释来源",
    "evidence.polluted_related_item": "相关项污染",
    "rule.max_one_sentence": "一句话内",
    "rule.no_tool_details": "不说工具细节",
    "rule.no_entity_id": "不说 entity_id",
    "rule.answer_first": "先答结论",
    "rule.no_long_list": "不读长列表",
    "rule.no_url": "不读 URL",
    "rule.one_question": "一次一个问题",
    "rule.no_action_before_clarity": "澄清前不执行",
    "rule.must_confirm": "必须确认",
    "rule.name_target": "复述对象",
    "rule.no_action_before_confirmation": "确认前不执行",
    "rule.external_facts_only": "仅外部事实",
    "rule.cite_in_panel": "来源放面板",
    "rule.short_tts": "短 TTS",
    "rule.local_clip_preferred": "优先本地片段",
    "rule.do_not_repeat": "不重复提示",
    "rule.do_not_extend_dialog": "不延长对话",
    "rule.stop_when_final_tts_starts": "最终 TTS 开始时停止",
    "rule.actionable_repair": "给出可执行修复",
    "rule.no_blame": "不责备用户",
    "rule.one_next_step": "只给下一步",
    "rule.non_blocking_voice": "语音不阻塞",
    "rule.no_direct_ha_action": "不直接控制 HA",
    "error.invalid_expected_json": "期望 JSON 格式不正确。",
    "policy.low_risk_success.title": "低风险成功",
    "policy.low_risk_success.spoken": "好了。",
    "policy.state_query.title": "状态查询",
    "policy.state_query.spoken": "先回答结论，不展开长解释。",
    "policy.clarification.title": "最小澄清",
    "policy.clarification.spoken": "一次只问一个最小澄清问题。",
    "policy.high_risk_confirmation.title": "高风险确认",
    "policy.high_risk_confirmation.spoken": "要操作{target}吗？请确认。",
    "policy.search_summary.title": "搜索摘要",
    "policy.search_summary.spoken": "先说结论，来源和长列表放到屏幕。",
    "policy.error_repair.title": "错误修复",
    "policy.error_repair.spoken": "说明下一步，而不是只说没听懂。",
    "policy.deep_task.title": "深度任务",
    "policy.deep_task.spoken": "我会继续分析，完成后发到 Home Assistant 通知里。",
    "sample.fast-light.name": "普通灯光控制",
    "sample.mid-search.name": "最新信息查询",
    "sample.risk-confirmation.name": "高风险动作确认",
    "earcon.clarification.purpose": "执行前需要补一个缺失信息。",
    "earcon.confirmation.purpose": "高风险动作需要用户显式确认。",
    "earcon.deep_task.purpose": "长推理已交给后台任务继续处理。",
    "earcon.failure.purpose": "请求失败，或助手无法安全继续。",
    "earcon.listening_end.purpose": "语音采集结束，助手正在处理。",
    "earcon.listening_start.purpose": "麦克风已打开，用户可以开始说话。",
    "earcon.processing_loop.purpose": "超过软延迟阈值后低音量循环播放，表示仍在等待 provider。",
    "earcon.provider_fallback.purpose": "主模型 provider 过慢或失败，请求正在切换到备用 provider。",
    "earcon.search.purpose": "正在为当前外部信息使用联网搜索。",
    "earcon.success.purpose": "低风险指令已完成。",
    "earcon.wake.purpose": "唤醒词已确认，助手进入语音流程。",
  },
};

const DEFAULT_DRAFTS = {
  en: {
    user: "Turn on the living room light",
    response: "**Done.** Living room light is on.",
    expected: JSON.stringify(DEFAULT_EXPECTED, null, 2),
  },
  "zh-Hans": {
    user: "打开客厅灯",
    response: "**已打开** 客厅灯。",
    expected: JSON.stringify(DEFAULT_EXPECTED, null, 2),
  },
};

class VoiceHarnessPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._activeTab = "runs";
    /** @type {HarnessStatus | null} */
    this._data = null;
    this._error = "";
    this._busy = false;
    this._result = null;
    this._settingsSaved = "";
    this._draftLocale = this._locale();
    this._draftTouched = false;
    /** @type {ScenarioDraft} */
    this._draft = this._defaultDraft(this._draftLocale);
  }

  set hass(value) {
    this._hass = value;
    const locale = this._locale();
    if (!this._draftTouched && this._draftLocale !== locale) {
      this._draftLocale = locale;
      this._draft = this._defaultDraft(locale);
    }
    if (this.isConnected && !this._data && !this._busy) {
      this._load();
    }
  }

  get hass() {
    return this._hass;
  }

  set panel(value) {
    this._panel = value;
  }

  connectedCallback() {
    this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
    this.shadowRoot.addEventListener("input", (event) => this._onInput(event));
    this.shadowRoot.addEventListener("submit", (event) => this._onSubmit(event));
    this._render();
    this._load();
  }

  async _load() {
    if (!this.hass || this._busy) {
      return;
    }
    this._busy = true;
    this._error = "";
    this._render();
    try {
      this._data = await this._api("GET", "llm_gateway/harness/status");
    } catch (err) {
      this._error = err.message || String(err);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _evaluate(payload) {
    this._busy = true;
    this._error = "";
    this._render();
    try {
      this._result = await this._api("POST", "llm_gateway/harness/evaluate", payload);
    } catch (err) {
      this._error = err.message || String(err);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  /** @param {OptionsUpdateRequest} payload */
  async _saveOptions(payload) {
    this._busy = true;
    this._error = "";
    this._settingsSaved = "";
    this._render();
    try {
      const result = await this._api("POST", "llm_gateway/harness/options", payload);
      if (result.entry && this._data?.entries) {
        this._data = {
          ...this._data,
          entries: this._data.entries.map((entry) =>
            entry.entry_id === result.entry.entry_id ? result.entry : entry
          ),
        };
      }
      this._settingsSaved = this._t("settings.saved");
    } catch (err) {
      this._error = err.message || String(err);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _satelliteAction(action) {
    if (!this.hass?.callService) {
      this._error = this._t("satellite.service_unavailable");
      this._render();
      return;
    }
    this._busy = true;
    this._error = "";
      this._render();
    try {
      if (action === "pause") {
        const minutes = this._satellitePauseMinutes();
        await this.hass.callService("script", "kukui_voice_pause", {
          minutes,
          reason: "voice_harness",
        });
      } else if (action === "resume") {
        await this.hass.callService("script", "kukui_voice_resume", {});
      } else if (action === "save-minutes") {
        const entityId = this._data?.satellite?.states?.pause_minutes?.entity_id;
        const value = this._satellitePauseMinutes();
        if (!entityId) {
          throw new Error(this._t("satellite.unavailable"));
        }
        await this.hass.callService("input_number", "set_value", {
          entity_id: entityId,
          value,
        });
      } else if (action === "save-config" || action === "apply-config") {
        await this._saveSatelliteConfigInputs();
        if (action === "apply-config") {
          await this.hass.callService("script", "kukui_voice_apply_config", {});
        }
      }
    } catch (err) {
      this._error = err.message || String(err);
    } finally {
      this._busy = false;
      await this._load();
    }
  }

  _satellitePauseMinutes() {
    const input = this.shadowRoot.querySelector("[data-satellite-minutes]");
    if (input instanceof HTMLInputElement) {
      return Number(input.value || 30);
    }
    return 30;
  }

  async _saveSatelliteConfigInputs() {
    const states = this._data?.satellite?.states || {};
    const keys = [
      "wake_threshold",
      "wake_trigger_level",
      "wake_refractory_seconds",
      "mic_volume_multiplier",
      "tts_volume_day",
      "tts_volume_night",
      "fallback_clip_volume",
    ];
    const calls = [];
    for (const key of keys) {
      const input = this.shadowRoot.querySelector(`[data-satellite-config="${key}"]`);
      const entityId = states[key]?.entity_id;
      if (!(input instanceof HTMLInputElement) || !entityId) {
        continue;
      }
      calls.push(this.hass.callService("input_number", "set_value", {
        entity_id: entityId,
        value: Number(input.value),
      }));
    }
    if (!calls.length) {
      throw new Error(this._t("satellite.unavailable"));
    }
    await Promise.all(calls);
  }

  async _api(method, path, payload) {
    if (this.hass?.callApi) {
      return this.hass.callApi(method, path, payload);
    }
    const response = await fetch(`/api/${path}`, {
      method,
      credentials: "same-origin",
      headers: payload ? { "Content-Type": "application/json" } : undefined,
      body: payload ? JSON.stringify(payload) : undefined,
    });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    return response.json();
  }

  _onClick(event) {
    const button = event.target.closest("button");
    if (!button) {
      return;
    }
    const tab = button.dataset.tab;
    if (tab) {
      this._activeTab = tab;
      this._render();
      return;
    }
    if (button.dataset.action === "refresh") {
      this._load();
      return;
    }
    if (button.dataset.satelliteAction) {
      this._satelliteAction(button.dataset.satelliteAction);
      return;
    }
    if (button.dataset.earcon) {
      this._playEarcon(button.dataset.earcon);
      return;
    }
    const sampleId = button.dataset.sample;
    if (sampleId) {
      const sample = this._data?.sample_scenarios?.find((item) => item.id === sampleId);
      if (sample) {
        const user = this._sampleUser(sample);
        const response = this._sampleResponse(sample);
        const expected = this._sampleExpected(sample);
        this._draft = {
          user,
          response,
          expected: JSON.stringify(expected, null, 2),
        };
        this._activeTab = "scenarios";
        this._evaluate({
          user,
          response,
          expected,
        });
      }
    }
  }

  _onInput(event) {
    const field = event.target.dataset.field;
    if (!field) {
      return;
    }
    this._draftTouched = true;
    this._draft = { ...this._draft, [field]: event.target.value };
  }

  _onSubmit(event) {
    event.preventDefault();
    const form = event.target;
    if (form.dataset.form === "settings") {
      this._submitSettingsForm(form);
      return;
    }
    if (form.dataset.form !== "scenario") {
      return;
    }
    let expected = {};
    try {
      expected = JSON.parse(this._draft.expected || "{}");
    } catch (err) {
      this._error = this._t("error.invalid_expected_json");
      this._render();
      return;
    }
    this._evaluate({
      user: this._draft.user,
      response: this._draft.response,
      expected,
    });
  }

  /** @param {HTMLFormElement} form */
  _submitSettingsForm(form) {
    const data = new FormData(form);
    const numberValue = (name) => Number(data.get(name) || 0);
    this._saveOptions({
      entry_id: form.dataset.entryId || "",
      options: {
        routing_mode: this._routeKind(data.get("routing_mode")),
        models: {
          fast: String(data.get("fast_model") || ""),
          mid: String(data.get("mid_model") || ""),
          deep: String(data.get("deep_model") || ""),
        },
        max_tokens: {
          fast: numberValue("fast_max_tokens"),
          mid: numberValue("mid_max_tokens"),
          deep: numberValue("deep_max_tokens"),
        },
        timeouts: {
          fast: numberValue("fast_timeout"),
          mid: numberValue("mid_timeout"),
          deep: numberValue("deep_timeout"),
        },
        trace: {
          enabled: data.get("diagnostic_traces") === "on",
          include_raw_messages: data.get("trace_include_raw_messages") === "on",
          max_runs: numberValue("trace_max_runs"),
          retention_hours: numberValue("trace_retention_hours"),
        },
        first_response_audio: {
          enabled: data.get("first_response_audio_enabled") === "on",
          adapter: this._firstResponseAdapter(data.get("first_response_adapter")),
          local_service: String(data.get("first_response_local_service") || "").trim(),
          tts_entity: String(data.get("first_response_tts_entity") || "").trim(),
          media_player_entity: String(data.get("first_response_media_player") || "").trim(),
        },
      },
    });
  }

  _playEarcon(name) {
    const file = this._data?.earcons?.files?.[name];
    if (!file?.url) {
      return;
    }
    const audio = new Audio(file.url);
    audio.play().catch((err) => {
      this._error = err.message || String(err);
      this._render();
    });
  }

  _render() {
    const entries = this._data?.entries || [];
    this.shadowRoot.innerHTML = `
      <style>${styles}</style>
      <main class="shell">
        <header class="topbar">
          <div>
            <h1>${escapeHtml(this._t("app.title"))}</h1>
            <div class="subline">${escapeHtml(this._statusLine(entries))}</div>
          </div>
          <button class="iconButton" data-action="refresh" title="${escapeHtml(this._t("common.refresh"))}">
            <ha-icon icon="mdi:refresh"></ha-icon>
          </button>
        </header>
        ${this._error ? `<div class="banner error">${escapeHtml(this._error)}</div>` : ""}
        <nav class="tabs" aria-label="${escapeHtml(this._t("aria.views"))}">
          ${TABS.map(([id, labelKey, icon]) => `
            <button class="tab ${this._activeTab === id ? "active" : ""}" data-tab="${id}">
              <ha-icon icon="${icon}"></ha-icon>
              <span>${escapeHtml(this._t(labelKey))}</span>
            </button>
          `).join("")}
        </nav>
        <section class="content">
          ${this._busy && !this._data ? this._renderLoading() : this._renderActive(entries)}
        </section>
      </main>
    `;
  }

  _statusLine(entries) {
    if (!this._data) {
      return this._busy ? this._t("status.loading") : this._t("status.waiting");
    }
    if (!entries.length) {
      return this._t("status.no_entries");
    }
    return this._t("status.entries", { count: entries.length });
  }

  _renderActive(entries) {
    if (!this._data) {
      return this._renderLoading();
    }
    if (this._activeTab === "runs") {
      return this._renderRuns(entries);
    }
    if (this._activeTab === "settings") {
      return this._renderSettings(entries);
    }
    if (this._activeTab === "satellite") {
      return this._renderSatellite();
    }
    if (this._activeTab === "policies") {
      return this._renderPolicies(entries);
    }
    if (this._activeTab === "scenarios") {
      return this._renderScenarioLab();
    }
    if (this._activeTab === "search") {
      return this._renderSearch(entries);
    }
    if (this._activeTab === "memory") {
      return this._renderMemory(entries);
    }
    if (this._activeTab === "earcons") {
      return this._renderEarcons();
    }
    return this._renderRegression();
  }

  _renderLoading() {
    return `
      <div class="grid">
        <div class="surface skeleton"></div>
        <div class="surface skeleton"></div>
        <div class="surface skeleton wide"></div>
      </div>
    `;
  }

  _renderRuns(entries) {
    if (!entries.length) {
      return `<div class="empty">${escapeHtml(this._t("runs.empty"))}</div>`;
    }
    return `
      <div class="entryGrid">
        ${entries.map((entry) => `
          <article class="surface entry">
            <div class="sectionHead">
              <div>
                <h2>${escapeHtml(entry.title)}</h2>
                <div class="meta">${escapeHtml(entry.base_url || this._t("entry.base_url_missing"))}</div>
              </div>
              <span class="chip ok">${escapeHtml(entry.state || "unknown")}</span>
            </div>
            <div class="routeGrid">
              ${(entry.routes || []).map((route) => this._routeCard(route)).join("")}
            </div>
            ${this._providerPanel(entry)}
            ${this._liveStatusBanner(entry)}
            ${this._renderTracePanel(entry)}
          </article>
        `).join("")}
      </div>
    `;
  }

  _liveStatusBanner(entry) {
    const event = entry.feedback?.latest_display;
    if (!event) {
      return `<div class="empty mini">${escapeHtml(this._t("runs.no_live_status"))}</div>`;
    }
    return `
      <div class="liveStatus ${escapeHtml(event.state || "")}">
        <div>
          <strong>${escapeHtml(this._t("runs.live_status"))}: ${escapeHtml(event.title || event.state || "")}</strong>
          <span>${escapeHtml(event.short_text || "")}</span>
          <span>${escapeHtml(event.turn_id || "")}</span>
        </div>
        <div class="summaryChips">
          <span class="chip muted">${escapeHtml(event.progress || "none")}</span>
          <span class="chip muted">${escapeHtml(this._t("runs.privacy"))}: ${escapeHtml(event.privacy_level || "")}</span>
          ${(event.action_buttons || []).length ? `<span class="chip warning">${escapeHtml(this._t("runs.actions_available"))}: ${escapeHtml((event.action_buttons || []).join(", "))}</span>` : ""}
        </div>
      </div>
    `;
  }

  _renderSettings(entries) {
    if (!entries.length) {
      return `<div class="empty">${escapeHtml(this._t("settings.empty"))}</div>`;
    }
    return `
      <div class="settingsGrid">
        ${this._settingsSaved ? `<div class="banner success">${escapeHtml(this._settingsSaved)}</div>` : ""}
        ${entries.map((entry) => this._settingsForm(entry)).join("")}
      </div>
    `;
  }

  _settingsForm(entry) {
    const options = entry.options || {};
    const trace = entry.trace || {};
    const editable = this._data?.editable || DEFAULT_EDITABLE;
    const tokenRange = editable.max_tokens || { min: 1, max: 16384 };
    const timeoutRange = editable.timeouts || { min: 5, max: 300 };
    const traceRunsRange = editable.trace_max_runs || { min: 1, max: 200 };
    const traceHoursRange = editable.trace_retention_hours || { min: 1, max: 168 };
    const routingModes = editable.routing_modes || ["auto", "fast", "mid", "deep"];
    const audioOptions = options.first_response_audio || {};
    const audioStatus = entry.first_response_audio || {};
    const playbackAdapters = editable.first_response_playback_adapters || ["local", "ha_media_player", "auto"];
    const formId = safeId(entry.entry_id);
    const localServices = audioStatus.candidates?.local_services || [];
    const ttsCandidates = audioStatus.candidates?.tts || [];
    const mediaCandidates = audioStatus.candidates?.media_player || [];
    return `
      <form class="surface settingsForm" data-form="settings" data-entry-id="${escapeHtml(entry.entry_id)}">
        <div class="sectionHead">
          <div>
            <h2>${escapeHtml(this._t("settings.title"))}</h2>
            <div class="meta">${escapeHtml(entry.title)} · ${escapeHtml(entry.base_url || this._t("entry.base_url_missing"))}</div>
          </div>
          <button class="primary" type="submit" ${this._busy ? "disabled" : ""}>
            <ha-icon icon="mdi:content-save-outline"></ha-icon>
            <span>${escapeHtml(this._t("common.save"))}</span>
          </button>
        </div>
        <p class="settingsNote">${escapeHtml(this._t("settings.description"))}</p>
        <fieldset>
          <legend>${escapeHtml(this._t("settings.routing"))}</legend>
          <label>
            <span>${escapeHtml(this._t("settings.routing_mode"))}</span>
            <select name="routing_mode">
              ${routingModes.map((mode) => `
                <option value="${escapeHtml(mode)}" ${options.routing_mode === mode ? "selected" : ""}>
                  ${escapeHtml(this._modeLabel(mode))}
                </option>
              `).join("")}
            </select>
          </label>
        </fieldset>
        <fieldset>
          <legend>${escapeHtml(this._t("settings.models"))}</legend>
          ${["fast", "mid", "deep"].map((tier) => `
            <label>
              <span>${escapeHtml(this._t("settings.model", { tier: this._tierLabel(tier) }))}</span>
              <input name="${tier}_model" value="${escapeHtml(options.models?.[tier] || "")}" autocomplete="off" required maxlength="256">
            </label>
          `).join("")}
        </fieldset>
        <fieldset>
          <legend>${escapeHtml(this._t("settings.budgets"))}</legend>
          <div class="settingsTriples">
            ${["fast", "mid", "deep"].map((tier) => `
              <label>
                <span>${escapeHtml(this._t("settings.max_tokens", { tier: this._tierLabel(tier) }))}</span>
                <input name="${tier}_max_tokens" type="number" min="${tokenRange.min}" max="${tokenRange.max}" step="1" value="${Number(options.max_tokens?.[tier] || 0)}" required>
              </label>
              <label>
                <span>${escapeHtml(this._t("settings.timeout", { tier: this._tierLabel(tier) }))}</span>
                <input name="${tier}_timeout" type="number" min="${timeoutRange.min}" max="${timeoutRange.max}" step="1" value="${Number(options.timeouts?.[tier] || 0)}" required>
              </label>
            `).join("")}
          </div>
        </fieldset>
        <fieldset>
          <legend>${escapeHtml(this._t("settings.first_response_audio"))}</legend>
          <label class="checkRow">
            <input name="first_response_audio_enabled" type="checkbox" ${audioOptions.enabled !== false ? "checked" : ""}>
            <span>${escapeHtml(this._t("settings.first_response_audio_enabled"))}</span>
          </label>
          <label>
            <span>${escapeHtml(this._t("settings.first_response_adapter"))}</span>
            <select name="first_response_adapter">
              ${playbackAdapters.map((adapter) => `
                <option value="${escapeHtml(adapter)}" ${this._firstResponseAdapter(audioOptions.adapter) === adapter ? "selected" : ""}>
                  ${escapeHtml(this._adapterLabel(adapter))}
                </option>
              `).join("")}
            </select>
          </label>
          ${this._audioRoutePanel(audioStatus, entry.feedback_policy || {})}
          <label>
            <span>${escapeHtml(this._t("settings.first_response_local_service"))}</span>
            <input
              name="first_response_local_service"
              value="${escapeHtml(audioOptions.local_service || "")}"
              list="local-services-${formId}"
              autocomplete="off"
              placeholder="rest_command.kukui_voice_feedback"
              maxlength="256"
            >
            <small>${escapeHtml(this._t("settings.first_response_local_service_hint"))}</small>
          </label>
          <datalist id="local-services-${formId}">
            ${localServices.map((item) => `<option value="${escapeHtml(item.service || "")}"></option>`).join("")}
          </datalist>
          <div class="settingsNote">${escapeHtml(this._t("settings.ha_fallback_notice"))}</div>
          <div class="settingsTriples two">
            <label>
              <span>${escapeHtml(this._t("settings.first_response_tts_entity"))}</span>
              <input name="first_response_tts_entity" value="${escapeHtml(audioOptions.tts_entity || "")}" list="tts-candidates-${formId}" autocomplete="off" maxlength="256">
            </label>
            <label>
              <span>${escapeHtml(this._t("settings.first_response_media_player"))}</span>
              <input name="first_response_media_player" value="${escapeHtml(audioOptions.media_player_entity || "")}" list="media-player-candidates-${formId}" autocomplete="off" maxlength="256">
            </label>
          </div>
          <datalist id="tts-candidates-${formId}">
            ${ttsCandidates.map((item) => `<option value="${escapeHtml(item.entity_id || "")}"></option>`).join("")}
          </datalist>
          <datalist id="media-player-candidates-${formId}">
            ${mediaCandidates.map((item) => `<option value="${escapeHtml(item.entity_id || "")}"></option>`).join("")}
          </datalist>
          ${this._audioCandidatePanel(audioStatus)}
        </fieldset>
        <fieldset>
          <legend>${escapeHtml(this._t("settings.traces"))}</legend>
          <label class="checkRow">
            <input name="diagnostic_traces" type="checkbox" ${trace.enabled ? "checked" : ""}>
            <span>${escapeHtml(this._t("settings.diagnostic_traces"))}</span>
          </label>
          <label class="checkRow">
            <input name="trace_include_raw_messages" type="checkbox" ${trace.include_raw_messages ? "checked" : ""}>
            <span>${escapeHtml(this._t("settings.include_raw"))}</span>
          </label>
          <div class="settingsTriples two">
            <label>
              <span>${escapeHtml(this._t("settings.max_runs"))}</span>
              <input name="trace_max_runs" type="number" min="${traceRunsRange.min}" max="${traceRunsRange.max}" step="1" value="${Number(trace.max_runs || 0)}" required>
            </label>
            <label>
              <span>${escapeHtml(this._t("settings.retention_hours"))}</span>
              <input name="trace_retention_hours" type="number" min="${traceHoursRange.min}" max="${traceHoursRange.max}" step="1" value="${Number(trace.retention_hours || 0)}" required>
            </label>
          </div>
        </fieldset>
      </form>
    `;
  }

  _audioRoutePanel(audioStatus, feedbackPolicy) {
    const route = audioStatus.route || {};
    const adapter = route.adapter || audioStatus.adapter || "local";
    const canPlay = Boolean(audioStatus.enabled !== false && audioStatus.can_play);
    const quiet = feedbackPolicy.quiet_hours || {};
    const routeTone = canPlay ? "ok" : "bad";
    const missingLocal = adapter === "local" && !canPlay;
    return `
      <div class="audioRoute">
        <div class="sectionHead compact">
          <div>
            <strong>${escapeHtml(this._t("settings.audio_route"))}</strong>
            <span>${escapeHtml(this._adapterLabel(adapter))}</span>
          </div>
          <span class="chip ${routeTone}">${escapeHtml(canPlay ? "ready" : "missing")}</span>
        </div>
        <div class="summaryChips">
          <span class="chip muted">backend: ${escapeHtml(route.backend || "none")}</span>
          <span class="chip muted">reason: ${escapeHtml(route.reason || "")}</span>
          ${route.local_service ? `<span class="chip ok">${escapeHtml(route.local_service)}</span>` : ""}
          ${quiet.active ? `<span class="chip warning">quiet hours · ${Number(quiet.current_local_hour ?? 0)}:00</span>` : `<span class="chip muted">local hour · ${Number(quiet.current_local_hour ?? 0)}:00</span>`}
        </div>
        ${missingLocal ? `<div class="banner error">${escapeHtml(this._t("settings.local_adapter_missing"))}</div>` : ""}
      </div>
    `;
  }

  _audioCandidatePanel(audioStatus) {
    const candidates = audioStatus.candidates || {};
    return `
      <details class="jsonBlock">
        <summary>${escapeHtml(this._t("settings.audio_candidates"))}</summary>
        <div class="candidateGrid">
          ${this._audioCandidateList("Local services", candidates.local_services || [], "service")}
          ${this._audioCandidateList("TTS", candidates.tts || [], "entity_id")}
          ${this._audioCandidateList("media_player", candidates.media_player || [], "entity_id")}
        </div>
      </details>
    `;
  }

  _audioCandidateList(title, items, key) {
    if (!items.length) {
      return `
        <div class="candidateList">
          <strong>${escapeHtml(title)}</strong>
          <span class="meta">-</span>
        </div>
      `;
    }
    return `
      <div class="candidateList">
        <strong>${escapeHtml(title)}</strong>
        ${items.slice(0, 8).map((item) => `
          <div class="candidateItem">
            <span>${escapeHtml(item[key] || "")}</span>
            <span class="chip ${item.available || item.usable ? "ok" : "muted"}">${escapeHtml(item.available || item.usable ? "usable" : "off")}</span>
            ${item.preferred ? `<span class="chip warning">preferred</span>` : ""}
          </div>
        `).join("")}
      </div>
    `;
  }

  _renderSatellite() {
    const satellite = this._data?.satellite || {};
    const states = satellite.states || {};
    const services = satellite.services || {};
    const pauseMinutes = Number(states.pause_minutes?.state || 30);
    const stateKeys = [
      "voice_pipeline",
      "voice_paused",
      "pause_requested",
      "display_awake",
      "voice_config",
      "asr_metrics",
      "ambient_light",
      "screen_brightness",
    ];
    const configKeys = [
      ["wake_threshold", 0.1, 0.95, 0.01],
      ["wake_trigger_level", 1, 5, 1],
      ["wake_refractory_seconds", 1, 30, 1],
      ["mic_volume_multiplier", 1, 12, 0.1],
      ["tts_volume_day", 0.2, 1.25, 0.01],
      ["tts_volume_night", 0.2, 1.25, 0.01],
      ["fallback_clip_volume", 0.2, 1.25, 0.01],
    ];
    return `
      <div class="satelliteGrid">
        <article class="surface satellitePanel">
          <div class="sectionHead">
            <div>
              <h2>${escapeHtml(this._t("satellite.title"))}</h2>
              <div class="meta">${escapeHtml(this._t("satellite.description"))}</div>
            </div>
          </div>
          <div class="satelliteControls">
            <label>
              <span>${escapeHtml(this._t("satellite.minutes"))}</span>
              <input data-satellite-minutes type="number" min="1" max="120" step="1" value="${pauseMinutes}">
            </label>
            <button type="button" data-satellite-action="save-minutes" ${services.set_pause_minutes ? "" : "disabled"}>
              <ha-icon icon="mdi:content-save-outline"></ha-icon>
              <span>${escapeHtml(this._t("satellite.save_minutes"))}</span>
            </button>
            <button type="button" data-satellite-action="pause" ${services.pause ? "" : "disabled"}>
              <ha-icon icon="mdi:microphone-off"></ha-icon>
              <span>${escapeHtml(this._t("satellite.pause"))}</span>
            </button>
            <button type="button" data-satellite-action="resume" ${services.resume ? "" : "disabled"}>
              <ha-icon icon="mdi:microphone"></ha-icon>
              <span>${escapeHtml(this._t("satellite.resume"))}</span>
            </button>
          </div>
          <h3>${escapeHtml(this._t("satellite.config"))}</h3>
          <div class="settingsTriples">
            ${configKeys.map(([key, min, max, step]) => this._satelliteConfigInput(key, states[key], min, max, step)).join("")}
          </div>
          <div class="satelliteControls compact">
            <button type="button" data-satellite-action="save-config" ${services.set_number ? "" : "disabled"}>
              <ha-icon icon="mdi:content-save-outline"></ha-icon>
              <span>${escapeHtml(this._t("satellite.save_config"))}</span>
            </button>
            <button type="button" data-satellite-action="apply-config" ${services.set_number && services.apply_config ? "" : "disabled"}>
              <ha-icon icon="mdi:check-circle-outline"></ha-icon>
              <span>${escapeHtml(this._t("satellite.apply_config"))}</span>
            </button>
          </div>
          <div class="stateList">
            ${stateKeys.map((key) => this._satelliteStateRow(key, states[key])).join("")}
          </div>
        </article>
      </div>
    `;
  }

  _satelliteConfigInput(key, state, min, max, step) {
    const available = Boolean(state?.available);
    const value = Number(state?.state || min);
    return `
      <label>
        <span>${escapeHtml(this._t(`satellite.${key}`))}</span>
        <input
          data-satellite-config="${escapeHtml(key)}"
          type="number"
          min="${Number(min)}"
          max="${Number(max)}"
          step="${Number(step)}"
          value="${Number.isFinite(value) ? value : Number(min)}"
          ${available ? "" : "disabled"}
        >
      </label>
    `;
  }

  _satelliteStateRow(key, state) {
    const available = Boolean(state?.available);
    const value = available
      ? `${state.state}${state.unit ? ` ${state.unit}` : ""}`
      : this._t("satellite.missing");
    return `
      <div class="stateRow">
        <div>
          <strong>${escapeHtml(this._t(`satellite.${key}`))}</strong>
          <span>${escapeHtml(state?.entity_id || "")}</span>
        </div>
        <span class="chip ${available ? "ok" : "error"}">${escapeHtml(value)}</span>
      </div>
    `;
  }

  _renderTracePanel(entry) {
    const trace = entry.trace || {};
    const records = entry.traces?.records || [];
    const liveRuns = Array.isArray(entry.voice_runs) ? entry.voice_runs : [];
    const storage = entry.traces?.storage || {};
    return `
      <section class="tracePanel">
        <div class="traceHeader">
          <div>
            <h2>${escapeHtml(trace.enabled ? this._t("runs.trace_enabled") : this._t("runs.trace_disabled"))}</h2>
            <div class="meta">${escapeHtml(this._t("runs.retention", {
              count: trace.max_runs || 0,
              hours: trace.retention_hours || 0,
            }))} · ${escapeHtml(trace.include_raw_messages ? this._t("runs.raw_enabled") : this._t("runs.raw_disabled"))}</div>
          </div>
          <span class="chip muted">${escapeHtml(this._t("runs.storage", {
            records: storage.records || 0,
            bytes: storage.compressed_bytes || 0,
          }))}</span>
        </div>
        <div class="traceList">
          ${records.map((record) => this._traceCard(record)).join("") || `<div class="empty mini">${escapeHtml(this._t("runs.trace_empty"))}</div>`}
        </div>
        <h3>${escapeHtml(this._t("runs.live"))}</h3>
        <div class="traceList">
          ${liveRuns.map((run) => this._liveRunCard(run)).join("") || `<div class="empty mini">${escapeHtml(this._t("runs.live_empty"))}</div>`}
        </div>
      </section>
    `;
  }

  _liveRunCard(run) {
    const timeline = Array.isArray(run.events) ? run.events : [];
    const duration = Number(run.running_duration_ms || 0);
    const lastStage = run.last_active_stage || (timeline.length ? timeline[timeline.length - 1].stage : "");
    const isRunning = run.status === "running";
    return `
      <details class="traceCard">
        <summary>
          <div>
            <strong>${escapeHtml(this._formatTime(Number(run.created_at || 0) * 1000))}</strong>
            <span>${escapeHtml(run.conversation_id || run.id || "")}</span>
            <span>${escapeHtml(run.user_text || "")}</span>
            <span>${escapeHtml(`${this._t("runs.active_stage")}: ${lastStage || "-"}`)}</span>
          </div>
          <span class="chip ${run.status === "error" ? "bad" : (isRunning ? "warning" : "ok")}">${escapeHtml(run.status || "")}</span>
        </summary>
        <div class="traceBody">
          <div class="traceText">
            <strong>${escapeHtml(this._t("runs.user"))}</strong>
            <p>${escapeHtml(run.user_text || "")}</p>
          </div>
          <div class="meterRow">
            <span>${escapeHtml(this._routeLabel(run.route))}</span>
            <span>${escapeHtml(run.provider || "")}</span>
            <span>${escapeHtml(this._t("runs.active_stage"))}: ${escapeHtml(lastStage || "-")}</span>
            <span>${escapeHtml(this._t(isRunning ? "runs.running_duration" : "runs.completion"))}: ${duration} ms</span>
          </div>
          <div class="attemptList timelineList">
            ${timeline.map((event) => `
              <div class="attempt ${event.status === "error" ? "bad" : "ok"}">
                <strong>${escapeHtml(event.stage || "")}</strong>
                <span>${Number(event.t_ms || 0)} ms</span>
                ${event.attrs ? `<span>${escapeHtml(JSON.stringify(event.attrs))}</span>` : ""}
              </div>
            `).join("")}
          </div>
        </div>
      </details>
    `;
  }

  _traceCard(record) {
    const rawMeta = record.raw_payload_meta || {};
    const route = record.route || {};
    const provider = route.provider || {};
    const attempts = Array.isArray(route.provider_attempts) ? route.provider_attempts : [];
    const timeline = Array.isArray(record.timeline_spans) && record.timeline_spans.length
      ? record.timeline_spans
      : (Array.isArray(record.timeline) ? record.timeline.map((event) => ({
          stage: event.stage,
          start_ms: event.t_ms,
          duration_ms: 0,
          status: event.status,
          attrs: event.attrs,
        })) : []);
    const flags = record.debug_flags || {};
    const tools = Array.isArray(record.tools) ? record.tools : [];
    const errors = Array.isArray(record.errors) ? record.errors : [];
    const input = record.input || {};
    const firstResponse = record.first_response_decision || {};
    const searchGate = record.search_gate || {};
    const completion = record.completion || {};
    const speech = record.speech || {};
    return `
      <details class="traceCard">
        <summary>
          <div>
            <strong>${escapeHtml(this._formatTime(record.created_at))}</strong>
            <span>${escapeHtml(record.user_text || "")}</span>
            <span>${escapeHtml(record.first_response_text || firstResponse.spoken_hint || firstResponse.task_type || "")}</span>
            <span>${escapeHtml(record.final_speech_text || record.assistant_text || "")}</span>
            <span>${escapeHtml(`${this._routeLabel(route.kind)} · ${route.model || ""} · ${Number(record.latency_ms || 0)} ms`)}</span>
            <span>${escapeHtml(`${firstResponse.task_type || ""} · ${searchGate.decision || ""}`)}</span>
          </div>
          <div class="summaryChips">
            ${this._runFlagChips(record)}
            <span class="chip ${record.status === "error" ? "bad" : "ok"}">${escapeHtml(this._traceStatusLabel(record.status))}</span>
          </div>
        </summary>
        <div class="traceBody">
          <h3>${escapeHtml(this._t("runs.detail"))}</h3>
          <div class="runFlags">
            ${this._flagChip(this._t("runs.search"), Boolean(flags.search), Boolean(flags.search) ? "warning" : "muted")}
            ${this._flagChip(this._t("runs.deep_model"), Boolean(flags.deep_route), Boolean(flags.deep_route) ? "warning" : "muted")}
            ${this._flagChip(this._t("runs.deep_verifier"), Boolean(flags.deep_verifier_waited), Boolean(flags.deep_verifier_waited) ? "bad" : "muted")}
            ${this._flagChip(this._t("runs.high_risk"), Boolean(flags.high_risk), Boolean(flags.high_risk) ? "bad" : "muted")}
            ${this._flagChip(this._t("runs.final_modified"), Boolean(flags.final_modified_by_grounding), Boolean(flags.final_modified_by_grounding) ? "warning" : "muted")}
            ${this._flagChip(this._t("runs.polluted_evidence"), Boolean(flags.polluted_evidence_present), Boolean(flags.polluted_evidence_used) ? "bad" : (flags.polluted_evidence_present ? "warning" : "muted"))}
            <span class="chip muted">${escapeHtml(this._t("runs.verifier_mode"))}: ${escapeHtml(this._verifierModeLabel(record.verifier_mode))}</span>
          </div>
          <div class="detailGrid">
            ${this._detailItem(this._t("runs.input"), [
              input.text || record.user_text || "",
              input.conversation_id || record.conversation_id || "",
            ])}
            ${this._detailItem(this._t("runs.route"), [
              `${this._routeLabel(route.kind)} · ${route.model || ""}`,
              provider.name ? `${this._t("runs.provider")}: ${provider.name}` : "",
            ])}
            ${this._detailItem(this._t("runs.first_response"), [
              firstResponse.task_type || "",
              record.first_response_text || firstResponse.spoken_hint || "",
              firstResponse.reason || "",
              firstResponse.spoken_hint || "",
            ])}
            ${this._detailItem(this._t("runs.search_gate"), [
              searchGate.decision || "",
              searchGate.reason || "",
              searchGate.searched === true ? "searched=true" : "searched=false",
            ])}
            ${this._detailItem(this._t("runs.completion"), [
              completion.complete === false ? "running" : (completion.status || record.status || ""),
              completion.last_active_stage ? `${this._t("runs.active_stage")}: ${completion.last_active_stage}` : "",
              completion.running_duration_ms ? `${this._t("runs.running_duration")}: ${Number(completion.running_duration_ms)} ms` : "",
            ])}
            ${this._detailItem(this._t("runs.final_speech"), [
              speech.final || record.final_speech_text || record.assistant_text || "",
              `${Number(record.latency_ms || 0)} ms`,
            ])}
          </div>
          ${this._firstResponsePanel(firstResponse, record.first_response_audio || {})}
          ${this._inventoryPanel(record)}
          <div class="traceText">
            <strong>${escapeHtml(this._t("runs.user"))}</strong>
            <p>${escapeHtml(record.user_text || "")}</p>
            <strong>${escapeHtml(this._t("runs.assistant"))}</strong>
            <p>${escapeHtml(record.assistant_text || "")}</p>
          </div>
          <div class="meterRow">
            <span>${escapeHtml(this._routeLabel(route.kind))}</span>
            <span>${escapeHtml(route.model || "")}</span>
            ${provider.name ? `<span>${escapeHtml(this._t("runs.provider"))}: ${escapeHtml(provider.name)}${provider.fallback_used ? " ↳" : ""}</span>` : ""}
            <span>${Number(record.latency_ms || 0)} ms</span>
            <span>${escapeHtml(this._t("runs.tools", { count: (record.tools || []).length }))}</span>
            ${rawMeta.compressed_bytes ? `<span>${rawMeta.compressed_bytes}/${rawMeta.uncompressed_bytes} B</span>` : ""}
          </div>
          ${this._weatherPathPanel(record)}
          ${this._toolIterationsPanel(record)}
          ${this._duplicateSuppressionsPanel(record)}
          ${this._criticalPathPanel(record)}
          ${this._searchDebugPanel(record)}
          ${this._actionsPanel(record)}
          ${this._earconEventsPanel(record)}
          ${this._displayStatusPanel(record)}
          ${this._errorsPanel(errors)}
          ${this._toolEventsPanel(tools)}
          ${this._groundingPanel(record)}
          ${this._evidencePanel(record)}
          ${attempts.length ? `
            <h3>${escapeHtml(this._t("runs.provider_attempts"))}</h3>
            <div class="attemptList">
              ${attempts.map((attempt) => `
                <div class="attempt ${attempt.status === "complete" ? "ok" : "bad"}">
                  <strong>${escapeHtml(attempt.provider || "")}</strong>
                  <span>${escapeHtml(attempt.model || "")}</span>
                  <span>${escapeHtml(attempt.status || "")} · ${Number(attempt.latency_ms || 0)} ms</span>
                  ${attempt.error ? `<span>${escapeHtml(attempt.error)}</span>` : ""}
                </div>
              `).join("")}
            </div>
          ` : ""}
          ${timeline.length ? `
            <h3>${escapeHtml(this._t("runs.timeline"))}</h3>
            <div class="attemptList timelineList">
              ${timeline.map((event) => `
                <div class="attempt ${event.status === "error" ? "bad" : "ok"}">
                  <strong>${escapeHtml(event.stage || "")}</strong>
                  <span>${Number(event.start_ms ?? event.t_ms ?? 0)} ms</span>
                  <span>${Number(event.duration_ms || 0)} ms</span>
                  ${event.attrs ? `<span>${escapeHtml(JSON.stringify(event.attrs))}</span>` : ""}
                </div>
              `).join("")}
            </div>
          ` : ""}
          ${record.raw_payload ? this._jsonDetails(this._t("runs.raw_payload"), record.raw_payload) : `<div class="empty mini">${escapeHtml(this._t("runs.no_raw"))}</div>`}
        </div>
      </details>
    `;
  }

  _runFlagChips(record) {
    const flags = record.debug_flags || {};
    return [
      this._flagChip("S", Boolean(flags.search), Boolean(flags.search) ? "warning" : "muted", this._t("runs.search")),
      this._flagChip("D", Boolean(flags.deep_route), Boolean(flags.deep_route) ? "warning" : "muted", this._t("runs.deep_model")),
      this._flagChip("V", Boolean(flags.deep_verifier_waited), Boolean(flags.deep_verifier_waited) ? "bad" : "muted", this._t("runs.deep_verifier")),
      this._flagChip("R", Boolean(flags.high_risk), Boolean(flags.high_risk) ? "bad" : "muted", this._t("runs.high_risk")),
      this._flagChip("G", Boolean(flags.final_modified_by_grounding), Boolean(flags.final_modified_by_grounding) ? "warning" : "muted", this._t("runs.final_modified")),
      this._flagChip("E", Boolean(flags.polluted_evidence_present), Boolean(flags.polluted_evidence_used) ? "bad" : (flags.polluted_evidence_present ? "warning" : "muted"), this._t("runs.polluted_evidence")),
    ].join("");
  }

  _flagChip(label, enabled, tone = "muted", title = "") {
    const state = enabled ? this._t("common.enabled") : this._t("common.disabled");
    return `<span class="chip ${tone}" title="${escapeHtml(title || label)}">${escapeHtml(label)}: ${escapeHtml(state)}</span>`;
  }

  _detailItem(label, lines) {
    const visible = (Array.isArray(lines) ? lines : []).filter((line) => String(line || "").trim());
    return `
      <div class="detailItem">
        <strong>${escapeHtml(label)}</strong>
        ${visible.map((line) => `<span>${escapeHtml(line)}</span>`).join("") || `<span class="meta">-</span>`}
      </div>
    `;
  }

  _firstResponsePanel(decision, audio = {}) {
    const keys = [...Object.keys(decision || {}), ...Object.keys(audio || {})];
    if (!keys.length) {
      return `<div class="empty mini">${escapeHtml(this._t("runs.first_response_detail"))}: -</div>`;
    }
    const deadline = Number(decision.deadline_ms || 0);
    const triggered = Number(decision.triggered_ms || decision.actual_ms || 0);
    const inTarget = deadline > 0 && triggered > 0 ? triggered <= deadline : null;
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.first_response_detail"))}</h3>
        <div class="detailGrid">
          ${this._detailItem(this._t("runs.first_response"), [
            decision.task_type || "",
            decision.cue || "",
            decision.spoken_hint || decision.text || decision.earcon || "",
          ])}
          ${this._detailItem(this._t("runs.timing"), [
            deadline ? `${deadline} ms deadline` : "",
            triggered ? `${triggered} ms actual` : "",
            inTarget === null ? "" : this._t(inTarget ? "runs.within_target" : "runs.missed_target"),
          ])}
          ${this._detailItem(this._t("runs.reason"), [
            decision.reason || "",
            decision.selection_reason || "",
          ])}
          ${this._detailItem(this._t("runs.first_response_audio"), [
            audio.scheduled ? "scheduled" : "not scheduled",
            audio.played ? `played · ${Number(audio.played_at_ms || 0)} ms` : "not played",
            audio.source || "",
            audio.backend || "",
            audio.tts_entity ? `tts=${audio.tts_entity}` : "",
            audio.media_player_entity ? `media=${audio.media_player_entity}` : "",
            audio.selection_reason || "",
            audio.suppressed_reason || "",
          ])}
        </div>
        ${this._jsonDetails(this._t("runs.first_response_detail"), decision)}
        ${this._jsonDetails(this._t("runs.first_response_audio"), audio)}
      </div>
    `;
  }

  _inventoryPanel(record) {
    const attrs = this._inventoryAttrs(record);
    if (!attrs) {
      return "";
    }
    const areas = Array.isArray(attrs.areas) ? attrs.areas : [];
    const domains = Array.isArray(attrs.domains) ? attrs.domains : [];
    const entities = Array.isArray(attrs.entities) ? attrs.entities : [];
    const tools = Array.isArray(attrs.tools_used) ? attrs.tools_used : [];
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.inventory"))}</h3>
        <div class="detailGrid">
          ${this._detailItem(this._t("runs.route"), [
            attrs.task_type || "",
            attrs.source || "",
          ])}
          ${this._detailItem(this._t("runs.inventory_scope"), [
            attrs.area ? `area=${attrs.area}` : "",
            attrs.domain ? `domain=${attrs.domain}` : "",
            attrs.capability ? `capability=${attrs.capability}` : "",
            `entities=${Number(attrs.entity_count || entities.length || 0)}`,
          ])}
          ${this._detailItem(this._t("runs.inventory_execution"), [
            `llm_used=${Boolean(attrs.llm_used)}`,
            `tools_used=${tools.length ? tools.join(", ") : "[]"}`,
          ])}
          ${this._detailItem("Areas / domains", [
            areas.length ? areas.join(", ") : "",
            domains.length ? domains.join(", ") : "",
          ])}
        </div>
        ${entities.length ? `
          <details class="jsonDetails">
            <summary>${escapeHtml(this._t("runs.inventory_entities"))}</summary>
            <div class="attemptList compact">
              ${entities.map((entity) => `
                <div class="attempt compactAttempt">
                  <strong>${escapeHtml(entity.name || "")}</strong>
                  <span>${escapeHtml(entity.domain || "")}</span>
                  <span>${escapeHtml(Array.isArray(entity.areas) ? entity.areas.join(", ") : "")}</span>
                  <span>${escapeHtml(entity.can_control ? "control" : "read")}</span>
                </div>
              `).join("")}
            </div>
          </details>
        ` : ""}
        ${this._jsonDetails(this._t("runs.inventory"), attrs)}
      </div>
    `;
  }

  _inventoryAttrs(record) {
    const rawTimeline = Array.isArray(record.timeline) ? record.timeline : [];
    const rawEvent = rawTimeline.find((event) => event?.stage === "local_inventory_render");
    if (rawEvent?.attrs && typeof rawEvent.attrs === "object") {
      return rawEvent.attrs;
    }
    const spans = Array.isArray(record.timeline_spans) ? record.timeline_spans : [];
    const span = spans.find((event) => event?.stage === "local_inventory_render");
    return span?.attrs && typeof span.attrs === "object" ? span.attrs : null;
  }

  _weatherPathPanel(record) {
    const path = record.weather_context_path || {};
    if (!path.active) {
      return "";
    }
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.weather_path"))}</h3>
        <div class="detailGrid">
          ${this._detailItem(this._t("runs.weather_path"), [
            path.path || "",
            `task_type=${path.task_type || ""}`,
          ])}
          ${this._detailItem("Local", [
            `local_state_cache=${Boolean(path.local_state_cache)}`,
            `weather_entity=${Boolean(path.weather_entity)}`,
          ])}
          ${this._detailItem("Live context", [
            `GetLiveContext calls=${Number(path.get_live_context_calls || 0)}`,
            `results=${Number(path.get_live_context_results || 0)}`,
          ])}
          ${this._detailItem("Fallback", [
            `search_fallback=${Boolean(path.search_fallback)}`,
            path.duplicate_live_context_suppressed ? "duplicate_live_context_suppressed=true" : "",
          ])}
        </div>
        ${this._jsonDetails(this._t("runs.weather_path"), path)}
      </div>
    `;
  }

  _toolIterationsPanel(record) {
    const iterations = Array.isArray(record.tool_calls_by_iteration)
      ? record.tool_calls_by_iteration
      : [];
    if (!iterations.length) {
      return `<div class="empty mini">${escapeHtml(this._t("runs.no_tool_iterations"))}</div>`;
    }
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.tool_iterations"))}</h3>
        <div class="attemptList">
          ${iterations.map((item) => {
            const calls = Array.isArray(item.calls) ? item.calls : [];
            const results = Array.isArray(item.results) ? item.results : [];
            const suppressions = Array.isArray(item.suppressions) ? item.suppressions : [];
            const tone = suppressions.length ? "warning" : "ok";
            return `
              <div class="attempt ${tone}">
                <strong>#${Number(item.iteration || 0)}</strong>
                <span>${escapeHtml(calls.join(", ") || "-")}</span>
                <span>${escapeHtml(results.map((result) => `${result.name}:${result.status || "ok"}`).join(", ") || "-")}</span>
                <span>${escapeHtml(suppressions.map((entry) => `${entry.name}:${entry.reason}`).join(", ") || item.forced_final_reason || "")}</span>
              </div>
            `;
          }).join("")}
        </div>
        ${this._jsonDetails(this._t("runs.tool_iterations"), iterations)}
      </div>
    `;
  }

  _duplicateSuppressionsPanel(record) {
    const suppressions = Array.isArray(record.duplicate_tool_suppressions)
      ? record.duplicate_tool_suppressions
      : [];
    if (!suppressions.length) {
      return `<div class="empty mini">${escapeHtml(this._t("runs.no_duplicate_suppressions"))}</div>`;
    }
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.duplicate_suppressions"))}</h3>
        <div class="attemptList">
          ${suppressions.map((item) => `
            <div class="attempt warning">
              <strong>${escapeHtml(item.name || "")}</strong>
              <span>#${Number(item.iteration || 0)}</span>
              <span>${Number(item.start_ms || 0)} ms</span>
              <span>${escapeHtml(item.reason || "")}</span>
            </div>
          `).join("")}
        </div>
        ${this._jsonDetails(this._t("runs.duplicate_suppressions"), suppressions)}
      </div>
    `;
  }

  _criticalPathPanel(record) {
    const path = Array.isArray(record.critical_path) ? record.critical_path : [];
    if (!path.length) {
      return `<div class="empty mini">${escapeHtml(this._t("runs.no_critical_path"))}</div>`;
    }
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.critical_path"))}</h3>
        <div class="attemptList timelineList">
          ${path.map((span) => {
            const blocking = Boolean(span.blocking);
            const tone = span.status === "error" ? "bad" : (blocking ? "warning" : "muted");
            return `
              <div class="attempt ${tone}">
                <strong>${escapeHtml(span.stage || "")}</strong>
                <span>${Number(span.start_ms || 0)} ms</span>
                <span>${Number(span.duration_ms || 0)} ms</span>
                <span>${escapeHtml(blocking ? this._t("runs.blocking") : this._t("runs.non_blocking"))}</span>
              </div>
            `;
          }).join("")}
        </div>
        ${this._jsonDetails(this._t("runs.critical_path"), path)}
      </div>
    `;
  }

  _searchDebugPanel(record) {
    const debug = record.search_debug || {};
    if (!Object.keys(debug).length) {
      return `<div class="empty mini">${escapeHtml(this._t("runs.no_search_debug"))}</div>`;
    }
    const queries = Array.isArray(debug.queries) ? debug.queries : [];
    const providers = Array.isArray(debug.providers) ? debug.providers : [];
    const results = Array.isArray(debug.results) ? debug.results : [];
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.search_debug"))}</h3>
        <div class="detailGrid">
          ${this._detailItem(this._t("runs.search_gate_reason"), [
            debug.searched ? this._t("common.enabled") : this._t("common.disabled"),
            debug.gate_reason || "",
          ])}
          ${this._detailItem("Latency", [
            `${Number(debug.latency_ms || 0)} ms`,
            `${Number(debug.result_count || 0)} results`,
            `${Number(debug.evidence_extracted || 0)} evidence`,
          ])}
          ${this._detailItem(this._t("runs.debug_flags"), [
            debug.timeout ? this._t("runs.timeout") : "",
            debug.cache_hit ? this._t("runs.cache_hit") : "",
            debug.polluted_result ? this._t("runs.polluted_result") : "",
          ])}
        </div>
        ${queries.length ? `
          <div class="ruleList compact">
            <strong>${escapeHtml(this._t("runs.search_queries"))}</strong>
            ${queries.map((query) => `<span>${escapeHtml(query)}</span>`).join("")}
          </div>
        ` : ""}
        ${providers.length ? `
          <div class="attemptList compact">
            <strong>${escapeHtml(this._t("runs.search_providers"))}</strong>
            ${providers.map((provider) => `
              <div class="attempt compactAttempt ${provider.status === "error" ? "bad" : "ok"}">
                <span>${escapeHtml(provider.provider || "")}</span>
                <span>${escapeHtml(provider.error || provider.status || "ok")}</span>
              </div>
            `).join("")}
          </div>
        ` : ""}
        ${results.length ? `
          <div class="attemptList">
            <strong>${escapeHtml(this._t("runs.search_results"))}</strong>
            ${results.map((result) => `
              <div class="attempt searchResult">
                <strong>${escapeHtml(result.title || "")}</strong>
                <span>${escapeHtml(result.url || "")}</span>
                <span>${escapeHtml(result.content || "")}</span>
              </div>
            `).join("")}
          </div>
        ` : ""}
        ${this._jsonDetails(this._t("runs.search_debug"), debug)}
      </div>
    `;
  }

  _actionsPanel(record) {
    const actions = Array.isArray(record.actions) ? record.actions : [];
    if (!actions.length) {
      return `<div class="empty mini">${escapeHtml(this._t("runs.no_actions"))}</div>`;
    }
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.actions"))}</h3>
        <div class="attemptList">
          ${actions.map((action) => {
            const tone = action.status === "error" || action.policy === "blocked"
              ? "bad"
              : (action.risk === "high" ? "warning" : "ok");
            return `
              <div class="attempt ${tone}">
                <strong>${escapeHtml(action.tool || "")}</strong>
                <span>${escapeHtml([action.area, action.domain, action.entity].filter(Boolean).join(" · "))}</span>
                <span>${escapeHtml(`${action.policy || ""} · ${action.risk || ""} · ${action.status || "ok"}`)}</span>
                <span>${escapeHtml(action.error || (action.unintended_state_change ? this._t("runs.unintended_state_change") : ""))}</span>
              </div>
            `;
          }).join("")}
        </div>
        ${this._jsonDetails(this._t("runs.actions"), actions)}
      </div>
    `;
  }

  _earconEventsPanel(record) {
    const earcons = Array.isArray(record.earcons) ? record.earcons : [];
    if (!earcons.length) {
      return `<div class="empty mini">${escapeHtml(this._t("runs.no_earcons"))}</div>`;
    }
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.earcons"))}</h3>
        <div class="attemptList">
          ${earcons.map((event) => `
            <div class="attempt ${event.suppressed_reason ? "muted" : "ok"}">
              <strong>${escapeHtml(event.earcon_name || "")}</strong>
              <span>${Number(event.scheduled_at_ms || 0)} ms → ${event.played_at_ms === null ? "-" : Number(event.played_at_ms || 0) + " ms"}</span>
              <span>${escapeHtml(`${event.volume_profile || ""} · ${event.duration_ms || 0} ms`)}</span>
              <span>${escapeHtml(event.suppressed_reason || event.trace_event_name || "")}</span>
            </div>
          `).join("")}
        </div>
        ${this._jsonDetails(this._t("runs.earcons"), earcons)}
      </div>
    `;
  }

  _displayStatusPanel(record) {
    const events = Array.isArray(record.display_status?.events)
      ? record.display_status.events
      : [];
    if (!events.length) {
      return `<div class="empty mini">${escapeHtml(this._t("runs.no_display_status"))}</div>`;
    }
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.display_status"))}</h3>
        <div class="attemptList">
          ${events.map((event) => `
            <div class="attempt ${event.state === "failed" ? "bad" : (event.state === "confirming" ? "warning" : "ok")}">
              <strong>${escapeHtml(event.state || "")}</strong>
              <span>${escapeHtml(event.title || "")}</span>
              <span>${escapeHtml(event.short_text || "")}</span>
              <span>${escapeHtml((event.action_buttons || []).join(", ") || event.deep_link || "")}</span>
            </div>
          `).join("")}
        </div>
        ${this._jsonDetails(this._t("runs.display_status"), events)}
      </div>
    `;
  }

  _errorsPanel(errors) {
    if (!errors.length) {
      return `<div class="empty mini">${escapeHtml(this._t("runs.no_errors"))}</div>`;
    }
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.errors"))}</h3>
        <div class="attemptList">
          ${errors.map((error) => `
            <div class="attempt bad">
              <strong>${escapeHtml(error.type || "")}</strong>
              <span>${escapeHtml(error.stage || "")}</span>
              <span>${escapeHtml(error.message || "")}</span>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  _toolEventsPanel(tools) {
    if (!tools.length) {
      return `<div class="empty mini">${escapeHtml(this._t("runs.no_tools"))}</div>`;
    }
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.tool_events"))}</h3>
        <div class="attemptList">
          ${tools.map((tool) => `
            <div class="attempt ${tool.status === "error" || tool.error ? "bad" : "ok"}">
              <strong>${escapeHtml(tool.name || "")}</strong>
              <span>${escapeHtml(tool.phase || "")}${tool.external ? " · external" : ""}</span>
              <span>${escapeHtml(tool.status || "ok")}</span>
              <span>${escapeHtml(tool.error || tool.tool_call_id || "")}</span>
            </div>
          `).join("")}
        </div>
        ${this._jsonDetails(this._t("runs.tool_events"), tools)}
      </div>
    `;
  }

  _evidencePanel(record) {
    const grounding = record.grounding || record.raw_payload?.grounding || {};
    const evidence = Array.isArray(grounding.evidence) ? grounding.evidence : [];
    if (!evidence.length) {
      return `<div class="empty mini">${escapeHtml(this._t("runs.no_evidence"))}</div>`;
    }
    return `
      <div class="debugSection">
        <h3>${escapeHtml(this._t("runs.evidence"))}</h3>
        <div class="evidenceTable">
          ${evidence.map((item) => `
            <div class="evidenceRow ${item.included_in_final ? "included" : ""}">
              <span>${escapeHtml(item.evidence_id || "")}</span>
              <span>${escapeHtml(this._evidenceTypeLabel(item.evidence_type))}</span>
              <span>${escapeHtml(item.text || "")}</span>
              <span>${escapeHtml(item.included_in_final ? this._t("common.enabled") : this._t("common.disabled"))}</span>
            </div>
          `).join("")}
        </div>
        ${this._jsonDetails(this._t("runs.evidence"), evidence)}
      </div>
    `;
  }

  _jsonDetails(label, value) {
    return `
      <details class="jsonDetails">
        <summary>${escapeHtml(label)}</summary>
        <pre>${escapeHtml(JSON.stringify(value, null, 2))}</pre>
      </details>
    `;
  }

  _groundingPanel(record) {
    const grounding = record.grounding || record.raw_payload?.grounding || {};
    const status = String(grounding.status || "");
    if (!status || status === "not_required") {
      return "";
    }
    const tone = this._groundingTone(status);
    const candidates = Array.isArray(grounding.candidates) ? grounding.candidates : [];
    const canonical = Array.isArray(grounding.canonical_answers) ? grounding.canonical_answers : [];
    const repairs = Array.isArray(grounding.repairs) ? grounding.repairs : [];
    return `
      <div class="groundingBox ${tone}">
        <div class="groundingHead">
          <h3>${escapeHtml(this._t("runs.grounding"))}</h3>
          <span class="chip ${tone}">${escapeHtml(this._groundingStatusLabel(status))}</span>
        </div>
        ${candidates.length ? `
          <div class="ruleList compact">
            <strong>${escapeHtml(this._t("runs.grounding_candidates"))}</strong>
            ${candidates.map((candidate) => `<span>${escapeHtml(candidate)}</span>`).join("")}
          </div>
        ` : ""}
        ${canonical.length ? `
          <div class="ruleList compact">
            <strong>${escapeHtml(this._t("runs.grounding_canonical"))}</strong>
            ${canonical.map((answer) => `<span>${escapeHtml(answer)}</span>`).join("")}
          </div>
        ` : ""}
        ${repairs.length ? `
          <div class="attemptList compact">
            <strong>${escapeHtml(this._t("runs.grounding_repairs"))}</strong>
            ${repairs.map((repair) => `
              <div class="attempt ok compactAttempt">
                <span>${escapeHtml(repair.from || "")}</span>
                <span>${escapeHtml(repair.to || "")}</span>
              </div>
            `).join("")}
          </div>
        ` : ""}
      </div>
    `;
  }

  _providerPanel(entry) {
    const providers = entry.model_providers || {};
    const primary = providers.primary || {};
    const fallbacks = Array.isArray(providers.fallbacks) ? providers.fallbacks : [];
    const health = Array.isArray(entry.provider_health) ? entry.provider_health : [];
    if (providers.config_error) {
      return `<div class="providerPanel error">${escapeHtml(this._t("providers.config_error", { message: providers.config_error }))}</div>`;
    }
    return `
      <div class="providerPanel">
        <div>
          <strong>${escapeHtml(this._t("providers.title"))}</strong>
          <span>${escapeHtml(this._t("providers.primary"))}: ${escapeHtml(primary.base_url || entry.base_url || "")}</span>
        </div>
        <div class="ruleList">
          ${fallbacks.map((provider) => `
            <span title="${escapeHtml(provider.base_url || "")}">
              ${escapeHtml(provider.name || "")}
            </span>
          `).join("") || `<span>${escapeHtml(this._t("providers.none"))}</span>`}
        </div>
        <span class="meta">${escapeHtml(this._t("providers.fallbacks", { count: fallbacks.length }))}</span>
        <div class="providerHealth">
          <strong>${escapeHtml(this._t("providers.health"))}</strong>
          ${health.map((item) => `
            <span class="chip ${Number(item.cooldown_remaining_s || 0) > 0 ? "warning" : "muted"}">
              ${escapeHtml(item.provider || "")} · ${escapeHtml(this._routeLabel(item.route))} · ${escapeHtml(this._t("providers.cooldown", { seconds: Number(item.cooldown_remaining_s || 0) }))}
            </span>
          `).join("") || `<span class="meta">${escapeHtml(this._t("providers.health_empty"))}</span>`}
        </div>
      </div>
    `;
  }

  _renderPolicies(entries) {
    const policies = this._data?.prompt_policies || [];
    return `
      <div class="policyGrid">
        ${policies.map((policy) => `
          <article class="surface">
            <div class="sectionHead">
              <div>
                <h2>${escapeHtml(this._policyTitle(policy))}</h2>
                <div class="meta">${escapeHtml(this._policySpoken(policy))}</div>
              </div>
              <span class="chip ${policy.risk === "high" ? "bad" : "muted"}">${escapeHtml(this._riskLabel(policy.risk))}</span>
            </div>
            <div class="ruleList">
              ${(policy.rules || []).map((rule) => `<span>${escapeHtml(this._ruleLabel(rule))}</span>`).join("")}
            </div>
          </article>
        `).join("") || `<div class="empty">${escapeHtml(this._t("policies.empty"))}</div>`}
      </div>
      ${entries.length ? `<div class="surface modelSurface">${entries.map((entry) => this._modelRows(entry.options)).join("")}</div>` : ""}
    `;
  }

  _renderScenarioLab() {
    return `
      <div class="workbench">
        <form class="surface form" data-form="scenario">
          <label>
            <span>${escapeHtml(this._t("scenario.user"))}</span>
            <textarea data-field="user" rows="3">${escapeHtml(this._draft.user)}</textarea>
          </label>
          <label>
            <span>${escapeHtml(this._t("scenario.response"))}</span>
            <textarea data-field="response" rows="4">${escapeHtml(this._draft.response)}</textarea>
          </label>
          <label>
            <span>${escapeHtml(this._t("scenario.expected"))}</span>
            <textarea class="codeInput" data-field="expected" rows="9">${escapeHtml(this._draft.expected)}</textarea>
          </label>
          <button class="primary" type="submit">
            <ha-icon icon="mdi:play"></ha-icon>
            <span>${escapeHtml(this._t("scenario.run"))}</span>
          </button>
        </form>
        ${this._renderResult()}
      </div>
    `;
  }

  _renderSearch(entries) {
    const providers = entries.flatMap((entry) => entry.search.providers || []);
    return `
      <div class="workbench">
        <article class="surface">
          <div class="sectionHead">
            <div>
              <h2>${escapeHtml(this._t("search.gating"))}</h2>
              <div class="meta">${providers.length ? providers.join(", ") : escapeHtml(this._t("search.no_providers"))}</div>
            </div>
          </div>
          <form class="compactForm" data-form="scenario">
            <textarea data-field="user" rows="3">${escapeHtml(this._draft.user)}</textarea>
            <textarea data-field="response" rows="3">${escapeHtml(this._draft.response)}</textarea>
            <button class="primary" type="submit">
              <ha-icon icon="mdi:magnify"></ha-icon>
              <span>${escapeHtml(this._t("search.evaluate"))}</span>
            </button>
          </form>
        </article>
        ${this._renderResult()}
      </div>
    `;
  }

  _renderMemory(entries) {
    const blocks = entries.flatMap((entry) =>
      (entry.memory?.sessions || []).map((session) => ({ entry, session }))
    );
    return `
      <div class="memoryGrid">
        ${blocks.map(({ entry, session }) => `
          <article class="surface">
            <div class="sectionHead">
              <div>
                <h2>${escapeHtml(entry.title)}</h2>
                <div class="meta">${escapeHtml(session.conversation_id)}</div>
              </div>
              <span class="chip muted">${escapeHtml(this._t("memory.turns", { count: (session.turns || []).length }))}</span>
            </div>
            ${session.summary ? `<p class="summary">${escapeHtml(session.summary)}</p>` : ""}
            <div class="turns">
              ${(session.turns || []).map((turn) => `
                <div class="turn">
                  <strong>${escapeHtml(this._t("memory.user"))}</strong>
                  <p>${escapeHtml(turn.user)}</p>
                  <strong>${escapeHtml(this._t("memory.assistant"))}</strong>
                  <p>${escapeHtml(turn.assistant)}</p>
                </div>
              `).join("")}
            </div>
          </article>
        `).join("") || `<div class="empty">${escapeHtml(this._t("memory.empty"))}</div>`}
      </div>
    `;
  }

  _renderEarcons() {
    const pack = this._data?.earcons || {};
    const files = Object.entries(pack.files || {});
    return `
      <div class="surface earconHeader">
        <div>
          <h2>${escapeHtml(pack.pack || this._t("earcon.no_pack"))}</h2>
          <div class="meta">${escapeHtml(this._t("earcon.meta", {
            sampleRate: pack.sample_rate || 0,
            targetLufs: pack.target_lufs || "?",
            peakDbfs: pack.true_peak_dbfs || "?",
          }))}</div>
        </div>
      </div>
      <div class="earconGrid">
        ${files.map(([name, file]) => `
          <article class="surface earcon">
            <div class="sectionHead">
              <div>
                <h2>${escapeHtml(name)}</h2>
                <div class="meta">${escapeHtml(this._earconPurpose(name, file))}</div>
              </div>
              <button class="iconButton" data-earcon="${escapeHtml(name)}" title="${escapeHtml(this._t("earcon.play", { name }))}">
                <ha-icon icon="mdi:play"></ha-icon>
              </button>
            </div>
            <div class="meterRow">
              <span>${escapeHtml(file.duration_ms)} ms</span>
              <span>${escapeHtml(file.lufs)} LUFS</span>
              <span>${escapeHtml(this._t("earcon.peak", { peak: file.peak_dbfs }))}</span>
              <span>${escapeHtml(file.semantic_state || "")}</span>
              <span>P${escapeHtml(file.priority || "")}</span>
              <span>${escapeHtml(file.can_play_while_listening ? "mic-safe" : "mic-muted")}</span>
              <span>${escapeHtml(file.quiet_hours_behavior || "")}</span>
            </div>
          </article>
        `).join("") || `<div class="empty">${escapeHtml(this._t("earcon.empty"))}</div>`}
      </div>
    `;
  }

  _renderRegression() {
    const samples = this._data?.sample_scenarios || [];
    return `
      <div class="regressionList">
        ${samples.map((sample) => `
          <article class="surface sample">
            <div>
              <h2>${escapeHtml(this._sampleName(sample))}</h2>
              <p>${escapeHtml(this._sampleUser(sample))}</p>
            </div>
            <button class="secondary" data-sample="${escapeHtml(sample.id)}">
              <ha-icon icon="mdi:play-outline"></ha-icon>
              <span>${escapeHtml(this._t("regression.run"))}</span>
            </button>
          </article>
        `).join("")}
      </div>
    `;
  }

  _routeCard(route) {
    return `
      <div class="route ${escapeHtml(route.kind)}">
        <span class="routeKind">${escapeHtml(this._routeLabel(route.kind))}</span>
        <strong>${escapeHtml(route.model)}</strong>
        <span>${escapeHtml(this._t("route.tokens", { count: route.max_tokens }))} · ${escapeHtml(this._t("route.timeout", { seconds: route.timeout_s }))}</span>
      </div>
    `;
  }

  _modelRows(options) {
    const tiers = ["fast", "mid", "deep"];
    return `
      <div class="table">
        ${tiers.map((tier) => `
          <div class="row">
            <span class="tier ${tier}">${escapeHtml(this._tierLabel(tier))}</span>
            <strong>${escapeHtml(options.models[tier])}</strong>
            <span>${escapeHtml(this._t("route.tokens", { count: options.max_tokens[tier] }))}</span>
            <span>${options.timeouts[tier]}s</span>
          </div>
        `).join("")}
      </div>
    `;
  }

  _renderResult() {
    if (!this._result) {
      return `<article class="surface result emptyState">${escapeHtml(this._t("result.empty"))}</article>`;
    }
    const result = this._result;
    const passed = result.passed ? this._t("result.passed") : this._t("result.failed");
    const search = result.search.allowed ? this._t("search.allowed") : this._t("search.blocked");
    return `
      <article class="surface result">
        <div class="sectionHead">
          <div>
            <h2>${escapeHtml(passed)}</h2>
            <div class="meta">${escapeHtml(this._t("result.meta", { route: this._routeLabel(result.route.kind), search }))}</div>
          </div>
          <span class="chip ${result.passed ? "ok" : "bad"}">${escapeHtml(passed)}</span>
        </div>
        <div class="spoken">${escapeHtml(result.spoken || "")}</div>
        ${(result.violations || []).length ? `
          <ul class="violations">
            ${result.violations.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
        ` : ""}
        <pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>
      </article>
    `;
  }

  _locale() {
    let storedLanguage = "";
    try {
      storedLanguage = localStorage.getItem("selectedLanguage") || "";
    } catch (_err) {
      storedLanguage = "";
    }
    const language = [
      this.hass?.locale?.language,
      this.hass?.selectedLanguage,
      this.hass?.language,
      this._panel?.language,
      document?.documentElement?.lang,
      storedLanguage,
      navigator.language,
    ].find(Boolean) || "en";
    return String(language).toLowerCase().startsWith("zh") ? "zh-Hans" : "en";
  }

  _t(key, params = {}) {
    const table = I18N[this._locale()] || I18N.en;
    const fallback = I18N.en[key] || key;
    return String(table[key] || fallback).replace(/\{(\w+)\}/g, (_match, name) =>
      params[name] ?? ""
    );
  }

  _defaultDraft(locale) {
    return { ...(DEFAULT_DRAFTS[locale] || DEFAULT_DRAFTS.en) };
  }

  _localize(value, fallback = "") {
    if (!value || typeof value !== "object") {
      return value || fallback;
    }
    const locale = this._locale();
    return value[locale] || value.en || value["zh-Hans"] || fallback;
  }

  _policyTitle(policy) {
    const key = `policy.${policy.id}.title`;
    return this._localize(policy.title_i18n, this._lookup(key, policy.title));
  }

  _policySpoken(policy) {
    const key = `policy.${policy.id}.spoken`;
    return this._localize(policy.spoken_i18n, this._lookup(key, policy.spoken));
  }

  _sampleName(sample) {
    const key = `sample.${sample.id}.name`;
    return this._localize(sample.name_i18n, this._lookup(key, sample.name));
  }

  _sampleUser(sample) {
    return this._localize(sample.user_i18n, sample.user);
  }

  _sampleResponse(sample) {
    return this._localize(sample.response_i18n, sample.response);
  }

  _sampleExpected(sample) {
    const value = sample.expected_i18n;
    if (!value || typeof value !== "object") {
      return sample.expected || {};
    }
    const locale = this._locale();
    return value[locale] || value.en || value["zh-Hans"] || sample.expected || {};
  }

  _earconPurpose(name, file) {
    const key = `earcon.${name}.purpose`;
    return this._localize(file.purpose_i18n, this._lookup(key, file.purpose || ""));
  }

  _modeLabel(value) {
    const mode = String(value || "auto");
    return this._lookup(`mode.${mode}`, mode);
  }

  _adapterLabel(value) {
    const adapter = String(value || "local");
    return this._lookup(`adapter.${adapter}`, adapter);
  }

  /** @returns {RouteKind} */
  _routeKind(value) {
    const candidate = String(value || "auto");
    switch (candidate) {
      case "fast":
      case "mid":
      case "deep":
      case "auto":
        return candidate;
      default:
        return "auto";
    }
  }

  /** @returns {FirstResponsePlaybackAdapter} */
  _firstResponseAdapter(value) {
    const candidate = String(value || "local");
    switch (candidate) {
      case "ha_media_player":
      case "auto":
      case "local":
        return candidate;
      default:
        return "local";
    }
  }

  _routeLabel(value) {
    const kind = String(value || "unknown");
    return this._lookup(`mode.${kind}`, kind);
  }

  _tierLabel(value) {
    const tier = String(value || "");
    return this._lookup(`tier.${tier}`, tier);
  }

  _riskLabel(value) {
    const risk = String(value || "low");
    return this._lookup(`risk.${risk}`, risk);
  }

  _ruleLabel(value) {
    const rule = String(value || "");
    return this._lookup(`rule.${rule}`, rule);
  }

  _traceStatusLabel(value) {
    const status = String(value || "unknown");
    return this._lookup(`trace.status.${status}`, status);
  }

  _groundingStatusLabel(value) {
    const status = String(value || "not_required");
    return this._lookup(`grounding.status.${status}`, status);
  }

  _verifierModeLabel(value) {
    const mode = String(value || "disabled");
    return this._lookup(`verifier.${mode}`, mode);
  }

  _evidenceTypeLabel(value) {
    const type = String(value || "");
    return this._lookup(`evidence.${type}`, type);
  }

  _groundingTone(value) {
    const status = String(value || "");
    if (status === "repaired") {
      return "warning";
    }
    if (["no_answer", "no_evidence", "unsupported", "verifier_error"].includes(status)) {
      return "bad";
    }
    return "ok";
  }

  _lookup(key, fallback = "") {
    const table = I18N[this._locale()] || I18N.en;
    return table[key] || I18N.en[key] || fallback || "";
  }

  _formatTime(value) {
    if (!value) {
      return "";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return String(value);
    }
    return new Intl.DateTimeFormat(this._locale(), {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(date);
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeId(value) {
  return String(value ?? "default").replace(/[^a-zA-Z0-9_-]/g, "-");
}

const styles = `
  :host {
    color: var(--primary-text-color);
    display: block;
    min-height: 100vh;
    background: var(--primary-background-color);
  }

  * {
    box-sizing: border-box;
    letter-spacing: 0;
  }

  .shell {
    width: min(1280px, 100%);
    margin: 0 auto;
    padding: 20px;
  }

  .topbar {
    min-height: 68px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    border-bottom: 1px solid var(--divider-color);
    margin-bottom: 14px;
  }

  h1, h2, h3, p {
    margin: 0;
  }

  h1 {
    font-size: 24px;
    font-weight: 650;
    line-height: 1.2;
  }

  h2 {
    font-size: 15px;
    font-weight: 650;
    line-height: 1.3;
  }

  h3 {
    font-size: 13px;
    font-weight: 650;
    line-height: 1.35;
  }

  .subline,
  .meta,
  .route span,
  .row span,
  .sample p {
    color: var(--secondary-text-color);
    font-size: 13px;
    line-height: 1.35;
  }

  button {
    min-height: 40px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    background: var(--card-background-color);
    color: var(--primary-text-color);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font: inherit;
    cursor: pointer;
    white-space: nowrap;
  }

  button:hover {
    border-color: var(--primary-color);
  }

  button:disabled {
    cursor: not-allowed;
    opacity: 0.58;
  }

  button ha-icon {
    width: 20px;
    height: 20px;
    pointer-events: none;
  }

  .iconButton {
    width: 44px;
    padding: 0;
  }

  .primary {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: var(--text-primary-color);
    padding: 0 16px;
  }

  .secondary {
    padding: 0 14px;
  }

  .tabs {
    display: grid;
    grid-template-columns: repeat(8, minmax(0, 1fr));
    gap: 8px;
    margin: 14px 0 18px;
  }

  .tab {
    height: 44px;
    padding: 0 10px;
  }

  .tab.active {
    border-color: var(--primary-color);
    background: color-mix(in srgb, var(--primary-color) 14%, var(--card-background-color));
  }

  .tab span {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .content {
    min-height: 420px;
  }

  .surface,
  .empty {
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
  }

  .surface {
    padding: 16px;
  }

  .empty,
  .emptyState {
    min-height: 180px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--secondary-text-color);
  }

  .empty.mini {
    min-height: 54px;
    padding: 10px 12px;
    text-align: center;
  }

  .banner {
    border-radius: 8px;
    padding: 12px 14px;
    margin: 12px 0;
    border: 1px solid var(--divider-color);
  }

  .banner.error {
    color: var(--error-color);
    background: color-mix(in srgb, var(--error-color) 10%, var(--card-background-color));
  }

  .banner.success {
    color: var(--success-color);
    background: color-mix(in srgb, var(--success-color) 10%, var(--card-background-color));
  }

  .grid,
  .entryGrid,
  .policyGrid,
  .memoryGrid,
  .earconGrid,
  .settingsGrid,
  .satelliteGrid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 14px;
  }

  .settingsGrid .banner {
    grid-column: 1 / -1;
  }

  .settingsForm {
    display: grid;
    gap: 14px;
  }

  .settingsNote {
    color: var(--secondary-text-color);
    font-size: 13px;
    line-height: 1.45;
  }

  small {
    color: var(--secondary-text-color);
    font-size: 12px;
    line-height: 1.35;
  }

  .audioRoute {
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    display: grid;
    gap: 8px;
    padding: 10px;
    background: var(--primary-background-color);
  }

  .sectionHead.compact {
    margin-bottom: 0;
    min-height: 32px;
  }

  .sectionHead.compact div {
    display: grid;
    gap: 3px;
    min-width: 0;
  }

  .sectionHead.compact span:not(.chip) {
    color: var(--secondary-text-color);
    font-size: 12px;
  }

  .candidateGrid {
    border-top: 1px solid var(--divider-color);
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    padding: 10px;
  }

  .candidateList {
    display: grid;
    gap: 6px;
    min-width: 0;
  }

  .candidateList strong {
    font-size: 12px;
  }

  .candidateItem {
    align-items: center;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    display: flex;
    gap: 6px;
    min-height: 34px;
    min-width: 0;
    padding: 6px 8px;
  }

  .candidateItem > span:first-child {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .satellitePanel {
    display: grid;
    gap: 14px;
  }

  .satelliteControls {
    align-items: end;
    display: grid;
    gap: 10px;
    grid-template-columns: minmax(140px, 1fr) repeat(3, max-content);
  }

  .stateList {
    display: grid;
    gap: 8px;
  }

  .stateRow {
    align-items: center;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    display: grid;
    gap: 10px;
    grid-template-columns: minmax(0, 1fr) max-content;
    min-height: 56px;
    padding: 8px 10px;
  }

  .stateRow div {
    display: grid;
    gap: 3px;
    min-width: 0;
  }

  .stateRow strong {
    font-size: 13px;
  }

  .stateRow span:not(.chip) {
    color: var(--secondary-text-color);
    font-size: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  fieldset {
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 12px;
    display: grid;
    gap: 12px;
  }

  legend {
    padding: 0 6px;
    color: var(--secondary-text-color);
    font-size: 12px;
    font-weight: 650;
  }

  label {
    display: grid;
    gap: 6px;
    min-width: 0;
  }

  label span {
    color: var(--secondary-text-color);
    font-size: 12px;
    line-height: 1.35;
  }

  input,
  select,
  textarea {
    width: 100%;
    min-height: 40px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font: inherit;
    padding: 8px 10px;
  }

  input:focus,
  select:focus,
  textarea:focus {
    border-color: var(--primary-color);
    outline: none;
  }

  .settingsTriples {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .settingsTriples.two {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .checkRow {
    min-height: 36px;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .checkRow input {
    width: 18px;
    min-height: 18px;
  }

  .workbench {
    display: grid;
    grid-template-columns: minmax(320px, 0.92fr) minmax(340px, 1.08fr);
    gap: 14px;
    align-items: start;
  }

  .sectionHead {
    min-height: 42px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
  }

  .chip {
    min-height: 26px;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 650;
    border: 1px solid var(--divider-color);
  }

  .chip.ok {
    color: var(--success-color);
    background: color-mix(in srgb, var(--success-color) 12%, transparent);
  }

  .chip.bad {
    color: var(--error-color);
    background: color-mix(in srgb, var(--error-color) 12%, transparent);
  }

  .chip.error {
    color: var(--error-color);
    background: color-mix(in srgb, var(--error-color) 12%, transparent);
  }

  .chip.muted {
    color: var(--secondary-text-color);
  }

  .chip.warning {
    color: var(--warning-color);
    background: color-mix(in srgb, var(--warning-color) 12%, transparent);
  }

  .routeGrid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .tracePanel {
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid var(--divider-color);
    display: grid;
    gap: 12px;
  }

  .providerPanel {
    margin-top: 12px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 12px;
    display: grid;
    gap: 10px;
    background: var(--primary-background-color);
  }

  .providerPanel.error {
    color: var(--error-color);
    background: color-mix(in srgb, var(--error-color) 8%, var(--primary-background-color));
  }

  .providerPanel > div:first-child {
    display: grid;
    gap: 4px;
  }

  .providerPanel strong {
    font-size: 13px;
  }

  .providerPanel span {
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .providerHealth {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }

  .traceHeader {
    min-height: 38px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .liveStatus {
    margin-top: 12px;
    min-height: 64px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    background: color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color));
  }

  .liveStatus.confirming {
    border-color: color-mix(in srgb, var(--warning-color) 44%, var(--divider-color));
  }

  .liveStatus.failed {
    border-color: color-mix(in srgb, var(--error-color) 38%, var(--divider-color));
  }

  .liveStatus div:first-child {
    min-width: 0;
    display: grid;
    gap: 4px;
  }

  .liveStatus span {
    min-width: 0;
    color: var(--secondary-text-color);
    font-size: 12px;
    overflow-wrap: anywhere;
  }

  .traceList {
    display: grid;
    gap: 10px;
  }

  .traceCard {
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    background: var(--primary-background-color);
    overflow: hidden;
  }

  .traceCard summary {
    min-height: 54px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 12px;
    cursor: pointer;
  }

  .traceCard summary > div {
    min-width: 0;
    display: grid;
    gap: 2px;
  }

  .summaryChips {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 6px;
  }

  .traceCard summary span {
    color: var(--secondary-text-color);
    font-size: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .traceBody {
    border-top: 1px solid var(--divider-color);
    padding: 12px;
    display: grid;
    gap: 12px;
  }

  .traceText {
    display: grid;
    gap: 6px;
  }

  .traceText strong {
    color: var(--secondary-text-color);
    font-size: 12px;
    text-transform: uppercase;
  }

  .traceText p {
    line-height: 1.45;
    overflow-wrap: anywhere;
  }

  .runFlags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .detailGrid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 10px;
  }

  .detailItem {
    min-height: 72px;
    display: grid;
    align-content: start;
    gap: 4px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 10px;
    background: var(--card-background-color);
  }

  .detailItem strong {
    color: var(--secondary-text-color);
    font-size: 12px;
    text-transform: uppercase;
  }

  .detailItem span {
    min-width: 0;
    overflow-wrap: anywhere;
    font-size: 13px;
  }

  .debugSection {
    display: grid;
    gap: 8px;
  }

  .debugSection h3 {
    margin: 0;
  }

  .evidenceTable {
    display: grid;
    gap: 6px;
  }

  .evidenceRow {
    min-height: 34px;
    display: grid;
    grid-template-columns: 64px minmax(120px, 0.8fr) minmax(180px, 1.4fr) 80px;
    align-items: center;
    gap: 8px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 8px 10px;
    background: var(--card-background-color);
  }

  .evidenceRow.included {
    border-color: color-mix(in srgb, var(--success-color) 38%, var(--divider-color));
  }

  .evidenceRow span {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 12px;
  }

  .jsonDetails {
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    background: var(--card-background-color);
  }

  .jsonDetails summary {
    cursor: pointer;
    padding: 8px 10px;
    color: var(--secondary-text-color);
    font-size: 12px;
    text-transform: uppercase;
  }

  .jsonDetails pre {
    margin: 0;
    border-top: 1px solid var(--divider-color);
    border-radius: 0;
  }

  .groundingBox {
    display: grid;
    gap: 10px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 10px;
    background: color-mix(in srgb, var(--card-background-color) 92%, var(--primary-color));
  }

  .groundingBox.ok {
    border-color: color-mix(in srgb, var(--success-color) 38%, var(--divider-color));
  }

  .groundingBox.warning {
    border-color: color-mix(in srgb, var(--warning-color) 44%, var(--divider-color));
  }

  .groundingBox.bad {
    border-color: color-mix(in srgb, var(--error-color) 38%, var(--divider-color));
  }

  .groundingHead {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .groundingHead h3 {
    margin: 0;
  }

  .ruleList.compact,
  .attemptList.compact {
    gap: 6px;
  }

  .attempt.compactAttempt {
    min-height: 30px;
    grid-template-columns: minmax(120px, 1fr) minmax(120px, 1fr);
  }

  .attemptList {
    display: grid;
    gap: 8px;
  }

  .attempt {
    min-height: 36px;
    display: grid;
    grid-template-columns: minmax(92px, 0.7fr) minmax(160px, 1.3fr) minmax(92px, 0.7fr) minmax(80px, 0.5fr);
    align-items: center;
    gap: 10px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 8px 10px;
    background: var(--card-background-color);
  }

  .attempt.ok {
    border-color: color-mix(in srgb, var(--success-color) 38%, var(--divider-color));
  }

  .attempt.warning {
    border-color: color-mix(in srgb, var(--warning-color) 44%, var(--divider-color));
  }

  .attempt.bad {
    border-color: color-mix(in srgb, var(--error-color) 38%, var(--divider-color));
  }

  .attempt.muted {
    opacity: 0.72;
  }

  .attempt.searchResult {
    grid-template-columns: minmax(120px, 0.8fr) minmax(140px, 0.9fr) minmax(180px, 1.3fr);
  }

  .attempt strong,
  .attempt span {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 12px;
  }

  .route {
    min-height: 112px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 12px;
    display: grid;
    align-content: start;
    gap: 8px;
  }

  .route strong {
    min-width: 0;
    font-size: 13px;
    line-height: 1.35;
    overflow-wrap: anywhere;
  }

  .routeKind,
  .tier {
    width: max-content;
    min-height: 22px;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
  }

  .fast .routeKind,
  .tier.fast {
    color: #0b7a53;
    background: color-mix(in srgb, #0b7a53 13%, transparent);
  }

  .mid .routeKind,
  .tier.mid {
    color: #1d5fd1;
    background: color-mix(in srgb, #1d5fd1 13%, transparent);
  }

  .deep .routeKind,
  .tier.deep {
    color: #a25500;
    background: color-mix(in srgb, #a25500 15%, transparent);
  }

  .table {
    display: grid;
    gap: 8px;
  }

  .modelSurface {
    margin-top: 14px;
  }

  .ruleList {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .ruleList span,
  .meterRow span {
    min-height: 26px;
    border-radius: 999px;
    border: 1px solid var(--divider-color);
    display: inline-flex;
    align-items: center;
    padding: 0 10px;
    color: var(--secondary-text-color);
    font-size: 12px;
  }

  .row {
    min-height: 46px;
    display: grid;
    grid-template-columns: 68px minmax(160px, 1fr) 96px 56px;
    align-items: center;
    gap: 10px;
    border-top: 1px solid var(--divider-color);
    padding-top: 8px;
  }

  .row strong {
    min-width: 0;
    overflow-wrap: anywhere;
    font-size: 13px;
  }

  .form,
  .compactForm {
    display: grid;
    gap: 12px;
  }

  label {
    display: grid;
    gap: 6px;
  }

  label span {
    font-size: 13px;
    color: var(--secondary-text-color);
  }

  textarea {
    width: 100%;
    resize: vertical;
    min-height: 76px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 10px 12px;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font: inherit;
    line-height: 1.45;
  }

  .codeInput,
  pre {
    font-family: var(--code-font-family, Menlo, Consolas, monospace);
    font-size: 12px;
  }

  .result {
    min-height: 260px;
    display: grid;
    align-content: start;
    gap: 12px;
  }

  .spoken {
    min-height: 44px;
    border-radius: 8px;
    padding: 12px;
    background: var(--primary-background-color);
    line-height: 1.45;
  }

  .violations {
    margin: 0;
    padding: 0 0 0 20px;
    color: var(--error-color);
  }

  pre {
    margin: 0;
    max-height: 320px;
    overflow: auto;
    border-radius: 8px;
    padding: 12px;
    background: var(--primary-background-color);
    color: var(--secondary-text-color);
  }

  .turns {
    display: grid;
    gap: 10px;
  }

  .turn {
    border-top: 1px solid var(--divider-color);
    padding-top: 10px;
    display: grid;
    gap: 4px;
  }

  .turn strong {
    color: var(--secondary-text-color);
    font-size: 12px;
    text-transform: uppercase;
  }

  .turn p,
  .summary {
    line-height: 1.45;
    overflow-wrap: anywhere;
  }

  .regressionList {
    display: grid;
    gap: 10px;
  }

  .earconHeader {
    min-height: 72px;
    display: flex;
    align-items: center;
    margin-bottom: 14px;
  }

  .earcon {
    min-height: 146px;
  }

  .meterRow {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .sample {
    min-height: 78px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .skeleton {
    min-height: 180px;
    background: linear-gradient(90deg, var(--card-background-color), var(--primary-background-color), var(--card-background-color));
  }

  .skeleton.wide {
    grid-column: 1 / -1;
  }

  @media (max-width: 900px) {
    .tabs {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .workbench {
      grid-template-columns: 1fr;
    }

    .routeGrid {
      grid-template-columns: 1fr;
    }

    .settingsTriples,
    .settingsTriples.two {
      grid-template-columns: 1fr;
    }

    .candidateGrid {
      grid-template-columns: 1fr;
    }

    .attempt {
      grid-template-columns: 1fr;
      align-items: start;
    }
  }

  @media (max-width: 560px) {
    .shell {
      padding: 12px;
    }

    .tabs {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .tab {
      justify-content: flex-start;
    }

    .grid,
    .entryGrid,
    .policyGrid,
    .memoryGrid,
    .earconGrid,
    .settingsGrid,
    .satelliteGrid {
      grid-template-columns: 1fr;
    }

    .satelliteControls {
      grid-template-columns: 1fr;
    }

    .row {
      grid-template-columns: 1fr;
      align-items: start;
    }

    .sample {
      align-items: stretch;
      flex-direction: column;
    }
  }
`;

try {
  if (!customElements.get("voice-harness-panel")) {
    customElements.define("voice-harness-panel", VoiceHarnessPanel);
  }
} catch (err) {
  if (!String(err?.message || err).includes("has already been used")) {
    throw err;
  }
}
