# 第三章：UI设计规范（核心功能版）

> **设计原则**：只保留核心导出功能，移除所有占位保留的功能，专注于静态/蒙皮/角色动画三种导出

---

## 3.1 插件偏好设置（全局设置）

**位置**: Edit → Preferences → Add-ons → BigWorld Exporter

**功能说明**:

```
┌────────────────────────────────────────────────────────────┐
│ BigWorld 插件全局设置                                       │
├────────────────────────────────────────────────────────────┤
│                                                             │
│ 📁 路径设置                                                 │
│ ├─ 导出根目录： [C:/BigWorld/res        ] [📁]            │
│ └─ 纹理根目录： [C:/BigWorld/res/maps   ] [📁]            │
│                                                             │
│ 🌐 坐标系与单位                                             │
│ ├─ 坐标系转换： [Z-up → Y-up ▼]                           │
│ └─ 单位缩放：   [1.0     ]  (1 BU = 1.0 米)              │
│                                                             │
│ ⚙️ 导出选项                                                 │
│ ├─ [✔] 导出前自动检测                                      │
│ └─ [✔] 写入审计日志                                        │
│                                                             │
│ [保存设置]                                                  │
└────────────────────────────────────────────────────────────┘
```

**实现的属性**（精简到6个核心属性）:
- `root_path` (StringProperty, DIR_PATH) - 导出根目录
- `texture_path` (StringProperty, DIR_PATH) - 纹理根目录
- `axis_mode` (EnumProperty) - 坐标系转换
  - `Z_UP_TO_Y_UP` - Z-up → Y-up（推荐）
  - `NONE` - 不转换
- `unit_scale` (FloatProperty) - 单位缩放（默认1.0）
- `auto_validate` (BoolProperty) - 导出前自动检测
- `write_audit` (BoolProperty) - 写入审计日志

**移除的属性**:
- ❌ `naming_template` - 不需要，使用默认规则
- ❌ `lod_rule_template` - LOD功能待实现
- ❌ `schema_file` - 不需要
- ❌ `directory_strategy` - 使用固定策略

**文件**: `ui/preferences_panel.py`

---

## 3.2 对象属性面板（N面板）

**位置**: 3D Viewport → N Panel → BigWorld

**功能说明**:

```
┌────────────────────────────────────────────────────────────┐
│ BigWorld 对象属性                                           │
├────────────────────────────────────────────────────────────┤
│                                                             │
│ 📦 基础设置                                                 │
│ ├─ 导出类型： [静态模型 ▼]                                 │
│ │   ├─ 静态模型   (无骨骼、无动画)                         │
│ │   ├─ 蒙皮模型   (有骨骼、无动画)                         │
│ │   └─ 角色动画   (有骨骼、有动画)                         │
│ ├─ 资源ID：   [cube_01        ]                           │
│ └─ 父模型：   [                ] (可选，用于角色组件)       │
│     说明：继承父模型的骨骼和动画                            │
│                                                             │
│ ────────────────────────────────────────────────────────── │
│                                                             │
│ 🎯 硬点管理（挂载点）                                       │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ 硬点列表                                     [+] [-] │   │
│ ├──────────────────────────────────────────────────────┤   │
│ │ ▸ HP_RightHand     🗡️ 武器      → RightHand       │   │
│ │ ▸ HP_LeftHand      🛡️ 副手      → LeftHand        │   │
│ │ ▸ HP_Head          👑 头盔      → Head             │   │
│ │ ▸ HP_Back          🎒 背包      → Spine1           │   │
│ │ ▸ HP_Effect        ✨ 特效      → Root             │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                             │
│ 选中的硬点设置：                                            │
│ ├─ 硬点名称：  [HP_RightHand    ]                         │
│ ├─ 硬点类型：  [武器挂载 ▼]                               │
│ │   └─ 选项：武器挂载 / 装备挂载 / 特效点 / 交互点         │
│ ├─ 绑定骨骼：  [RightHand ▼] (从骨架选择)                 │
│ └─ 或使用Empty： [                ] (从场景Empty选择)      │
│                                                             │
│ ────────────────────────────────────────────────────────── │
│                                                             │
│ 🎬 Action 管理（仅角色动画类型显示）                        │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ Action 列表                              [+] [-]     │   │
│ ├──────────────────────────────────────────────────────┤   │
│ │ ▸ WalkForward    walk      ✔混合  轨道:0          │   │
│ │ ▸ RunForward     run       ✔混合  轨道:0          │   │
│ │ ▸ Attack         attack    ✘混合  轨道:1          │   │
│ │ ▸ Idle           idle      ✔混合  轨道:0          │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                             │
│ 选中的Action设置：                                          │
│ ├─ Action名称：  [WalkForward      ]                       │
│ ├─ 关联动画：    [walk      ▼] (从Blender Actions选择)    │
│ ├─ [✔] 混合播放                                            │
│ └─ 动画轨道：    [0] (0-10)                               │
│                                                             │
│ ────────────────────────────────────────────────────────── │
│                                                             │
│ 🎨 材质信息（仅网格对象显示）                               │
│ ├─ 材质槽数量： 2                                          │
│ └─ 纹理路径将从Blender材质节点自动提取                     │
│                                                             │
│ ────────────────────────────────────────────────────────── │
│                                                             │
│ [🔍 运行导出前检测]                                         │
└────────────────────────────────────────────────────────────┘
```

**实现的属性**（核心功能）:

```python
# 基础设置
export_type: EnumProperty(
    items=[
        ('STATIC', '静态模型', '无骨骼、无动画'),
        ('SKINNED', '蒙皮模型', '有骨骼、无动画'),
        ('CHARACTER', '角色动画', '有骨骼、有动画')
    ]
)
resource_id: StringProperty(name="资源ID")
parent_model: StringProperty(name="父模型", description="继承父模型的骨骼和动画")

# 硬点系统
hardpoints: CollectionProperty(type=BigWorldHardpoint)
hardpoints_index: IntProperty()

class BigWorldHardpoint(PropertyGroup):
    name: StringProperty(name="硬点名称")
    hardpoint_type: EnumProperty(
        items=[
            ('WEAPON', '武器挂载', '武器挂载点'),
            ('EQUIPMENT', '装备挂载', '装备挂载点'),
            ('EFFECT', '特效点', '特效播放位置'),
            ('INTERACT', '交互点', '交互触发点')
        ]
    )
    bone_name: StringProperty(name="绑定骨骼")
    use_empty: BoolProperty(name="使用Empty对象")
    target_empty: PointerProperty(type=bpy.types.Object)

# Action系统（仅角色动画）
actions: CollectionProperty(type=BigWorldAction)
actions_index: IntProperty()

class BigWorldAction(PropertyGroup):
    name: StringProperty(name="Action名称")
    animation_name: StringProperty(name="关联动画")
    blended: BoolProperty(name="混合播放", default=True)
    track: IntProperty(name="动画轨道", default=0, min=0, max=10)
```

**移除的属性**:
- ❌ `object_type` - 与export_type重复
- ❌ `group` - 不需要
- ❌ `lod_enabled`, `lod_auto_generate`, `lod_rule` - LOD功能待实现
- ❌ `material_template`, `texture_compression` - 自动处理
- ❌ `animation_tracks` - 改用actions
- ❌ `anim_is_coordinated`, `anim_is_impacting` - 辅助功能
- ❌ `collision_source`, `collision_layer` - 功能待实现
- ❌ `portal_space_id`, `portal_adjacent_space` - 功能待实现

**文件**: `ui/object_panel.py`

---

## 3.3 导出执行面板（File → Export → BigWorld）

**位置**: File → Export → BigWorld

**功能说明**:

```
┌────────────────────────────────────────────────────────────┐
│ 导出 BigWorld 文件                                          │
├────────────────────────────────────────────────────────────┤
│                                                             │
│ 📁 输出设置                                                 │
│ └─ 保存到： [C:/BigWorld/res/models/hero.model] [浏览]    │
│                                                             │
│ 🎯 导出配置                                                 │
│ ├─ 导出范围： [选中对象 ▼]                                 │
│ │   └─ 选项：选中对象 / 所有对象 / 场景所有                │
│ └─ 导出类型： [角色动画 ▼]                                 │
│     └─ 选项：静态模型 / 蒙皮模型 / 角色动画                │
│                                                             │
│ ────────────────────────────────────────────────────────── │
│                                                             │
│ 📄 生成文件                                                 │
│ ├─ [✔] .primitives   (几何数据)                           │
│ ├─ [✔] .visual       (渲染配置)                           │
│ ├─ [✔] .model        (模型组合)                           │
│ ├─ [✔] .animation    (动画数据) ← 角色动画时可用          │
│ ├─ [✔] manifest.json (导出清单)                           │
│ └─ [✔] audit.log     (审计日志)                           │
│                                                             │
│ ────────────────────────────────────────────────────────── │
│                                                             │
│ 💡 导出预览                                                 │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ 导出对象： 1 个 (hero)                                │   │
│ │ 导出类型： 角色动画                                   │   │
│ │ 顶点格式： xyznuviiiww                                │   │
│ │ 骨骼数量： 45 根                                      │   │
│ │ 动画数量： 12 个                                      │   │
│ │ Action数量：8 个                                      │   │
│ │ 硬点数量： 5 个                                       │   │
│ │ ──────────────────────────────────────────────────── │   │
│ │ 生成文件：                                            │   │
│ │ ✅ hero.primitives                                   │   │
│ │ ✅ hero.visual                                       │   │
│ │ ✅ hero.model                                        │   │
│ │ ✅ animations/walk.animation                         │   │
│ │ ✅ animations/run.animation                          │   │
│ │ ✅ ... (共12个动画)                                  │   │
│ │ ✅ manifest.json                                     │   │
│ │ ✅ audit.log                                         │   │
│ │ ──────────────────────────────────────────────────── │   │
│ │ 输出目录： C:/BigWorld/res/characters/hero/          │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                             │
│ [✅ 导出 BigWorld] [取消]                                   │
└────────────────────────────────────────────────────────────┘
```

**实现的属性**:
- `filepath` (StringProperty, FILE_PATH) - 文件保存路径
- `export_mode` (EnumProperty) - 导出范围
  - `SELECTED` - 选中对象
  - `ALL` - 所有对象
  - `SCENE` - 场景所有
- `export_type` (EnumProperty) - 导出类型
  - `STATIC` - 静态模型
  - `SKINNED` - 蒙皮模型
  - `CHARACTER` - 角色动画
- `export_primitives` (BoolProperty) - 生成.primitives
- `export_visual` (BoolProperty) - 生成.visual
- `export_model` (BoolProperty) - 生成.model
- `export_animation` (BoolProperty) - 生成.animation
- `export_manifest` (BoolProperty) - 生成manifest.json
- `export_audit` (BoolProperty) - 生成audit.log

**移除的属性**:
- ❌ `geometry_format` - 固定使用primitives
- ❌ `export_collision` - 碰撞功能待实现
- ❌ `directory_strategy` - 使用固定策略
- ❌ `export_preset` - 不需要

**文件**: `ui/export_panel.py`, `__init__.py` (BigWorldExportOperator)

---

## 3.4 UI状态变化逻辑

### 3.4.1 根据导出类型动态显示UI

```python
当用户在对象属性面板选择导出类型时：

if export_type == 'STATIC':  # 静态模型
    ✅ 显示：基础设置（资源ID）
    ❌ 隐藏：父模型字段（灰掉）
    ❌ 隐藏：硬点管理（静态无骨骼）
    ❌ 隐藏：Action管理
    
if export_type == 'SKINNED':  # 蒙皮模型
    ✅ 显示：基础设置（资源ID）
    ✅ 显示：父模型字段（推荐填写）
    ✅ 显示：硬点管理（有骨骼可绑定）
    ❌ 隐藏：Action管理（无动画）
    
if export_type == 'CHARACTER':  # 角色动画
    ✅ 显示：基础设置（资源ID）
    ✅ 显示：父模型字段（可选）
    ✅ 显示：硬点管理（有骨骼可绑定）
    ✅ 显示：Action管理（动画核心）
```

### 3.4.2 导出面板的文件选项联动

```python
当用户在导出面板选择导出类型时：

if export_type == 'STATIC':
    export_animation.enabled = False  # 禁用.animation选项
    预览显示：生成3个文件
    
if export_type == 'SKINNED':
    export_animation.enabled = False  # 禁用.animation选项
    预览显示：生成3个文件
    
if export_type == 'CHARACTER':
    export_animation.enabled = True   # 启用.animation选项
    预览显示：生成N+3个文件（N=动画数量）
```

---

## 3.5 硬点系统详细设计

### 3.5.1 硬点数据结构

```python
class BigWorldHardpoint(PropertyGroup):
    """硬点属性"""
    
    name: StringProperty(
        name="硬点名称",
        description="硬点唯一标识（如：HP_RightHand）",
        default="HP_Mount"
    )
    
    hardpoint_type: EnumProperty(
        name="硬点类型",
        items=[
            ('WEAPON', '武器挂载', '武器挂载点（剑、枪等）'),
            ('EQUIPMENT', '装备挂载', '装备挂载点（盾牌、背包等）'),
            ('EFFECT', '特效点', '特效播放位置（光环、粒子等）'),
            ('INTERACT', '交互点', '交互触发点（按钮、开关等）')
        ],
        default='WEAPON'
    )
    
    bone_name: StringProperty(
        name="绑定骨骼",
        description="硬点绑定到的骨骼名称",
        default=""
    )
    
    use_empty: BoolProperty(
        name="使用Empty对象",
        description="从场景中的Empty对象获取位置",
        default=False
    )
    
    target_empty: PointerProperty(
        name="目标Empty",
        description="用作硬点位置的Empty对象",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'EMPTY'
    )
```

### 3.5.2 硬点在文件中的体现

硬点数据会写入到 `.model` 文件的 `<hardPoint>` 节点：

```xml
<root>
  <nodefullVisual>hero</nodefullVisual>
  
  <!-- 硬点定义 -->
  <hardPoint>
    <name>HP_RightHand</name>
    <identifier>Scene Root/biped/biped..Spine/biped..R Clavicle/biped..R UpperArm/biped..R Forearm/biped..R Hand</identifier>
    <transform>
      <row0>1.0 0.0 0.0</row0>
      <row1>0.0 1.0 0.0</row1>
      <row2>0.0 0.0 1.0</row2>
      <row3>0.0 0.0 0.0</row3>
    </transform>
  </hardPoint>
</root>
```

**字段说明**:
- `<name>` - 硬点名称（如：HP_RightHand）
- `<identifier>` - 骨骼完整路径（从Scene Root到目标骨骼）
- `<transform>` - 相对于绑定骨骼的变换矩阵（4x3）

### 3.5.3 硬点的典型使用场景

**场景1：武器挂载**
```
硬点名称：HP_RightHand
硬点类型：武器挂载
绑定骨骼：biped..R Hand

用途：游戏中动态挂载武器模型
     武器模型会跟随手部骨骼运动
```

**场景2：装备挂载**
```
硬点名称：HP_Head
硬点类型：装备挂载
绑定骨骼：biped..Head

用途：游戏中动态挂载头盔/帽子
     装备会跟随头部骨骼运动
```

**场景3：特效点**
```
硬点名称：HP_Weapon_Trail
硬点类型：特效点
绑定骨骼：biped..R Hand

用途：游戏中播放武器拖尾特效
     特效起始位置跟随手部运动
```

---

## 3.6 Action系统详细设计

### 3.6.1 Action数据结构

```python
class BigWorldAction(PropertyGroup):
    """Action属性"""
    
    name: StringProperty(
        name="Action名称",
        description="游戏中的动作标识（如：WalkForward）",
        default="Action"
    )
    
    animation_name: StringProperty(
        name="关联动画",
        description="Blender中的Action名称",
        default=""
    )
    
    blended: BoolProperty(
        name="混合播放",
        description="是否支持动画混合",
        default=True
    )
    
    track: IntProperty(
        name="动画轨道",
        description="动画播放轨道（0-10）",
        default=0,
        min=0,
        max=10
    )
```

### 3.6.2 Action在文件中的体现

Action数据会写入到 `.model` 文件的 `<action>` 节点：

```xml
<root>
  <nodefullVisual>hero</nodefullVisual>
  
  <!-- 动画引用 -->
  <animation>
    <name>walk</name>
    <nodes>characters/hero/animations/walk</nodes>
  </animation>
  <animation>
    <name>run</name>
    <nodes>characters/hero/animations/run</nodes>
  </animation>
  
  <!-- Action定义 -->
  <action>
    <name>WalkForward</name>
    <animation>walk</animation>
    <blended>true</blended>
    <track>0</track>
  </action>
  <action>
    <name>RunForward</name>
    <animation>run</animation>
    <blended>true</blended>
    <track>0</track>
  </action>
  <action>
    <name>Attack</name>
    <animation>attack</animation>
    <blended>false</blended>
    <track>1</track>
  </action>
</root>
```

**字段说明**:
- `<name>` - Action名称（游戏逻辑使用）
- `<animation>` - 引用上面定义的animation名称
- `<blended>` - 是否支持混合（true/false）
- `<track>` - 动画轨道索引（0-10）

---

## 3.7 三种导出类型的UI状态对比

| UI元素 | 静态模型 | 蒙皮模型 | 角色动画 |
|--------|---------|---------|---------|
| **对象属性面板** | | | |
| 导出类型 | ✅ 显示 | ✅ 显示 | ✅ 显示 |
| 资源ID | ✅ 显示 | ✅ 显示 | ✅ 显示 |
| 父模型 | ❌ 灰掉 | ✅ 显示（推荐） | ✅ 显示（可选） |
| 硬点管理 | ❌ 隐藏 | ✅ 显示 | ✅ 显示 |
| Action管理 | ❌ 隐藏 | ❌ 隐藏 | ✅ 显示 |
| 材质信息 | ✅ 显示 | ✅ 显示 | ✅ 显示 |
| **导出面板** | | | |
| .primitives | ✅ 可选 | ✅ 可选 | ✅ 可选 |
| .visual | ✅ 可选 | ✅ 可选 | ✅ 可选 |
| .model | ✅ 可选 | ✅ 可选 | ✅ 可选 |
| .animation | ❌ 禁用 | ❌ 禁用 | ✅ 可选 |
| 预览信息 | 简单 | 中等 | 详细 |

---

## 3.8 UI属性统计（重构前后对比）

| UI面板 | 重构前 | 重构后 | 变化 | 说明 |
|--------|--------|--------|------|------|
| **偏好设置** | 10个属性 | 6个属性 | ↓ 40% | 移除占位功能 |
| **对象面板** | 20+个属性 | 8个属性 + 2个列表 | ↓ 50% | 精简核心功能 |
| **导出面板** | 12个属性 | 10个属性 | ↓ 17% | 移除占位选项 |
| **总计** | **42+个** | **24个 + 2列表** | **↓ 43%** | **大幅精简** |

---

## 3.9 UI与数据文件的映射关系

### 3.9.1 UI控件 → 文件数据映射表

| UI控件 | 属性名 | 关联数据 | 写入文件 | 数据格式 |
|--------|--------|---------|---------|---------|
| **偏好设置** | | | | |
| 导出根目录 | `root_path` | 输出目录 | 全部 | 路径前缀 |
| 纹理根目录 | `texture_path` | 纹理路径 | .visual | `<TextureFactor>` |
| 坐标系转换 | `axis_mode` | 坐标转换 | 全部 | 影响所有坐标 |
| 单位缩放 | `unit_scale` | 单位换算 | .primitives | 顶点位置缩放 |
| **对象属性** | | | | |
| 导出类型 | `export_type` | 导出模式 | 全部 | 决定文件内容 |
| 资源ID | `resource_id` | 文件名 | 全部 | 文件名前缀 |
| 父模型 | `parent_model` | 模型继承 | .model | `<parent>` |
| **硬点列表** | `hardpoints` | 挂载点 | .model | `<hardPoint>` |
| - 硬点名称 | `name` | 硬点ID | .model | `<hardPoint><name>` |
| - 硬点类型 | `hardpoint_type` | 类型标识 | .model | 注释/元数据 |
| - 绑定骨骼 | `bone_name` | 骨骼路径 | .model | `<hardPoint><identifier>` |
| - Empty对象 | `target_empty` | 变换矩阵 | .model | `<hardPoint><transform>` |
| **Action列表** | `actions` | 动作定义 | .model | `<action>` |
| - Action名称 | `name` | 动作ID | .model | `<action><name>` |
| - 关联动画 | `animation_name` | 动画引用 | .model | `<action><animation>` |
| - 混合播放 | `blended` | 混合标志 | .model | `<action><blended>` |
| - 动画轨道 | `track` | 轨道索引 | .model | `<action><track>` |
| **导出面板** | | | | |
| 导出范围 | `export_mode` | 对象筛选 | - | 控制逻辑 |
| .primitives | `export_primitives` | 生成控制 | .primitives | 是否生成 |
| .visual | `export_visual` | 生成控制 | .visual | 是否生成 |
| .model | `export_model` | 生成控制 | .model | 是否生成 |
| .animation | `export_animation` | 生成控制 | .animation | 是否生成 |

---

## 3.10 控件类型对照表（3ds Max → Blender）

用于参考旧版 3ds Max 插件的 UI 设计：

| 功能类别 | 3ds Max 控件 | Blender 控件 | 状态 | 用途 |
|---------|-------------|-------------|------|------|
| 布尔开关 | CheckBox | BoolProperty | ✅ | 导出选项 |
| 下拉选择 | ComboBox | EnumProperty | ✅ | 类型选择 |
| 文本输入 | EditText | StringProperty | ✅ | 路径、ID |
| 数值输入 | Spinner | IntProperty/FloatProperty | ✅ | 轨道索引 |
| 按钮 | Button | Operator | ✅ | 添加/删除 |
| 文件选择 | FilePicker | StringProperty(FILE_PATH) | ✅ | 导出路径 |
| 文件夹选择 | FolderPicker | StringProperty(DIR_PATH) | ✅ | 根目录 |
| 列表 | UIList | UIList | ✅ | 硬点/Action列表 |
| 对象选择 | ObjectPicker | PointerProperty | ✅ | Empty引用 |

---


