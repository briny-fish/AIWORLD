# 3D Observer

M10b 提供一个 Three.js 3D 观察器原型，挂在本地 API 的 `/observer3d`。

启动服务：

```powershell
python -m virtual_society.cli --serve --seed 7 --port 8765
```

打开：

```text
http://127.0.0.1:8765/observer3d
```

当前 3D 场景表达：

- 智能体：环绕公共中心的 3D 节点，颜色表示平均需求状态。
- 组织：地面上的蓝色凝聚力环，环的粗细和透明度随凝聚力变化。
- 资源：食物、材料、庇护所三个资源塔。
- 事件：外围事件标记，灾害/危机/组织/广播使用不同颜色。
- 公共中心：代表当前社会共同体。

交互：

- 点击智能体查看需求、计划、声望、组织归属。
- `1 Day` / `7 Days` 推进时间。
- `Food` 投放食物。
- `Broadcast` 发希望广播。
- `Storm` 制造压力测试。
- `Reset` 重置当前 seed。

设计边界：

- 3D 页面只调用 M9 API，不直接修改模拟状态。
- 当前通过 CDN 加载 Three.js，保持项目本体零依赖。
- 这是 Web 3D 原型，不是最终美术方向；它用于验证“可观察、可参与、可影响”的交互闭环。
- 后续可以替换成 Unity、Unreal、Godot 或本地 WebGPU 客户端，只要继续遵守 API 协议。
