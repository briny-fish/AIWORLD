# Local API

M9 提供一个零依赖的本地 HTTP API。它的职责是稳定协议边界，不负责 3D 渲染，也不让外部直接改内部状态。

启动：

```powershell
python -m virtual_society.cli --serve --seed 7 --host 127.0.0.1 --port 8765
```

如果要让服务按周期记录历史快照：

```powershell
python -m virtual_society.cli --serve --seed 7 --snapshot-every 30
```

## Endpoints

`GET /health`

返回服务状态和当前天数。

`GET /state`

返回当前世界快照，包括智能体、组织、资源、规则、事件日志、当前指标和待执行干预。

`GET /metrics`

返回通过 API 推进后记录的指标序列。

`GET /events?limit=50`

返回最近事件。

`GET /history`

返回周期性历史快照摘要。

`GET /report/run.json`

导出当前运行的 JSON 报告。

`GET /report/run.html`

导出当前运行的离线 HTML 报告。

`GET /agents`

Returns the `agent-dossier-v1` index for all current individuals. This is the
shared product contract for observer UIs, story surfaces, and future roleplay
or LLM layers.

`GET /agents/{id}`

Returns one `agent-dossier-v1` record with identity continuity, recent life
journal, recent memory, relationship pressure, relevant recommendations, and
bounded observer affordances. Clients must still apply changes through
structured interventions and `/step`; the dossier is read-only.

`GET /locations`

Returns the `world-object-dossier-v1` index for all locations, including
condition state, resident count, connected route state, recent evidence, and
bounded observer affordances.

`GET /locations/{id}`

Returns one location dossier. Location affordances currently include bounded
food/material support and repair-focused broadcasts where damage or blocked
routes make that relevant.

`GET /organizations`

Returns the `world-object-dossier-v1` index for all organizations.

`GET /organizations/{id}`

Returns one organization dossier with members, cohesion/fracture state, home
location inventory gaps, recent evidence, and bounded coordination affordances.

`GET /observer`

打开同源交互式观察器页面。观察器会调用当前 API 服务读取状态、推进时间和提交干预。

`GET /observer3d`

打开 Three.js 3D 观察器原型。它使用同一套 API 读取世界状态并提交干预。

`POST /step`

推进模拟。

```json
{
  "days": 7,
  "interventions": [
    {
      "kind": "resource",
      "reason": "observer aid",
      "params": {
        "resource": "food",
        "amount": 5
      }
    }
  ]
}
```

没有 `day` 的干预会默认安排到下一天。有 `day` 的干预使用绝对世界日期。

`POST /interventions`

安排未来干预，但不立刻推进时间。

```json
{
  "day": 12,
  "kind": "organization",
  "reason": "specialized work group",
  "params": {
    "id": "builders_lodge",
    "name": "Builders Lodge",
    "kind": "guild",
    "members": ["a2", "a6"],
    "norms": ["maintain_shelter"]
  }
}
```

### Observer Intent Broadcast

The narrowed participation path uses `broadcast` with structured `intent`.
It does not directly edit world state. It writes a remembered observer message
to target agents; later cognition may turn that memory into a plan, and the
Simulation Core still validates execution.

```json
{
  "kind": "broadcast",
  "reason": "observer intent repair_routes",
  "params": {
    "intent": "repair_routes",
    "tone": "hope",
    "strength": 0.1,
    "target_agent_ids": ["a1", "a7"],
    "message": "Reopen blocked routes before more hauling."
  }
}
```

Supported intent values: `repair_routes`, `reconcile_relationships`,
`protect_food`, and `coordinate`. Omit `target_agent_ids` to broadcast to all
agents.

`POST /reset`

重置服务里的模拟。

```json
{
  "seed": 7
}
```

## Design Rules

- API 只通过 `Intervention` 和 `step` 影响世界。
- 外部系统不能直接写 `WorldState`。
- 3D 客户端、Web 观察器和未来 LLM 对话层都应通过这套协议接入。
- 服务当前是单进程内存态，适合本地开发和调试；持久化和多用户并发属于后续里程碑。
