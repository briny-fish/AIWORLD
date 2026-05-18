# ADR-0004: Codex CLI Provider 先作为调试入口

## 状态

Accepted

## 背景

本机 Codex CLI 可以通过 ChatGPT 登录态执行 `codex exec`，因此不需要单独配置 `OPENAI_API_KEY`。但一次调用会启动完整 Codex agent 流程，包含上下文、插件加载和网络请求，延迟和成本都明显高于直接 API 调用。

## 决策

实现 `CodexCliCognition`，但默认不用于每日模拟循环。CLI 只提供单角色调试入口：

```powershell
python -m virtual_society.cli --days 5 --seed 7 --codex-cli-plan-agent a1
```

## 后果

我们可以立即验证真实模型是否能基于社会上下文生成结构化计划。长期运行阶段仍需要更轻量的 provider，例如直接 API、批量请求或本地模型。

