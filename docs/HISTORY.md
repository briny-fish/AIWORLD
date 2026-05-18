# History And Snapshots

M8 的目标是让长期运行可审计。

模拟器每天仍然只由规则推进；历史系统只是观察层，不会修改世界状态。`HistoryRecorder` 在每个 tick 之后读取当前 `WorldState` 和 `Metrics`，按固定间隔捕获压缩快照。

快照包含：

- 当日核心指标。
- 相比上一个快照的趋势变化。
- 当前资源储备。
- 当前组织状态。
- 当前行动计划分布。
- 区间内事件计数。
- 区间内重要事件摘要。
- 当前需求较低的角色列表。

命令行用法：

```powershell
python -m virtual_society.cli --days 365 --seed 7 --snapshot-every 30 --save-run-json artifacts/run-seed7-365-history.json --save-run-html artifacts/run-seed7-365-history.html
```

把每个快照单独写成 JSON 文件：

```powershell
python -m virtual_society.cli --days 365 --seed 7 --snapshot-every 30 --save-snapshots-dir artifacts/snapshots-seed7-365
```

如果提供 `--save-snapshots-dir` 但没有设置 `--snapshot-every`，默认每 30 天捕获一次。

设计边界：

- 快照不参与世界状态变更。
- 快照不替代完整事件日志，只负责给长跑提供可读索引。
- 后续 LLM 长期记忆应优先读取这些摘要，而不是直接吞完整事件日志。
- 3D/交互式观察器也应优先消费这些快照和摘要，避免在前端处理过大的历史日志。
