# Virtual Society

这是一个长期项目：用社会模拟、3D 游戏技术和 LLM 创建一个可以自行发展、可观察、可参与、可影响的虚拟社会。

项目目标不是写剧情分支树，而是建立一套可运行的世界约束和生成式 agent 架构，让个人、资源、组织、关系、制度和环境在约束中自然演化。

## 快速运行

```powershell
python -m virtual_society.cli --days 30 --seed 7 --show-plans
```

运行 12 人生成式 Alpha 预设：

```powershell
python -m virtual_society.cli --days 30 --seed 7 --world-preset generative_alpha --show-plans
```

生成离线报告：

```powershell
python -m virtual_society.cli --days 30 --seed 7 --world-preset generative_alpha --snapshot-every 7 --save-run-json artifacts/run-generative-alpha-30.json --save-run-html artifacts/run-generative-alpha-30.html
```

运行 Alpha 风暴压力测试：

```powershell
python -m virtual_society.cli --days 30 --seed 7 --world-preset generative_alpha --intervention-file scenarios/generative-alpha-storm.json --snapshot-every 5 --save-run-html artifacts/run-generative-alpha-storm-30.html
```

运行多 seed 实验：

```powershell
python -m virtual_society.cli --days 365 --experiment-seeds 1,2,3,4,5 --report-every 365
```

启动本地 API 和观察器：

```powershell
python -m virtual_society.cli --serve --port 8765
```

打开：

- `http://127.0.0.1:8765/observer3d`
- `http://127.0.0.1:8765/observer`
- `http://127.0.0.1:8765/state`

## 当前能力

- 固定 seed 的确定性模拟。
- 每日事件日志和健康指标。
- 资源、地点、路线、组织和组织间交换。
- 观察者干预：资源、灾害、规则法令、新角色、广播、组织。
- 2D Web 观察器和 Three.js 3D 观察器。
- 离线 JSON/HTML 报告。
- 多 seed 长跑实验。
- LLM 接入契约、Codex CLI debug provider、混合认知降级策略。
- 生成式 agent 基座：身份档案、结构化记忆流、记忆检索、周期反思。
- 12 人 `generative_alpha` 预设：多地点、多组织、组织交换和社交对话。
- 社会可信度评估：记忆覆盖、反思覆盖、对话密度、组织参与和信任饱和风险。

## 项目文档

- [项目宪章](docs/PROJECT_CHARTER.md)
- [系统架构](docs/ARCHITECTURE.md)
- [生成式社会调研](docs/GENERATIVE_SOCIETY_RESEARCH.md)
- [生成式 agent 架构](docs/GENERATIVE_AGENT_ARCHITECTURE.md)
- [Generative Society Alpha](docs/GENERATIVE_SOCIETY_ALPHA.md)
- [下一步里程碑](docs/NEXT_MILESTONES.md)

## LLM 接入说明

当前不需要 OpenAI API key 也能运行完整模拟。默认 provider 是确定性的 `RuleBasedCognition`。

本机 Codex CLI provider 可以复用 Codex/ChatGPT 登录状态，用于单个角色计划调试：

```powershell
python -m virtual_society.cli --days 5 --seed 7 --codex-cli-plan-agent a1 --codex-cli-model gpt-5.4-mini
```

真实批量 LLM 模拟会在 M16 接入 OpenAI API provider。届时会需要 API key，并会加入缓存、预算、失败降级和运行记录。

当前已经有 OpenAI Responses API provider 代码边界，可通过环境变量 `OPENAI_API_KEY` 启用：

```powershell
python -m virtual_society.cli --days 7 --seed 7 --world-preset generative_alpha --cognition hybrid-openai --llm-agent-ids a1 --llm-every-days 7 --llm-max-calls 1
```
