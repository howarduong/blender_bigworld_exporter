好的 ✅，Rick。我来为你整理一份 **最终定版方案（长文档）**，把我们之前所有的讨论、改进和定版内容完整汇总，形成一份可以直接保存的文档。  

---

# BigWorld Blender Exporter 最终定版方案

---

## 1. 总体目标与原则

- **目标**  
  构建一个 **Blender 插件**，完整替代原有 **3ds Max BigWorld 插件**，实现与 BigWorld 引擎导出文件 **逐字节对齐**。  
  确保团队在 Blender 环境下能无缝生产 3D 资产，导出文件能直接进入 BigWorld 引擎生产线。

- **原则**  
  1. **全面对齐**：所有导出文件结构、字段顺序、对齐规则必须与 3ds Max 插件一致。  
  2. **模块化**：每个功能（网格、材质、骨骼、动画、碰撞、门户、预制、Hitbox、Cue Track）独立 Writer 模块。  
  3. **可维护性**：代码结构清晰，UI 与导出逻辑分离，便于后续扩展。  
  4. **团队协作**：所有参数、字段、导出规则必须有文档（schema_reference.md）作为唯一真相来源。  
  5. **验证闭环**：每个模块导出后必须通过 `validators/hex_diff.py` 与 3ds Max 插件产物对比，确保一致。  

---

## 2. 插件目录结构

```
blender_bigworld_exporter/
├── __init__.py                # 插件入口，注册/注销
├── preferences.py              # 插件全局设置（Addon Preferences）
├── ui_panel.py                 # N 面板 UI（对象级参数）
├── export_operator.py          # 导出入口（File > Export）
│
├── core/                       # 核心 Writer 模块
│   ├── binsection_writer.py
│   ├── primitives_writer.py
│   ├── material_writer.py
│   ├── skeleton_writer.py
│   ├── animation_writer.py
│   ├── collision_writer.py
│   ├── portal_writer.py
│   ├── prefab_assembler.py
│   ├── hitbox_xml_writer.py
│   └── utils.py
│
├── validators/                 # 校验工具
│   ├── structure_checker.py
│   ├── hex_diff.py
│   └── path_validator.py
│
└── docs/
    └── schema_reference.md     # 导出文件权威规范
```

---

## 3. 核心模块说明

- **binsection_writer.py**  
  提供 `BinWriter`、`BWHeaderWriter`，负责二进制写入、文件头。  

- **primitives_writer.py**  
  导出网格（顶点、索引、法线、切线、UV、颜色、权重）。  

- **material_writer.py**  
  导出材质与纹理路径。  

- **skeleton_writer.py**  
  导出骨骼层级、绑定矩阵、硬点。  

- **animation_writer.py**  
  导出骨骼动画轨道、Cue Track。  

- **collision_writer.py**  
  导出碰撞体（Mesh、BSP、ConvexHull）。  

- **portal_writer.py**  
  导出门户（类型、标签、几何）。  

- **prefab_assembler.py**  
  导出预制体与实例表。  

- **hitbox_xml_writer.py**  
  导出 Hitbox（XML + 二进制）。  

- **validators/**  
  - `structure_checker.py`：校验导出文件结构是否符合 schema。  
  - `hex_diff.py`：逐字节对比 Blender 与 3ds Max 导出文件。  
  - `path_validator.py`：校验资源路径是否存在。  

---

## 4. UI 设计与定版

### 4.1 N 面板（对象级参数）
```
[BigWorld 导出参数]

▶ 转换参数
   [✔] 坐标轴映射 (Y→Z)
   单位缩放: 1.0
   [✔] 翻转面绕序
   [✔] 重建法线/切线
   法线阈值(度): 45.0

▶ 分组与 LOD
   LOD 等级: 0
   分组索引: 0
   分割策略: [字符串]

▶ 碰撞与几何派生
   [ ] 标记为碰撞体
   [ ] 标记为 BSP
   [ ] 标记为 凸包
   精度: [float32/float16]

▶ Hitbox
   名称: [字符串]
   类型: [Box/Sphere/Capsule/Mesh]
   层级: [Object/Bone]

▶ 门户
   类型: [Standard/Heaven/Exit/None]
   标签: [字符串]
   几何来源: [Bounding Box/Custom Mesh]

▶ 预制与实例
   预制体组: [字符串]
   实例角色: [字符串]
   [✔] 可见性

▶ 硬点
   名称: [字符串]
   类型: [字符串]
   绑定骨骼: [字符串]

▶ 动画事件
   事件列表(JSON): [...]
```

---

### 4.2 导出对话框（全局参数）
```
[导出路径与版本]
   导出根目录: [路径选择]
   引擎版本: [2.x / 3.x]
   坐标系模式: [与3ds Max兼容 / Blender原生]

[缩放与应用]
   默认缩放: 1.0
   [ ] 应用缩放到几何

[范围与集合]
   [✔] 仅导出选中对象
   [ ] 导出所在集合

[校验与日志]
   [ ] 启用结构校验（严格）
   [ ] 启用十六进制差异比对
   [ ] 输出详细日志

[导出模块]
   [✔] 网格 (Mesh)
   [✔] 材质 (Material)
   [✔] 骨骼 (Skeleton)
   [ ] 动画 (Animation)
   [ ] 碰撞 (Collision)
   [ ] 门户 (Portal)
   [ ] 预制/实例表 (Prefab/Instances)
   [ ] Hitbox / XML
   [ ] 事件轨道 (Cue Track)

[高级选项]
   [ ] 校验资源路径
   [ ] 自动修复路径
```

---

## 5. 导出流程与模块开关逻辑

1. **用户操作**  
   - 在 N 面板设置对象级参数。  
   - 在导出对话框设置全局参数。  

2. **Operator 执行**  
   - 写入文件头。  
   - 遍历对象。  
   - 根据模块开关调用对应 Writer。  

3. **Writer 模块**  
   - 每个 Writer 写入一个 Section，遵循 schema_reference.md。  

4. **校验与日志**  
   - 根据 UI 开关调用 `validators/` 工具。  

---

## 6. 功能描述

- **Mesh**：顶点、索引、法线、切线、UV、颜色、权重。  
- **材质**：材质参数、纹理路径、着色器引用。  
- **骨骼**：骨骼层级、绑定矩阵、硬点。  
- **动画**：骨骼动画轨道、关键帧、Cue Track。  
- **碰撞**：Mesh 碰撞体、BSP、ConvexHull。  
- **门户**：Portal 类型、标签、几何。  
- **预制**：Prefab 组与实例表。  
- **Hitbox**：Hitbox 二进制与 XML。  
- **校验工具**：结构校验、Hex Diff、路径校验与修复。  

---

## 7. 流程描述（用户视角）

1. 在 N 面板设置对象参数（如勾选“碰撞体”）。  
2. 打开导出对话框，设置全局参数（如选择导出模块）。  
3. 点击导出 → 插件写入文件头 → 遍历对象 → 调用 Writer → 写入 Section。  
4. 导出完成后执行校验（结构、Hex Diff、路径）。  
5. 输出日志，提示导出成功或错误。  

---

---

## 8. 参考文献（完整）

- **BigWorld MAXScripts (3ds Max 插件源码)**  
  https://github.com/howarduong/BigWorld_MAXScripts  
  > 我们的所有 Section ID、字段顺序、导出逻辑都必须对照此仓库，确保逐字节对齐。

- **BigWorld Engine 文档（BNF 格式说明）**  
  内部资料，用于确认 primitives、binsection、animation 等文件格式。  

- **Blender API 文档**  
  https://docs.blender.org/api/current/  
  > 用于实现 UI、PropertyGroup、ExportHelper、bpy.types.Object 属性挂载。

- **团队内部规范**  
  - `docs/schema_reference.md`：唯一真相来源，定义所有 Section 结构。  
  - 导出 UI Mockup（ASCII 定版）：确保 UI 命名、分组一致。  
  - 验证工具使用手册：说明如何运行 `structure_checker.py`、`hex_diff.py`、`path_validator.py`。  

---

## 9. 验证与对齐方案

### 9.1 验证目标
- 确保 Blender 插件导出的文件与 3ds Max 插件导出的文件 **逐字节一致**。  
- 确保所有 Section 顺序、字段对齐、默认值完全一致。  

### 9.2 验证工具
- **structure_checker.py**  
  - 输入：导出文件  
  - 输出：检查 Section 顺序、长度、对齐是否符合 schema_reference.md  

- **hex_diff.py**  
  - 输入：Blender 导出文件 + 3ds Max 导出文件  
  - 输出：逐字节差异报告（偏移量、期望值、实际值）  

- **path_validator.py**  
  - 输入：导出文件中的路径引用  
  - 输出：检查路径是否存在，是否为相对路径，是否大小写一致  

### 9.3 验证流程
1. 使用 Blender 插件导出一个最小场景（Cube + 材质 + 骨骼）。  
2. 使用 3ds Max 插件导出同样场景。  
3. 运行 `structure_checker.py` → 确认结构正确。  
4. 运行 `hex_diff.py` → 确认逐字节一致。  
5. 如果有差异 → 定位到具体 Writer 模块修复。  
6. 运行 `path_validator.py` → 确认所有纹理路径有效。  

---

## 10. 后续扩展计划

- **动画系统完善**  
  - Cue Track 导出  
  - 动画事件绑定  
  - 支持多 Action 导出  

- **碰撞系统扩展**  
  - BSP、ConvexHull 完整实现  
  - 碰撞体优化（合并、简化）  

- **Prefab/Instances**  
  - 支持复杂实例表导出  
  - 与场景集合绑定  

- **Hitbox 系统**  
  - 完整 XML 导出  
  - 与骨骼绑定的 Hitbox  

- **高级校验**  
  - 自动修复路径（大小写、相对路径转换）  
  - 导出后自动运行 Hex Diff（CI 集成）  

- **团队协作**  
  - 将 schema_reference.md 与 UI Mockup 固化为版本化文档  
  - 每次修改必须通过 Code Review 与验证工具  

---

# ✅ 最终总结

这份 **BigWorld Blender Exporter 最终定版方案** 包含：

1. 总体目标与原则  
2. 插件目录结构  
3. 核心模块说明  
4. UI 设计与定版（N 面板 + 导出对话框）  
5. 导出流程与模块开关逻辑  
6. 功能描述  
7. 流程描述（用户视角）  
8. 参考文献  
9. 验证与对齐方案  
10. 后续扩展计划  

它既是 **开发规范**，也是 **团队协作手册**，同时也是 **验证闭环的执行指南**。  

---


---

# BigWorld Blender Exporter 开发进度清单

## ✅ 当前已完成（已开发 & 基本可用）
- **插件框架**
  - `__init__.py` 插件入口，注册/注销逻辑完整
  - 目录结构（core / validators / docs）已建立
- **UI**
  - N 面板（对象级参数）已实现，支持折叠/展开，参数完整
  - 导出对话框（全局参数）已实现，包含路径、版本、缩放、范围、校验、模块开关、高级选项
- **Writer 模块（初版）**
  - `binsection_writer.py`：文件头、二进制写入
  - `primitives_writer.py`：网格导出（顶点、索引、法线、切线、UV、颜色、权重）
  - `material_writer.py`：材质导出（基础参数、纹理路径）
  - `skeleton_writer.py`：骨骼层级、绑定矩阵
- **验证工具**
  - `structure_checker.py`：检查 Section 顺序、对齐
  - `hex_diff.py`：逐字节对比 Blender 与 3ds Max 文件
  - `path_validator.py`：路径存在性检查

---

## 🟡 待开发功能
- **动画系统**
  - `animation_writer.py`：关键帧轨道完整实现
  - Cue Track 导出（事件轨道）
- **碰撞系统**
  - `collision_writer.py`：BSP、ConvexHull 支持
- **门户系统**
  - `portal_writer.py`：Portal 几何导出（Bounding Box / Custom Mesh）
- **预制系统**
  - `prefab_assembler.py`：Prefab 组与实例表导出
- **Hitbox 系统**
  - `hitbox_xml_writer.py`：XML 导出 + 二进制矩阵绑定
- **高级选项**
  - 自动修复路径（大小写、相对路径转换）
  - 索引类型选择（u16/u32）
  - 矩阵存储方式选择（行主/列主）

---

## 🔵 待测试功能
- **最小场景导出验证**
  - Cube + 材质 + 骨骼 → Blender vs 3ds Max Hex Diff
- **模块单测**
  - Mesh 导出 → 验证顶点/索引一致性
  - Material 导出 → 验证纹理路径一致性
  - Skeleton 导出 → 验证骨骼层级、矩阵一致性
- **校验工具**
  - structure_checker → 确认 Section 顺序正确
  - hex_diff → 确认逐字节一致
  - path_validator → 确认路径有效

---

## 🚀 下一步开发计划
1. **短期（近期迭代）**
   - 完成 `animation_writer.py`（骨骼动画轨道 + Cue Track）
   - 完成 `collision_writer.py` 的 BSP/ConvexHull
   - 增加导出对话框的高级选项（索引类型、矩阵存储方式）
   - 跑通最小验证闭环（Cube + 材质 + 骨骼 + 动画）

2. **中期（功能补齐）**
   - 实现 PortalWriter（门户导出）
   - 实现 PrefabAssembler（预制体导出）
   - 实现 Hitbox XML + 二进制导出
   - 增加路径自动修复逻辑

3. **长期（优化与扩展）**
   - 导出性能优化（批量写入、缓存）
   - 自动化测试（CI 集成 Hex Diff）
   - 团队文档化（schema_reference.md 固化版本，UI Mockup 固化）

---
**好的 ✅，Rick。下面是我们参考过的关键链接清单，每个条目都包含：链接地址、主要内容、功能说明，以及我们在开发中参考的部分。**

---

## 📚 参考链接清单（详细说明）

### 1. **BigWorld_MAXScripts GitHub 仓库**
- **链接**：[https://github.com/howarduong/BigWorld_MAXScripts](https://github.com/howarduong/BigWorld_MAXScripts)  
- **内容**：这是原始的 **3ds Max BigWorld 插件脚本集合**，包含宏脚本、启动脚本、导入导出工具、材质库、帮助文档等。  
- **功能**：  
  - 提供了 BigWorld 引擎在 3ds Max 下的完整工具链。  
  - 包含 **导出 Visual（模型）**、**导出 Animation（动画）**、**添加碰撞体（Hull/BSP）**、**添加 Portal**、**添加 HardPoint**、**导出 Hitbox XML** 等功能。  
- **我们参考的部分**：  
  - **Section ID 与字段顺序**（例如 Mesh、Material、Skeleton、Animation 的导出格式）。  
  - **UI 设计思路**（3ds Max 工具栏按钮 → 我们在 Blender 中改为 N 面板 + 导出对话框）。  
  - **功能覆盖范围**（确保 Blender 插件的导出模块与 Max 插件一致）。  

---

### 2. **BigWorld MAXScripts 功能说明页面**
- **链接**：[https://howarduong.github.io/github.io/content_creation/46_bigworld_maxscripts.htm](https://howarduong.github.io/github.io/content_creation/46_bigworld_maxscripts.htm)  
- **内容**：详细介绍了 BigWorld MAXScripts 的安装方法、功能按钮、使用流程。  
- **功能**：  
  - **导出 Visual 和 Animation**（支持全选导出或仅选中导出）。  
  - **添加 Custom Hull**（自定义碰撞体）。  
  - **Portal 标签与几何设置**。  
  - **Hitbox 附加与 XML 导出**。  
  - **Prefab Assembler**（预制体组装）。  
- **我们参考的部分**：  
  - **功能清单** → 确保 Blender 插件的导出模块覆盖相同功能。  
  - **操作流程** → 例如 “Export Selected vs Export All”，我们在 Blender 导出对话框里对应为 “仅导出选中对象”。  
  - **命名规范** → Hull、Portal、Hitbox 的命名方式。  

---

### 3. **BigWorld 引擎相关资料（KBEngine/BigWorld 架构）**
- **链接**：[知乎文章：基于KBEngine（BigWorld）的完整游戏Demo及部署流程](https://zhuanlan.zhihu.com/p/30510145998)  
- **内容**：介绍了 BigWorld/KBEngine 的整体架构，包括 LoginApp、BaseApp、CellApp、DBProxy 等。  
- **功能**：  
  - 解释了 BigWorld 引擎的 **分布式架构** 和 **大地图切分方案**。  
  - 说明了 **Prefab、Portal、Collision** 在引擎运行时的作用。  
- **我们参考的部分**：  
  - **Portal 与 Prefab 的引擎语义** → 确保导出数据能被引擎正确识别。  
  - **Hitbox 与骨骼绑定** → 确认 Hitbox 的用途和导出必要性。  

---

### 4. **BigWorld 开源版（OSE）介绍**
- **链接**：[CSDN 博客：探索广阔无垠的游戏世界：BigWorld 开源版](https://blog.csdn.net/gitblog_00009/article/details/139850191)  
- **内容**：介绍了 BigWorld Open-Source Edition（OSE）的功能与特点。  
- **功能**：  
  - 提供了 **服务器、客户端、工具链** 的开源实现。  
  - 强调 **负载均衡、可扩展性、故障容错**。  
- **我们参考的部分**：  
  - **确认 BigWorld 工具链的开放性** → 我们的 Blender 插件可以对接 OSE。  
  - **文档与工具链说明** → 确认导出文件在 OSE 下同样可用。  

---

## 🔑 总结
- **GitHub 仓库**（[1]） → 我们的 **核心对照源**，确保导出文件逐字节对齐。  
- **功能说明页面**（[2]） → 我们的 **功能清单参考**，确保 Blender 插件覆盖所有模块。  
- **知乎 KBEngine 文章**（[4]） → 我们的 **引擎语义参考**，确保导出数据能被引擎正确使用。  
- **BigWorld OSE 介绍**（[5]） → 我们的 **未来兼容性参考**，确保插件能支持开源版引擎。  

---


---

# BigWorld Blender Exporter  
## 代码构建需求与标准清单

---

### 1. **目录与模块规范**
- 插件必须遵循既定目录结构（`__init__.py`、`preferences.py`、`ui_panel.py`、`export_operator.py`、`core/`、`validators/`、`docs/`）。  
- 每个功能模块独立成文件（如 `primitives_writer.py`、`material_writer.py`），避免单文件过大。  
- 所有 Writer 模块必须依赖 `binsection_writer.py`，禁止重复实现二进制写入逻辑。  
- `docs/schema_reference.md` 是唯一真相来源，所有导出逻辑必须对照此文档。  

---

### 2. **代码风格与规范**
- **语言**：Python 3.10+，遵循 Blender API 规范。  
- **命名规范**：  
  - 类名：`PascalCase`（如 `PrimitivesWriter`）  
  - 函数名/变量名：`snake_case`（如 `write_mesh`、`export_root`）  
  - 常量：`UPPER_CASE`  
- **注释要求**：  
  - 每个模块文件开头必须有功能说明。  
  - 每个类、函数必须有 docstring，说明输入、输出、用途。  
  - 关键逻辑必须有行内注释，特别是二进制写入部分。  
- **行宽**：不超过 100 字符。  
- **缩进**：4 空格，不允许 Tab。  

---

### 3. **UI 与属性规范**
- 所有对象级参数必须定义在 `BigWorldObjectSettings`（PropertyGroup）中。  
- 所有全局参数必须定义在 `EXPORT_OT_bigworld`（Operator 属性）中。  
- UI 分组必须与定版 Mockup 一致（路径与版本、缩放与应用、范围与集合、校验与日志、导出模块、高级选项）。  
- 属性命名必须与 schema_reference.md 对应，避免歧义。  

---

### 4. **导出逻辑规范**
- 遍历对象时必须检查 `hasattr(obj, "bw_settings")`，避免报错。  
- 每个 Writer 模块必须：  
  - 接收对象数据 + 导出选项  
  - 严格按照 schema 写入 Section  
  - 返回写入状态（成功/失败）  
- 导出文件必须包含文件头（`BWHeaderWriter`），并写入正确版本号。  
- 所有导出必须支持 **仅选中对象** 与 **全场景导出** 两种模式。  

---

### 5. **校验与测试规范**
- 每个模块开发完成后，必须通过以下验证：  
  - **结构校验**：`validators/structure_checker.py`  
  - **Hex Diff**：与 3ds Max 插件导出结果逐字节对比  
  - **路径校验**：`validators/path_validator.py`  
- 所有测试场景必须包含：  
  - 最小场景（Cube + 材质 + 骨骼）  
  - 动画场景（骨骼 + 动画轨道）  
  - 碰撞体场景（Mesh + 碰撞体标记）  
  - Portal/Prefab/Hitbox 场景  

---

### 6. **提交与版本管理**
- 所有代码必须通过 **Code Review**，至少一人审核。  
- 提交信息必须清晰，格式：  
  ```
  [模块] 功能/修复描述
  例: [PrimitivesWriter] 修复法线导出顺序错误
  ```
- 每次修改必须更新 `schema_reference.md` 或 UI Mockup（如涉及参数/结构变更）。  
- 版本号遵循 **语义化版本**：`MAJOR.MINOR.PATCH`。  

---

### 7. **性能与可维护性**
- Writer 模块必须支持批量写入，避免逐顶点循环写入导致性能瓶颈。  
- 所有导出逻辑必须可配置（通过 UI 属性控制），避免硬编码。  
- 必须考虑未来扩展（如新 Section、新引擎版本），代码需模块化、可插拔。  

---

### 8. **错误处理与日志**
- 所有导出错误必须通过 `self.report({'ERROR'}, "错误信息")` 报告给用户。  
- 日志分级：  
  - INFO：导出成功、路径信息  
  - WARNING：非致命问题（如缺少材质）  
  - ERROR：导出失败、结构不符  
- 如果启用 `enable_verbose_log`，必须输出详细导出步骤。  

---

## ✅ 总结
这份清单定义了 **代码构建需求与标准**，覆盖了：
- 目录与模块  
- 代码风格  
- UI 与属性  
- 导出逻辑  
- 校验与测试  
- 提交与版本管理  
- 性能与可维护性  
- 错误处理与日志  


---

# BigWorld Blender Exporter  
## 补充部分（形成完整方案）

---

## 11. 需求范围与边界

### 11.1 功能范围（必须实现）
- **导出模块**  
  - 网格 (Mesh)  
  - 材质 (Material)  
  - 骨骼 (Skeleton)  
  - 动画 (Animation)  
  - 碰撞 (Collision)  
  - 门户 (Portal)  
  - 预制/实例表 (Prefab/Instances)  
  - Hitbox / XML  
  - 事件轨道 (Cue Track)  

- **UI**  
  - N 面板（对象级参数）  
  - 导出对话框（全局参数、模块开关、高级选项）  

- **验证工具**  
  - 结构校验（structure_checker）  
  - Hex Diff（hex_diff）  
  - 路径校验与修复（path_validator）  

---

### 11.2 非范围功能（明确不做）
- **实时渲染/预览**（插件只负责导出，不负责渲染）  
- **非 BigWorld 格式导出**（如 FBX、GLTF、USD，不在本插件范围）  
- **引擎运行时逻辑**（AI、物理、脚本逻辑不在导出范围）  
- **第三方引擎兼容**（Unity、Unreal 导出不在范围）  

---

### 11.3 边界条件
- 插件必须在 **Blender 4.5+** 环境下运行，低版本不保证兼容。  
- 导出文件必须与 **3ds Max BigWorld 插件产物逐字节对齐**。  
- 所有参数必须有默认值，避免导出时缺失字段。  
- 所有路径必须转换为 **相对路径**，禁止绝对路径写入。  

---


---

## 12. 角色与职责分工

### 12.1 职责分工表

| 模块/任务            | 主要职责说明                                                                 | 负责人（可指派） |
|----------------------|------------------------------------------------------------------------------|------------------|
| **核心 Writer 模块** | 负责实现各导出模块（Mesh、Material、Skeleton、Animation、Collision、Portal、Prefab、Hitbox、Cue Track）的二进制写入逻辑，确保与 schema 对齐 | 技术架构师 / 核心开发 |
| **UI 与交互**        | 负责 N 面板与导出对话框的 UI 实现，确保与 Mockup 一致，属性与 schema 对应     | 前端逻辑开发     |
| **验证工具**         | 负责 `structure_checker.py`、`hex_diff.py`、`path_validator.py` 的实现与维护，确保验证闭环 | 工具链开发       |
| **文档与规范**       | 负责维护 `schema_reference.md`、UI Mockup、开发手册、用户手册，确保文档与代码同步 | 文档负责人       |
| **测试与验证**       | 负责设计测试用例（最小场景、动画场景、碰撞场景、Portal 场景等），执行导出与 Hex Diff 验证 | 测试工程师       |
| **集成与打包**       | 负责插件打包、版本管理、CI/CD 流程，确保每个版本可安装、可运行、可验证       | 构建工程师       |
| **Code Review**      | 负责代码审查，确保风格一致、逻辑正确、无遗漏，必要时回退或修复               | 技术负责人       |

---

### 12.2 协作规范
- **单一负责人**：每个模块必须有明确负责人，避免交叉开发导致冲突。  
- **交叉 Review**：模块负责人开发完成后，必须由另一人进行 Code Review。  
- **文档同步**：任何代码改动必须同步更新 `schema_reference.md` 与 UI Mockup。  
- **测试闭环**：每个模块完成后，必须通过验证工具（结构校验 + Hex Diff + 路径校验）。  
- **版本发布**：每个里程碑版本必须由构建工程师打包，并附带验证报告。  

---


---

## 13. 开发流程与里程碑

### 13.1 开发流程（迭代式）
- **迭代周期**：建议每 2 周为一个迭代周期。  
- **流程步骤**：  
  1. **需求确认**：对照 `schema_reference.md` 和 UI Mockup，确认本迭代要完成的模块。  
  2. **开发实现**：模块负责人完成 Writer/工具/界面开发。  
  3. **单元测试**：使用最小场景验证模块功能。  
  4. **集成测试**：运行导出流程，使用验证工具（结构校验 + Hex Diff）。  
  5. **文档更新**：同步更新 schema_reference.md、开发手册、用户手册。  
  6. **Review & 发布**：代码审查通过后，构建工程师打包插件，形成迭代版本。  

---

### 13.2 里程碑划分

#### **M1：最小可用版本 (MVP)**
- **目标**：实现基础导出功能，能导出最小场景（Cube + 材质 + 骨骼）。  
- **交付物**：  
  - Mesh 导出（PrimitivesWriter）  
  - Material 导出（MaterialWriter）  
  - Skeleton 导出（SkeletonWriter）  
  - 导出对话框 UI（路径、版本、缩放、范围、日志）  
  - 验证工具初版（structure_checker、hex_diff）  
- **验证**：Blender 导出文件与 3ds Max 文件 Hex Diff 一致。  

---

#### **M2：功能扩展版本**
- **目标**：补齐核心模块，支持动画、碰撞、Portal。  
- **交付物**：  
  - AnimationWriter（骨骼动画轨道）  
  - CollisionWriter（Mesh 碰撞体）  
  - PortalWriter（Portal 类型、标签、几何）  
  - 导出对话框增加模块开关（动画、碰撞、Portal）  
- **验证**：导出含动画和碰撞体的场景，Hex Diff 一致。  

---

#### **M3：高级功能版本**
- **目标**：实现高级模块，支持 Prefab、Hitbox、Cue Track。  
- **交付物**：  
  - PrefabAssembler（预制体与实例表）  
  - HitboxBinaryWriter + XML 导出  
  - AnimationWriter 扩展 Cue Track  
  - 导出对话框增加模块开关（Prefab、Hitbox、Cue Track）  
- **验证**：导出含 Prefab、Hitbox 的场景，Hex Diff 一致。  

---

#### **M4：验证闭环与优化版本**
- **目标**：形成完整闭环，保证质量与可维护性。  
- **交付物**：  
  - path_validator（路径校验与修复）  
  - 自动化测试（CI 集成 Hex Diff）  
  - 高级选项（索引类型、矩阵存储方式）  
  - 性能优化（批量写入、缓存）  
  - 文档完善（开发手册、用户手册、变更日志）  
- **验证**：所有测试场景通过，CI 自动验证通过。  

---

### 13.3 里程碑时间线（文字版）

```
M1 (第1-2周) → MVP：Mesh + Material + Skeleton + 基础UI + 验证工具
M2 (第3-4周) → 动画 + 碰撞 + Portal
M3 (第5-6周) → Prefab + Hitbox + Cue Track
M4 (第7-8周) → 验证闭环 + 高级选项 + CI/CD + 文档完善
```

---


---

## 14. 测试策略

### 14.1 测试目标
- 确保 Blender 插件导出的文件与 3ds Max 插件产物 **逐字节一致**。  
- 确保所有模块（Mesh、Material、Skeleton、Animation、Collision、Portal、Prefab、Hitbox、Cue Track）在不同场景下均能正确导出。  
- 确保路径、结构、日志输出符合规范。  

---

### 14.2 测试类型

1. **单元测试（Unit Test）**
   - 针对每个 Writer 模块独立测试。  
   - 输入：最小对象（如一个三角形 Mesh、一个单骨骼 Armature）。  
   - 输出：验证 Section 数据结构正确，字段完整。  

2. **集成测试（Integration Test）**
   - 将多个模块组合导出，验证整体文件结构。  
   - 输入：包含 Mesh + 材质 + 骨骼的场景。  
   - 输出：运行 `structure_checker.py`，确认 Section 顺序与 schema 对齐。  

3. **回归测试（Regression Test）**
   - 每次修改后，重新导出最小场景，运行 Hex Diff。  
   - 确保新代码未破坏已有功能。  

4. **验证工具测试**
   - **structure_checker**：检查 Section 顺序、长度、对齐。  
   - **hex_diff**：逐字节对比 Blender 与 3ds Max 文件。  
   - **path_validator**：检查路径是否存在、是否为相对路径、是否大小写一致。  

---

### 14.3 测试用例库

| 测试场景            | 内容描述 | 预期结果 | 验证工具 |
|---------------------|----------|----------|----------|
| **最小场景**        | Cube + 材质 + 骨骼 | 导出文件与 Max 文件 Hex Diff 一致 | structure_checker + hex_diff |
| **动画场景**        | 骨骼 + 动画轨道 | 动画关键帧正确导出，Cue Track 正确 | hex_diff |
| **碰撞体场景**      | Mesh + 碰撞体标记 | 碰撞体 Section 正确写入 | structure_checker |
| **Portal 场景**     | Mesh + Portal 标签 | Portal Section 正确写入 | structure_checker |
| **Prefab 场景**     | 多个对象组成预制体 | Prefab Section 正确写入 | structure_checker |
| **Hitbox 场景**     | 骨骼 + Hitbox | Hitbox 二进制与 XML 正确导出 | hex_diff |
| **路径校验场景**    | 材质引用绝对路径 | 自动修复为相对路径 | path_validator |

---

### 14.4 测试流程
1. 开发完成 → 编写对应测试用例。  
2. 执行单元测试 → 验证 Writer 模块输出。  
3. 执行集成测试 → 验证整体导出文件结构。  
4. 执行回归测试 → 确认未破坏已有功能。  
5. 执行验证工具 → 确认文件逐字节一致。  
6. 记录测试结果 → 更新测试报告。  

---


## 15. 文档与知识传递

### 15.1 文档清单

| 文档名称                | 内容说明                                                                 | 维护人           | 更新频率 |
|-------------------------|--------------------------------------------------------------------------|------------------|----------|
| **schema_reference.md** | 定义所有 Section 的结构、字段顺序、数据类型，是导出逻辑的唯一真相来源       | 技术架构师       | 每次结构变更必须更新 |
| **UI Mockup (ASCII)**   | 定义 N 面板与导出对话框的最终布局、分组、命名，确保 UI 与代码一致           | UI 负责人        | 每次 UI 改动必须更新 |
| **开发手册**            | 面向开发者，说明插件目录结构、模块职责、如何运行验证工具、如何调试导出流程   | 技术负责人       | 每个迭代结束更新 |
| **用户手册**            | 面向美术/设计师，说明如何在 Blender 中使用插件（N 面板参数、导出对话框操作） | 文档负责人       | 每个版本发布时更新 |
| **测试用例库**          | 列出所有测试场景（最小场景、动画、碰撞、Portal、Prefab、Hitbox），包含预期结果 | 测试工程师       | 每次新增功能时更新 |
| **变更日志 (CHANGELOG)**| 记录每次版本更新的功能、修复、已知问题                                     | 构建工程师       | 每次发布版本时更新 |

---

### 15.2 知识传递机制
- **代码与文档双轨更新**  
  - 任何代码改动必须同步更新 schema_reference.md 和 UI Mockup。  
  - Code Review 时必须检查文档是否同步更新。  

- **团队共享**  
  - 所有文档存放在 `docs/` 目录，并同步到团队知识库（如 Git 仓库 Wiki）。  
  - 每个迭代结束必须召开一次 **知识同步会议**，由模块负责人讲解改动点。  

- **新成员入职**  
  - 必须先阅读开发手册、用户手册、schema_reference.md。  
  - 必须通过一次最小场景导出 + Hex Diff 测试，确保理解流程。  

---

### 15.3 文档示例（schema_reference.md 片段）
```markdown
# Section: Mesh (0x1001)

- Vertex Count (uint32)
- Index Count (uint32)
- Vertex Format:
  - Position (float32 * 3)
  - Normal (float32 * 3)
  - Tangent (float32 * 3)
  - UV (float32 * 2)
  - Color (uint8 * 4)
  - Weights (float32 * 4)
- Index Buffer (uint16/uint32)
```

---



## 16. 质量保障与 CI/CD

### 16.1 代码质量保障
- **代码检查**  
  - 使用 `flake8` 检查语法与风格。  
  - 使用 `black` 自动格式化，保证统一风格。  
  - 使用 `mypy` 做静态类型检查，避免类型错误。  

- **代码审查 (Code Review)**  
  - 每个 PR 必须至少一人审核。  
  - 审查内容包括：逻辑正确性、风格一致性、文档同步性。  
  - 审查 checklist：  
    - 是否遵循 schema_reference.md  
    - 是否更新 UI Mockup（如涉及 UI 改动）  
    - 是否有单元测试/验证用例  
    - 是否有清晰提交信息  

---

### 16.2 自动化测试
- **单元测试**：运行 pytest，覆盖 Writer 模块的最小输入输出。  
- **集成测试**：导出最小场景，运行 `structure_checker.py`。  
- **回归测试**：运行 `hex_diff.py`，对比 Blender 与 3ds Max 文件。  
- **路径校验**：运行 `path_validator.py`，确保路径正确。  

---

### 16.3 CI/CD 流程（文字版流程图）

```
[开发者提交代码]
        ↓
[CI - 代码检查]
  flake8 / black / mypy
        ↓
[CI - 单元测试]
  pytest (Writer 模块)
        ↓
[CI - 集成测试]
  structure_checker.py
        ↓
[CI - 回归测试]
  hex_diff.py (对比 Max 文件)
        ↓
[CI - 路径校验]
  path_validator.py
        ↓
[构建工程师打包插件]
  生成 zip 包 + 版本号
        ↓
[发布版本]
  上传到团队仓库 / 内部分发
        ↓
[附带验证报告]
  - 测试结果
  - Hex Diff 报告
  - 变更日志
```

---

### 16.4 发布规范
- **版本号**：遵循语义化版本 `MAJOR.MINOR.PATCH`。  
- **发布包**：打包为 `blender_bigworld_exporter-x.y.z.zip`。  
- **发布文档**：必须包含：  
  - CHANGELOG.md  
  - 验证报告（Hex Diff、结构校验结果）  
  - 用户手册更新  
- **回滚机制**：如发现导出文件与 Max 不一致，必须立即回滚到上一个稳定版本。  

---


---

## 17. 风险与应对

### 17.1 风险清单表

| 风险类别         | 风险描述                                                                 | 应对措施 |
|------------------|--------------------------------------------------------------------------|----------|
| **兼容性风险**   | Blender API 版本更新可能导致插件接口失效（如 4.5 → 4.6 改动）。            | 锁定最低支持版本（Blender 4.5+），定期回归测试，关注 API 变更日志。 |
| **一致性风险**   | 导出文件与 3ds Max 插件产物不一致，导致引擎无法识别或运行异常。             | 强制使用 `hex_diff.py` 验证，任何差异必须修复后才能合并代码。 |
| **协作风险**     | 多人同时修改 schema_reference.md 或 Writer 模块，可能导致冲突或遗漏。       | 所有改动必须通过 Code Review，文档与代码必须同步更新。 |
| **性能风险**     | 大场景导出时，逐顶点写入可能导致性能瓶颈，影响生产效率。                     | 优化 Writer 模块，采用批量写入与缓存机制，必要时引入 C 扩展。 |
| **路径风险**     | 美术资源路径不规范（绝对路径、大小写不一致），导致引擎加载失败。             | 使用 `path_validator.py` 校验，启用自动修复路径功能。 |
| **测试覆盖不足** | 新功能上线但缺少对应测试用例，可能导致回归 bug。                           | 建立测试用例库，新增功能必须附带测试场景。 |
| **知识流失风险** | 团队成员更替时，缺乏文档或交接，导致后续维护困难。                         | 强制更新 schema_reference.md、开发手册、用户手册，定期知识分享。 |
| **扩展性风险**   | 将来引擎版本升级或新增 Section 时，插件难以扩展。                           | 模块化设计，Writer 独立，schema_reference.md 可扩展。 |

---

### 17.2 风险管理机制
1. **预防为主**：所有开发必须遵循 schema_reference.md，避免随意实现。  
2. **验证闭环**：每次导出必须经过结构校验 + Hex Diff，确保一致性。  
3. **文档同步**：任何改动必须更新文档，避免知识流失。  
4. **定期回顾**：每个迭代结束，团队必须回顾风险清单，确认是否有新增风险。  

---


---

## 18. 优先级与路线图

### 18.1 功能优先级矩阵

| 优先级 | 功能模块/任务                  | 说明 |
|--------|--------------------------------|------|
| **高** | Mesh 导出 (PrimitivesWriter)   | 基础功能，所有场景必需 |
|        | Material 导出 (MaterialWriter) | 基础功能，保证材质正确性 |
|        | Skeleton 导出 (SkeletonWriter) | 基础功能，保证骨骼层级与绑定 |
|        | 验证工具 (structure_checker, hex_diff) | 保证一致性闭环 |
|        | 导出对话框基础参数 (路径、版本、缩放、范围、日志) | 必须先有的全局控制 |
| **中** | Animation 导出 (AnimationWriter) | 骨骼动画轨道，Cue Track 后续扩展 |
|        | Collision 导出 (CollisionWriter) | 碰撞体导出，游戏运行时必需 |
|        | Portal 导出 (PortalWriter)     | 场景切分与引擎运行时必需 |
| **低** | Prefab 导出 (PrefabAssembler)  | 高级功能，后期扩展 |
|        | Hitbox 导出 (HitboxBinaryWriter + XML) | 高级功能，战斗系统相关 |
|        | Cue Track 导出 (AnimationWriter 扩展) | 高级功能，动画事件系统 |
|        | 高级选项 (路径修复、索引类型、矩阵存储方式) | 优化与增强功能 |

---

### 18.2 开发路线图

```
阶段 1 (M1 - 高优先级)
  - Mesh、Material、Skeleton 导出
  - 基础导出对话框
  - 验证工具 (structure_checker, hex_diff)

阶段 2 (M2 - 中优先级)
  - Animation 导出
  - Collision 导出
  - Portal 导出
  - 导出对话框增加模块开关

阶段 3 (M3 - 低优先级)
  - Prefab 导出
  - Hitbox 导出
  - Cue Track 导出
  - 高级选项 (路径修复、索引类型、矩阵存储方式)

阶段 4 (M4 - 验证闭环与优化)
  - CI/CD 集成
  - 自动化测试
  - 性能优化
  - 文档与用户手册完善
```

---

### 18.3 执行策略
- **先核心，后扩展**：先保证 Mesh/Material/Skeleton/验证工具，确保最小可用版本。  
- **逐步补齐**：再实现 Animation/Collision/Portal，覆盖核心生产需求。  
- **最后增强**：Prefab/Hitbox/Cue Track/高级选项，作为扩展功能上线。  
- **持续优化**：CI/CD、性能优化、文档完善，保证长期可维护性。  

---

