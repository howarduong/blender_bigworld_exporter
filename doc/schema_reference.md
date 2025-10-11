# BigWorld Blender Exporter - Schema Reference

本文件定义了导出文件的二进制结构规范。所有 Writer 模块必须严格遵循此文档，任何修改需团队评审并版本化。

---

## 文件头 (Header)

| 字段       | 类型   | 长度 | 说明 |
|------------|--------|------|------|
| magic      | char[4]| 4    | 固定为 `BWV\0` |
| version    | u32    | 4    | 引擎版本号 (2 或 3) |

对齐: 4 字节

---

## Section ID 分配表

| Section ID | 名称         | 模块                | 对齐 | 说明 |
|------------|--------------|---------------------|------|------|
| 0x1001     | Mesh         | primitives_writer   | 4    | 网格数据 (顶点/索引/法线/切线/UV/颜色/权重) |
| 0x2001     | Material     | material_writer     | 4    | 材质与纹理路径 |
| 0x3001     | Skeleton     | skeleton_writer     | 4    | 骨骼层级与绑定矩阵 |
| 0x3002     | HardPoint    | skeleton_writer     | 4    | 硬点 (挂点) |
| 0x4001     | Animation    | animation_writer    | 4    | 动画轨道 (骨骼关键帧) |
| 0x4002     | CueTrack     | animation_writer    | 4    | 动画事件 (Cue Track) |
| 0x5001     | Collision    | collision_writer    | 4    | 普通碰撞体 (Mesh) |
| 0x5002     | BSP          | collision_writer    | 4    | BSP 碰撞体 |
| 0x5003     | ConvexHull   | collision_writer    | 4    | 凸包 |
| 0x6001     | Portal       | portal_writer       | 4    | 门户 (类型/标签/几何) |
| 0x7001     | Prefab       | prefab_assembler    | 4    | 预制体与实例表 |
| 0x8001     | Hitbox       | hitbox_xml_writer   | 4    | Hitbox 数据 (二进制) |

---

## Mesh (0x1001)

| 字段         | 类型   | 说明 |
|--------------|--------|------|
| vertex_count | u32    | 顶点数量 |
| index_count  | u32    | 索引数量 |
| vertices     | f32[3] * N | 顶点位置 |
| normals      | f32[3] * N | 法线 |
| tangents     | f32[3] * N | 切线 |
| uvs          | f32[2] * N | UV 坐标 |
| colors       | f32[4] * N | 顶点颜色 (RGBA) |
| weights      | f32[4] * N | 骨骼权重 (占位) |
| indices      | u32 * M    | 三角形索引 (TODO: 确认是否 u16) |

对齐: 4 字节

---

## Material (0x2001)

| 字段          | 类型   | 说明 |
|---------------|--------|------|
| material_count| u32    | 材质数量 |
| name          | cstring| 材质名称 |
| base_color    | f32[4] | 漫反射颜色 (RGBA) |
| specular      | f32    | 高光强度 |
| alpha         | f32    | 透明度 |
| texture_path  | cstring| 纹理路径 (相对路径) |
| shader        | cstring| 着色器引用 |

对齐: 4 字节

---

## Skeleton (0x3001)

| 字段         | 类型   | 说明 |
|--------------|--------|------|
| bone_count   | u32    | 骨骼数量 |
| name         | cstring| 骨骼名称 |
| parent_index | i32    | 父骨骼索引 (-1 表示无父) |
| bind_matrix  | f32[16]| 绑定矩阵 (行主/列主需确认) |
| inv_bind     | f32[16]| Inverse Bind Pose (占位) |

---

## HardPoint (0x3002)

| 字段   | 类型   | 说明 |
|--------|--------|------|
| name   | cstring| 硬点名称 |
| type   | cstring| 硬点类型 (weapon/attach 等) |
| bone   | cstring| 绑定骨骼 |
| matrix | f32[16]| 矩阵 |

---

## Animation (0x4001)

| 字段       | 类型   | 说明 |
|------------|--------|------|
| name       | cstring| 动画名称 |
| duration   | f32    | 动画时长 (秒) |
| bone_count | u32    | 骨骼数量 |
| bone_track | struct | 每个骨骼的关键帧轨道 |

### Bone Track

| 字段       | 类型   | 说明 |
|------------|--------|------|
| bone_name  | cstring| 骨骼名称 |
| key_count  | u32    | 关键帧数量 |
| time       | f32    | 时间戳 (秒) |
| position   | f32[3] | 位置 |
| rotation   | f32[4] | 旋转 (四元数) |
| scale      | f32[3] | 缩放 |

---

## CueTrack (0x4002)

| 字段   | 类型   | 说明 |
|--------|--------|------|
| time   | f32    | 时间戳 (秒) |
| label  | cstring| 事件标签 |
| param  | cstring| 附加参数 |

---

## Collision (0x5001)

| 字段         | 类型   | 说明 |
|--------------|--------|------|
| vertex_count | u32    | 顶点数量 |
| index_count  | u32    | 索引数量 |
| vertices     | f32[3] * N | 顶点 |
| indices      | u32 * M    | 索引 (TODO: 确认是否 u16) |

---

## BSP (0x5002) / ConvexHull (0x5003)

占位，需对照旧插件实现。

---

## Portal (0x6001)

| 字段       | 类型   | 说明 |
|------------|--------|------|
| type       | cstring| 门户类型 (standard/heaven/exit/none) |
| label      | cstring| 门户标签 |
| geometry   | cstring| 几何来源 (BOUNDING_BOX/CUSTOM_MESH) |
| vertices   | f32[3] * N | 顶点 (若有) |
| indices    | u32 * M    | 索引 (若有) |

---

## Prefab (0x7001)

| 字段        | 类型   | 说明 |
|-------------|--------|------|
| group       | cstring| 预制体组名 |
| instance_count | u32 | 实例数量 |
| role        | cstring| 实例角色 |
| visible     | u32    | 可见性 (1/0) |
| matrix      | f32[16]| 变换矩阵 |

---

## Hitbox (0x8001)

| 字段   | 类型   | 说明 |
|--------|--------|------|
| name   | cstring| Hitbox 名称 |
| type   | cstring| Hitbox 类型 (box/sphere/capsule/mesh) |
| level  | cstring| 层级 (object/bone) |
| bone   | cstring| 绑定骨骼 |
| matrix | f32[16]| 矩阵 |

---

## 对齐规则

- 所有 Section 起始位置按 **4 字节对齐**。
- Section 内部字段按自然对齐 (u32/f32 → 4 字节)。
- 若有特殊对齐 (8/16)，需在对应 Section 定义中标注。

---

## TODO

- 确认 **索引类型 (u16/u32)**。
- 确认 **矩阵存储顺序 (行主/列主)**。
- 确认 **法线/切线重建算法** 与旧插件一致。
- BSP/ConvexHull 的具体结构待补充。
