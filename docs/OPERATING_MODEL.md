# 长期运行方式

## 每日开发循环

1. 选择一个具体社会能力，例如“饥饿导致劳动优先级上升”。
2. 写最小规则和测试。
3. 运行固定 seed 的模拟。
4. 查看事件日志和指标。
5. 判断这个能力是否让社会更真实、更稳定或更可解释。

## 每周实验循环

每周固定做一次长跑实验：

- 运行多个 seed。
- 每个 seed 至少 365 个 tick。
- 保存最终指标。
- 记录异常社会。
- 把异常转化为下一周的任务。

当前命令：

```powershell
python -m virtual_society.cli --days 365 --experiment-seeds 1,2,3,4,5 --report-every 30
```

带干预场景：

```powershell
python -m virtual_society.cli --days 365 --experiment-seeds 1,2,3,4,5 --intervention-file scenarios/storm-and-aid.json
```

保存实验产物：

```powershell
python -m virtual_society.cli --days 365 --experiment-seeds 1,2,3,4,5 --save-experiment-json artifacts/experiment-365.json --save-experiment-html artifacts/experiment-365.html
```

## 决策规则

优先级从高到低：

1. 能提升长期稳定性。
2. 能提升可观察性。
3. 能提升因果解释能力。
4. 能增加自然演化可能性。
5. 能改善用户体验。
6. 能提升视觉表现。

## 何时使用 LLM

适合使用 LLM：

- 角色对话。
- 对历史事件做主观解释。
- 生成计划候选。
- 压缩个人记忆。
- 生成文化、谣言、传说、新闻。

不适合直接交给 LLM：

- 资源数量。
- 位置状态。
- 生死判定。
- 交易结算。
- 制度规则最终执行。

这些必须由模拟核心决定。

当前阶段不需要 API。默认认知实现是 `RuleBasedCognition`：

- 输入：角色需求、资源、职业、关系、最近记忆、最近事件。
- 输出：结构化 `Plan`。
- 执行：由 Simulation Core 校验并落地。

只有当规则式计划不足以表达对话、主观解释、复杂计划候选或记忆摘要时，才进入 LLM provider 阶段。

API 接入前必须先看上下文是否足够：

```powershell
python -m virtual_society.cli --days 5 --seed 7 --dump-cognition-context a1
```

如果这个上下文无法支持角色做出合理计划，先改上下文压缩和事件摘要，不急着接模型。

本机 Codex CLI 可以作为调试型 LLM provider，但不能无限制进入主循环。启用时必须设置调用预算：

```powershell
python -m virtual_society.cli --days 2 --seed 7 --cognition hybrid-codex-cli --llm-agent-ids a1 --llm-max-calls 1 --show-cognition-stats
```

原则：先用单角色验证计划质量，再决定是否扩大到更多角色或更多天数。

## 何时使用 3D

3D 应该在社会核心已经可以稳定运行后接入。否则会把时间花在场景、动画和交互上，而不是解决社会是否真实演化的问题。

早期可以只定义一个稳定协议：

- 世界状态快照。
- 事件流。
- 用户命令。
- 角色可视状态。

## 核心风险

### 状态爆炸

解决方式：分层模拟、摘要历史、事件重要性评分。

### LLM 幻觉污染状态

解决方式：LLM 输出结构化意图，核心模拟验证后才执行。

### 社会很快崩溃

解决方式：先用指标识别崩溃原因，再调规则，不用硬编码剧情救场。

### 社会长期停滞

解决方式：加入资源压力、社会欲望、创新机制和外部事件。

### 复杂但不可解释

解决方式：所有状态变化必须能追溯到事件、规则和输入。
