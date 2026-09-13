# Voice and room intent / 语音与空间意图

Room questions use room observations. Room comfort requests change RoomMind's
policy. Explicit AC requests keep their device meaning. These three operations
must not substitute for one another.

问室温、设定舒适目标、调整空调，是三个不同意图。RoomMind 的 Control Cycle
继续负责 observe → plan → constrain → submit → reconcile → learn → publish → persist。
Gateway 通过现有 HA 实体读写，不读取或改写 RoomMind 内部状态。

## Room observations / 房间观测

For temperature and humidity, the local query loop reads the area's designated
`temperature_entity_id` and `humidity_entity_id` from the HA area registry.
It respects Assist exposure, disabled/hidden entities, and per-field
`observed_at` / `observation_max_age_s` when the sensor supplies them.

An unavailable or expired designated sensor produces an unavailable answer.
It cannot fall back to an AC's internal temperature or target. Named room
aliases and numbered rooms remain distinct; ambiguous aliases ask for the room.
An explicit multi-room request retains missing rooms in its answer.

“卧室现在多少度？”读取卧室指定温度源；紧接着的“那客厅呢？”继承温度查询。
温湿度联合查询保留两个指标。插入其他话题后，不再继承旧查询。

Rooms without a designated source use the existing exposed sensor reader.
Whole-home summaries also exclude climate-device temperature as a substitute
for room temperature. An air-quality summary can use the sensors present;
an explicitly requested missing measurement remains missing. Formaldehyde,
TVOC, CO₂, and eCO₂ are separate measurements. The M1 provides temperature,
humidity, PM2.5, and formaldehyde; this feature creates no sensor entities.

## Comfort and device requests / 舒适目标与设备动作

| Request / 说法 | Meaning / 含义 |
| --- | --- |
| 把卧室温度调到 25.5 度 | Set the existing RoomMind comfort entity to 25.5°C. Its normal hold semantics and Control Cycle apply. |
| 把卧室空调设为 25.5 度 | Send a 25.5°C setpoint request to the explicitly named AC. |
| 卧室空调现在多少度？ | Read the device's reported temperature, separate from the room observation. |

Comfort entities are resolved through the entity registry's RoomMind unique ID,
so an entity rename does not change ownership. Missing, unavailable, hidden,
or unexposed comfort control does not redirect the request to an AC. Negated
requests and questions about whether a change happened do not dispatch it.

An unavailable comfort control ends as an error, not a request for clarification.
The room and target are already understood; repeating them cannot restore the
control. A missing or ambiguous room still asks only for the room.
控制不可用时明确结束本次请求；只有房间不明确时才请用户补充。

Device matching removes the requested temperature from the device name. When
two devices still need clarification, choosing one retains the original
setpoint. Confirmation applies to the chosen name only; it does not increase
confidence in every similarly named device. 空调与舒适实体共存时，明确说出的空调
无需重复确认；真正需要澄清时，也不要求用户重说温度。

After a successful comfort service call, Gateway reads the comfort entity's
`override_active`, `override_temperature`, and `override_suppressed` attributes.
Only a matching active override supports **Comfort target saved**. A missing or
different value stays **Comfort target submitted**. An away-policy suppression
is stated explicitly. This readback is a copied policy observation with its HA
timestamp; it neither confirms AC application nor says the room reached its goal.

“把温度调到 25.5 度”缺少房间时，只追问房间；随后“卧室”或明确的房间别名会沿用
25.5 度。单独回答“对的”不会擅自选一个房间。首轮使用 HA 已分配给 ChatLog 的
会话 ID，后续澄清、记忆与记录因此属于同一会话。重复肯定词如“对的，对的，是的”
可确认已明确提问的设备，不再退回模型重复追问。

## Dispatch and confirmation / 发出与确认

Each local service attempt retains its HA context ID, request data, and dispatch
result. For the companion TCL integration, Gateway listens to the existing
`tcl_udp_ac_command_result` event during the blocking service call. Both the
context ID and entity must match. Reports arriving before the service returns
are retained; the listener is released on completion, error, or cancellation.
The Gateway adds no polling or device retry.

- A successful HA return establishes **sent**.
- A transport receipt establishes **accepted**, separately from application.
- The driver's **applied** event establishes that the device reported the
  requested state. Every captured operation and target must be covered before
  the dispatch summary says **confirmed**.
- A **not_confirmed** result stays distinct from a failed service call.
- Missing driver evidence remains **unknown**. Later observations are separate
  facts; this short-lived voice listener does not claim to reconcile them.

Bulk actions retain every attempted dispatch, including failures and their
context IDs. A partial or entirely failed batch cannot leave a success-only
evidence list. Already satisfied targets retain their separate skipped records.

“设备已回报设定 25.5 度”只确认设备设定，不表示房间已达到 25.5°C，也不证明压缩机
正在制冷。房间策略保存完成同样不等于空调执行完成。RoomMind 的执行器仍按其原有
context ID 关联与迟到证据处理规则记录 Control Outcome。

Run events copy bounded attributes when recorded. Scalar booleans, numbers and
nulls retain their types at the nesting limit, so a saved comfort target remains
recognizable after trace persistence. A completed local action is a completed
reply; the separate dispatch and device evidence still determine confirmation.
记录不会因调用方后续修改而变更事实，也不会把布尔确认值变成展示用字符串。

## Assist pipeline / 语音入口

The household Norta pipeline must route conversation through Gateway with
`prefer_local_intents: false`. Gateway still handles supported room reads and
device requests locally, without a model call.

On the target HA version, the native temperature intent can select a designated
sensor but the Chinese response template reads the climate-only
`current_temperature` attribute. The observed answer was “现在温度是None度”.
With no designated sensor, the same path previously chose the AC's internal
temperature. Routing this pipeline through one conversation owner also keeps
follow-ups, exposure checks, speech, and outcome records together. Other Assist
pipelines and HA core files need no changes.

Set this option on the household Assist pipeline and verify a pipeline run after
restarting HA. A direct `conversation.process` call to Gateway does not exercise
the pipeline's local-intent preference. 直接调用 Gateway 成功，不等于实际语音入口
已经经过 Gateway；验收必须检查 Assist 管线中的 `intent-start` 和 `intent-end`。

## Calm surface / 平静界面

Overview leads with the understood utterance, reply, and evidence. Metrics,
connections, and memory expand under System details. Runs opens on the dialogue;
timing, model usage, replay, and technical events remain under Evidence. Test
helps investigate an actual response. Settings offers existing audio scenes and
automatic night volume first, with individual gains under Fine-tune volumes.

原有故障提示、取消、权限与高风险确认保留。减少的是首屏视觉负担，所有诊断和试听
能力仍可按需使用；没有新增 hash、冻结契约或发布门禁。
