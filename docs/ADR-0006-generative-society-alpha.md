# ADR-0006: Pivot To Generative Society Alpha

## Status

Accepted.

## Context

M12 已经证明资源、地点、路线和组织交换可以稳定运行。但继续在少数角色上增加规则，会让项目变成规则表越来越复杂的模拟器，不能自然走向最终目标。

用户明确指出：不能永远做最小半成品，也不能只复制 Stanford 小镇。

## Decision

从 M13/M14 开始，项目转向生成式社会架构：

- 规则系统保留为世界约束层。
- agent 社会行为转向身份、记忆、检索、计划、对话、反思和关系解释。
- LLM 作为可替换 provider 进入认知层。
- Simulation Core 仍然是唯一状态裁判。
- M14 以完整 Alpha 切片为目标，不以最小 demo 为目标。

## Consequences

正面影响：

- 后续可以接入真实 LLM，而不让 LLM 直接破坏世界状态。
- agent 行为有连续性和可解释上下文。
- 用户干预可以通过记忆、关系和制度传播，而不是走预设分支。

代价：

- 需要更多运行记录和评估。
- 需要控制 LLM 成本和不确定性。
- 世界规则、agent 记忆和观察器必须一起演进。

## First Implementation

本决策的第一步实现：

- `AgentProfile`
- `MemoryItem`
- `memory_stream`
- `retrieve_memories`
- weekly reflections
- LLM context with profile, retrieved memories, and reflections
