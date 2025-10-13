# File: ./ui_panel.py
# Relative path: blender_bigworld_exporter/ui_panel.py
# 功能描述:
# 本文件严格对齐《BigWorld Blender Exporter 最终定版方案》的 UI 设计与字段映射，重建对象级参数面板（N 面板）。
# 所有对象级参数通过一个集中式 PropertyGroup（BigWorldObjectSettingsV2）进行定义与管理，并完整绑定到 bpy.types.Object。
# 面板按照文档的分组进行呈现：基础设置、几何与转换、材质绑定、碰撞与派生、Hitbox 与硬点、门户与预制、动画事件、对象校验。
# 字段命名、类型、默认值与 Max 插件字段保持一一映射关系（参考“Max 插件字段 → Blender 插件字段 映射表”）。
# 本文件不包含任何省略、精简或示例代码。所有字段均可直接传递给核心导出逻辑（core/* Writers）与验证器（validators/*）。
# 关联依赖与核心：
# - 导出入口: export_operator.py 执行时读取 bpy.types.Object.bw_settings_v2 中的所有字段，聚合为 ExportRequest。
# - 核心 Writer 模块: core/primitives_writer.py、core/material_writer.py、core/skeleton_writer.py、core/animation_writer.py、
#   core/collision_writer.py、core/portal_writer.py、core/prefab_assembler.py、core/hitbox_xml_writer.py 通过 ExportRequest 消费该对象级参数。
# - 验证工具: validators/structure_checker.py、validators/path_validator.py 在 Pre/Post 校验阶段检查对象级字段的完整性与合法性。
# - 适配器层: ui_adapter.py（若存在）用于从 V1 字段回退读取或从 V2 字段优先读取，保证增量迁移安全。
# 注意事项:
# - 本文件仅负责对象级 UI 的字段定义与面板布局，不包含业务逻辑或导出流程代码。
# - 所有字段在重构后必须与 schema_reference.md 的字段规范一致，并在导出前进行严格校验。
# - 注册/注销函数完整实现，便于插件生命周期管理。

import bpy
from bpy.types import PropertyGroup, Panel
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
    CollectionProperty
)


class BigWorldMaterialSlotItem(bpy.types.PropertyGroup):
    # 材质槽映射项：slot_name → bw_material
    slot_name: StringProperty(
        name="Slot Name",
        description="Blender 材质槽名称"
    )
    bw_material: StringProperty(
        name="BigWorld Material",
        description="BigWorld 材质名或引用路径（相对路径）"
    )


class BigWorldAnimationEventItem(bpy.types.PropertyGroup):
    # 动画事件项：用于 CueTrack 的 JSON 列表拆解与校验（UI 存储为结构化数据）
    time: FloatProperty(
        name="Time",
        description="事件触发时间（秒）",
        default=0.0,
        min=0.0
    )
    event_type: StringProperty(
        name="Event Type",
        description="事件类型（字符串）"
    )
    params_json: StringProperty(
        name="Params (JSON)",
        description="事件参数（JSON 字符串，导出时需校验）"
    )


class BigWorldObjectSettingsV2(PropertyGroup):
    # —— 基础设置（Max: exportEnabled, exportType, resourceName, relativePath, groupIndex, lodLevel）——
    bw_export_enabled: BoolProperty(
        name="启用导出",
        description="对象是否参与导出流程",
        default=True
    )
    bw_export_type: EnumProperty(
        name="导出类型",
        description="静态网格或骨骼网格等类型选择",
        items=[
            ("STATIC_MESH", "静态网格", ""),
            ("SKINNED_MESH", "骨骼网格", "")
        ],
        default="STATIC_MESH"
    )
    bw_resource_name: StringProperty(
        name="资源名称",
        description="导出资源名称（文件名基）"
    )
    bw_relative_path: StringProperty(
        name="相对路径",
        description="导出到 res 下的相对路径（例如 /env/props/）",
        default=""
    )
    bw_group_index: IntProperty(
        name="分组索引",
        description="渲染子集或实例分组索引",
        default=0,
        min=0
    )
    bw_lod_level: IntProperty(
        name="LOD 等级",
        description="当前对象的 LOD 等级",
        default=0,
        min=0
    )

    # —— 几何与转换（Max: axisMapping, flipWinding, rebuildNormalsTangents, normalThreshold, precision）——
    bw_axis_mapping: BoolProperty(
        name="坐标轴映射 (Y→Z)",
        description="对象级坐标轴映射（会叠加会话级/偏好设置）",
        default=False
    )
    bw_flip_winding: BoolProperty(
        name="翻转绕序",
        description="翻转面绕序以匹配引擎渲染要求",
        default=False
    )
    bw_rebuild_normals: BoolProperty(
        name="重建法线/切线",
        description="重新计算法线与切线（当源数据不可靠时开启）",
        default=False
    )
    bw_normal_threshold: FloatProperty(
        name="法线角度阈值 (度)",
        description="平滑法线的角度阈值（度）",
        default=45.0,
        min=0.0,
        max=180.0
    )
    bw_precision: EnumProperty(
        name="精度类型",
        description="顶点数据精度（float32/float16）",
        items=[
            ("FLOAT32", "float32", ""),
            ("FLOAT16", "float16", "")
        ],
        default="FLOAT32"
    )

    # —— 材质绑定（Max: materialSlotMap, shaderTag, textureSet, supportPBR, proceduralTexture）——
    bw_material_slot_map: CollectionProperty(
        type=BigWorldMaterialSlotItem,
        name="材质槽映射",
        description="Blender 材质槽 → BigWorld 材质映射列表"
    )
    bw_shader_tag: EnumProperty(
        name="Shader 标签",
        description="材质管线标签（与 Max 插件对齐）",
        items=[
            ("BW_PBR", "BW_PBR", ""),
            ("BW_LEGACY", "BW_LEGACY", ""),
            ("BW_CUSTOM", "BW_CUSTOM", "")
        ],
        default="BW_PBR"
    )
    bw_texture_set: EnumProperty(
        name="纹理集合",
        description="材质贴图集合标记（由美术管线定义）",
        items=[
            ("default_pbr", "default_pbr", ""),
            ("character_pbr", "character_pbr", ""),
            ("environment_pbr", "environment_pbr", "")
        ],
        default="default_pbr"
    )
    bw_support_pbr: BoolProperty(
        name="支持 PBR",
        description="材质是否为 PBR 流程",
        default=True
    )
    bw_procedural_texture: BoolProperty(
        name="程序贴图",
        description="材质是否包含程序贴图",
        default=False
    )

    # —— 碰撞与派生（Max: collisionType, bakeWorldMatrix, groupTriangleCollision）——
    bw_collision_type: EnumProperty(
        name="碰撞体类型",
        description="导出碰撞体类别",
        items=[
            ("NONE", "无", ""),
            ("MESH", "Mesh", ""),
            ("BSP", "BSP", ""),
            ("CONVEX", "凸包", "")
        ],
        default="NONE"
    )
    bw_bake_world_matrix: BoolProperty(
        name="烘焙世界矩阵",
        description="将对象世界变换烘焙到静态碰撞体数据中",
        default=False
    )
    bw_group_triangle_collision: BoolProperty(
        name="群碰三角碰撞",
        description="启用群体三角碰撞支持（大型场景优化）",
        default=False
    )

    # —— Hitbox 与硬点（Max: hitboxName, hitboxType, hitboxLevel, hardpointName, hardpointType, bindBone）——
    bw_hitbox_name: StringProperty(
        name="Hitbox 名称",
        description="命中体名称"
    )
    bw_hitbox_type: EnumProperty(
        name="Hitbox 类型",
        description="命中体类型",
        items=[
            ("NONE", "无", ""),
            ("BOX", "Box", ""),
            ("SPHERE", "Sphere", ""),
            ("CAPSULE", "Capsule", ""),
            ("MESH", "Mesh", "")
        ],
        default="NONE"
    )
    bw_hitbox_level: EnumProperty(
        name="Hitbox 层级",
        description="命中体层级（对象级或骨骼级）",
        items=[
            ("OBJECT", "Object", ""),
            ("BONE", "Bone", "")
        ],
        default="OBJECT"
    )
    bw_hardpoint_name: StringProperty(
        name="硬点名称",
        description="挂点名称（武器/特效等）"
    )
    bw_hardpoint_type: StringProperty(
        name="硬点类型",
        description="挂点类型（字符串标记）"
    )
    bw_bind_bone: StringProperty(
        name="绑定骨骼",
        description="绑定骨骼名称（用于硬点或 Hitbox）"
    )

    # —— 门户与预制（Max: portalType, portalTag, portalGeometrySource, prefabGroup, instanceRole, seriesType, visibilityFlag, entryAttributeFlag）——
    bw_portal_type: EnumProperty(
        name="门户类型",
        description="场景门户类型（用于引擎场景连接）",
        items=[
            ("NONE", "无", ""),
            ("STANDARD", "Standard", ""),
            ("HEAVEN", "Heaven", ""),
            ("EXIT", "Exit", "")
        ],
        default="NONE"
    )
    bw_portal_tag: StringProperty(
        name="门户标签",
        description="门户标签（用于场景连接匹配）"
    )
    bw_portal_geometry_source: EnumProperty(
        name="几何来源",
        description="门户几何来源（包围盒或 Mesh）",
        items=[
            ("BOUNDING_BOX", "Bounding Box", ""),
            ("MESH", "Mesh", "")
        ],
        default="BOUNDING_BOX"
    )
    bw_prefab_group: StringProperty(
        name="预制体组名",
        description="预制体组名称"
    )
    bw_instance_role: StringProperty(
        name="实例角色",
        description="实例角色名称/标记"
    )
    bw_series_type: EnumProperty(
        name="系列类型",
        description="实例系列类型（u16/u32）",
        items=[
            ("U16", "u16", ""),
            ("U32", "u32", "")
        ],
        default="U16"
    )
    bw_visibility_flag: BoolProperty(
        name="可见性标志",
        description="对象在实例表中的可见性标志",
        default=True
    )
    bw_entry_attribute_flag: BoolProperty(
        name="入口属性标志",
        description="对象作为场景入口的标志",
        default=False
    )

    # —— 动画事件（Max: animationEvents）——
    bw_animation_events_json: StringProperty(
        name="动画事件 JSON",
        description="CueTrack 事件列表（JSON 字符串，导出前必校验）",
        default=""
    )
    bw_animation_events: CollectionProperty(
        type=BigWorldAnimationEventItem,
        name="动画事件列表",
        description="结构化的 CueTrack 事件项集合"
    )


class BW_PT_ObjectExportV2(Panel):
    bl_label = "BigWorld 对象导出参数"
    bl_idname = "BW_PT_ObjectExportV2"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw(self, context):
        obj = context.object
        layout = self.layout

        if not hasattr(obj, "bw_settings_v2"):
            layout.label(text="未检测到 BigWorld 对象设置（bw_settings_v2）。", icon='ERROR')
            return

        s = obj.bw_settings_v2

        # ▶ 基础设置
        box_base = layout.box()
        box_base.label(text="基础设置")
        col_base = box_base.column(align=True)
        col_base.prop(s, "bw_export_enabled")
        col_base.prop(s, "bw_export_type")
        col_base.prop(s, "bw_resource_name")
        col_base.prop(s, "bw_relative_path")
        row_base = col_base.row(align=True)
        row_base.prop(s, "bw_group_index")
        row_base.prop(s, "bw_lod_level")

        # ▶ 几何与转换
        box_geo = layout.box()
        box_geo.label(text="几何与转换")
        col_geo = box_geo.column(align=True)
        col_geo.prop(s, "bw_axis_mapping")
        col_geo.prop(s, "bw_flip_winding")
        col_geo.prop(s, "bw_rebuild_normals")
        col_geo.prop(s, "bw_normal_threshold")
        col_geo.prop(s, "bw_precision")

        # ▶ 材质绑定
        box_mat = layout.box()
        box_mat.label(text="材质绑定")
        col_mat = box_mat.column(align=True)
        col_mat.template_list("UI_UL_list", "bw_material_slot_map", s, "bw_material_slot_map", s, "bw_material_slot_map_index", rows=3)
        col_mat.prop(s, "bw_shader_tag")
        col_mat.prop(s, "bw_texture_set")
        row_mat = col_mat.row(align=True)
        row_mat.prop(s, "bw_support_pbr")
        row_mat.prop(s, "bw_procedural_texture")

        # ▶ 碰撞与派生
        box_col = layout.box()
        box_col.label(text="碰撞与派生")
        col_col = box_col.column(align=True)
        col_col.prop(s, "bw_collision_type")
        col_col.prop(s, "bw_bake_world_matrix")
        col_col.prop(s, "bw_group_triangle_collision")

        # ▶ Hitbox 与硬点
        box_hbx = layout.box()
        box_hbx.label(text="Hitbox 与硬点")
        col_hbx = box_hbx.column(align=True)
        col_hbx.prop(s, "bw_hitbox_name")
        col_hbx.prop(s, "bw_hitbox_type")
        col_hbx.prop(s, "bw_hitbox_level")
        col_hbx.separator()
        col_hbx.prop(s, "bw_hardpoint_name")
        col_hbx.prop(s, "bw_hardpoint_type")
        col_hbx.prop(s, "bw_bind_bone")

        # ▶ 门户与预制
        box_por = layout.box()
        box_por.label(text="门户与预制")
        col_por = box_por.column(align=True)
        col_por.prop(s, "bw_portal_type")
        col_por.prop(s, "bw_portal_tag")
        col_por.prop(s, "bw_portal_geometry_source")
        col_por.separator()
        col_por.prop(s, "bw_prefab_group")
        col_por.prop(s, "bw_instance_role")
        col_por.prop(s, "bw_series_type")
        row_vis = col_por.row(align=True)
        row_vis.prop(s, "bw_visibility_flag")
        row_vis.prop(s, "bw_entry_attribute_flag")

        # ▶ 动画事件
        box_ani = layout.box()
        box_ani.label(text="动画事件")
        col_ani = box_ani.column(align=True)
        col_ani.prop(s, "bw_animation_events_json")
        col_ani.template_list("UI_UL_list", "bw_animation_events", s, "bw_animation_events", s, "bw_animation_events_index", rows=3)

        # ▶ 对象校验（只读状态）
        box_val = layout.box()
        box_val.label(text="对象校验")
        col_val = box_val.column(align=True)
        col_val.label(text="请在导出前运行结构校验与路径校验（由导出对话框控制）。")


classes = (
    BigWorldMaterialSlotItem,
    BigWorldAnimationEventItem,
    BigWorldObjectSettingsV2,
    BW_PT_ObjectExportV2,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.bw_settings_v2 = bpy.props.PointerProperty(type=BigWorldObjectSettingsV2)
    # 用于 UI 列表索引存储（材质槽映射、动画事件列表）
    bpy.types.Object.bw_material_slot_map_index = IntProperty(
        name="Material Slot Map Index",
        description="材质槽映射列表 UI 索引",
        default=0,
        min=0
    )
    bpy.types.Object.bw_animation_events_index = IntProperty(
        name="Animation Events Index",
        description="动画事件列表 UI 索引",
        default=0,
        min=0
    )


def unregister():
    # 注销顺序反向
    del bpy.types.Object.bw_animation_events_index
    del bpy.types.Object.bw_material_slot_map_index
    del bpy.types.Object.bw_settings_v2
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
