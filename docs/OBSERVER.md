# Observer

M10a 提供一个同源 Web 观察器，挂在本地 API 的 `/observer`。

启动服务：

```powershell
python -m virtual_society.cli --serve --seed 7 --port 8765
```

打开：

```text
http://127.0.0.1:8765/observer
```

当前观察器包含：

- 核心指标条。
- 智能体社会地图。
- 组织状态列表。
- 指标曲线。
- 最近事件流。
- 推进 1 天、推进 7 天、投放食物、希望广播、风暴压力测试、重置。

设计边界：

- 页面不直接修改世界状态。
- 所有影响都通过 `/step` 或 `/interventions` 进入模拟核心。
- 当前是调试观察器，不是最终 3D 客户端。
- 后续可以把社会地图替换为 Three.js/WebGPU 场景，但协议仍然复用 M9 API。
