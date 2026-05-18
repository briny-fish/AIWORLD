# Logistics

M12b-M12f 的目标是让“地点”不只是 3D 观察器里的坐标，而是会影响生存稳定性、经济效率、制度能力和组织关系的模拟结构。

## Resource Model

`WorldState.resources` 是全局汇总，不再是唯一事实来源。每个 `Location.resources` 保存本地库存，模拟核心在资源变化后调用同步逻辑，把地点库存汇总到全局指标。

当前资源流：

- `farm`: 在 `north_field` 增加食物，并受地点 `production.food` 和 `condition` 影响。
- `gather`: 在 `woodlot` 增加材料，并受地点 `production.materials` 和 `condition` 影响。
- `repair`: 消耗 `workshop` 材料，在 `shelter_house` 增加庇护，并受 `workshop` 的 `production.shelter` 影响。
- `haul`: 把食物搬到 `commons`，或把材料搬到 `workshop`。
- `exchange`: 组织按库存目标和交换偏好进行资源交换。
- meals: 只消费 `commons` 和 `shelter_house` 的食物。
- upkeep: 庇护资源会按人口折旧。
- disaster: 从地点库存中分布式扣除资源。

## Active Hauling

智能体会在这些情况下优先考虑 `haul`：

- 公共食物仓库低于目标，且远端地点有可搬运食物。
- 工坊材料低于目标，且其他地点有可搬运材料。
- 修理计划被工坊材料短缺阻塞，但社会仍有材料。

如果没有有效路线，`haul` 不会凭空搬运无关资源，而是记录为无可用路线并恢复少量能量。

## Route Network

地点通过 `connected_location_ids` 形成运输网络。路线按无向连接处理，因为当前世界还没有单向道路或通行权。

运输规则：

- 只有可达地点之间可以搬运或交换。
- 直接连接距离为 1，多跳路线距离更高。
- 距离越高，主动搬运和组织交换的有效容量越低。
- 距离越高，主动搬运的能量成本越高。
- 路线地点状态越差，运输能力越差。
- 当天路线负载记录在 `WorldState.route_loads`。
- 重载超过软容量后会产生 `route_strain`，并磨损路线两端地点。

## Organization Exchange

M12f 增加组织经济层：

- 每个组织有 `home_location_id`，表示它的主要库存地点。
- 每个组织有 `inventory_targets`，表示它希望在家园地点保有多少资源。
- 每个组织有 `exchange_preferences`，表示它愿意优先交换哪些资源。
- 如果一个组织低于库存目标，另一个组织在自己家园地点有明确盈余，且路线可达，就会发生 `exchange`。
- 一天中完成多条交换时会记录 `market` 事件。
- 食物交换只允许流向 `commons` 或 `shelter_house`，避免把可消费食物调去非用餐地点。

这个机制让资源差异开始自然产生交易和援助。后续只需要加入跨聚落信任、拒绝交易和封锁，就能演化出冲突压力。

## Common Supply Routes

公共供给路线是制度能力的基础物流层。每天行动结束、晚餐分配前，公共组织会尝试把远端食物送到共享仓库。

路线能力由两部分构成：

- `supply_route_base_capacity`: 基础运输能力。
- `supply_route_cohesion_capacity`: 由组织凝聚力放大的运输能力。

路线能力不是无限的，因此物流失效仍然会造成配给和饥荒。

## Common Maintenance

公共维护是 M12e 的维护闭环：

- 地点按 `maintenance_need` 承受日常状态衰减。
- 庇护资源按人口日常折旧。
- 如果公共组织凝聚力足够，且 `workshop` 有材料，会优先维护低状态地点。
- 维护材料从 `workshop` 消耗，并通过路线网络产生路线负载。

材料现在既是修理输入，也是维持空间经济系统的基础资源。

## Stability Baseline

已验证：

- 单元测试：56 tests OK。
- `python -m compileall virtual_society tests`: OK。
- 365 天、5 seed 长跑：全部 `stable`。
- 当前长跑没有低幸福度、社会断裂或制度崩溃。

## Next Extension

M12g 应该把组织交换推进为多聚落经济：

- 第二聚落或外围营地。
- 跨聚落库存目标和交换路线。
- 援助、拒绝交易、封锁和跨组织信任变化。
- 迁移、联盟和冲突的前置条件。
