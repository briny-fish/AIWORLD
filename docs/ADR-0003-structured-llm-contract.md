# ADR-0003: LLM 必须通过结构化计划契约接入

## 状态

Accepted

## 背景

LLM 很适合生成解释、计划候选和自然语言，但不适合作为世界事实来源。虚拟社会需要长期运行、复现和审计，因此外部模型输出不能直接修改状态。

## 决策

LLM provider 必须遵守结构化计划契约：

1. 输入来自 `build_cognition_context`。
2. 提示词由 `render_plan_prompt` 生成或遵循同等约束。
3. 输出必须是 JSON 对象。
4. 输出必须通过 `parse_plan_response`。
5. 解析后的 `Plan` 仍由 Simulation Core 校验。

## 后果

外部模型可以替换认知候选生成逻辑，但不能绕过模拟核心。没有 API 时，项目继续使用 `RuleBasedCognition`。

