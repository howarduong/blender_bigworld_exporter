# File: ./ui_panel_export.py
# Relative path: blender_bigworld_exporter/ui_panel_export.py
# 功能描述:
# 本文件严格对齐《BigWorld Blender Exporter 最终定版方案》的 UI 设计与字段映射，重建场景级导出对话框面板。
# 所有会话级参数通过集中式 PropertyGroup（BigWorldExportSettingsV2）进行定义与管理，并完整绑定到 bpy.types.Scene。
# 面板按照文档分组呈现：路径与坐标、Skeleton 与 Animation 设置、导出范围、导出模块、校验与日志、状态与执行。
# 字段命名、类型、默认值与 Max 插件字段保持一一映射关系（参考“Max 插件字段 → Blender 插件字段 映射表”）。
# 本文件不包含任何省略、精简或示例代码。所有字段均被导出入口（export_operator.py）读取并传递到核心 Writer/Validator。
# 关联依赖与核心：
# - 导出入口: export_operator.py 从 bpy.types.Scene.bw_export_v2 读取所有会话级参数。
# - 核心 Writer 模块: core/* 依据模块开关（mesh/material/skeleton/animation/collision/portal/prefab/hitbox/cuetrack）执行。
# - 验证工具: validators/* 按校验与日志选项运行结构校验、Hex 对比、路径校验与修复。
# - 节组织: core/binsection_writer.py 统一组织 Section 顺序与字节对齐。
# 注意事项:
# - 导出范围（全部/选中/集合）为单选逻辑，不允许混合。
# - 标签过滤逻辑由 export_operator.py 实施，字段定义与 UI 控制在此文件。
# - 所有字段在重构后必须与 schema_reference.md 的字段规范一致，并在导出前进行严格校验。

import bpy
from bpy.types import PropertyGroup, Panel
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty
)


class BigWorldExportSettingsV2(PropertyGroup):
    # —— 路径与坐标（Max: exportPath, tempPath, coordinateSystem, defaultScale, applyScaleToGeometry）——
    bw_export_path: StringProperty(
        name="导出路径",
        description="本次导出会话的输出根目录（指向 res 根）",
        subtype='DIR_PATH',
        default=""
    )
    bw_temp_path: StringProperty(
        name="临时路径",
        description="导出临时数据与报告存放目录",
        subtype='DIR_PATH',
        default=""
    )
    bw_coordinate_system: EnumProperty(
        name="坐标系统",
        description="坐标系统选择（与 Max 插件对齐）",
        items=[
            ("MAX_COMPAT", "与 Max 兼容", ""),
            ("BLENDER_NATIVE", "Blender 原生", "")
        ],
        default="MAX_COMPAT"
    )
    bw_default_scale: FloatProperty(
        name="默认缩放",
        description="单位缩放（用于尺寸对齐）",
        default=1.0,
        min=0.0001
    )
    bw_apply_scale_to_geometry: BoolProperty(
        name="应用缩放到几何",
        description="将默认缩放应用到几何数据中",
        default=True
    )

    # —— Skeleton 与 Animation 设置（Max: skeletonMatrixMode, skeletonFrameScale, animationMatrixMode, animationFPS, enableCueTrack）——
    bw_skeleton_matrix_mode: BoolProperty(
        name="Skeleton 行主序矩阵",
        description="骨骼矩阵采用行主序写入模式",
        default=True
    )
    bw_skeleton_frame_scale: BoolProperty(
        name="Skeleton 帧世界缩放",
        description="骨骼动画帧应用世界缩放策略",
        default=False
    )
    bw_animation_matrix_mode: BoolProperty(
        name="Animation 行主序矩阵",
        description="动画矩阵采用行主序写入模式",
        default=True
    )
    bw_animation_fps: IntProperty(
        name="Animation FPS",
        description="动画采样帧率",
        default=30,
        min=1,
        max=240
    )
    bw_enable_cuetrack: BoolProperty(
        name="启用 CueTrack",
        description="导出动画事件轨（需要对象级 JSON 字段合法）",
        default=True
    )

    # —— 导出范围（Max: exportAllObjects, exportSelectedObjects, exportCollectionObjects, exportTagFilter）——
    bw_export_all_objects: BoolProperty(
        name="导出全部对象",
        description="导出场景中的全部对象",
        default=True
    )
    bw_export_selected_objects: BoolProperty(
        name="仅导出选中对象",
        description="仅导出当前选中的对象",
        default=False
    )
    bw_export_collection_objects: BoolProperty(
        name="导出所在集合",
        description="导出当前集合中的对象",
        default=False
    )
    bw_export_tag_filter: StringProperty(
        name="标签过滤",
        description="按标签过滤导出对象（自定义属性或命名空间前缀）",
        default=""
    )

    # —— 导出模块（Max: mesh/material/skeleton/animation/collision/portal/prefab/hitbox/cuetrack）——
    bw_export_mesh: BoolProperty(
        name="网格 (Mesh)",
        description="启用网格数据导出",
        default=True
    )
    bw_export_material: BoolProperty(
        name="材质 (Material)",
        description="启用材质与纹理路径导出",
        default=True
    )
    bw_export_skeleton: BoolProperty(
        name="骨骼 (Skeleton)",
        description="启用骨骼层级与硬点导出",
        default=True
    )
    bw_export_animation: BoolProperty(
        name="动画 (Animation)",
        description="启用动画轨道与帧数据导出",
        default=False
    )
    bw_export_collision: BoolProperty(
        name="碰撞 (Collision)",
        description="启用碰撞体导出",
        default=False
    )
    bw_export_portal: BoolProperty(
        name="门户 (Portal)",
        description="启用门户数据导出",
        default=False
    )
    bw_export_prefab: BoolProperty(
        name="预制/实例表 (Prefab/Instances)",
        description="启用预制体与实例表导出",
        default=False
    )
    bw_export_hitbox: BoolProperty(
        name="Hitbox / XML",
        description="启用命中体数据导出（XML/二进制）",
        default=False
    )
    bw_export_cuetrack: BoolProperty(
        name="事件轨 (CueTrack)",
        description="启用事件轨导出（依赖动画模块）",
        default=True
    )

    # —— 校验与日志（Max: enableStructureCheck, enableHexDiff, enablePathCheck, enablePathFix, logLevel, saveReport）——
    bw_enable_structure_check: BoolProperty(
        name="启用结构校验（严格）",
        description="导出前后进行结构校验（字段/顺序/对齐）",
        default=True
    )
    bw_enable_hex_diff: BoolProperty(
        name="启用 Hex 对比",
        description="与 Max 导出文件逐字节对比",
        default=True
    )
    bw_enable_path_check: BoolProperty(
        name="校验资源路径",
        description="校验路径合法性与资源存在性",
        default=True
    )
    bw_enable_path_fix: BoolProperty(
        name="自动修复路径",
        description="对非法及绝对路径进行自动修复（将记录到报告）",
        default=False
    )
    bw_log_level: EnumProperty(
        name="日志等级",
        description="导出过程中日志输出详细程度",
        items=[
            ("INFO", "Info", ""),
            ("DEBUG", "Debug", ""),
            ("ERROR", "Error", "")
        ],
        default="INFO"
    )
    bw_save_report: BoolProperty(
        name="保存报告",
        description="导出与校验报告持久化到临时目录",
        default=True
    )


class BW_PT_ExportDialogV2(Panel):
    bl_label = "BigWorld 导出执行"
    bl_idname = "BW_PT_ExportDialogV2"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BigWorld"

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        if not hasattr(scene, "bw_export_v2"):
            layout.label(text="未检测到 BigWorld 导出设置（bw_export_v2）。", icon='ERROR')
            return

        s = scene.bw_export_v2

        # ▶ 路径与坐标
        box_path = layout.box()
        box_path.label(text="路径与坐标")
        col_path = box_path.column(align=True)
        col_path.prop(s, "bw_export_path")
        col_path.prop(s, "bw_temp_path")
        col_path.prop(s, "bw_coordinate_system")
        row_scale = col_path.row(align=True)
        row_scale.prop(s, "bw_default_scale")
        row_scale.prop(s, "bw_apply_scale_to_geometry")

        # ▶ Skeleton 与 Animation 设置
        box_ska = layout.box()
        box_ska.label(text="Skeleton 与 Animation 设置")
        col_ska = box_ska.column(align=True)
        col_ska.prop(s, "bw_skeleton_matrix_mode")
        col_ska.prop(s, "bw_skeleton_frame_scale")
        col_ska.prop(s, "bw_animation_matrix_mode")
        col_ska.prop(s, "bw_animation_fps")
        col_ska.prop(s, "bw_enable_cuetrack")

        # ▶ 导出范围（单选逻辑提示）
        box_rng = layout.box()
        box_rng.label(text="导出范围")
        col_rng = box_rng.column(align=True)
        col_rng.prop(s, "bw_export_all_objects")
        col_rng.prop(s, "bw_export_selected_objects")
        col_rng.prop(s, "bw_export_collection_objects")
        col_rng.prop(s, "bw_export_tag_filter")
        col_rng.label(text="注意：导出范围为单选逻辑，导出入口将根据优先级进行筛选。")

        # ▶ 导出模块
        box_mod = layout.box()
        box_mod.label(text="导出模块")
        col_mod = box_mod.column(align=True)
        row_mod1 = col_mod.row(align=True)
        row_mod1.prop(s, "bw_export_mesh")
        row_mod1.prop(s, "bw_export_material")
        row_mod1.prop(s, "bw_export_skeleton")
        row_mod2 = col_mod.row(align=True)
        row_mod2.prop(s, "bw_export_animation")
        row_mod2.prop(s, "bw_export_collision")
        row_mod2.prop(s, "bw_export_portal")
        row_mod3 = col_mod.row(align=True)
        row_mod3.prop(s, "bw_export_prefab")
        row_mod3.prop(s, "bw_export_hitbox")
        row_mod3.prop(s, "bw_export_cuetrack")
        col_mod.label(text="提示：事件轨依赖动画模块；若仅启用事件轨而关闭动画将阻断导出。")

        # ▶ 校验与日志
        box_val = layout.box()
        box_val.label(text="校验与日志")
        col_val = box_val.column(align=True)
        col_val.prop(s, "bw_enable_structure_check")
        col_val.prop(s, "bw_enable_hex_diff")
        col_val.prop(s, "bw_enable_path_check")
        col_val.prop(s, "bw_enable_path_fix")
        col_val.prop(s, "bw_log_level")
        col_val.prop(s, "bw_save_report")

        # ▶ 状态与执行
        box_run = layout.box()
        box_run.label(text="状态与执行")
        col_run = box_run.column(align=True)
        col_run.operator("bw.export", text="开始导出", icon='EXPORT')
        col_run.operator("bw.open_log", text="打开日志", icon='TEXT')
        col_run.label(text="执行后将显示状态码与报告路径。")


classes = (
    BigWorldExportSettingsV2,
    BW_PT_ExportDialogV2,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bw_export_v2 = bpy.props.PointerProperty(type=BigWorldExportSettingsV2)


def unregister():
    del bpy.types.Scene.bw_export_v2
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
