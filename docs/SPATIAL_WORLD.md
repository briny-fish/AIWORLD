# Spatial World

M12a 引入空间层，M12b-M12f 把空间层从显示结构推进为真实模拟结构。

## Locations

当前地点：

- `commons`: 公共场地，社会活动和公共仓库中心。
- `north_field`: 田地，主要食物生产地点。
- `woodlot`: 林地，主要材料采集地点。
- `workshop`: 工坊，修理、维护和材料加工地点。
- `shelter_house`: 庇护所，休息、安全和部分食物储备地点。

每个智能体都有 `location_id`。行动会改变位置：

- `farm` -> `north_field`
- `gather` -> `woodlot`
- `haul` -> 根据物流路线移动到目标仓库或工坊
- `repair` -> `workshop`
- `rest` -> `shelter_house`
- `socialize` -> 目标角色所在地点，或 `commons`

## Location State

地点有 `condition`、`resources`、`production` 和 `maintenance_need`：

- `condition` 影响生产和运输效率。
- `resources` 是地点本地库存，全局资源只是地点库存的汇总。
- `production` 表示地点专长，例如田地更擅长生产食物，林地更擅长生产材料。
- `maintenance_need` 表示地点日常维护压力，维护压力会让状态缓慢下降。

地点不是装饰结构：劳动、运输、拥堵、维护、修理和组织交换都会改变它。

## Logistics

食物生产后先进入 `north_field`，不会自动变成可消费食物。社会需要把食物运到 `commons` 或 `shelter_house` 后，晚餐分配才会消费它。

物流有三层：

- 主动搬运：智能体执行 `haul`。
- 公共供给路线：组织凝聚力越高，每天可自动维持越多基础运输能力。
- 组织交换：组织根据库存目标和交换偏好在家园地点之间转移资源。

运输必须走 `connected_location_ids` 定义的地点网络。断开的地点无法搬运或交换；多跳路线会降低有效运力并增加能量成本。

## Organization Economy

组织现在有空间边界：

- `home_location_id`: 组织主要库存地点。
- `inventory_targets`: 组织希望维持的库存目标。
- `exchange_preferences`: 组织交换资源的偏好。

当前初始组织：

- `household_north`: 家园在 `north_field`。
- `household_south`: 家园在 `shelter_house`。
- `common_council`: 家园在 `commons`。
- `maker_guild`: 家园在 `workshop`。

这让资源不再只是地点之间移动，也开始成为组织之间的关系。

## Maintenance Economy

M12e 加入了维护经济：

- 庇护资源会日常折旧，避免无限累积。
- 地点状态会因维护负担缓慢下降。
- 公共组织会消耗 `workshop` 的材料维护低状态地点。
- 运输会记录当天路线负载，重载路线会产生 `route_strain` 并磨损连接地点。

## Observation

2D 观察器显示地点库存、地点专长和组织库存目标。3D 观察器会渲染地点路线，路线当天负载越高，线条越粗、越偏琥珀色。

## Current Boundary

地点库存、路线网络、生产专长、维护成本、路线负载和组织交换已经可运行。下一步 M12g 会加入第二聚落或外围营地，让贸易、援助、拒绝交易、封锁和迁移有真实边界。
