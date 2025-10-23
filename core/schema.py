# File: core/schema.py
# Purpose: BigWorld 导出数据结构定义（dataclass）
# Notes:
# - 所有导出文件的核心数据结构
# - Primitives / Visual / Model / Animation / Skeleton / Collision / Portal
# - 按方案文档 schema_reference.md 对齐
# - ✔ 必须实现字段 / ◆ 占位保留字段

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum


# ==================== 枚举类型 ====================

class ObjectType(Enum):
    """对象类型"""
    STATIC = "static"           # 静态模型
    SKINNED = "skinned"         # 蒙皮模型
    CHARACTER = "character"     # 角色
    COLLISION = "collision"     # 碰撞体
    PORTAL = "portal"           # 门户
    GROUP = "group"             # 组


class DirectoryStrategy(Enum):
    """目录策略"""
    BY_TYPE = "by_type"         # 按类型分目录
    BY_PACKAGE = "by_package"   # 按包分目录
    BY_LOD = "by_lod"           # 按LOD分目录


class CoordinateSystem(Enum):
    """坐标系"""
    Z_UP = "z_up"               # Blender 默认 Z-up
    Y_UP = "y_up"               # BigWorld Y-up


class CompressionType(Enum):
    """纹理压缩格式"""
    NONE = "none"
    DXT5 = "dxt5"
    BC7 = "bc7"


# ==================== Primitives 数据结构 ====================

@dataclass
class PrimitiveGroup:
    """子网格分组（对应一个材质槽）"""
    name: str                   # 组名
    start_index: int            # 起始索引
    num_primitives: int         # 三角形数量（索引数 / 3）
    start_vertex: int           # 顶点起始
    num_vertices: int           # 顶点数量
    material_slot: int          # 材质槽索引


@dataclass
class Primitives:
    """
    .primitives 文件数据结构（BinSection）
    """
    version: int = 1
    
    # 顶点数据 ✔ 必须
    vertices: List[Tuple[float, float, float]] = field(default_factory=list)  # 位置
    normals: List[Tuple[float, float, float]] = field(default_factory=list)   # 法线
    uvs: List[Tuple[float, float]] = field(default_factory=list)              # UV坐标
    
    # 可选顶点数据 ◆ 占位
    tangents: List[Tuple[float, float, float]] = field(default_factory=list)  # 切线
    binormals: List[Tuple[float, float, float]] = field(default_factory=list) # 副切线
    colors: List[Tuple[float, float, float, float]] = field(default_factory=list) # 顶点颜色
    
    # 蒙皮数据 ✔ 角色模型需要
    bone_indices: List[Tuple[int, int, int, int]] = field(default_factory=list)  # 骨骼索引（最多4个）
    bone_weights: List[Tuple[float, float, float, float]] = field(default_factory=list)  # 骨骼权重
    
    # 索引数据 ✔ 必须
    indices: List[int] = field(default_factory=list)                          # 索引数组
    
    # 分组 ✔ 必须
    groups: List[PrimitiveGroup] = field(default_factory=list)
    
    # BSP 数据 ◆ 占位（静态场景用）
    bsp_data: Optional[bytes] = None
    
    # 顶点格式字符串（动态生成，如 "xyznuvtb"）
    vertex_format: str = ""


# ==================== Visual 数据结构 ====================

@dataclass
class HardPoint:
    """硬点（挂载点/交互点/特效点）- 符合BigWorld官方规范"""
    name: str                                   # 硬点名称（如：HP_RightHand）
    identifier: str = ""                        # 骨骼完整路径（如：Scene Root/biped/...）
    transform: List[List[float]] = field(default_factory=lambda: [  # 4x3 变换矩阵
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, 0.0, 0.0]
    ])
    hardpoint_type: str = "WEAPON"             # 类型: WEAPON / EQUIPMENT / EFFECT / INTERACT


@dataclass
class MaterialSlot:
    """材质槽"""
    name: str                           # 材质名
    shader: str = ""                    # shader/fx 路径 ✔
    
    # 纹理路径 ✔ 必须
    base_color: str = ""                # BaseColor/Diffuse
    normal: str = ""                    # Normal
    orm: str = ""                       # ORM (Occlusion+Roughness+Metallic)
    
    # 可选纹理 ◆ 占位
    specular: str = ""
    emissive: str = ""
    alpha: str = ""
    
    # 材质参数 ✔
    compression: CompressionType = CompressionType.NONE
    uv_channel: int = 0
    
    # 扩展参数 ◆ 占位
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RenderSet:
    """渲染集（geometry + material 绑定）"""
    geometry: str                       # 引用 .primitives 路径 ✔
    primitive_group_indices: List[int]  # 对应的 group 索引 ✔
    material: MaterialSlot              # 材质槽 ✔


@dataclass
class Visual:
    """
    .visual 文件数据结构（PackedSection）
    """
    version: int = 1
    
    # 渲染集 ✔ 必须
    render_sets: List[RenderSet] = field(default_factory=list)
    
    # 材质槽列表 ✔
    materials: List[MaterialSlot] = field(default_factory=list)
    
    # 包围体 ✔ 必须
    bounding_box: Tuple[
        Tuple[float, float, float],  # min
        Tuple[float, float, float]   # max
    ] = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    
    bounding_sphere: Tuple[
        Tuple[float, float, float],  # center
        float                         # radius
    ] = ((0.0, 0.0, 0.0), 0.0)
    
    # 骨骼节点 ◆ 占位（蒙皮模型用）
    nodes: List[str] = field(default_factory=list)  # 简化的字符串列表（兼容）
    skeleton: Optional['Skeleton'] = None  # 完整的骨骼结构（用于写入层级）
    
    # 渲染标志 ◆ 占位
    flags: int = 0
    
    # LOD 绑定 ◆ 占位
    lod_binding: Dict[str, int] = field(default_factory=dict)
    
    # 目录策略 ◆ 占位
    directory_strategy: DirectoryStrategy = DirectoryStrategy.BY_TYPE


# ==================== Animation 数据结构 ====================

@dataclass
class AnimationKeyFrame:
    """动画关键帧"""
    time: float                         # 时间戳（秒）
    value: Any                          # 值（Vector3/Quaternion）


@dataclass
class AnimationKeys:
    """动画通道关键帧集合"""
    position_keys: List[Tuple[float, Tuple[float, float, float]]] = field(default_factory=list)
    rotation_keys: List[Tuple[float, Tuple[float, float, float, float]]] = field(default_factory=list)  # Quaternion
    scale_keys: List[Tuple[float, Tuple[float, float, float]]] = field(default_factory=list)


@dataclass
class AnimationChannel:
    """动画通道（每根骨骼）"""
    bone_name: str                      # 骨骼名 ✔
    bone_index: int = -1                # 骨骼索引
    keys: AnimationKeys = field(default_factory=AnimationKeys)


@dataclass
class AnimationTrackEvent:
    """动画事件标签"""
    name: str                           # 事件名（如 IsCoordinated）
    frame: float                        # 触发帧/时间


@dataclass
class Animation:
    """
    .animation 文件数据结构（PackedSection）
    """
    version: int = 1
    
    # 基础信息 ✔ 必须
    name: str = ""                      # 动画名
    skeleton_ref: str = ""              # 骨骼引用
    duration: float = 0.0               # 时长（秒）
    
    # 采样参数 ◆ 占位
    frame_rate: int = 30
    
    # 通道列表 ✔ 必须
    channels: List[AnimationChannel] = field(default_factory=list)
    
    # 压缩 ◆ 占位
    compression: bool = False
    
    # 事件标签 ◆ 占位
    events: List[AnimationTrackEvent] = field(default_factory=list)


# ==================== Skeleton 数据结构 ====================

@dataclass
class SkeletonBone:
    """骨骼节点"""
    name: str                           # 骨骼名
    parent: Optional[str] = None        # 父骨骼名
    bind_matrix: List[List[float]] = field(default_factory=list)  # 4x4 绑定矩阵


@dataclass
class Skeleton:
    """骨骼结构"""
    bone_names: List[str] = field(default_factory=list)
    bones: List[SkeletonBone] = field(default_factory=list)
    root: str = ""


# ==================== Model 数据结构 ====================

@dataclass
class ModelAnimation:
    """Model 中的动画引用"""
    name: str                           # 动画名
    resource: str                       # .animation 路径


@dataclass
class ModelAction:
    """Model中的Action定义（符合BigWorld官方规范）"""
    name: str                           # Action名称（如：WalkForward）
    animation_ref: str                  # 引用的animation名称（如：walk）
    blended: bool = True               # 是否混合播放
    track: int = 0                     # 动画轨道索引（0-10）
    # 未来扩展字段：
    # filler: Optional[int] = None
    # match_info: Optional[Dict] = None


@dataclass
class Model:
    """
    .model 文件数据结构（PackedSection）
    """
    version: int = 1
    
    # 基础信息 ✔ 必须
    resource_id: str = ""               # 资源ID
    object_type: ObjectType = ObjectType.STATIC
    
    # 引用文件 ✔ 必须
    visual: str = ""                    # .visual 路径
    has_skeleton: bool = False          # 是否有骨骼（决定使用 nodefullVisual 还是 nodelessVisual）
    
    # 可选引用 ◆ 占位
    parent: str = ""                    # 父模型
    skeleton: Optional[Skeleton] = None
    
    # 包围体 ✔ 必须
    extent: float = 20.0  # LOD 距离（米）
    bounding_box: Tuple[
        Tuple[float, float, float],
        Tuple[float, float, float]
    ] = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    
    # 动画 ◆ 占位
    animations: List[ModelAnimation] = field(default_factory=list)
    actions: List[ModelAction] = field(default_factory=list)
    
    # 硬点 ✔
    hardpoints: List[HardPoint] = field(default_factory=list)
    
    # 染色 ◆ 占位
    dye_tint: Dict[str, Any] = field(default_factory=dict)
    
    # LOD ◆ 占位
    lod_impostor: Dict[str, Any] = field(default_factory=dict)


# ==================== Collision 数据结构 ◆ 占位 ====================

@dataclass
class Collision:
    """碰撞体数据结构（占位保留）"""
    version: int = 1
    collision_type: str = "mesh"        # mesh / hull / simplified
    vertices: List[Tuple[float, float, float]] = field(default_factory=list)
    indices: List[int] = field(default_factory=list)
    layer: str = "default"
    bounding_box: Tuple[
        Tuple[float, float, float],
        Tuple[float, float, float]
    ] = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


# ==================== Portal 数据结构 ◆ 占位 ====================

@dataclass
class Portal:
    """门户数据结构（占位保留）"""
    version: int = 1
    space_id: str = ""
    adjacent_space: str = ""
    plane: Tuple[float, float, float, float] = (0.0, 1.0, 0.0, 0.0)  # 法线 + 距离
    vertices: List[Tuple[float, float, float]] = field(default_factory=list)
    normal_check: bool = True
    flags: List[str] = field(default_factory=list)


# ==================== 导出设置数据结构 ====================

@dataclass
class ExportSettings:
    """全局导出设置（来自 Preferences）"""
    root_path: str = ""                 # 导出根目录 ✔
    texture_path: str = ""              # 纹理根目录 ✔
    axis_mode: CoordinateSystem = CoordinateSystem.Z_UP  # 坐标系转换 ✔
    unit_scale: float = 1.0             # 单位缩放 ✔
    
    # 命名规范 ✔
    naming_template: str = "default"
    
    # 占位保留 ◆
    lod_rule_template: str = ""
    schema_file: str = ""
    directory_strategy: DirectoryStrategy = DirectoryStrategy.BY_TYPE
    
    # 导出选项 ✔
    auto_validate: bool = True          # 导出前自动检测
    write_audit: bool = True            # 写入审计日志


@dataclass
class ObjectSettings:
    """对象级设置（来自 Object Panel）"""
    object_type: ObjectType = ObjectType.STATIC  # 对象类型 ✔
    resource_id: str = ""               # 资源ID ✔
    group: str = ""                     # 分组 ✔
    
    # LOD ◆ 占位
    lod_enabled: bool = False
    lod_rule: str = ""
    
    # 硬点 ✔
    hardpoints: List[Dict[str, Any]] = field(default_factory=list)
    
    # 材质槽配置 ✔
    material_slots: List[MaterialSlot] = field(default_factory=list)


# ==================== Manifest / Audit 数据结构 ====================

@dataclass
class ManifestEntry:
    """清单条目"""
    file: str                           # 文件路径
    file_type: str                      # primitives / visual / model / animation
    dependencies: List[str] = field(default_factory=list)
    hash: str = ""
    timestamp: str = ""


@dataclass
class Manifest:
    """manifest.json 结构"""
    version: int = 1
    entries: List[ManifestEntry] = field(default_factory=list)


@dataclass
class AuditEntry:
    """审计日志条目"""
    code: str                           # 错误码（如 GEO001）
    message: str                        # 消息
    severity: str                       # ERROR / WARNING / INFO
    object_name: Optional[str] = None   # 关联对象
    timestamp: str = ""

