# Generative Society Research Notes

本阶段调研的结论是：Stanford Smallville 是重要起点，但不能成为唯一范式。我们的目标需要吸收它的 agent 认知结构，同时吸收更强的世界约束、技能积累和评估框架。

## 参考项目

### Generative Agents

来源：[Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)

可采用：

- memory stream: agent 持续记录经历。
- retrieval: 按相关性、重要性、近期性提取上下文。
- reflection: 从经历中抽象出更高层的想法。
- planning: 先生成日程或计划，再落到具体行动。

不直接复制：

- 小镇 demo 的世界约束较轻，不足以承担长期资源、制度和冲突演化。
- 对话和日程很强，但社会物理、经济和制度反馈不足。

对本项目的影响：

- M14 必须先补齐记忆、反思和计划循环。
- 世界状态仍由模拟核心结算，LLM 只提出意图。

### Concordia

来源：[Google DeepMind Concordia](https://github.com/google-deepmind/concordia)

可采用：

- 把模拟拆成 agent、component、game master。
- Game master 负责把自然语言行动结算为世界状态变化。
- 支持多个实验场景，而不是绑定一个小镇。

不直接复制：

- Concordia 更偏研究框架，不是面向 3D 观察、长期运行和用户参与的产品。

对本项目的影响：

- 我们的 Simulation Core 相当于可测试的 GM。
- 每个 agent 的认知组件必须可以单独替换、测试、预算控制。

### Voyager

来源：[Voyager: An Open-Ended Embodied Agent with Large Language Models](https://arxiv.org/abs/2305.16291)

可采用：

- lifelong learning 思路。
- 把成功经验沉淀为可复用技能。
- 让 agent 在环境反馈中改进，而不是只在 prompt 中变聪明。

不直接复制：

- Voyager 面向 Minecraft 单 agent 探索，本项目是多 agent 社会。

对本项目的影响：

- M16 之后可以加入 agent 技能库，例如“组织救灾会议”“修复路线”“建立交换协议”。
- 技能必须由世界验证，不能是纯文本自我声明。

### SOTOPIA

来源：[SOTOPIA: Interactive Evaluation for Social Intelligence in Language Agents](https://arxiv.org/abs/2310.11667)

可采用：

- 用社会任务评估语言 agent，而不只评估文本质量。
- 关注目标达成、关系处理、社会规范和互动质量。

不直接复制：

- SOTOPIA 主要是评估环境，不是持续世界模拟。

对本项目的影响：

- M15 要建立社会可信度评估，不只看平均需求和资源是否稳定。
- 评估必须覆盖关系连续性、干预反应、冲突后恢复和制度一致性。

## 结论

当前正确路线不是“复制 Stanford 小镇”，也不是“扩写更多规则”。正确路线是：

1. 保留现有世界约束层，保证长期运行不会失控。
2. 引入生成式 agent 架构，保证社会行为来自记忆、关系、目标和局部推理。
3. 引入评估框架，防止我们误把稳定数值当成真实社会。
4. 在小规模 Alpha 中做完整闭环，再扩展聚落、人口和 3D 表现。
